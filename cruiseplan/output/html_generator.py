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
"""

        # Add leg schedule section
        html_content += self._generate_leg_schedules(config, timeline, stats)

        html_content += """
</body>
</html>
"""

        # Write to file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return output_file

    def _generate_leg_schedules(
        self, config: CruiseConfig, timeline: List[ActivityRecord], stats: dict
    ) -> str:
        """
        Generate HTML section with per-leg schedule tables.

        Parameters
        ----------
        config : CruiseConfig
            Cruise configuration
        timeline : List[ActivityRecord]
            Complete timeline from scheduler
        stats : dict
            Statistics from summary calculation

        Returns
        -------
        str
            HTML content for leg schedules section
        """
        html_content = """
    <h2>3. Leg Schedules</h2>
    <p>Individual leg schedules including transit connections between legs.</p>
"""

        # Group activities by leg
        legs_data = self._group_activities_by_leg(config, timeline)

        # Generate table for each leg
        for i, (leg_name, leg_data) in enumerate(legs_data.items(), 1):
            leg_letter = chr(ord("a") + i - 1)  # a, b, c, ...

            html_content += f"""
    <h3>3{leg_letter}. {leg_name}</h3>
    <table cellpadding="5" cellspacing="0" border="1">
        <tr>
            <th>Activity</th>
            <th>Type</th>
            <th>Position</th>
            <th>Duration (hrs)</th>
            <th>Comments</th>
        </tr>
"""

            total_leg_duration = 0

            # Add transit to leg start (from previous leg end or departure port)
            if leg_data["transit_to_start"]:
                transit = leg_data["transit_to_start"]
                duration_hrs = transit.get("duration_minutes", 0) / 60
                total_leg_duration += duration_hrs

                html_content += f"""
        <tr style="background-color: #f0f8ff;">
            <td>{transit.get('label', 'Transit')}</td>
            <td>Transit to leg start</td>
            <td>{transit.get('start_pos', '')} &rarr; {transit.get('end_pos', '')}</td>
            <td class="number">{duration_hrs:.1f}</td>
            <td>{transit.get('comment', 'Transit between legs')}</td>
        </tr>
"""

            # Add leg activities
            for activity in leg_data["activities"]:
                duration_hrs = activity.get("duration_minutes", 0) / 60
                total_leg_duration += duration_hrs

                # Format position
                if "lat" in activity and "lon" in activity:
                    position = f"{activity['lat']:.4f}, {activity['lon']:.4f}"
                else:
                    position = "N/A"

                # Determine activity type using correct field names
                activity_type = activity.get("activity", "Unknown")
                if activity_type == "Station":
                    operation = activity.get("operation_type", "N/A")
                    activity_type = f"Station ({operation})"
                elif activity_type == "Mooring":
                    action = activity.get("action", "N/A")
                    activity_type = f"Mooring ({action})"
                elif activity_type == "Transit":
                    operation = activity.get("operation_type", "N/A")
                    activity_type = f"Transit ({operation})"

                html_content += f"""
        <tr>
            <td>{activity.get('label', 'Unknown')}</td>
            <td>{activity_type}</td>
            <td>{position}</td>
            <td class="number">{duration_hrs:.1f}</td>
            <td>{activity.get('comment', '')}</td>
        </tr>
"""

            # Add transit from leg end (for last leg only - to arrival port)
            if leg_data["transit_from_end"]:
                transit = leg_data["transit_from_end"]
                duration_hrs = transit.get("duration_minutes", 0) / 60
                total_leg_duration += duration_hrs

                html_content += f"""
        <tr style="background-color: #f0f8ff;">
            <td>{transit.get('label', 'Transit')}</td>
            <td>Transit to arrival port</td>
            <td>{transit.get('start_pos', '')} &rarr; {transit.get('end_pos', '')}</td>
            <td class="number">{duration_hrs:.1f}</td>
            <td>{transit.get('comment', 'Transit to arrival port')}</td>
        </tr>
