from fastapi import APIRouter

from brokenclaw.models.instagram import (
    InstagramComment,
    InstagramDirectThread,
    InstagramFollower,
    InstagramPost,
    InstagramProfile,
    InstagramReel,
    InstagramSavedPost,
    InstagramSearchResult,
    InstagramStory,
)
from brokenclaw.services import instagram as instagram_service

router = APIRouter(prefix="/api/instagram", tags=["instagram"])


@router.get("/profile")
def profile(account: str = "default") -> InstagramProfile:
    return instagram_service.get_my_profile(account)


@router.get("/profile/{username}")
def user_profile(username: str, account: str = "default") -> InstagramProfile:
    return instagram_service.get_user_profile(username, account)


@router.get("/feed")
def feed(count: int = 20, account: str = "default") -> list[InstagramPost]:
    return instagram_service.get_my_feed(count, account)


@router.get("/posts/{user_id}")
def user_posts(user_id: str, count: int = 20, account: str = "default") -> list[InstagramPost]:
    return instagram_service.get_user_posts(user_id, count, account)


@router.get("/posts/{post_id}/comments")
def post_comments(post_id: str, count: int = 20, account: str = "default") -> list[InstagramComment]:
    return instagram_service.get_post_comments(post_id, count, account)


@router.get("/stories")
def stories(account: str = "default") -> list[InstagramStory]:
    return instagram_service.get_my_stories(account)


@router.get("/stories/{user_id}")
def user_stories(user_id: str, account: str = "default") -> list[InstagramStory]:
    return instagram_service.get_user_stories(user_id, account)


@router.get("/reels/{user_id}")
def user_reels(user_id: str, count: int = 20, account: str = "default") -> list[InstagramReel]:
    return instagram_service.get_user_reels(user_id, count, account)


@router.get("/followers/{user_id}")
def followers(user_id: str, count: int = 20, account: str = "default") -> list[InstagramFollower]:
    return instagram_service.list_followers(user_id, count, account)


@router.get("/following/{user_id}")
def following(user_id: str, count: int = 20, account: str = "default") -> list[InstagramFollower]:
    return instagram_service.list_following(user_id, count, account)


@router.get("/saved")
def saved(count: int = 20, account: str = "default") -> list[InstagramSavedPost]:
    return instagram_service.get_saved_posts(count, account)


@router.get("/direct")
def direct(count: int = 20, account: str = "default") -> list[InstagramDirectThread]:
    return instagram_service.list_direct_threads(count, account)


@router.get("/search")
def search(query: str, count: int = 20, account: str = "default") -> list[InstagramSearchResult]:
    return instagram_service.search_users(query, count, account)


@router.get("/explore")
def explore(account: str = "default") -> list[InstagramPost]:
    return instagram_service.get_explore(account)
