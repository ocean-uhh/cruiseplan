"""
Output formatting for station plan forecasts.

This module provides functions to format forecast activities into 
letsgo.m compatible text format and LaTeX table format for 
MATLAB cruise planning tools and cruise operations documentation.
"""

import logging
import math
from typing import List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def map_work_codes(category: str, activity_type: str, action: str) -> int:
    """
    Map cruise activity types to standardized work codes.
    
    Parameters
    ----------
    category : str
        Activity category ('point_operation', 'transit', 'other')
    activity_type : str
        Specific operation type (CTD, mooring, etc.)
    action : str
        Specific action (deployment, recovery, profile, etc.)
        
    Returns
    -------
    int
        Work code:
        - 1: Transit (category: 'transit')
        - 2: CTD (type: 'CTD')
        - 3: Mooring (type: 'mooring')
        - 4: PIES (type: 'PIES')
        - 5: Float/Drifter (type: 'float' or 'drifter')
        - 6: Survey (category: 'other' with survey operations)
        
    Examples
    --------
    >>> map_work_codes('transit', '', '')
    1
    >>> map_work_codes('point_operation', 'CTD', 'profile')
    2
    >>> map_work_codes('point_operation', 'mooring', 'deployment')
    3
    """
    # Clean up string inputs
    category = category.lower().strip()
    activity_type = activity_type.lower().strip()
    action = action.lower().strip()
    
    # Transit activities
    if category == 'transit':
        return 1
    
    # Point operations by type
    if category == 'point_operation':
        if 'ctd' in activity_type:
            return 2
        elif 'mooring' in activity_type:
            return 3
        elif 'pies' in activity_type:
            return 4
        elif 'float' in activity_type or 'drifter' in activity_type:
            return 5
    
    # Survey operations (other category)
    if category == 'other':
        if any(word in activity_type.lower() for word in ['survey', 'multibeam', 'bathymetry']):
            return 6
        # Ports and other non-survey activities default to survey code
        return 6
    
    # Default fallback - log unknown combinations
    logger.warning(f"Unknown activity combination: category='{category}', type='{activity_type}', action='{action}' - defaulting to code 6")
    return 6


def format_coordinates(latitude: float, longitude: float) -> Tuple[str, str]:
    """
    Convert decimal degrees to degrees/minutes format.
    
    Parameters
    ----------
    latitude : float
        Latitude in decimal degrees
    longitude : float
        Longitude in decimal degrees
        
    Returns
    -------
    Tuple[str, str]
        Formatted coordinates as (lat_str, lon_str)
        Format: "DD MM.mmm N/S" and "DDD MM.mmm E/W"
        
    Examples
    --------
    >>> format_coordinates(65.583733, -29.464)
    ('65 35.024 N', '029 27.840 W')
    >>> format_coordinates(-45.25, 170.75)
    ('45 15.000 S', '170 45.000 E')
    """
    # Latitude formatting
    lat_abs = abs(latitude)
    lat_deg = int(lat_abs)
    lat_min = (lat_abs - lat_deg) * 60
    lat_hem = 'N' if latitude >= 0 else 'S'
    lat_str = f"{lat_deg:02d} {lat_min:06.3f} {lat_hem}"
    
    # Longitude formatting  
    lon_abs = abs(longitude)
    lon_deg = int(lon_abs)
    lon_min = (lon_abs - lon_deg) * 60
    lon_hem = 'E' if longitude >= 0 else 'W'
    lon_str = f"{lon_deg:03d} {lon_min:06.3f} {lon_hem}"
    
    return lat_str, lon_str


def format_letsgo_output(
    forecast_activities: List[Tuple[int, datetime, str, str, str, float, float, float, str]],
    start_time: str,
    transit_speed: float = 10.0
) -> str:
    """
    Format forecast activities as letsgo.m compatible text.
    
    Parameters
    ----------
    forecast_activities : List[Tuple[int, datetime, str, str, str, float, float, float, str]]
        Forecast activities from generate_forecast()
    start_time : str
        Start time for header metadata
    transit_speed : float, optional
        Ship transit speed in knots (default: 10.0)
        
    Returns
    -------
    str
        Formatted letsgo.m compatible text with header and activity lines
        
    Format
    ------
    Lines: work_code, latitude, longitude, name, duration
    Header includes metadata and work code legend
        
    Examples
    --------
    >>> activities = [(18, datetime(2026,8,30,14,0), 'transit', '', '', 20.8, 65.69, -18.55, 'Transit to Reykjavik')]
    >>> print(format_letsgo_output(activities, "2026-08-30T14:00:00"))
    """
    if not forecast_activities:
        return "% No activities in forecast window"
    
    # Parse start time for header
    try:
        start_dt = datetime.fromisoformat(start_time.replace('T', ' '))
        start_date_str = start_dt.strftime("%Y/%m/%d %H:%M")
    except:
        start_date_str = start_time
    
    # Header
    lines = [
        "% Station Plan Forecast",
        f"% Start_Date = {start_date_str}",
        f"% Ship_Speed = {transit_speed:.0f}",
        f"% Transit_Speed = {transit_speed:.0f}",
        "%",
        "% (1: Transit, 2: CTD, 3: Mooring, 4: PIES, 5: Float/Drifter, 6: Survey)",
        "%",
        ""
    ]
    
    # Activity lines
    for orig_idx, abs_time, category, activity_type, action, duration, lat, lon, name in forecast_activities:
        work_code = map_work_codes(category, activity_type, action)
        lat_str, lon_str = format_coordinates(lat, lon)
        
        # Format: work_code, latitude, longitude, name, duration
        line = f"{work_code}, {lat_str}, {lon_str}, {name}, {duration:.1f}"
        lines.append(line)
    
    return "\n".join(lines)