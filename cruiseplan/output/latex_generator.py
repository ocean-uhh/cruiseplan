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
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from jinja2 import Environment, FileSystemLoader

from cruiseplan.config.cruise_config import CruiseConfig
from cruiseplan.config.values import DEFAULT_DEPTH, DEFAULT_MOORING_DURATION_MIN
from cruiseplan.output.output_utils import _duration_hours, _positive_depth
from cruiseplan.output.provenance import provenance_lines
from cruiseplan.timeline.record import ActivityRecord
from cruiseplan.timeline.scheduler import fill_duration_summary, timeline_minutes
from cruiseplan.utils.coordinates import ddm_parts, distance_nm, format_position_latex
from cruiseplan.utils.units import hours_to_days, round_to_minutes

logger = logging.getLogger(__name__)


def _format_depth_for_latex(activity: ActivityRecord) -> str:
    """Depth for a table cell: operation depth, else water depth; "fill" or "N/A"."""
    depth = activity.operation_depth_m
    if depth is None:
        depth = activity.water_depth_m
    if depth is None:
        return "N/A"
    depth = _positive_depth(depth)
    return "fill" if depth == DEFAULT_DEPTH else f"{depth:.0f}"


def _provenance_comment(config: CruiseConfig, timeline: list[ActivityRecord]) -> str:
    """Return TeX comment lines with the schedule provenance and fill durations."""
    lines = [f"% {line}" for line in provenance_lines(config)]
    filled = list(dict.fromkeys(str(a.label) for a in timeline if a.duration_is_fill))
    if filled:
        summary = fill_duration_summary(timeline)
        if summary:
            lines.append(f"% {summary}")
        lines.append(
            f"% fill duration {DEFAULT_MOORING_DURATION_MIN / 60:.0f} h used for: "
            + ", ".join(filled)
        )
    return "\n".join(lines) + "\n"


def _row_hours(row: dict[str, str]) -> float:
    """Hours in a work-days row (operation plus transit column)."""
    return sum(float(row[key]) for key in ("duration_h", "transit_h") if row[key])


def _format_duration_hours(activity: ActivityRecord) -> str:
    """Format the duration in hours, marking the fill value."""
    hours, is_fill = _duration_hours(activity)
    return f"{hours} (fill)" if is_fill else hours


