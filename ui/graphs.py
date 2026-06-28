"""
Module de génération des graphiques Plotly (2D Polar Radar et 3D Airspace Dome).
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from typing import Optional, List


def render_polar_radar(
    df: pd.DataFrame, 
    max_range: float, 
    selected_icao: Optional[str],
    history_df: pd.DataFrame = pd.DataFrame()
) -> go.Figure:
    """
    Génère la figure du radar polaire 2D.
    
    Args:
        df: DataFrame contenant les vols à afficher.
        max_range: Portée maximale du radar (km).
        selected_icao: ICAO24 de l'avion sélectionné (cible active).
        history_df: DataFrame global d'historique pour tracer les trajectoires.
    """
    RADAR_GREEN = '#39ff14'
    RADAR_CYAN = '#00f2fe'
    RADAR_YELLOW = '#ffb000'
    TRANSPARENT = 'rgba(0,0,0,0)'
    
    # 1. Traitement des cas où il n'y a pas de cible
    if df.empty:
        return _render_empty_radar("RECHERCHE DE CIBLES EN COURS...", RADAR_CYAN)
        
    # 2. Construction des vecteurs de données pour Plotly
    r_coords: List[float] = []
    theta_coords: List[float] = []
    text_labels: List[str] = []
    hover_texts: List[str] = []
    marker_colors: List[str] = []
    marker_sizes: List[int] = []
    custom_data_list: List[str] = []
    
    for _, row in df.iterrows():
        r_coords.append(float(row['distance_km']))
        theta_coords.append(float(row['azimuth']))
        custom_data_list.append(str(row['icao24']))
        
        callsign: str = str(row['callsign']).strip()
        icao = row['icao24']
        is_selected = (selected_icao == icao)
        
        # Filtrage des étiquettes pour éviter le chevauchement (clutter)
        # On affiche l'étiquette uniquement si l'avion est sélectionné OU s'il est en vol actif (> 1200m)
        on_ground = bool(row.get('on_ground', False))
        alt_baro = row.get('baro_altitude', 0)
        alt_val = 0 if pd.isna(alt_baro) else float(alt_baro)
        
        if is_selected:
            text_labels.append(f" <b>{callsign}</b>")
        elif not on_ground and alt_val > 1200:
            text_labels.append(f" {callsign}")
        else:
            text_labels.append("")  # Masquer le texte pour éviter le fouillis
            
        # Style selon sélection
        if is_selected:
            marker_colors.append(RADAR_YELLOW)
            marker_sizes.append(15)
        else:
            # Coloration par catégorie d'altitude
            alt = row['baro_altitude']
            if pd.isna(alt) or alt < 3000:
                marker_colors.append(RADAR_GREEN)  # Basse
            elif alt < 10000:
                marker_colors.append(RADAR_CYAN)   # Moyenne
            else:
                marker_colors.append('#bf5af2')    # Haute (Violet)
            marker_sizes.append(9)
            
        hover_texts.append(
            f"<b>VOL: {callsign}</b><br>"
            f"Alt: {row['baro_altitude']:.0f}m ({row['altitude_category']})<br>"
            f"Vit: {row['velocity']*3.6:.0f} km/h<br>"
            f"Dist: {row['distance_km']:.1f} km"
        )
        
    fig = go.Figure()
    
    # 3. Traçage de la traînée de trajectoire pour l'avion sélectionné
    if selected_icao and not history_df.empty and 'icao24' in history_df.columns:
        df_hist = history_df[history_df['icao24'] == selected_icao].sort_values('update_time')
        # On ne garde que les points dans la portée actuelle du radar
        df_hist = df_hist[df_hist['distance_km'] <= max_range]
        if not df_hist.empty:
            fig.add_trace(go.Scatterpolar(
                r=df_hist['distance_km'].tolist(),
                theta=df_hist['azimuth'].tolist(),
                mode='lines',
                line=dict(color=RADAR_YELLOW, width=2, dash='dot'),
                opacity=0.6,
                hoverinfo='skip',
                name='Trajectoire'
            ))
            
    # 4. Traçage des halos de détection (cercles transparents sous les marqueurs)
    fig.add_trace(go.Scatterpolar(
        r=r_coords,
        theta=theta_coords,
        mode='markers',
        customdata=custom_data_list,
        marker=dict(
            size=[s * 2.5 for s in marker_sizes],
            color=marker_colors,
            opacity=0.15,
            symbol='circle'
        ),
        hoverinfo='skip'
    ))
    
    # 5. Traçage des marqueurs principaux (triangles)
    fig.add_trace(go.Scatterpolar(
        r=r_coords,
        theta=theta_coords,
        mode='markers+text',
        customdata=custom_data_list,
        marker=dict(
            size=marker_sizes,
            color=marker_colors,
            symbol='triangle-up',
            opacity=0.9,
            line=dict(width=1.5, color='#030712')
        ),
        text=text_labels,
        textposition='top center',
        textfont=dict(
            size=10,
            color=RADAR_CYAN,
            family="JetBrains Mono",
            weight="bold"
        ),
        hovertext=hover_texts,
        hoverinfo='text'
    ))
    
    fig.update_layout(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font=dict(family="Outfit, sans-serif", color=RADAR_CYAN),
        polar=dict(
            bgcolor=TRANSPARENT,
            radialaxis=dict(
                visible=True,
                showgrid=True,
                showline=False,
                gridcolor='rgba(0, 242, 254, 0.12)',
                linecolor='rgba(0, 242, 254, 0.2)',
                range=[0, max_range],
                ticksuffix=' km',
                tickfont=dict(color='rgba(0, 242, 254, 0.6)', size=9, family='JetBrains Mono')
            ),
            angularaxis=dict(
                rotation=90,
                direction='clockwise',
                showgrid=True,
                showline=True,
                gridcolor='rgba(0, 242, 254, 0.12)',
                linecolor='rgba(0, 242, 254, 0.2)',
                tickfont=dict(color='rgba(0, 242, 254, 0.8)', size=11, family='Outfit')
            )
        ),
        hovermode='closest',
        showlegend=False,
        margin=dict(t=15, b=15, l=15, r=15)
    )
    
    return fig


def render_3d_airspace(df: pd.DataFrame, max_range: float, selected_icao: Optional[str]) -> go.Figure:
    """
    Génère la figure 3D de l'espace aérien.
    
    Args:
        df: DataFrame contenant les vols à afficher.
        max_range: Portée maximale d'affichage (km).
        selected_icao: ICAO24 de l'avion sélectionné.
    """
    RADAR_CYAN = '#00f2fe'
    RADAR_RED = '#ff3333'
    RADAR_YELLOW = '#ffb000'
    TRANSPARENT = 'rgba(0,0,0,0)'
    
    if df.empty:
        return _render_empty_radar("AUCUNE DONNÉE POUR L'ESPACE 3D", RADAR_CYAN)
        
    fig = go.Figure()
    
    # 1. Tracé de l'observateur au centre (0,0,0)
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[0],
        mode='markers',
        name='CENTRE',
        marker=dict(size=8, color=RADAR_RED, symbol='diamond', opacity=0.9),
        hoverinfo='text',
        hovertext="CENTRE RADAR (VOUS)"
    ))
    
    # 2. Conversion cartésienne locale et tracé des avions
    df_3d = df.copy()
    df_3d['x'] = df_3d['distance_km'] * np.sin(np.radians(df_3d['azimuth']))
    df_3d['y'] = df_3d['distance_km'] * np.cos(np.radians(df_3d['azimuth']))
    df_3d['z'] = df_3d['baro_altitude'].fillna(0)
    
    colors_3d: List[str] = []
    sizes_3d: List[int] = []
    for _, row in df_3d.iterrows():
        if selected_icao and row['icao24'] == selected_icao:
            colors_3d.append(RADAR_YELLOW)
            sizes_3d.append(8)
        else:
            colors_3d.append(RADAR_CYAN)
            sizes_3d.append(4)
            
    fig.add_trace(go.Scatter3d(
        x=df_3d['x'].to_list(),
        y=df_3d['y'].to_list(),
        z=df_3d['z'].to_list(),
        mode='markers+text',
        customdata=df_3d['icao24'].to_list(),
        marker=dict(
            size=sizes_3d,
            color=colors_3d,
            opacity=0.8
        ),
        text=df_3d['callsign'].str.strip().to_list(),
        textposition='top center',
        textfont=dict(color=RADAR_CYAN, size=9, family="JetBrains Mono"),
        hovertext=[
            f"<b>{row['callsign']}</b><br>Alt: {row['baro_altitude']:.0f}m<br>Dist: {row['distance_km']:.1f}km"
            for _, row in df_3d.iterrows()
        ],
        hoverinfo='text'
    ))
    
    fig.update_layout(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font=dict(family="JetBrains Mono, monospace", color=RADAR_CYAN),
        scene=dict(
            xaxis=dict(
                title='OUEST - EST (km)',
                backgroundcolor=TRANSPARENT,
                gridcolor='rgba(0, 242, 254, 0.1)',
                showbackground=False,
                color=RADAR_CYAN,
                range=[-max_range, max_range]
            ),
            yaxis=dict(
                title='SUD - NORD (km)',
                backgroundcolor=TRANSPARENT,
                gridcolor='rgba(0, 242, 254, 0.1)',
                showbackground=False,
                color=RADAR_CYAN,
                range=[-max_range, max_range]
            ),
            zaxis=dict(
                title='ALTITUDE (m)',
                backgroundcolor=TRANSPARENT,
                gridcolor='rgba(0, 242, 254, 0.1)',
                showbackground=False,
                color=RADAR_CYAN,
                range=[0, 15000]
            ),
            camera=dict(
                eye=dict(x=1.3, y=1.3, z=0.9)
            )
        ),
        margin=dict(t=0, b=0, l=0, r=0),
        showlegend=False
    )
    
    return fig


def _render_empty_radar(message: str, text_color: str) -> go.Figure:
    """Helper pour afficher un radar vide avec un message."""
    TRANSPARENT = 'rgba(0,0,0,0)'
    return go.Figure().add_annotation(
        text=message,
        showarrow=False,
        font=dict(size=14, color=text_color, family="Outfit")
    ).update_layout(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False)
    )
