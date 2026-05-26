import json
import logging
import os
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED = os.path.join(ROOT, "data", "processed")
MODELS_DIR = os.path.join(ROOT, "data", "models")
RAW = os.path.join(ROOT, "data", "raw")

META_COLS = {"home_team", "away_team", "date", "result", "match_id", "stage", "matchday"}
TARGET_NAMES = ["Empate (0)", "Home win (1)", "Away win (2)"]

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
}


def normalize_name(name: str) -> str:
    return TEAM_ALIASES.get(name, name)


def load_training_data() -> tuple[pd.DataFrame, pd.Series, list[str]]:
    df = pd.read_csv(os.path.join(PROCESSED, "training_data.csv"))
    feature_cols = [c for c in df.columns if c not in META_COLS]
    return df[feature_cols], df["result"], feature_cols


def build_models() -> dict:
    return {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ]),
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=200, random_state=42),
    }


def evaluate_model(name: str, model, X_train, X_test, y_train, y_test, X_all, y_all) -> dict:
    t0 = time.time()
    model.fit(X_train, y_train)
    elapsed = time.time() - t0

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)

    logger.info("CV %s (5-fold)...", name)
    cv_scores = cross_val_score(model, X_all, y_all, cv=5, scoring="accuracy", n_jobs=-1)

    logger.info(
        "%s -> acc=%.3f  f1=%.3f  cv=%.3f+/-%.3f  (train %.1fs)",
        name, acc, f1, cv_scores.mean(), cv_scores.std(), elapsed,
    )
    return {
        "name": name, "model": model, "y_pred": y_pred,
        "accuracy": acc, "f1_macro": f1,
        "cv_mean": cv_scores.mean(), "cv_std": cv_scores.std(),
    }


def get_feature_importance(name: str, model, feature_cols: list) -> list[tuple]:
    if "Logistic" in name:
        coef = model.named_steps["clf"].coef_
        importance = np.mean(np.abs(coef), axis=0)
    elif hasattr(model, "feature_importances_"):
        importance = model.feature_importances_
    else:
        return []
    return sorted(zip(feature_cols, importance), key=lambda x: -x[1])[:10]


def load_group_mapping() -> dict:
    path = os.path.join(RAW, "wc_standings.json")
    if not os.path.exists(path):
        return {}
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


def predict_wc(model, feature_cols: list) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(PROCESSED, "wc_prediction_data.csv"))
    X = df[feature_cols]
    probs = model.predict_proba(X)
    classes = list(model.classes_)
    ci = {c: classes.index(c) for c in classes}

    out = df[["match_id", "home_team", "away_team", "date", "stage", "matchday"]].copy()
    out["predicted_result"] = np.array(classes)[np.argmax(probs, axis=1)]
    out["prob_home_win"] = np.round(probs[:, ci[1]], 4)
    out["prob_draw"] = np.round(probs[:, ci[0]], 4)
    out["prob_away_win"] = np.round(probs[:, ci[2]], 4)
    return out


def format_group_name(raw: str) -> str:
    return raw.replace("GROUP_", "Grupo ").replace("_", " ")


def print_group_predictions(preds: pd.DataFrame, team_to_group: dict) -> None:
    gs = preds[preds["stage"] == "GROUP_STAGE"].copy()
    gs["group"] = gs["home_team"].map(team_to_group)
    gs = gs.sort_values(["group", "matchday", "date"])

    print("\n" + "=" * 72)
    print("  PREDICCIONES — FASE DE GRUPOS  MUNDIAL 2026")
    print("=" * 72)

    for group_raw in sorted(gs["group"].dropna().unique()):
        group_label = format_group_name(group_raw)
        print(f"\n  --- {group_label} ---")
        for _, row in gs[gs["group"] == group_raw].iterrows():
            home = row["home_team"]
            away = row["away_team"]
            ph = row["prob_home_win"]
            pd_ = row["prob_draw"]
            pa = row["prob_away_win"]
            res = int(row["predicted_result"])

            # Ordenar por probabilidad para mostrar la más alta primero
            outcomes = sorted(
                [(ph, f"{home} gana"), (pd_, "Empate"), (pa, f"{away} gana")],
                key=lambda x: -x[0],
            )
            parts = " | ".join(f"{label} ({prob * 100:.0f}%)" for prob, label in outcomes)
            print(f"    MD{int(row['matchday'])}  {home:<22} vs {away:<22}")
            print(f"         {parts}")

    print("\n" + "=" * 72)


