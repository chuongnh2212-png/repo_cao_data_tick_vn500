# daily_update.ps1 - Chay hang ngay tren may Windows (Task Scheduler):
#   1) git pull du lieu khop lenh (thu thap tu dong tren may chu luc 15:10)
#   2) nap ma _OF + levels vao AmiBroker
#   3) xuat MetaKit N phien gan nhat tu AmiBroker, nap vao data/metakit
#   4) commit + push len GitHub
# Tham so mac dinh: repo C:\vnflow\repo, du lieu xuat C:\vnflow\metakit_export, log C:\vnflow\logs
param(
  [string]$Repo = "C:\vnflow\repo",
  [string]$Apx = "C:\vnflow\vnflow_export.apx",
  [string]$ExportDir = "C:\vnflow\metakit_export",
  [string]$AmiOut = "C:\vnflow\amibroker_out",
  [string]$AmiDir = $(if ($env:AMIBROKER_DIR) { $env:AMIBROKER_DIR } else { "C:\Program Files\AmiBroker" })
)
$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path "C:\vnflow\logs" | Out-Null
$log = "C:\vnflow\logs\update_$(Get-Date -Format yyyy-MM-dd).log"
function Log($m) { "$(Get-Date -Format 'HH:mm:ss') $m" | Tee-Object -FilePath $log -Append }

Set-Location $Repo
Log "== Bat dau =="
git pull --ff-only 2>&1 | ForEach-Object { Log $_ }

Log "-- Nap khop lenh (_OF) vao AmiBroker"
python -m vnflow.amibroker --out $AmiOut 2>&1 | ForEach-Object { Log $_ }
Copy-Item "$Repo\amibroker\vnflow.format" "$AmiDir\Formats\vnflow.format" -Force -ErrorAction SilentlyContinue
cscript //nologo "$Repo\amibroker\import_vnflow.js" "$AmiOut\vnflow_daily.csv" 2>&1 | ForEach-Object { Log $_ }

Log "-- Xuat MetaKit tu AmiBroker"
cscript //nologo "$Repo\amibroker\run_export.js" $Apx 2>&1 | ForEach-Object { Log $_ }
if ($LASTEXITCODE -eq 0) {
  python -m vnflow.metakit $ExportDir 2>&1 | ForEach-Object { Log $_ }
  git add data/metakit
  git diff --cached --quiet
  if ($LASTEXITCODE -ne 0) {
    git commit -m "data: MetaKit cap nhat $(Get-Date -Format yyyy-MM-dd)" 2>&1 | ForEach-Object { Log $_ }
    git push 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) { git pull --rebase 2>&1 | ForEach-Object { Log $_ }; git push 2>&1 | ForEach-Object { Log $_ } }
  } else { Log "Khong co du lieu MetaKit moi" }
} else { Log "LOI: xuat MetaKit that bai (ma $LASTEXITCODE)" }
Log "== Xong =="
