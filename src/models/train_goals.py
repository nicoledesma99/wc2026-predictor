import json
import logging
import os

import joblib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED = os.path.join(ROOT, "data", "processed")
MODELS_DIR = os.path.join(ROOT, "data", "models")
RAW = os.path.join(ROOT, "data", "raw")

META_COLS = {"home_team", "away_team", "date", "result", "match_id",
             "stage", "matchday", "home_score", "away_score"}

TEAM_ALIASES = {
    "Korea Republic": "South Korea",
    "Czech Republic": "Czechia",
    "USA": "United States",
    "DR Congo": "Congo DR",
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Cape Verde": "Cape Verde Islands",
    "Cote d'Ivoire": "Ivory Coast",
    "Curacao": "Curacao",
}


def normalize_name(name: str) -> str:
    return TEAM_ALIASES.get(str(name), str(name))


# ── 1. Load & merge data ──────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    logger.info("Cargando training_data.csv...")
    tr = pd.read_csv(os.path.join(PROCESSED, "training_data.csv"))

    if "home_score" in tr.columns and "away_score" in tr.columns:
        logger.info("Scores ya presentes en training_data.csv")
        df = tr.dropna(subset=["home_score", "away_score"]).copy()
    else:
        logger.info("Mergeando scores desde results.csv...")
        raw = pd.read_csv(os.path.join(RAW, "results.csv"))
        raw["home_team"] = raw["home_team"].apply(normalize_name)
        raw["away_team"] = raw["away_team"].apply(normalize_name)
        raw["date"] = pd.to_datetime(raw["date"]).dt.strftime("%Y-%m-%d")
        tr["date"] = pd.to_datetime(tr["date"]).dt.strftime("%Y-%m-%d")

        df = tr.merge(
            raw[["date", "home_team", "away_team", "home_score", "away_score"]],
            on=["date", "home_team", "away_team"],
            how="inner",
        )
        logger.info("Filas tras merge: %d (de %d originales)", len(df), len(tr))

    df = df.dropna(subset=["home_score", "away_score"])
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    return df


def get_feature_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in META_COLS]


# ── 2. Train Poisson models ───────────────────────────────────────────────────

def train_poisson(X_train: np.ndarray, y_train: np.ndarray,
                  X_test: np.ndarray, y_test: np.ndarray,
                  label: str) -> tuple:
    """Fit GLM Poisson, return (fitted_result, mae, rmse)."""
    X_tr_const = sm.add_constant(X_train, has_constant="add")
    X_te_const = sm.add_constant(X_test, has_constant="add")

    glm = sm.GLM(y_train, X_tr_const, family=sm.families.Poisson())
    result = glm.fit(maxiter=200, method="newton")

    preds = result.predict(X_te_const)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))

    # Naive baseline: historical mean
    baseline_pred = np.full(len(y_test), y_train.mean())
    mae_base = mean_absolute_error(y_test, baseline_pred)
    rmse_base = np.sqrt(mean_squared_error(y_test, baseline_pred))

    print(f"\n  {label}")
    print(f"    MAE  Poisson: {mae:.4f}  vs  Baseline: {mae_base:.4f}")
    print(f"    RMSE Poisson: {rmse:.4f}  vs  Baseline: {rmse_base:.4f}")
    print(f"    Media historica goles: {y_train.mean():.3f}")

    return result, mae, rmse, mae_base


def train_models(df: pd.DataFrame, feature_cols: list[str]) -> tuple:
    X = df[feature_cols].fillna(0).values
    y_home = df["home_score"].values.astype(float)
    y_away = df["away_score"].values.astype(float)

    X_train, X_test, yh_train, yh_test, ya_train, ya_test = train_test_split(
        X, y_home, y_away, test_size=0.2, random_state=42
    )
    logger.info("Split -> train %d | test %d", len(X_train), len(X_test))

    print("\n" + "=" * 60)
    print("ENTRENAMIENTO MODELOS POISSON")
    print("=" * 60)

    model_home, mae_h, rmse_h, base_h = train_poisson(
        X_train, yh_train, X_test, yh_test, "Goles LOCAL (poisson_home)"
    )
    model_away, mae_a, rmse_a, base_a = train_poisson(
        X_train, ya_train, X_test, ya_test, "Goles VISITANTE (poisson_away)"
    )

    print("\n" + "=" * 60)
    print(f"  Mejora vs baseline — Local:     MAE {base_h - mae_h:+.4f}")
    print(f"  Mejora vs baseline — Visitante: MAE {base_a - mae_a:+.4f}")
    print("=" * 60)

    return model_home, model_away, mae_h, rmse_h, mae_a, rmse_a