def main() -> None:
    os.makedirs(MODELS_DIR, exist_ok=True)

    # ── Cargar datos ─────────────────────────────────────────────────────────
    logger.info("Cargando training data...")
    X, y, feature_cols = load_training_data()
    logger.info("Shape: %d filas × %d features", len(X), len(feature_cols))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    logger.info("Train: %d | Test: %d", len(X_train), len(X_test))

    # ── Entrenar y evaluar ───────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("ENTRENAMIENTO Y EVALUACIÓN (3 modelos)")
    print("=" * 60)

    results = []
    for name, model in build_models().items():
        print(f"\n--- {name} ---")
        res = evaluate_model(name, model, X_train, X_test, y_train, y_test, X, y)
        results.append(res)
        print(classification_report(
            y_test, res["y_pred"],
            labels=[0, 1, 2], target_names=TARGET_NAMES, zero_division=0,
        ))

    # ── Tabla comparativa ────────────────────────────────────────────────────
    print("=" * 60)
    print("COMPARACIÓN DE MODELOS")
    print("=" * 60)
    print(f"  {'Modelo':<25} {'Accuracy':>9} {'CV Mean':>9} {'CV Std':>8} {'F1 Macro':>9}")
    print("  " + "-" * 60)
    for r in sorted(results, key=lambda x: -x["cv_mean"]):
        mark = " *" if r == max(results, key=lambda x: x["cv_mean"]) else "  "
        print(f"{mark} {r['name']:<25} {r['accuracy']:>9.3f} {r['cv_mean']:>9.3f} {r['cv_std']:>8.3f} {r['f1_macro']:>9.3f}")

    best = max(results, key=lambda x: x["cv_mean"])
    print(f"\n  Mejor modelo: {best['name']}  (CV accuracy = {best['cv_mean']:.3f} +/- {best['cv_std']:.3f})")

    # ── Feature importance ───────────────────────────────────────────────────
    top_features = get_feature_importance(best["name"], best["model"], feature_cols)
    if top_features:
        print(f"\n{'=' * 60}")
        print(f"TOP 10 FEATURES — {best['name']}")
        print("=" * 60)
        max_imp = top_features[0][1]
        for i, (feat, imp) in enumerate(top_features, 1):
            bar = "#" * int(imp / max_imp * 30)
            print(f"  {i:>2}. {feat:<32} {imp:.4f}  {bar}")

    # ── Guardar ──────────────────────────────────────────────────────────────
    joblib.dump(best["model"], os.path.join(MODELS_DIR, "best_model.pkl"))

    with open(os.path.join(MODELS_DIR, "feature_names.json"), "w") as f:
        json.dump(feature_cols, f, indent=2)

    metrics = {
        "model_name": best["name"],
        "accuracy": round(float(best["accuracy"]), 4),
        "cv_mean": round(float(best["cv_mean"]), 4),
        "cv_std": round(float(best["cv_std"]), 4),
        "f1_macro": round(float(best["f1_macro"]), 4),
    }
    with open(os.path.join(MODELS_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Modelo guardado -> data/models/best_model.pkl")

    # ── Predicciones WC ──────────────────────────────────────────────────────
    logger.info("Generando predicciones del Mundial 2026...")
    predictions = predict_wc(best["model"], feature_cols)
    predictions.to_csv(os.path.join(PROCESSED, "wc_predictions.csv"), index=False)

    team_to_group = load_group_mapping()
    print_group_predictions(predictions, team_to_group)

    print(f"  Predicciones -> data/processed/wc_predictions.csv")
    print(f"  Modelo       -> data/models/best_model.pkl")
    print(f"  Metricas     -> data/models/metrics.json\n")


if __name__ == "__main__":
    main()
