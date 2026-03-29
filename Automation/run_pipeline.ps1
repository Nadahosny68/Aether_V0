# Automation/run_pipeline.ps1
# ─────────────────────────────────────────────────────────────
# This script is called by Windows Task Scheduler every day.
# It activates the venv and runs the Prefect pipeline.
# ─────────────────────────────────────────────────────────────

$ROOT    = "D:\Aether\Aether_V0"
$PYTHON  = "$ROOT\venv\Scripts\python.exe"
$SCRIPT  = "$ROOT\Automation\prefect_pipeline.py"
$LOGDIR  = "$ROOT\logs"
$LOGFILE = "$LOGDIR\scheduler.log"

# Ensure log folder exists
New-Item -ItemType Directory -Force -Path $LOGDIR | Out-Null

# Timestamp function
function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts | $msg" | Tee-Object -FilePath $LOGFILE -Append
}

Log "========================================"
Log "Aether daily pipeline starting"
Log "Python : $PYTHON"
Log "Script : $SCRIPT"
Log "========================================"

# Run the pipeline
& $PYTHON $SCRIPT 2>&1 | ForEach-Object {
    Log $_
}

$EXIT = $LASTEXITCODE
if ($EXIT -eq 0) {
    Log "Pipeline finished successfully (exit 0)"
} else {
    Log "ERROR: Pipeline failed with exit code $EXIT"
}

Log "========================================"
