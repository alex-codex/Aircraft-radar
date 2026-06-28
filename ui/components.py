"""
Composants HTML réutilisables pour le tableau de bord Dash.
"""

import numpy as np
import pandas as pd
from dash import html
from typing import List, Optional, Union, Tuple


def render_telemetry_panel(selected_row: Optional[pd.Series]) -> html.Div:
    """
    Génère le panneau HTML de télémétrie de la cible active.
    
    Args:
        selected_row: Ligne de données de la cible active, ou None si aucune sélection.
    """
    if selected_row is None or selected_row.empty:
        return html.Div(
            "ENGAGER LE SUIVI D'UNE CIBLE POUR OBTENIR SA TÉLÉMÉTRIE COMPLÈTE.",
            style={'color': '#475569', 'fontSize': '11px', 'textAlign': 'center', 'paddingTop': '40px', 'lineHeight': '1.5'}
        )
        
    # Calculs de vitesse
    velocity = float(selected_row.get('velocity', 0))
    speed_kmh = velocity * 3.6
    speed_kts = velocity * 1.94384
    
    # Indicateur vertical
    vertical_rate = selected_row.get('vertical_rate')
    v_text, v_color = _calculate_vertical_rate_indicator(vertical_rate)
    
    # Cap cardinal
    true_track = selected_row.get('true_track')
    cardinal = _get_cardinal_direction(true_track)
    
    is_ground = bool(selected_row.get('on_ground', False))
    status_text = "AU SOL" if is_ground else "EN VOL"
    status_color = '#ff3333' if is_ground else '#39ff14'
    
    return html.Div([
        _render_telemetry_row("INDICATIF :", f"✈️ {selected_row.get('callsign', 'UNKNOWN')}", value_class="highlight", value_style={'fontSize': '14px'}),
        _render_telemetry_row("ADRESSE ICAO :", str(selected_row.get('icao24', 'N/A')).upper()),
        _render_telemetry_row("PAYS D'ORIGINE :", str(selected_row.get('origin_country', 'INCONNU'))),
        _render_telemetry_row("DISTANCE CENTRE :", f"{selected_row.get('distance_km', 0):.2f} km", value_class="highlight"),
        _render_telemetry_row("AZIMUT / CAP :", f"{selected_row.get('azimuth', 0):.1f}° / {cardinal}"),
        _render_telemetry_row("ALTITUDE BARO :", f"{selected_row.get('baro_altitude', 0):,.0f} m"),
        _render_telemetry_row("VITESSE :", f"{speed_kmh:.0f} km/h ({speed_kts:.0f} kts)"),
        _render_telemetry_row("TAUX VERTICAL :", v_text, value_class=v_color),
        _render_telemetry_row("STATUT :", status_text, value_style={'color': status_color}),
    ])


def render_flight_list(df: pd.DataFrame, selected_icao: Optional[str]) -> Union[List[html.Div], html.Div]:
    """
    Génère la liste défilante des cartes de vols.
    
    Args:
        df: DataFrame filtré des cibles actives.
        selected_icao: ICAO24 de la cible sélectionnée.
    """
    if df.empty:
        return html.Div(
            "AUCUNE CIBLE DANS LE CHAMP D'ACQUISITION.",
            style={'color': '#475569', 'fontFamily': 'Share Tech Mono', 'fontSize': '12px', 'textAlign': 'center', 'paddingTop': '50px', 'lineHeight': '1.8'}
        )
        
    list_children: List[html.Div] = []
    
    for _, row in df.iterrows():
        icao = str(row['icao24'])
        callsign = str(row['callsign']).strip()
        
        # Style de sélection
        is_selected = (selected_icao == icao)
        card_class = "flight-card selected" if is_selected else "flight-card"
        
        # Flèche verticale
        v_rate = row.get('vertical_rate', 0)
        v_arrow, v_class = _calculate_vertical_rate_arrow(v_rate)
                
        # Composant de carte interactive
        card = html.Div([
            html.Div([
                html.Span(callsign, className="flight-callsign"),
                html.Span(str(row.get('origin_country', 'Unknown')), className="flight-country")
            ], className="flight-card-header"),
            
            html.Div([
                _render_card_metric("ALT: ", [
                    f"{row.get('baro_altitude', 0):,.0f} m",
                    html.Span(f" {v_arrow}", className=f"vertical-rate-indicator {v_class}")
                ]),
                _render_card_metric("DIST: ", f"{row.get('distance_km', 0):.1f} km"),
                _render_card_metric("VIT: ", f"{row.get('velocity', 0)*3.6:.0f} km/h"),
                _render_card_metric("CAP: ", f"{row.get('true_track', 0):.0f}°")
            ], className="flight-card-body")
        ], id={'type': 'flight-card', 'index': icao}, className=card_class, n_clicks=0)
        
        list_children.append(card)
        
    return list_children


# --- Helpers internes (Private) ---

def _render_telemetry_row(label: str, value: Union[str, list], value_class: str = "", value_style: Optional[dict] = None) -> html.Div:
    """Helper pour générer une ligne de télémétrie."""
    return html.Div([
        html.Span(label, className="telemetry-label"),
        html.Span(value, className=f"telemetry-value {value_class}", style=value_style)
    ], className="telemetry-row")


def _render_card_metric(label: str, value: Union[str, list]) -> html.Div:
    """Helper pour générer un indicateur de métrique de carte."""
    return html.Div([
        html.Span(label, className="metric-label"),
        html.Span(value, className="metric-val")
    ], className="flight-metric")


def _calculate_vertical_rate_indicator(v_rate: Optional[float]) -> Tuple[str, str]:
    """Calcule le libellé et la classe CSS pour le taux vertical."""
    if v_rate is None or np.isnan(v_rate):
        return "N/A", "level"
    
    if v_rate > 0.5:
        return f"+{v_rate:.1f} m/s (↗)", "climb"
    elif v_rate < -0.5:
        return f"{v_rate:.1f} m/s (↘)", "descend"
    else:
        return f"{v_rate:.1f} m/s (→)", "level"


def _calculate_vertical_rate_arrow(v_rate: Optional[float]) -> Tuple[str, str]:
    """Calcule la flèche de tendance et la classe CSS pour le taux vertical de carte."""
    if v_rate is None or np.isnan(v_rate):
        return "→", "level"
        
    if v_rate > 0.5:
        return "↗", "climb"
    elif v_rate < -0.5:
        return "↘", "descend"
    else:
        return "→", "level"


def _get_cardinal_direction(degree: Optional[float]) -> str:
    """Convertit un cap en degrés en direction cardinale."""
    if degree is None or np.isnan(degree):
        return "N/A"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((degree + 22.5) % 360 / 45)
    return f"{degree:.0f}° ({directions[idx]})"
