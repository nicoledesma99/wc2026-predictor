import json
import logging
import math
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent

TEAM_ALIASES = {
    "Korea Republic": "South Korea",
    "Czech Republic": "Czechia",
    "USA": "United States",
    "DR Congo": "Congo DR",
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Cape Verde": "Cape Verde Islands",
    "Cote d'Ivoire": "Ivory Coast",
    "Curacao": "Curaçao",
}

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

RESULT_LABELS = {0: "draw", 1: "home_win", 2: "away_win"}


class PredictRequest(BaseModel):
    home_team: str
    away_team: str


# ── Module-level state (populated at startup) ─────────────────────────────────
_data: dict = {}


def normalize_name(name: str) -> str:
    return TEAM_ALIASES.get(name, name)


def format_group_name(raw: str) -> str:
    # raw is already "Group A" from the API
    return raw


def group_id_to_raw(group_id: str) -> str:
    """Convert any group reference to the canonical 'Group X' key used in standings."""
    g = group_id.strip()
    # Already in canonical form: "Group A"
    if g.title().startswith("Group ") and len(g) == 7:
        return g.title()
    # Single letter: "A" -> "Group A"
    if len(g) == 1 and g.isalpha():
        return f"Group {g.upper()}"
    # "GROUP_A" legacy
    if g.upper().startswith("GROUP_"):
        return f"Group {g.upper()[6:]}"
    return f"Group {g.upper()}"


def safe_float(v, default: float = 0.0) -> float:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return default
    return float(v)


def safe_int(v, default: int = 0) -> int:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return default
    return int(v)


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_data() -> None:
    logger.info("Cargando datos al startup...")

    # Predictions + feature columns
    preds_df = pd.read_csv(ROOT / "data/processed/wc_predictions.csv")
    pred_feat_df = pd.read_csv(ROOT / "data/processed/wc_prediction_data.csv")

    # Load Poisson models if available
    poisson_home = poisson_away = None
    classifier = None
    ph_path = ROOT / "data/models/poisson_home.pkl"
    pa_path = ROOT / "data/models/poisson_away.pkl"
    clf_path = ROOT / "data/models/best_model.pkl"
    if ph_path.exists() and pa_path.exists():
        ph_bundle = joblib.load(ph_path)
        pa_bundle = joblib.load(pa_path)
        poisson_home = ph_bundle["model"]
        poisson_away = pa_bundle["model"]
        poisson_features = ph_bundle["feature_cols"]
        logger.info("Modelos Poisson cargados.")
    else:
        poisson_features = []
        logger.warning("Modelos Poisson no encontrados — /api/predict no disponible.")
    if clf_path.exists():
        classifier = joblib.load(clf_path)
        logger.info("Clasificador cargado.")
    training_df = pd.read_csv(ROOT / "data/processed/training_data.csv")

    with open(ROOT / "data/models/metrics.json", encoding="utf-8") as f:
        metrics = json.load(f)
    with open(ROOT / "data/models/feature_names.json", encoding="utf-8") as f:
        feature_names = json.load(f)
    with open(ROOT / "data/raw/wc_standings.json", encoding="utf-8") as f:
        standings_raw = json.load(f)

    # Group mapping
    group_teams: dict[str, list] = {}
    team_to_group: dict[str, str] = {}
    for s in standings_raw.get("standings", []):
        group_raw = s.get("group", "")
        teams = [normalize_name(e["team"]["name"]) for e in s.get("table", []) if e.get("team")]
        group_teams[group_raw] = teams
        for t in teams:
            team_to_group[t] = group_raw

    # Merge xG estimates + goals columns into predictions
    feat_cols = ["match_id", "home_team", "away_team",
                 "home_goals_scored_avg", "away_goals_scored_avg"]
    available = [c for c in feat_cols if c in pred_feat_df.columns]
    merged = preds_df.merge(pred_feat_df[available], on=["match_id", "home_team", "away_team"], how="left")

    # Build match predictions list
    match_predictions = []
    for _, row in merged.iterrows():
        home = str(row["home_team"])
        away = str(row["away_team"])
        group_raw = team_to_group.get(home, "")
        # Poisson goals (present after train_goals.py runs)
        home_goals = safe_int(row.get("home_goals"), -1)
        away_goals = safe_int(row.get("away_goals"), -1)
        scoreline = str(row.get("scoreline", "")) if home_goals >= 0 else ""
        match_predictions.append({
            "match_id": safe_int(row.get("match_id"), 0),
            "home_team": home,
            "away_team": away,
            "group_raw": group_raw,
            "group": format_group_name(group_raw),
            "matchday": safe_int(row.get("matchday"), 0),
            "date": str(row.get("date", ""))[:10],
            "stage": str(row.get("stage", "")),
            "predicted_result": safe_int(row.get("predicted_result"), 0),
            "predicted_result_label": RESULT_LABELS.get(safe_int(row.get("predicted_result"), 0), "draw"),
            "prob_home_win": round(safe_float(row.get("prob_home_win")), 4),
            "prob_draw": round(safe_float(row.get("prob_draw")), 4),
            "prob_away_win": round(safe_float(row.get("prob_away_win")), 4),
            "home_goals_avg": round(safe_float(row.get("home_goals_scored_avg"), 1.4), 3),
            "away_goals_avg": round(safe_float(row.get("away_goals_scored_avg"), 1.1), 3),
            "home_goals": home_goals if home_goals >= 0 else None,
            "away_goals": away_goals if away_goals >= 0 else None,
            "scoreline": scoreline,
        })

    # Team stats (average of each team's features across all their WC matches)
    feat_base = ["win_rate", "draw_rate", "goals_scored_avg", "goals_conceded_avg",
                 "clean_sheet_rate", "goal_diff_avg", "form_last5"]
    accumulator: dict[str, dict] = {}
    for _, row in pred_feat_df.iterrows():
        for team, prefix in [(str(row["home_team"]), "home_"), (str(row["away_team"]), "away_")]:
            if team not in accumulator:
                accumulator[team] = {f: [] for f in feat_base}
            for feat in feat_base:
                val = row.get(f"{prefix}{feat}")
                if val is not None and not (isinstance(val, float) and math.isnan(val)):
                    accumulator[team][feat].append(float(val))

    team_stats: dict = {}
    for team, feat_lists in accumulator.items():
        team_stats[team] = {
            "team": team,
            "ranking": FIFA_RANKINGS.get(team, 60),
            "group": format_group_name(team_to_group.get(team, "")),
            **{f: round(float(np.mean(vals)), 4) if vals else 0.0 for f, vals in feat_lists.items()},
        }

    # Predicted group standings simulation
    predicted_standings = _simulate_standings(group_teams, match_predictions)

    _data.update({
        "match_predictions": match_predictions,
        "group_teams": group_teams,
        "team_to_group": team_to_group,
        "team_stats": team_stats,
        "predicted_standings": predicted_standings,
        "metrics": metrics,
        "feature_names": feature_names,
        "training_row_count": len(training_df),
        "classifier": classifier,
        "poisson_home": poisson_home,
        "poisson_away": poisson_away,
        "poisson_features": poisson_features,
        "wc_feat_df": pred_feat_df,
    })
    logger.info("Datos cargados: %d partidos, %d equipos, %d grupos",
                len(match_predictions), len(team_stats), len(group_teams))


