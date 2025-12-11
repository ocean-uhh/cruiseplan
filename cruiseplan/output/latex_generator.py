"""
LaTeX Table Generation System (Phase 3a).
Generates proposal-ready tables using Jinja2 templates.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

from cruiseplan.calculators.scheduler import ActivityRecord
from cruiseplan.core.validation import CruiseConfig
from cruiseplan.utils.activity_utils import is_scientific_transit
from cruiseplan.utils.coordinates import format_position_latex


class LaTeXGenerator:
    """
    Manages the Jinja2 environment and template rendering for LaTeX outputs.
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
            if activity["activity"] in ["Station", "Mooring"]
            or activity["operation_type"] in ["station", "mooring"]
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
        """
        template = self.env.get_template("work_days_table.tex.j2")

        # Create summary breakdown from timeline activities
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

        if navigation_transits:
            # First navigation transit is to working area, last is from working area
            if len(navigation_transits) >= 1:
                transit_to_area_h = navigation_transits[0]["duration_minutes"] / 60
            if len(navigation_transits) >= 2:
                transit_from_area_h = navigation_transits[-1]["duration_minutes"] / 60
            # Any middle navigation transits are within area
            if len(navigation_transits) > 2:
                middle_nav_transits = navigation_transits[1:-1]
                transit_within_area_h = (
                    sum(a["duration_minutes"] for a in middle_nav_transits) / 60
                )

        total_navigation_transit_h = transit_to_area_h + transit_from_area_h

        # --- Build Summary Rows ---

        # 1. Navigation Transit (To Area)
        if transit_to_area_h > 0:
            summary_rows.append(
                {
                    "activity": "Transit to area",
                    "duration_h": "",  # No operation duration
                    "transit_h": f"{transit_to_area_h:.1f}",
                    "notes": f"{config.departure_port.name} to {config.first_station}",
                }
            )

        # 2. Station Operations
        if station_activities:
            summary_rows.append(
                {
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
                    "activity": "Mooring Operations",
                    "duration_h": f"{mooring_duration_h:.1f}",
                    "transit_h": "",  # No transit time for this row
                    "notes": f"{len(mooring_activities)} operations",
                }
            )

        # 4. Scientific Transits (Grouped by action)
        # Sort keys for predictable output
        sorted_actions = sorted(scientific_op_durations_h.keys())
        for action in sorted_actions:
            duration_h = scientific_op_durations_h[action]
            display_name = ACTION_TO_DISPLAY_NAME.get(action, f"{action} Operations")

            # Count the number of segments for the notes field
            num_activities = len(
                [a for a in scientific_transits if a.get("action") == action]
            )

            summary_rows.append(
                {
                    "activity": display_name,
                    "duration_h": f"{duration_h:.1f}",
                    "transit_h": "",  # Scientific transit duration counts as operation time
                    "notes": f"{num_activities} segments",
                }
            )

        # 5. Scientific survey (Area)
        if area_activities:
            summary_rows.append(
                {
                    "activity": "Area Survey Operations",
                    "duration_h": f"{area_duration_h:.1f}",
                    "transit_h": "",  # No transit time for this row
                    "notes": f"{len(area_activities)} areas",
                }
            )

        # 6. Navigation Transit (Within Area)
        if transit_within_area_h > 0:
            summary_rows.append(
                {
                    "activity": "Transit within area",
                    "duration_h": f"{transit_within_area_h:.1f}",
                    "transit_h": "",  # No operation duration
                    "notes": "Between operations",
                }
            )

        # 7. Navigation Transit (From Area)
        if transit_from_area_h > 0:
            summary_rows.append(
                {
                    "activity": "Transit from area",
                    "duration_h": "",  # No operation duration
                    "transit_h": f"{transit_from_area_h:.1f}",
                    "notes": f"{config.last_station} to {config.arrival_port.name}",
                }
            )

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
        total_days = total_duration_h / 24

        paginated_data = self._paginate_data(summary_rows, "work_days")

        return template.render(
            cruise_name=str(config.cruise_name).replace("_", "-"),
            pages=paginated_data,
            total_duration_h=f"{total_operation_duration_h:.1f}",
            total_transit_h=f"{total_transit_h:.1f}",
            total_days=f"{total_days:.1f}",
        )


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
