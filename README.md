# Mundial 2026 Predictor

Modelo de predicción para la Copa del Mundo 2026 usando datos históricos de partidos internacionales y la API de football-data.org.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tu API key de football-data.org
```

## Estructura

- `data/raw/` — datos crudos descargados
- `data/processed/` — datos procesados para modelos
- `data/models/` — modelos entrenados (.pkl)
- `src/data/` — scripts de descarga y feature engineering
- `src/models/` — entrenamiento y predicción
- `src/api/` — FastAPI para servir predicciones
- `notebooks/` — exploración y análisis

## Uso

```bash
# Descargar datos históricos
python src/data/fetch_historical.py

# Testear la API
python src/data/test_api.py
```