def _is_station_record(record: ActivityRecord) -> bool:
    """Return True for a station or mooring record (waypoints excluded)."""
    op_type = (record.op_type or "").lower()
    return record.kind in {"station", "mooring"} and op_type != "waypoint"


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

    def __init__(self) -> None:
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
        Split data rows into pages and add metadata (caption, header).

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
        self, _config: CruiseConfig, timeline: list[ActivityRecord]
    ) -> list[dict[str, str]]:
        """
        Extract station/operation data from timeline for table generation.

        Returns
        -------
        List[Dict[str, str]]
            List of dictionaries with station data for LaTeX table.
        """
        # Science records only (no ports, transits or buffers)
        science_operations = [activity for activity in timeline if activity.is_science]

        # Format rows for the LaTeX template
        table_rows = []
        for op in science_operations:
            if op.kind == "line":
                # Line operations (surveys): start and end of the line
                start_pos_str = format_position_latex(op.entry_lat, op.entry_lon)
                end_pos_str = format_position_latex(op.exit_lat, op.exit_lon)
                action = op.action or op.op_type
                depth_str = "N/A"  # Surveys typically don't have a single station depth

                table_rows.append(
                    {
                        "operation": f"Line ({action})",
                        "station": str(op.label).replace("_", "-"),
                        "position": f"({start_pos_str}) to ({end_pos_str})",
                        "depth_m": depth_str,
                        "start_time": op.start_time.strftime("%Y-%m-%d %H:%M"),
                        "duration_hours": _format_duration_hours(op),
                    }
                )

            elif op.kind == "area":
                # Area operations (polygon-based operations like bathymetry surveys)
                position_str = format_position_latex(op.entry_lat, op.entry_lon)
                action = op.action

                table_rows.append(
                    {
                        "operation": f"Area ({action})",
                        "station": str(op.label).replace("_", "-"),
                        "position": f"Center: {position_str}",
                        "depth_m": "Variable",  # Areas typically span multiple depths
                        "start_time": op.start_time.strftime("%Y-%m-%d %H:%M"),
                        "duration_hours": _format_duration_hours(op),
                    }
                )

            else:
                # Point operations (Station, Mooring)
                position_str = format_position_latex(op.entry_lat, op.entry_lon)
                activity_type = op.activity

                table_rows.append(
                    {
                        "operation": activity_type,
                        "station": str(op.label).replace("_", "-"),
                        "position": position_str,
                        "depth_m": _format_depth_for_latex(op),
                        "start_time": op.start_time.strftime("%Y-%m-%d %H:%M"),
                        "duration_hours": _format_duration_hours(op),
                    }
                )

        return table_rows

    def generate_stations_table(
        self, config: CruiseConfig, timeline: list[ActivityRecord]
    ) -> str:
        """Generate the Working Area, Stations and Profiles table from the timeline."""
        template = self.env.get_template("stations_table.tex.j2")

        table_rows = self._generate_stations_rows(config, timeline)
        paginated_data = self._paginate_data(table_rows, "stations")

        cruise_name = str(config.cruise_name).replace("_", "-")
        return template.render(cruise_name=cruise_name, pages=paginated_data)

    def generate_work_days_table(
        self, config: CruiseConfig, timeline: list[ActivityRecord]
    ) -> str:
        """
        Generate the Work Days at Sea table from the scheduler timeline.

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
        # Multiple legs - generate unified table with leg information in Area column
        return self._generate_unified_multi_leg_work_days_table(
            config, timeline, leg_names
        )

    def _generate_single_work_days_table(
        self, config: CruiseConfig, timeline: list[ActivityRecord]
    ) -> str:
        """Generate a single work days table for the entire cruise."""
        template = self.env.get_template("work_days_table.tex.j2")

        # Generate work days rows for the timeline
        summary_rows = self._generate_work_days_rows_for_timeline(timeline)

        # Totals: the rows, which add up to the elapsed time
        total_operation_duration_h = sum(
            float(row["duration_h"]) for row in summary_rows if row["duration_h"]
        )
        total_transit_h = sum(
            float(row["transit_h"]) for row in summary_rows if row["transit_h"]
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
        """Generate separate work days tables for each leg."""
        template = self.env.get_template("work_days_table.tex.j2")

        all_tables = []

        for leg_name in leg_names:
            # Filter timeline activities for this leg
            leg_timeline = [
                activity for activity in timeline if activity.leg_name == leg_name
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
        """Generate a unified work days table with leg information in the Area column."""
        template = self.env.get_template("work_days_table.tex.j2")

        all_summary_rows = []
        total_operation_duration_h = 0.0
        total_transit_h = 0.0

        for leg_name in leg_names:
            # Filter timeline activities for this leg
            leg_timeline = [
                activity for activity in timeline if activity.leg_name == leg_name
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

        # Leg delays lie between the legs: add them so the total is elapsed time
        between_h = (
            timeline_minutes(timeline) / 60.0
            - total_operation_duration_h
            - total_transit_h
        )
        if between_h >= 0.05:
            all_summary_rows.append(
                {
                    "area": "",
                    "activity": "Waiting between legs",
                    "duration_h": f"{between_h:.1f}",
                    "transit_h": "",
                    "notes": "Leg delays",
                }
            )
            total_operation_duration_h += float(f"{between_h:.1f}")

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
        """Extract work days summary rows from a timeline (used for both single and multi-leg)."""
        summary_rows = []

        # Use scheduler statistics instead of manual calculations
        from cruiseplan.timeline.scheduler import calculate_timeline_statistics

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
                    if activity.activity not in ["Port_Departure", "Port_Arrival"]
                ),
                None,
            )
            destination = first_operation.label if first_operation else "working area"

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
        # Group science records by (kind, op_type); ports, transits and
        # buffers are reported separately. CTD casts and generic stations
        # are one group.
        operation_groups = {}
        for activity in timeline:
            if not activity.is_science:
                continue
            op_type = activity.op_type
            if activity.kind == "station" and (op_type or "").lower() in {
                "ctd",
                "station",
                "",
            }:
                op_type = "station"
            key = (activity.kind, op_type)
            if key not in operation_groups:
                operation_groups[key] = []
            operation_groups[key].append(activity)

        # Create summary rows for each operation type
        for (kind, op_type), activities in operation_groups.items():
            if not activities:
                continue

            total_duration_h = sum(a.duration_minutes for a in activities) / 60.0
            count = len(activities)

            # Determine activity name and notes based on operation class and type
            if kind == "mooring":
                activity_name = "Mooring Operations"
                notes = f"{count} operations"
            elif kind == "line":
                activity_name = "Scientific Surveys"
                total_distance_nm = sum(a.dist_nm for a in activities)
                notes = f"{count} surveys, {total_distance_nm:.1f} nm"
            elif kind == "area":
                activity_name = "Area Survey Operations"
                notes = f"{count} survey areas"
            elif op_type == "station":
                activity_name = "CTD/Station Operations"
                notes = f"{count} stations"
            else:
                activity_name = f"{(op_type or 'station').title()} Operations"
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

        # Waiting (leg delays) and contingency (buffers): the rest of the
        # elapsed time, so the rows add up to the schedule total
        listed_h = sum(_row_hours(row) for row in summary_rows) + transit_from_area_h
        remainder_h = timeline_minutes(timeline) / 60.0 - listed_h
        if remainder_h >= 0.05:
            summary_rows.append(
                {
                    "area": "",
                    "activity": "Waiting and contingency",
                    "duration_h": f"{remainder_h:.1f}",
                    "transit_h": "",
                    "notes": "Leg delays and buffer time",
                }
            )

        # 7. Navigation Transit (From Area)
        if transit_from_area_h > 0:
            # Find last operational activity (non-port) as working area origin
            last_operation = None
            for activity in reversed(timeline):
                if activity.activity not in ["Port_Departure", "Port_Arrival"]:
                    last_operation = activity
                    break
            origin = last_operation.label if last_operation else "working area"

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

    def generate_letsgo_table(
        self,
        records: list[ActivityRecord],
        cruise_name: str = "Cruise",
        config: CruiseConfig | None = None,  # noqa: ARG002 - public keyword, kept for callers
        logo_path: str | Path | None = None,
        workplan_number: str | None = None,
        cruise_title: str | None = None,
    ) -> str:
        """
        Generate TeX table in letsgo.m format from ActivityRecord objects.

        This replicates the texprint function from letsgo.m using rich NetCDF data.

        Parameters
        ----------
        records : list[ActivityRecord]
            ActivityRecord objects (typically from NetCDF reader).
        cruise_name : str
            Name of cruise for table header. Default is ``"Cruise"``.
        config : CruiseConfig, optional
            Accepted for compatibility and not used: the header takes the
            cruise name from ``cruise_name`` and ``cruise_title``.
        logo_path : str or Path, optional
            Path to a logo image file (PNG, JPG, PDF). If None, the generator
            searches ``config/images/`` for ``project_logo.*`` or
            ``institution_logo.*``. If no logo is found, a plain-text title is
            used instead.
        workplan_number : str, optional
            Workplan number printed in the TeX header (e.g. ``"28"``).
        cruise_title : str, optional
            Cruise title printed in the TeX header (e.g. ``"MSM142"``).

        Returns
        -------
        str
            TeX table content in letsgo.m format.
        """
        # Filter out transits for cleaner output (like MATLAB version)
        station_records = [r for r in records if r.activity != "Transit"]

        # Generate TeX content with table breaking support
        table_sections = []  # Store table sections for breaking long tables
        current_table_lines = []
        line_count = 0
        max_lines_per_table = 36

        # Track current date for potential break points
        current_date = None
        potential_break_points = []  # Store indices where we could break at date changes

        # First print the date
        if station_records:
            first_time = self._round_time_to_10min(station_records[0].start_time)
            first_date = first_time.strftime("%d.%m.%Y")
            first_day = first_time.strftime("%A")
            date_line = f"\\rowcolor{{pink!40}}\\multicolumn{{2}}{{l}}{{\\textbf{{{first_date} {first_day}}}}} & & & & \\\\"
            current_table_lines.append(date_line)
            line_count += 1
            current_date = first_time.date()

        for i, record in enumerate(station_records):
            # Date headers follow the printed (rounded) time
            rounded_time = self._round_time_to_10min(record.start_time)
            if rounded_time.date() != current_date:
                current_date = rounded_time.date()
                date_str = rounded_time.strftime("%d.%m.%Y")
                day_str = rounded_time.strftime("%A")

                # Check if we need to break the table before adding this date
                if line_count > max_lines_per_table:
                    # Break the table here - save current table and start new one
                    table_sections.append(current_table_lines)
                    current_table_lines = []
                    line_count = 0
                    potential_break_points = []

                # Mark this as a potential break point for future use
                potential_break_points.append((len(current_table_lines), line_count))

                date_line = f"\\rowcolor{{pink!40}}\\multicolumn{{2}}{{l}}{{\\textbf{{{date_str} {day_str}}}}} & & & & \\\\"
                current_table_lines.append(date_line)
                line_count += 1

            # Time and position
            time_str = rounded_time.strftime("%H:%M")

            # Use entry coordinates from NetCDF data
            lat_str, lon_str = self._format_lat_lon_dms(
                record.entry_lat, record.entry_lon
            )
            position = f"{time_str} & {lat_str}\\quad{lon_str}"

            # Lines and areas also print their exit position
            is_line_operation = record.kind in {"line", "area"}

            # Water depth column for point operations other than ports/waypoints
            is_station = _is_station_record(record)

            if (
                is_station
                and record.water_depth_m is not None
                and not np.isnan(record.water_depth_m)
            ):
                water_depth = _positive_depth(record.water_depth_m)
                if water_depth == DEFAULT_DEPTH:
                    depth_str = " & fill"
                else:
                    depth_str = f" & {water_depth:4.0f} m"
            else:
                depth_str = " &       "

            # Add midrule before each new activity (except the first one)
            if i > 0:
                current_table_lines.append("\\midrule")
                line_count += 1

            # Station name/label and comment
            station_name = self._escape_latex_text(record.label)
            comment = self._escape_latex_text(getattr(record, "comment", "") or "")

            if is_line_operation:
                # For line operations: show start position with operation distance on same line
                operation_distance = getattr(record, "dist_nm", 0.0)
                if operation_distance > 0.5:
                    distance_str = f"{operation_distance:.1f} nm"
                else:
                    distance_str = ""

                current_table_lines.append(
                    f"{position}{depth_str} & {distance_str} & {station_name} & {comment} \\\\"
                )
                line_count += 1

                # Show end position on next line (without time)
                exit_lat_str, exit_lon_str = self._format_lat_lon_dms(
                    record.exit_lat, record.exit_lon
                )
                current_table_lines.append(
                    f"  & {exit_lat_str}\\quad{exit_lon_str} &        & &  &  \\\\"
                )
                line_count += 1

                # Add repositioning distance to next activity if > 0.5 nm
                transit_dist = record.transit_dist_nm or 0.0
                if transit_dist > 0.5:
                    current_table_lines.append(
                        f" &                       "
                        f"&        & +{transit_dist:.1f} nm &  \\\\"
                    )
                    line_count += 1
            else:
                # For point operations: show normally
                current_table_lines.append(
                    f"{position}{depth_str} & & {station_name} & {comment} \\\\"
                )
                line_count += 1

                # Add transit distance to next station if > 0.5 nm
                transit_dist = record.transit_dist_nm or 0.0
                if transit_dist > 0.5:
                    current_table_lines.append(
                        f" &                       "
                        f"&        & +{transit_dist:.1f} nm &  \\\\"
                    )
                    line_count += 1

        # Add the final table section
        if current_table_lines:
            table_sections.append(current_table_lines)

        # If no sections were created (table is <= 36 lines), use all lines as single table
        if not table_sections:
            table_sections = [current_table_lines]

        # Generate multiple table content sections
        table_contents = []
        for section_lines in table_sections:
            table_content = "\n".join(section_lines)
            table_contents.append(table_content)

        # Create new title format: "MSM142 - Workplan XX" and date range
        # Use provided cruise title or extract from cruise name
        if cruise_title:
            main_cruise_name = cruise_title
        else:
            # Extract cruise name and clean it up as fallback
            base_cruise_name = cruise_name

            # Remove various suffixes
            suffixes_to_remove = [
                " schedule forecast",
                "schedule forecast",
                " schedule",
                "schedule",
            ]
            for suffix in suffixes_to_remove:
                if suffix in base_cruise_name.lower():
                    # Case-insensitive removal
                    idx = base_cruise_name.lower().find(suffix.lower())
                    if idx >= 0:
                        base_cruise_name = (
                            base_cruise_name[:idx]
                            + base_cruise_name[idx + len(suffix) :]
                        )
                        break

            # Replace underscores with spaces and clean up
            base_cruise_name = base_cruise_name.replace("_", " ").strip()

            # Extract just the cruise identifier (e.g., "MSM142" from "MSM142 StJohns")
            cruise_parts = base_cruise_name.split()
            main_cruise_name = cruise_parts[0] if cruise_parts else base_cruise_name

        # Use provided workplan number or default
        workplan_num = workplan_number if workplan_number else "01"

        # Calculate date range from records
        if station_records:
            start_date = self._round_time_to_10min(station_records[0].start_time)
            end_date = self._round_time_to_10min(station_records[-1].start_time)

            # Format dates for title using portable day formatting
            start_str = str(start_date.day)  # Day without leading zero
            end_str = str(end_date.day)  # Day without leading zero
            month_year = end_date.strftime("%B %Y")  # Full month name and year

            date_range = f"{start_str}--{end_str} {month_year}"
        else:
            date_range = ""

        # Handle logo inclusion
        logo_header = ""
        logo_packages = ""

        if logo_path:
            # Resolve to absolute path so \includegraphics works regardless of
            # where pdflatex is invoked (output dir differs from CWD at compile time).
            logo_file = Path(logo_path).resolve()
            if logo_file.exists():
                logo_packages = "\\usepackage{graphicx}\n"
                # Create header with logo and new title format
                logo_header = f"""\\begin{{center}}
