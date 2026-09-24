"""Tạo phụ đề tự động (auto subtitle) từ audio của video, dùng faster-whisper (chạy offline).
Nếu chưa cài faster-whisper, hàm sẽ báo lỗi rõ ràng và trả về None thay vì crash.
"""
import os

_MODEL_CACHE = {}


def _get_model(model_size="small"):
    if model_size not in _MODEL_CACHE:
        from faster_whisper import WhisperModel
        # device="cpu" để chạy được trên mọi máy Windows không cần GPU
        _MODEL_CACHE[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _MODEL_CACHE[model_size]


def _format_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def generate_srt(video_path: str, srt_out_path: str, language: str = "vi", log_fn=print) -> str | None:
    try:
        model = _get_model("small")
    except ImportError:
        log_fn("  ⚠ Chưa cài faster-whisper nên bỏ qua auto-subtitle. "
               "Cài bằng: pip install faster-whisper")
        return None
    except Exception as e:
        log_fn(f"  ⚠ Không tải được model nhận diện giọng nói: {e}")
        return None

    log_fn("  Đang nhận diện giọng nói để tạo phụ đề...")
    try:
        segments, _info = model.transcribe(video_path, language=language, vad_filter=True)
        with open(srt_out_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, start=1):
                f.write(f"{i}\n{_format_ts(seg.start)} --> {_format_ts(seg.end)}\n{seg.text.strip()}\n\n")
        return srt_out_path
    except Exception as e:
        log_fn(f"  ⚠ Lỗi khi tạo phụ đề: {e}")
        return None


def parse_srt(srt_path: str):
    """Đọc file .srt, trả về list (start_sec, end_sec, text)."""
    entries = []
    if not os.path.exists(srt_path):
        return entries
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
    blocks = content.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        time_line = lines[1]
        try:
            start_str, end_str = time_line.split(" --> ")
            start = _srt_ts_to_sec(start_str)
            end = _srt_ts_to_sec(end_str)
            text = " ".join(lines[2:])
            entries.append((start, end, text))
        except Exception:
            continue
    return entries


def _srt_ts_to_sec(ts: str) -> float:
    ts = ts.strip().replace(",", ".")
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)
