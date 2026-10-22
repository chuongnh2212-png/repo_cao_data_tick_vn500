# vn-orderflow

Thu thập khớp lệnh từng lệnh (có chiều mua/bán chủ động) cho cổ phiếu Việt Nam và phân tích cung cầu:
Volume Profile theo bước giá, delta, lệnh lô lớn, Anchored VWAP, VSA, Wyckoff, CMF.
Dùng với **Claude Code trên đám mây**: Claude đọc `CLAUDE.md` và skill `phan-tich-cung-cau` để phân tích theo quy trình chuẩn.

## Bắt đầu
```bash
pip install -e ".[dev]"
python -m pytest -q
python -m vnflow.collect --symbols SSI --allow-partial    # thử 1 mã
```

## Thu thập hằng ngày
API DSC chỉ trả dữ liệu **ngày hiện tại**, nên phải chạy mỗi ngày giao dịch sau 15:00 (giờ Việt Nam):
`bash scripts/daily.sh` → ghi `data/levels`, `data/daily`, `data/large`, `data/quality` rồi commit + push.

Yêu cầu với môi trường Claude Code trên đám mây:
1. Cho phép truy cập mạng tới `trading.dsc.com.vn` trong cấu hình mạng của môi trường.
2. Phiên có quyền push vào repo này.

Danh sách mã: `config/tickers.txt`. Với ~500 mã và nhịp 0,8 giây/lần gọi, một lần chạy mất khoảng 7–10 phút.

## Phân tích
- Trong Claude Code: "Phân tích cung cầu SSI" → skill `phan-tich-cung-cau`.
- Thủ công: `python -m vnflow.report SSI` (khớp lệnh) hoặc thêm `--ohlcv <file>` (nến ngày).

## Giới hạn
- API DSC là API nội bộ, không có tài liệu; định dạng có thể đổi. `tests/fixtures/dsc_ssi_sample.json` lưu định dạng đã kiểm tra ngày 22/10/2026.
- Khớp lệnh không cho biết danh tính người mua/bán; mọi kết luận về "nhà đầu tư lớn" là suy luận gián tiếp.
- Phân tích phục vụ nghiên cứu, không phải khuyến nghị đầu tư.
