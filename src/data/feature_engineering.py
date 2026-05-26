import bisect
import json
import logging
import os
from collections import defaultdict

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RAW = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw"))
PROCESSED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed"))

# CSV names → canonical API names
TEAM_ALIASES = {
    "Korea Republic": "South Korea",
    "Czech Republic": "Czechia",
    "USA": "United States",
    "DR Congo": "Congo DR",
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Cape Verde": "Cape Verde Islands",
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "Curacao": "Curaçao",
    "Trinidad and Tobago": "Trinidad and Tobago",
    "Trinidad & Tobago": "Trinidad and Tobago",
}

# FIFA rankings for WC 2026 teams (Italy #13 no clasificó → Morocco pasa a ser 14 entre WC teams)
FIFA_RANKINGS = {
    "Argentina": 1, "France": 2, "Brazil": 3, "England": 4, "Portugal": 5,
    "Spain": 6, "Netherlands": 7, "Belgium": 8, "Colombia": 9, "Germany": 10,
    "Uruguay": 11, "Croatia": 12, "Morocco": 14, "Japan": 15,
    "United States": 16, "Mexico": 17, "Ecuador": 18, "Turkey": 19, "Iran": 20,
    "South Korea": 21, "Australia": 22, "Austria": 23, "Switzerland": 24,
    "Sweden": 25, "Scotland": 26, "Norway": 27, "Congo DR": 28, "Egypt": 29,
    "Senegal": 30, "Tunisia": 31, "Algeria": 32, "Iraq": 33, "Saudi Arabia": 34,
    "Ivory Coast": 35, "Canada": 36, "Qatar": 37, "Jordan": 38, "Uzbekistan": 39,
    "Ghana": 40, "Paraguay": 41, "Panama": 42, "South Africa": 43,
    "Bosnia-Herzegovina": 44, "New Zealand": 45, "Haiti": 46,
    "Curaçao": 47, "Cape Verde Islands": 48,
}

DEFAULT_RANKING = 60  # equipos no clasificados al mundial

FEATURE_COLS = [
    "win_rate", "draw_rate", "goals_scored_avg", "goals_conceded_avg",
    "clean_sheet_rate", "goal_diff_avg", "form_last5",
]

META_COLS = {"home_team", "away_team", "date", "result", "match_id", "stage", "matchday"}

# Palabras clave para inferir is_group_stage en datos históricos
GROUP_STAGE_KEYWORDS = (
    "World Cup", "Euro", "Copa Am", "African Cup", "AFCON",
    "Asian Cup", "Gold Cup", "Nations League",
)


def normalize_name(name: str) -> str:
    return TEAM_ALIASES.get(name, name)


def load_results() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(RAW, "results.csv"), parse_dates=["date"])
    df["home_team_norm"] = df["home_team"].map(normalize_name)
    df["away_team_norm"] = df["away_team"].map(normalize_name)
    return df


def build_team_history(df: pd.DataFrame) -> dict:
    """
    Devuelve dict: team → lista ordenada de (date, goals_for, goals_against, result).
    """
    records: dict = defaultdict(list)

    for row in df.itertuples(index=False):
        if pd.isna(row.home_score) or pd.isna(row.away_score):
            continue
        hs, as_ = int(row.home_score), int(row.away_score)
        date = row.date
        home, away = row.home_team_norm, row.away_team_norm

        if hs > as_:
            h_res, a_res = "W", "L"
        elif hs < as_:
            h_res, a_res = "L", "W"
        else:
            h_res = a_res = "D"

        records[home].append((date, hs, as_, h_res))
        records[away].append((date, as_, hs, a_res))

    for team in records:
        records[team].sort(key=lambda x: x[0])

    return dict(records)


