"""
Module de CHARGEMENT - Persistance des données en base SQLite.
Partie "L" du pipeline ETL.
"""

import logging
import pandas as pd
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean
from sqlalchemy.orm import declarative_base, Session
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

Base = declarative_base()


class AircraftRecord(Base):
    """Modèle ORM SQLAlchemy pour les enregistrements de vols."""
    __tablename__ = 'aircraft'
    
    id = Column(Integer, primary_key=True)
    icao24 = Column(String(10), unique=True)
    callsign = Column(String(10))
    origin_country = Column(String(50))
    latitude = Column(Float)
    longitude = Column(Float)
    baro_altitude = Column(Float)
    velocity = Column(Float)
    true_track = Column(Float)
    vertical_rate = Column(Float)
    
    distance_km = Column(Float)
    azimuth = Column(Float)
    altitude_relative = Column(Float)
    elevation_angle = Column(Float)
    altitude_category = Column(String(20))
    speed_category = Column(String(20))
    airline_code = Column(String(10))
    status = Column(String(20))
    
    # Timestamps
    time_position = Column(DateTime)
    last_contact = Column(DateTime)
    processed_at = Column(DateTime)
    
    on_ground = Column(Boolean)


class DatabaseLoader:
    """Gère le chargement et la lecture des données dans SQLite."""
    
    db_path: str
    engine: Any
    
    def __init__(self, db_path: str = "aircraft_radar.db") -> None:
        """
        Initialise la connexion à la base de données.
        
        Args:
            db_path: Chemin du fichier SQLite
        """
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}')
        
        # Crée les tables si elles n'existent pas
        Base.metadata.create_all(self.engine)
    
    def load_dataframe(self, df: pd.DataFrame, if_exists: str = 'append') -> int:
        """
        Charge un DataFrame dans la base de données.
        
        Args:
            df: DataFrame transformé
            if_exists: 'fail', 'replace', 'append'
        
        Returns:
            Nombre de lignes chargées
        """
        if df.empty:
            return 0
            
        logger.info(f"Chargement en base : {len(df)} enregistrements")
        
        try:
            # Sélectionne les colonnes qui correspondent au modèle
            columns_to_load = [col for col in df.columns if col in AircraftRecord.__table__.columns]
            df_load = df[columns_to_load].copy()
            
            df_load.to_sql(
                'aircraft',
                con=self.engine,
                if_exists=if_exists,
                index=False
            )
            return len(df_load)
        
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données en base SQLite: {e}")
            return 0
    
    def query_recent_flights(self, limit: int = 100, hours_back: int = 1) -> pd.DataFrame:
        """
        Récupère les vols récents depuis la base de données.
        
        Args:
            limit: Nombre max de résultats
            hours_back: Heures à remonter dans le temps
        
        Returns:
            DataFrame des vols récents
        """
        query = f"""
        SELECT *
        FROM aircraft
        WHERE processed_at >= datetime('now', '-{hours_back} hours')
        ORDER BY processed_at DESC
        LIMIT {limit}
        """
        
        try:
            df = pd.read_sql_query(query, self.engine)
            return df
        except Exception as e:
            logger.error(f"Erreur lors de la requête des vols récents : {e}")
            return pd.DataFrame()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Récupère des statistiques globales sur la base."""
        try:
            with Session(self.engine) as session:
                total_records = session.query(AircraftRecord).count()
                unique_aircraft = session.query(AircraftRecord.icao24).distinct().count()
                
                return {
                    'total_records': total_records,
                    'unique_aircraft': unique_aircraft,
                    'db_path': self.db_path,
                    'timestamp': datetime.now()
                }
        except Exception as e:
            logger.error(f"Erreur lors du calcul des statistiques de base : {e}")
            return {}
    
    def export_to_csv(self, output_path: str, hours_back: int = 24) -> bool:
        """Exporte les données récentes dans un fichier CSV."""
        try:
            df = self.query_recent_flights(limit=10000, hours_back=hours_back)
            if not df.empty:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                df.to_csv(output_path, index=False)
                return True
            else:
                logger.warning("Aucune donnée à exporter")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de l'export CSV : {e}")
            return False
            
    def cleanup_old_data(self, days_to_keep: int = 7) -> int:
        """Supprime les données antérieures à N jours."""
        try:
            with Session(self.engine) as session:
                from datetime import timedelta
                cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                cutoff_date -= timedelta(days=days_to_keep)
                
                count = session.query(AircraftRecord).filter(
                    AircraftRecord.processed_at < cutoff_date
                ).delete()
                
                session.commit()
                return count
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de la base de données : {e}")
            return 0
