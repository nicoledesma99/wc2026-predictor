import os
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

URL = (
    "https://raw.githubusercontent.com/"
    "martj42/international_results/"
    "master/results.csv"
)
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "raw", "results.csv"
)


def download_historical_data(url: str = URL, dest: str = OUTPUT_PATH) -> str:
    dest = os.path.abspath(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    logger.info("Descargando datos históricos desde %s", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    with open(dest, "wb") as f:
        f.write(response.content)

    size_kb = len(response.content) / 1024
    logger.info("Guardado en %s (%.1f KB)", dest, size_kb)
    return dest


if __name__ == "__main__":
    path = download_historical_data()
    print(f"Descarga completada: {path}")