\\includegraphics[width=0.3\\textwidth]{{{logo_file.as_posix()}}}\\\\[0.5cm]
\\Large \\textbf{{{main_cruise_name} - Workplan {workplan_num}}}\\\\
\\textbf{{{date_range}}}
\\end{{center}}
\\vspace{{0.5cm}}

"""
            else:
                # Logo file doesn't exist, fall back to text title
                logo_header = f"""\\section*{{\\textbf{{{main_cruise_name} - Workplan {workplan_num}}}}}
\\textbf{{{date_range}}}

"""
        else:
            # Try to find default logo
            default_logos = [
                "config/images/project_logo.png",
                "config/images/project_logo.pdf",
                "config/images/project_logo.jpg",
                "config/images/institution_logo.png",
                "config/images/institution_logo.pdf",
                "config/images/institution_logo.jpg",
            ]

            for default_logo in default_logos:
                logo_file = Path(default_logo).resolve()
                if logo_file.exists():
                    logo_packages = "\\usepackage{graphicx}\n"
                    logo_header = f"""\\begin{{center}}
\\includegraphics[width=0.3\\textwidth]{{{logo_file.as_posix()}}}\\\\[0.5cm]
\\Large \\textbf{{{main_cruise_name} - Workplan {workplan_num}}}\\\\
\\textbf{{{date_range}}}
\\end{{center}}
\\vspace{{0.5cm}}