# ── 3. Save models & metrics ──────────────────────────────────────────────────

def save_models(model_home, model_away,
                feature_cols: list[str],
                mae_h: float, rmse_h: float,
                mae_a: float, rmse_a: float) -> None:
    os.makedirs(MODELS_DIR, exist_ok=True)

    # Wrap statsmodels result for easy pickling
    joblib.dump({"model": model_home, "feature_cols": feature_cols},
                os.path.join(MODELS_DIR, "poisson_home.pkl"))
    joblib.dump({"model": model_away, "feature_cols": feature_cols},
                os.path.join(MODELS_DIR, "poisson_away.pkl"))
    logger.info("Modelos Poisson guardados.")

    metrics_path = os.path.join(MODELS_DIR, "metrics.json")
    with open(metrics_path, encoding="utf-8") as f:
        metrics = json.load(f)

    metrics["goals_model"] = "Poisson GLM (statsmodels)"
    metrics["poisson_home_mae"] = round(float(mae_h), 4)
    metrics["poisson_home_rmse"] = round(float(rmse_h), 4)
    metrics["poisson_away_mae"] = round(float(mae_a), 4)
    metrics["poisson_away_rmse"] = round(float(rmse_a), 4)

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info("metrics.json actualizado con metricas de goles.")


# ── 4. Regenerate WC predictions ─────────────────────────────────────────────

def predict_goals_row(X_row: np.ndarray, model_home, model_away) -> tuple[int, int]:
    X_const = sm.add_constant(X_row.reshape(1, -1), has_constant="add")
    hg = float(model_home.predict(X_const)[0])
    ag = float(model_away.predict(X_const)[0])
    return max(0, round(hg)), max(0, round(ag))


