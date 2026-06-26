"""
DASHBOARD TEMPS RÉEL - Mise à jour toutes les x secondes

"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple

import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go

from extraction import OpenSkyExtractor
from transformation import TransformationPipeline
from loading import DatabaseLoader

import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



load_dotenv()

USERNAME = os.getenv("OPENSKY_USERNAME")
PASSWORD = os.getenv("OPENSKY_PASSWORD")


# Configuration
CENTER_LAT = 48.926916
CENTER_LON = 2.18888
LOCATION_NAME = "HOUILLES"
REFRESH_INTERVAL = 1  # en minute
MAX_DISTANCE = 30 
HISTORY_HOURS = 1 


extractor = OpenSkyExtractor()
transformer = TransformationPipeline(CENTER_LAT, CENTER_LON)
loader = DatabaseLoader("aircraft_realtime.db")


global_history = pd.DataFrame()


def fetch_and_transform_data() -> Tuple[pd.DataFrame, dict]:
    """
    Récupère et transforme les données
    
    Returns:
        (DataFrame transformé, statistiques)
    """
    try:
        
        radius = MAX_DISTANCE / 111.0
        df_raw = extractor.get_flights_in_bounding_box(
            lat_min=CENTER_LAT - radius,
            lat_max=CENTER_LAT + radius,
            lon_min=CENTER_LON - radius / np.cos(np.radians(CENTER_LAT)),
            lon_max=CENTER_LON + radius / np.cos(np.radians(CENTER_LAT))
        )
        
        if df_raw.empty:
            logger.warning("Aucune donnée")
            return pd.DataFrame(), {'count': 0, 'timestamp': datetime.now()}
        
        df_transformed = transformer.execute(df_raw, max_distance_km=MAX_DISTANCE)
        
        if not df_transformed.empty:
            loader.load_dataframe(df_transformed, if_exists='append')
        
        stats = {
            'count': len(df_transformed),
            'timestamp': datetime.now(),
            'unique_aircraft': df_transformed['icao24'].nunique() if not df_transformed.empty else 0,
            'avg_altitude': df_transformed['baro_altitude'].mean() if not df_transformed.empty else 0,
            'max_altitude': df_transformed['baro_altitude'].max() if not df_transformed.empty else 0
        }
        
        logger.info(f"✅ {stats['count']} avions | {stats['unique_aircraft']} uniques")
        return df_transformed, stats
    
    except Exception as e:
        logger.error(f"Erreur: {e}")
        return pd.DataFrame(), {'count': 0, 'timestamp': datetime.now(), 'error': str(e)}

def update_history(df_new: pd.DataFrame) -> pd.DataFrame:
    """
    Met à jour l'historique avec les nouvelles données
    Garde seulement les HISTORY_HOURS dernières heures
    """
    global global_history
    
    if df_new.empty:
        return global_history
    
    
    if 'update_time' not in df_new.columns:
        df_new['update_time'] = datetime.now()
    
    global_history = pd.concat([global_history, df_new], ignore_index=True)
    
    # Garder seulement HISTORY_HOURS
    cutoff_time = datetime.now() - timedelta(hours=HISTORY_HOURS)
    global_history = global_history[
        pd.to_datetime(global_history['update_time']) > cutoff_time
    ]
    
    return global_history

app = dash.Dash(__name__)

# Injection du CSS pour l'animation radar
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Mon mini Sonar</title>
        {%favicon%}
        {%css%}
        <style>
            .radar-animation-wrapper {
                position: relative;
                width: 100%;
                max-width: 700px;
                height: 600px;
                background-color: #051005; /* Fond noir/vert */
                border-radius: 8px;
                overflow: hidden;
                margin: 0 auto;
            }
            .radar-circle {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                border: 2px solid rgba(0, 255, 0, 0.3);
                border-radius: 50%;
                animation: ripple 4s linear infinite;
                pointer-events: none;
                z-index: 0;
            }
            .circle-1 { animation-delay: 0s; }
            .circle-2 { animation-delay: -1s; }
            .circle-3 { animation-delay: -2s; }
            .circle-4 { animation-delay: -3s; }

            @keyframes ripple {
                0% { width: 0px; height: 0px; opacity: 1; }
                100% { width: 800px; height: 800px; opacity: 0; }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer></footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </body>
</html>
'''

app.layout = html.Div([
    html.H1("radar avion Temps Réel"),
    html.P(f"Localisation: {LOCATION_NAME} & Rayon: {MAX_DISTANCE} km"),
    html.Div(id='refresh-time', style={'marginBottom': '15px', 'fontWeight': 'bold'}),

    dcc.Interval(
        id='interval-component',
        interval=REFRESH_INTERVAL * 60000,
        n_intervals=0
    ),
    dcc.Store(id='data-store', data={}, storage_type='memory'),

    dcc.Loading(
        id='loading-radar',
        type='default',
        children=html.Div([
            html.Div(className="radar-circle circle-1"),
            html.Div(className="radar-circle circle-2"),
            html.Div(className="radar-circle circle-3"),
            html.Div(className="radar-circle circle-4"),
            dcc.Graph(
                id='radar-graph', 
                style={'position': 'relative', 'zIndex': '1', 'height': '600px'}
            )
        ], className="radar-animation-wrapper")
    ),

    html.Br(),

    dcc.Loading(
        id='loading-3d',
        type='default',
        children=dcc.Graph(id='graph-3d')
    ),

], style={'padding': '20px', 'fontFamily': 'Arial, sans-serif'})


# Callback pour rafraîchir les données
@app.callback(
    Output('data-store', 'data'),
    Output('refresh-time', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_data(n_intervals):
    """Récupère les données toutes les 30 secondes"""
    df_new, stats = fetch_and_transform_data()
    update_history(df_new)
    
    timestamp = datetime.now().strftime('%H:%M:%S')
    refresh_text = f"Dernière mise à jour: {timestamp} "
    
    data = {
        'current': df_new.to_dict('records') if not df_new.empty else [],
        'history': global_history.to_dict('records') if not global_history.empty else [],
        'stats': stats,
        'timestamp': timestamp
    }
    
    return data, refresh_text

@app.callback(
    Output('radar-graph', 'figure'),
    Input('data-store', 'data')
)
def update_radar(data):
    
    RADAR_GREEN = '#00FF00'   # Vert phosphore
    
    TRANSPARENT = 'rgba(0,0,0,0)'
    
    if not data or not data.get('current'):
        return go.Figure().add_annotation(
            text="En attente de données...",
            showarrow=False,
            font=dict(size=20, color=RADAR_GREEN)
        ).update_layout(
            paper_bgcolor=TRANSPARENT,
            plot_bgcolor=TRANSPARENT,
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False)
        )

    df = pd.DataFrame(data['current'])

    if df.empty or 'distance_km' not in df.columns:
        return go.Figure().add_annotation(
            text="Aucune donnée",
            font=dict(color=RADAR_GREEN),
            showarrow=False
        ).update_layout(
            paper_bgcolor=TRANSPARENT,
            plot_bgcolor=TRANSPARENT,
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False)
        )

    fig = go.Figure()

    df['display_text'] = "✈️ " + df['callsign'].fillna('?').str.strip()

    hover_text = [
        f"<b>{row.get('callsign', 'N/A')}</b><br>"
        f"Altitude: {row.get('baro_altitude', 0):.0f}m<br>"
        f"Vitesse: {row.get('velocity', 0):.0f} m/s<br>"
        f"Distance: {row.get('distance_km', 0):.1f}km"
        for _, row in df.iterrows()
    ]

    fig.add_trace(go.Scatterpolar(
        r=df['distance_km'],
        theta=df['azimuth'],
        mode='markers+text',
        name='Avions',
        marker=dict(
            size=12,
            color=RADAR_GREEN,
            symbol='triangle-up', 
            opacity=0.9,
            line=dict(width=1, color=RADAR_GREEN)
        ),
        text=df['display_text'],
        textposition='top center',
        textfont=dict(
            size=11, 
            color=RADAR_GREEN,
            family="Courier New, monospace",
            weight="bold"
        ),
        hovertext=hover_text,
        hoverinfo='text'
    ))

    fig.update_layout(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font=dict(family="Courier New, monospace", color=RADAR_GREEN),
        title={
            'text': f"<b>RADAR</b><br><sub>Cibles détecte+es : {len(df)}</sub>",
            'x': 0.5,
            'xanchor': 'center',
            'font': dict(color=RADAR_GREEN, size=18)
        },
        polar=dict(
            bgcolor=TRANSPARENT,
            radialaxis=dict(
                visible=False,
                showgrid=False,
                showline=False,              
                gridcolor='rgba(0,0,0,0)',    
                linecolor='rgba(0,0,0,0)',    
                range=[0, MAX_DISTANCE],
                ticksuffix='km',
                tickfont=dict(color=RADAR_GREEN)
            ),
            angularaxis=dict(
                rotation=90,             
                direction='clockwise',   
                showgrid=False,
                showline=False,               
                gridcolor='rgba(0,0,0,0)',    
                linecolor='rgba(0,0,0,0)',    
                showticklabels=False,        
                tickfont=dict(color=RADAR_GREEN)
            )
        ),
        hovermode='closest',
        height=600,
        showlegend=False,
        margin=dict(t=80, b=40, l=40, r=40)
    )

    return fig


# Callback pour la vue 3D
@app.callback(
    Output('graph-3d', 'figure'),
    Input('data-store', 'data')
)
def update_3d(data):
    """Met à jour la vue 3D"""
    if not data or not data.get('current'):
        return go.Figure().add_annotation(text="En attente de données...")
    
    df = pd.DataFrame(data['current'])
    
    if df.empty:
        return go.Figure().add_annotation(text="Aucune donnée")
    
    df['x'] = df['distance_km'] * np.cos(np.radians(df['azimuth']))
    df['y'] = df['distance_km'] * np.sin(np.radians(df['azimuth']))
    df['z'] = df['baro_altitude'].fillna(0) / 1000
    
    fig = go.Figure()
    
    colors_map = {
        'Sol': '#FF6B6B',
        'Basse': '#FFA500',
        'Moyenne': '#FFD93D',
        'Haute': '#6BCB77',
        'Très haute': '#4D96FF'
    }
    
    for altitude_cat in ['Sol', 'Basse', 'Moyenne', 'Haute', 'Très haute']:
        mask = df['altitude_category'] == altitude_cat
        df_cat = df[mask]
        
        if len(df_cat) == 0:
            continue
        
        fig.add_trace(go.Scatter3d(
            x=df_cat['x'],
            y=df_cat['y'],
            z=df_cat['z'],
            mode='markers+text',
            name=altitude_cat,
            marker=dict(
                size=5,
                color=colors_map.get(altitude_cat, '#4D96FF'),
                opacity=0.8
            ),
            text=df_cat['callsign'].str.strip() if 'callsign' in df_cat.columns else [],
            hovertext=[
                f"<b>{row.get('callsign', 'N/A')}</b><br>"
                f"Altitude: {row.get('baro_altitude', 0):.0f}m<br>"
                f"Vitesse: {row.get('velocity', 0):.0f} m/s"
                for _, row in df_cat.iterrows()
            ],
            hoverinfo='text'
        ))
    
    fig.add_trace(go.Scatter3d(
        x=[0],
        y=[0],
        z=[0],
        mode='markers',
        name='Observateur',
        marker=dict(size=8, color='red', symbol='diamond'),
        hovertext=['Vous'],
        hoverinfo='text'
    ))
    
    fig.update_layout(
        title="Vue 3D - EN DIRECT",
        scene=dict(
            xaxis_title='Est-Ouest',
            yaxis_title='Nord-Sud',
            zaxis_title='Altitude'
        ),
        height=600,
        hovermode='closest'
    )
    
    return fig


if __name__ == '__main__':
    DEFAULT_HOST = '0.0.0.0'
    DEFAULT_PORT = 8050
    logger.info(f"📍 Localisation: {LOCATION_NAME}")
    logger.info(f"🌐 Accédez à: http://localhost:{DEFAULT_PORT}/")
    
    app.run(debug=True, host=DEFAULT_HOST, port=DEFAULT_PORT)