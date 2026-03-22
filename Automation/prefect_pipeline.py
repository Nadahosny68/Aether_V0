import sys
import os
import logging
import subprocess
import time
from prefect import flow, task

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON = os.path.join(ROOT, "venv", "Scripts", "python.exe")
DTEXEC = r"C:\Program Files\Microsoft SQL Server\160\DTS\Binn\dtexec.exe"

SSIS_ENVIRONMENTAL = os.path.join(ROOT, "ssis", "LoadEnvironmentalFeatures.dtsx")
SSIS_WEATHER       = os.path.join(ROOT, "ssis", "LoadWeatherMetrics.dtsx")
SSIS_POLLUTION     = os.path.join(ROOT, "ssis", "LoadPollutionMetrics.dtsx")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Logging ────────────────────────────────────────────────────────────────
os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)

logger = logging.getLogger("AetherPipeline")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    log_path  = os.path.join(ROOT, "logs", "pipeline.log")
    handler   = logging.FileHandler(log_path)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# ── Helpers ────────────────────────────────────────────────────────────────
def run_script(relative_path):
    full_path = os.path.join(ROOT, relative_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Script not found: {full_path}")

    logger.info(f"Running: {relative_path}")
    start  = time.time()

    result = subprocess.run(
        [PYTHON, full_path],
        capture_output=True,
        text=True,
        cwd=ROOT
    )

    duration = round(time.time() - start, 2)

    if result.stdout:
        logger.info(result.stdout.strip())
    if result.stderr:
        logger.warning(result.stderr.strip())
    if result.returncode != 0:
        logger.error(f"Failed: {relative_path} (took {duration}s)")
        raise Exception(f"Script failed: {relative_path}")

    logger.info(f"Completed: {relative_path} (took {duration}s)")


def run_ssis(package_path):
    package_name = os.path.basename(package_path)
    logger.info(f"Running SSIS: {package_name}")
    start = time.time()

    if not os.path.exists(DTEXEC):
        raise FileNotFoundError(
            f"dtexec.exe not found at:\n{DTEXEC}\n"
            "Run: Get-ChildItem 'C:\\Program Files\\Microsoft SQL Server' "
            "-Recurse -Filter dtexec.exe"
        )

    if not os.path.exists(package_path):
        raise FileNotFoundError(
            f"SSIS package not found at:\n{package_path}\n"
            "Copy the .dtsx file into the ssis/ folder."
        )

    result = subprocess.run(
        [DTEXEC, "/F", package_path],
        capture_output=True,
        text=True
    )

    duration = round(time.time() - start, 2)

    if result.stdout:
        logger.info(f"dtexec output:\n{result.stdout.strip()}")
    if result.stderr:
        logger.error(f"dtexec stderr:\n{result.stderr.strip()}")

    logger.info(f"dtexec exit code: {result.returncode}")

    if result.returncode != 0:
        logger.error(f"SSIS failed: {package_name} (took {duration}s)")
        raise Exception(f"SSIS package failed: {package_path}")

    logger.info(f"SSIS completed: {package_name} (took {duration}s)")


# ── Tasks ──────────────────────────────────────────────────────────────────
@task(retries=2, retry_delay_seconds=10)
def fetch_weather():
    logger.info("----- Fetch Weather API -----")
    run_script("pipelines/ingestion/fetch_weather_api.py")


@task(retries=2, retry_delay_seconds=10)
def fetch_pollution():
    logger.info("----- Fetch Pollution API -----")
    run_script("pipelines/ingestion/fetch_pollution_api.py")


@task(retries=2, retry_delay_seconds=10)
def feature_engineering():
    logger.info("----- Feature Engineering -----")
    run_script("pipelines/transformation/feature_engineering.py")


@task(retries=2, retry_delay_seconds=10)
def load_environmental():
    logger.info("----- SSIS: Load EnvironmentalFeatures -----")
    run_ssis(SSIS_ENVIRONMENTAL)


@task(retries=2, retry_delay_seconds=10)
def load_weather():
    logger.info("----- SSIS: Load WeatherMetrics -----")
    if not os.path.exists(SSIS_WEATHER):
        logger.warning("LoadWeatherMetrics.dtsx not found — skipping.")
        return
    run_ssis(SSIS_WEATHER)


@task(retries=2, retry_delay_seconds=10)
def load_pollution():
    logger.info("----- SSIS: Load PollutionMetrics -----")
    if not os.path.exists(SSIS_POLLUTION):
        logger.warning("LoadPollutionMetrics.dtsx not found — skipping.")
        return
    run_ssis(SSIS_POLLUTION)


@task(retries=2, retry_delay_seconds=10)
def run_predictions():
    logger.info("----- ML Predictions -----")
    run_script("ML/inference/predict_risk.py")


# ── Flow ───────────────────────────────────────────────────────────────────
@flow(name="Aether Pipeline")
def aether_pipeline():
    logger.info(f"===== Aether Pipeline Started — {time.strftime('%Y-%m-%d %H:%M:%S')} =====")

    try:
        # Step 1 — fetch live data from APIs
        fetch_weather()
        fetch_pollution()

        # Step 2 — transform and engineer features
        feature_engineering()

        # Step 3 — load into SQL via SSIS
        load_environmental()
        load_weather()
        load_pollution()

        # Step 4 — ML predictions
        run_predictions()

        logger.info("===== Pipeline Completed Successfully =====")

    except Exception as e:
        logger.error(f"===== Pipeline Failed: {e} =====")
        raise


if __name__ == "__main__":
    aether_pipeline()




# Three things worth noting in this version:
# `load_weather` and `load_pollution` have a graceful skip — if those `.dtsx` files are not copied to the `ssis/` folder yet, the pipeline logs a warning and continues instead of crashing. This means you can run the full pipeline right now even if only `LoadEnvironmentalFeatures.dtsx` exists.
# `run_script` now checks if the script file exists before running it, giving a clear error message instead of a subprocess failure.

# The exit code and full dtexec output are always logged so SSIS failures are never silent again.

# Copy `LoadWeatherMetrics.dtsx` and `LoadPollutionMetrics.dtsx` from your Visual Studio project folder to `ssis/` the same way you did for EnvironmentalFeatures, then run:
# python Automation/prefect_pipeline.py