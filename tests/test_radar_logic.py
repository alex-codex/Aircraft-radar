"""
Tests unitaires pour la logique de filtrage et de calculs géométriques du radar.
"""

import unittest
import pandas as pd
import numpy as np
from ui.components import _get_cardinal_direction
from ui.callbacks import _filter_local_data


class TestRadarLogic(unittest.TestCase):

    def test_cardinal_direction(self) -> None:
        """Vérifie la conversion des angles de cap en directions cardinales."""
        # Nord
        self.assertEqual(_get_cardinal_direction(0), "0° (N)")
        self.assertEqual(_get_cardinal_direction(360), "360° (N)")
        self.assertEqual(_get_cardinal_direction(350), "350° (N)")
        self.assertEqual(_get_cardinal_direction(10), "10° (N)")
        
        # Est, Sud, Ouest
        self.assertEqual(_get_cardinal_direction(90), "90° (E)")
        self.assertEqual(_get_cardinal_direction(180), "180° (S)")
        self.assertEqual(_get_cardinal_direction(270), "270° (W)")
        
        # Intermédiaires
        self.assertEqual(_get_cardinal_direction(45), "45° (NE)")
        self.assertEqual(_get_cardinal_direction(135), "135° (SE)")
        self.assertEqual(_get_cardinal_direction(225), "225° (SW)")
        self.assertEqual(_get_cardinal_direction(315), "315° (NW)")
        
        # Cas limites / valeurs manquantes
        self.assertEqual(_get_cardinal_direction(None), "N/A")
        self.assertEqual(_get_cardinal_direction(np.nan), "N/A")

    def test_filter_local_data(self) -> None:
        """Vérifie le bon fonctionnement du filtrage local multicritère."""
        # Création d'un jeu de données de test
        data = {
            'icao24': ['3c65a1', '3c65a2', '3c65a3', '3c65a4'],
            'callsign': ['AFR123', 'DLH456', 'BAW789', 'AFR999'],
            'distance_km': [10.0, 25.0, 45.0, 60.0],
            'altitude_category': ['Sol', 'Basse', 'Moyenne', 'Haute'],
            'baro_altitude': [500, 4500, 8500, 12000]
        }
        df = pd.DataFrame(data)
        
        # Test 1 : Filtrage par distance (max 30km)
        df_dist = _filter_local_data(df, max_range=30.0, alt_filter='ALL', search_callsign=None)
        self.assertEqual(len(df_dist), 2)
        self.assertListEqual(df_dist['icao24'].tolist(), ['3c65a1', '3c65a2'])
        
        # Test 2 : Filtrage par altitude ('Moyenne')
        df_alt = _filter_local_data(df, max_range=100.0, alt_filter='Moyenne', search_callsign=None)
        self.assertEqual(len(df_alt), 1)
        self.assertEqual(df_alt.iloc[0]['icao24'], '3c65a3')
        
        # Test 3 : Filtrage par indicatif ('AFR')
        df_search = _filter_local_data(df, max_range=100.0, alt_filter='ALL', search_callsign='AFR')
        self.assertEqual(len(df_search), 2)
        self.assertListEqual(df_search['callsign'].tolist(), ['AFR123', 'AFR999'])
        
        # Test 4 : Filtrage combiné (distance <= 50km AND search 'AFR')
        df_comb = _filter_local_data(df, max_range=50.0, alt_filter='ALL', search_callsign='AFR')
        self.assertEqual(len(df_comb), 1)
        self.assertEqual(df_comb.iloc[0]['callsign'], 'AFR123')


if __name__ == '__main__':
    unittest.main()