def build_h2h_index(df: pd.DataFrame) -> dict:
    """
    Devuelve dict: (min_team, max_team) → lista ordenada de
    (date, equipo_que_jugó_de_local, goles_local, goles_visitante).
    """
    h2h: dict = defaultdict(list)

    for row in df.itertuples(index=False):
        if pd.isna(row.home_score) or pd.isna(row.away_score):
            continue
        t1, t2 = row.home_team_norm, row.away_team_norm
        key = (min(t1, t2), max(t1, t2))
        h2h[key].append((row.date, t1, int(row.home_score), int(row.away_score)))

    for key in h2h:
        h2h[key].sort(key=lambda x: x[0])

    return dict(h2h)


def compute_rolling_features(matches: list) -> dict | None:
    if not matches:
        return None
    n = len(matches)
    goals_scored = [gs for _, gs, _, _ in matches]
    goals_conceded = [gc for _, _, gc, _ in matches]
    wins = sum(1 for _, _, _, r in matches if r == "W")
    draws = sum(1 for _, _, _, r in matches if r == "D")
    last5 = matches[-5:]
    form = sum(3 if r == "W" else 1 if r == "D" else 0 for _, _, _, r in last5)
    return {
        "win_rate": wins / n,
        "draw_rate": draws / n,
        "goals_scored_avg": sum(goals_scored) / n,
        "goals_conceded_avg": sum(goals_conceded) / n,
        "clean_sheet_rate": sum(1 for gc in goals_conceded if gc == 0) / n,
        "goal_diff_avg": (sum(goals_scored) - sum(goals_conceded)) / n,
        "form_last5": form / 15,
    }


def get_hist_features(team: str, before_date, team_history: dict, n: int = 20) -> dict | None:
    matches = team_history.get(team, [])
    if not matches:
        return None
    dates = [m[0] for m in matches]
    idx = bisect.bisect_left(dates, before_date)
    return compute_rolling_features(matches[max(0, idx - n): idx])


def get_recent_features(team_name: str, recent_data: dict) -> dict | None:
    """Extrae features del team_recent_matches.json (datos más actuales para predicción)."""
    for info in recent_data.values():
        if info["team_name"] != team_name:
            continue
        finished = []
        for m in info.get("matches", []):
            if m.get("status") != "FINISHED":
                continue
            ft = m.get("score", {}).get("fullTime", {})
            hs, as_ = ft.get("home"), ft.get("away")
            if hs is None or as_ is None:
                continue
            is_home = m.get("homeTeam", {}).get("name") == team_name
            gs, gc = (hs, as_) if is_home else (as_, hs)
            res = ("W" if gs > gc else ("D" if gs == gc else "L"))
            finished.append((pd.to_datetime(m["utcDate"][:10]), gs, gc, res))
        finished.sort(key=lambda x: x[0])
        return compute_rolling_features(finished[-20:])
    return None


def get_h2h(home: str, away: str, before_date, h2h_index: dict) -> dict:
    key = (min(home, away), max(home, away))
    records = h2h_index.get(key, [])
    ten_years_ago = before_date - pd.Timedelta(days=3650)
    relevant = [r for r in records if ten_years_ago <= r[0] < before_date]

    home_wins = draws = away_wins = 0
    for _, rec_home, hs, as_ in relevant:
        if rec_home == home:
            if hs > as_: home_wins += 1
            elif hs < as_: away_wins += 1
            else: draws += 1
        else:
            if hs > as_: away_wins += 1
            elif hs < as_: home_wins += 1
            else: draws += 1

    return {"h2h_home_wins": home_wins, "h2h_away_wins": away_wins, "h2h_draws": draws}


def assemble_row(home: str, away: str, hf: dict, af: dict, h2h: dict,
                 rank_h: int, rank_a: int, is_group: int) -> dict:
    row = {f"home_{k}": v for k, v in hf.items()}
    row.update({f"away_{k}": v for k, v in af.items()})
    row["diff_win_rate"] = hf["win_rate"] - af["win_rate"]
    row["diff_goals_avg"] = hf["goals_scored_avg"] - af["goals_scored_avg"]
    row.update(h2h)
    row["home_ranking"] = rank_h
    row["away_ranking"] = rank_a
    row["ranking_diff"] = rank_h - rank_a  # negativo = home mejor rankeado
    row["is_group_stage"] = is_group
    return row


