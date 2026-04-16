import re
import json
import os
import time
import base64
import requests
from datetime import datetime, timezone


def _markdown_to_html(md: str) -> str:
    """シンプルなMarkdown → HTML変換"""
    def inline(text):
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*',     r'<em>\1</em>', text)
        text = re.sub(r'`(.+?)`',       r'<code>\1</code>', text)
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
        return text

    result = []
    list_type = ''

    def close_list():
        nonlocal list_type
        if list_type:
            result.append(f'</{list_type}>')
            list_type = ''

    for line in md.split('\n'):
        t = line.strip()
        if not t:
            close_list()
            continue
        if t.startswith('### '):
            close_list()
            result.append(f'<h3>{inline(t[4:])}</h3>')
        elif t.startswith('## '):
            close_list()
            result.append(f'<h2>{inline(t[3:])}</h2>')
        elif t.startswith('# '):
            close_list()
            result.append(f'<h1>{inline(t[2:])}</h1>')
        elif re.match(r'^[-*] ', t):
            if list_type != 'ul':
                close_list()
                result.append('<ul>')
                list_type = 'ul'
            result.append(f'<li>{inline(t[2:])}</li>')
        elif re.match(r'^\d+\. ', t):
            if list_type != 'ol':
                close_list()
                result.append('<ol>')
                list_type = 'ol'
            cleaned = re.sub(r'^\d+\. ', '', t)
            result.append(f'<li>{inline(cleaned)}</li>')
        else:
            close_list()
            result.append(f'<p>{inline(t)}</p>')

    close_list()
    return '\n'.join(result)


def _build_html(content: dict) -> str:
    title    = content.get("title", "Untitled")
    subtitle = content.get("subtitle", "")
    body_md  = content.get("body_markdown", "")
    product  = content.get("product", {})

    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:60]
    filename = f"{slug}-{int(time.time())}.html"

    body_html = _markdown_to_html(body_md)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body{{font-family:Georgia,serif;max-width:740px;margin:40px auto;padding:0 20px;line-height:1.7;color:#292929}}
  h1{{font-size:2rem;margin-bottom:4px}}
  h2{{font-size:1.4rem;margin-top:2rem}}
  h3{{font-size:1.2rem;margin-top:1.5rem}}
  p{{margin:.8rem 0}}
  ul,ol{{padding-left:1.5rem}}
  li{{margin-bottom:.4rem}}
  a{{color:#1a8917}}
  em{{font-style:italic}}
  .subtitle{{font-size:1.2rem;color:#6b6b6b;margin-bottom:1.5rem}}
</style>
</head>
<body>
<h1>{title}</h1>
{f'<p class="subtitle">{subtitle}</p>' if subtitle else ''}
{body_html}
</body>
</html>"""
    return html, filename


class MediumPoster:
    """
    Medium Integration Token は2025年1月以降新規発行停止。
    GitHub Pages (my-articles) に HTML をプッシュして
    Medium の "Import a story" URL でインポートする方式。
    """

    REPO_OWNER   = "svqnmtn76r-lang"
    REPO_NAME    = "my-articles"
    PAGES_BASE   = "https://svqnmtn76r-lang.github.io/my-articles"

    def post(self, content: dict) -> str:
        html, filename = _build_html(content)
        gh_token = os.environ.get("GITHUB_TOKEN", "")
        if not gh_token:
            raise RuntimeError("GITHUB_TOKEN not set")

        # GitHub Contents API でファイルをプッシュ
        path = f"https://api.github.com/repos/{self.REPO_OWNER}/{self.REPO_NAME}/contents/{filename}"
        resp = requests.put(
            path,
            headers={
                "Authorization": f"token {gh_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "message": f"Add affiliate article: {content.get('title','')}",
                "content": base64.b64encode(html.encode()).decode(),
            },
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"GitHub push failed {resp.status_code}: {resp.text}")

        article_url = f"{self.PAGES_BASE}/{filename}"
        print(f"  ✅ Article published: {article_url}")
        print(f"  📋 Import to Medium: https://medium.com/p/import?url={article_url}")
        return article_url
