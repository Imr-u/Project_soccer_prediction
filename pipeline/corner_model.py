"""Corner picks: each round, the LEGS games with the lowest market chance of 3+ goals, each for under 11.5 corners.

The market chance of 3+ goals comes from the over/under 2.5 goal odds with the bookmaker's margin removed
(low = few goals expected). A round (a "week") is won only if EVERY pick finishes under 11.5 corners
(11 or fewer). Shared by make_corner_picks.py and validate_corner_picks.py.
"""
import csv
import math
from pathlib import Path

from pick_model import parse_date
from update_results import ALPHA_SOURCE

MODEL_NAME = "corners-v1"
UNDER_LINE = 11.5
UNDER_MAX = 11            # under 11.5 corners means 11 or fewer
LEGS = 3                  # games picked per round; the round is won only if all of them finish under
MIN_GAMES = 8             # rounds with fewer games (that have odds) than this are not used
OVER_COLS = ["Avg>2.5", "B365>2.5"]     # the first column with a value is used
UNDER_COLS = ["Avg<2.5", "B365<2.5"]


def _first_odds(row, columns):
    for c in columns:
        try:
            v = float((row.get(c) or "").strip())
        except ValueError:
            continue
        if v > 1:
            return v
    return None


def p_over25(row):
    """Chance of 3+ goals from the over/under 2.5 odds with the margin removed. None if the odds are missing."""
    over, under = _first_odds(row, OVER_COLS), _first_odds(row, UNDER_COLS)
    if over is None or under is None:
        return None
    return (1 / over) / (1 / over + 1 / under)


def load_corner_results(alpha_source=ALPHA_SOURCE):
    """Every match with corners (HC + AC) and its market chance of 3+ goals, oldest first."""
    rows = []
    for path in sorted(Path(alpha_source).glob("*.csv")):
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            for r in csv.DictReader(f):
                home, away = (r.get("HomeTeam") or "").strip(), (r.get("AwayTeam") or "").strip()
                try:
                    corners = int(float(r["HC"])) + int(float(r["AC"]))
                    day = parse_date(r["Date"])
                except (KeyError, TypeError, ValueError):
                    continue          # blank, unplayed or incomplete row
                if not home or not away:
                    continue
                rows.append({"season": path.stem, "date": day, "home": home, "away": away,
                             "corners": corners, "p_over25": p_over25(r)})
    rows.sort(key=lambda m: m["date"])
    return rows


def backtest(results):
    """Replay the rule over every past week that has at least MIN_GAMES games with odds.

    A week = a run of match days with no gap of 2+ days. The rule has no fitted numbers, but it was found
    by looking at this same data, so the replay flatters it a little.
    """
    weeks, week, prev = {}, 0, None
    for m in results:
        if prev is not None and (m["date"] - prev).days >= 2:
            week += 1
        prev = m["date"]
        weeks.setdefault(week, []).append(m)

    n_weeks = won = pick_hits = pick_n = rest_hits = rest_n = 0
    rand_won, first_season = 0.0, None
    for games in weeks.values():
        with_odds = [m for m in games if m["p_over25"] is not None]
        if len(with_odds) < MIN_GAMES:
            continue
        with_odds.sort(key=lambda m: m["p_over25"])          # stable: ties keep date order
        picks, rest = with_odds[:LEGS], with_odds[LEGS:]
        hits = [m["corners"] <= UNDER_MAX for m in picks]
        n_weeks += 1
        won += all(hits)
        pick_hits += sum(hits)
        pick_n += LEGS
        rest_hits += sum(m["corners"] <= UNDER_MAX for m in rest)
        rest_n += len(rest)
        u = sum(m["corners"] <= UNDER_MAX for m in with_odds)
        rand_won += math.comb(u, LEGS) / math.comb(len(with_odds), LEGS)    # random picks, all legs hit
        first_season = first_season or with_odds[0]["season"]
    if not n_weeks:
        return None
    return {"since": first_season, "weeks": n_weeks,
            "model_weeks_won_pct": round(100 * won / n_weeks, 1),
            "random_weeks_won_pct": round(100 * rand_won / n_weeks, 1),
            "model_leg_hit_pct": round(100 * pick_hits / pick_n, 1),
            "other_games_hit_pct": round(100 * rest_hits / rest_n, 1)}