"""
Module de configuration et de gestion des variables d'environnement.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Chemin racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent

# Chargement des variables d'environnement (.env)
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Identifiants API OpenSky
OPENSKY_USERNAME: str = os.getenv("OPENSKY_USERNAME", "")
OPENSKY_PASSWORD: str = os.getenv("OPENSKY_PASSWORD", "")
OPENSKY_CLIENT_ID: str = os.getenv("OPENSKY_CLIENT_ID", "")
OPENSKY_CLIENT_SECRET: str = os.getenv("OPENSKY_CLIENT_SECRET", "")

# Coordonnées géographiques du centre du radar (Houilles par défaut)
CENTER_LAT: float = float(os.getenv("CENTER_LAT", 48.926916))
CENTER_LON: float = float(os.getenv("CENTER_LON", 2.18888))
LOCATION_NAME: str = os.getenv("LOCATION_NAME", "HOUILLES")

# Paramètres de rafraîchissement et de portée
REFRESH_INTERVAL_SEC: int = int(os.getenv("REFRESH_INTERVAL_SEC", 30))
FETCH_RADIUS_KM: float = float(os.getenv("FETCH_RADIUS_KM", 100.0))
DEFAULT_MAX_RANGE_KM: float = float(os.getenv("DEFAULT_MAX_RANGE_KM", 35.0))

# Base de données
DB_PATH: str = os.getenv("DB_PATH", "aircraft_realtime.db")
