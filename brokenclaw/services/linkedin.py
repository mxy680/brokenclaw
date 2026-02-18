"""LinkedIn service layer — parses Voyager API responses into Pydantic models."""

from urllib.parse import quote

from brokenclaw.models.linkedin import (
    LinkedInConnection,
    LinkedInConversation,
    LinkedInEducation,
    LinkedInExperience,
    LinkedInFullProfile,
    LinkedInMessage,
    LinkedInNotification,
    LinkedInPost,
    LinkedInProfile,
    LinkedInSearchResult,
    LinkedInSkill,
)
from brokenclaw.services.linkedin_client import (
    _extract_voyager_entities,
    linkedin_get,
    linkedin_get_paginated,
)


def _format_date(date_dict: dict | None) -> str | None:
    """Format a Voyager date object {month, year} to 'YYYY-MM' string."""
    if not date_dict:
        return None
    year = date_dict.get("year")
    month = date_dict.get("month")
    if year and month:
        return f"{year}-{month:02d}"
    if year:
        return str(year)
    return None


def _get_profile_url(public_id: str | None) -> str | None:
    if not public_id:
        return None
    return f"https://www.linkedin.com/in/{public_id}"


# --- Profile ---


def get_my_profile(account: str = "default") -> LinkedInProfile:
    """Get the authenticated user's profile."""
    data = linkedin_get("me", account)
    mini = data.get("miniProfile") or data
    public_id = mini.get("publicIdentifier") or data.get("publicIdentifier")
    return LinkedInProfile(
        entity_urn=data.get("entityUrn") or mini.get("entityUrn"),
        first_name=mini.get("firstName") or data.get("firstName"),
        last_name=mini.get("lastName") or data.get("lastName"),
        headline=mini.get("headline") or data.get("headline"),
        summary=data.get("summary"),
        location=mini.get("locationName") or data.get("locationName"),
        profile_url=_get_profile_url(public_id),
    )


def get_full_profile(
    public_id: str,
    account: str = "default",
) -> LinkedInFullProfile:
    """Get a full profile by public ID (the slug in linkedin.com/in/{slug})."""
    # Basic profile info
    data = linkedin_get(f"identity/profiles/{public_id}", account)
    profile = LinkedInProfile(
        entity_urn=data.get("entityUrn"),
        first_name=data.get("firstName"),
        last_name=data.get("lastName"),
        headline=data.get("headline"),
        summary=data.get("summary"),
        location=data.get("locationName") or data.get("geoLocationName"),
        profile_url=_get_profile_url(public_id),
    )

    # Experience
    experience = []
    try:
        exp_data = linkedin_get(
            f"identity/profiles/{public_id}/positions",
            account,
            params={"count": 50},
        )
        for elem in exp_data.get("included", []):
            if "title" in elem or "companyName" in elem:
                experience.append(LinkedInExperience(
                    title=elem.get("title"),
                    company_name=elem.get("companyName"),
                    location=elem.get("locationName"),
                    start_date=_format_date(elem.get("timePeriod", {}).get("startDate")),
                    end_date=_format_date(elem.get("timePeriod", {}).get("endDate")),
                    description=elem.get("description"),
                ))
    except Exception:
        pass

    # Education
    education = []
    try:
        edu_data = linkedin_get(
            f"identity/profiles/{public_id}/educations",
            account,
            params={"count": 50},
        )
        for elem in edu_data.get("included", []):
            if "schoolName" in elem or "degreeName" in elem:
                tp = elem.get("timePeriod", {})
                education.append(LinkedInEducation(
                    school_name=elem.get("schoolName"),
                    degree=elem.get("degreeName"),
                    field_of_study=elem.get("fieldOfStudy"),
                    start_year=tp.get("startDate", {}).get("year") if tp.get("startDate") else None,
                    end_year=tp.get("endDate", {}).get("year") if tp.get("endDate") else None,
                ))
    except Exception:
        pass

    # Skills
    skills = []
    try:
        skill_data = linkedin_get(
            f"identity/profiles/{public_id}/skills",
            account,
            params={"count": 50},
        )
        for elem in skill_data.get("included", []):
            if "name" in elem and elem.get("$type", "").endswith("Skill"):
                skills.append(LinkedInSkill(
                    name=elem.get("name"),
                    endorsement_count=elem.get("endorsementCount"),
                ))
    except Exception:
        pass

    return LinkedInFullProfile(
        profile=profile,
        experience=experience,
        education=education,
        skills=skills,
    )


# --- Feed ---


