"""
HTML Schedule Generation System.

Generates comprehensive HTML reports with summary tables and detailed activity listings
for cruise planning and execution. Provides human-readable visualizations of cruise
schedules including statistics, timelines, and operational details.

Notes
-----
The HTML generator creates self-contained HTML files with embedded CSS styling,
requiring no external dependencies for viewing. Output includes summary statistics
for different activity types (moorings, stations, surveys, areas) and detailed
tables for each operation type.
"""

import logging
from pathlib import Path
from typing import List

from cruiseplan.calculators.scheduler import ActivityRecord
from cruiseplan.core.validation import CruiseConfig
from cruiseplan.utils.activity_utils import is_scientific_operation

logger = logging.getLogger(__name__)


def _convert_decimal_to_deg_min_html(decimal_degrees):
    """
    Convert decimal degrees to DD MM.mmm format for HTML display.

    Parameters
    ----------
    decimal_degrees : float
        Latitude or longitude in decimal degrees.

    Returns
    -------
    str
        Formatted coordinate string in DD MM.mmm format with leading zeros.
    """
    degrees = int(abs(decimal_degrees))
    minutes = abs((abs(decimal_degrees) - degrees) * 60)

    if decimal_degrees >= 0:
        return f"{degrees:02d} {minutes:06.3f}"
    else:
        return f"-{degrees:02d} {minutes:06.3f}"
    degrees = int(abs(decimal_degrees))
    minutes = abs((abs(decimal_degrees) - degrees) * 60)

    if decimal_degrees >= 0:
        return f"{degrees:02d} {minutes:06.3f}"
    else:
        return f"-{degrees:02d} {minutes:06.3f}"