"""
                    break
            else:
                # No logo found, use text title
                logo_header = f"""\\section*{{\\textbf{{{main_cruise_name} - Workplan {workplan_num}}}}}
\\textbf{{{date_range}}}

"""

        # Generate table blocks for each section
        table_blocks = []
        for _i, table_content in enumerate(table_contents):
            table_block = f"""\\begin{{table}}[htbp]
\\begin{{tabular}}{{lllllp{{2in}}}}
\\toprule
Time & Position & Depth & Distance & Station & Comment \\\\
\\ LT & &\\quad m & \\quad nm & \\\\
\\midrule
{table_content}
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""
            table_blocks.append(table_block)

        # Join tables with page breaks between them if there are multiple tables
        if len(table_blocks) > 1:
            all_tables = "\n\n\\clearpage\n\n".join(table_blocks)
        else:
            all_tables = table_blocks[0]

        return f"""\\documentclass{{article}}
\\usepackage{{booktabs}}
\\usepackage{{geometry}}
\\usepackage{{textcomp}}
\\usepackage{{xcolor}}
\\usepackage{{colortbl}}
{logo_packages}\\geometry{{a4paper,margin=1in}}

\\begin{{document}}

{logo_header}

{all_tables}

\\end{{document}}
"""

    def _escape_latex_text(self, text: str) -> str:
        """Escape LaTeX special characters in text."""
        return (
            text.replace("_", " ")
            .replace("&", "\\&")
            .replace("%", "\\%")
            .replace("$", "\\$")
            .replace("#", "\\#")
            .replace("{", "\\{")
            .replace("}", "\\}")
        )

    def _get_original_station_coordinates(
        self, station_name: str, config: CruiseConfig | None = None
    ) -> tuple[float, float, bool]:
        """
        Get original station coordinates from cruise configuration.

        Returns (lat, lon, found) where found indicates if station was found in config.
        """
        if config is None:
            return 0.0, 0.0, False

        try:
            # Look for station in cruise configuration points
            if hasattr(config, "points") and config.points:
                for point in config.points:
                    if (
                        hasattr(point, "name")
                        and point.name == station_name
                        and hasattr(point, "latitude")
                        and hasattr(point, "longitude")
                    ):
                        return float(point.latitude), float(point.longitude), True

            # Also check legs->clusters->activities if no direct match
            if hasattr(config, "legs") and config.legs:
                for leg in config.legs:
                    if hasattr(leg, "clusters") and leg.clusters:
                        for cluster in leg.clusters:
                            if hasattr(cluster, "activities") and cluster.activities:
                                for activity_name in cluster.activities:
                                    if activity_name == station_name:
                                        # Found in cluster, now look for the point definition
                                        for point in config.points:
                                            if (
                                                hasattr(point, "name")
                                                and point.name == station_name
                                            ):
                                                return (
                                                    float(point.latitude),
                                                    float(point.longitude),
                                                    True,
                                                )

        except Exception as e:  # noqa: BLE001 - best-effort lookup; falls back to timeline coordinates
            logger.warning(
                f"Error looking up original coordinates for {station_name}: {e}"
            )

        return 0.0, 0.0, False

    def _verify_station_coordinates(
        self, record: ActivityRecord, config: CruiseConfig | None = None
    ) -> tuple[float, float, str]:
        """
        Verify station coordinates and return the correct ones to use.

        Returns (lat, lon, note) where note indicates any coordinate discrepancies.
        """
        # For non-station activities, use the timeline coordinates
        if record.activity not in ["Station", "Mooring"]:
            return record.entry_lat, record.entry_lon, ""

        # For stations, check against original configuration
        orig_lat, orig_lon, found = self._get_original_station_coordinates(
            record.label, config
        )

        if not found:
            # Use timeline coordinates if no original found
            return record.entry_lat, record.entry_lon, " (from timeline)"

        # Check if coordinates match (within reasonable tolerance)
        lat_diff = abs(orig_lat - record.entry_lat)
        lon_diff = abs(orig_lon - record.entry_lon)

        if lat_diff > 0.001 or lon_diff > 0.001:  # ~100m tolerance
            # Coordinates differ - use original and add note
            logger.warning(
                f"Station {record.label}: coordinate mismatch. "
                f"Original: {orig_lat:.6f}, {orig_lon:.6f} "
                f"Timeline: {record.entry_lat:.6f}, {record.entry_lon:.6f}"
            )
            return orig_lat, orig_lon, " (corrected)"
        # Coordinates match - use original
        return orig_lat, orig_lon, ""

    def _round_time_to_10min(self, dt: datetime) -> datetime:
        """Round time to nearest 10 minutes like letsgo.m, carrying into the date."""
        return round_to_minutes(dt, 10)

    def _format_lat_lon_dms(self, lat: float, lon: float) -> tuple[str, str]:
        """Format latitude/longitude in degrees/minutes like MATLAB gllfancy."""
        # Format latitude - use ASCII characters for LaTeX compatibility
        lat_deg, lat_min = ddm_parts(lat, 2)
        lat_hem = "N" if lat >= 0 else "S"
        lat_str = f"{lat_deg:02d}\\textdegree{lat_min:05.2f}'{lat_hem}"

        # Format longitude - use ASCII characters for LaTeX compatibility
        lon_deg, lon_min = ddm_parts(lon, 2)
        lon_hem = "E" if lon >= 0 else "W"
        lon_str = f"{lon_deg:03d}\\textdegree{lon_min:05.2f}'{lon_hem}"

        return lat_str, lon_str

    def _calculate_distances_nm(self, records: list[ActivityRecord]) -> list[float]:
        """Calculate distances between stations in nautical miles."""
        distances = [0.0]  # First station has no distance

        for i in range(1, len(records)):
            distances.append(
                distance_nm(
                    (records[i - 1].entry_lat, records[i - 1].entry_lon),
                    (records[i].entry_lat, records[i].entry_lon),
                )
            )

        return distances