def _simulate_standings(group_teams: dict, match_predictions: list) -> dict:
    standings: dict = {}
    for group_raw, teams in group_teams.items():
        table = {
            t: {"team": t, "pts": 0, "w": 0, "d": 0, "l": 0, "xgf": 0.0, "xgc": 0.0}
            for t in teams
        }
        group_matches = [
            m for m in match_predictions
            if m["group_raw"] == group_raw and m["stage"] == "GROUP_STAGE"
        ]
        for m in group_matches:
            home, away = m["home_team"], m["away_team"]
            result = m["predicted_result"]
            h_xg = m["home_goals_avg"]
            a_xg = m["away_goals_avg"]

            if home in table:
                table[home]["xgf"] += h_xg
                table[home]["xgc"] += a_xg
                if result == 1:
                    table[home]["pts"] += 3
                    table[home]["w"] += 1
                elif result == 0:
                    table[home]["pts"] += 1
                    table[home]["d"] += 1
                else:
                    table[home]["l"] += 1

            if away in table:
                table[away]["xgf"] += a_xg
                table[away]["xgc"] += h_xg
                if result == 2:
                    table[away]["pts"] += 3
                    table[away]["w"] += 1
                elif result == 0:
                    table[away]["pts"] += 1
                    table[away]["d"] += 1
                else:
                    table[away]["l"] += 1

        sorted_table = sorted(
            table.values(),
            key=lambda x: (x["pts"], x["xgf"] - x["xgc"], x["xgf"]),
            reverse=True,
        )
        for i, entry in enumerate(sorted_table):
            entry["xgf"] = round(entry["xgf"], 2)
            entry["xgc"] = round(entry["xgc"], 2)
            entry["xgd"] = round(entry["xgf"] - entry["xgc"], 2)
            entry["qualifies"] = i < 2
        standings[group_raw] = sorted_table
    return standings


# ── App & CORS ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_data()
    yield


