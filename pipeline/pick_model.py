"""Baseline pick model and helpers shared by make_picks.py and validate_picks.py.

The model: expected total goals for a match is
    (home attack + away defence) / 2  +  (away attack + home defence) / 2
where each team's attack/defence is its average goals scored/conceded in ALL its earlier
matches, pulled toward the league average as if backed by SHRINK_K extra average matches.
Lower expected goals = safer pick for "under 4.5".
"""
import csv
import math
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from update_results import ALPHA_SOURCE

MODEL_NAME = "baseline-v1"
LINE = 4.5
UNDER_MAX = 4          # "under 4.5" means 4 goals or fewer
PICKS = 5              # games picked per round
MIN_GAMES = 8          # rounds with fewer games than this are not announced
SHRINK_K = 5
LEAGUE_AVG_START = 1.45
LONDON = ZoneInfo("Europe/London")   # fixture times are UK local time


def parse_date(text):
    text = text.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unrecognised date: {text!r}")


def season_of(d):
    """Seasons start in August: 2026-11-07 -> '2026-2027'."""
    start = d.year if d.month >= 8 else d.year - 1
    return f"{start}-{start + 1}"


def kickoff_utc(d, time_text):
    """Kickoff as a UTC datetime from a date and a 'HH:MM' UK time (00:00 if the time is missing)."""
    try:
        hh, mm = (int(x) for x in (time_text or "").strip().split(":")[:2])
    except ValueError:
        hh, mm = 0, 0
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=LONDON).astimezone(timezone.utc)


def poisson_cdf(k, lam):
    return sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k + 1))


def load_results(alpha_source=ALPHA_SOURCE):
    """Every played match, oldest first."""
    rows = []
    for path in sorted(Path(alpha_source).glob("*.csv")):
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            for r in csv.DictReader(f):
                home = (r.get("HomeTeam") or "").strip()
                try:
                    hg, ag = int(float(r["FTHG"])), int(float(r["FTAG"]))
                except (KeyError, TypeError, ValueError):
                    continue          # blank or unplayed row
                if not home:
                    continue
                rows.append({"season": path.stem, "date": parse_date(r["Date"]), "home": home,
                             "away": r["AwayTeam"].strip(), "hg": hg, "ag": ag})
    rows.sort(key=lambda m: m["date"])
    return rows


class RatingState:
    """Running record of each team's goals scored/conceded. Feed matches in date order."""

    def __init__(self):
        self.hist = {}
        self.total_goals = 0
        self.matches = 0

    @property
    def league_avg(self):
        return self.total_goals / (2 * self.matches) if self.matches else LEAGUE_AVG_START

    def add(self, m):
        self.hist.setdefault(m["home"], []).append((m["hg"], m["ag"]))
        self.hist.setdefault(m["away"], []).append((m["ag"], m["hg"]))
        self.total_goals += m["hg"] + m["ag"]
        self.matches += 1

    def _averages(self, team):
        h = self.hist.get(team, [])
        n, K, avg = len(h), SHRINK_K, self.league_avg
        return ((sum(s for s, c in h) + K * avg) / (n + K),
                (sum(c for s, c in h) + K * avg) / (n + K))

    def expected_goals(self, home, away):
        scored_h, conceded_h = self._averages(home)
        scored_a, conceded_a = self._averages(away)
        return (scored_h + conceded_a) / 2 + (scored_a + conceded_h) / 2


def backtest(results, from_season="2022-2023"):
    """Replay the method over past weeks (each prediction uses only earlier matches).

    A week = a run of match days with no gap of 2+ days. Weeks with fewer than MIN_GAMES games are skipped.
    """
    state, rows, week, prev = RatingState(), [], 0, None
    for m in results:
        if prev is not None and (m["date"] - prev).days >= 2:
            week += 1
        prev = m["date"]
        rows.append({**m, "week": week, "exp": state.expected_goals(m["home"], m["away"])})
        state.add(m)

    by_week = {}
    for r in rows:
        by_week.setdefault(r["week"], []).append(r)

    weeks = won = 0
    picked_under = picked_total = 0
    rand_won = rand_under = 0.0
    for games in by_week.values():
        if len(games) < MIN_GAMES or games[0]["season"] < from_season:
            continue
        n = len(games)
        u = sum(1 for g in games if g["hg"] + g["ag"] <= UNDER_MAX)
        best = sorted(games, key=lambda g: g["exp"])[:PICKS]
        k = sum(1 for g in best if g["hg"] + g["ag"] <= UNDER_MAX)
        weeks += 1
        won += k == PICKS
        picked_under += k
        picked_total += PICKS
        rand_won += math.comb(u, PICKS) / math.comb(n, PICKS)
        rand_under += u / n
    if not weeks:
        return None
    return {"since": from_season, "weeks": weeks,
            "model_weeks_won_pct": round(100 * won / weeks, 1),
            "random_weeks_won_pct": round(100 * rand_won / weeks, 1),
            "model_picks_under_pct": round(100 * picked_under / picked_total, 1),
            "random_picks_under_pct": round(100 * rand_under / weeks, 1)}
