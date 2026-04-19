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


# ── ① edge-tts ───────────────────────────────────────────────────────────────

async def _tts_async(text: str, path: str) -> None:
    import edge_tts
    await edge_tts.Communicate(text, TTS_VOICE).save(path)


def _generate_tts(text: str, name: str) -> str:
    path = str(OUT_DIR / f"{name}_audio.mp3")
    asyncio.run(_tts_async(text, path))
    return path


# ── ④ 背景画像 (Pollinations, セグメント別並列生成) ───────────────────────────

def _generate_image(prompt: str, name: str, w: int, h: int) -> str:
    import time
    encoded = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={w}&height={h}&nologo=true"
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            path = OUT_DIR / f"{name}_bg.jpg"
            path.write_bytes(r.content)
            return str(path)
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


# ── ⑤ BGM生成 (FFmpeg lavfi, Cm アンビエントコード) ─────────────────────────

def _generate_bgm(ffmpeg_bin: str, duration: int, name: str) -> str:
    path = str(OUT_DIR / f"{name}_bgm.aac")
    # C minor chord: C3(130.81) + G3(196) + C4(261.63) + Eb4(311.13)
    expr = (
        "sin(130.81*2*PI*t)*0.25"
        "+sin(196.00*2*PI*t)*0.18"
        "+sin(261.63*2*PI*t)*0.15"
        "+sin(311.13*2*PI*t)*0.10"
    )
    total = duration + 5
    fade_out_start = max(0, duration - 3)
    result = subprocess.run(
        [ffmpeg_bin, "-y",
         "-f", "lavfi", "-i", f"aevalsrc={expr}:s=44100:d={total}",
         "-af", f"afade=t=in:d=2,afade=t=out:st={fade_out_start}:d=3",
         "-c:a", "aac", "-b:a", "96k", path],
        capture_output=True, text=True,
    )
    return path if result.returncode == 0 else ""


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


# ── ② Ken Burns + セグメントクリップ生成 ─────────────────────────────────────

def _supports_drawtext(path: str) -> bool:
    try:
        r = subprocess.run([path, "-filters"], capture_output=True)
        return r.returncode == 0 and b"drawtext" in r.stdout
    except FileNotFoundError:
        return False


def _get_ffmpeg() -> str:
    return next(
        (p for p in ["/usr/local/opt/ffmpeg-full/bin/ffmpeg", "ffmpeg"]
         if _supports_drawtext(p)),
        "ffmpeg"
    )


def _build_segment_clip(
    ffmpeg_bin: str, img: str, duration: int, text: str,
    w: int, h: int, fps: int, idx: int, name: str,
) -> str:
    out = str(OUT_DIR / f"{name}_seg{idx:02d}.mp4")
    ken_burns = (
        f"zoompan=z='min(zoom+0.0003\\,1.3)':d=1"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":s={w}x{h}:fps={fps},setsar=1"
    )
    cap = _drawtext(text, 0, duration) if text else ""
    vf = ",".join(filter(None, [ken_burns, cap]))

    def run(vf_arg: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [ffmpeg_bin, "-y", "-loop", "1", "-t", str(duration), "-i", img,
             "-vf", vf_arg, "-c:v", "libx264", "-t", str(duration),
             "-r", str(fps), "-pix_fmt", "yuv420p", out],
            capture_output=True, text=True,
        )

    result = run(vf)
    if result.returncode != 0:
        no_zoom = "zoompan" in result.stderr
        no_text = "drawtext" in result.stderr or "No such filter" in result.stderr
        base = f"scale={w}:{h},setsar=1" if no_zoom else ken_burns
        fallback_vf = ",".join(filter(None, [base] + ([cap] if cap and not no_text else [])))
        result = run(fallback_vf)
    if result.returncode != 0:
        result = run(f"scale={w}:{h},setsar=1")
    if result.returncode != 0:
        raise RuntimeError(f"Segment {idx} failed: {result.stderr[-300:]}")
    return out


# ── クリップ結合 + 音声ミックス ───────────────────────────────────────────────

def _concat_and_mix(
    ffmpeg_bin: str, clips: list[str], tts: str, bgm: str, out: str,
) -> str:
    list_file = str(OUT_DIR / "concat.txt")
    with open(list_file, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")

    concat_video = str(OUT_DIR / "concat_video.mp4")
    r = subprocess.run(
        [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", list_file,
         "-c", "copy", concat_video],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"Concat failed: {r.stderr[-300:]}")

    if bgm:
        # BGMを小音量(weights=1 0.12)でTTSとミックス
        cmd = [
            ffmpeg_bin, "-y",
            "-i", concat_video, "-i", tts, "-i", bgm,
            "-filter_complex", "[1:a][2:a]amix=inputs=2:weights=1 0.12:duration=first[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-shortest", out,
        ]
    else:
        cmd = [
            ffmpeg_bin, "-y",
            "-i", concat_video, "-i", tts,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-shortest", out,
        ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Mix failed: {r.stderr[-300:]}")
    return out


# ── エントリポイント ──────────────────────────────────────────────────────────

def build(platform: str, content: dict, name: str) -> str:
    OUT_DIR.mkdir(exist_ok=True)
    spec = SPECS[platform]
    w, h, fps = spec["w"], spec["h"], spec["fps"]
    ffmpeg_bin = _get_ffmpeg()

    script = content.get("script", [])
    fallback_prompt = content.get("bg_image_prompt", "minimalist dark abstract background")

    tts = _generate_tts(content.get("tts_narration", ""), name)

    # ④ セグメント別背景画像を逐次生成（Pollinationsレート制限対策）
    import time as _time
    seg_images: dict[int, str] = {}
    if script:
        for i, seg in enumerate(script):
            prompt = seg.get("bg_image_prompt") or f"{fallback_prompt}, scene variation {i + 1}"
            seg_images[i] = _generate_image(prompt, f"{name}_s{i:02d}", w, h)
            if i < len(script) - 1:
                _time.sleep(3)
    else:
        seg_images[0] = _generate_image(fallback_prompt, name, w, h)

    # 総尺を計算してBGM生成
    total_sec = (
        sum(_parse_time(s.get("time", "0-5"))[1] - _parse_time(s.get("time", "0-5"))[0]
            for s in script)
        if script else 30
    )
    bgm = _generate_bgm(ffmpeg_bin, total_sec, name)

    # セグメント別クリップ生成
    if script:
        clips = []
        for i, seg in enumerate(script):
            start, end = _parse_time(seg.get("time", "0-5"))
            duration = max(1, end - start)
            clips.append(_build_segment_clip(
                ffmpeg_bin, seg_images[i], duration,
                seg.get("text_overlay", ""), w, h, fps, i, name,
            ))
    else:
        duration = min(30, spec["max_sec"])
        clips = [_build_segment_clip(
            ffmpeg_bin, seg_images[0], duration, "", w, h, fps, 0, name,
        )]

    out = str(OUT_DIR / f"{name}.mp4")
    return _concat_and_mix(ffmpeg_bin, clips, tts, bgm, out)
