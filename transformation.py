"""
Module de TRANSFORMATION - Nettoyage, validation et enrichissement
Part du pipeline ETL (le "T")
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Tuple

logger = logging.getLogger(__name__)


class FlightTransformer:
    """Transforme et enrichit les données brutes d'avions"""
    
    @staticmethod
    def clean_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Nettoyage des données
        - Suppression des valeurs nulles critiques
        - Conversion de types
        - Validation des coordonnées
        """
        
        df = df.copy()
        
        # Suppression des avions sans coordonnées GPS
        df = df[df[['latitude', 'longitude']].notna().all(axis=1)]
        
        # Suppression des altitudes impossibles
        df = df[(df['baro_altitude'].isna()) | 
                ((df['baro_altitude'] >= -1000) & (df['baro_altitude'] <= 45000))]
        
        # Convertion timestamps
        df['time_position'] = pd.to_datetime(df['time_position'], unit='s', errors='coerce')
        df['last_contact'] = pd.to_datetime(df['last_contact'], unit='s', errors='coerce')
        
        # Nettoyage indificatif d'appel
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
        Enrichissement avec calculs géométriques pour le radar
        
        Args:
            df: DataFrame nettoyé
            reference_lat, reference_lon: Centre du radar
            reference_alt: Altitude de l'observateur
        """
        
        df = df.copy()
        
        # 1. Distance horizontale
        df['distance_km'] = FlightTransformer._haversine_distance(
            reference_lat, reference_lon,
            df['latitude'], df['longitude']
        )
        
        # Azimut
        df['azimuth'] = FlightTransformer._calculate_bearing(
            reference_lat, reference_lon,
            df['latitude'], df['longitude']
        )
        
        # altitude relative
        df['altitude_relative'] = df['baro_altitude'].fillna(0) - reference_alt
        
        # Distance 3D
        distance_3d_m = np.sqrt(
            (df['distance_km'] * 1000) ** 2 + 
            df['altitude_relative'] ** 2
        )
        df['distance_3d_km'] = distance_3d_m / 1000
        
        #  Angle d'élévation
        df['elevation_angle'] = np.arctan2(
            df['altitude_relative'],
            df['distance_km'] * 1000
        )
        df['elevation_angle'] = np.degrees(df['elevation_angle'])
        
        df['altitude_category'] = pd.cut(
            df['baro_altitude'].fillna(0),
            bins=[-np.inf, 3000, 6000, 10000, 15000, np.inf],
            labels=['Sol', 'Basse', 'Moyenne', 'Haute', 'Très haute']
        )
        
        df['speed_category'] = pd.cut(
            df['velocity'].fillna(0),
            bins=[-np.inf, 100, 300, 500, np.inf],
            labels=['Lent', 'Normal', 'Rapide', 'Très rapide'],
            include_lowest=True
        )
        
        df['airline_code'] = df['callsign'].str[:3]
        
       
        df['status'] = df['on_ground'].apply(
            lambda x: 'Sol' if x else 'Vol' if x is False else 'Inconnu'
        )
        
        return df
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> np.ndarray:
        """Distance entre deux points géographiques en km"""
        R = 6371  # rayon de la terre
        
        lat1, lon1 = np.radians(lat1), np.radians(lon1)
        lat2, lon2 = np.radians(lat2), np.radians(lon2)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        
        return R * c
    
    @staticmethod
    def _calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> np.ndarray:
        """Azimut en degrés (0-360, 0=Nord)"""
        lat1, lon1 = np.radians(lat1), np.radians(lon1)
        lat2, lon2 = np.radians(lat2), np.radians(lon2)
        
        dlon = lon2 - lon1
        
        x = np.sin(dlon) * np.cos(lat2)
        y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
        
        bearing = np.arctan2(x, y)
        bearing = np.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    @staticmethod
    def filter_by_distance(df: pd.DataFrame, max_distance_km: float = 100) -> pd.DataFrame:
        """Filtre les avions au-delà d'une distance max"""
        df_filtered = df[df['distance_km'] <= max_distance_km].copy()
        logger.info(f" {len(df_filtered)} avions dans la zone")
        return df_filtered
    
    @staticmethod
    def add_metadata(df: pd.DataFrame) -> pd.DataFrame:
        """Ajoute métadonnées de processing"""
        df = df.copy()
        df['processed_at'] = datetime.now()
        df['pipeline_version'] = '1.0'
        return df


class TransformationPipeline:
    """Orchestre l'ensemble du pipeline de transformation"""
    
    def __init__(self, reference_lat: float, reference_lon: float, reference_alt: float = 0):
        self.reference_lat = reference_lat
        self.reference_lon = reference_lon
        self.reference_alt = reference_alt
        self.transformer = FlightTransformer()
    
    def execute(self, raw_df: pd.DataFrame, max_distance_km: float = 100) -> pd.DataFrame:
        """
        Exécute la pipeline complète de transformation
        
        Returns:
            DataFrame transformé et prêt pour visualisation
        """
        logger.info("\n" + "="*50)
        logger.info("DÉBUT TRANSFORMATION PIPELINE")
        logger.info("="*50)
        
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


if __name__ == "__main__":
    from extraction import extract_flights_around_location
    
    # Point de coordonnées de Aulnay sous bois
    aulnay_lat, aulnay_lon = 48.9531, 2.5048
    raw_data = extract_flights_around_location(aulnay_lat, aulnay_lon, radius_km=100)
    
    if not raw_data.empty:
        pipeline = TransformationPipeline(aulnay_lat, aulnay_lon)
        transformed_data = pipeline.execute(raw_data, max_distance_km=100)
        
        print("\n Aperçu des données transformées:")
        print(transformed_data[['callsign', 'distance_km', 'azimuth', 'altitude_relative']].head(10))
