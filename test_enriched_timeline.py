#!/usr/bin/env python3
"""Test enriched YAML with timeline generation."""

import sys

sys.path.insert(0, ".")

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.cruise import Cruise

try:
    # Use the enriched YAML
    cruise = Cruise("/private/tmp/test_enriched_enriched.yaml")
    timeline = generate_timeline(cruise.config, cruise.runtime_legs)

    print("Timeline with enriched ports:")
    for i, activity in enumerate(timeline):
        print(
            f"  {i+1}: activity='{activity.get('activity')}', label='{activity.get('label')}', action='{activity.get('action')}', op_type='{activity.get('op_type')}'"
        )

        # Test the HTML formatting too
        from cruiseplan.output.output_utils import format_activity_type

        formatted = format_activity_type(activity)
        print(f"       Formatted type: '{formatted}'")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
