import os
import time
import requests
from utils.video_builder import build


def _refresh_token() -> str:
    """TikTok アクセストークンをリフレッシュ"""
    client_key    = os.environ.get("TIKTOK_CLIENT_KEY", "")
    client_secret = os.environ.get("TIKTOK_CLIENT_SECRET", "")
    refresh_token = os.environ.get("TIKTOK_REFRESH_TOKEN", "")

    if not all([client_key, client_secret, refresh_token]):
        raise RuntimeError("TIKTOK_CLIENT_KEY / CLIENT_SECRET / REFRESH_TOKEN not set")

    resp = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key":    client_key,
            "client_secret": client_secret,
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=15,
    )
    if not resp.ok:
        raise RuntimeError(f"TikTok token refresh failed {resp.status_code}: {resp.text}")
    return resp.json()["data"]["access_token"]


def _upload_video(video_path: str, caption: str, hashtags: list, access_token: str) -> str:
    """TikTok Content Posting API でショート動画を投稿"""
    tags_str = " ".join(hashtags[:5])
    full_caption = f"{caption} {tags_str}"[:2200]

    # Step 1: initialize upload
    init_resp = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json; charset=UTF-8",
        },
        json={
            "post_info": {
                "title":            full_caption,
                "privacy_level":    "PUBLIC_TO_EVERYONE",
                "disable_duet":     False,
                "disable_comment":  False,
                "disable_stitch":   False,
            },
            "source_info": {
                "source":       "FILE_UPLOAD",
                "video_size":   os.path.getsize(video_path),
                "chunk_size":   os.path.getsize(video_path),
                "total_chunk_count": 1,
            },
        },
        timeout=30,
    )
    if not init_resp.ok:
        raise RuntimeError(f"TikTok init failed {init_resp.status_code}: {init_resp.text}")

    data       = init_resp.json()["data"]
    publish_id = data["publish_id"]
    upload_url = data["upload_url"]

    # Step 2: upload video file
    with open(video_path, "rb") as f:
        video_data = f.read()

    upload_resp = requests.put(
        upload_url,
        headers={
            "Content-Type":            "video/mp4",
            "Content-Range":           f"bytes 0-{len(video_data)-1}/{len(video_data)}",
            "Content-Length":          str(len(video_data)),
        },
        data=video_data,
        timeout=120,
    )
    if upload_resp.status_code not in (200, 201, 206):
        raise RuntimeError(f"TikTok upload failed {upload_resp.status_code}: {upload_resp.text}")

    return f"https://www.tiktok.com/ (publish_id: {publish_id})"


class TikTokPoster:
    def post(self, content: dict) -> str:
        caption  = content.get("caption", "")
        hashtags = content.get("hashtags", [])

        name = f"tiktok_{int(time.time())}"
        print(f"  🎬 Building TikTok video...")
        video_path = build("tiktok", content, name)
        print(f"  ✅ Video built: {video_path}")

        access_token = _refresh_token()
        print(f"  📤 Uploading to TikTok...")
        result = _upload_video(video_path, caption, hashtags, access_token)
        print(f"  ✅ Uploaded: {result}")
        return result
