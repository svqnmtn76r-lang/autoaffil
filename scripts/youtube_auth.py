#!/usr/bin/env python3
"""
YouTube OAuth2 ローカル認証スクリプト
YOUTUBE_REFRESH_TOKEN を取得して ~/.env に保存する

使い方: python3 scripts/youtube_auth.py
"""
import os
import re
import sys
import json
import webbrowser
import requests
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

ENV_PATH     = os.path.expanduser("~/.env")
PORT         = 8888
REDIRECT_URI = f"http://localhost:{PORT}/callback"
SCOPES       = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube"

received_code = None


def load_env():
    env = {}
    if not os.path.exists(ENV_PATH):
        return env
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def save_env_key(key, value):
    with open(ENV_PATH) as f:
        content = f.read()
    pattern = rf"^{re.escape(key)}=.*$"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, f"{key}={value}", content, flags=re.MULTILINE)
    else:
        content += f"\n{key}={value}"
    with open(ENV_PATH, "w") as f:
        f.write(content)


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global received_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        received_code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2 style='font-family:monospace;color:green'>OK! Return to terminal</h2>")

    def log_message(self, *args):
        pass


def main():
    env = load_env()
    client_id     = env.get("YOUTUBE_CLIENT_ID", "")
    client_secret = env.get("YOUTUBE_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET が ~/.env に未設定")
        sys.exit(1)

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={urllib.parse.quote(client_id)}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&response_type=code"
        f"&scope={urllib.parse.quote(SCOPES)}"
        f"&access_type=offline"
        f"&prompt=consent"
    )

    print(f"\n🌐 ブラウザを開いています...")
    print(f"   自動で開かない場合は以下のURLをコピー:\n\n{auth_url}\n")
    webbrowser.open(auth_url)

    print(f"⏳ 認証待ち (port {PORT})...")
    server = HTTPServer(("localhost", PORT), CallbackHandler)
    server.handle_request()

    if not received_code:
        print("❌ 認証コードが取得できませんでした")
        sys.exit(1)

    print(f"✅ 認証コード取得")
    print("🔄 トークン交換中...")

    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code":          received_code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "redirect_uri":  REDIRECT_URI,
            "grant_type":    "authorization_code",
        },
        timeout=15,
    )
    if not resp.ok:
        print(f"❌ トークン交換失敗: {resp.status_code} {resp.text}")
        sys.exit(1)

    data = resp.json()
    refresh_token = data.get("refresh_token", "")
    if not refresh_token:
        print(f"❌ refresh_token が含まれていません: {data}")
        sys.exit(1)

    save_env_key("YOUTUBE_REFRESH_TOKEN", refresh_token)
    print(f"✅ YOUTUBE_REFRESH_TOKEN を ~/.env に保存しました")

    # GitHub Secrets にも追加
    gh_token = env.get("GITHUB_TOKEN", "")
    if gh_token:
        try:
            sys.path.insert(0, os.path.expanduser("~/my-articles/scripts"))
            from sync_secrets import gh_request, encrypt_secret
            for repo in ["autoaffil"]:
                pk = gh_request("GET", f"/repos/svqnmtn76r-lang/{repo}/actions/secrets/public-key", gh_token)
                encrypted = encrypt_secret(pk["key"], refresh_token)
                gh_request("PUT", f"/repos/svqnmtn76r-lang/{repo}/actions/secrets/YOUTUBE_REFRESH_TOKEN",
                           gh_token, {"encrypted_value": encrypted, "key_id": pk["key_id"]})
                print(f"✅ GitHub Secrets ({repo}/YOUTUBE_REFRESH_TOKEN) 更新完了")
        except Exception as e:
            print(f"⚠️  GitHub Secrets更新失敗: {e}")
            print("   手動で: python3 ~/my-articles/scripts/sync_secrets.py --force")

    print("\n🎉 YouTube認証完了！\n")


if __name__ == "__main__":
    main()
