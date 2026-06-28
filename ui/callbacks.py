"""
Enregistrement des callbacks Dash et logique d'interaction.
"""

import json
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, ALL
from typing import Tuple, Dict, Any, List, Optional

import config.settings as settings
from src.extraction import OpenSkyExtractor
from src.transformation import TransformationPipeline
from src.loading import DatabaseLoader
from ui.graphs import render_polar_radar, render_3d_airspace
from ui.components import render_telemetry_panel, render_flight_list

logger = logging.getLogger(__name__)

# Initialisation des services ETL
extractor = OpenSkyExtractor()
transformer = TransformationPipeline(settings.CENTER_LAT, settings.CENTER_LON)
loader = DatabaseLoader(settings.DB_PATH)

global_history = pd.DataFrame()


def register_callbacks(app: dash.Dash) -> None:
    """Enregistre tous les callbacks sur l'application Dash."""
    
    # 1. Mise à jour de l'horloge
    @app.callback(
        Output('live-clock', 'children'),
        Input('clock-interval', 'n_intervals')
    )
    def update_clock(n: int) -> str:
        return datetime.now().strftime("%d %b %Y %H:%M:%S").upper()

    # 2. Basculement de la vue (2D/3D)
    @app.callback(
        [Output('btn-view-2d', 'className'),
         Output('btn-view-3d', 'className'),
         Output('current-view-store', 'data')],
        [Input('btn-view-2d', 'n_clicks'),
         Input('btn-view-3d', 'n_clicks')],
        [State('current-view-store', 'data')]
    )
    def toggle_view(click_2d: int, click_3d: int, current_view: str) -> Tuple[str, str, str]:
        ctx = dash.callback_context
        if not ctx.triggered:
            return "view-btn active", "view-btn", "2D"
            
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == "btn-view-2d":
            return "view-btn active", "view-btn", "2D"
        elif button_id == "btn-view-3d":
            return "view-btn", "view-btn active", "3D"
        return "view-btn active", "view-btn", "2D"

    # 3. Acquisition périodique des données
    @app.callback(
        Output('data-store', 'data'),
        Input('data-interval', 'n_intervals')
    )
    def refresh_data(n: int) -> Dict[str, Any]:
        df_new, stats = _fetch_and_process_data()
        return {
            'current': df_new.to_dict('records') if not df_new.empty else [],
            'stats': stats,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }

    # 4. Sélection de cible (clic radar ou clic carte)
    @app.callback(
        Output('selected-aircraft-store', 'data'),
        [Input('radar-graph', 'clickData'),
         Input({'type': 'flight-card', 'index': ALL}, 'n_clicks')],
        [State('selected-aircraft-store', 'data')],
        prevent_initial_call=True
    )
    def handle_target_selection(radar_click: Optional[dict], card_clicks: List[int], current_selected: Optional[str]) -> Optional[str]:
        ctx = dash.callback_context
        if not ctx.triggered:
            return current_selected
            
        trigger_id = ctx.triggered[0]['prop_id']
        
        if "radar-graph" in trigger_id:
            return _get_icao_from_radar_click(radar_click)
        elif "flight-card" in trigger_id:
            return _get_icao_from_card_click(trigger_id)
            
        return current_selected

    # 5. Rendu dynamique du conteneur Viewport (2D ou 3D)
    @app.callback(
        Output('radar-viewport-container', 'children'),
        [Input('current-view-store', 'data')]
    )
    def render_viewport(current_view: str) -> html.Div:
        if current_view == "2D":
            return html.Div([
                html.Div(className="radar-sweep-effect"),
                html.Div(className="radar-grid-decors"),
                html.Div(className="radar-crosshair-h"),
                html.Div(className="radar-crosshair-v"),
                dcc.Graph(
                    id='radar-graph',
                    className='radar-plotly-graph',
                    config={'displayModeBar': False, 'scrollZoom': False}
                )
            ], style={'position': 'relative', 'width': '100%', 'height': '100%', 'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center'})
        else:
            return dcc.Graph(
                id='graph-3d',
                className='three-d-plotly-graph',
                config={'displayModeBar': True}
            )

    # 6. Rendu centralisé des éléments filtrés et KPIs
    @app.callback(
        [Output('radar-graph', 'figure'),
         Output('graph-3d', 'figure'),
         Output('flight-list', 'children'),
         Output('kpi-targets', 'children'),
         Output('kpi-alt-avg', 'children'),
         Output('kpi-speed-max', 'children'),
         Output('kpi-unique', 'children'),
         Output('telemetry-panel', 'children'),
         Output('scanning-status-text', 'children')],
        [Input('data-store', 'data'),
         Input('range-slider', 'value'),
         Input('altitude-filter', 'value'),
         Input('callsign-search', 'value'),
         Input('selected-aircraft-store', 'data')],
        [State('current-view-store', 'data')]
    )
    def update_dashboard_elements(
        data: Dict[str, Any],
        max_range: float,
        alt_filter: str,
        search_callsign: Optional[str],
        selected_icao: Optional[str],
        current_view: str
    ) -> Tuple[Any, Any, Any, str, str, str, str, Any, str]:
        
        # Si aucune donnée, retourner l'état vide
        if not data or not data.get('current'):
            empty_fig = render_polar_radar(pd.DataFrame(), max_range, None)
            no_telemetry = render_telemetry_panel(None)
            return (empty_fig, empty_fig, html.Div("Aucun appareil détecté.", style={'textAlign': 'center', 'marginTop': '20px'}),
                    "00", "0 m", "0 km/h", "0", no_telemetry, "SCANNING...")
        
        df = pd.DataFrame(data['current'])
        
        # 1. Filtrage local
        df_filtered = _filter_local_data(df, max_range, alt_filter, search_callsign)
        
        # 2. Calcul des statistiques (KPIs)
        kpi_targets, kpi_alt, kpi_speed, kpi_unique = _calculate_kpis(df_filtered)
        scanner_text = f"TRACKING {len(df_filtered)} TARGETS" if not df_filtered.empty else "SCANNING AIRSPACE..."
        
        # 3. Recherche de la cible active pour la télémétrie
        selected_row: Optional[pd.Series] = None
        if selected_icao:
            matches = df[df['icao24'] == selected_icao]
            if not matches.empty:
                selected_row = matches.iloc[0]
                
        # 4. Rendu des composants visuels
        fig_radar = render_polar_radar(df_filtered, max_range, selected_icao)
        fig_3d = render_3d_airspace(df_filtered, max_range, selected_icao) if current_view == "3D" else go.Figure()
        flight_list_elements = render_flight_list(df_filtered, selected_icao)
        telemetry_element = render_telemetry_panel(selected_row)
        
        return (fig_radar, fig_3d, flight_list_elements,
                kpi_targets, kpi_alt, kpi_speed, kpi_unique,
                telemetry_element, scanner_text)