"""

            # Add leg total row
            html_content += f"""
        <tr style="font-weight: bold; background-color: #f2f2f2;">
            <td>Leg Total</td>
            <td>{len(leg_data['activities'])} operations</td>
            <td></td>
            <td class="number">{total_leg_duration:.1f}</td>
            <td>{total_leg_duration/24:.1f} days</td>
        </tr>
    </table>
"""

        return html_content

    def _group_activities_by_leg(
        self, config: CruiseConfig, timeline: List[ActivityRecord]
    ) -> dict:
        """
        Group timeline activities by leg and add appropriate transit connections.

        Parameters
        ----------
        config : CruiseConfig
            Cruise configuration
        timeline : List[ActivityRecord]
            Complete timeline from scheduler

        Returns
        -------
        dict
            Dictionary mapping leg names to leg data including activities and transits
        """
        legs_data = {}

        # Get leg names from config
        leg_names = (
            [leg.name for leg in config.legs]
            if hasattr(config, "legs") and config.legs
            else []
        )

        if not leg_names:
            # If no legs defined, create a single "Main Cruise" leg
            main_activities = []
            for activity in timeline:
                if isinstance(activity, dict):
                    main_activities.append(activity)
                elif hasattr(activity, "__dict__"):
                    main_activities.append(vars(activity))
                else:
                    main_activities.append(
                        {
                            "label": getattr(activity, "label", "Unknown"),
                            "lat": getattr(activity, "lat", 0.0),
                            "lon": getattr(activity, "lon", 0.0),
                            "duration_minutes": getattr(
                                activity, "duration_minutes", 0
                            ),
                            "activity": getattr(activity, "activity", "Unknown"),
                            "operation_type": getattr(
                                activity, "operation_type", "Unknown"
                            ),
                            "action": getattr(activity, "action", ""),
                            "comment": getattr(activity, "comment", ""),
                        }
                    )

            legs_data["Main Cruise"] = {
                "activities": main_activities,
                "transit_to_start": None,
                "transit_from_end": None,
            }
            return legs_data

        # Initialize legs
        for leg_name in leg_names:
            legs_data[leg_name] = {
                "activities": [],
                "transit_to_start": None,
                "transit_from_end": None,
            }

        # Group activities by leg using leg_name field
        for activity in timeline:
            # ActivityRecord is a dict, so use .get() instead of getattr()
            leg_name = (
                activity.get("leg_name", None)
                if isinstance(activity, dict)
                else getattr(activity, "leg_name", None)
            )

            # Convert activity to dict safely - ActivityRecord is already a dict
            if isinstance(activity, dict):
                activity_dict = activity
            elif hasattr(activity, "__dict__"):
                activity_dict = vars(activity)
            else:
                # Fallback for objects without __dict__
                activity_dict = {
                    "label": getattr(activity, "label", "Unknown"),
                    "lat": getattr(activity, "lat", 0.0),
                    "lon": getattr(activity, "lon", 0.0),
                    "duration_minutes": getattr(activity, "duration_minutes", 0),
                    "activity": getattr(activity, "activity", "Unknown"),
                    "operation_type": getattr(activity, "operation_type", "Unknown"),
                    "action": getattr(activity, "action", ""),
                    "comment": getattr(activity, "comment", ""),
                }

            if leg_name and leg_name in legs_data:
                legs_data[leg_name]["activities"].append(activity_dict)
            # If no leg_name, assign to first leg or create default
            elif leg_names:
                legs_data[leg_names[0]]["activities"].append(activity_dict)
            else:
                legs_data.setdefault(
                    "Main Cruise",
                    {
                        "activities": [],
                        "transit_to_start": None,
                        "transit_from_end": None,
                    },
                )
                legs_data["Main Cruise"]["activities"].append(activity_dict)

        # Add transit connections between legs
        self._add_leg_transits(legs_data, config)

        return legs_data

    def _add_leg_transits(self, legs_data: dict, config: CruiseConfig):
        """
        Add transit connections between legs.

        Parameters
        ----------
        legs_data : dict
            Leg data dictionary to modify
        config : CruiseConfig
            Cruise configuration
        """
        from cruiseplan.calculators.distance import haversine_distance

        def calculate_transit_duration(
            start_pos: str, end_pos: str, vessel_speed_knots: float = 8.0
        ) -> float:
            """Calculate transit duration in minutes based on distance and vessel speed."""
            try:
                # Parse position strings like "12.3456, -67.8901"
                start_lat, start_lon = map(float, start_pos.split(", "))
                end_lat, end_lon = map(float, end_pos.split(", "))

                # Calculate distance in km
                distance_km = haversine_distance(
                    (start_lat, start_lon), (end_lat, end_lon)
                )

                # Convert to nautical miles and calculate duration
                distance_nm = distance_km * 0.539957  # km to nautical miles
                duration_hours = distance_nm / vessel_speed_knots
                return duration_hours * 60  # convert to minutes
            except (ValueError, AttributeError):
                # Fallback to reasonable default if parsing fails
                return 120.0  # 2 hours default

        # Use vessel speed from config if available, otherwise default
        vessel_speed = getattr(config, "default_vessel_speed", 8.0)

        leg_names = list(legs_data.keys())

        for i, leg_name in enumerate(leg_names):
            # Add transit to leg start (except for first leg, which gets departure port transit)
            if i == 0:
                # First leg: transit from departure port to first station
                if hasattr(config, "departure_port") and config.departure_port:
                    departure_pos = f"{config.departure_port.position.latitude:.4f}, {config.departure_port.position.longitude:.4f}"
                    first_activity = (
                        legs_data[leg_name]["activities"][0]
                        if legs_data[leg_name]["activities"]
                        else None
                    )
                    if first_activity and "lat" in first_activity:
                        first_pos = (
                            f"{first_activity['lat']:.4f}, {first_activity['lon']:.4f}"
                        )
                        legs_data[leg_name]["transit_to_start"] = {
                            "label": f"Transit from {config.departure_port.name}",
                            "duration_minutes": calculate_transit_duration(
                                departure_pos, first_pos, vessel_speed
                            ),
                            "start_pos": departure_pos,
                            "end_pos": first_pos,
                            "comment": f"Transit from departure port ({config.departure_port.name})",
                        }
            else:
                # Subsequent legs: transit from previous leg end to this leg start
                prev_leg = leg_names[i - 1]
                prev_activities = legs_data[prev_leg]["activities"]
                current_activities = legs_data[leg_name]["activities"]

                if prev_activities and current_activities:
                    last_prev = prev_activities[-1]
                    first_current = current_activities[0]

                    if (
                        last_prev
                        and first_current
                        and "lat" in last_prev
                        and "lat" in first_current
                    ):
                        start_pos = f"{last_prev['lat']:.4f}, {last_prev['lon']:.4f}"
                        end_pos = (
                            f"{first_current['lat']:.4f}, {first_current['lon']:.4f}"
                        )

                        legs_data[leg_name]["transit_to_start"] = {
                            "label": f"Transit {prev_leg} to {leg_name}",
                            "duration_minutes": calculate_transit_duration(
                                start_pos, end_pos, vessel_speed
                            ),
                            "start_pos": start_pos,
                            "end_pos": end_pos,
                            "comment": "Transit between legs",
                        }

            # Add transit from leg end (only for last leg - to arrival port)
            if i == len(leg_names) - 1:
                if hasattr(config, "arrival_port") and config.arrival_port:
                    arrival_pos = f"{config.arrival_port.position.latitude:.4f}, {config.arrival_port.position.longitude:.4f}"
                    last_activity = (
                        legs_data[leg_name]["activities"][-1]
                        if legs_data[leg_name]["activities"]
                        else None
                    )
                    if last_activity and "lat" in last_activity:
                        last_pos = (
                            f"{last_activity['lat']:.4f}, {last_activity['lon']:.4f}"
                        )
                        legs_data[leg_name]["transit_from_end"] = {
                            "label": f"Transit to {config.arrival_port.name}",
                            "duration_minutes": calculate_transit_duration(
                                last_pos, arrival_pos, vessel_speed
                            ),
                            "start_pos": last_pos,
                            "end_pos": arrival_pos,
                            "comment": f"Transit to arrival port ({config.arrival_port.name})",
                        }


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
