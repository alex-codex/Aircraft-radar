"""
Point d'entrée principal de l'application de contrôle aérien (Tactical Radar).
Initialise l'application Dash, configure le layout et démarre le serveur.
"""

import logging
import dash
from dash import dcc, html
import config.settings as settings
from ui.callbacks import register_callbacks

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de l'application Dash
app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    title="TACTICAL RADAR - AIRSPACE CONTROL"
)

# Configuration du layout structurel
app.layout = html.Div([
    # Grille décorative en arrière-plan
    html.Div(className="grid-background"),
    
    # Horloge invisible pour rafraîchir l'heure locale
    dcc.Interval(id='clock-interval', interval=1000, n_intervals=0),
    
    # Intervalle de rafraîchissement des données (OpenSky API)
    dcc.Interval(
        id='data-interval', 
        interval=settings.REFRESH_INTERVAL_SEC * 1000, 
        n_intervals=0
    ),
    
    # Stockages de données côté client
    dcc.Store(id='data-store', data={}),
    dcc.Store(id='selected-aircraft-store', data=None),
    
    # --- CONTENEUR GRILLE PRINCIPALE ---
    html.Div([
        
        # 1. HEADER (Titre, Références et Statut)
        html.Header([
            html.Div([
                html.H1("TACTICAL RADAR"),
                html.Div(
                    f"GRID REF: {settings.CENTER_LAT:.4f}°N, {settings.CENTER_LON:.4f}°E ({settings.LOCATION_NAME})", 
                    className="header-subtitle"
                )
            ], className="header-title-section"),
            
            html.Div([
                html.Div([
                    html.Div(className="status-dot"),
                    html.Span("SCANNING ACTIVE", id="scanning-status-text")
                ], className="status-indicator"),
                html.Div(id="live-clock", className="header-clock")
            ], className="header-status-section")
        ], className="app-header"),
        
        # 2. PANNEAU GAUCHE : STATISTIQUES, FILTRES & TÉLÉMÉTRIE DETAILED
        html.Div([
            html.Div("COMMAND CENTER", className="panel-title"),
            
            # Grille de statistiques rapides (KPIs)
            html.Div([
                html.Div([
                    html.Span("Cibles Actives", className="stat-label"),
                    html.Div("00", id="kpi-targets", className="stat-value green")
                ], className="stat-card"),
                html.Div([
                    html.Span("Altitude Moy.", className="stat-label"),
                    html.Div("0 m", id="kpi-alt-avg", className="stat-value")
                ], className="stat-card"),
                html.Div([
                    html.Span("Vitesse Max", className="stat-label"),
                    html.Div("0 km/h", id="kpi-speed-max", className="stat-value")
                ], className="stat-card"),
                html.Div([
                    html.Span("Appareils Uniques", className="stat-label"),
                    html.Div("0", id="kpi-unique", className="stat-value")
                ], className="stat-card"),
            ], className="stats-grid"),
            
            # Curseur de portée radar
            html.Div([
                html.Label("Portée Radar (km)", className="control-label"),
                dcc.Slider(
                    id='range-slider',
                    min=5,
                    max=100,
                    step=5,
                    value=settings.DEFAULT_MAX_RANGE_KM,
                    marks={5: '5', 20: '20', 35: '35', 50: '50', 75: '75', 100: '100'}
                )
            ], className="control-group", style={'marginBottom': '25px'}),
            
            # Sélecteur de couche d'altitude
            html.Div([
                html.Label("Filtre d'Altitude", className="control-label"),
                dcc.Dropdown(
                    id='altitude-filter',
                    options=[
                        {'label': 'Toutes altitudes', 'value': 'ALL'},
                        {'label': 'Sol (< 3 000 m)', 'value': 'Sol'},
                        {'label': 'Basse (3 000 - 6 000 m)', 'value': 'Basse'},
                        {'label': 'Moyenne (6 000 - 10 000 m)', 'value': 'Moyenne'},
                        {'label': 'Haute (10 000 - 15 000 m)', 'value': 'Haute'},
                        {'label': 'Très haute (> 15 000 m)', 'value': 'Très haute'}
                    ],
                    value='ALL',
                    clearable=False,
                    className="dash-dropdown"
                )
            ], className="control-group"),
            
            # Recherche par indicatif
            html.Div([
                html.Label("Recherche d'indicatif", className="control-label"),
                dcc.Input(
                    id='callsign-search',
                    type='text',
                    placeholder='Ex: AFR123...',
                    className='dash-input',
                    debounce=True
                )
            ], className="control-group"),
            
            # Télémétrie de la cible sélectionnée
            html.Div([
                html.Div("TARGET TELEMETRY", className="panel-title", style={'marginTop': '15px', 'fontSize': '12px'}),
                html.Div(id='telemetry-panel')
            ], className="telemetry-container")
            
        ], className="glass-panel"),
        
        # 3. PANNEAU CENTRAL : RADAR VISUEL 2D OU VUE 3D
        html.Div([
            html.Div([
                html.Button("TACTICAL RADAR 2D", id="btn-view-2d", className="view-btn active", n_clicks=0),
                html.Button("AIRSPACE DOME 3D", id="btn-view-3d", className="view-btn", n_clicks=0),
                dcc.Store(id="current-view-store", data="2D")
            ], className="view-selector-container"),
            
            # Zone d'affichage du radar (contient les deux vues, masquées/affichées via CSS)
            html.Div([
                # Conteneur 2D
                html.Div([
                    html.Div(className="radar-sweep-effect"),
                    html.Div(className="radar-grid-decors"),
                    html.Div(className="radar-crosshair-h"),
                    html.Div(className="radar-crosshair-v"),
                    dcc.Graph(
                        id='radar-graph',
                        className='radar-plotly-graph',
                        config={'displayModeBar': False, 'scrollZoom': False}
                    )
                ], id="radar-2d-container", style={'position': 'relative', 'width': '100%', 'height': '100%', 'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center'}),
                
                # Conteneur 3D
                html.Div([
                    dcc.Graph(
                        id='graph-3d',
                        className='three-d-plotly-graph',
                        config={'displayModeBar': True}
                    )
                ], id="radar-3d-container", style={'width': '100%', 'height': '100%', 'display': 'none'})
            ], id="radar-viewport-container", className="radar-viewport")
            
        ], className="glass-panel center-panel"),
        
        # 4. PANNEAU DROIT : LISTE DES CIBLES (DIRECTORY)
        html.Div([
            html.Div([
                html.Span("TARGET DIRECTORY", className="panel-title"),
            ], style={'display': 'flex', 'justifyContent': 'between', 'alignItems': 'center'}),
            
            html.Div(id="flight-list", className="flight-list-container")
        ], className="glass-panel")
        
    ], className="app-container")
], id="main-layout")

# Enregistrement des callbacks
register_callbacks(app)

# Démarrage du serveur
if __name__ == '__main__':
    host = '0.0.0.0'
    port = 8050
    logger.info(f"📍 Radar Center: {settings.LOCATION_NAME}")
    logger.info(f"🌐 Lancement du serveur sur : http://localhost:{port}/")
    
    app.run(debug=True, host=host, port=port)
