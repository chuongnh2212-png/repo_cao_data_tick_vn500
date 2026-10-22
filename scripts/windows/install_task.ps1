# install_task.ps1 - Dang ky lich chay daily_update.ps1 luc 16:00 thu Hai - thu Sau.
# Chay task khi nguoi dung dang dang nhap (AmiBroker can phien Windows tuong tac).
param([string]$Repo = "C:\vnflow\repo", [string]$At = "16:00")
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
           -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Repo\scripts\windows\daily_update.ps1`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "vnflow - cap nhat du lieu" -Action $action -Trigger $trigger `
  -Settings $settings -Description "Nap khop lenh vao AmiBroker, xuat MetaKit, day len GitHub" -Force
Write-Output "Da dang ky: vnflow - cap nhat du lieu, $At thu 2-6. Chay thu: Start-ScheduledTask 'vnflow - cap nhat du lieu'"
