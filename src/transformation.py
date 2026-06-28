"""
Module de TRANSFORMATION - Nettoyage, validation et enrichissement.
Partie "T" du pipeline ETL.
"""

import logging
from typing import Tuple
import numpy as np
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class FlightTransformer:
    """Transforme et enrichit les données brutes d'avions."""
    
    @staticmethod
    def clean_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Nettoyage des données :
        - Suppression des valeurs nulles critiques (coordonnées GPS)
        - Conversion de types (timestamps)
        - Validation des coordonnées et altitudes
        """
        df = df.copy()
        
        # Suppression des avions sans coordonnées GPS
        df = df[df[['latitude', 'longitude']].notna().all(axis=1)]
        
        # Suppression des altitudes impossibles
        df = df[(df['baro_altitude'].isna()) | 
                ((df['baro_altitude'] >= -1000) & (df['baro_altitude'] <= 45000))]
        
        # Conversion des timestamps
        df['time_position'] = pd.to_datetime(df['time_position'], unit='s', errors='coerce')
        df['last_contact'] = pd.to_datetime(df['last_contact'], unit='s', errors='coerce')
        
        # Nettoyage indicatif d'appel
        df['callsign'] = df['callsign'].fillna('UNKNOWN').str.strip()
        
        return df
    
    @staticmethod
    def enrich_with_calculations(
        df: pd.DataFrame,
        reference_lat: float,
        reference_lon: float,
        reference_alt: float = 0
    ) -> pd.DataFrame:
        """
        Enrichissement avec calculs géométriques pour le radar.
        
        Args:
            df: DataFrame nettoyé
            reference_lat, reference_lon: Centre du radar
            reference_alt: Altitude de l'observateur (mètres)
        """
        df = df.copy()
        
        # 1. Distance horizontale
        df['distance_km'] = FlightTransformer._haversine_distance(
            reference_lat, reference_lon,
            df['latitude'].to_numpy(), df['longitude'].to_numpy()
        )
        
        # 2. Azimut (bearing)
        df['azimuth'] = FlightTransformer._calculate_bearing(
            reference_lat, reference_lon,
            df['latitude'].to_numpy(), df['longitude'].to_numpy()
        )
        
        # 3. Altitude relative
        df['altitude_relative'] = df['baro_altitude'].fillna(0) - reference_alt
        
        # 4. Distance 3D en km
        distance_3d_m = np.sqrt(
            (df['distance_km'] * 1000) ** 2 + 
            df['altitude_relative'] ** 2
        )
        df['distance_3d_km'] = distance_3d_m / 1000.0
        
        # 5. Angle d'élévation en degrés
        df['elevation_angle'] = np.degrees(
            np.arctan2(df['altitude_relative'], df['distance_km'] * 1000)
        )
        
        # 6. Catégorisation de l'altitude
        df['altitude_category'] = pd.cut(
            df['baro_altitude'].fillna(0),
            bins=[-np.inf, 3000, 6000, 10000, 15000, np.inf],
            labels=['Sol', 'Basse', 'Moyenne', 'Haute', 'Très haute']
        ).astype(str)
        
        # 7. Catégorisation de la vitesse
        df['speed_category'] = pd.cut(
            df['velocity'].fillna(0),
            bins=[-np.inf, 100, 300, 500, np.inf],
            labels=['Lent', 'Normal', 'Rapide', 'Très rapide'],
            include_lowest=True
        ).astype(str)
        
        # 8. Code de compagnie aérienne (3 premières lettres du callsign)
        df['airline_code'] = df['callsign'].str[:3]
        
        # 9. Statut simplifié
        df['status'] = df['on_ground'].apply(
            lambda x: 'Sol' if x else 'Vol' if x is False else 'Inconnu'
        )
        
        return df
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
        """Calcule la distance horizontale en km entre un point et une série de points."""
        r_earth = 6371.0  # rayon de la terre en km
        
        lat1_rad = np.radians(lat1)
        lon1_rad = np.radians(lon1)
        lat2_rad = np.radians(lat2)
        lon2_rad = np.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        
        return r_earth * c
    
    @staticmethod
    def _calculate_bearing(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
        """Calcule l'azimut en degrés (0-360, 0=Nord) entre un point et une série de points."""
        lat1_rad = np.radians(lat1)
        lon1_rad = np.radians(lon1)
        lat2_rad = np.radians(lat2)
        lon2_rad = np.radians(lon2)
        
        dlon = lon2_rad - lon1_rad
        
        x = np.sin(dlon) * np.cos(lat2_rad)
        y = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(dlon)
        
        bearing = np.arctan2(x, y)
        bearing = np.degrees(bearing)
        bearing = (bearing + 360.0) % 360.0
        
        return bearing
    
    @staticmethod
    def filter_by_distance(df: pd.DataFrame, max_distance_km: float = 100.0) -> pd.DataFrame:
        """Filtre les avions au-delà d'une distance maximale."""
        df_filtered = df[df['distance_km'] <= max_distance_km].copy()
        logger.info(f"Filtrage : {len(df_filtered)} avions dans la zone <= {max_distance_km}km")
        return df_filtered
    
    @staticmethod
    def add_metadata(df: pd.DataFrame) -> pd.DataFrame:
        """Ajoute des métadonnées de traitement."""
        df = df.copy()
        df['processed_at'] = datetime.now()
        df['pipeline_version'] = '1.0'
        return df


class TransformationPipeline:
    """Orchestre l'ensemble du pipeline de transformation."""
    
    reference_lat: float
    reference_lon: float
    reference_alt: float
    transformer: FlightTransformer
    
    def __init__(self, reference_lat: float, reference_lon: float, reference_alt: float = 0.0) -> None:
        self.reference_lat = reference_lat
        self.reference_lon = reference_lon
        self.reference_alt = reference_alt
        self.transformer = FlightTransformer()
    
    def execute(self, raw_df: pd.DataFrame, max_distance_km: float = 100.0) -> pd.DataFrame:
        """
        Exécute le pipeline complet de transformation.
        
        Returns:
            DataFrame transformé et enrichi
        """
        df_clean = self.transformer.clean_data(raw_df)
        
        df_enriched = self.transformer.enrich_with_calculations(
            df_clean,
            self.reference_lat,
            self.reference_lon,
            self.reference_alt
        )
        
        df_filtered = self.transformer.filter_by_distance(df_enriched, max_distance_km)
        df_final = self.transformer.add_metadata(df_filtered)
        
        return df_final
