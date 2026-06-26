"""
Module de CHARGEMENT
"""

import logging
import pandas as pd
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean
from sqlalchemy.orm import declarative_base, Session
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

Base = declarative_base()


class AircraftRecord(Base):
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
    
    def __init__(self, db_path: str = "aircraft_radar.db"):
        """
        Initialise la connexion à la base de données
        
        Args:
            db_path: Chemin du fichier SQLite
        """
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}')
        
        # Crée les tables si elles n'existent pas
        Base.metadata.create_all(self.engine)
    
    def load_dataframe(self, df: pd.DataFrame, if_exists: str = 'append') -> int:
        """
        Charge un DataFrame dans la base de données
        
        Args:
            df: DataFrame transformé
            if_exists: 'fail', 'replace', 'append'
        
        Returns:
            Nombre de lignes chargées
        """
        logger.info(f" Chargement: {len(df)} enregistrements")
        
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
            logger.error(f"Erreur :{e}")
            return 0
    
    def query_recent_flights(self, limit: int = 100, hours_back: int = 1) -> pd.DataFrame:
        """
        Récupère les vols récents depuis la base de données
        
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
            logger.error(f"Erreur requête: {e}")
            return pd.DataFrame()
    
    def get_statistics(self) -> dict:
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
            logger.error(f"Erreur stats: {e}")
            return {}
    
    def export_to_csv(self, output_path: str, hours_back: int = 24) -> bool:
        
        try:
            df = self.query_recent_flights(limit=10000, hours_back=hours_back)
            if not df.empty:
                df.to_csv(output_path, index=False)
                return True
            else:
                logger.warning("Aucune donnée à exporter")
                return False
        except Exception as e:
            logger.error(f"Erreur export: {e}")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 7) -> int:
        """
        Supprime les données antérieures à N jours
        
        Args:
            days_to_keep: Nombre de jours à conserver
        
        Returns:
            Nombre de lignes supprimées
        """
        
        try:
            with Session(self.engine) as session:
                cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                from datetime import timedelta
                cutoff_date -= timedelta(days=days_to_keep)
                
                count = session.query(AircraftRecord).filter(
                    AircraftRecord.processed_at < cutoff_date
                ).delete()
                
                session.commit()
                return count
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")
            return 0


class CSVLoader:

    
    @staticmethod
    def save_to_csv(df: pd.DataFrame, output_path: str) -> bool:
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_path, index=False)
            return True
        except Exception as e:
            logger.error(f"Erreur CSV: {e}")
            return False
    
    @staticmethod
    def load_from_csv(file_path: str) -> pd.DataFrame:
        try:
            df = pd.read_csv(file_path)
            return df
        except Exception as e:
            logger.error(f"Erreur: {e}")
            return pd.DataFrame()


if __name__ == "__main__":
   
    loader = DatabaseLoader("test_aircraft.db")
    
    stats = loader.get_statistics()
    print(f"\n Statistiques base de données:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