app = FastAPI(
    title="Mundial 2026 Predictor API",
    version="1.0.0",
    description="Predicciones ML para los 72 partidos de fase de grupos del Mundial 2026.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Meta"])
def health():
    return {"status": "ok", "data_loaded": bool(_data)}


@app.get("/api/predictions", tags=["Predicciones"])
def get_predictions(
    group: Optional[str] = Query(None, description="Letra del grupo: A-L"),
    team: Optional[str] = Query(None, description="Nombre del equipo (parcial)"),
):
    """Devuelve predicciones de la fase de grupos. Filtrable por grupo o equipo."""
    results = [m for m in _data["match_predictions"] if m["stage"] == "GROUP_STAGE"]

    if group:
        raw = group_id_to_raw(group)
        results = [m for m in results if m["group_raw"] == raw]

    if team:
        q = team.lower()
        results = [
            m for m in results
            if q in m["home_team"].lower() or q in m["away_team"].lower()
        ]

    return {"count": len(results), "predictions": results}


@app.get("/api/groups", tags=["Grupos"])
def get_groups():
    """Devuelve los 12 grupos con tabla de posiciones predicha y clasificados."""
    groups = []
    for group_raw in sorted(_data["group_teams"].keys()):
        standing = _data["predicted_standings"].get(group_raw, [])
        groups.append({
            "group_id": group_raw.replace("Group ", ""),
            "group_name": format_group_name(group_raw),
            "teams": _data["group_teams"][group_raw],
            "standings": standing,
            "qualifies": [s["team"] for s in standing[:2]],
        })
    return {"count": len(groups), "groups": groups}


@app.get("/api/groups/{group_id}", tags=["Grupos"])
def get_group_detail(group_id: str):
    """Detalle de un grupo: tabla de posiciones + partidos + clasificados."""
    group_raw = group_id_to_raw(group_id)
    if group_raw not in _data["group_teams"]:
        raise HTTPException(status_code=404, detail=f"Grupo '{group_id}' no encontrado. Usar A-L.")

    standing = _data["predicted_standings"].get(group_raw, [])
    matches = sorted(
        [m for m in _data["match_predictions"] if m["group_raw"] == group_raw],
        key=lambda x: (x["matchday"], x["date"]),
    )
    return {
        "group_id": group_raw.replace("Group ", ""),
        "group_name": format_group_name(group_raw),
        "teams": _data["group_teams"][group_raw],
        "standings": standing,
        "qualifies": [s["team"] for s in standing[:2]],
        "matches": matches,
    }


@app.get("/api/teams", tags=["Equipos"])
def get_teams():
    """Lista de los 48 equipos clasificados con sus stats de forma reciente."""
    teams = sorted(_data["team_stats"].values(), key=lambda x: x["ranking"])
    return {"count": len(teams), "teams": teams}


@app.get("/api/teams/{team_name}", tags=["Equipos"])
def get_team_detail(team_name: str):
    """Detalle de un equipo: stats + sus partidos en el Mundial."""
    stats = _data["team_stats"]
    team_norm = normalize_name(team_name)

    # Exact match first, then case-insensitive
    found = stats.get(team_norm)
    if not found:
        match = next((k for k in stats if k.lower() == team_name.lower()), None)
        if not match:
            raise HTTPException(status_code=404, detail=f"Equipo '{team_name}' no encontrado.")
        found = stats[match]

    team = found["team"]
    matches = sorted(
        [m for m in _data["match_predictions"] if m["home_team"] == team or m["away_team"] == team],
        key=lambda x: (x["matchday"], x["date"]),
    )
    return {**found, "matches": matches}


@app.get("/api/model-info", tags=["Modelo"])
def get_model_info():
    """Métricas del modelo, features usadas y tamaño del dataset de entrenamiento."""
    return {
        **_data["metrics"],
        "training_rows": _data["training_row_count"],
        "feature_count": len(_data["feature_names"]),
        "features": _data["feature_names"],
    }


@app.get("/api/favorites", tags=["Análisis"])
def get_favorites():
    """Top 10 favoritos: equipos con mayor probabilidad promedio de ganar en grupos."""
    team_win_probs: dict[str, list] = {}
    for m in _data["match_predictions"]:
        if m["stage"] != "GROUP_STAGE":
            continue
        home, away = m["home_team"], m["away_team"]
        team_win_probs.setdefault(home, []).append(m["prob_home_win"])
        team_win_probs.setdefault(away, []).append(m["prob_away_win"])

    favorites = []
    for team, probs in team_win_probs.items():
        t_stats = _data["team_stats"].get(team, {})
        favorites.append({
            "team": team,
            "group": t_stats.get("group", ""),
            "ranking": t_stats.get("ranking", 60),
            "avg_win_prob": round(float(np.mean(probs)), 4),
            "win_rate_form": round(t_stats.get("win_rate", 0.0), 4),
            "form_last5": round(t_stats.get("form_last5", 0.0), 4),
        })

    favorites.sort(key=lambda x: -x["avg_win_prob"])
    return {"favorites": favorites[:10]}


