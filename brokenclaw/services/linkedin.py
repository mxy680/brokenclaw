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
    # Profile data is in the included array as a MiniProfile entity
    mini = _extract_voyager_entities(data, "MiniProfile")
    mini = mini[0] if mini else {}
    public_id = mini.get("publicIdentifier")
    return LinkedInProfile(
        entity_urn=mini.get("entityUrn") or mini.get("dashEntityUrn"),
        first_name=mini.get("firstName"),
        last_name=mini.get("lastName"),
        headline=mini.get("occupation") or mini.get("headline"),
        summary=mini.get("summary"),
        location=mini.get("locationName"),
        profile_url=_get_profile_url(public_id),
    )


def get_full_profile(
    public_id: str,
    account: str = "default",
) -> LinkedInFullProfile:
    """Get a full profile by public ID (the slug in linkedin.com/in/{slug}).

    Uses the GraphQL profile endpoint since the old identity/profiles
    endpoint returns 410.
    """
    # Basic profile via graphql
    qs = f"includeWebMetadata=true&variables=(vanityName:{public_id})&queryId=voyagerIdentityDashProfiles.34ead06db82a2cc9a778fac97f69ad6a"
    data = linkedin_get("graphql", account, raw_qs=qs)

    included = data.get("included", [])
    profile_data = {}
    experience = []
    education = []
    skills = []

    for item in included:
        type_name = item.get("$type", "")

        if type_name.endswith("Profile"):
            if not profile_data or item.get("firstName"):
                profile_data = item

        if type_name.endswith("Position") or ("title" in item and "companyName" in item):
            tp = item.get("timePeriod") or item.get("dateRange") or {}
            experience.append(LinkedInExperience(
                title=item.get("title"),
                company_name=item.get("companyName"),
                location=item.get("locationName"),
                start_date=_format_date(tp.get("startDate") or tp.get("start")),
                end_date=_format_date(tp.get("endDate") or tp.get("end")),
                description=item.get("description"),
            ))

        if type_name.endswith("Education") or "schoolName" in item or "degreeName" in item:
            tp = item.get("timePeriod") or item.get("dateRange") or {}
            sd = tp.get("startDate") or tp.get("start") or {}
            ed = tp.get("endDate") or tp.get("end") or {}
            education.append(LinkedInEducation(
                school_name=item.get("schoolName"),
                degree=item.get("degreeName"),
                field_of_study=item.get("fieldOfStudy"),
                start_year=sd.get("year") if isinstance(sd, dict) else None,
                end_year=ed.get("year") if isinstance(ed, dict) else None,
            ))

        if type_name.endswith("Skill") and "name" in item:
            skills.append(LinkedInSkill(
                name=item.get("name"),
                endorsement_count=item.get("endorsementCount"),
            ))

    profile = LinkedInProfile(
        entity_urn=profile_data.get("entityUrn") or profile_data.get("dashEntityUrn"),
        first_name=profile_data.get("firstName"),
        last_name=profile_data.get("lastName"),
        headline=profile_data.get("headline") or profile_data.get("occupation"),
        summary=profile_data.get("summary"),
        location=profile_data.get("locationName") or profile_data.get("geoLocationName"),
        profile_url=_get_profile_url(public_id),
    )

    return LinkedInFullProfile(
        profile=profile,
        experience=experience,
        education=education,
        skills=skills,
    )


# --- Feed ---


def get_feed(count: int = 20, account: str = "default") -> list[LinkedInPost]:
    """Get the user's LinkedIn feed posts.

    Uses the voyagerFeedDashMainFeed GraphQL endpoint.
    """
    qs = f"includeWebMetadata=true&variables=(start:0,count:{count},sortOrder:RELEVANCE)&queryId=voyagerFeedDashMainFeed.923020905727c01516495a0ac90bb475"
    try:
        data = linkedin_get("graphql", account, raw_qs=qs)
    except Exception:
        return []

    posts = []
    included = data.get("included", [])

    # Build entity map for cross-referencing
    entity_map = {}
    for item in included:
        urn = item.get("entityUrn") or item.get("$id")
        if urn:
            entity_map[urn] = item

    # Extract updates
    for item in included:
        type_name = item.get("$type", "")
        if not type_name.endswith("Update"):
            continue

        # Extract post text from commentary
        text = None
        commentary = item.get("commentary") or {}
        if isinstance(commentary, dict):
            text_obj = commentary.get("text") or {}
            if isinstance(text_obj, dict):
                text = text_obj.get("text")
            elif isinstance(text_obj, str):
                text = text_obj
        if not text:
            continue

        # Author info — actor is an inline component object in modern feed
        author_name = None
        actor = item.get("actor") or {}
        if isinstance(actor, dict):
            name_obj = actor.get("name") or {}
            if isinstance(name_obj, dict):
                author_name = name_obj.get("text")
        elif isinstance(actor, str) and actor in entity_map:
            actor_entity = entity_map[actor]
            first = actor_entity.get("firstName", "")
            last = actor_entity.get("lastName", "")
            author_name = f"{first} {last}".strip() or actor_entity.get("name")

        # Social counts — follow ref chain: *socialDetail → *totalSocialActivityCounts
        social_ref = item.get("*socialDetail")
        social = entity_map.get(social_ref, {}) if isinstance(social_ref, str) else {}
        counts_ref = social.get("*totalSocialActivityCounts") or social.get("totalSocialActivityCounts")
        if isinstance(counts_ref, str) and counts_ref in entity_map:
            counts = entity_map[counts_ref]
        elif isinstance(counts_ref, dict):
            counts = counts_ref
        else:
            counts = {}

        urn = item.get("entityUrn") or ""
        url = f"https://www.linkedin.com/feed/update/{urn}" if urn else None

        posts.append(LinkedInPost(
            author_name=author_name,
            text=text[:2000] if text else None,
            created_at=item.get("createdAt"),
            num_likes=counts.get("numLikes") if isinstance(counts, dict) else None,
            num_comments=counts.get("numComments") if isinstance(counts, dict) else None,
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
            headline=p.get("occupation") or p.get("headline"),
            profile_url=_get_profile_url(public_id),
            connected_at=p.get("connectedAt"),
        ))

    return connections


