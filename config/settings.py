import os

# ── Claude API ────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── X (Twitter) OAuth2 ───────────────────────────────────────
X_CLIENT_ID            = os.environ.get("X_CLIENT_ID", "")
X_CLIENT_SECRET        = os.environ.get("X_CLIENT_SECRET", "")
X_OAUTH2_ACCESS_TOKEN  = os.environ.get("X_OAUTH2_ACCESS_TOKEN", "")
X_OAUTH2_REFRESH_TOKEN = os.environ.get("X_OAUTH2_REFRESH_TOKEN", "")

# ── Medium ────────────────────────────────────────────────────
# Medium Integration Token は2025年1月以降新規発行停止
# GitHub Pages 経由でインポートURLを使用
MEDIUM_GITHUB_PAGES_BASE = "https://svqnmtn76r-lang.github.io/my-articles"

# ── Google Sheets ─────────────────────────────────────────────
GOOGLE_SHEETS_CREDS = os.environ.get("GOOGLE_SHEETS_CREDS", "")
SPREADSHEET_ID      = os.environ.get("SPREADSHEET_ID", "")

# ── Affiliate ─────────────────────────────────────────────────
NICHE_ROTATION_FILE = "/tmp/autoaffil_niche_state.json"
