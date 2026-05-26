import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from fetch_api import FootballDataClient

RAW = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw"))


def save(filename: str, data: dict) -> None:
    path = os.path.join(RAW, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Guardado: {path}")


def main():
    os.makedirs(RAW, exist_ok=True)
    client = FootballDataClient()

    print("Descargando datos del Mundial 2026...\n")

    print("[1/4] Información general de la competición...")
    competition = client.get_competition("WC")
    save("wc_competition.json", competition)
    time.sleep(1)

    print("[2/4] Equipos clasificados...")
    teams_data = client.get_teams("WC")
    save("wc_teams.json", teams_data)
    time.sleep(1)

    print("[3/4] Partidos...")
    matches_data = client.get_matches("WC")
    save("wc_matches.json", matches_data)
    time.sleep(1)

    print("[4/4] Standings / grupos...")
    standings_data = client.get_standings("WC")
    save("wc_standings.json", standings_data)

    # ── Resumen ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESUMEN MUNDIAL 2026")
    print("=" * 60)

    teams = teams_data.get("teams", [])
    print(f"\nEquipos clasificados: {len(teams)}")

    matches = matches_data.get("matches", [])
    print(f"Partidos programados: {len(matches)}")

    dates = sorted(
        m.get("utcDate", "")[:10] for m in matches if m.get("utcDate")
    )
    if dates:
        print(f"Primer partido:       {dates[0]}")
        print(f"Último partido:       {dates[-1]}")

    # Grupos
    standings = standings_data.get("standings", [])
    groups = [s for s in standings if s.get("type") == "TOTAL"]
    if groups:
        print(f"\nGrupos ({len(groups)}):")
        for group in groups:
            group_name = group.get("group", "")
            group_teams = [t.get("team", {}).get("name", "") for t in group.get("table", [])]
            print(f"  {group_name}: {', '.join(group_teams)}")
    else:
        # Standings puede venir en otro formato si aún no arrancó la fase de grupos
        print(f"\nStandings: {len(standings)} entrada(s) (puede estar vacío antes del torneo)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