def _calculate_summary_statistics(timeline):
    """
    Calculate summary statistics for HTML output from activity timeline.

    Computes comprehensive statistics for different activity types including
    counts, durations, distances, and averages. Separates activities into
    scientific operations and navigation transits.

    Parameters
    ----------
    timeline : list of dict
        List of activity records from the scheduler.

    Returns
    -------
    dict
        Dictionary containing statistics for each activity type with keys:
        'moorings', 'stations', 'surveys', 'areas', 'within_area', 'port_area',
        and 'mooring_activities' (raw mooring data).
    """
    # Separate activities by type
    station_activities = [a for a in timeline if a["activity"] == "Station"]
    mooring_activities = [a for a in timeline if a["activity"] == "Mooring"]
    area_activities = [a for a in timeline if a["activity"] == "Area"]
    all_transits = [a for a in timeline if a["activity"] == "Transit"]

    # Separate scientific and navigation transits
    scientific_transits = [
        a
        for a in all_transits
        if is_scientific_operation(a) and a["activity"] == "Transit"
    ]
    navigation_transits = [a for a in all_transits if not is_scientific_operation(a)]

    # Calculate mooring statistics
    mooring_stats = {}
    if mooring_activities:
        total_mooring_duration_h = (
            sum(a["duration_minutes"] for a in mooring_activities) / 60
        )
        avg_mooring_duration_h = total_mooring_duration_h / len(mooring_activities)
        mooring_stats = {
            "count": len(mooring_activities),
            "avg_duration_h": avg_mooring_duration_h,
            "total_duration_h": total_mooring_duration_h,
            "total_duration_days": total_mooring_duration_h / 24,
        }
    else:
        mooring_stats = {
            "count": 0,
            "avg_duration_h": 0,
            "total_duration_h": 0,
            "total_duration_days": 0,
        }

    # Calculate station statistics
    station_stats = {}
    if station_activities:
        total_station_duration_h = (
            sum(a["duration_minutes"] for a in station_activities) / 60
        )
        avg_station_duration_h = total_station_duration_h / len(station_activities)
        avg_depth = sum(a.get("depth", 0) for a in station_activities) / len(
            station_activities
        )
        station_stats = {
            "count": len(station_activities),
            "avg_duration_h": avg_station_duration_h,
            "avg_depth_m": avg_depth,
            "total_duration_h": total_station_duration_h,
            "total_duration_days": total_station_duration_h / 24,
        }
    else:
        station_stats = {
            "count": 0,
            "avg_duration_h": 0,
            "avg_depth_m": 0,
            "total_duration_h": 0,
            "total_duration_days": 0,
        }

    # Calculate survey operations (scientific transits)
    survey_stats = {}
    if scientific_transits:
        total_survey_duration_h = (
            sum(a["duration_minutes"] for a in scientific_transits) / 60
        )
        avg_survey_duration_h = total_survey_duration_h / len(scientific_transits)
        total_survey_distance_nm = sum(
            a.get("operation_dist_nm", 0) for a in scientific_transits
        )
        avg_survey_distance_nm = total_survey_distance_nm / len(scientific_transits)
        survey_stats = {
            "count": len(scientific_transits),
            "avg_duration_h": avg_survey_duration_h,
            "avg_distance_nm": avg_survey_distance_nm,
            "total_distance_nm": total_survey_distance_nm,
            "total_duration_h": total_survey_duration_h,
            "total_duration_days": total_survey_duration_h / 24,
        }
    else:
        survey_stats = {
            "count": 0,
            "avg_duration_h": 0,
            "avg_distance_nm": 0,
            "total_distance_nm": 0,
            "total_duration_h": 0,
            "total_duration_days": 0,
        }

    # Calculate area operations
    area_stats = {}
    if area_activities:
        total_area_duration_h = sum(a["duration_minutes"] for a in area_activities) / 60
        avg_area_duration_h = total_area_duration_h / len(area_activities)
        area_stats = {
            "count": len(area_activities),
            "avg_duration_h": avg_area_duration_h,
            "total_duration_h": total_area_duration_h,
            "total_duration_days": total_area_duration_h / 24,
        }
    else:
        area_stats = {
            "count": 0,
            "avg_duration_h": 0,
            "total_duration_h": 0,
            "total_duration_days": 0,
        }

    # Calculate within-area navigation transits (excluding first and last)
    within_area_transits = (
        navigation_transits[1:-1] if len(navigation_transits) > 2 else []
    )
    within_area_stats = {}
    if within_area_transits:
        total_within_duration_h = (
            sum(a["duration_minutes"] for a in within_area_transits) / 60
        )
        total_within_distance_nm = sum(
            a.get("transit_dist_nm", 0) for a in within_area_transits
        )
        avg_speed_kts = (
            total_within_distance_nm / total_within_duration_h
            if total_within_duration_h > 0
            else 0
        )
        within_area_stats = {
            "total_distance_nm": total_within_distance_nm,
            "avg_speed_kts": avg_speed_kts,
            "total_duration_h": total_within_duration_h,
            "total_duration_days": total_within_duration_h / 24,
        }
    else:
        within_area_stats = {
            "total_distance_nm": 0,
            "avg_speed_kts": 0,
            "total_duration_h": 0,
            "total_duration_days": 0,
        }

    # Calculate to/from working area transits (first and last)
    port_transits = []
    if len(navigation_transits) >= 1:
        port_transits.append(navigation_transits[0])  # First transit
    if len(navigation_transits) >= 2:
        port_transits.append(navigation_transits[-1])  # Last transit

    port_area_stats = {}
    if port_transits:
        total_port_duration_h = sum(a["duration_minutes"] for a in port_transits) / 60
        total_port_distance_nm = sum(a.get("transit_dist_nm", 0) for a in port_transits)
        avg_speed_kts = (
            total_port_distance_nm / total_port_duration_h
            if total_port_duration_h > 0
            else 0
        )
        port_area_stats = {
            "total_distance_nm": total_port_distance_nm,
            "avg_speed_kts": avg_speed_kts,
            "total_duration_h": total_port_duration_h,
            "total_duration_days": total_port_duration_h / 24,
        }
    else:
        port_area_stats = {
            "total_distance_nm": 0,
            "avg_speed_kts": 0,
            "total_duration_h": 0,
            "total_duration_days": 0,
        }

    return {
        "moorings": mooring_stats,
        "stations": station_stats,
        "surveys": survey_stats,
        "areas": area_stats,
        "within_area": within_area_stats,
        "port_area": port_area_stats,
        "mooring_activities": mooring_activities,
    }


