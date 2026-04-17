import os
import time
import hmac
import hashlib
import base64
import urllib.parse
import secrets
import requests


def _oauth1_header(method: str, url: str, extra_params: dict = None) -> str:
    consumer_key    = os.environ["X_CONSUMER_KEY"]
    consumer_secret = os.environ["X_CONSUMER_SECRET"]
    access_token    = os.environ["X_ACCESS_TOKEN"]
    token_secret    = os.environ["X_ACCESS_TOKEN_SECRET"]

    params = {
        "oauth_consumer_key":     consumer_key,
        "oauth_nonce":            secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        str(int(time.time())),
        "oauth_token":            access_token,
        "oauth_version":          "1.0",
    }
    if extra_params:
        params.update(extra_params)

    sorted_params = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
        for k, v in sorted(params.items())
    )
    base = "&".join([
        method.upper(),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(sorted_params, safe=""),
    ])
    signing_key = f"{urllib.parse.quote(consumer_secret, safe='')}&{urllib.parse.quote(token_secret, safe='')}"
    sig = base64.b64encode(
        hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()
    ).decode()
    params["oauth_signature"] = sig

    return "OAuth " + ", ".join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(params.items())
        if k.startswith("oauth_")
    )


def _post_tweet(text: str, reply_to_id: str = None) -> str:
    url     = "https://api.twitter.com/2/tweets"
    payload = {"text": text}
    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

    auth_header = _oauth1_header("POST", url)
    resp = requests.post(
        url,
        headers={"Authorization": auth_header, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Tweet failed {resp.status_code}: {resp.text}")

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
