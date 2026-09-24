"""Tải video hàng loạt từ danh sách URL bằng yt-dlp."""
import os
import re
import yt_dlp


def _safe_name(s: str, idx: int) -> str:
    s = re.sub(r"[\\/:*?\"<>|]", "_", s)[:80].strip()
    return s or f"video_{idx}"


def download_videos(urls: list[str], out_dir: str, log_fn=print) -> list[str]:
    """
    Tải danh sách URL video (Youtube, Facebook, TikTok, v.v. - bất cứ site nào yt-dlp hỗ trợ).
    Trả về danh sách đường dẫn file .mp4 đã tải thành công.
    """
    os.makedirs(out_dir, exist_ok=True)
    downloaded = []

    for idx, url in enumerate(urls, start=1):
        url = url.strip()
        if not url:
            continue
        log_fn(f"[{idx}/{len(urls)}] Đang tải: {url}")
        outtmpl = os.path.join(out_dir, f"src_{idx:03d}_%(title).60s.%(ext)s")
        ydl_opts = {
            "outtmpl": outtmpl,
            "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "ignoreerrors": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    log_fn(f"  ✗ Lỗi: không lấy được thông tin video từ {url}")
                    continue
                filepath = ydl.prepare_filename(info)
                # yt-dlp có thể đổi đuôi sau khi merge sang mp4
                base, _ = os.path.splitext(filepath)
                mp4path = base + ".mp4"
                final_path = mp4path if os.path.exists(mp4path) else filepath
                if os.path.exists(final_path):
                    downloaded.append(final_path)
                    log_fn(f"  ✓ Xong: {os.path.basename(final_path)}")
                else:
                    log_fn(f"  ✗ Không tìm thấy file sau khi tải: {url}")
        except Exception as e:
            log_fn(f"  ✗ Lỗi khi tải {url}: {e}")

    return downloaded
