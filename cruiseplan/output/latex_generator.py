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
from typing import Any

from jinja2 import Environment, FileSystemLoader

from cruiseplan.calculators.scheduler import ActivityRecord
from cruiseplan.output.output_utils import is_scientific_operation
from cruiseplan.schema import CruiseConfig
from cruiseplan.utils.coordinates import format_position_latex
from cruiseplan.utils.units import hours_to_days


def _format_depth_for_latex(activity: dict) -> str:
    """Format depth value for LaTeX output.

    The scheduler has already applied Operation.get_depth() logic and stored
    the result in the ActivityRecord depth fields.

    Parameters
    ----------
    activity : dict
        Activity dictionary from timeline.

    Returns
    -------
    str
        Formatted depth string, or "N/A" if no depth available.
    """
    # Use operation_depth (target depth) if available, otherwise water_depth (seafloor depth)
    depth = activity.get("operation_depth") or activity.get("water_depth")
    return f"{abs(depth):.0f}" if depth is not None else "N/A"


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
        self, data_rows: list[dict], table_type: str
    ) -> list[dict[str, Any]]:
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

    def _generate_stations_rows(
        self, config: CruiseConfig, timeline: list[ActivityRecord]
    ) -> list[dict[str, str]]:
        """
        Extract station/operation data from timeline for table generation.

        Returns
        -------
        List[Dict[str, str]]
            List of dictionaries with station data for LaTeX table.
        """
        # Filter out non-science operations (exclude pure transit activities and ports)
        science_operations = [
            activity
            for activity in timeline
            if is_scientific_operation(activity)
            and not activity.get("activity", "").startswith("Port")
            and activity.get("op_type") != "port"
        ]

        # Format rows for the LaTeX template
        table_rows = []
        for op in science_operations:
            operation_class = op.get("operation_class", "")

            if operation_class == "LineOperation":
                # Line operations (surveys), show start and end positions.
                start_lat = op.get("start_lat", op["lat"])
                start_lon = op.get("start_lon", op["lon"])

                start_pos_str = format_position_latex(start_lat, start_lon)
                end_pos_str = format_position_latex(op["lat"], op["lon"])
                action = op.get("action") or op.get("op_type", "Survey")
                depth_str = "N/A"  # Surveys typically don't have a single station depth

                table_rows.append(
                    {
                        "operation": f"Line ({action})",
                        "station": str(op["label"]).replace("_", "-"),
                        "position": f"({start_pos_str}) to ({end_pos_str})",
                        "depth_m": depth_str,
                        "start_time": op["start_time"].strftime("%Y-%m-%d %H:%M"),
                        "duration_hours": f"{op['duration_minutes']/60:.1f}",
                    }
                )

            elif operation_class == "AreaOperation":
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

            elif operation_class == "PointOperation":
                # Point operations (Station, Mooring)
                position_str = format_position_latex(op["lat"], op["lon"])
                activity_type = op.get("activity", op.get("op_type", "Operation"))

                table_rows.append(
                    {
                        "operation": activity_type,
                        "station": str(op["label"]).replace("_", "-"),
                        "position": position_str,
                        "depth_m": _format_depth_for_latex(op),
                        "start_time": op["start_time"].strftime("%Y-%m-%d %H:%M"),
                        "duration_hours": f"{op['duration_minutes']/60:.1f}",
                    }
                )

        return table_rows

    def generate_stations_table(
        self, config: CruiseConfig, timeline: list[ActivityRecord]
    ) -> str:
        """
        Generates the Working Area, Stations and Profiles table from scheduler timeline.
        """
        template = self.env.get_template("stations_table.tex.j2")

        table_rows = self._generate_stations_rows(config, timeline)
        paginated_data = self._paginate_data(table_rows, "stations")

        cruise_name = str(config.cruise_name).replace("_", "-")
        return template.render(cruise_name=cruise_name, pages=paginated_data)

    def generate_work_days_table(
        self, config: CruiseConfig, timeline: list[ActivityRecord]
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
        self, config: CruiseConfig, timeline: list[ActivityRecord]
    ) -> str:
        """
        Generate a single work days table for the entire cruise.
        """
        template = self.env.get_template("work_days_table.tex.j2")

        # Use scheduler statistics instead of manual calculations
        from cruiseplan.calculators.scheduler import calculate_timeline_statistics

        stats = calculate_timeline_statistics(timeline)

        # Extract statistics from the scheduler calculation
        station_duration_h = stats["stations"]["total_duration_h"]
        mooring_duration_h = stats["moorings"]["total_duration_h"]
        area_duration_h = stats["areas"]["total_duration_h"]
        total_scientific_op_h = stats["surveys"]["total_duration_h"]

        # Transit durations from scheduler statistics
        transit_within_area_h = stats["within_area_transits"]["total_duration_h"]
        transit_to_area_h = stats["port_transits_to_area"]["total_duration_h"]
        transit_from_area_h = stats["port_transits_from_area"]["total_duration_h"]
        total_port_transit_h = transit_to_area_h + transit_from_area_h

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
            total_port_transit_h  # Only port-to-area and area-to-port transit duration
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
        self, config: CruiseConfig, timeline: list[ActivityRecord], leg_names: list[str]
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
        self, config: CruiseConfig, timeline: list[ActivityRecord], leg_names: list[str]
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
        self, timeline: list[ActivityRecord]
    ) -> list[dict[str, str]]:
        """
        Extract work days summary rows from a timeline (used for both single and multi-leg).
        """
        summary_rows = []

        # Use scheduler statistics instead of manual calculations
        from cruiseplan.calculators.scheduler import calculate_timeline_statistics

        stats = calculate_timeline_statistics(timeline)

        # Transit durations from scheduler statistics
        transit_within_area_h = stats["within_area_transits"]["total_duration_h"]
        transit_to_area_h = stats["port_transits_to_area"]["total_duration_h"]
        transit_from_area_h = stats["port_transits_from_area"]["total_duration_h"]

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

        # 2. Discover and process all scientific operations dynamically
        # Group operations by (operation_class, op_type) combinations
        operation_groups = {}
        for activity in timeline:
            operation_class = activity.get("operation_class", "Unknown")
            op_type = activity.get("op_type", "")

            # Skip non-scientific operations (ports, transits)
            if operation_class == "NavigationalTransit" or op_type == "port":
                continue

            key = (operation_class, op_type)
            if key not in operation_groups:
                operation_groups[key] = []
            operation_groups[key].append(activity)

        # Create summary rows for each operation type
        for (operation_class, op_type), activities in operation_groups.items():
            if not activities:
                continue

            total_duration_h = sum(a["duration_minutes"] for a in activities) / 60.0
            count = len(activities)

            # Determine activity name and notes based on operation class and type
            if operation_class == "PointOperation":
                if op_type == "station":
                    activity_name = "CTD/Station Operations"
                    notes = f"{count} stations"
                elif op_type == "mooring":
                    activity_name = "Mooring Operations"
                    notes = f"{count} operations"
                else:
                    activity_name = f"{op_type.title()} Operations"
                    notes = f"{count} operations"
            elif operation_class == "LineOperation":
                activity_name = "Scientific Surveys"
                total_distance_nm = sum(a.get("dist_nm", 0) for a in activities)
                notes = f"{count} surveys, {total_distance_nm:.1f} nm"
            elif operation_class == "AreaOperation":
                activity_name = "Area Survey Operations"
                notes = f"{count} survey areas"
            else:
                activity_name = f"{operation_class} Operations"
                notes = f"{count} operations"

            summary_rows.append(
                {
                    "area": "",  # Area will be populated by caller for multi-leg
                    "activity": activity_name,
                    "duration_h": f"{total_duration_h:.1f}",
                    "transit_h": "",  # No transit time for this row
                    "notes": notes,
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
    config: CruiseConfig, timeline: list[ActivityRecord], output_dir: Path
) -> list[Path]:
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

    # Generate individual tables (revert to separate files for multi-leg support)
    try:
        stations_table = generator.generate_stations_table(config, timeline)
        work_days_table = generator.generate_work_days_table(config, timeline)
    except Exception:
        logging.exception("Failed to generate LaTeX tables")
        return []

    # Write to files
    output_dir.mkdir(exist_ok=True, parents=True)

    # Use standardized base name generation
    from cruiseplan.utils.io import setup_output_paths

    _, base_name = setup_output_paths(
        config_file="dummy", output_dir=str(output_dir), output=None
    )
    # Override with actual cruise name if available
    if hasattr(config, "cruise_name") and config.cruise_name:
        base_name = str(config.cruise_name).replace(" ", "_").replace("/", "-")

    # Generate separate files with consistent naming
    stations_file = output_dir / f"{base_name}_stations.tex"
    work_days_file = output_dir / f"{base_name}_work_days.tex"

    stations_file.write_text(stations_table, encoding="utf-8")
    work_days_file.write_text(work_days_table, encoding="utf-8")

    files_created.append(stations_file)
    files_created.append(work_days_file)

    return files_created
