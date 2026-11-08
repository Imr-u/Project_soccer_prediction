"""Announce this round's picks: the 5 safest games (lowest expected goals) among games not yet kicked off.

Reads data/fixtures.csv, appends one row per game to data/picks_log.csv. Rows already in the log are
never edited, so a round can't be redone after the results are known.

Usage:  python pipeline/make_picks.py
Exit codes: 0 = fine (announced, or nothing to announce), 1 = bad input
"""
import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from pick_model import (MIN_GAMES, MODEL_NAME, PICKS, UNDER_MAX, RatingState, kickoff_utc,
                        load_results, parse_date, poisson_cdf, season_of)
from update_results import LEAGUE

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "data" / "fixtures.csv"
LOG = ROOT / "data" / "picks_log.csv"
LOG_FIELDS = ["batch_id", "model", "announced_at", "season", "date", "time",
              "home", "away", "exp_goals", "p_under", "rank", "picked"]


def read_log(log_path):
    if not Path(log_path).exists():
        return []
    with open(log_path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def announce(now, fixtures_path=FIXTURES, log_path=LOG, results=None):
    results = load_results() if results is None else results
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
             "home": r["HomeTeam"].strip(), "away": r["AwayTeam"].strip()}
        if (g["season"], g["home"], g["away"]) in known:
            continue                                  # belongs to a round already announced
        g["kickoff"] = kickoff_utc(d, g["time"])
        games.append(g)

    if len(games) < MIN_GAMES:
        print(f"{len(games)} new games in the fixtures file (need {MIN_GAMES}); nothing to announce")
        return "none"

    eligible = [g for g in games if g["kickoff"] > now]
    if len(eligible) < PICKS:
        print(f"Only {len(eligible)} of {len(games)} games have not kicked off; skipping this round")
        return "skipped"

    state = RatingState()
    for m in results:
        state.add(m)
    for g in games:
        g["exp"] = state.expected_goals(g["home"], g["away"])
        g["p"] = poisson_cdf(UNDER_MAX, g["exp"])

    ranked = sorted(eligible, key=lambda g: (g["exp"], g["kickoff"], g["home"]))
    for i, g in enumerate(ranked, start=1):
        g["rank"], g["picked"] = i, int(i <= PICKS)

    batch_id = min(g["date"] for g in games).isoformat()
    taken = {r["batch_id"] for r in log if r["model"] == MODEL_NAME}
    suffix, base = 1, batch_id
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
                        "home": g["home"], "away": g["away"], "exp_goals": round(g["exp"], 3),
                        "p_under": round(g["p"], 4), "rank": g.get("rank", ""), "picked": g.get("picked", 0)})

    print(f"Announced round {batch_id}: {len(games)} games, {PICKS} picks")
    for g in ranked[:PICKS]:
        print(f"  {g['rank']}. {g['home']} v {g['away']} ({g['date']:%d %b} {g['time']}): "
              f"{g['exp']:.2f} expected goals, {100 * g['p']:.1f}% under 4.5")
    return "announced"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", help="override the current time for testing, e.g. 2026-11-07T10:00:00Z")
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
