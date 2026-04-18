import os
import re
import asyncio
import subprocess
import requests
from pathlib import Path

OUT_DIR = Path("/tmp/autoaffil_videos")

SPECS = {
    "tiktok":    {"w": 1080, "h": 1920, "fps": 30, "max_sec": 35},
    "youtube":   {"w": 1080, "h": 1920, "fps": 30, "max_sec": 60},
    "instagram": {"w": 1080, "h": 1920, "fps": 30, "max_sec": 60},
}

TTS_VOICE = "en-US-GuyNeural"


# ── ① edge-tts (無料) ────────────────────────────────────────────────────────

async def _tts_async(text: str, path: str) -> None:
    import edge_tts
    await edge_tts.Communicate(text, TTS_VOICE).save(path)


def _generate_tts(text: str, name: str) -> str:
    path = str(OUT_DIR / f"{name}_audio.mp3")
    asyncio.run(_tts_async(text, path))
    return path


# ── 背景画像 (Pollinations 無料) ──────────────────────────────────────────────

def _generate_image(prompt: str, name: str, w: int, h: int) -> str:
    encoded = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={w}&height={h}&nologo=true"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    path = OUT_DIR / f"{name}_bg.jpg"
    path.write_bytes(r.content)
    return str(path)


# ── ③ 字幕タイミングパーサ ────────────────────────────────────────────────────

def _parse_time(t_str: str) -> tuple[int, int]:
    m = re.search(r'(\d+)\D+(\d+)', t_str)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 5)


def _drawtext(text: str, start: int, end: int) -> str:
    safe = re.sub(r"['\\\[\]{}|<>]", "", text)[:55]
    safe = safe.replace(":", "\\:")
    return (
        f"drawtext=text='{safe}'"
        f":fontsize=62:fontcolor=white"
        f":x=(w-text_w)/2:y=h*0.82"
        f":shadowcolor=black:shadowx=3:shadowy=3"
        f":box=1:boxcolor=black@0.55:boxborderw=14"
        f":enable='between(t\\,{start}\\,{end})'"
    )


# ── ② Ken Burns + ③ 字幕 合成 ────────────────────────────────────────────────

def _compose_video(img: str, audio: str, script: list, spec: dict, name: str) -> str:
    out_path = str(OUT_DIR / f"{name}.mp4")
    w, h, fps = spec["w"], spec["h"], spec["fps"]

    # ② Ken Burns: 1.0→1.3x ゆっくりズームイン
    ken_burns = (
        f"zoompan=z='min(zoom+0.0003\\,1.3)':d=1"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":s={w}x{h}:fps={fps},setsar=1"
    )

    # ③ タイミング付き字幕フィルター
    caption_filters = [
        _drawtext(seg["text_overlay"], *_parse_time(seg.get("time", "0-5s")))
        for seg in script
        if seg.get("text_overlay")
    ]

    ffmpeg_bin = next(
        (p for p in ["/usr/local/opt/ffmpeg-full/bin/ffmpeg", "ffmpeg"]
         if subprocess.run([p, "-version"], capture_output=True).returncode == 0
         and b"drawtext" in subprocess.run([p, "-filters"], capture_output=True).stdout),
        "ffmpeg"
    )

    def _run(vf: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [ffmpeg_bin, "-y", "-loop", "1", "-i", img, "-i", audio,
             "-vf", vf, "-c:v", "libx264", "-c:a", "aac",
             "-shortest", "-r", str(fps), out_path],
            capture_output=True, text=True,
        )

    def _no_drawtext(stderr: str) -> bool:
        return "drawtext" in stderr or ("No such filter" in stderr)

    # フル品質で試行（Ken Burns + 字幕）
    vf_full = ",".join([ken_burns] + caption_filters)
    result = _run(vf_full)

    if result.returncode != 0:
        stderr = result.stderr
        no_zoom = "zoompan" in stderr
        no_text = _no_drawtext(stderr)
        base = f"scale={w}:{h},setsar=1" if no_zoom else ken_burns
        parts = [base] if no_text else [base] + caption_filters
        result = _run(",".join(parts))

    # 最終フォールバック
    if result.returncode != 0:
        result = _run(f"scale={w}:{h},setsar=1")

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-500:]}")

    return out_path


# ── エントリポイント ──────────────────────────────────────────────────────────

def build(platform: str, content: dict, name: str) -> str:
    OUT_DIR.mkdir(exist_ok=True)
    spec = SPECS[platform]

    audio = _generate_tts(content.get("tts_narration", ""), name)
    image = _generate_image(
        content.get("bg_image_prompt", "minimalist dark abstract background"),
        name, spec["w"], spec["h"],
    )
    return _compose_video(image, audio, content.get("script", []), spec, name)