def generate_letsgo_table_from_netcdf(
    netcdf_path: Path,
    output_path: Path | None = None,
    logo_path: str | Path | None = None,
    workplan_number: str | None = None,
    cruise_title: str | None = None,
) -> Path:
    """
    Generate TeX table in letsgo.m format from NetCDF schedule file.

    Parameters
    ----------
    netcdf_path : Path
        Path to NetCDF schedule file
    output_path : Path, optional
        Output path for .tex file. If None, uses netcdf_path with .tex extension
    logo_path : str or Path, optional
        Path to a logo image (PNG, JPG or PDF). If None, ``config/images/`` is
        searched for a default logo.
    workplan_number : str, optional
        Workplan number printed in the TeX header (e.g. ``"28"``).
    cruise_title : str, optional
        Cruise title printed in the TeX header (e.g. ``"MSM142"``).

    Returns
    -------
    Path
        Path to generated .tex file
    """
    from cruiseplan.forecast.reader import netcdf_to_activity_records, read_schedule

    if output_path is None:
        output_path = netcdf_path.with_suffix(".tex")

    # Read NetCDF and convert to ActivityRecord objects
    schedule = read_schedule(netcdf_path)
    try:
        records = netcdf_to_activity_records(schedule)
    finally:
        schedule.close()

    # Generate TeX table
    generator = LaTeXGenerator()
    cruise_name = netcdf_path.stem
    tex_content = generator.generate_letsgo_table(
        records,
        cruise_name,
        logo_path=logo_path,
        workplan_number=workplan_number,
        cruise_title=cruise_title,
    )

    # Write to file
    output_path.write_text(tex_content, encoding="utf-8")

    return output_path


def generate_latex_tables(
    config: CruiseConfig,
    timeline: list[ActivityRecord],
    output_dir: Path,
    base_name: str | None = None,
) -> list[Path]:
    """
    Generate LaTeX tables for a cruise proposal from the scheduler timeline.

    Parameters
    ----------
    config : CruiseConfig
        The cruise configuration object
    timeline : List[ActivityRecord]
        Timeline generated by the scheduler
    output_dir : Path
        Directory to write output files
    base_name : str, optional
        Filename stem for the .tex files. If None, a default stem is derived.

    Returns
    -------
    list of Path
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

    # Use provided base_name or generate one if not provided
    if base_name is None:
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

    header = _provenance_comment(config, timeline)
    stations_file.write_text(header + stations_table, encoding="utf-8")
    work_days_file.write_text(header + work_days_table, encoding="utf-8")

    files_created.append(stations_file)
    files_created.append(work_days_file)

    return files_created
