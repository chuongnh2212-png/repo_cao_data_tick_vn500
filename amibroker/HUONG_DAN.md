# Dùng vn-orderflow với AmiBroker (Windows)

Có ba nguồn dữ liệu, mỗi nguồn là một mã riêng trong AmiBroker:

| Mã | Nguồn | Trường |
|---|---|---|
| `SSI` | FireAnt MetaKit | O H L C (nghìn đồng), V = KL, OI = số CP lưu hành |
| `SSI_CC` | MetaKit – cung cầu đặt lệnh | O = KL đặt bán, C = KL đặt mua, H/L = max/min, V = số lệnh đặt bán, OI = số lệnh đặt mua |
| `SSI_NN` | MetaKit – khối ngoại | O = KL bán, C = KL mua, H/L = max/min, V = GT bán, OI = GT mua |
| `SSI_OF` | **vnflow** – khớp lệnh DSC | O H L C V từ khớp lệnh, Aux1 = mua chủ động, Aux2 = bán chủ động, OI = delta lô lớn |

Quy ước `_CC`, `_NN` lấy từ *FireAnt MetaKit Professional User Guide*. Tài liệu không ghi số phiên bản:
nếu MetaKit 6 khác, bật tham số **Kiểm tra trường** trong `vnflow_metakit.afl` để xem giá trị thô và đối chiếu.

## Cài đặt (một lần)
1. Cài **Git** và **Python 3.10+** (tích "Add Python to PATH").
2. Mở CMD:
   ```bat
   git clone https://github.com/chuongnh2212-png/repo_cao_data_tick_vn500 C:\vnflow
   cd C:\vnflow
   pip install -e .
   ```
3. Chép `amibroker\vnflow.format` vào `C:\Program Files\AmiBroker\Formats\` (cần quyền Administrator).
   AmiBroker cài chỗ khác thì đặt biến môi trường `AMIBROKER_DIR`.
4. Chép 3 file `.afl` trong `amibroker\` vào `AmiBroker\Formulas\Custom\`.

## Hằng ngày
- Mở AmiBroker (đúng database đang dùng MetaKit), rồi chạy `C:\vnflow\amibroker\run_vnflow.bat`
  → kéo dữ liệu 500 mã từ GitHub (thu thập tự động lúc 15:10), xuất và nạp mã `_OF` vào AmiBroker.
- **Chạy tay vài mã, bất kỳ lúc nào** (kể cả trong phiên):
  ```bat
  C:\vnflow\amibroker\run_vnflow.bat SSI MBB HPG
  ```
  Dữ liệu chạy tay lưu ở `data_local\` (không đụng dữ liệu đồng bộ GitHub). Sau 15:10, bản đủ ngày từ GitHub được ưu tiên.
- Tự động: Windows Task Scheduler → 15:40 thứ Hai–thứ Sáu → chạy `run_vnflow.bat` (AmiBroker phải đang mở).

## Các file AFL
| File | Dùng ở đâu | Cho thấy |
|---|---|---|
| `vnflow_profile.afl` | Kéo vào **khung giá** | Volume Profile khớp lệnh thật: mua chủ động (xanh), bán chủ động (đỏ), ATO/ATC (xám), POC, Value Area |
| `vnflow_metakit.afl` | **Khung mới** + Explore | Dư đặt mua/bán, tỷ lệ đặt, KL bình quân mỗi lệnh, NN mua ròng, delta chủ động, CVD |

Explore toàn bộ VN500: Analysis → chọn `vnflow_metakit.afl` → Apply to: watchlist VN500 → Range: 1 recent bar → **Explore**.
Sắp theo cột "Delta 5p", "NN rong 5p", "Du dat 5p" để tìm mã có lực mua áp đảo nhiều phiên.

## Xuất lịch sử MetaKit (từ 2015) cho Claude phân tích
1. Analysis → Formula: `vnflow_export.afl` → Apply to: watchlist mã gốc (VN500) → Range: From-To `01/01/2015` → hôm nay → **Explore**.
2. Mỗi mã thành một file `C:\vnflow\metakit_export\<MÃ>.csv` (giá, KL, số CP lưu hành, đặt mua/bán, khối ngoại).
3. Nạp vào dự án và đẩy lên GitHub:
   ```bat
   cd C:\vnflow
   python -m vnflow.metakit C:\vnflow\metakit_export
   git add data/metakit && git commit -m "data: lịch sử MetaKit" && git push
   ```
   Lệnh nạp in báo cáo kiểm tra quy ước trường; nếu có "CẢNH BÁO" thì gửi lại cho Claude.
   Hoặc nén thư mục `metakit_export` thành .zip và gửi thẳng cho Claude.

## Lưu ý
- Các AFL viết cho AmiBroker **6.10+** và chưa được chạy thử trên máy thật: nếu báo lỗi, gửi lại dòng lỗi.
- Đường dẫn mặc định `C:\vnflow\amibroker_out\levels\` (đổi trong Parameters của `vnflow_profile.afl`).
- Đặt lệnh (`_CC`) ≠ khớp lệnh chủ động (`_OF`): lệnh đặt có thể hủy, lệnh khớp chủ động là tiền thật đã vào.
- "KL/lệnh mua" lớn hơn hẳn "KL/lệnh bán" chỉ là **dấu hiệu gián tiếp** của tổ chức phía mua, không định danh được.