def fill_nulls(df: pd.DataFrame, medians: pd.Series | None = None) -> tuple:
    num_cols = [c for c in df.columns if c not in META_COLS]
    if medians is None:
        medians = df[num_cols].median()
    df[num_cols] = df[num_cols].fillna(medians)
    return df, medians


def main():
    os.makedirs(PROCESSED, exist_ok=True)

    logger.info("Cargando datos raw...")
    results_df = load_results()

    with open(os.path.join(RAW, "wc_teams.json"), encoding="utf-8") as f:
        wc_teams_raw = json.load(f).get("teams", [])
    with open(os.path.join(RAW, "wc_matches.json"), encoding="utf-8") as f:
        wc_matches_raw = json.load(f).get("matches", [])
    with open(os.path.join(RAW, "team_recent_matches.json"), encoding="utf-8") as f:
        recent_data = json.load(f)

    wc_teams = {normalize_name(t["name"]) for t in wc_teams_raw}

    # ── Verificar cobertura de nombres ───────────────────────────────────────
    all_hist = set(results_df["home_team_norm"]) | set(results_df["away_team_norm"])
    unmatched_wc = wc_teams - all_hist
    if unmatched_wc:
        logger.warning("Equipos WC sin historial en CSV (se imputará mediana): %s", unmatched_wc)
    else:
        logger.info("Todos los equipos WC tienen historial en CSV.")

    logger.info("Construyendo índices (team_history + H2H)...")
    team_history = build_team_history(results_df)
    h2h_index = build_h2h_index(results_df)

    # ── TRAINING DATA ─────────────────────────────────────────────────────────
    logger.info("Construyendo training dataset...")

    train_mask = (
        (results_df["date"].dt.year >= 2015)
        & (
            results_df["home_team_norm"].isin(wc_teams)
            | results_df["away_team_norm"].isin(wc_teams)
        )
        & results_df["home_score"].notna()
        & results_df["away_score"].notna()
    )
    train_df = results_df[train_mask]
    logger.info("Partidos de training (2015+, ≥1 equipo WC): %d", len(train_df))

    null_hist_teams: set = set()
    train_rows = []
    null_feat = {k: np.nan for k in FEATURE_COLS}

    for row in train_df.itertuples(index=False):
        home, away, date = row.home_team_norm, row.away_team_norm, row.date

        hf = get_hist_features(home, date, team_history)
        af = get_hist_features(away, date, team_history)

        if hf is None: null_hist_teams.add(home)
        if af is None: null_hist_teams.add(away)

        hf = hf or null_feat.copy()
        af = af or null_feat.copy()

        h2h = get_h2h(home, away, date, h2h_index)
        rh = FIFA_RANKINGS.get(home, DEFAULT_RANKING)
        ra = FIFA_RANKINGS.get(away, DEFAULT_RANKING)

        tournament = getattr(row, "tournament", "")
        is_group = 1 if any(kw in tournament for kw in GROUP_STAGE_KEYWORDS) else 0

        r = assemble_row(home, away, hf, af, h2h, rh, ra, is_group)
        hs, as_ = int(row.home_score), int(row.away_score)
        r["result"] = 1 if hs > as_ else (0 if hs == as_ else 2)
        r["home_team"] = home
        r["away_team"] = away
        r["date"] = date
        train_rows.append(r)

    training_data = pd.DataFrame(train_rows)
    training_data, train_medians = fill_nulls(training_data)

    # ── PREDICTION DATA (WC 2026) ─────────────────────────────────────────────
    logger.info("Construyendo prediction dataset (104 partidos WC)...")

    today = pd.Timestamp.now().normalize()
    pred_rows = []

    for match in wc_matches_raw:
        home = normalize_name(match.get("homeTeam", {}).get("name", ""))
        away = normalize_name(match.get("awayTeam", {}).get("name", ""))
        if not home or not away:
            continue

        hf = get_recent_features(home, recent_data) or get_hist_features(home, today, team_history)
        af = get_recent_features(away, recent_data) or get_hist_features(away, today, team_history)

        hf = hf or null_feat.copy()
        af = af or null_feat.copy()

        h2h = get_h2h(home, away, today, h2h_index)
        rh = FIFA_RANKINGS.get(home, DEFAULT_RANKING)
        ra = FIFA_RANKINGS.get(away, DEFAULT_RANKING)

        stage = match.get("stage", "")
        is_group = 1 if stage == "GROUP_STAGE" else 0

        r = assemble_row(home, away, hf, af, h2h, rh, ra, is_group)
        r["match_id"] = match.get("id")
        r["home_team"] = home
        r["away_team"] = away
        r["date"] = match.get("utcDate", "")[:10]
        r["stage"] = stage
        r["matchday"] = match.get("matchday")
        pred_rows.append(r)

    prediction_data = pd.DataFrame(pred_rows)

    # Rellenar NaN con medianas del training
    num_pred_cols = [c for c in prediction_data.columns if c not in META_COLS]
    for col in num_pred_cols:
        if col in train_medians.index:
            prediction_data[col] = prediction_data[col].fillna(train_medians[col])
        else:
            prediction_data[col] = prediction_data[col].fillna(0)

    # ── Guardar ───────────────────────────────────────────────────────────────
    training_data.to_csv(os.path.join(PROCESSED, "training_data.csv"), index=False)
    prediction_data.to_csv(os.path.join(PROCESSED, "wc_prediction_data.csv"), index=False)

    # ── Resumen ───────────────────────────────────────────────────────────────
    train_num_cols = [c for c in training_data.columns if c not in META_COLS]

    print("\n" + "=" * 60)
    print("RESUMEN FEATURE ENGINEERING")
    print("=" * 60)

    print(f"\nTraining data:   {training_data.shape[0]:>5} filas × {training_data.shape[1]} cols")
    print(f"Prediction data: {prediction_data.shape[0]:>5} filas × {prediction_data.shape[1]} cols")

    print("\nDistribución target (training):")
    labels = {1: "Home win (1)", 0: "Empate  (0)", 2: "Away win (2)"}
    counts = training_data["result"].value_counts()
    total = len(training_data)
    for k in [1, 0, 2]:
        v = counts.get(k, 0)
        print(f"  {labels[k]}: {v:>5}  ({v / total * 100:.1f}%)")

    print("\nTop 5 equipos WC por win_rate (promedio como local y visitante):")
    team_wrs = {}
    for team in sorted(wc_teams):
        vals = []
        h_mask = training_data["home_team"] == team
        a_mask = training_data["away_team"] == team
        if h_mask.any():
            vals.append(training_data.loc[h_mask, "home_win_rate"].mean())
        if a_mask.any():
            vals.append(training_data.loc[a_mask, "away_win_rate"].mean())
        if vals:
            team_wrs[team] = float(np.mean(vals))
    for team, wr in sorted(team_wrs.items(), key=lambda x: -x[1])[:5]:
        print(f"  {team:<25} {wr:.3f}")

    nan_train = training_data[train_num_cols].isna().sum().sum()
    nan_pred_cols = [c for c in num_pred_cols if c in prediction_data.columns]
    nan_pred = prediction_data[nan_pred_cols].isna().sum().sum()
    print(f"\nNaN restantes — training: {nan_train}  |  prediction: {nan_pred}")

    if null_hist_teams:
        wc_nulls = null_hist_teams & wc_teams
        non_wc_nulls = null_hist_teams - wc_teams
        if wc_nulls:
            print(f"\nEquipos WC imputados con mediana (sin historial): {sorted(wc_nulls)}")
        if non_wc_nulls:
            print(f"Equipos no-WC imputados (sin historial):           {sorted(non_wc_nulls)}")
    else:
        print("\nTodos los equipos tenían historial previo al partido.")

    print("=" * 60)


if __name__ == "__main__":
    main()
