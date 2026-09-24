# Batch Video Editor — Hướng dẫn cài đặt (Windows)

Phần mềm này: dán/nhập nhiều link video → tự động tải về → edit hàng loạt theo mẫu có sẵn
(watermark, intro/outro, nhạc nền, phụ đề tự động, hiệu ứng fade/zoom) → xuất file .mp4
theo độ phân giải bạn chọn.

> ⚠️ Đây là mã nguồn Python. Vì được tạo ngoài môi trường Windows nên chưa có sẵn file .exe
> — làm theo bước 4 bên dưới để tự đóng gói thành .exe trên máy bạn (chỉ mất 1 lệnh).

## 1. Cài Python
Tải Python 3.10 hoặc 3.11 tại https://www.python.org/downloads/ (khi cài, tick vào
**"Add Python to PATH"**).

## 2. Cài FFmpeg
- Cách dễ nhất: không cần cài riêng — thư viện `imageio-ffmpeg` trong requirements.txt sẽ
  tự tải ffmpeg cần thiết.
- Nếu muốn cài FFmpeg riêng (khuyến khích để ổn định hơn): tải tại
  https://www.gyan.dev/ffmpeg/builds/ (bản "essentials"), giải nén, thêm thư mục `bin`
  vào biến môi trường PATH của Windows.

## 3. Cài thư viện Python
Mở Command Prompt (cmd) tại thư mục chứa mã nguồn này, chạy:

```bat
pip install -r requirements.txt
```

Lưu ý: `faster-whisper` (dùng cho tính năng tự tạo phụ đề) khá nặng (~1-2GB tải model lần
đầu chạy). Nếu bạn không cần auto-subtitle, có thể bỏ dòng `faster-whisper` khỏi
requirements.txt để cài nhanh hơn — phần mềm vẫn chạy bình thường, chỉ tắt được tính năng đó.

## 4. Chạy thử phần mềm (chưa cần đóng gói .exe)

```bat
python main.py
```

Cửa sổ giao diện sẽ hiện lên. Dán link video vào ô bên trái, chọn mẫu edit, chọn độ phân
giải, chọn thư mục xuất, bấm "Bắt đầu".

## 5. Đóng gói thành file .exe (để chạy không cần cài Python)

```bat
pip install pyinstaller
pyinstaller --onefile --windowed --name BatchVideoEditor --add-data "templates.json;." main.py
```

File `.exe` sẽ nằm trong thư mục `dist\BatchVideoEditor.exe`. Copy file này cùng với file
`templates.json` (và các file watermark/nhạc/intro/outro bạn dùng) đi đâu cũng chạy được,
miễn máy đó cũng cần FFmpeg (xem bước 2) nếu bạn không dùng imageio-ffmpeg.

## Cấu trúc mã nguồn
- `main.py` — điểm khởi chạy
- `gui.py` — giao diện chính + cửa sổ quản lý mẫu
- `downloader.py` — tải video hàng loạt (yt-dlp, hỗ trợ Youtube/TikTok/Facebook/... )
- `editor.py` — pipeline edit: cắt, watermark, intro/outro, nhạc nền, hiệu ứng, xuất mp4
- `subtitle_gen.py` — tạo phụ đề tự động (faster-whisper) từ giọng nói trong video
- `templates.py` / `templates.json` — lưu các mẫu edit bạn tạo (mỗi mẫu là 1 bộ cấu hình)

## Ghi chú quan trọng
- Chỉ tải các video bạn có quyền sử dụng — tôn trọng bản quyền và điều khoản của nền tảng
  gốc (YouTube, TikTok, Facebook...).
- Watermark cần là file ảnh PNG có nền trong suốt để đẹp nhất.
- Intro/outro cần là file video (mp4) cùng tỷ lệ khung hình với video chính để tránh méo hình.
- Nếu xử lý nhiều video độ phân giải cao, quá trình edit có thể tốn thời gian và RAM —
  nên thử với 1-2 video trước khi chạy hàng loạt lớn.
