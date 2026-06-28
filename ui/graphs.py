"""
Module de génération des graphiques Plotly (2D Polar Radar et 3D Airspace Dome).
Conforme à la règle de qualité des 50 lignes par fonction.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from typing import Optional, List, Tuple


def render_polar_radar(
    df: pd.DataFrame, 
    max_range: float, 
    selected_icao: Optional[str],
    history_df: pd.DataFrame = pd.DataFrame()
) -> go.Figure:
    """Génère la figure du radar polaire 2D."""
    RADAR_CYAN = '#00f2fe'
    RADAR_YELLOW = '#ffb000'
    
    if df.empty:
        return _render_empty_radar("RECHERCHE DE CIBLES EN COURS...", RADAR_CYAN)
        
    # 1. Extraction et formatage des données
    r_coords, theta_coords, text_labels, hover_texts, marker_colors, marker_sizes, custom_data = \
        _process_radar_data(df, selected_icao)
        
    fig = go.Figure()
    
    # 2. Traçage de la trajectoire historique de la cible active
    _add_radar_history_trail(fig, selected_icao, history_df, max_range, RADAR_YELLOW)
            
    # 3. Traçage des halos de détection (cercles transparents sous les triangles)
    fig.add_trace(go.Scatterpolar(
        r=r_coords, theta=theta_coords, mode='markers', customdata=custom_data,
        marker=dict(size=[s * 2.5 for s in marker_sizes], color=marker_colors, opacity=0.15, symbol='circle'),
        hoverinfo='skip'
    ))
    
    # 4. Traçage des blips principaux (triangles)
    fig.add_trace(go.Scatterpolar(
        r=r_coords, theta=theta_coords, mode='markers+text', customdata=custom_data,
        marker=dict(size=marker_sizes, color=marker_colors, symbol='triangle-up', opacity=0.9, line=dict(width=1.5, color='#030712')),
        text=text_labels, textposition='top center',
        textfont=dict(size=10, color=RADAR_CYAN, family="JetBrains Mono", weight="bold"),
        hovertext=hover_texts, hoverinfo='text'
    ))
    
    # 5. Configuration de la mise en page
    _apply_radar_layout(fig, max_range, RADAR_CYAN)
    return fig


def render_3d_airspace(df: pd.DataFrame, max_range: float, selected_icao: Optional[str]) -> go.Figure:
    """Génère la figure 3D de l'espace aérien."""
    RADAR_CYAN = '#00f2fe'
    RADAR_RED = '#ff3333'
    
    if df.empty:
        return _render_empty_radar("AUCUNE DONNÉE POUR L'ESPACE 3D", RADAR_CYAN)
        
    fig = go.Figure()
    
    # 1. Tracé de l'observateur au centre
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[0], mode='markers', name='CENTRE',
        marker=dict(size=8, color=RADAR_RED, symbol='diamond', opacity=0.9),
        hoverinfo='text', hovertext="CENTRE RADAR (VOUS)"
    ))
    
    # 2. Extraction et tracé des coordonnées cartésiennes des avions
    x_coords, y_coords, z_coords, callsigns, colors, sizes, custom_data = _process_3d_data(df, selected_icao)
    
    fig.add_trace(go.Scatter3d(
        x=x_coords, y=y_coords, z=z_coords, mode='markers+text', customdata=custom_data,
        marker=dict(size=sizes, color=colors, opacity=0.8),
        text=callsigns, textposition='top center',
        textfont=dict(color=RADAR_CYAN, size=9, family="JetBrains Mono"),
        hovertext=[
            f"<b>{callsign}</b><br>Alt: {alt:.0f}m<br>Dist: {dist:.1f}km"
            for callsign, alt, dist in zip(callsigns, z_coords, df['distance_km'])
        ],
        hoverinfo='text'
    ))
    
    # 3. Configuration de la mise en page 3D
    _apply_3d_layout(fig, max_range, RADAR_CYAN)
    return fig


# --- Fonctions d'aide de traitement de données (< 50 lignes) ---

def _process_radar_data(
    df: pd.DataFrame, 
    selected_icao: Optional[str]
) -> Tuple[List[float], List[float], List[str], List[str], List[str], List[int], List[str]]:
    """Extrait et formate les données pour le radar 2D."""
    RADAR_GREEN, RADAR_CYAN, RADAR_YELLOW, RADAR_PURPLE = '#39ff14', '#00f2fe', '#ffb000', '#bf5af2'
    
    r_coords, theta_coords, text_labels, hover_texts, marker_colors, marker_sizes, custom_data = \
        [], [], [], [], [], [], []
        
    for _, row in df.iterrows():
        r_coords.append(float(row['distance_km']))
        theta_coords.append(float(row['azimuth']))
        custom_data.append(str(row['icao24']))
        
        callsign: str = str(row['callsign']).strip()
        icao = row['icao24']
        is_selected = (selected_icao == icao)
        
        # Filtre anti-chevauchement (clutter) des étiquettes
        on_ground = bool(row.get('on_ground', False))
        alt_baro = row.get('baro_altitude', 0)
        alt_val = 0 if pd.isna(alt_baro) else float(alt_baro)
        
        if is_selected:
            text_labels.append(f" <b>{callsign}</b>")
        elif not on_ground and alt_val > 1200:
            text_labels.append(f" {callsign}")
        else:
            text_labels.append("")
            
        # Couleur et taille selon sélection / altitude
        if is_selected:
            marker_colors.append(RADAR_YELLOW)
            marker_sizes.append(15)
        else:
            alt = row['baro_altitude']
            if pd.isna(alt) or alt < 3000:
                marker_colors.append(RADAR_GREEN)
            elif alt < 10000:
                marker_colors.append(RADAR_CYAN)
            else:
                marker_colors.append(RADAR_PURPLE)
            marker_sizes.append(9)
            
        hover_texts.append(
            f"<b>VOL: {callsign}</b><br>Alt: {alt_val:.0f}m ({row['altitude_category']})<br>"
            f"Vit: {row['velocity']*3.6:.0f} km/h<br>Dist: {row['distance_km']:.1f} km"
        )
        
    return r_coords, theta_coords, text_labels, hover_texts, marker_colors, marker_sizes, custom_data


