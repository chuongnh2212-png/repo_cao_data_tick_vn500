---
name: phan-tich-cung-cau
description: Phân tích cung cầu một mã cổ phiếu Việt Nam theo quy trình 8 bước (kiểm tra dữ liệu, Wyckoff, Volume Profile, AVWAP, VSA, dòng tiền, nhận định có điều kiện). Dùng khi người dùng yêu cầu phân tích cung cầu, vùng mua/bán, vùng gom hàng, nhà đầu tư lớn, Volume Profile hoặc khớp lệnh của một mã.
---

# Phân tích cung cầu một mã

Trả lời bằng tiếng Việt. Mỗi con số phải có nguồn trong `data/` hoặc file người dùng đưa; không bịa.

## Bước 1 — Dữ liệu
- Khớp lệnh thật: `store.load_levels(MÃ)`, `store.load_daily(MÃ)`; ghi số phiên đã có.
- Nến ngày (nếu có): `store.load_ohlcv(path)` → `quality.check_ohlcv` trên dữ liệu GỐC.
- Mọi phiên vượt biên độ: tìm sự kiện quyền (web), tính hệ số, `quality.adjust_before`. Ghi rõ hệ số và nguồn.
- Đọc `data/quality/*.json` các ngày liên quan; nếu có lỗi `acc_vol`/`incomplete_day` thì cảnh báo.

## Bước 2 — Pha lớn (Wyckoff)
Xác định pha trên biểu đồ tuần: tích lũy / tăng / phân phối / giảm. Đánh dấu sự kiện (SC, AR, ST, Spring,
SOS, LPS, BC, UT, UTAD, SOW, LPSY) kèm ngày, giá, KL × TB20. Nếu chưa phân định, nêu 2 kịch bản.

## Bước 3 — Volume Profile
- Ưu tiên `analysis.profile_from_levels` (có mua/bán chủ động); thiếu thì `profile_from_ohlcv` (ghi "ước lượng").
- Dựng cho toàn kỳ VÀ riêng pha hiện tại. `analysis.value_area`, `analysis.nodes` → POC, VAL, VAH, HVN/LVN gần giá.
- Với levels: delta theo vùng giá, lô lớn mua/bán theo vùng giá.

## Bước 4 — AVWAP
Chọn 3–5 mốc có lý do (đỉnh, đáy, phiên bứt phá/gãy, GDKHQ). Bảng: mốc · lý do · AVWAP · % giá so với AVWAP.

## Bước 5 — VSA 10–20 phiên gần nhất
`analysis.vsa`: liệt kê phiên rv ≥ 1,8 hoặc ≤ 0,6. Mỗi phiên: thay đổi %, rv, rs, clv, cách đọc, phiên sau xác nhận hay không.

## Bước 6 — Dòng tiền
CMF20 (`analysis.cmf`); nếu có levels: delta ngày, CVD (`analysis.cvd`), phân kỳ CVD với giá, lô lớn.

## Bước 7 — Nhận định theo mẫu
| Mục | Nội dung |
|---|---|
| Ngày chốt dữ liệu | |
| Pha lớn | |
| Profile | |
| AVWAP | |
| VSA gần nhất | |
| Dòng tiền | |
| Nhận định + mức tin cậy | |
| Điều kiện tích cực | |
| Điều kiện nhận định sai / tiêu cực | |
| Dữ liệu còn thiếu | |
| Ngày xem lại | |

## Bước 8 — Đầu ra
- Chạy `python -m vnflow.report MÃ [...]` để có biểu đồ trong `reports/MÃ/`.
- Trả lời: kết luận có điều kiện trước, rồi bằng chứng ủng hộ / phản bác, kịch bản, tín hiệu theo dõi.
- Không khuyến nghị mua/bán vô điều kiện.
