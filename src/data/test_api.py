import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from fetch_api import FootballDataClient

COMPETITIONS_OUTPUT = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "raw", "available_competitions.json"
)


def main():
    client = FootballDataClient()

    # 1. Listar TODAS las competiciones disponibles en el plan
    print("\n=== 1. Competiciones disponibles en mi plan ===")
    data = client._get("competitions/")
    competitions = data.get("competitions", [])
    print(f"  Total: {len(competitions)}\n")
    for c in competitions:
        print(f"  [{c.get('id'):>4}]  {c.get('code', ''):6}  {c.get('name')}")

    # Guardar en JSON
    os.makedirs(os.path.dirname(os.path.abspath(COMPETITIONS_OUTPUT)), exist_ok=True)
    with open(os.path.abspath(COMPETITIONS_OUTPUT), "w", encoding="utf-8") as f:
        json.dump(competitions, f, indent=2, ensure_ascii=False)
    print(f"\n  Guardado en: {os.path.abspath(COMPETITIONS_OUTPUT)}")

    # 2. Verificar key con CL (Champions League)
    print("\n=== 2. Test con CL (Champions League) ===")
    comp = client.get_competition("CL")
    print(f"  Nombre:    {comp.get('name')}")
    print(f"  ID:        {comp.get('id')}")
    season = comp.get("currentSeason", {})
    print(f"  Temporada: {season.get('startDate', '')[:4]}/{season.get('endDate', '')[:4]}")

    matches_data = client.get_matches("CL")
    matches = matches_data.get("matches", [])
    print(f"\n  Partidos CL disponibles: {len(matches)}")
    print("  Últimos 5:")
    for m in matches[-5:]:
        home = m.get("homeTeam", {}).get("name", "TBD")
        away = m.get("awayTeam", {}).get("name", "TBD")
        date = m.get("utcDate", "")[:10]
        score = m.get("score", {}).get("fullTime", {})
        result = f"{score.get('home')}-{score.get('away')}" if score.get("home") is not None else m.get("status", "")
        print(f"    {date}  {home} vs {away}  {result}")


if __name__ == "__main__":
    main()
