$verge = Get-Process verge-mihomo -ErrorAction SilentlyContinue
if ($verge) {
  Write-Host "=== 发现 verge-mihomo 进程 ==="
  $verge | Format-Table Id, ProcessName, Path -AutoSize | Out-String | Write-Host

  Write-Host "=== 尝试 taskkill /F /PID ==="
  $verge | ForEach-Object {
    Write-Host "--- PID $($_.Id) ---"
    cmd /c "taskkill /F /PID $($_.Id)" 2>&1
  }

  Start-Sleep -Seconds 3

  Write-Host "=== 3 秒后剩余进程 ==="
  $still = Get-Process verge-mihomo -ErrorAction SilentlyContinue
  if ($still) {
    Write-Host "还在运行："
    $still | Format-Table Id, ProcessName -AutoSize | Out-String | Write-Host
  } else {
    Write-Host "已结束。"
  }
} else {
  Write-Host "没有 verge-mihomo 进程在运行。"
}
