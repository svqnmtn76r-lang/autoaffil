import os
import json
import base64
import time
import urllib.request
import urllib.error


def _refresh_token() -> str:
    client_id     = os.environ.get("X_CLIENT_ID", "")
    client_secret = os.environ.get("X_CLIENT_SECRET", "")
    refresh_token = os.environ.get("X_OAUTH2_REFRESH_TOKEN", "")
    if not refresh_token or not client_id:
        raise RuntimeError("X OAuth2 credentials not set")

    body = f"grant_type=refresh_token&refresh_token={refresh_token}"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if client_secret:
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
    else:
        body += f"&client_id={client_id}"

    req = urllib.request.Request(
        "https://api.x.com/2/oauth2/token",
        data=body.encode(), headers=headers, method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    if "access_token" not in data:
        raise RuntimeError(f"Token refresh failed: {data}")
    os.environ["X_OAUTH2_ACCESS_TOKEN"] = data["access_token"]
    if "refresh_token" in data:
        os.environ["X_OAUTH2_REFRESH_TOKEN"] = data["refresh_token"]
    return data["access_token"]


def _post_tweet(text: str, reply_to_id: str = None) -> str:
    token = os.environ.get("X_OAUTH2_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("X_OAUTH2_ACCESS_TOKEN not set")

    payload = {"text": text}
    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.twitter.com/2/tweets",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            new_token = _refresh_token()
            req.headers["Authorization"] = f"Bearer {new_token}"
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
        else:
            raise RuntimeError(f"Tweet failed {e.code}: {e.read().decode()}")

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
            reply_id = _post_tweet(link_reply, reply_to_id=tweet_id)
            print(f"  ✅ Link reply posted: {reply_id}")

        if engagement_reply:
            time.sleep(2)
            print(f"  📤 Posting engagement reply...")
            _post_tweet(engagement_reply, reply_to_id=tweet_id)
            print(f"  ✅ Engagement reply posted")

        return f"https://x.com/i/web/status/{tweet_id}"
