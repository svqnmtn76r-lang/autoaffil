#!/usr/bin/env python3
"""
AutoAffil 毎朝エラーチェック & 自動修復スクリプト
- 各プラットフォームの直近ワークフロー実行結果を確認
- 失敗またはスキップされていた場合は再トリガー
- X トークン期限チェック & 事前リフレッシュ
- 結果を Google Sheets に記録
"""
import os
import sys
import json
import time
import base64
import datetime
import requests

REPO_OWNER = "svqnmtn76r-lang"
REPO_NAME  = "autoaffil"

WORKFLOWS = [
    {"name": "X",         "file": "post_x.yml"},
    {"name": "Medium",    "file": "post_medium.yml"},
    {"name": "YouTube",   "file": "post_youtube.yml"},
    {"name": "Instagram", "file": "post_instagram.yml"},
    {"name": "TikTok",   "file": "post_tiktok.yml"},
]

GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def gh_get(path: str) -> dict:
    r = requests.get(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def gh_post(path: str, data: dict = None):
    r = requests.post(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        json=data or {},
        timeout=30,
    )
    return r.status_code


def get_last_run(workflow_file: str) -> dict | None:
    """ワークフローの直近実行結果を取得"""
    data = gh_get(f"/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow_file}/runs?per_page=1")
    runs = data.get("workflow_runs", [])
    return runs[0] if runs else None


def trigger_workflow(workflow_file: str) -> bool:
    """ワークフローを手動トリガー"""
    status = gh_post(
        f"/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow_file}/dispatches",
        {"ref": "main"},
    )
    return status == 204


def check_x_token() -> bool:
    """X アクセストークンの有効性を確認"""
    token = os.environ.get("X_OAUTH2_ACCESS_TOKEN", "")
    if not token:
        return False
    r = requests.get(
        "https://api.twitter.com/2/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    return r.status_code == 200


def refresh_x_token() -> bool:
    """X トークンをリフレッシュして GitHub Secrets に保存"""
    refresh_token = os.environ.get("X_OAUTH2_REFRESH_TOKEN", "")
    client_id     = os.environ.get("X_CLIENT_ID", "")
    client_secret = os.environ.get("X_CLIENT_SECRET", "")
    if not refresh_token or not client_id:
        return False

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data    = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    if client_secret:
        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"
    else:
        data["client_id"] = client_id

    r = requests.post("https://api.x.com/2/oauth2/token", headers=headers, data=data, timeout=15)
    if not r.ok:
        print(f"  ❌ X トークンリフレッシュ失敗: {r.text}")
        return False

    new_access  = r.json().get("access_token", "")
    new_refresh = r.json().get("refresh_token", "")
    if not new_access:
        return False

    # GitHub Secrets に保存
    _update_secret("X_OAUTH2_ACCESS_TOKEN",  new_access)
    if new_refresh:
        _update_secret("X_OAUTH2_REFRESH_TOKEN", new_refresh)

    print("  ✅ X トークンリフレッシュ完了・Secrets 更新済み")
    return True


def _update_secret(name: str, value: str):
    """GitHub Secrets を更新"""
    try:
        from nacl import public as nacl_public
    except ImportError:
        return

    pk_data = gh_get(f"/repos/{REPO_OWNER}/{REPO_NAME}/actions/secrets/public-key")
    pk      = nacl_public.PublicKey(base64.b64decode(pk_data["key"]))
    encrypted = base64.b64encode(nacl_public.SealedBox(pk).encrypt(value.encode())).decode()
    requests.put(
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/secrets/{name}",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        json={"encrypted_value": encrypted, "key_id": pk_data["key_id"]},
        timeout=30,
    )


def log_to_sheets(rows: list):
    """Google Sheets にヘルスチェック結果を記録"""
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDS", "")
    sid        = os.environ.get("SPREADSHEET_ID", "")
    if not creds_json or not sid:
        return
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        creds = Credentials.from_service_account_info(
            json.loads(creds_json),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        svc = build("sheets", "v4", credentials=creds)
        svc.spreadsheets().values().append(
            spreadsheetId=sid,
            range="HealthCheck_Log!A:E",
            valueInputOption="USER_ENTERED",
            body={"values": rows},
        ).execute()
    except Exception as e:
        print(f"  ⚠️  Sheets 記録失敗: {e}")


def main():
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"\n{'='*60}")
    print(f"[AutoAffil HealthCheck] {ts}")
    print(f"{'='*60}\n")

    if not GH_TOKEN:
        print("❌ GITHUB_TOKEN が未設定")
        sys.exit(1)

    # ── X トークンチェック ────────────────────────────────────────
    print("🔍 X トークン確認中...")
    if not check_x_token():
        print("  ⚠️  X トークン無効 → リフレッシュ試行")
        refresh_x_token()
    else:
        print("  ✅ X トークン有効")

    # ── 各ワークフローチェック ────────────────────────────────────
    print("\n🔍 ワークフロー実行状況確認中...")
    log_rows = []
    retrigger_count = 0

    for wf in WORKFLOWS:
        run = get_last_run(wf["file"])
        if run is None:
            status = "NO_RUNS"
            action = "SKIP"
            print(f"  [{wf['name']:10}] 実行履歴なし")
        else:
            conclusion = run.get("conclusion") or run.get("status", "unknown")
            created_at = run.get("created_at", "")[:19]
            status = conclusion.upper()

            if conclusion in ("failure", "cancelled", "timed_out"):
                print(f"  [{wf['name']:10}] ❌ {conclusion} ({created_at}) → 再トリガー")
                ok = trigger_workflow(wf["file"])
                action = "RETRIGGERED" if ok else "RETRIGGER_FAILED"
                retrigger_count += 1
                time.sleep(3)  # レート制限回避
            elif conclusion == "success":
                print(f"  [{wf['name']:10}] ✅ success ({created_at})")
                action = "OK"
            else:
                print(f"  [{wf['name']:10}] ⚠️  {conclusion} ({created_at})")
                action = "SKIP"

        log_rows.append([ts, wf["name"], status, action, ""])

    # ── Sheets 記録 ──────────────────────────────────────────────
    log_to_sheets(log_rows)

    print(f"\n✅ ヘルスチェック完了 (再トリガー: {retrigger_count}件)\n")


if __name__ == "__main__":
    main()