# --- Messaging ---


def list_conversations(
    count: int = 20,
    account: str = "default",
) -> list[LinkedInConversation]:
    """List recent messaging conversations.

    Uses the voyagerMessagingGraphQL endpoint.
    """
    # Get user's profile URN first
    me = linkedin_get("me", account)
    mini = _extract_voyager_entities(me, "MiniProfile")
    profile_urn = mini[0].get("dashEntityUrn", "") if mini else ""
    encoded_urn = quote(profile_urn, safe="")

    qs = f"queryId=messengerConversations.0d5e6781bbee71c3e51c8843c6519f48&variables=(mailboxUrn:{encoded_urn})"
    try:
        data = linkedin_get("voyagerMessagingGraphQL/graphql", account, raw_qs=qs)
    except Exception:
        return []

    included = data.get("included", [])
    entity_map = {}
    for item in included:
        urn = item.get("entityUrn") or item.get("$id")
        if urn:
            entity_map[urn] = item

    conversations = []
    for item in included:
        type_name = item.get("$type", "")
        if "Conversation" not in type_name:
            continue

        # Participants — refs in *conversationParticipants, entities have
        # participantType.member.firstName.text / lastName.text
        participants = []
        p_refs = item.get("*conversationParticipants", item.get("conversationParticipants", []))
        if isinstance(p_refs, list):
            for p_ref in p_refs:
                participant = entity_map.get(p_ref) if isinstance(p_ref, str) else p_ref
                if not isinstance(participant, dict):
                    continue
                pt = participant.get("participantType") or {}
                member = pt.get("member") or {}
                first_obj = member.get("firstName") or {}
                last_obj = member.get("lastName") or {}
                first = first_obj.get("text", "") if isinstance(first_obj, dict) else str(first_obj)
                last = last_obj.get("text", "") if isinstance(last_obj, dict) else str(last_obj)
                name = f"{first} {last}".strip()
                if name:
                    participants.append(name)

        # Last message text — from linked Message entities
        last_msg = None
        msgs = item.get("messages") or {}
        msg_refs = msgs.get("*elements", []) if isinstance(msgs, dict) else []
        if msg_refs:
            msg_entity = entity_map.get(msg_refs[0]) if isinstance(msg_refs[0], str) else None
            if isinstance(msg_entity, dict):
                body = msg_entity.get("body")
                if isinstance(body, dict):
                    last_msg = body.get("text")
                elif isinstance(body, str):
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
    encoded_urn = quote(conversation_urn, safe="")
    qs = f"queryId=messengerMessages.5846eeb71c981f11e0134cb6626cc314&variables=(conversationUrn:{encoded_urn})"
    try:
        data = linkedin_get("voyagerMessagingGraphQL/graphql", account, raw_qs=qs)
    except Exception:
        return []

    included = data.get("included", [])
    entity_map = {}
    for item in included:
        urn = item.get("entityUrn") or item.get("$id")
        if urn:
            entity_map[urn] = item

    messages = []
    for item in included:
        type_name = item.get("$type", "")
        if "Message" not in type_name and "Event" not in type_name:
            continue

        # Extract text
        body = item.get("body") or item.get("text")
        if isinstance(body, dict):
            body = body.get("text")
        attributed = item.get("attributedBody")
        if not body and isinstance(attributed, dict):
            body = attributed.get("text")

        if not body:
            continue

        # Sender — ref to MessagingParticipant entity
        sender_name = None
        sender_ref = item.get("*sender") or item.get("sender") or item.get("from")
        if isinstance(sender_ref, str) and sender_ref in entity_map:
            sender = entity_map[sender_ref]
            pt = sender.get("participantType") or {}
            member = pt.get("member") or {}
            first_obj = member.get("firstName") or {}
            last_obj = member.get("lastName") or {}
            first = first_obj.get("text", "") if isinstance(first_obj, dict) else str(first_obj)
            last = last_obj.get("text", "") if isinstance(last_obj, dict) else str(last_obj)
            sender_name = f"{first} {last}".strip() or None

        messages.append(LinkedInMessage(
            sender_name=sender_name,
            text=body,
            sent_at=item.get("deliveredAt") or item.get("createdAt"),
        ))

    return messages


