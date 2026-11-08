"""Check logged picks against real results and write docs/picks.json for the site.

For each announced round: every picked game is under (4 goals or fewer), over (5+), pending, or void
(postponed more than VOID_AFTER_DAYS). A round is
    won      all 5 picks under        (counts +1)
    lost     any pick over            (known as soon as one goes over)
    void     no pick over, but one was postponed for good
    pending  otherwise
It also checks the log itself and exits with an error (writing nothing) if something is wrong.

Usage:  python pipeline/validate_picks.py
"""
import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pick_model import MODEL_NAME, PICKS, UNDER_MAX, backtest, kickoff_utc, load_results

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "picks_log.csv"
OUT = ROOT / "docs" / "picks.json"
VOID_AFTER_DAYS = 14


def read_log(path):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check_log(log):
    """Return a list of problems found in the log."""
    problems = []
    seen = set()
    for r in log:
        key = (r["season"], r["home"], r["away"])
        if key in seen:
            problems.append(f"duplicate game in log: {r['home']} v {r['away']} ({r['season']})")
        seen.add(key)

    batches = {}
    for r in log:
        batches.setdefault((r["model"], r["batch_id"]), []).append(r)
    for (model, bid), rows in batches.items():
        picked = [r for r in rows if r["picked"] == "1"]
        ranks = sorted(int(r["rank"]) for r in picked if r["rank"])
        if len(picked) != PICKS or ranks != list(range(1, PICKS + 1)):
            problems.append(f"round {bid} ({model}): expected picks ranked 1 to {PICKS}, found {len(picked)} picks, ranks {ranks}")
        for r in picked:
            announced = datetime.fromisoformat(r["announced_at"].replace("Z", "+00:00"))
            if announced >= kickoff_utc(date.fromisoformat(r["date"]), r["time"]):
                problems.append(f"round {bid}: {r['home']} v {r['away']} was announced after kickoff")
    return problems


def evaluate(log, results, now):
    res = {(m["season"], m["home"], m["away"]): (m["hg"], m["ag"]) for m in results}
    batches = {}
    for r in log:
        batches.setdefault((r["model"], r["batch_id"]), []).append(r)

    weeks = []
    for (model, bid), rows in batches.items():
        picks = []
        for r in sorted((r for r in rows if r["picked"] == "1"), key=lambda r: int(r["rank"])):
            kickoff = kickoff_utc(date.fromisoformat(r["date"]), r["time"])
            got = res.get((r["season"], r["home"], r["away"]))
            if got:
                status, score = ("under" if sum(got) <= UNDER_MAX else "over"), f"{got[0]}-{got[1]}"
            elif now > kickoff + timedelta(days=VOID_AFTER_DAYS):
                status, score = "void", None
            else:
                status, score = "pending", None
            picks.append({"date": r["date"], "time": r["time"], "home": r["home"], "away": r["away"],
                          "exp_goals": float(r["exp_goals"]), "p_under": float(r["p_under"]),
                          "result": status, "score": score})
        states = {p["result"] for p in picks}
        status = ("lost" if "over" in states else "void" if "void" in states
                  else "pending" if "pending" in states else "won")
        weeks.append({"id": bid, "model": model, "announced_at": rows[0]["announced_at"],
                      "status": status, "games_total": len(rows), "picks": picks})
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

    log, results = read_log(LOG), load_results()
    problems = check_log(log)
    if problems:
        for p in problems:
            print(f"ERROR: {p}", file=sys.stderr)
        return 1

    weeks = evaluate(log, results, now)
    out = {"generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "model": MODEL_NAME, "line": 4.5, "picks_per_week": PICKS,
           "summary": summarize(weeks), "backtest": backtest(results), "weeks": weeks}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    s = out["summary"]
    print(f"{len(weeks)} rounds logged: {s['weeks_won']} won, {s['weeks_lost']} lost, "
          f"{s['weeks_pending']} pending, {s['weeks_void']} void")
    for w in weeks:
        marks = " ".join({"under": "✓", "over": "✗", "pending": "·", "void": "-"}[p["result"]] for p in w["picks"])
        print(f"  {w['id']}: {w['status']:7} {marks}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
