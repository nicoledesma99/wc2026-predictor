import time
import logging
import requests
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class FootballDataClient:
    BASE_URL = "https://api.football-data.org/v4/"

    def __init__(self):
        api_key = os.getenv("FOOTBALL_DATA_API_KEY")
        if not api_key:
            raise ValueError("FOOTBALL_DATA_API_KEY no encontrada en .env")
        self.session = requests.Session()
        self.session.headers.update({"X-Auth-Token": api_key})

    def _get(self, path: str, params: dict = None) -> dict:
        url = self.BASE_URL + path.lstrip("/")
        logger.info("GET %s params=%s", url, params)

        for attempt in range(5):
            response = self.session.get(url, params=params)
            self._handle_rate_limit(response.headers)

            if response.status_code == 429:
                wait = 2 ** attempt
                logger.warning("429 Too Many Requests — reintentando en %ss", wait)
                time.sleep(wait)
                continue

            if response.status_code == 403:
                raise PermissionError(
                    f"403 Forbidden: sin acceso a {url}. Verificá tu API key o plan."
                )
            if response.status_code == 404:
                raise FileNotFoundError(f"404 Not Found: {url}")

            response.raise_for_status()
            return response.json()

        raise RuntimeError(f"No se pudo completar la request a {url} tras 5 intentos")

    def _handle_rate_limit(self, headers: dict) -> None:
        available = headers.get("X-Requests-Available-Minute")
        reset = headers.get("X-RequestCounter-Reset")

        if available is None:
            return

        available = int(available)
        logger.info("Requests disponibles este minuto: %d", available)

        if available < 2 and reset:
            wait = max(int(reset), 1)
            logger.warning(
                "Rate limit bajo (%d disponibles) — esperando %ss hasta reset",
                available,
                wait,
            )
            time.sleep(wait)

    def get_competition(self, code: str) -> dict:
        return self._get(f"competitions/{code}")

    def get_matches(self, code: str, season: int = None, matchday: int = None) -> dict:
        params = {}
        if season is not None:
            params["season"] = season
        if matchday is not None:
            params["matchday"] = matchday
        return self._get(f"competitions/{code}/matches", params or None)

    def get_standings(self, code: str, season: int = None) -> dict:
        params = {"season": season} if season is not None else None
        return self._get(f"competitions/{code}/standings", params)

    def get_teams(self, code: str) -> dict:
        return self._get(f"competitions/{code}/teams")

    def get_team_matches(self, team_id: int, limit: int = 20) -> dict:
        return self._get(f"teams/{team_id}/matches", {"limit": limit})
