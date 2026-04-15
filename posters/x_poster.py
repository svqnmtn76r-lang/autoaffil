import os
import json
import time
import hmac
import hashlib
import base64
import urllib.request
import urllib.error
import urllib.parse
import secrets
from datetime import datetime, timezone


def _oauth1_header(method: str, url: str, params: dict = None) -> str:
    """OAuth1 Authorization ヘッダーを生成"""
    consumer_key    = os.environ.get("X_CONSUMER_KEY", "")
    consumer_secret = os.environ.get("X_CONSUMER_SECRET", "")
    access_token    = os.environ.get("X_ACCESS_TOKEN", "")
    token_secret    = os.environ.get("X_ACCESS_TOKEN_SECRET", "")

    if not all([consumer_key, consumer_secret, access_token, token_secret]):
        raise RuntimeError("X OAuth1 credentials not set (X_CONSUMER_KEY/SECRET, X_ACCESS_TOKEN/SECRET)")

    oauth_params = {
        "oauth_consumer_key":     consumer_key,
        "oauth_nonce":            secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        str(int(datetime.now(timezone.utc).timestamp())),
        "oauth_token":            access_token,
        "oauth_version":          "1.0",
    }

    # シグネチャ生成
    all_params = {**(params or {}), **oauth_params}
    sorted_params = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
        for k, v in sorted(all_params.items())
    )
    base_string = "&".join([
        method.upper(),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(sorted_params, safe=""),
    ])
    signing_key = f"{urllib.parse.quote(consumer_secret, safe='')}&{urllib.parse.quote(token_secret, safe='')}"
    signature   = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()
    oauth_params["oauth_signature"] = signature

    header = "OAuth " + ", ".join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(oauth_params.items())
    )
    return header


def _post_tweet(text: str, reply_to_id: str = None) -> str:
    url     = "https://api.twitter.com/2/tweets"
    payload = {"text": text}
    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

    body   = json.dumps(payload).encode()
    header = _oauth1_header("POST", url)

    req = urllib.request.Request(
        url, data=body,
        headers={"Authorization": header, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
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
