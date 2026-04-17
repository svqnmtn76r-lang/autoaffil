import os
import json
import time
import urllib.request
import urllib.error

GRAPH_API = "https://graph.facebook.com/v25.0"


def _get_image_url(prompt: str, w: int = 1080, h: int = 1350) -> str:
    """Pollinations AI で画像URLを生成（無料）"""
    encoded = urllib.request.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width={w}&height={h}&nologo=true"


def _graph(method: str, path: str, params: dict) -> dict:
    token = params.get("access_token", "")
    url   = f"{GRAPH_API}/{path}"

    if method == "GET":
        query = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
        req = urllib.request.Request(f"{url}?{query}")
    else:
        body = json.dumps(params).encode()
        req  = urllib.request.Request(url, data=body,
               headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Graph API {e.code}: {e.read().decode()}")


class InstagramPoster:
    def __init__(self):
        self.ig_id       = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
        self.page_token  = (os.environ.get("INSTAGRAM_PAGE_ACCESS_TOKEN")
                            or os.environ.get("FB_PAGE_ACCESS_TOKEN", ""))
        if not self.ig_id or not self.page_token:
            raise RuntimeError("INSTAGRAM_ACCOUNT_ID または INSTAGRAM_PAGE_ACCESS_TOKEN が未設定")

    def post(self, content: dict) -> str:
        caption      = content.get("caption", "")
        hashtags     = " ".join(content.get("hashtags", []))
        image_prompt = content.get("image_prompt", "")

        full_caption = f"{caption}\n\n{hashtags}".strip()
        image_url    = _get_image_url(image_prompt) if image_prompt else ""

        if not image_url:
            raise ValueError("image_url が生成できませんでした")

        print(f"  🖼️  画像生成中: {image_url[:80]}...")

        # Step 1: メディアコンテナ作成
        resp = _graph("POST", f"{self.ig_id}/media", {
            "image_url":    image_url,
            "caption":      full_caption[:2200],
            "access_token": self.page_token,
        })
        if "id" not in resp:
            raise RuntimeError(f"コンテナ作成失敗: {resp}")

        container_id = resp["id"]
        print(f"  📦 コンテナ作成: {container_id}")

        # Step 2: メディア処理完了を待機
        for attempt in range(10):
            time.sleep(6)
            status = _graph("GET", container_id, {
                "fields":       "status_code",
                "access_token": self.page_token,
            })
            code = status.get("status_code", "")
            print(f"  ⏳ ステータス: {code} (試行 {attempt+1}/10)")
            if code == "FINISHED":
                break
            if code == "ERROR":
                raise RuntimeError(f"メディア処理エラー: {status}")
        else:
            raise RuntimeError("メディア処理タイムアウト")

        # Step 3: 公開
        resp2 = _graph("POST", f"{self.ig_id}/media_publish", {
            "creation_id":  container_id,
            "access_token": self.page_token,
        })
        if "id" not in resp2:
            raise RuntimeError(f"公開失敗: {resp2}")

        post_id = resp2["id"]
        print(f"  ✅ Instagram投稿完了: {post_id}")
        return f"https://www.instagram.com/p/{post_id}/"
