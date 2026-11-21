"""Announce this round's corner picks: the 3 games with the lowest market chance of 3+ goals, each for under 11.5 corners.

Reads data/fixtures.csv (needs the over/under 2.5 odds columns), appends one row per game to
data/corner_picks_log.csv. Rows already in the log are never edited.

Usage:  python pipeline/make_corner_picks.py [--now 2026-11-27T10:00:00Z]
Exit codes: 0 = fine (announced, or nothing to announce), 1 = bad input
"""
import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from corner_model import LEGS, MIN_GAMES, MODEL_NAME, p_over25
from pick_model import kickoff_utc, parse_date, season_of
from update_results import LEAGUE

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "data" / "fixtures.csv"
LOG = ROOT / "data" / "corner_picks_log.csv"
LOG_FIELDS = ["batch_id", "model", "announced_at", "season", "date", "time",
              "home", "away", "p_over25", "rank", "picked"]


def read_log(log_path):
    if not Path(log_path).exists():
        return []
    with open(log_path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def announce(now, fixtures_path=FIXTURES, log_path=LOG):
    log = read_log(log_path)
    known = {(r["season"], r["home"], r["away"]) for r in log}

    if not Path(fixtures_path).exists():
        print("No fixtures file yet, nothing to announce")
        return "none"
    with open(fixtures_path, encoding="utf-8", newline="") as f:
        fixture_rows = [r for r in csv.DictReader(f) if (r.get("Div") or "").strip() == LEAGUE]

    games = []
    for r in fixture_rows:
        d = parse_date(r["Date"])
        g = {"date": d, "time": (r.get("Time") or "").strip(), "season": season_of(d),
             "home": r["HomeTeam"].strip(), "away": r["AwayTeam"].strip(), "p": p_over25(r)}
        if (g["season"], g["home"], g["away"]) in known:
            continue                                   # belongs to a round already announced
        g["kickoff"] = kickoff_utc(d, g["time"])
        games.append(g)

    with_odds = [g for g in games if g["p"] is not None]
    if len(with_odds) < MIN_GAMES:
        print(f"{len(with_odds)} new games with over/under 2.5 odds (need {MIN_GAMES}); nothing to announce")
        return "none"

    eligible = [g for g in with_odds if g["kickoff"] > now]
    if len(eligible) < MIN_GAMES:
        print(f"Only {len(eligible)} games with odds have not kicked off (need {MIN_GAMES}); skipping this round")
        return "skipped"

    ranked = sorted(eligible, key=lambda g: (g["p"], g["kickoff"], g["home"]))   # lowest chance of 3+ goals first
    for i, g in enumerate(ranked, start=1):
        g["rank"], g["picked"] = i, int(i <= LEGS)

    batch_id = min(g["date"] for g in games).isoformat()
    taken = {r["batch_id"] for r in log if r["model"] == MODEL_NAME}
    base, suffix = batch_id, 1
    while batch_id in taken:
        suffix += 1
        batch_id = f"{base}-{suffix}"

    announced_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    new_file = not Path(log_path).exists()
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS, lineterminator="\n")
        if new_file:
            w.writeheader()
        for g in sorted(games, key=lambda g: (g["kickoff"], g["home"])):
            w.writerow({"batch_id": batch_id, "model": MODEL_NAME, "announced_at": announced_at,
                        "season": g["season"], "date": g["date"].isoformat(), "time": g["time"],
                        "home": g["home"], "away": g["away"],
                        "p_over25": "" if g["p"] is None else round(g["p"], 4),
                        "rank": g.get("rank", ""), "picked": g.get("picked", 0)})

    print(f"Announced corner round {batch_id}: {len(games)} games, {LEGS} picks (all must finish under 11.5 corners)")
    for g in ranked[:LEGS]:
        print(f"  {g['rank']}. {g['home']} v {g['away']} ({g['date']:%d %b} {g['time']}): "
              f"market chance of 3+ goals {100 * g['p']:.1f}%")
    return "announced"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", help="override the current time for testing, e.g. 2026-11-27T10:00:00Z")
    args = ap.parse_args()
    now = (datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now
           else datetime.now(timezone.utc))
    try:
        announce(now)
    except (ValueError, KeyError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())