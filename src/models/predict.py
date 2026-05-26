import os

import joblib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODELS_DIR = os.path.join(ROOT, "data", "models")
PROCESSED = os.path.join(ROOT, "data", "processed")

RESULT_LABELS = {0: "draw", 1: "home_win", 2: "away_win"}


def _load_models():
    classifier = joblib.load(os.path.join(MODELS_DIR, "best_model.pkl"))
    ph_bundle = joblib.load(os.path.join(MODELS_DIR, "poisson_home.pkl"))
    pa_bundle = joblib.load(os.path.join(MODELS_DIR, "poisson_away.pkl"))
    return classifier, ph_bundle, pa_bundle


def _get_team_features(team: str, role: str, wc_feat: pd.DataFrame) -> dict | None:
    """Extract per-team feature averages from WC prediction data."""
    col_map = {
        "win_rate": f"{role}_win_rate",
        "draw_rate": f"{role}_draw_rate",
        "goals_scored_avg": f"{role}_goals_scored_avg",
        "goals_conceded_avg": f"{role}_goals_conceded_avg",
        "clean_sheet_rate": f"{role}_clean_sheet_rate",
        "goal_diff_avg": f"{role}_goal_diff_avg",
        "form_last5": f"{role}_form_last5",
    }
    rows = wc_feat[wc_feat[f"{role}_team"] == team]
    if rows.empty:
        return None
    return {k: float(rows[v].mean()) for k, v in col_map.items() if v in rows.columns}


def predict_match(home_team: str, away_team: str) -> dict:
    """
    Predict result + scoreline for any matchup between WC teams.
    Returns dict with probabilities, predicted result, goals, and scoreline.
    """
    classifier, ph_bundle, pa_bundle = _load_models()
    wc_feat = pd.read_csv(os.path.join(PROCESSED, "wc_prediction_data.csv"))

    feature_cols = ph_bundle["feature_cols"]
    model_home = ph_bundle["model"]
    model_away = pa_bundle["model"]

    # Build feature vector for this matchup
    home_feats = _get_team_features(home_team, "home", wc_feat)
    away_feats = _get_team_features(away_team, "away", wc_feat)

    if home_feats is None:
        raise ValueError(f"Equipo local no encontrado en datos WC: '{home_team}'")
    if away_feats is None:
        raise ValueError(f"Equipo visitante no encontrado en datos WC: '{away_team}'")

    # Reconstruct a feature row matching training schema
    sample = {}
    for col in feature_cols:
        if col.startswith("home_"):
            key = col[5:]
            sample[col] = home_feats.get(key, 0.0)
        elif col.startswith("away_"):
            key = col[5:]
            sample[col] = away_feats.get(key, 0.0)
        elif col == "diff_win_rate":
            sample[col] = home_feats.get("win_rate", 0.0) - away_feats.get("win_rate", 0.0)
        elif col == "diff_goals_avg":
            sample[col] = home_feats.get("goals_scored_avg", 0.0) - away_feats.get("goals_scored_avg", 0.0)
        elif col == "h2h_home_wins":
            # Look up H2H from wc_feat if available
            row = wc_feat[(wc_feat["home_team"] == home_team) & (wc_feat["away_team"] == away_team)]
            sample[col] = float(row["h2h_home_wins"].iloc[0]) if not row.empty else 0.0
        elif col == "h2h_away_wins":
            row = wc_feat[(wc_feat["home_team"] == home_team) & (wc_feat["away_team"] == away_team)]
            sample[col] = float(row["h2h_away_wins"].iloc[0]) if not row.empty else 0.0
        elif col == "h2h_draws":
            row = wc_feat[(wc_feat["home_team"] == home_team) & (wc_feat["away_team"] == away_team)]
            sample[col] = float(row["h2h_draws"].iloc[0]) if not row.empty else 0.0
        elif col == "home_ranking":
            row = wc_feat[wc_feat["home_team"] == home_team]
            sample[col] = float(row["home_ranking"].iloc[0]) if not row.empty else 50.0
        elif col == "away_ranking":
            row = wc_feat[wc_feat["away_team"] == away_team]
            sample[col] = float(row["away_ranking"].iloc[0]) if not row.empty else 50.0
        elif col == "ranking_diff":
            hr = sample.get("home_ranking", 50.0)
            ar = sample.get("away_ranking", 50.0)
            sample[col] = hr - ar
        elif col == "is_group_stage":
            sample[col] = 1.0
        else:
            sample[col] = 0.0

    X = pd.DataFrame([sample])[feature_cols].fillna(0)

    # Classifier
    probs = classifier.predict_proba(X)[0]
    classes = list(classifier.classes_)
    ci = {c: classes.index(c) for c in classes}
    predicted_result_int = int(classes[np.argmax(probs)])

    # Poisson goals
    X_np = X.values
    X_const = sm.add_constant(X_np, has_constant="add")
    home_goals = max(0, round(float(model_home.predict(X_const)[0])))
    away_goals = max(0, round(float(model_away.predict(X_const)[0])))

    return {
        "home_team": home_team,
        "away_team": away_team,
        "predicted_result": RESULT_LABELS.get(predicted_result_int, "draw"),
        "prob_home": round(float(probs[ci[1]]), 4),
        "prob_draw": round(float(probs[ci[0]]), 4),
        "prob_away": round(float(probs[ci[2]]), 4),
        "home_goals": home_goals,
        "away_goals": away_goals,
        "scoreline": f"{home_goals}-{away_goals}",
    }
