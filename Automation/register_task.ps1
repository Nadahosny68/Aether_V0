# Automation/register_task.ps1
# ─────────────────────────────────────────────────────────────
# Run this script ONCE as Administrator to register the
# Windows Task Scheduler job.
#
# Usage (in PowerShell as Administrator):
#   cd D:\Aether\Aether_V0
#   .\Automation\register_task.ps1
# ─────────────────────────────────────────────────────────────

$TASK_NAME   = "Aether Daily Pipeline"
$SCRIPT_PATH = "D:\Aether\Aether_V0\Automation\run_pipeline.ps1"
$RUN_AT      = "07:00"        # 7:00 AM every day — change if needed
$CURRENT_USER = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

Write-Host "Registering Task Scheduler job..." -ForegroundColor Cyan
Write-Host "  Task name : $TASK_NAME"
Write-Host "  Script    : $SCRIPT_PATH"
Write-Host "  Runs at   : $RUN_AT daily"
Write-Host "  User      : $CURRENT_USER"
Write-Host ""

# Remove existing task if present
$existing = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false
    Write-Host "Removed existing task." -ForegroundColor Yellow
}

# Build the action — PowerShell runs the pipeline script
$ACTION = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$SCRIPT_PATH`""

# Trigger: daily at $RUN_AT
$TRIGGER = New-ScheduledTaskTrigger `
    -Daily `
    -At $RUN_AT

# Settings: run whether user is logged in or not, restart on failure
$SETTINGS = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 15) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# Register the task
Register-ScheduledTask `
    -TaskName $TASK_NAME `
    -Action $ACTION `
    -Trigger $TRIGGER `
    -Settings $SETTINGS `
    -RunLevel Highest `
    -Force | Out-Null

Write-Host "Task registered successfully." -ForegroundColor Green
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  Run now    : Start-ScheduledTask -TaskName '$TASK_NAME'"
Write-Host "  Check status: Get-ScheduledTask -TaskName '$TASK_NAME' | Select-Object State"
Write-Host "  View logs  : Get-Content D:\Aether\Aether_V0\logs\scheduler.log -Tail 50"
Write-Host "  Remove task: Unregister-ScheduledTask -TaskName '$TASK_NAME' -Confirm:`$false"
