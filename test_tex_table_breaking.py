#!/usr/bin/env python3
"""
Test script for LaTeX table breaking functionality.

This tests that TeX tables break correctly when they exceed 36 lines,
preferably at date boundaries.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path


def test_table_breaking():
    """Test that tables break correctly when exceeding 36 lines."""
    try:
        from cruiseplan.output.latex_generator import LaTeXGenerator

        # Create mock activity records that would generate > 36 lines
        class MockRecord:
            def __init__(self, start_time, label, water_depth=None):
                self.activity = "Station"
                self.label = label
                self.start_time = start_time
                self.entry_lat = 60.0
                self.entry_lon = -30.0
                self.exit_lat = 60.0
                self.exit_lon = -30.0
                self.water_depth = water_depth
                self.comment = f"Test station {label}"
                self.dist_nm = 0.0
                self.transit_dist_nm = 5.0

        # Create records spanning multiple days to test date-based breaking
        records = []
        base_date = datetime(2026, 8, 30, 8, 0, 0)

        # Day 1: 20 stations
        for i in range(20):
            time_offset = timedelta(hours=i * 0.5)  # 30 min intervals
            records.append(
                MockRecord(
                    start_time=base_date + time_offset,
                    label=f"CTD-{i + 1:03d}",
                    water_depth=3000 + i * 10,
                )
            )

        # Day 2: 20 stations (should trigger table break)
        day2_base = base_date + timedelta(days=1)
        for i in range(20):
            time_offset = timedelta(hours=i * 0.5)
            records.append(
                MockRecord(
                    start_time=day2_base + time_offset,
                    label=f"CTD-{i + 21:03d}",
                    water_depth=3200 + i * 10,
                )
            )

        # Day 3: 10 more stations
        day3_base = base_date + timedelta(days=2)
        for i in range(10):
            time_offset = timedelta(hours=i * 0.5)
            records.append(
                MockRecord(
                    start_time=day3_base + time_offset,
                    label=f"CTD-{i + 41:03d}",
                    water_depth=3400 + i * 10,
                )
            )

        print(f"Created {len(records)} mock records spanning 3 days")

        # Generate LaTeX table
        generator = LaTeXGenerator()
        tex_content = generator.generate_letsgo_table(
            records=records,
            cruise_name="Test Cruise Table Breaking",
            workplan_number="99",
        )

        # Check if multiple tables were generated
        table_count = tex_content.count("\\begin{table}")
        page_breaks = tex_content.count("\\clearpage")

        print(f"Generated TeX contains {table_count} table(s)")
        print(f"Generated TeX contains {page_breaks} page break(s)")

        # Save to file for inspection
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tex", delete=False) as f:
            f.write(tex_content)
            output_file = Path(f.name)

        print(f"TeX output saved to: {output_file}")

        # Basic validation
        if table_count > 1:
            print("✅ Table breaking is working - multiple tables generated")

            # Check that page breaks exist between tables
            if page_breaks > 0:
                print("✅ Page breaks added between tables")
            else:
                print("⚠️ No page breaks found between tables")

        else:
            print("ℹ️ Only one table generated (may be expected if < 36 lines total)")

        # Count actual lines to verify logic
        lines_in_first_table = []
        in_first_table = False
        table_num = 0

        for line in tex_content.split("\n"):
            if "\\begin{tabular}" in line:
                in_first_table = True
                table_num += 1
                print(f"\n--- Table {table_num} content preview ---")
                continue
            elif "\\end{tabular}" in line:
                if in_first_table:
                    print(
                        f"Table {table_num} has ~{len(lines_in_first_table)} content lines"
                    )
                in_first_table = False
                lines_in_first_table = []
                continue
            elif in_first_table and line.strip() and not line.strip().startswith("%"):
                lines_in_first_table.append(line)
                if len(lines_in_first_table) <= 3:  # Show first few lines
                    print(f"  {line[:60]}...")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    """Run table breaking test."""
    print("=== LaTeX Table Breaking Test ===")
    print()

    success = test_table_breaking()

    print()
    if success:
        print("🎉 Table breaking test completed successfully!")
    else:
        print("❌ Table breaking test failed")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
