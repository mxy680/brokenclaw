from pydantic import BaseModel


class LinkedInProfile(BaseModel):
    entity_urn: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    profile_url: str | None = None
    profile_pic_url: str | None = None
    connections_count: int | None = None


class LinkedInExperience(BaseModel):
    title: str | None = None
    company_name: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class LinkedInEducation(BaseModel):
    school_name: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_year: int | None = None
    end_year: int | None = None


class LinkedInSkill(BaseModel):
    name: str | None = None
    endorsement_count: int | None = None


class LinkedInFullProfile(BaseModel):
    profile: LinkedInProfile
    experience: list[LinkedInExperience] = []
    education: list[LinkedInEducation] = []
    skills: list[LinkedInSkill] = []


class LinkedInPost(BaseModel):
    author_name: str | None = None
    text: str | None = None
    created_at: int | None = None
    num_likes: int | None = None
    num_comments: int | None = None
    url: str | None = None
    image_url: str | None = None


class LinkedInConnection(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    headline: str | None = None
    profile_url: str | None = None
    profile_pic_url: str | None = None
    connected_at: int | None = None


class LinkedInConversation(BaseModel):
    conversation_urn: str | None = None
    participants: list[str] = []
    last_message_text: str | None = None
    last_activity_at: int | None = None
    unread: bool | None = None


class LinkedInMessageAttachment(BaseModel):
    name: str | None = None
    media_type: str | None = None
    url: str | None = None


class LinkedInMessage(BaseModel):
    sender_name: str | None = None
    text: str | None = None
    sent_at: int | None = None
    attachments: list[LinkedInMessageAttachment] = []


class LinkedInNotification(BaseModel):
    text: str | None = None
    notification_type: str | None = None
    created_at: int | None = None
    url: str | None = None


class LinkedInSearchResult(BaseModel):
    name: str | None = None
    headline: str | None = None
    description: str | None = None
    location: str | None = None
    result_type: str | None = None
    url: str | None = None
    image_url: str | None = None
