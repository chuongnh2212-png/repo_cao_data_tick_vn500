# Cài đặt tự động trên máy Windows (dành cho phiên Claude desktop đã liên kết máy)

Mục tiêu: hằng ngày 16:00 (thứ Hai–thứ Sáu) máy tự nạp khớp lệnh vào AmiBroker, xuất MetaKit 10 phiên gần nhất,
nạp vào `data/metakit` và đẩy lên GitHub `chuongnh2212-png/repo_cao_data_tick_vn500`.

1. Kiểm tra Git, Python ≥ 3.10 (`git --version`, `python --version`); thiếu thì hướng dẫn người dùng cài.
2. `git clone https://github.com/chuongnh2212-png/repo_cao_data_tick_vn500 C:\vnflow\repo`
   (lần push đầu Git Credential Manager mở trình duyệt để đăng nhập GitHub — người dùng tự đăng nhập).
3. `cd C:\vnflow\repo && pip install -e .`
4. Chép `amibroker\*.afl` vào `<AmiBroker>\Formulas\Custom\`, `amibroker\vnflow.format` vào `<AmiBroker>\Formats\`.
5. Người dùng tạo 1 lần file project trong AmiBroker: Analysis → Formula `vnflow_export.afl` →
   Apply to: watchlist VN500 → Range: **N last days = 10** → File → Save As `C:\vnflow\vnflow_export.apx`.
6. Chạy thử: `powershell -ExecutionPolicy Bypass -File C:\vnflow\repo\scripts\windows\daily_update.ps1`
   (AmiBroker đang mở), đọc log `C:\vnflow\logs\update_<ngày>.log`.
7. Đăng ký lịch: `powershell -ExecutionPolicy Bypass -File C:\vnflow\repo\scripts\windows\install_task.ps1`.
