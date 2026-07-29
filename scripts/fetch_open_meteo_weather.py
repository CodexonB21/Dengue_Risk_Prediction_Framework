"""Fetch and append Open-Meteo daily weather for all 25 district CSVs.

Uses the Open-Meteo Archive API for observed gap-fill (last file date + 1
through yesterday) and the Forecast API for future days (today through the
operational horizon). Non-commercial use; data © Open-Meteo (CC BY 4.0).

Run standalone::

    python scripts/fetch_open_meteo_weather.py

Or via ``scripts/refresh_dashboard_data.py`` (recommended).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import FORECAST_HORIZON_WEEKS, RAW_WEATHER_DIR  # noqa: E402
from src.preprocessing.shared import load_weather_file  # noqa: E402

logger = logging.getLogger(__name__)

ARCHIVE_API_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "Asia/Colombo"

# Open-Meteo daily variable names (API) -> existing raw CSV column names.
DAILY_API_VARIABLES = [
    "relative_humidity_2m_mean",
    "relative_humidity_2m_max",
    "relative_humidity_2m_min",
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_mean",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "rain_sum",
    "precipitation_sum",
    "weather_code",
]

API_TO_CSV_COLUMNS = {
    "relative_humidity_2m_mean": "relative_humidity_2m_mean (%)",
    "relative_humidity_2m_max": "relative_humidity_2m_max (%)",
    "relative_humidity_2m_min": "relative_humidity_2m_min (%)",
    "temperature_2m_max": "temperature_2m_max (°C)",
    "temperature_2m_min": "temperature_2m_min (°C)",
    "temperature_2m_mean": "temperature_2m_mean (°C)",
    "apparent_temperature_mean": "apparent_temperature_mean (°C)",
    "apparent_temperature_max": "apparent_temperature_max (°C)",
    "apparent_temperature_min": "apparent_temperature_min (°C)",
    "rain_sum": "rain_sum (mm)",
    "precipitation_sum": "precipitation_sum (mm)",
    "weather_code": "weather_code (wmo code)",
}

DATA_COLUMNS = ["time"] + list(API_TO_CSV_COLUMNS.values())
SOURCE_COLUMN = "climate_data_source"

FILENAME_RE = re.compile(
    r"^open-meteo-(?P<lat>\d+\.?\d*)N(?P<lon>\d+\.?\d*)E(?P<elev>\d+)m (?P<district>.+)\.csv$",
    re.IGNORECASE,
)

REQUEST_DELAY_SECONDS = 0.35
MAX_FORECAST_DAYS = 16  # Open-Meteo free Forecast API daily limit.


def parse_weather_filename(path: Path) -> dict[str, str | float]:
    match = FILENAME_RE.match(path.name)
    if not match:
        raise ValueError(f"Unexpected weather filename pattern: {path.name}")
    return {
        "district": match.group("district"),
        "latitude": float(match.group("lat")),
        "longitude": float(match.group("lon")),
        "elevation": float(match.group("elev")),
    }


def read_preamble_metadata(path: Path) -> dict[str, float]:
    """Read lat/lon/elevation from row 2 of the Open-Meteo CSV preamble."""
    with open(path, "r", encoding="utf-8-sig") as fh:
        fh.readline()  # header row 1
        row2 = fh.readline().strip().split(",")
    return {
        "latitude": float(row2[0]),
        "longitude": float(row2[1]),
        "elevation": float(row2[2]),
    }


def _detect_date_format(series: pd.Series) -> str:
    sample = series.dropna().astype(str).iloc[-1] if len(series) else ""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", sample):
        return "iso"
    return "mdy"


def _format_date(d: date, fmt: str) -> str:
    if fmt == "iso":
        return d.isoformat()
    # Match Colombo-style M/D/YYYY (no zero-padding).
    return f"{d.month}/{d.day}/{d.year}"


def _fetch_json(url: str, retries: int = 3) -> dict:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.loads(response.read())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_err = exc
            if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
                wait = 2 ** attempt
                logger.warning("Rate limited (429); sleeping %ds before retry...", wait)
                time.sleep(wait)
            else:
                time.sleep(1.0 + attempt)
    raise RuntimeError(f"Open-Meteo request failed after {retries} attempts: {last_err}")


def _api_response_to_frame(payload: dict, source_tag: str) -> pd.DataFrame:
    daily = payload["daily"]
    rows = {"time": pd.to_datetime(daily["time"])}
    for api_col, csv_col in API_TO_CSV_COLUMNS.items():
        rows[csv_col] = daily.get(api_col)
    df = pd.DataFrame(rows)
    df[SOURCE_COLUMN] = source_tag
    return df


def fetch_archive(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
    if start > end:
        return pd.DataFrame(columns=DATA_COLUMNS + [SOURCE_COLUMN])
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(DAILY_API_VARIABLES),
        "timezone": TIMEZONE,
    }
    url = ARCHIVE_API_URL + "?" + urllib.parse.urlencode(params)
    payload = _fetch_json(url)
    return _api_response_to_frame(payload, "observed")


def fetch_forecast(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
    if start > end:
        return pd.DataFrame(columns=DATA_COLUMNS + [SOURCE_COLUMN])
    forecast_days = min((end - start).days + 1, MAX_FORECAST_DAYS)
    params = {
        "latitude": lat,
        "longitude": lon,
        "forecast_days": forecast_days,
        "daily": ",".join(DAILY_API_VARIABLES),
        "timezone": TIMEZONE,
    }
    url = FORECAST_API_URL + "?" + urllib.parse.urlencode(params)
    payload = _fetch_json(url)
    df = _api_response_to_frame(payload, "forecast")
    df = df[(df["time"].dt.date >= start) & (df["time"].dt.date <= end)]
    return df


def compute_forecast_horizon_end(today: date) -> date:
    """End date for forecast fetch: at least ``FORECAST_HORIZON_WEEKS`` epi-weeks
    beyond the last case week when calendar data is available, capped by the
    Forecast API's ``MAX_FORECAST_DAYS`` window from ``today``."""
    calendar_path = PROJECT_ROOT / "data" / "processed" / "shared" / "epi_week_calendar.csv"
    target_end = today + timedelta(days=MAX_FORECAST_DAYS - 1)
    if calendar_path.exists():
        cal = pd.read_csv(calendar_path, parse_dates=["Week_End_Date"])
        if not cal.empty:
            last_end = cal["Week_End_Date"].max().date()
            weeks_target = last_end + timedelta(days=FORECAST_HORIZON_WEEKS * 7)
            target_end = min(weeks_target, today + timedelta(days=MAX_FORECAST_DAYS - 1))
    return target_end


