import os
import subprocess
import requests
from pathlib import Path

OUT_DIR = Path("/tmp/autoaffil_videos")

SPECS = {
    "tiktok":    {"w": 1080, "h": 1920, "fps": 30, "max_sec": 35},
    "youtube":   {"w": 1080, "h": 1920, "fps": 30, "max_sec": 60},
    "instagram": {"w": 1080, "h": 1920, "fps": 30, "max_sec": 60},
}


def _generate_tts(text: str, name: str) -> str:
    """OpenAI TTS でナレーション音声を生成"""
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    path = OUT_DIR / f"{name}_audio.mp3"
    response = client.audio.speech.create(model="tts-1", voice="nova", input=text)
    response.stream_to_file(str(path))
    return str(path)


def _generate_image(prompt: str, name: str, w: int, h: int) -> str:
    """Pollinations AI（無料）で背景画像を生成"""
    encoded = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={w}&height={h}&nologo=true"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    path = OUT_DIR / f"{name}_bg.jpg"
    path.write_bytes(r.content)
    return str(path)


def _compose_video(img: str, audio: str, overlay: str, spec: dict, name: str) -> str:
    """FFmpeg で画像 + 音声 + テキストオーバーレイを合成"""
    out_path = OUT_DIR / f"{name}.mp4"
    safe = overlay.replace("'", "\\'").replace(":", "\\:")[:80]
    drawtext = (
        f"drawtext=text='{safe}':fontsize=56:fontcolor=white:"
        f"x=(w-text_w)/2:y=120:shadowcolor=black:shadowx=3:shadowy=3"
    )

    def _run(vf: str) -> subprocess.CompletedProcess:
        return subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", img,
            "-i", audio,
            "-vf", vf,
            "-c:v", "libx264", "-c:a", "aac",
            "-shortest", "-r", str(spec["fps"]),
            str(out_path),
        ], capture_output=True, text=True)

    result = _run(f"scale={spec['w']}:{spec['h']},setsar=1,{drawtext}")
    if result.returncode != 0 and "No such filter" in result.stderr:
        # drawtext unavailable (e.g. macOS system FFmpeg) — retry without overlay
        result = _run(f"scale={spec['w']}:{spec['h']},setsar=1")
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-500:]}")
    return str(out_path)


def build(platform: str, content: dict, name: str) -> str:
    """動画を生成して保存パスを返す"""
    OUT_DIR.mkdir(exist_ok=True)
    spec = SPECS[platform]

    narration = content.get("tts_narration", "")
    bg_prompt  = content.get("bg_image_prompt", "minimalist dark background")
    script     = content.get("script", [{}])
    overlay    = script[0].get("text_overlay", "") if script else ""

    audio = _generate_tts(narration, name)
    image = _generate_image(bg_prompt, name, spec["w"], spec["h"])
    return _compose_video(image, audio, overlay, spec, name)
