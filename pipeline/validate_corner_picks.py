"""Check logged corner picks against real corner counts and write docs/corners.json for the site.

Each picked game is under (11 corners or fewer), over (12+), pending, or void (postponed more than
VOID_AFTER_DAYS). A round is
    won      all picks under        (counts +1)
    lost     any pick over          (known as soon as one goes over)
    void     no pick over, but one was postponed for good
    pending  otherwise
It also checks the log itself and exits with an error (writing nothing) if something is wrong.

Usage:  python pipeline/validate_corner_picks.py [--now 2026-11-30T12:00:00Z]
"""
import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from corner_model import LEGS, MODEL_NAME, UNDER_LINE, UNDER_MAX, backtest, load_corner_results
from pick_model import kickoff_utc

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "corner_picks_log.csv"
OUT = ROOT / "docs" / "corners.json"
VOID_AFTER_DAYS = 14


def read_log(path):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check_log(log):
    """Return a list of problems found in the log."""
    problems, seen = [], set()
    for r in log:
        key = (r["season"], r["home"], r["away"])
        if key in seen:
            problems.append(f"duplicate game in corner log: {r['home']} v {r['away']} ({r['season']})")
        seen.add(key)

    batches = {}
    for r in log:
        batches.setdefault((r["model"], r["batch_id"]), []).append(r)
    for (model, bid), rows in batches.items():
        picked = [r for r in rows if r["picked"] == "1"]
        ranks = sorted(int(r["rank"]) for r in picked if r["rank"])
        if len(picked) != LEGS or ranks != list(range(1, LEGS + 1)):
            problems.append(f"corner round {bid} ({model}): expected picks ranked 1 to {LEGS}, "
                            f"found {len(picked)} picks, ranks {ranks}")
        for r in picked:
            announced = datetime.fromisoformat(r["announced_at"].replace("Z", "+00:00"))
            if announced >= kickoff_utc(date.fromisoformat(r["date"]), r["time"]):
                problems.append(f"corner round {bid}: {r['home']} v {r['away']} was announced after kickoff")
    return problems


def game_row(r, res):
    """One game of a round (picked or not) for the site, with its corner count once played."""
    corners = res.get((r["season"], r["home"], r["away"]))
    p = r["p_over25"]
    return {"date": r["date"], "time": r["time"], "home": r["home"], "away": r["away"],
            "p_over25": float(p) if p != "" else None, "picked": r["picked"] == "1",
            "result": "pending" if corners is None else ("under" if corners <= UNDER_MAX else "over"),
            "corners": corners}


def evaluate(log, results, now):
    res = {(m["season"], m["home"], m["away"]): m["corners"] for m in results}
    batches = {}
    for r in log:
        batches.setdefault((r["model"], r["batch_id"]), []).append(r)

    weeks = []
    for (model, bid), rows in batches.items():
        picks = []
        for r in sorted((r for r in rows if r["picked"] == "1"), key=lambda r: int(r["rank"])):
            kickoff = kickoff_utc(date.fromisoformat(r["date"]), r["time"])
            corners = res.get((r["season"], r["home"], r["away"]))
            if corners is not None:
                status = "under" if corners <= UNDER_MAX else "over"
            elif now > kickoff + timedelta(days=VOID_AFTER_DAYS):
                status = "void"
            else:
                status = "pending"
            picks.append({"date": r["date"], "time": r["time"], "home": r["home"], "away": r["away"],
                          "p_over25": float(r["p_over25"]), "result": status, "corners": corners})
        states = {p["result"] for p in picks}
        status = ("lost" if "over" in states else "void" if "void" in states
                  else "pending" if "pending" in states else "won")
        weeks.append({"id": bid, "model": model, "announced_at": rows[0]["announced_at"],
                      "status": status, "games_total": len(rows), "picks": picks,
                      "games": [game_row(r, res) for r in sorted(rows, key=lambda r: (r["date"], r["time"]))]})
    weeks.sort(key=lambda w: (w["picks"][0]["date"] if w["picks"] else "", w["announced_at"]), reverse=True)
    return weeks


def summarize(weeks):
    count = {s: sum(1 for w in weeks if w["status"] == s) for s in ("won", "lost", "pending", "void")}
    finished = count["won"] + count["lost"]
    return {"weeks_won": count["won"], "weeks_lost": count["lost"], "weeks_pending": count["pending"],
            "weeks_void": count["void"], "win_rate": round(count["won"] / finished, 3) if finished else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", help="override the current time for testing")
    args = ap.parse_args()
    now = (datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now
           else datetime.now(timezone.utc))

    log, results = read_log(LOG), load_corner_results()
    problems = check_log(log)
    if problems:
        for p in problems:
            print(f"ERROR: {p}", file=sys.stderr)
        return 1

    weeks = evaluate(log, results, now)
    out = {"generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "model": MODEL_NAME, "line": UNDER_LINE,
           "legs": LEGS, "summary": summarize(weeks), "backtest": backtest(results), "weeks": weeks}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    s, bt = out["summary"], out["backtest"]
    print(f"{len(weeks)} corner rounds logged: {s['weeks_won']} won, {s['weeks_lost']} lost, "
          f"{s['weeks_pending']} pending, {s['weeks_void']} void")
    for w in weeks:
        marks = " ".join({"under": "✓", "over": "✗", "pending": "·", "void": "-"}[p["result"]] for p in w["picks"])
        print(f"  {w['id']}: {w['status']:7} {marks}")
    if bt:
        print(f"Backtest over {bt['weeks']} weeks since {bt['since']}: {bt['model_weeks_won_pct']}% of weeks won "
              f"(random picks {bt['random_weeks_won_pct']}%); per game {bt['model_leg_hit_pct']}% "
              f"vs {bt['other_games_hit_pct']}% for the other games")
    return 0


if __name__ == "__main__":
    sys.exit(main())