def _read_preamble_lines(path: Path) -> list[str]:
    with open(path, "r", encoding="utf-8-sig") as fh:
        return [fh.readline() for _ in range(3)]


def _write_appended_csv(
    path: Path,
    preamble_lines: list[str],
    existing: pd.DataFrame,
    new_rows: pd.DataFrame,
    date_fmt: str,
) -> None:
    combined = pd.concat([existing, new_rows], ignore_index=True)
    combined["time"] = pd.to_datetime(combined["time"])
    combined = combined.drop_duplicates(subset="time", keep="first")
    combined = combined.sort_values("time").reset_index(drop=True)

    if SOURCE_COLUMN not in combined.columns:
        combined[SOURCE_COLUMN] = "observed"

    header_cols = DATA_COLUMNS + [SOURCE_COLUMN]
    out_lines: list[str] = preamble_lines[:3]
    if not out_lines[2].strip():
        out_lines[2] = "\n"
    out_lines.append(",".join(header_cols) + "\n")

    for _, row in combined.iterrows():
        d = row["time"].date() if hasattr(row["time"], "date") else pd.Timestamp(row["time"]).date()
        values = [_format_date(d, date_fmt)]
        for col in API_TO_CSV_COLUMNS.values():
            val = row[col]
            if pd.isna(val):
                values.append("")
            elif col == "weather_code (wmo code)":
                values.append(str(int(val)))
            elif col.endswith("(mm)"):
                values.append(f"{float(val):.2f}" if float(val) != int(float(val)) else str(int(val)))
            else:
                values.append(str(round(float(val), 1) if float(val) != int(float(val)) else int(val)))
        values.append(str(row[SOURCE_COLUMN]))
        out_lines.append(",".join(values) + "\n")

    path.write_text("".join(out_lines), encoding="utf-8")


