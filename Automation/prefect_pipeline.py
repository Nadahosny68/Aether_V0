import os
import subprocess
from datetime import datetime
from dotenv import dotenv_values
from prefect import flow, task, get_run_logger

ROOT   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON = os.path.join(ROOT, "venv", "Scripts", "python.exe")
DTEXEC = r"C:\Program Files\Microsoft SQL Server\160\DTS\Binn\dtexec.exe"
SSIS   = os.path.join(ROOT, "ssis", "LoadEnvironmentalFeatures.dtsx")

# Load .env once here and pass to every subprocess
ENV = {**os.environ, **dotenv_values(os.path.join(ROOT, ".env"))}


def run_script(relative_path: str, *args) -> None:
    logger = get_run_logger()
    full_path = os.path.join(ROOT, relative_path)
    label     = os.path.basename(relative_path)
    logger.info("Running: %s", label)

    result = subprocess.run(
        [PYTHON, full_path, *args],
        capture_output=True,
        text=True,
        env=ENV,                    # passes all .env vars to subprocess
    )

    if result.stdout.strip():
        logger.info(result.stdout.strip())
    if result.stderr.strip():
        logger.warning(result.stderr.strip())   # always show stderr

    if result.returncode != 0:
        raise Exception(f"Script failed: {relative_path}")

    logger.info("%s completed OK", label)


@task(retries=2, retry_delay_seconds=10)
def fetch_weather():
    run_script("pipelines/ingestion/fetch_weather_api.py")

@task(retries=2, retry_delay_seconds=10)
def fetch_pollution():
    run_script("pipelines/ingestion/fetch_pollution_api.py")

@task(retries=1)
def feature_engineering(w, p):
    run_script("pipelines/transformation/feature_engineering.py")

@task(retries=2, retry_delay_seconds=15)
def load_ssis(fe):
    logger = get_run_logger()
    logger.info("Executing SSIS package …")
    result = subprocess.run(
        [DTEXEC, "/FILE", SSIS],
        capture_output=True, text=True, env=ENV,
    )
    if result.stdout.strip():
        logger.info(result.stdout.strip())
    if result.returncode not in (0, 1):
        raise RuntimeError(f"SSIS failed (exit {result.returncode})")
    logger.info("SSIS completed OK")

@task(retries=1)
def run_predictions(ss):
    run_script("ML/inference/predict_risk.py")

@task(retries=2, retry_delay_seconds=10)
def fetch_weather_forecast():
    run_script("pipelines/ingestion/fetch_weather_forecast.py")

@task(retries=2, retry_delay_seconds=10)
def fetch_pollution_forecast():
    run_script("pipelines/ingestion/fetch_pollution_forecast.py")

@task(retries=1)
def engineer_forecast_features(wf, pf):
    run_script("pipelines/transformation/feature_engineering_forecast.py")

@task(retries=1)
def run_forecast_predictions(fef):
    run_script("ML/inference/predict_forecast.py")


@flow(name="aether-daily-pipeline", log_prints=True)
def aether_pipeline():
    logger = get_run_logger()
    logger.info("=== Aether pipeline started: %s ===", datetime.now().isoformat())

    # Branch A: historical update
    w  = fetch_weather()
    p  = fetch_pollution()
    fe = feature_engineering(w, p)
    ss = load_ssis(fe)
    run_predictions(ss)

    # Branch B: 3-day forecast
    wf  = fetch_weather_forecast()
    pf  = fetch_pollution_forecast()
    fef = engineer_forecast_features(wf, pf)
    run_forecast_predictions(fef)

    logger.info("=== Aether pipeline complete ===")


if __name__ == "__main__":
    aether_pipeline()