def load_group_mapping() -> dict:
    path = os.path.join(RAW, "wc_standings.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    team_to_group = {}
    for s in data.get("standings", []):
        group = s.get("group", "")
        for entry in s.get("table", []):
            team = normalize_name(entry.get("team", {}).get("name", ""))
            if team:
                team_to_group[team] = group
    return team_to_group


def regenerate_predictions(model_home, model_away, feature_cols: list[str]) -> pd.DataFrame:
    preds_old = pd.read_csv(os.path.join(PROCESSED, "wc_predictions.csv"))
    wc_feat = pd.read_csv(os.path.join(PROCESSED, "wc_prediction_data.csv"))

    X_wc = wc_feat[feature_cols].fillna(0).values

    home_goals, away_goals = [], []
    for i in range(len(X_wc)):
        hg, ag = predict_goals_row(X_wc[i], model_home, model_away)
        home_goals.append(hg)
        away_goals.append(ag)

    preds_old["home_goals"] = home_goals
    preds_old["away_goals"] = away_goals
    preds_old["scoreline"] = [f"{h}-{a}" for h, a in zip(home_goals, away_goals)]

    out_path = os.path.join(PROCESSED, "wc_predictions.csv")
    preds_old.to_csv(out_path, index=False)
    logger.info("wc_predictions.csv actualizado con goles y marcadores.")
    return preds_old


def simulate_standings_with_goals(group_teams: dict, preds: pd.DataFrame) -> dict:
    standings: dict = {}
    for group_raw, teams in group_teams.items():
        table = {t: {"team": t, "pts": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "gc": 0}
                 for t in teams}
        group_matches = preds[
            (preds["home_team"].isin(teams)) &
            (preds["stage"] == "GROUP_STAGE")
        ]
        for _, row in group_matches.iterrows():
            home, away = str(row["home_team"]), str(row["away_team"])
            hg, ag = int(row["home_goals"]), int(row["away_goals"])
            res = int(row["predicted_result"])

            if home in table:
                table[home]["gf"] += hg
                table[home]["gc"] += ag
                if res == 1:
                    table[home]["pts"] += 3; table[home]["w"] += 1
                elif res == 0:
                    table[home]["pts"] += 1; table[home]["d"] += 1
                else:
                    table[home]["l"] += 1

            if away in table:
                table[away]["gf"] += ag
                table[away]["gc"] += hg
                if res == 2:
                    table[away]["pts"] += 3; table[away]["w"] += 1
                elif res == 0:
                    table[away]["pts"] += 1; table[away]["d"] += 1
                else:
                    table[away]["l"] += 1

        sorted_table = sorted(
            table.values(),
            key=lambda x: (x["pts"], x["gf"] - x["gc"], x["gf"]),
            reverse=True,
        )
        for entry in sorted_table:
            entry["dg"] = entry["gf"] - entry["gc"]
        standings[group_raw] = sorted_table
    return standings


def print_predictions_with_scores(preds: pd.DataFrame, team_to_group: dict) -> None:
    gs = preds[preds["stage"] == "GROUP_STAGE"].copy()
    gs["group"] = gs["home_team"].map(team_to_group)
    gs = gs.sort_values(["group", "matchday", "date"])

    RESULT_LABEL = {1: "gana", 0: "Empate", 2: "gana"}

    print("\n" + "=" * 72)
    print("  PREDICCIONES CON MARCADOR — FASE DE GRUPOS  MUNDIAL 2026")
    print("=" * 72)

    group_teams_map: dict[str, list] = {}
    for _, row in gs.iterrows():
        g = row["group"]
        if g not in group_teams_map:
            group_teams_map[g] = []

    for group_raw in sorted(gs["group"].dropna().unique()):
        print(f"\n  === {group_raw} ===")
        group_data = gs[gs["group"] == group_raw]

        for _, row in group_data.iterrows():
            home = str(row["home_team"])
            away = str(row["away_team"])
            hg = int(row["home_goals"])
            ag = int(row["away_goals"])
            score = f"{hg}-{ag}"
            res = int(row["predicted_result"])
            ph = row["prob_home_win"]
            pd_ = row["prob_draw"]
            pa = row["prob_away_win"]

            if res == 1:
                winner_str = f"{home} gana ({ph*100:.0f}%)"
            elif res == 2:
                winner_str = f"{away} gana ({pa*100:.0f}%)"
            else:
                winner_str = f"Empate ({pd_*100:.0f}%)"

            line = f"    {home:<22} {score:>5}  {away:<22} | {winner_str}"
            print(line)

    print("\n" + "=" * 72)


def print_standings(standings: dict) -> None:
    print("\n" + "=" * 72)
    print("  TABLA DE POSICIONES PREDICHA")
    print("=" * 72)

    for group_raw in sorted(standings.keys()):
        print(f"\n  {group_raw}")
        print(f"    {'Equipo':<22} {'J':>2} {'G':>2} {'E':>2} {'P':>2} {'GF':>3} {'GC':>3} {'DG':>4} {'Pts':>4}")
        print("    " + "-" * 52)
        for i, row in enumerate(standings[group_raw]):
            mark = " *" if i < 2 else "  "
            j = row["w"] + row["d"] + row["l"]
            dg = row["gf"] - row["gc"]
            print(
                f"{mark}  {row['team']:<22} {j:>2} {row['w']:>2} {row['d']:>2} {row['l']:>2}"
                f" {row['gf']:>3} {row['gc']:>3} {dg:>+4} {row['pts']:>4}"
            )

    print("\n  (* = clasifica a octavos de final)")
    print("=" * 72 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # 1. Load data
    df = load_data()
    feature_cols = get_feature_cols(df)
    logger.info("Dataset: %d filas, %d features", len(df), len(feature_cols))

    # 2. Train
    model_home, model_away, mae_h, rmse_h, mae_a, rmse_a = train_models(df, feature_cols)

    # 3. Save
    save_models(model_home, model_away, feature_cols, mae_h, rmse_h, mae_a, rmse_a)

    # 4. Regenerate WC predictions
    preds = regenerate_predictions(model_home, model_away, feature_cols)

    # 5. Print results
    team_to_group = load_group_mapping()
    print_predictions_with_scores(preds, team_to_group)

    # 6. Standings with real goal counts
    group_teams = {}
    for team, group in team_to_group.items():
        group_teams.setdefault(group, []).append(team)

    standings = simulate_standings_with_goals(group_teams, preds)
    print_standings(standings)

    print(f"  Modelos  -> data/models/poisson_home.pkl / poisson_away.pkl")
    print(f"  Preds    -> data/processed/wc_predictions.csv")
    print(f"  Metrics  -> data/models/metrics.json\n")


if __name__ == "__main__":
    main()
