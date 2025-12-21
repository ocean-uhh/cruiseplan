"""
LaTeX Table Generation System (Phase 3a).

Generates proposal-ready tables using Jinja2 templates for LaTeX documents.
Creates paginated tables with proper LaTeX formatting for scientific proposals
and reports. Supports multiple table types with automatic page breaks.

Notes
-----
Uses Jinja2 templating with custom delimiters to avoid LaTeX syntax conflicts.
Templates are stored in the templates/ subdirectory. Tables are automatically
paginated to fit within LaTeX float environments.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

from cruiseplan.calculators.scheduler import ActivityRecord
from cruiseplan.core.validation import CruiseConfig
from cruiseplan.utils.activity_utils import is_scientific_transit
from cruiseplan.utils.constants import hours_to_days
from cruiseplan.utils.coordinates import format_position_latex


class LaTeXGenerator:
    """
    Manages the Jinja2 environment and template rendering for LaTeX outputs.

    This class handles LaTeX table generation using Jinja2 templates with
    custom delimiters to avoid conflicts with LaTeX syntax. Supports automatic
    pagination of large tables.

    Attributes
    ----------
    MAX_ROWS_PER_PAGE : int
        Maximum number of rows per page for LaTeX table float environment (45).
    env : jinja2.Environment
        Jinja2 environment configured with LaTeX-safe delimiters.
    """

    # Max rows per page for LaTeX table float environment
    MAX_ROWS_PER_PAGE = 45

    def __init__(self):
        # Locate the template directory relative to this file
        template_dir = Path(__file__).parent / "templates"

        # Initialize Jinja2 Environment with custom block/variable syntax for LaTeX safety
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            block_start_string="\\BLOCK{",
            block_end_string="}",
            variable_start_string="\\VAR{",
            variable_end_string="}",
            comment_start_string="\\#{",
            comment_end_string="}",
            line_statement_prefix="%%",
            line_comment_prefix="%#",
        )

    def _paginate_data(
        self, data_rows: List[Dict], table_type: str
    ) -> List[Dict[str, Any]]:
        """
        Splits data rows into pages and adds metadata (caption, header).

        Parameters
        ----------
        data_rows : list of dict
            Raw data rows to be paginated.
        table_type : str
            Type of table for generating appropriate captions and headers.

        Returns
        -------
        list of dict
            List of page dictionaries, each containing paginated data with
            metadata for LaTeX rendering.
        """
        pages = []
        num_rows = len(data_rows)

        for i in range(0, num_rows, self.MAX_ROWS_PER_PAGE):
            start = i
            end = min(i + self.MAX_ROWS_PER_PAGE, num_rows)
            page_data = data_rows[start:end]

            caption_suffix = ""
            if i > 0:
                caption_suffix = " (Continued)"

            pages.append(
                {
                    "rows": page_data,
                    "is_first_page": i == 0,
                    "caption_suffix": caption_suffix,
                    "table_type": table_type,  # 'stations' or 'work_days'
                }
            )

        return pages

    def generate_stations_table(
        self, config: CruiseConfig, timeline: List[ActivityRecord]
    ) -> str:
        """
        Generates the Working Area, Stations and Profiles table from scheduler timeline.
        """
        template = self.env.get_template("stations_table.tex.j2")

        # Filter out non-science operations (exclude pure transit activities)
        science_operations = [
            activity
            for activity in timeline
            if activity["activity"] in ["Station", "Mooring", "Area"]
            or activity.get("operation_type", "") in ["station", "mooring", "area"]
            or is_scientific_transit(activity)  # <-- Include scientific transits
        ]

        # Format rows for the LaTeX template
        table_rows = []
        for op in science_operations:
            if is_scientific_transit(op):
                # Scientific transits are line operations, show start and end positions.
                # Assuming the ActivityRecord is populated with the start coordinates by the scheduler.
                # If these fields are missing, it defaults to the end position for the start as a fallback.
                start_lat = op.get("start_lat", op["lat"])
                start_lon = op.get("start_lon", op["lon"])

                start_pos_str = format_position_latex(start_lat, start_lon)
                end_pos_str = format_position_latex(op["lat"], op["lon"])
                position_str = f"({start_pos_str}) to ({end_pos_str})"
                depth_str = "N/A"  # Surveys typically don't have a single station depth

                table_rows.append(
                    {
                        "operation": "Survey (start)",
                        "station": str(op["label"]).replace("_", "-"),
                        "position": start_pos_str,
                        "depth_m": depth_str,
                        "start_time": op["start_time"].strftime("%Y-%m-%d %H:%M"),
                        "duration_hours": f"{op['duration_minutes']/60:.1f}",
                    }
                )
                table_rows.append(
                    {
                        "operation": "Survey (end)",
                        "station": str(op["label"]).replace("_", "-"),
                        "position": end_pos_str,
                        "depth_m": depth_str,
                        "start_time": op["start_time"].strftime("%Y-%m-%d %H:%M"),
                        "duration_hours": f"{op['duration_minutes']/60:.1f}",
                    }
                )

            elif op["activity"] == "Area" or op.get("operation_type", "") == "area":
                # Area operations (polygon-based operations like bathymetry surveys)
                position_str = format_position_latex(op["lat"], op["lon"])
                action = op.get(
                    "action", "survey"
                )  # Default to 'survey' if no action specified

                table_rows.append(
                    {
                        "operation": f"Area ({action})",
                        "station": str(op["label"]).replace("_", "-"),
                        "position": f"Center: {position_str}",
                        "depth_m": "Variable",  # Areas typically span multiple depths
                        "start_time": op["start_time"].strftime("%Y-%m-%d %H:%M"),
                        "duration_hours": f"{op['duration_minutes']/60:.1f}",
                    }
                )

            else:
                # Point operations (Station, Mooring)
                position_str = format_position_latex(op["lat"], op["lon"])

                table_rows.append(
                    {
                        "operation": op["activity"],
                        "station": str(op["label"]).replace("_", "-"),
                        "position": position_str,
                        "depth_m": f"{op['depth']:.0f}",
                        "start_time": op["start_time"].strftime("%Y-%m-%d %H:%M"),
                        "duration_hours": f"{op['duration_minutes']/60:.1f}",
                    }
                )

        paginated_data = self._paginate_data(table_rows, "stations")

        cruise_name = str(config.cruise_name).replace("_", "-")
        return template.render(cruise_name=cruise_name, pages=paginated_data)

    def generate_work_days_table(
        self, config: CruiseConfig, timeline: List[ActivityRecord]
    ) -> str:
        """
        Generates the Work Days at Sea table from scheduler timeline.
        If multiple legs exist, generates separate tables per leg.
        """
        # Check if we have multiple legs
        leg_names = (
            [leg.name for leg in config.legs]
            if hasattr(config, "legs") and config.legs
            else []
        )

        if len(leg_names) <= 1:
            # Single leg or no legs defined - generate single table
            return self._generate_single_work_days_table(config, timeline)
        else:
            # Multiple legs - generate unified table with leg information in Area column
            return self._generate_unified_multi_leg_work_days_table(
                config, timeline, leg_names
            )

    def _generate_single_work_days_table(
        self, config: CruiseConfig, timeline: List[ActivityRecord]
    ) -> str:
        """
        Generate a single work days table for the entire cruise.
        """
        template = self.env.get_template("work_days_table.tex.j2")

        # Calculate activity groups for this method
        station_activities = [a for a in timeline if a["activity"] == "Station"]
        mooring_activities = [a for a in timeline if a["activity"] == "Mooring"]
        area_activities = [a for a in timeline if a["activity"] == "Area"]
        all_transits = [a for a in timeline if a["activity"] == "Transit"]
        scientific_transits = [
            a for a in all_transits if a.get("action")
        ]  # Scientific transits have actions

        station_duration_h = sum(a["duration_minutes"] for a in station_activities) / 60
        mooring_duration_h = sum(a["duration_minutes"] for a in mooring_activities) / 60
        area_duration_h = sum(a["duration_minutes"] for a in area_activities) / 60

        # Calculate scientific operation durations by action
        scientific_op_durations_h = {}
        for activity in scientific_transits:
            action = activity.get("action", "Uncategorized")
            duration_h = activity["duration_minutes"] / 60
            scientific_op_durations_h[action] = (
                scientific_op_durations_h.get(action, 0.0) + duration_h
            )

        total_scientific_op_h = sum(scientific_op_durations_h.values())

        ACTION_TO_DISPLAY_NAME = {
            "survey": "Survey Operations",
            "ADCP": "ADCP Survey",
            "bathymetry": "Bathymetric Survey",
        }

        # Calculate transit variables that are used later
        navigation_transits = [
            a for a in all_transits if not a.get("action")
        ]  # Navigation transits don't have actions

        # Calculate major port transits (departure and arrival)
        port_departure_activities = [
            a for a in timeline if a["activity"] == "Port_Departure"
        ]
        port_arrival_activities = [
            a for a in timeline if a["activity"] == "Port_Arrival"
        ]

        # Transit categorization using correct port activities
        transit_to_area_h = 0.0
        transit_from_area_h = 0.0
        transit_within_area_h = 0.0

        # Transit to area = departure port activity duration
        if port_departure_activities:
            transit_to_area_h = port_departure_activities[0]["duration_minutes"] / 60

        # Transit from area = arrival port activity duration
        if port_arrival_activities:
            transit_from_area_h = port_arrival_activities[0]["duration_minutes"] / 60

        # Within area = navigation transits between operations
        if navigation_transits:
            transit_within_area_h = (
                sum(t["duration_minutes"] for t in navigation_transits) / 60
            )
        # Note that navigation transits only include to/from port transits here
        total_navigation_transit_h = transit_to_area_h + transit_from_area_h

        # Generate work days rows for the timeline
        summary_rows = self._generate_work_days_rows_for_timeline(timeline)

        # Calculate totals
        total_operation_duration_h = (
            station_duration_h
            + mooring_duration_h
            + area_duration_h
            + total_scientific_op_h  # Scientific transit duration is operation time
            + transit_within_area_h  # Within-area transit counted as operation time
        )
        total_transit_h = (
            total_navigation_transit_h  # Only pure navigation transit duration
        )
        total_duration_h = total_operation_duration_h + total_transit_h
        total_days = hours_to_days(total_duration_h)

        paginated_data = self._paginate_data(summary_rows, "work_days")

        return template.render(
            cruise_name=str(config.cruise_name).replace("_", "-"),
            pages=paginated_data,
            total_duration_h=f"{total_operation_duration_h:.1f}",
            total_transit_h=f"{total_transit_h:.1f}",
            total_days=f"{total_days:.1f}",
        )

    def _generate_multi_leg_work_days_tables(
        self, config: CruiseConfig, timeline: List[ActivityRecord], leg_names: List[str]
    ) -> str:
        """
        Generate separate work days tables for each leg.
        """
        template = self.env.get_template("work_days_table.tex.j2")

        all_tables = []

        for leg_name in leg_names:
            # Filter timeline activities for this leg
            leg_timeline = [
                activity
                for activity in timeline
                if activity.get("leg_name") == leg_name
            ]

            if not leg_timeline:
                continue

            # Generate work days data for this leg
            summary_rows = self._generate_work_days_rows_for_timeline(leg_timeline)

            # Calculate totals for this leg
            total_operation_duration_h = 0.0
            total_transit_h = 0.0

            for row in summary_rows:
                if row["duration_h"] and row["duration_h"] != "":
                    total_operation_duration_h += float(row["duration_h"])
                if row["transit_h"] and row["transit_h"] != "":
                    total_transit_h += float(row["transit_h"])

            total_duration_h = total_operation_duration_h + total_transit_h
            total_days = hours_to_days(total_duration_h)

            paginated_data = self._paginate_data(summary_rows, "work_days")

            # Generate table for this leg
            leg_table = template.render(
                cruise_name=f"{str(config.cruise_name).replace('_', '-')} - {leg_name.replace('_', '-')}",
                pages=paginated_data,
                total_duration_h=f"{total_operation_duration_h:.1f}",
                total_transit_h=f"{total_transit_h:.1f}",
                total_days=f"{total_days:.1f}",
            )

            all_tables.append(leg_table)

        # Combine all leg tables with page breaks
        return "\n\n\\clearpage\n\n".join(all_tables)

    def _generate_unified_multi_leg_work_days_table(
        self, config: CruiseConfig, timeline: List[ActivityRecord], leg_names: List[str]
    ) -> str:
        """
        Generate a unified work days table with leg information in the Area column.
        """
        template = self.env.get_template("work_days_table.tex.j2")

        all_summary_rows = []
        total_operation_duration_h = 0.0
        total_transit_h = 0.0

        for leg_name in leg_names:
            # Filter timeline activities for this leg
            leg_timeline = [
                activity
                for activity in timeline
                if activity.get("leg_name") == leg_name
            ]

            if not leg_timeline:
                continue

            # Generate work days data for this leg
            leg_summary_rows = self._generate_work_days_rows_for_timeline(leg_timeline)

            # Add leg name to Area column for each row in this leg
            sanitized_leg_name = leg_name.replace("_", "-")
            for i, row in enumerate(leg_summary_rows):
                if i == 0:
                    # First row shows the leg name
                    row["area"] = sanitized_leg_name
                else:
                    # Subsequent rows leave area blank for cleaner table appearance
                    row["area"] = ""
                all_summary_rows.append(row)

            # Calculate totals across all legs
            for row in leg_summary_rows:
                if row["duration_h"] and row["duration_h"] != "":
                    total_operation_duration_h += float(row["duration_h"])
                if row["transit_h"] and row["transit_h"] != "":
                    total_transit_h += float(row["transit_h"])

        total_duration_h = total_operation_duration_h + total_transit_h
        total_days = hours_to_days(total_duration_h)

        paginated_data = self._paginate_data(all_summary_rows, "work_days")

        return template.render(
            cruise_name=str(config.cruise_name).replace("_", "-"),
            pages=paginated_data,
            total_duration_h=f"{total_operation_duration_h:.1f}",
            total_transit_h=f"{total_transit_h:.1f}",
            total_days=f"{total_days:.1f}",
        )

    def _generate_work_days_rows_for_timeline(
        self, timeline: List[ActivityRecord]
    ) -> List[Dict[str, str]]:
        """
        Extract work days summary rows from a timeline (used for both single and multi-leg).
        """
        summary_rows = []

        # Group activities by type and classify transits
        all_transits = [a for a in timeline if a["activity"] == "Transit"]
        station_activities = [a for a in timeline if a["activity"] == "Station"]
        mooring_activities = [a for a in timeline if a["activity"] == "Mooring"]
        area_activities = [a for a in timeline if a["activity"] == "Area"]

        # Separate transits into scientific and navigation (Step 2)
        scientific_transits = [a for a in all_transits if is_scientific_transit(a)]
        navigation_transits = [a for a in all_transits if not is_scientific_transit(a)]

        # Map scientific action names to display names (Step 4)
        ACTION_TO_DISPLAY_NAME = {
            "ADCP": "ADCP Survey",
            "bathymetry": "Bathymetric Survey",
        }

        # Calculate operation durations in hours (CTD/Mooring)
        station_duration_h = sum(a["duration_minutes"] for a in station_activities) / 60
        mooring_duration_h = sum(a["duration_minutes"] for a in mooring_activities) / 60
        area_duration_h = sum(a["duration_minutes"] for a in area_activities) / 60

        # 3. Duration Categorization - Scientific Transits (counted as operation time)
        scientific_op_durations_h: Dict[str, float] = {}
        for a in scientific_transits:
            # action can be None if the YAML schema is poorly formed, use a fallback
            action = a.get("action", "Uncategorized Scientific Transit")
            duration_h = a["duration_minutes"] / 60
            scientific_op_durations_h[action] = (
                scientific_op_durations_h.get(action, 0.0) + duration_h
            )

        total_scientific_op_h = sum(scientific_op_durations_h.values())

        # 3. Duration Categorization - Pure Navigation Transits (counted as transit time)
        transit_to_area_h = 0.0
        transit_from_area_h = 0.0
        transit_within_area_h = 0.0

        # Calculate major port transits (departure and arrival)
        port_departure_activities = [
            a for a in timeline if a["activity"] == "Port_Departure"
        ]
        port_arrival_activities = [
            a for a in timeline if a["activity"] == "Port_Arrival"
        ]

        # Transit to area = departure port activity duration
        if port_departure_activities:
            transit_to_area_h = port_departure_activities[0]["duration_minutes"] / 60

        # Transit from area = arrival port activity duration
        if port_arrival_activities:
            transit_from_area_h = port_arrival_activities[0]["duration_minutes"] / 60

        # Within area = navigation transits between operations
        if navigation_transits:
            transit_within_area_h = (
                sum(t["duration_minutes"] for t in navigation_transits) / 60
            )

        total_navigation_transit_h = transit_to_area_h + transit_from_area_h

        # --- Build Summary Rows ---

        # 1. Navigation Transit (To Area)
        if transit_to_area_h > 0:
            # Find first operational activity (non-port) as working area destination
            first_operation = next(
                (
                    activity
                    for activity in timeline
                    if activity["activity"] not in ["Port_Departure", "Port_Arrival"]
                ),
                None,
            )
            destination = (
                first_operation["label"] if first_operation else "working area"
            )

            summary_rows.append(
                {
                    "area": "",  # Area will be populated by caller for multi-leg
                    "activity": "Transit to area",
                    "duration_h": "",  # No operation duration
                    "transit_h": f"{transit_to_area_h:.1f}",
                    "notes": f"Departure port to {destination}",
                }
            )

        # 2. Station Operations
        if station_activities:
            summary_rows.append(
                {
                    "area": "",  # Area will be populated by caller for multi-leg
                    "activity": "CTD/Station Operations",
                    "duration_h": f"{station_duration_h:.1f}",
                    "transit_h": "",  # No transit time for this row
                    "notes": f"{len(station_activities)} stations",
                }
            )

        # 3. Mooring Operations
        if mooring_activities:
            summary_rows.append(
                {
                    "area": "",  # Area will be populated by caller for multi-leg
                    "activity": "Mooring Operations",
                    "duration_h": f"{mooring_duration_h:.1f}",
                    "transit_h": "",  # No transit time for this row
                    "notes": f"{len(mooring_activities)} operations",
                }
            )

        # 4. Scientific Transit Operations (counted as operation duration)
        if scientific_transits:
            for action, duration_h in scientific_op_durations_h.items():
                display_name = ACTION_TO_DISPLAY_NAME.get(
                    action, f"{action.title()} Survey"
                )
                summary_rows.append(
                    {
                        "area": "",  # Area will be populated by caller for multi-leg
                        "activity": display_name,
                        "duration_h": f"{duration_h:.1f}",
                        "transit_h": "",  # No transit time, this is operation time
                        "notes": "Scientific transit operation",
                    }
                )

        # 5. Area/Survey Operations
        if area_activities:
            summary_rows.append(
                {
                    "area": "",  # Area will be populated by caller for multi-leg
                    "activity": "Area Survey Operations",
                    "duration_h": f"{area_duration_h:.1f}",
                    "transit_h": "",  # No transit time for this row
                    "notes": f"{len(area_activities)} survey areas",
                }
            )

        # 6. Within-area navigation transits (counted as operation time)
        if transit_within_area_h > 0:
            summary_rows.append(
                {
                    "area": "",  # Area will be populated by caller for multi-leg
                    "activity": "Within-area transits",
                    "duration_h": f"{transit_within_area_h:.1f}",
                    "transit_h": "",  # No transit time, this is operation time
                    "notes": "Navigation within working areas",
                }
            )

        # 7. Navigation Transit (From Area)
        if transit_from_area_h > 0:
            # Find last operational activity (non-port) as working area origin
            last_operation = None
            for activity in reversed(timeline):
                if activity["activity"] not in ["Port_Departure", "Port_Arrival"]:
                    last_operation = activity
                    break
            origin = last_operation["label"] if last_operation else "working area"

            summary_rows.append(
                {
                    "area": "",  # Area will be populated by caller for multi-leg
                    "activity": "Transit from area",
                    "duration_h": "",  # No operation duration
                    "transit_h": f"{transit_from_area_h:.1f}",
                    "notes": f"{origin} to arrival port",
                }
            )

        return summary_rows


def generate_latex_tables(
    config: CruiseConfig, timeline: List[ActivityRecord], output_dir: Path
) -> List[Path]:
    """
    Main interface to generate LaTeX tables for cruise proposal from scheduler timeline.

    Parameters
    ----------
    config : CruiseConfig
        The cruise configuration object
    timeline : List[ActivityRecord]
        Timeline generated by the scheduler
    output_dir : Path
        Directory to write output files

    Returns
    -------
        List of generated .tex files
    """
    generator = LaTeXGenerator()
    files_created = []

    # 1. Generate individual tables
    try:
        stations_table = generator.generate_stations_table(config, timeline)
        work_days_table = generator.generate_work_days_table(config, timeline)
    except Exception as e:
        logging.error(f"Failed to generate LaTeX tables: {e}")
        return []

    # 2. Write to files
    output_dir.mkdir(exist_ok=True, parents=True)

    stations_file = output_dir / f"{config.cruise_name}_stations.tex"
    work_days_file = output_dir / f"{config.cruise_name}_work_days.tex"

    stations_file.write_text(stations_table, encoding="utf-8")
    work_days_file.write_text(work_days_table, encoding="utf-8")

    files_created.append(stations_file)
    files_created.append(work_days_file)

    return files_created
