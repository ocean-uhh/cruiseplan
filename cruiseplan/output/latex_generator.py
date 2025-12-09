"""
LaTeX Table Generation System (Phase 3a).
Generates proposal-ready tables using Jinja2 templates.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader


# Local utility for coordinate conversion
def format_position_latex(lat: float, lon: float) -> str:
    r"""
    Convert decimal degrees to LaTeX-formatted degrees and decimal minutes.

    Example: 53.5 -> 53^\circ 30.00'N
    """
    # --- Latitude ---
    lat_deg = int(abs(lat))
    lat_min = (abs(lat) - lat_deg) * 60
    lat_dir = "N" if lat >= 0 else "S"

    # --- Longitude ---
    lon_deg = int(abs(lon))
    lon_min = (abs(lon) - lon_deg) * 60
    lon_dir = "E" if lon >= 0 else "W"

    # The format uses LaTeX commands for the degree symbol
    return f"{lat_deg:02d}$^\circ${lat_min:05.2f}'${lat_dir}$, {lon_deg:03d}$^\circ${lon_min:05.2f}'${lon_dir}$"


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

    def generate_stations_table(self, cruise_data: Dict) -> str:
        """
        Generates the Working Area, Stations and Profiles table, including pagination.
        """
        template = self.env.get_template("stations_table.tex.j2")

        # Assume 'operations' is a flattened list of all CTDs, Moorings, etc.
        operations = cruise_data.get("operations", [])

        # Format rows for the LaTeX template
        table_rows = []
        for op in operations:
            # We assume a base dictionary structure from the cruise object
            # and format the coordinates using the utility function.
            position_str = format_position_latex(op["latitude"], op["longitude"])

            table_rows.append(
                {
                    "operation": op.get("type", "Unknown"),
                    "station": op.get("name", "N/A"),
                    "position": position_str,
                    "depth_m": f"{op.get('depth', 0):.0f}",
                }
            )

        paginated_data = self._paginate_data(table_rows, "stations")

        return template.render(
            cruise_name=cruise_data["cruise_name"], pages=paginated_data
        )

    def generate_work_days_table(self, cruise_data: Dict) -> str:
        """
        Generates the Work Days at Sea table, assuming summary data exists.
        """
        template = self.env.get_template("work_days_table.tex.j2")

        # We assume 'summary_breakdown' contains pre-calculated rows like
        # 'Transit to Area 1', 'CTD stations', 'Total duration', etc.
        summary_rows = cruise_data.get("summary_breakdown", [])

        # Calculate totals
        total_duration = sum(float(row.get('duration_h', 0) or 0) for row in summary_rows)
        total_transit = sum(float(row.get('transit_h', 0) or 0) for row in summary_rows)

        paginated_data = self._paginate_data(summary_rows, "work_days")

        return template.render(
            cruise_name=cruise_data["cruise_name"],
            pages=paginated_data,
            total_duration_h=total_duration,
            total_transit_h=total_transit
        )


def generate_latex_tables(cruise_data: Dict, output_dir: Path) -> List[Path]:
    """
    Main interface to generate LaTeX tables for cruise proposal.

    Returns
    -------
        List of generated .tex files
    """
    generator = LaTeXGenerator()
    files_created = []

    # 1. Generate individual tables
    try:
        stations_table = generator.generate_stations_table(cruise_data)
        work_days_table = generator.generate_work_days_table(cruise_data)
    except Exception as e:
        logging.error(f"Failed to generate LaTeX tables: {e}")
        return []

    # 2. Write to files
    output_dir.mkdir(exist_ok=True, parents=True)

    stations_file = output_dir / f"{cruise_data['cruise_name']}_stations.tex"
    work_days_file = output_dir / f"{cruise_data['cruise_name']}_work_days.tex"

    stations_file.write_text(stations_table, encoding="utf-8")
    work_days_file.write_text(work_days_table, encoding="utf-8")

    files_created.append(stations_file)
    files_created.append(work_days_file)

    return files_created
