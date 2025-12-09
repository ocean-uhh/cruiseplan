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
        ]

        # Format rows for the LaTeX template
        table_rows = []
        for op in science_operations:
            position_str = format_position_latex(op["lat"], op["lon"])

            table_rows.append(
                {
                    "operation": op["activity"],
                    "station": op["label"],
                    "position": position_str,
                    "depth_m": f"{op['depth']:.0f}",
                    "start_time": op["start_time"].strftime("%Y-%m-%d %H:%M"),
                    "duration_hours": f"{op['duration_minutes']/60:.1f}",
                }
            )

        paginated_data = self._paginate_data(table_rows, "stations")

        return template.render(cruise_name=config.cruise_name, pages=paginated_data)

    def generate_work_days_table(
        self, config: CruiseConfig, timeline: List[ActivityRecord]
    ) -> str:
        """
        Generates the Work Days at Sea table from scheduler timeline.
        """
        template = self.env.get_template("work_days_table.tex.j2")

        # Create summary breakdown from timeline activities
        summary_rows = []

        # Group activities by type and location
        transit_activities = [a for a in timeline if a["activity"] == "Transit"]
        station_activities = [a for a in timeline if a["activity"] == "Station"]
        mooring_activities = [a for a in timeline if a["activity"] == "Mooring"]

        # Calculate operation durations in hours (these go in Duration column)
        station_duration_h = sum(a["duration_minutes"] for a in station_activities) / 60
        mooring_duration_h = sum(a["duration_minutes"] for a in mooring_activities) / 60

        # Break down transit activities
        transit_to_area_h = 0.0
        transit_from_area_h = 0.0
        transit_within_area_h = 0.0

        if transit_activities:
            # First transit is to working area, last is from working area
            if len(transit_activities) >= 1:
                transit_to_area_h = transit_activities[0]["duration_minutes"] / 60
            if len(transit_activities) >= 2:
                transit_from_area_h = transit_activities[-1]["duration_minutes"] / 60
            # Any middle transits are within area
            if len(transit_activities) > 2:
                middle_transits = transit_activities[1:-1]
                transit_within_area_h = (
                    sum(a["duration_minutes"] for a in middle_transits) / 60
                )

        total_transit_h = (
            transit_to_area_h + transit_from_area_h + transit_within_area_h
        )

        # Add summary rows (Duration in col 3, Transit in col 4)
        summary_rows.append(
            {
                "activity": "Transit to area",
                "duration_h": "",  # No operation duration
                "transit_h": f"{transit_to_area_h:.1f}",
                "notes": f"{config.departure_port.name} to {config.first_station}",
            }
        )

        if station_activities:
            summary_rows.append(
                {
                    "activity": "CTD/Station Operations",
                    "duration_h": f"{station_duration_h:.1f}",
                    "transit_h": "",  # No transit time for this row
                    "notes": f"{len(station_activities)} stations",
                }
            )

        if mooring_activities:
            summary_rows.append(
                {
                    "activity": "Mooring Operations",
                    "duration_h": f"{mooring_duration_h:.1f}",
                    "transit_h": "",  # No transit time for this row
                    "notes": f"{len(mooring_activities)} operations",
                }
            )

        if transit_within_area_h > 0:
            summary_rows.append(
                {
                    "activity": "Transit within area",
                    "duration_h": "",  # No operation duration
                    "transit_h": f"{transit_within_area_h:.1f}",
                    "notes": "Between operations",
                }
            )

        summary_rows.append(
            {
                "activity": "Transit from area",
                "duration_h": "",  # No operation duration
                "transit_h": f"{transit_from_area_h:.1f}",
                "notes": f"{config.last_station} to {config.arrival_port.name}",
            }
        )

        # Calculate totals
        total_operation_duration_h = station_duration_h + mooring_duration_h
        total_duration_h = total_operation_duration_h + total_transit_h
        total_days = total_duration_h / 24

        # Add total row
        summary_rows.append(
            {
                "activity": "TOTAL",
                "duration_h": f"{total_operation_duration_h:.1f}",
                "transit_h": f"{total_transit_h:.1f}",
                "notes": f"≈ {total_days:.1f} days at sea",
            }
        )

        paginated_data = self._paginate_data(summary_rows, "work_days")

        return template.render(
            cruise_name=config.cruise_name,
            pages=paginated_data,
            total_duration_h=total_duration_h,
            total_transit_h=total_transit_h,
            total_days=total_days,
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


# Backward compatibility function for the old interface
def generate_latex_tables_from_dict(cruise_data: Dict, output_dir: Path) -> List[Path]:
    """
    DEPRECATED: Backward compatibility function for the old dictionary-based interface.
    Use generate_latex_tables(config, timeline, output_dir) instead.
    """
    import warnings

    warnings.warn(
        "generate_latex_tables_from_dict is deprecated. Use generate_latex_tables(config, timeline, output_dir) instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    # This would require converting cruise_data back to config and timeline
    # For now, just raise an error to force migration
    raise NotImplementedError(
        f"Old dictionary-based interface is no longer supported. "
        f"Use generate_latex_tables(config, timeline, output_dir) with scheduler output. "
        f"cruise_data keys: {list(cruise_data.keys())}, output_dir: {output_dir}"
    )
