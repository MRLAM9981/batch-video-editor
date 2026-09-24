"""Pipeline edit video theo template, xuất file mp4 theo độ phân giải chọn."""
import os
from moviepy.editor import (
    VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips,
    AudioFileClip, CompositeAudioClip, afx, vfx,
)
from PIL import Image, ImageDraw, ImageFont

RESOLUTIONS = {
    "Giữ nguyên gốc": None,
    "360p": (640, 360),
    "480p": (854, 480),
    "720p (HD)": (1280, 720),
    "1080p (Full HD)": (1920, 1080),
    "1440p (2K)": (2560, 1440),
}


def _position_xy(position: str, w: int, h: int, cw: int, ch: int, margin=20):
    pos_map = {
        "top-left": (margin, margin),
        "top-right": (w - cw - margin, margin),
        "bottom-left": (margin, h - ch - margin),
        "bottom-right": (w - cw - margin, h - ch - margin),
        "center": ((w - cw) // 2, (h - ch) // 2),
    }
    return pos_map.get(position, pos_map["bottom-right"])


def _make_watermark_clip(wm_cfg: dict, video_w: int, video_h: int, duration: float):
    path = wm_cfg.get("path")
    if not wm_cfg.get("enabled") or not path or not os.path.exists(path):
        return None
    scale = wm_cfg.get("scale", 0.15)
    clip = ImageClip(path)
    target_w = int(video_w * scale)
    clip = clip.resize(width=target_w)
    clip = clip.set_opacity(wm_cfg.get("opacity", 0.7))
    xy = _position_xy(wm_cfg.get("position", "bottom-right"), video_w, video_h, clip.w, clip.h)
    clip = clip.set_position(xy).set_duration(duration)
    return clip


def _make_subtitle_clips(srt_entries: list, sub_cfg: dict, video_w: int, video_h: int):
    """Render mỗi dòng phụ đề thành ảnh PNG (qua PIL) rồi overlay lên video."""
    clips = []
    if not sub_cfg.get("enabled") or not srt_entries:
        return clips

    font_size = sub_cfg.get("font_size", 42)
    color = sub_cfg.get("color", "white")
    position = sub_cfg.get("position", "bottom")
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    for start, end, text in srt_entries:
        if not text.strip():
            continue
        dur = max(end - start, 0.3)
        img_w, img_h = video_w, int(font_size * 2.2)
        img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx, ty = (img_w - tw) // 2, (img_h - th) // 2
        # viền đen để dễ đọc trên mọi nền
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((tx + dx, ty + dy), text, font=font, fill="black")
        draw.text((tx, ty), text, font=font, fill=color)

        clip = ImageClip(__import__("numpy").array(img)).set_start(start).set_duration(dur)
        y = video_h - img_h - 40 if position == "bottom" else 30
        clip = clip.set_position(("center", y))
        clips.append(clip)
    return clips


def _apply_effects(clip, effects_cfg: dict):
    if effects_cfg.get("speed", 1.0) and effects_cfg["speed"] != 1.0:
        clip = clip.fx(vfx.speedx, effects_cfg["speed"])
    if effects_cfg.get("fade_in_out", True):
        clip = clip.fx(vfx.fadein, 0.5).fx(vfx.fadeout, 0.5)
    if effects_cfg.get("zoom_ken_burns", False):
        clip = clip.resize(lambda t: 1 + 0.02 * t)  # zoom-in nhẹ dần (hiệu ứng Ken Burns)
    return clip


def _load_side_clip(path: str, target_size):
    c = VideoFileClip(path)
    if target_size:
        c = c.resize(newsize=target_size)
    return c


def edit_video(video_path: str, template: dict, resolution_key: str, output_path: str,
               srt_path: str = None, log_fn=print):
    """
    Áp dụng 1 template lên 1 video và xuất ra output_path (mp4).
    srt_path: nếu có, sẽ burn phụ đề từ file .srt này vào video.
    """
    clip = VideoFileClip(video_path)

    trim_start = template.get("trim_start", 0) or 0
    trim_end = template.get("trim_end", 0) or 0
    end_t = clip.duration - trim_end if trim_end > 0 else clip.duration
    if trim_start > 0 or trim_end > 0:
        clip = clip.subclip(trim_start, max(trim_start + 0.5, end_t))

    target_size = RESOLUTIONS.get(resolution_key)
    if target_size:
        clip = clip.resize(newsize=target_size)

    clip = _apply_effects(clip, template.get("effects", {}))
    video_w, video_h = clip.size

    layers = [clip]

    wm_clip = _make_watermark_clip(template.get("watermark", {}), video_w, video_h, clip.duration)
    if wm_clip:
        layers.append(wm_clip)

    if srt_path and os.path.exists(srt_path):
        from subtitle_gen import parse_srt
        entries = parse_srt(srt_path)
        layers.extend(_make_subtitle_clips(entries, template.get("subtitle", {}), video_w, video_h))

    final_clip = CompositeVideoClip(layers, size=(video_w, video_h)).set_duration(clip.duration)
    final_clip.audio = clip.audio

    # Trộn nhạc nền
    bg_cfg = template.get("bg_music", {})
    if bg_cfg.get("enabled") and bg_cfg.get("path") and os.path.exists(bg_cfg["path"]):
        music = AudioFileClip(bg_cfg["path"]).fx(afx.audio_loop, duration=final_clip.duration)
        music = music.volumex(bg_cfg.get("volume", 0.2))
        if final_clip.audio:
            final_audio = CompositeAudioClip([final_clip.audio, music])
        else:
            final_audio = music
        final_clip.audio = final_audio

    # Ghép intro / outro
    parts = []
    intro_cfg = template.get("intro", {})
    outro_cfg = template.get("outro", {})
    if intro_cfg.get("enabled") and intro_cfg.get("path") and os.path.exists(intro_cfg["path"]):
        parts.append(_load_side_clip(intro_cfg["path"], (video_w, video_h)))
    parts.append(final_clip)
    if outro_cfg.get("enabled") and outro_cfg.get("path") and os.path.exists(outro_cfg["path"]):
        parts.append(_load_side_clip(outro_cfg["path"], (video_w, video_h)))

    result = concatenate_videoclips(parts, method="compose") if len(parts) > 1 else final_clip

    log_fn(f"  Đang xuất file: {os.path.basename(output_path)} ...")
    result.write_videofile(
        output_path, codec="libx264", audio_codec="aac",
        fps=clip.fps or 30, threads=4, logger=None,
    )

    clip.close()
    result.close()
    return output_path