# --- Notifications ---


def list_notifications(
    count: int = 20,
    account: str = "default",
) -> list[LinkedInNotification]:
    """List recent notifications.

    Uses the voyagerIdentityDashNotificationCards endpoint.
    """
    data = linkedin_get(
        "voyagerIdentityDashNotificationCards",
        account,
        params={
            "decorationId": "com.linkedin.voyager.dash.deco.identity.notifications.CardsCollectionWithInjectionsNoPills-24",
            "count": count,
            "q": "filterVanityName",
        },
    )

    notifications = []
    for item in data.get("included", []):
        type_name = item.get("$type", "")
        if not type_name.endswith("Card"):
            continue

        headline = item.get("headline") or {}
        text = headline.get("text") if isinstance(headline, dict) else str(headline) if headline else None

        notifications.append(LinkedInNotification(
            text=text,
            notification_type=item.get("notificationType") or item.get("cardType"),
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
    """Search LinkedIn using the GraphQL search endpoint."""
    kw = keywords
    if location:
        kw = f"{keywords} {location}"

    # Build graphql query string — includeFiltersInResponse goes inside query()
    encoded_kw = kw.replace(" ", "%20")
    query_params = f"keywords:{encoded_kw},flagshipSearchIntent:SEARCH_SRP,queryParameters:List((key:resultType,value:List({type_filter or 'PEOPLE'}))),includeFiltersInResponse:false"
    qs = f"includeWebMetadata=true&variables=(start:0,origin:GLOBAL_SEARCH_HEADER,query:({query_params}),count:{count})&queryId=voyagerSearchDashClusters.05111e1b90ee7fea15bebe9f9410ced9"

    try:
        data = linkedin_get("graphql", account, raw_qs=qs)
    except Exception:
        return []

    results = []
    for item in data.get("included", []):
        type_name = item.get("$type", "")

        if "EntityResult" in type_name:
            title = item.get("title") or {}
            title_text = title.get("text") if isinstance(title, dict) else str(title) if title else None

            subtitle = item.get("primarySubtitle") or {}
            subtitle_text = subtitle.get("text") if isinstance(subtitle, dict) else str(subtitle) if subtitle else None

            secondary = item.get("secondarySubtitle") or {}
            location_text = secondary.get("text") if isinstance(secondary, dict) else str(secondary) if secondary else None

            summary = item.get("summary") or {}
            summary_text = summary.get("text") if isinstance(summary, dict) else str(summary) if summary else None

            results.append(LinkedInSearchResult(
                name=title_text,
                headline=subtitle_text,
                description=summary_text,
                location=location_text,
                result_type=type_filter or "UNKNOWN",
                url=item.get("navigationUrl"),
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
    """Search for jobs on LinkedIn.

    Uses the voyagerJobsDashJobCards REST endpoint (separate from people/company search).
    """
    encoded_kw = keywords.replace(" ", "%20")
    location_part = ""
    if location:
        encoded_loc = location.replace(" ", "%20")
        location_part = f",locationUnion:(seoLocation:(location:{encoded_loc}))"

    qs = (
        f"decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-220"
        f"&count={count}&q=jobSearch"
        f"&query=(origin:JOB_SEARCH_PAGE_OTHER_ENTRY,keywords:{encoded_kw}{location_part},spellCorrectionEnabled:true)"
        f"&start=0"
    )

    try:
        data = linkedin_get("voyagerJobsDashJobCards", account, raw_qs=qs)
    except Exception:
        return []

    included = data.get("included", [])
    entity_map = {}
    for item in included:
        urn = item.get("entityUrn") or item.get("$id")
        if urn:
            entity_map[urn] = item

    results = []
    for item in included:
        if "JobPostingCard" not in item.get("$type", ""):
            continue

        title = item.get("title") or {}
        title_text = title.get("text", "").strip() if isinstance(title, dict) else None
        if not title_text:
            continue

        primary = item.get("primaryDescription") or {}
        company = primary.get("text") if isinstance(primary, dict) else None

        secondary = item.get("secondaryDescription") or {}
        location_text = secondary.get("text") if isinstance(secondary, dict) else None

        tertiary = item.get("tertiaryDescription") or {}
        extra = tertiary.get("text") if isinstance(tertiary, dict) else None

        # Build job URL from job posting reference
        url = None
        jp_ref = item.get("*jobPosting")
        if isinstance(jp_ref, str) and jp_ref in entity_map:
            jp = entity_map[jp_ref]
            jp_urn = jp.get("entityUrn", "")
            job_id = jp_urn.split(":")[-1] if jp_urn else None
            if job_id:
                url = f"https://www.linkedin.com/jobs/view/{job_id}/"

        results.append(LinkedInSearchResult(
            name=title_text,
            headline=company,
            description=extra,
            location=location_text,
            result_type="JOBS",
            url=url,
        ))

    return results
