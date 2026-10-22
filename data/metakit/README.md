# Báo cáo chất lượng dữ liệu MetaKit (nạp ngày 22/10/2026)

Nguồn: FireAnt MetaKit 6 qua AmiBroker, xuất bằng `amibroker/vnflow_export.afl`, nạp bằng `python -m vnflow.metakit`.
Chi tiết từng mã: `data/metakit_quality.csv`.

| Chỉ tiêu | Kết quả |
|---|---|
| Số mã | 500 |
| Tổng số phiên | 1,170,865 |
| Khoảng ngày | 2015-09-01 → 2026-10-22 |
| Mã dừng trước 22/10/2026 | BCG (phiên cuối 18/08/2026) |
| Mã không có _CC/_NN (mới niêm yết, ≤256 phiên) | 12: AAN, ALC, CLI, CRV, DCV, GEL, HPA, RGG, TCX, UPS, VCK, VPX |
| Mã thiếu số lệnh đặt (cc_lenh_*) >50% phiên | 30 |
| Mã có phiên biến động >15,5% (vượt mọi biên độ) | 181 mã, 1643 phiên |
| Mã có >5% phiên GT/KL khối ngoại lệch >3 lần giá | 132 |

## Kết luận dùng dữ liệu
1. **Đặt lệnh (_CC) và khối ngoại theo chiều (mua/bán ròng)**: dùng được; đã sửa quy ước "một bên = 0" (cột `*_raw` giữ số gốc).
2. **Khối lượng khối ngoại trước 2022 có đơn vị không nhất quán** (nhiều phiên GT/KL ≈ 10× giá, ví dụ ACV 2017):
   số lỗi theo năm 2015–2021 là hàng nghìn phiên/năm, từ 2022 chỉ còn vài chục–vài trăm.
   → Với khối ngoại trước 2022, ưu tiên **giá trị (nn_gt_*, đồng)** hoặc chỉ dùng **dấu** của ròng; không so KL khối ngoại với KL khớp.
3. **Phiên biến động >15,5%**: gần như chắc chắn là sự kiện quyền chưa điều chỉnh, ngày chào sàn hoặc lỗi dữ liệu.
   Phải kiểm tra trước khi tính lợi suất, AVWAP hay profile qua các phiên này. Nhiều nhất: VFC (80), DCF (44), MVB (41), TBD (41), TSJ (35), FIC (30), HPI (29), GTD (29), VLB (29), VIW (28).
4. Giá MetaKit là giá đã điều chỉnh (nghìn đồng), có thể khác giá DSC (VND, chưa điều chỉnh).