def _process_3d_data(
    df: pd.DataFrame, 
    selected_icao: Optional[str]
) -> Tuple[List[float], List[float], List[float], List[str], List[int], List[int], List[str]]:
    """Calcule les coordonnées cartésiennes et le style 3D."""
    RADAR_CYAN, RADAR_YELLOW = '#00f2fe', '#ffb000'
    
    x_coords = (df['distance_km'] * np.sin(np.radians(df['azimuth']))).to_list()
    y_coords = (df['distance_km'] * np.cos(np.radians(df['azimuth']))).to_list()
    z_coords = df['baro_altitude'].fillna(0).to_list()
    callsigns = df['callsign'].str.strip().to_list()
    custom_data = df['icao24'].to_list()
    
    colors: List[str] = []
    sizes: List[int] = []
    for _, row in df.iterrows():
        if selected_icao and row['icao24'] == selected_icao:
            colors.append(RADAR_YELLOW)
            sizes.append(8)
        else:
            colors.append(RADAR_CYAN)
            sizes.append(4)
            
    return x_coords, y_coords, z_coords, callsigns, colors, sizes, custom_data


# --- Fonctions d'aide de tracé et de mise en page (< 50 lignes) ---

def _add_radar_history_trail(fig: go.Figure, selected_icao: Optional[str], history_df: pd.DataFrame, max_range: float, color: str) -> None:
    """Trace la traînée historique sur le radar 2D si une cible est active."""
    if selected_icao and not history_df.empty and 'icao24' in history_df.columns:
        df_hist = history_df[history_df['icao24'] == selected_icao].sort_values('update_time')
        df_hist = df_hist[df_hist['distance_km'] <= max_range]
        if not df_hist.empty:
            fig.add_trace(go.Scatterpolar(
                r=df_hist['distance_km'].tolist(), theta=df_hist['azimuth'].tolist(),
                mode='lines', line=dict(color=color, width=2, dash='dot'),
                opacity=0.6, hoverinfo='skip', name='Trajectoire'
            ))


def _apply_radar_layout(fig: go.Figure, max_range: float, color: str) -> None:
    """Configure le layout circulaire du radar 2D."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Outfit, sans-serif", color=color),
        polar=dict(
            bgcolor='rgba(0,0,0,0)',
            radialaxis=dict(
                visible=True, showgrid=True, showline=False, gridcolor='rgba(0, 242, 254, 0.12)',
                range=[0, max_range], ticksuffix=' km',
                tickfont=dict(color='rgba(0, 242, 254, 0.6)', size=9, family='JetBrains Mono')
            ),
            angularaxis=dict(
                rotation=90, direction='clockwise', showgrid=True, showline=True, gridcolor='rgba(0, 242, 254, 0.12)',
                linecolor='rgba(0, 242, 254, 0.2)', tickfont=dict(color='rgba(0, 242, 254, 0.8)', size=11, family='Outfit')
            )
        ),
        hovermode='closest', showlegend=False, margin=dict(t=15, b=15, l=15, r=15)
    )


def _apply_3d_layout(fig: go.Figure, max_range: float, color: str) -> None:
    """Configure le layout de la scène 3D."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="JetBrains Mono, monospace", color=color),
        scene=dict(
            xaxis=dict(
                title='OUEST - EST (km)', backgroundcolor='rgba(0,0,0,0)', gridcolor='rgba(0, 242, 254, 0.1)',
                showbackground=False, color=color, range=[-max_range, max_range]
            ),
            yaxis=dict(
                title='SUD - NORD (km)', backgroundcolor='rgba(0,0,0,0)', gridcolor='rgba(0, 242, 254, 0.1)',
                showbackground=False, color=color, range=[-max_range, max_range]
            ),
            zaxis=dict(
                title='ALTITUDE (m)', backgroundcolor='rgba(0,0,0,0)', gridcolor='rgba(0, 242, 254, 0.1)',
                showbackground=False, color=color, range=[0, 15000]
            ),
            camera=dict(eye=dict(x=1.3, y=1.3, z=0.9))
        ),
        margin=dict(t=0, b=0, l=0, r=0), showlegend=False
    )


def _render_empty_radar(message: str, text_color: str) -> go.Figure:
    """Affiche une figure vide avec un message d'attente."""
    return go.Figure().add_annotation(
        text=message, showarrow=False,
        font=dict(size=14, color=text_color, family="Outfit")
    ).update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False)
    )
