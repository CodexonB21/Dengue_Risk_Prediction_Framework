"""Module 1 raw data audit.

Read-only diagnostic script. Does not modify any files. Run this to get a
factual picture of the raw epidemiological and weather data before building
the preprocessing pipeline.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

EPI_PATH = RAW / "epidemiological" / "dengue_cases_corected.csv"
# All 25 canonical per-district weather CSVs live flat in this folder (the
# old "Weather (Except Humidity)/" and "Humidity/" subfolders were removed
# once the redundant Humidity/ source was confirmed and dropped).
WEATHER_DIR = RAW / "weather"


def district_from_filename(path: Path) -> str:
    stem = path.stem
    parts = stem.split(" ", 1)
    return parts[1].strip() if len(parts) > 1 else stem.strip()


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def audit_epi() -> pd.DataFrame:
    section("EPIDEMIOLOGICAL DATA")
    epi = pd.read_csv(EPI_PATH, encoding="utf-8-sig")
    print("Shape:", epi.shape)
    print("Columns:", list(epi.columns))
    print("Dtypes:\n", epi.dtypes)

    epi["Week_Start_Date"] = pd.to_datetime(epi["Week_Start_Date"])
    epi["Week_End_Date"] = pd.to_datetime(epi["Week_End_Date"])

    districts = sorted(epi["District"].unique())
    print(f"\nUnique districts ({len(districts)}):")
    print(districts)

    print("\nDate range:", epi["Week_Start_Date"].min(), "to", epi["Week_End_Date"].max())

    print("\nRow count per district (should be identical if no missing weeks):")
    print(epi["District"].value_counts().sort_index())

    print("\nMax epi-week number per year (years with 53 flagged):")
    wpy = epi.groupby("Year")["Week"].max()
    print(wpy.to_string())
    print("\nYears with 53 weeks:", list(wpy[wpy > 52].index))

    print("\nNegative case values:", int((epi["Number_of_Cases"] < 0).sum()))
    print(
        "Duplicate (District, Year, Week) rows:",
        int(epi.duplicated(subset=["District", "Year", "Week"]).sum()),
    )

    zero_pct = (
        epi.groupby("District")["Number_of_Cases"]
        .apply(lambda s: (s == 0).mean() * 100)
        .sort_values(ascending=False)
    )
    print("\nZero-case-week percentage per district (sorted, most sparse first):")
    print(zero_pct.round(1).to_string())

    print("\nOverall zero-case-week percentage (all districts pooled): "
          f"{(epi['Number_of_Cases'] == 0).mean() * 100:.1f}%")

    print("\nTotal cases and mean weekly cases per district:")
    stats = epi.groupby("District")["Number_of_Cases"].agg(["sum", "mean", "max"]).sort_values("sum", ascending=False)
    print(stats.round(1).to_string())

    return epi


def audit_weather() -> None:
    section("WEATHER FILES: INVENTORY")
    files = sorted(WEATHER_DIR.glob("*.csv"))
    file_map = {district_from_filename(f): f for f in files}

    print(f"Weather file count: {len(file_map)}")
    print("\nDistrict names parsed from weather filenames:")
    print(sorted(file_map.keys()))

    section("WEATHER FILES: COLUMN STRUCTURE CONSISTENCY")
    col_sigs = {}
    skip_used = {}
    for f in files:
        with open(f, "r", encoding="utf-8-sig") as fh:
            lines = [fh.readline() for _ in range(6)]
        header_line_idx = next(
            (i for i, l in enumerate(lines) if l.lower().startswith("time,")), None
        )
        skip_used[f.name] = header_line_idx
        if header_line_idx is None:
            continue
        df = pd.read_csv(f, skiprows=header_line_idx, nrows=3, encoding="utf-8-sig")
        col_sigs[f.name] = tuple(df.columns)
    unique_sigs = set(col_sigs.values())
    unique_skips = set(skip_used.values())
    print(f"\nHeader row index (0-based) found in: {unique_skips}")
    print(f"Unique column signatures: {len(unique_sigs)} across {len(files)} files")
    if len(unique_sigs) > 1:
        for sig in unique_sigs:
            matches = [f for f, s in col_sigs.items() if s == sig]
            print("  columns:", sig)
            print("  files:", matches)

    section("WEATHER FILES: SAMPLE DATE RANGE / GAP CHECK (Colombo)")
    f = file_map.get("Colombo")
    if f is not None:
        with open(f, "r", encoding="utf-8-sig") as fh:
            lines = [fh.readline() for _ in range(6)]
        header_idx = next(i for i, l in enumerate(lines) if l.lower().startswith("time,"))
        df = pd.read_csv(f, skiprows=header_idx, encoding="utf-8-sig")
        df["time"] = pd.to_datetime(df["time"])
        full_range = pd.date_range(df["time"].min(), df["time"].max(), freq="D")
        missing = full_range.difference(df["time"])
        dup_dates = df["time"].duplicated().sum()
        print(f"\nColombo file: {f.name}")
        print("  Row count:", len(df))
        print("  Date range:", df["time"].min().date(), "to", df["time"].max().date())
        print("  Missing calendar days within range:", len(missing))
        print("  Duplicate date rows:", int(dup_dates))

    section("WEATHER FILES: RAW HEADER BYTES (encoding check)")
    if f is not None:
        with open(f, "rb") as fh:
            raw_lines = [fh.readline() for _ in range(5)]
        print(f"\n{f.name} raw bytes (first 5 lines):")
        for rl in raw_lines:
            print(" ", rl)


def audit_district_alignment(epi: pd.DataFrame) -> None:
    section("DISTRICT NAME ALIGNMENT: CASE DATA vs WEATHER FILES")
    files = sorted(WEATHER_DIR.glob("*.csv"))
    full_districts = {district_from_filename(f) for f in files}
    epi_districts = set(epi["District"].unique())

    norm = lambda s: s.strip().lower()
    epi_norm = {norm(d): d for d in epi_districts}
    full_norm = {norm(d): d for d in full_districts}

    print(f"Epi districts: {len(epi_districts)} | Weather districts: {len(full_districts)}")

    unmatched_epi = sorted(set(epi_norm) - set(full_norm))
    unmatched_weather = sorted(set(full_norm) - set(epi_norm))

    print("\nEpi districts with NO matching weather file (case-insensitive):")
    print([epi_norm[k] for k in unmatched_epi])
    print("\nWeather files with NO matching epi district (case-insensitive):")
    print([full_norm[k] for k in unmatched_weather])


def main() -> None:
    epi = audit_epi()
    audit_weather()
    audit_district_alignment(epi)


if __name__ == "__main__":
    main()