def get_feed(count: int = 20, account: str = "default") -> list[LinkedInPost]:
    """Get the user's LinkedIn feed posts."""
    data = linkedin_get(
        "feed/updatesV2",
        account,
        params={"q": "FEED_TYPE_FOLLOWED", "count": count},
    )

    posts = []
    # Build a lookup of included entities by entityUrn
    included_map = {}
    for item in data.get("included", []):
        urn = item.get("entityUrn") or item.get("$id")
        if urn:
            included_map[urn] = item

    for item in data.get("included", []):
        type_name = item.get("$type", "")

        # Look for activity/update entities
        if "Activity" not in type_name and "Update" not in type_name:
            continue

        # Try to extract post text from commentary or various fields
        text = None
        commentary = item.get("commentary") or item.get("specificContent", {}).get("com.linkedin.ugc.ShareContent", {}).get("shareCommentary", {})
        if isinstance(commentary, dict):
            text = commentary.get("text")
        elif isinstance(commentary, str):
            text = commentary

        if not text:
            text = item.get("text") or item.get("message")

        if not text:
            continue

        # Extract author info
        author_name = None
        actor = item.get("actor") or item.get("author")
        if isinstance(actor, dict):
            author_name = actor.get("name") or actor.get("firstName")
        elif isinstance(actor, str) and actor in included_map:
            actor_entity = included_map[actor]
            first = actor_entity.get("firstName", "")
            last = actor_entity.get("lastName", "")
            author_name = f"{first} {last}".strip() or actor_entity.get("name")

        # Engagement counts
        social = item.get("socialDetail") or {}
        if isinstance(social, str) and social in included_map:
            social = included_map[social]

        urn = item.get("entityUrn") or item.get("urn") or ""
        activity_id = urn.split(":")[-1] if urn else None
        url = f"https://www.linkedin.com/feed/update/{urn}" if urn else None

        posts.append(LinkedInPost(
            author_name=author_name,
            text=text[:2000] if text else None,
            created_at=item.get("createdAt") or item.get("created", {}).get("time"),
            num_likes=social.get("totalSocialActivityCounts", {}).get("numLikes") if isinstance(social, dict) else None,
            num_comments=social.get("totalSocialActivityCounts", {}).get("numComments") if isinstance(social, dict) else None,
            url=url,
        ))

    return posts


# --- Connections ---


def list_connections(
    count: int = 20,
    start: int = 0,
    account: str = "default",
) -> list[LinkedInConnection]:
    """List the user's connections."""
    data = linkedin_get(
        "relationships/connections",
        account,
        params={"sortType": "RECENTLY_ADDED", "count": count, "start": start},
    )

    connections = []
    profiles = _extract_voyager_entities(data, "MiniProfile")
    for p in profiles:
        public_id = p.get("publicIdentifier")
        connections.append(LinkedInConnection(
            first_name=p.get("firstName"),
            last_name=p.get("lastName"),
            headline=p.get("headline"),
            profile_url=_get_profile_url(public_id),
            connected_at=p.get("connectedAt"),
        ))

    return connections


# --- Messaging ---


def list_conversations(
    count: int = 20,
    account: str = "default",
) -> list[LinkedInConversation]:
    """List recent messaging conversations."""
    data = linkedin_get(
        "messaging/conversations",
        account,
        params={"keyVersion": "LEGACY_INBOX", "count": count},
    )

    included_map = {}
    for item in data.get("included", []):
        urn = item.get("entityUrn") or item.get("$id")
        if urn:
            included_map[urn] = item

    conversations = []
    for item in data.get("included", []):
        type_name = item.get("$type", "")
        if "Conversation" not in type_name:
            continue

        # Extract participants
        participants = []
        for p_ref in item.get("participants", []):
            if isinstance(p_ref, dict):
                mini = p_ref.get("com.linkedin.voyager.messaging.MessagingMember") or p_ref
                profile = mini.get("miniProfile", {})
                first = profile.get("firstName", "")
                last = profile.get("lastName", "")
                name = f"{first} {last}".strip()
                if name:
                    participants.append(name)
            elif isinstance(p_ref, str) and p_ref in included_map:
                member = included_map[p_ref]
                profile = member.get("miniProfile", {})
                if isinstance(profile, str) and profile in included_map:
                    profile = included_map[profile]
                first = profile.get("firstName", "")
                last = profile.get("lastName", "")
                name = f"{first} {last}".strip()
                if name:
                    participants.append(name)

        # Last message
        last_msg = None
        events = item.get("events", [])
        if events:
            last_event = events[0] if isinstance(events[0], dict) else included_map.get(events[0], {})
            event_content = last_event.get("eventContent") or {}
            if isinstance(event_content, dict):
                msg_event = event_content.get("com.linkedin.voyager.messaging.event.MessageEvent") or event_content
                body = msg_event.get("body") or msg_event.get("attributedBody", {}).get("text")
                last_msg = body

        conversations.append(LinkedInConversation(
            conversation_urn=item.get("entityUrn"),
            participants=participants,
            last_message_text=last_msg,
            last_activity_at=item.get("lastActivityAt"),
            unread=item.get("unreadCount", 0) > 0 if item.get("unreadCount") is not None else None,
        ))

    return conversations


