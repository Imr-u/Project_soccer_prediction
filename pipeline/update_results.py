"""Download the current season's Premier League results from football-data.co.uk
and overwrite alpha_source/<season>.csv with the fresh copy.

Usage (from anywhere):  python pipeline/update_results.py

Exit codes:
  0  ok: updated, unchanged, or the new season's file isn't published yet
  1  something looks wrong; nothing was written
"""
import csv
import io
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

BASE_URL = "https://www.football-data.co.uk/mmz4281/{code}/{league}.csv"
LEAGUE = "E0"  # Premier League
REQUIRED_COLUMNS = ["Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]
ALPHA_SOURCE = Path(__file__).resolve().parent.parent / "alpha_source"


class NotPublished(Exception):
    """The season file doesn't exist on the site (HTTP 404)."""


def current_season(today=None):
    """Seasons start in August. Returns ("2026-2027", "2627") for Oct 2026."""
    today = today or date.today()
    start = today.year if today.month >= 8 else today.year - 1
    return f"{start}-{start + 1}", f"{start % 100:02d}{(start + 1) % 100:02d}"


def download(url, retries=3):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (soccer-prediction-updater)"}
    )
    err = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:  # must come before URLError
            if e.code == 404:
                raise NotPublished(url) from e
            err = e
        except (urllib.error.URLError, TimeoutError) as e:
            err = e
        if attempt < retries:
            time.sleep(5 * attempt)
    raise RuntimeError(f"download failed after {retries} tries: {err}")


def parse(raw):
    """Validate a results CSV and return its match rows (blank rows dropped)."""
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"missing expected columns: {missing}")
    rows = [r for r in reader if (r.get("HomeTeam") or "").strip()]
    wrong_div = [r for r in rows if (r.get("Div") or "").strip() != LEAGUE]
    if wrong_div:
        raise ValueError(f"{len(wrong_div)} rows are not league {LEAGUE}")
    return rows


def update_season(season, code, dest_dir=ALPHA_SOURCE, fetch=download):
    url = BASE_URL.format(code=code, league=LEAGUE)
    dest = Path(dest_dir) / f"{season}.csv"

    try:
        raw = fetch(url)
    except NotPublished:
        print(f"{season}: not published yet ({url}), skipping")
        return "not_published"

    new_rows = parse(raw)
    old_n = len(parse(dest.read_bytes())) if dest.exists() else 0

    if not new_rows and old_n == 0:
        print(f"{season}: file has no matches yet, skipping")
        return "no_matches_yet"
    if len(new_rows) < old_n:
        raise ValueError(
            f"download has {len(new_rows)} matches but the repo already has "
            f"{old_n}; refusing to overwrite"
        )
    if dest.exists() and dest.read_bytes() == raw:
        print(f"{season}: unchanged ({old_n} matches)")
        return "unchanged"

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)  # raw bytes: file stays identical to the original
    print(f"{season}: {old_n} -> {len(new_rows)} matches")
    return "updated"


def main():
    season, code = current_season()
    try:
        update_season(season, code)
    except (ValueError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())