class HTMLGenerator:
    """
    Manages HTML generation for cruise schedules with summary tables and detailed listings.

    This class provides methods to generate comprehensive HTML reports from cruise
    schedule data, including summary statistics and detailed activity breakdowns.
    """

    def __init__(self):
        """Initialize the HTML generator."""
        pass

    def generate_schedule_report(
        self, config: CruiseConfig, timeline: List[ActivityRecord], output_file: Path
    ) -> Path:
        """
        Generate comprehensive HTML schedule report.

        Parameters
        ----------
        config : CruiseConfig
            The cruise configuration object
        timeline : List[ActivityRecord]
            Timeline generated by the scheduler
        output_file : Path
            Path to output HTML file

        Returns
        -------
        Path
            Path to generated HTML file
        """
        # Calculate summary statistics
        stats = _calculate_summary_statistics(timeline)

        # Calculate total statistics
        total_duration_h = (
            stats["moorings"]["total_duration_h"]
            + stats["stations"]["total_duration_h"]
            + stats["surveys"]["total_duration_h"]
            + stats["areas"]["total_duration_h"]
            + stats["within_area"]["total_duration_h"]
            + stats["port_area"]["total_duration_h"]
        )
        total_duration_days = total_duration_h / 24

        # Create HTML content
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Schedule for {config.cruise_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 5px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .number {{ text-align: right; }}
        h1, h2 {{ color: #333; }}
        .description {{ font-style: italic; color: #666; }}
    </style>
</head>
<body>
    <h1>{config.cruise_name}</h1>
    {f'<p class="description">{config.description}</p>' if config.description else ''}

    <h2>1. Cruise Schedule</h2>
    <table cellpadding="5" cellspacing="0" border="1">
        <tr>
            <th>Activity</th>
            <th>Description</th>
            <th>Hours</th>
            <th>Days</th>
        </tr>
"""

        # Moorings row
        if stats["moorings"]["count"] > 0:
            html_content += f"""
        <tr>
            <td>Moorings</td>
            <td>{stats["moorings"]["count"]} operations, avg {stats["moorings"]["avg_duration_h"]:.1f} hrs each</td>
            <td class="number">{stats["moorings"]["total_duration_h"]:.1f}</td>
            <td class="number">{stats["moorings"]["total_duration_days"]:.1f}</td>
        </tr>
"""

        # CTD Profiles row
        if stats["stations"]["count"] > 0:
            html_content += f"""
        <tr>
            <td>CTD Profiles</td>
            <td>{stats["stations"]["count"]} stations, avg depth {stats["stations"]["avg_depth_m"]:.0f} m, avg {stats["stations"]["avg_duration_h"]:.1f} hrs each</td>
            <td class="number">{stats["stations"]["total_duration_h"]:.1f}</td>
            <td class="number">{stats["stations"]["total_duration_days"]:.1f}</td>
        </tr>
"""

        # Survey operations row
        if stats["surveys"]["count"] > 0:
            html_content += f"""
        <tr>
            <td>Survey operations</td>
            <td>{stats["surveys"]["count"]} operations, avg distance {stats["surveys"]["avg_distance_nm"]:.1f} nm, avg {stats["surveys"]["avg_duration_h"]:.1f} hrs each</td>
            <td class="number">{stats["surveys"]["total_duration_h"]:.1f}</td>
            <td class="number">{stats["surveys"]["total_duration_days"]:.1f}</td>
        </tr>
"""

        # Area operations row
        if stats["areas"]["count"] > 0:
            html_content += f"""
        <tr>
            <td>Area operations</td>
            <td>{stats["areas"]["count"]} operations, avg {stats["areas"]["avg_duration_h"]:.1f} hrs each</td>
            <td class="number">{stats["areas"]["total_duration_h"]:.1f}</td>
            <td class="number">{stats["areas"]["total_duration_days"]:.1f}</td>
        </tr>
"""

        # Transit within area row
        if stats["within_area"]["total_distance_nm"] > 0:
            html_content += f"""
        <tr>
            <td>Transit within area</td>
            <td>{stats["within_area"]["total_distance_nm"]:.1f} nm, avg {stats["within_area"]["avg_speed_kts"]:.1f} kts</td>
            <td class="number">{stats["within_area"]["total_duration_h"]:.1f}</td>
            <td class="number">{stats["within_area"]["total_duration_days"]:.1f}</td>
        </tr>
"""

        # Transit to/from working area row
        if stats["port_area"]["total_distance_nm"] > 0:
            html_content += f"""
        <tr>
            <td>Transit to/from working area</td>
            <td>{stats["port_area"]["total_distance_nm"]:.1f} nm, avg {stats["port_area"]["avg_speed_kts"]:.1f} kts</td>
            <td class="number">{stats["port_area"]["total_duration_h"]:.1f}</td>
            <td class="number">{stats["port_area"]["total_duration_days"]:.1f}</td>
        </tr>
"""

        # Total row
        html_content += f"""
        <tr style="font-weight: bold;">
            <td>Total Cruise</td>
            <td>{stats["moorings"]["count"] + stats["stations"]["count"] + stats["surveys"]["count"] + stats["areas"]["count"]} operations</td>
            <td class="number">{total_duration_h:.1f}</td>
            <td class="number">{total_duration_days:.1f}</td>
        </tr>
    </table>
"""

        # Moorings detail table
        html_content += """
    <h2>2. Moorings</h2>
    <table cellpadding="5" cellspacing="0" border="1">
        <tr>
            <th>Name</th>
            <th>Comment</th>
            <th>Position (Decimal)</th>
            <th>Position (DD MM.mmm)</th>
            <th>Depth (m)</th>
            <th>Duration (hrs)</th>
            <th>Action</th>
        </tr>
"""

        if stats["mooring_activities"]:
            for mooring in stats["mooring_activities"]:
                lat_dmm = _convert_decimal_to_deg_min_html(mooring["lat"])
                lon_dmm = _convert_decimal_to_deg_min_html(mooring["lon"])
                comment = mooring.get("comment", "")
                depth = mooring.get("depth", 0)
                action = mooring.get("action", "N/A")

                html_content += f"""
        <tr>
            <td>{mooring['label']}</td>
            <td>{comment}</td>
            <td>{mooring['lat']:.6f}, {mooring['lon']:.6f}</td>
            <td>{lat_dmm}, {lon_dmm}</td>
            <td class="number">{depth:.0f}</td>
            <td class="number">{mooring['duration_minutes']/60:.1f}</td>
            <td>{action}</td>
        </tr>
"""
        else:
            html_content += """
        <tr>
            <td colspan="7">No moorings defined</td>
        </tr>
"""

        html_content += """
    </table>
</body>
</html>
"""

        # Write to file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"HTML schedule saved to: {output_file}")
        return output_file


def generate_html_schedule(
    config: CruiseConfig, timeline: List[ActivityRecord], output_file: Path
) -> Path:
    """
    Main interface to generate HTML schedule from scheduler timeline.

    Parameters
    ----------
    config : CruiseConfig
        The cruise configuration object
    timeline : List[ActivityRecord]
        Timeline generated by the scheduler
    output_file : Path
        Path to output HTML file

    Returns
    -------
    Path
        Path to generated HTML file
    """
    generator = HTMLGenerator()
    return generator.generate_schedule_report(config, timeline, output_file)
