#!/usr/bin/env bash
# Thu thập khớp lệnh trong ngày cho config/tickers.txt rồi commit + push dữ liệu tổng hợp.
# Dùng cho lịch chạy hằng ngày sau 15:00 giờ Việt Nam (thứ Hai–thứ Sáu).
set -euo pipefail
cd "$(dirname "$0")/.."

pip install -q -e . >/dev/null 2>&1 || pip install -q --break-system-packages -e .
python -m vnflow.collect

DAY=$(TZ=Asia/Ho_Chi_Minh date +%F)
git add data/levels data/daily data/large data/quality
if git diff --cached --quiet; then
  echo "Không có dữ liệu mới cho $DAY (ngày nghỉ hoặc lỗi thu thập)."
  exit 0
fi
git commit -m "data: khớp lệnh $DAY"
git push
