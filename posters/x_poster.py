import os
import time
import base64
import requests


def _write_token_file(name: str, value: str) -> None:
    """リフレッシュ後のトークンをファイルに書き出す（gh CLIでSecrets更新用）"""
    try:
        from pathlib import Path
        Path(f"/tmp/autoaffil_{name}").write_text(value)
    except Exception:
        pass


def _refresh_access_token() -> str:
    refresh_token = os.environ.get("X_OAUTH2_REFRESH_TOKEN", "")
    client_id     = os.environ.get("X_CLIENT_ID", "")
    client_secret = os.environ.get("X_CLIENT_SECRET", "")
    if not refresh_token or not client_id:
        raise RuntimeError("X OAuth2 refresh credentials not set")

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data    = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    if client_secret:
        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"
    else:
        data["client_id"] = client_id

    r = requests.post("https://api.x.com/2/oauth2/token", headers=headers, data=data, timeout=15)
    if not r.ok:
        raise RuntimeError(f"Token refresh failed {r.status_code}: {r.text}")

    new_access  = r.json().get("access_token", "")
    new_refresh = r.json().get("refresh_token", "")
    if not new_access:
        raise RuntimeError(f"No access_token in refresh response: {r.text}")

    os.environ["X_OAUTH2_ACCESS_TOKEN"] = new_access
    if new_refresh:
        os.environ["X_OAUTH2_REFRESH_TOKEN"] = new_refresh
        _write_token_file("X_OAUTH2_REFRESH_TOKEN", new_refresh)
        _write_token_file("X_OAUTH2_ACCESS_TOKEN", new_access)

    print("  ✓ X OAuth2 token refreshed")
    return new_access


def _get_access_token() -> str:
    token = os.environ.get("X_OAUTH2_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("X_OAUTH2_ACCESS_TOKEN is not set")
    return token


def _post_tweet(text: str, reply_to_id: str = None) -> str:
    url     = "https://api.twitter.com/2/tweets"
    payload = {"text": text}
    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

    for attempt in range(2):
        token = _get_access_token()
        resp  = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if resp.status_code == 401 and attempt == 0:
            print("  ↩ Access token expired, refreshing...")
            _refresh_access_token()
            continue
        if not resp.ok:
            raise RuntimeError(f"Tweet failed {resp.status_code}: {resp.text}")
        break

    data = resp.json()
    if "data" in data and "id" in data["data"]:
        return data["data"]["id"]
    raise RuntimeError(f"Unexpected response: {data}")


class XPoster:
    def post(self, content: dict) -> str:
        main_post        = content.get("main_post", "")
        link_reply       = content.get("link_reply", "")
        engagement_reply = content.get("engagement_reply", "")

        if not main_post:
            raise ValueError("main_post is empty")

        print(f"  📤 Posting main tweet...")
        tweet_id = _post_tweet(main_post)
        print(f"  ✅ Main tweet posted: {tweet_id}")

        if link_reply:
            time.sleep(2)
            print(f"  📤 Posting link reply...")
            try:
                reply_id = _post_tweet(link_reply, reply_to_id=tweet_id)
                print(f"  ✅ Link reply posted: {reply_id}")
            except Exception as e:
                print(f"  ⚠️  Link reply skipped: {e}")

        if engagement_reply:
            time.sleep(2)
            print(f"  📤 Posting engagement reply...")
            try:
                _post_tweet(engagement_reply, reply_to_id=tweet_id)
                print(f"  ✅ Engagement reply posted")
            except Exception as e:
                print(f"  ⚠️  Engagement reply skipped: {e}")

        return f"https://x.com/i/web/status/{tweet_id}"
