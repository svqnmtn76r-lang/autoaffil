import os
import json
import time
import base64
import requests


def _get_access_token() -> str:
    """OAuth2リフレッシュトークンからアクセストークン取得"""
    client_id     = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")

    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError("YOUTUBE_CLIENT_ID / CLIENT_SECRET / REFRESH_TOKEN not set")

    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id":     client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type":    "refresh_token",
        },
        timeout=15,
    )
    if not resp.ok:
        raise RuntimeError(f"YouTube token refresh failed {resp.status_code}: {resp.text}")
    return resp.json()["access_token"]


def _upload_video(video_path: str, title: str, description: str,
                  tags: list, access_token: str) -> str:
    """YouTube Data API v3 でショート動画をアップロード"""
    metadata = {
        "snippet": {
            "title":       title[:100],
            "description": description,
            "tags":        tags[:15],
            "categoryId":  "22",  # People & Blogs
        },
        "status": {
            "privacyStatus":           "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    # resumable upload
    init_resp = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization":  f"Bearer {access_token}",
            "Content-Type":   "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
        },
        json=metadata,
        timeout=30,
    )
    if not init_resp.ok:
        raise RuntimeError(f"Upload init failed {init_resp.status_code}: {init_resp.text}")

    upload_url = init_resp.headers["Location"]

    with open(video_path, "rb") as f:
        video_data = f.read()

    upload_resp = requests.put(
        upload_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "video/mp4",
        },
        data=video_data,
        timeout=300,
    )
    if not upload_resp.ok:
        raise RuntimeError(f"Upload failed {upload_resp.status_code}: {upload_resp.text}")

    video_id = upload_resp.json()["id"]
    return f"https://www.youtube.com/shorts/{video_id}"


class YouTubePoster:
    def post(self, content: dict, fmt: str = "shorts") -> str:
        from utils.video_builder import build

        title       = content.get("title", "AutoAffil Video")
        description = content.get("description", content.get("description_intro", ""))
        hashtags    = content.get("hashtags", ["#Shorts"])
        tags        = [h.lstrip("#") for h in hashtags] + content.get("tags", [])

        # 動画生成
        name = f"youtube_{int(time.time())}"
        print(f"  🎬 Building video...")
        video_path = build("youtube", content, name)
        print(f"  ✅ Video built: {video_path}")

        # アップロード
        access_token = _get_access_token()
        print(f"  📤 Uploading to YouTube...")
        url = _upload_video(video_path, title, description, tags, access_token)
        print(f"  ✅ Uploaded: {url}")
        return url