def refresh_district_file(path: Path, today: date | None = None) -> dict:
    today = today or date.today()
    yesterday = today - timedelta(days=1)

    meta = parse_weather_filename(path)
    preamble = read_preamble_metadata(path)
    lat, lon = preamble["latitude"], preamble["longitude"]

    existing = load_weather_file(path)
    if SOURCE_COLUMN not in existing.columns:
        existing[SOURCE_COLUMN] = "observed"

    old_max = existing["time"].max().date()
    date_fmt = _detect_date_format(existing["time"])

    observed_start = old_max + timedelta(days=1)
    forecast_start = today
    forecast_end = compute_forecast_horizon_end(today)

    observed_df = fetch_archive(lat, lon, observed_start, yesterday)
    time.sleep(REQUEST_DELAY_SECONDS)
    forecast_df = fetch_forecast(lat, lon, forecast_start, forecast_end)

    new_rows = pd.concat([observed_df, forecast_df], ignore_index=True)
    if new_rows.empty:
        logger.info(
            "%s: already up to date (max=%s).",
            meta["district"], old_max,
        )
        return {
            "district": meta["district"],
            "old_max_date": old_max.isoformat(),
            "new_max_date": old_max.isoformat(),
            "rows_appended": 0,
            "observed_rows": 0,
            "forecast_rows": 0,
        }

    existing_dates = set(existing["time"].dt.normalize())
    new_rows["time"] = pd.to_datetime(new_rows["time"]).dt.normalize()
    new_rows = new_rows[~new_rows["time"].isin(existing_dates)]

    if new_rows.empty:
        logger.info("%s: API returned no new dates beyond existing file.", meta["district"])
        new_max = old_max
        rows_appended = 0
        n_obs = n_fc = 0
    else:
        preamble_lines = _read_preamble_lines(path)
        _write_appended_csv(path, preamble_lines, existing, new_rows, date_fmt)
        new_max = max(old_max, new_rows["time"].max().date())
        rows_appended = len(new_rows)
        n_obs = int((new_rows[SOURCE_COLUMN] == "observed").sum())
        n_fc = int((new_rows[SOURCE_COLUMN] == "forecast").sum())
        logger.info(
            "%s: max %s -> %s | appended %d rows (%d observed, %d forecast).",
            meta["district"], old_max, new_max, rows_appended, n_obs, n_fc,
        )

    return {
        "district": meta["district"],
        "old_max_date": old_max.isoformat(),
        "new_max_date": new_max.isoformat(),
        "rows_appended": rows_appended,
        "observed_rows": n_obs,
        "forecast_rows": n_fc,
    }


def run_fetch(weather_dir: Path = RAW_WEATHER_DIR, today: date | None = None) -> pd.DataFrame:
    today = today or date.today()
    files = sorted(weather_dir.glob("open-meteo-*.csv"))
    if not files:
        raise FileNotFoundError(f"No weather CSVs found in {weather_dir}")

    summaries = []
    for i, path in enumerate(files):
        summaries.append(refresh_district_file(path, today=today))
        if i < len(files) - 1:
            time.sleep(REQUEST_DELAY_SECONDS)

    summary_df = pd.DataFrame(summaries)
    manifest_path = weather_dir / "climate_fetch_manifest.csv"
    summary_df.to_csv(manifest_path, index=False)
    logger.info(
        "Fetch complete for %d districts. Total appended rows: %d. Manifest: %s",
        len(summary_df),
        int(summary_df["rows_appended"].sum()),
        manifest_path,
    )
    return summary_df


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh Open-Meteo daily weather CSVs.")
    parser.add_argument(
        "--weather-dir",
        type=Path,
        default=RAW_WEATHER_DIR,
        help="Directory containing per-district open-meteo-*.csv files.",
    )
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="Override today's date (YYYY-MM-DD) for reproducible runs.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    run_fetch(args.weather_dir, today=as_of)
