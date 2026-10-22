# vn-orderflow — hướng dẫn cho Claude Code

Dự án thu thập khớp lệnh từng lệnh cổ phiếu Việt Nam (nguồn API DSC) và phân tích cung cầu:
Volume Profile, Anchored VWAP, VSA, Wyckoff, dòng tiền (CMF, delta/CVD), lệnh lô lớn.

## Người dùng và cách trả lời
- Luôn trả lời bằng **tiếng Việt**, rõ ràng, chuyên nghiệp; giữ thuật ngữ tiếng Anh phổ biến (POC, VWAP, delta…).
- Người dùng tự ra quyết định đầu tư. Đưa **kết luận có điều kiện + mức tin cậy + điều kiện khiến nhận định sai**.
  Không đưa khuyến nghị mua/bán vô điều kiện.
- Tách rõ: dữ kiện / diễn giải / giả định / dự báo. Không suy tương quan thành nhân quả.
- Ghi rõ ngày chốt dữ liệu, đơn vị (VND hay nghìn đồng), mã, sàn.
- Không bịa số liệu. Nếu thiếu dữ liệu, nói rõ đang thiếu gì.

## Lệnh thường dùng
```bash
pip install -e ".[dev]"                       # cài đặt (hook SessionStart đã làm sẵn)
python -m pytest -q                           # kiểm thử offline
python -m vnflow.collect                      # thu thập toàn bộ config/tickers.txt (chỉ chạy sau 15:00 giờ VN)
python -m vnflow.collect --symbols SSI MBB --allow-partial   # thử nhanh trong phiên
python -m vnflow.report SSI                   # báo cáo từ khớp lệnh đã thu thập
python -m vnflow.report SSI --ohlcv data/ohlcv/SSI_2025-05-28_2026-10-09.xlsx \
    --adjust 2026-07-10:0.7992 --anchors 2025-08-29 2026-07-28   # báo cáo từ nến ngày
bash scripts/daily.sh                         # thu thập + commit + push (dùng cho lịch hằng ngày)
```

## Nguồn dữ liệu DSC (đã kiểm tra 22/10/2026)
- `https://trading.dsc.com.vn/datafeed/alltranslogs/{MÃ}` → JSON `{s, ec, em, d:[...]}`.
- **Chỉ trả về ngày hiện tại**; tham số ngày bị bỏ qua. Bỏ lỡ ngày nào là mất ngày đó.
- `lastColor`: `B` = mua chủ động, `S` = bán chủ động, không có = phiên định kỳ ATO/ATC.
- `totalBuyVol` / `totalSellVol`: lũy kế mua/bán chủ động trong ngày. Giá tính bằng **VND**.
- API nội bộ, không có tài liệu: giữ nhịp ≥ 0,8 giây/lần gọi, 1 lần/mã/ngày.
- Môi trường cloud phải được phép truy cập mạng tới `trading.dsc.com.vn`.

## Cấu trúc dữ liệu (`data/`)
| Thư mục | Nội dung | Commit? |
|---|---|---|
| `levels/YYYY/YYYY-MM-DD.parquet` | mã × giá: vol, buy_vol, sell_vol, auction_vol, delta, lô lớn | Có |
| `daily/…` | mã × ngày: OHLC, vol, value, buy/sell, delta, VWAP, POC, ATO/ATC, lô lớn | Có |
| `large/…` | danh sách lệnh lô lớn (≥ 1 tỷ VND hoặc ≥ phân vị 99% của mã) | Có |
| `quality/YYYY-MM-DD.json` | tóm tắt lần chạy + lỗi kiểm tra | Có |
| `raw/…` | khớp lệnh thô (`--keep-raw`) | Không (quá lớn) |
| `ohlcv/` | nến ngày người dùng cung cấp (Excel/CSV, giá nghìn đồng) | Có |
| `metakit/<MÃ>.parquet` | lịch sử FireAnt MetaKit từ 2015: giá, KL, CP lưu hành, đặt mua/bán (`cc_*`), khối ngoại (`nn_*`); nạp bằng `python -m vnflow.metakit`, đọc bằng `metakit.load(MÃ)` | Có |

## Quy tắc phân tích bắt buộc
1. **Kiểm tra dữ liệu trước**: `quality.check_trades` cho khớp lệnh; `quality.check_ohlcv` cho nến ngày
   (biến động vượt biên độ HOSE ±7% / HNX ±10% / UPCoM ±15%, giá lẻ bước giá, O=H=L=C, trùng ngày).
2. Biến động vượt biên độ = gần như chắc chắn là **sự kiện quyền điều chỉnh sai**. Tìm sự kiện, tính hệ số,
   dùng `quality.adjust_before`. Ví dụ đã biết: SSI 10/07/2026 hệ số 0,7992 (cổ tức 1.000 đ + thưởng 5:1,
   GDKHQ 17/08/2026); SSI 16/09/2025 −10,2% chưa rõ nguyên nhân.
3. Phiên trần/sàn trắng: KL thấp vì một bên biến mất, **không** đọc là cạn cung/cầu.
4. Profile từ nến ngày là **ước lượng**; ưu tiên `data/levels` khi đủ phiên.
5. Nhãn VSA trong `analysis.vsa` chỉ là gợi ý: phải đọc bối cảnh và phiên sau xác nhận/phủ nhận.
6. Dữ liệu MetaKit: đọc `data/metakit/README.md` trước. KL khối ngoại trước 2022 lệch đơn vị → dùng GT hoặc dấu ròng; phiên |biến động| >15,5% phải xử lý trước khi phân tích.
7. Khi nói về "nhà đầu tư lớn", nói rõ đây là suy luận gián tiếp (delta, lô lớn, hấp thụ), không phải dữ liệu định danh.

Quy trình phân tích đầy đủ nằm trong skill `phan-tich-cung-cau` (`.claude/skills/`).

## Quy ước code
- Python ≥ 3.10, pandas, pyarrow (parquet zstd). Hàm thuần trong `src/vnflow/`, CLI qua `python -m`.
- Thêm/sửa logic phải kèm test trong `tests/` chạy được không cần mạng.
- Không commit `data/raw/`, khóa API hay thông tin tài khoản.
