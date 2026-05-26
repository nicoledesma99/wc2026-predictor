import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from fetch_api import FootballDataClient

RAW = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw"))
TEAMS_FILE = os.path.join(RAW, "wc_teams.json")
OUTPUT_FILE = os.path.join(RAW, "team_recent_matches.json")
CHECKPOINT_FILE = os.path.join(RAW, "team_recent_matches_checkpoint.json")


def load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_checkpoint(data: dict) -> None:
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    if not os.path.exists(TEAMS_FILE):
        print(f"ERROR: No se encuentra {TEAMS_FILE}. Ejecutá fetch_worldcup.py primero.")
        sys.exit(1)

    with open(TEAMS_FILE, encoding="utf-8") as f:
        teams_data = json.load(f)

    teams = teams_data.get("teams", [])
    total = len(teams)
    print(f"Enriqueciendo {total} equipos con sus últimos 20 partidos...\n")

    # Retomar desde checkpoint si existe
    results = load_checkpoint()
    if results:
        already_done = len(results)
        print(f"  Checkpoint encontrado: {already_done}/{total} equipos ya descargados. Retomando...\n")

    client = FootballDataClient()
    failed = []

    for i, team in enumerate(teams, start=1):
        team_id = str(team["id"])
        team_name = team.get("name", f"ID {team_id}")

        if team_id in results:
            print(f"  [{i:>2}/{total}] {team_name} — ya descargado, saltando")
            continue

        print(f"  [{i:>2}/{total}] Descargando equipo: {team_name}...")
        try:
            matches = client.get_team_matches(int(team_id), limit=20)
            results[team_id] = {
                "team_id": int(team_id),
                "team_name": team_name,
                "matches": matches.get("matches", []),
            }
            save_checkpoint(results)
        except Exception as e:
            print(f"    ERROR en {team_name}: {e}")
            failed.append({"team_id": team_id, "team_name": team_name, "error": str(e)})

        time.sleep(0.5)

    # Guardar resultado final
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Limpiar checkpoint si todo terminó sin errores
    if not failed and os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        print("\nCheckpoint eliminado (descarga completa).")

    print(f"\nListo. {len(results)}/{total} equipos guardados en {OUTPUT_FILE}")
    if failed:
        print(f"Fallaron {len(failed)} equipos:")
        for f_ in failed:
            print(f"  - {f_['team_name']}: {f_['error']}")


if __name__ == "__main__":
    main()