@app.get("/api/upsets", tags=["Análisis"])
def get_upsets():
    """10 partidos más parejos (mayor incertidumbre / mayor potencial de sorpresa)."""
    def entropy(m: dict) -> float:
        return -sum(
            p * math.log(p + 1e-9)
            for p in [m["prob_home_win"], m["prob_draw"], m["prob_away_win"]]
        )

    group_matches = [m for m in _data["match_predictions"] if m["stage"] == "GROUP_STAGE"]
    enriched = sorted(
        [
            {
                **m,
                "uncertainty_score": round(entropy(m), 4),
                "favorite": (
                    m["home_team"] if m["prob_home_win"] > m["prob_away_win"] else m["away_team"]
                ),
                "underdog": (
                    m["away_team"] if m["prob_home_win"] > m["prob_away_win"] else m["home_team"]
                ),
                "prob_gap": round(
                    abs(m["prob_home_win"] - m["prob_away_win"]), 4
                ),
            }
            for m in group_matches
        ],
        key=lambda x: -x["uncertainty_score"],
    )
    return {"upsets": enriched[:10]}


@app.post("/api/predict", tags=["Predicciones"])
def predict_custom(req: PredictRequest):
    """
    Prediccion en tiempo real para cualquier cruce entre equipos del Mundial.
    Body: {"home_team": "Argentina", "away_team": "Brazil"}
    """
    classifier = _data.get("classifier")
    poisson_home = _data.get("poisson_home")
    poisson_away = _data.get("poisson_away")
    feature_cols = _data.get("poisson_features", [])
    wc_feat = _data.get("wc_feat_df")

    if classifier is None or poisson_home is None or poisson_away is None:
        raise HTTPException(
            status_code=503,
            detail="Modelos no cargados. Ejecuta train_goals.py primero.",
        )

    home_team = normalize_name(req.home_team)
    away_team = normalize_name(req.away_team)

    def get_team_feats(team: str, role: str) -> dict | None:
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

    home_feats = get_team_feats(home_team, "home")
    away_feats = get_team_feats(away_team, "away")

    if home_feats is None:
        raise HTTPException(status_code=404, detail=f"Equipo '{home_team}' no encontrado en datos WC.")
    if away_feats is None:
        raise HTTPException(status_code=404, detail=f"Equipo '{away_team}' no encontrado en datos WC.")

    sample: dict = {}
    for col in feature_cols:
        if col.startswith("home_"):
            sample[col] = home_feats.get(col[5:], 0.0)
        elif col.startswith("away_"):
            sample[col] = away_feats.get(col[5:], 0.0)
        elif col == "diff_win_rate":
            sample[col] = home_feats.get("win_rate", 0.0) - away_feats.get("win_rate", 0.0)
        elif col == "diff_goals_avg":
            sample[col] = home_feats.get("goals_scored_avg", 0.0) - away_feats.get("goals_scored_avg", 0.0)
        elif col in ("h2h_home_wins", "h2h_away_wins", "h2h_draws"):
            row = wc_feat[(wc_feat["home_team"] == home_team) & (wc_feat["away_team"] == away_team)]
            sample[col] = float(row[col].iloc[0]) if not row.empty and col in row.columns else 0.0
        elif col == "home_ranking":
            r = wc_feat[wc_feat["home_team"] == home_team]
            sample[col] = float(r["home_ranking"].iloc[0]) if not r.empty else 50.0
        elif col == "away_ranking":
            r = wc_feat[wc_feat["away_team"] == away_team]
            sample[col] = float(r["away_ranking"].iloc[0]) if not r.empty else 50.0
        elif col == "ranking_diff":
            sample[col] = sample.get("home_ranking", 50.0) - sample.get("away_ranking", 50.0)
        elif col == "is_group_stage":
            sample[col] = 1.0
        else:
            sample[col] = 0.0

    X = pd.DataFrame([sample])[feature_cols].fillna(0)

    probs = classifier.predict_proba(X)[0]
    classes = list(classifier.classes_)
    ci = {c: classes.index(c) for c in classes}
    predicted_result_int = int(classes[int(np.argmax(probs))])

    X_np = X.values
    X_const = sm.add_constant(X_np, has_constant="add")
    home_goals = max(0, round(float(poisson_home.predict(X_const)[0])))
    away_goals = max(0, round(float(poisson_away.predict(X_const)[0])))

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
