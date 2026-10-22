"""Cấu hình chung của dự án vn-orderflow."""
from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
# VNFLOW_DATA: đổi thư mục dữ liệu (chạy tay trên máy cá nhân dùng data_local để không đụng dữ liệu đồng bộ từ GitHub)
DATA = Path(os.environ.get("VNFLOW_DATA", ROOT / "data"))
if not DATA.is_absolute():
    DATA = ROOT / DATA
RAW_DIR = DATA / "raw"          # khớp lệnh từng lệnh (mặc định KHÔNG commit, xem .gitignore)
LEVELS_DIR = DATA / "levels"    # tổng hợp theo bước giá / mã / ngày (commit)
DAILY_DIR = DATA / "daily"      # tóm tắt ngày từ khớp lệnh (commit)
LARGE_DIR = DATA / "large"      # danh sách lệnh lô lớn (commit)
QUALITY_DIR = DATA / "quality"  # nhật ký kiểm tra dữ liệu (commit)
OHLCV_DIR = DATA / "ohlcv"      # nến ngày nhập tay (Excel/CSV)
REPORTS = ROOT / "reports"
TICKERS_FILE = ROOT / "config" / "tickers.txt"

TZ = ZoneInfo("Asia/Ho_Chi_Minh")

# Nguồn dữ liệu: API nội bộ của DSC, không có tài liệu công khai.
# Chỉ trả về khớp lệnh của NGÀY HIỆN TẠI; tham số ngày bị bỏ qua (đã kiểm tra 22/10/2026).
DSC_URL = os.environ.get("DSC_URL", "https://trading.dsc.com.vn/datafeed/alltranslogs/{symbol}")
REQUEST_DELAY_SEC = float(os.environ.get("REQUEST_DELAY_SEC", "0.8"))  # lịch sự với máy chủ
REQUEST_TIMEOUT_SEC = 30
MAX_RETRIES = 3

# Lệnh lô lớn: giá trị khớp >= ngưỡng (VND). Có thêm cờ theo phân vị 99% của từng mã/ngày.
LARGE_LOT_VALUE_VND = float(os.environ.get("LARGE_LOT_VALUE_VND", 1_000_000_000))
LARGE_LOT_QUANTILE = 0.99

# Biên độ dao động (cổ phiếu) theo sàn.
PRICE_LIMIT = {"HOSE": 0.07, "HSX": 0.07, "HNX": 0.10, "UPCOM": 0.15}

# Phiên khớp lệnh định kỳ (HOSE): ATO 09:00–09:15, ATC 14:30–14:45.
ATO_END = "09:15:00"
ATC_START = "14:30:00"
SESSION_CLOSE = "14:45:00"


def tick_size(price_vnd: float, exchange: str) -> int:
    """Bước giá cổ phiếu (VND). HNX/UPCoM: 100. HOSE: 10 / 50 / 100 theo vùng giá."""
    ex = (exchange or "").upper()
    if ex in ("HNX", "UPCOM"):
        return 100
    if price_vnd < 10_000:
        return 10
    if price_vnd < 50_000:
        return 50
    return 100
