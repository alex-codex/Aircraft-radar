"""
Module d'EXTRACTION - Récupération des données depuis OpenSky API.
Partie "E" du pipeline ETL.
"""

import logging
from typing import Optional
import pandas as pd
from opensky_api import OpenSkyApi, TokenManager
import config.settings as settings

logger = logging.getLogger(__name__)


class OpenSkyExtractor:
    """Extracteur de données depuis l'API OpenSky."""
    
    api: OpenSkyApi

    def __init__(self) -> None:
        """Initialise la connexion avec TokenManager ou en mode anonyme."""
        try:
            client_id: str = settings.OPENSKY_CLIENT_ID
            client_secret: str = settings.OPENSKY_CLIENT_SECRET
            
            if client_id and client_secret:
                token_manager = TokenManager(
                    client_id=client_id,
                    client_secret=client_secret
                )
                self.api = OpenSkyApi(token_manager=token_manager)
                logger.info("Connecté avec TokenManager à OpenSky")
            else:
                # Mode anonyme
                self.api = OpenSkyApi()
                logger.info("Connecté en mode anonyme à OpenSky")
        
        except Exception as e:
            logger.error(f"Erreur d'initialisation de l'API OpenSky : {e}")
            raise
    
    def get_flights_in_bounding_box(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        time_secs: int = 0
    ) -> pd.DataFrame:
        """
        Récupère les vecteurs d'état des avions dans une zone géographique.
        
        Args:
            lat_min: Latitude minimale
            lat_max: Latitude maximale
            lon_min: Longitude minimale
            lon_max: Longitude maximale
            time_secs: Timestamp Unix (0 pour les données temps réel)
        
        Returns:
            DataFrame Pandas contenant les données des vecteurs d'état
        """
        bbox_tuple = (lat_min, lat_max, lon_min, lon_max)
        
        try:
            states = self.api.get_states(
                time_secs=time_secs,
                bbox=bbox_tuple
            )
            
            if not states or not states.states:
                logger.warning("Aucun avion détecté dans cette zone ou limite de requêtes atteinte")
                return pd.DataFrame()
            
            raw_data = [state.__dict__ for state in states.states]
            df = pd.DataFrame(raw_data)
            return df
            
        except ValueError as ve:
            logger.error(f"Erreur de validation des coordonnées géographiques: {ve}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données OpenSky: {e}")
            return pd.DataFrame()

    def close(self) -> None:
        """Ferme proprement la session OpenSky."""
        if hasattr(self, 'api'):
            try:
                self.api.close()
                logger.info("Session OpenSky fermée.")
            except Exception as e:
                logger.error(f"Erreur lors de la fermeture de la session API : {e}")
                
        # Nettoyage si necessaire