def get_conversation_messages(
    conversation_urn: str,
    count: int = 20,
    account: str = "default",
) -> list[LinkedInMessage]:
    """Get messages from a specific conversation."""
    # conversation_urn is like "urn:li:messagingThread:2-xxx"
    # The API path uses the full URN encoded
    encoded_urn = quote(conversation_urn, safe="")
    data = linkedin_get(
        f"messaging/conversations/{encoded_urn}/events",
        account,
        params={"count": count},
    )

    included_map = {}
    for item in data.get("included", []):
        urn = item.get("entityUrn") or item.get("$id")
        if urn:
            included_map[urn] = item

    messages = []
    for item in data.get("included", []):
        type_name = item.get("$type", "")
        if "Event" not in type_name:
            continue

        event_content = item.get("eventContent") or {}
        if isinstance(event_content, dict):
            msg_event = event_content.get("com.linkedin.voyager.messaging.event.MessageEvent") or event_content
            body = msg_event.get("body") or msg_event.get("attributedBody", {}).get("text")
        else:
            body = None

        if not body:
            continue

        # Sender info
        sender_name = None
        sender_ref = item.get("from") or item.get("sender")
        if isinstance(sender_ref, dict):
            mini = sender_ref.get("com.linkedin.voyager.messaging.MessagingMember", {}).get("miniProfile", {})
            if isinstance(mini, str) and mini in included_map:
                mini = included_map[mini]
            first = mini.get("firstName", "")
            last = mini.get("lastName", "")
            sender_name = f"{first} {last}".strip() or None
        elif isinstance(sender_ref, str) and sender_ref in included_map:
            member = included_map[sender_ref]
            mini = member.get("miniProfile", {})
            if isinstance(mini, str) and mini in included_map:
                mini = included_map[mini]
            first = mini.get("firstName", "")
            last = mini.get("lastName", "")
            sender_name = f"{first} {last}".strip() or None

        messages.append(LinkedInMessage(
            sender_name=sender_name,
            text=body,
            sent_at=item.get("createdAt"),
        ))

    return messages


# --- Notifications ---


def list_notifications(
    count: int = 20,
    account: str = "default",
) -> list[LinkedInNotification]:
    """List recent notifications."""
    data = linkedin_get(
        "notifications",
        account,
        params={"count": count},
    )

    notifications = []
    for item in data.get("included", []):
        type_name = item.get("$type", "")
        if "Notification" not in type_name:
            continue

        # Extract text from headline or various fields
        headline = item.get("headline") or {}
        text = headline.get("text") if isinstance(headline, dict) else str(headline) if headline else None

        if not text:
            text = item.get("subHeadline", {}).get("text") if isinstance(item.get("subHeadline"), dict) else None

        notifications.append(LinkedInNotification(
            text=text,
            notification_type=item.get("notificationType") or item.get("trackingId"),
            created_at=item.get("publishedAt") or item.get("createdAt"),
            url=item.get("navigationUrl"),
        ))

    return notifications


# --- Search ---


def _search(
    keywords: str,
    type_filter: str | None = None,
    count: int = 10,
    location: str | None = None,
    account: str = "default",
) -> list[LinkedInSearchResult]:
    """Search LinkedIn using the Voyager search endpoint."""
    params: dict = {
        "q": "all",
        "keywords": keywords,
        "count": count,
        "origin": "GLOBAL_SEARCH_HEADER",
    }
    if type_filter:
        params["filters"] = f"List(resultType->{type_filter})"
    if location:
        params["keywords"] = f"{keywords} {location}"

    data = linkedin_get("search/dash/clusters", account, params=params)

    results = []
    for item in data.get("included", []):
        type_name = item.get("$type", "")

        # Look for search result entities
        if "SearchHit" in type_name or "EntityResult" in type_name:
            title = item.get("title") or {}
            title_text = title.get("text") if isinstance(title, dict) else str(title) if title else None

            summary = item.get("primarySubtitle") or item.get("headline") or {}
            summary_text = summary.get("text") if isinstance(summary, dict) else str(summary) if summary else None

            secondary = item.get("secondarySubtitle") or item.get("subline") or {}
            location_text = secondary.get("text") if isinstance(secondary, dict) else str(secondary) if secondary else None

            nav_url = item.get("navigationUrl")

            results.append(LinkedInSearchResult(
                name=title_text,
                headline=summary_text,
                location=location_text,
                result_type=type_filter or "UNKNOWN",
                url=nav_url,
            ))

    return results


def search_people(
    keywords: str,
    count: int = 10,
    account: str = "default",
) -> list[LinkedInSearchResult]:
    """Search for people on LinkedIn."""
    return _search(keywords, "PEOPLE", count, account=account)


def search_companies(
    keywords: str,
    count: int = 10,
    account: str = "default",
) -> list[LinkedInSearchResult]:
    """Search for companies on LinkedIn."""
    return _search(keywords, "COMPANIES", count, account=account)


def search_jobs(
    keywords: str,
    location: str | None = None,
    count: int = 10,
    account: str = "default",
) -> list[LinkedInSearchResult]:
    """Search for jobs on LinkedIn."""
    return _search(keywords, "JOBS", count, location=location, account=account)
