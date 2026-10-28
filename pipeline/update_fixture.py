"""Download the upcoming-fixtures file from football-data.co.uk, keep only the
Premier League (E0) rows that haven't been played yet, and save them to
data/fixtures.csv.

Usage (from anywhere):  python pipeline/update_fixtures.py

The site's file only ever lists the next round of matches, refreshed about
Friday (weekend games) and Tuesday (midweek games). An empty result is normal
during international breaks and the off-season, so it is not an error.

Exit codes:
  0  ok: updated, unchanged, or no upcoming matches
  1  the download failed or the file doesn't look like a fixtures file
"""
import csv
import io
import sys
from pathlib import Path

from update_results import ALPHA_SOURCE, LEAGUE, NotPublished, current_season, download

FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"
REQUIRED_COLUMNS = ["Div", "Date", "Time", "HomeTeam", "AwayTeam"]
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def read_fixtures(raw):
    """Return (column names, E0 rows) from the raw fixtures download."""
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    fields = [f for f in (reader.fieldnames or []) if f]
    missing = [c for c in REQUIRED_COLUMNS if c not in fields]
    if missing:
        raise ValueError(f"fixtures file is missing expected columns: {missing}")
    rows = [
        r
        for r in reader
        if (r.get("Div") or "").strip() == LEAGUE
        and (r.get("HomeTeam") or "").strip()
    ]
    return fields, rows


def read_results(results_path):
    """Return (played, teams) from the season results file.

    played: set of (home, away) pairs that already have a result.
    teams:  every team name that appears in the file.
    """
    played, teams = set(), set()
    if not Path(results_path).exists():
        return played, teams
    with open(results_path, encoding="utf-8-sig", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            home = (r.get("HomeTeam") or "").strip()
            away = (r.get("AwayTeam") or "").strip()
            if not home:
                continue
            teams.update([home, away])
            if (r.get("FTR") or "").strip():  # has a result = already played
                played.add((home, away))
    return played, teams


def update_fixtures(results_path, out_dir=DATA_DIR, fetch=download):
    try:
        raw = fetch(FIXTURES_URL)
    except NotPublished:
        raise RuntimeError(f"fixtures file not found at {FIXTURES_URL}")

    fields, rows = read_fixtures(raw)
    played, teams = read_results(results_path)

    upcoming = [
        r for r in rows
        if ((r["HomeTeam"].strip(), r["AwayTeam"].strip())) not in played
    ]

    if teams:  # only meaningful once the season has some results
        unknown = sorted(
            {r[k].strip() for r in upcoming for k in ("HomeTeam", "AwayTeam")} - teams
        )
        for name in unknown:
            print(f"WARNING: fixture team '{name}' not found in results data; "
                  "check the spelling or add it to a name mapping")

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore",
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(upcoming)
    new_text = buf.getvalue()

    dest = Path(out_dir) / "fixtures.csv"
    summary = (f"fixtures: {len(rows)} {LEAGUE} rows in download, "
               f"{len(rows) - len(upcoming)} already played, "
               f"{len(upcoming)} upcoming")

    if dest.exists() and dest.read_text(encoding="utf-8") == new_text:
        print(f"{summary} (unchanged)")
        return "unchanged"

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(new_text, encoding="utf-8")
    print(f"{summary} (written to {dest.name})")
    return "updated"


def main():
    season, _ = current_season()
    try:
        update_fixtures(ALPHA_SOURCE / f"{season}.csv")
    except (ValueError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())