# --- Fonctions d'aide internes (Private, < 50 lignes) ---

def _fetch_and_process_data() -> Tuple[pd.DataFrame, dict]:
    """Récupère les données brutes et les transforme via le pipeline ETL."""
    global global_history
    try:
        radius = settings.FETCH_RADIUS_KM / 111.0
        df_raw = extractor.get_flights_in_bounding_box(
            lat_min=settings.CENTER_LAT - radius,
            lat_max=settings.CENTER_LAT + radius,
            lon_min=settings.CENTER_LON - radius / np.cos(np.radians(settings.CENTER_LAT)),
            lon_max=settings.CENTER_LON + radius / np.cos(np.radians(settings.CENTER_LAT))
        )
        
        if df_raw.empty:
            return pd.DataFrame(), {'count': 0, 'timestamp': datetime.now()}
            
        df_transformed = transformer.execute(df_raw, max_distance_km=settings.FETCH_RADIUS_KM)
        
        if not df_transformed.empty:
            loader.load_dataframe(df_transformed, if_exists='append')
            # Mise à jour historique glissant
            df_transformed['update_time'] = datetime.now()
            global_history = pd.concat([global_history, df_transformed], ignore_index=True)
            cutoff = datetime.now() - timedelta(hours=1)
            global_history = global_history[pd.to_datetime(global_history['update_time']) > cutoff]
            
        stats = {
            'count': len(df_transformed),
            'timestamp': datetime.now(),
            'unique_aircraft': df_transformed['icao24'].nunique() if not df_transformed.empty else 0,
            'avg_altitude': df_transformed['baro_altitude'].mean() if not df_transformed.empty else 0,
            'max_velocity': df_transformed['velocity'].max() if not df_transformed.empty else 0
        }
        return df_transformed, stats
    except Exception as e:
        logger.error(f"Erreur d'acquisition : {e}")
        return pd.DataFrame(), {'count': 0, 'timestamp': datetime.now(), 'error': str(e)}


def _filter_local_data(df: pd.DataFrame, max_range: float, alt_filter: str, search_callsign: Optional[str]) -> pd.DataFrame:
    """Filtre localement le DataFrame selon la distance, l'altitude et la recherche."""
    df_filtered = df[df['distance_km'] <= max_range].copy()
    
    if alt_filter != 'ALL':
        df_filtered = df_filtered[df_filtered['altitude_category'] == alt_filter]
        
    if search_callsign:
        search_val = search_callsign.strip().upper()
        df_filtered = df_filtered[df_filtered['callsign'].str.upper().str.contains(search_val)]
        
    return df_filtered.sort_values('distance_km')


def _calculate_kpis(df: pd.DataFrame) -> Tuple[str, str, str, str]:
    """Calcule les KPIs textuels pour l'affichage."""
    count = len(df)
    kpi_targets = f"{count:02d}"
    
    avg_alt = df['baro_altitude'].mean() if count > 0 else 0
    kpi_alt = f"{avg_alt:.0f} m" if avg_alt > 0 else "0 m"
    
    max_speed = df['velocity'].max() if count > 0 else 0
    kpi_speed = f"{max_speed * 3.6:.0f} km/h" if max_speed > 0 else "0 km/h"
    
    unique_count = df['icao24'].nunique() if count > 0 else 0
    kpi_unique = f"{unique_count}"
    
    return kpi_targets, kpi_alt, kpi_speed, kpi_unique


def _get_icao_from_radar_click(click_data: Optional[dict]) -> Optional[str]:
    """Extrait l'adresse ICAO depuis un clic sur le graphique radar."""
    if click_data and 'points' in click_data:
        point = click_data['points'][0]
        if 'customdata' in point:
            return str(point['customdata'])
    return None


def _get_icao_from_card_click(trigger_id: str) -> Optional[str]:
    """Extrait l'adresse ICAO depuis l'ID d'une carte cliquée."""
    try:
        component_id_str = trigger_id.split('.n_clicks')[0]
        component_id = json.loads(component_id_str)
        return str(component_id['index'])
    except Exception as e:
        logger.error(f"Erreur d'extraction de l'ID cliqué : {e}")
    return None
