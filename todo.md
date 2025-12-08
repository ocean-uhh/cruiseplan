
How to link Gemini to VS Code (Phase-by-Phase)

To execute this, do not try to generate the whole project at once. You should act as the Product Manager, and Gemini acts as the Lead Developer.

Prerequisite: The Tooling

VS Code: Install Visual Studio Code.

Extension: Install "Google Cloud Code" (official) or use the Gemini 1.5 Pro interface in your browser and copy-paste files.

Recommendation: For a project of this size, I recommend using the Browser Interface (AI Studio) for generating large chunks of code (High Context Window) and VS Code for running/debugging.

Phase 1: The Skeleton & Data Model (Week 1)

Goal: Create the directory structure and the Pydantic/YAML validators.

Prompt Gemini:

"I am acting as the Architect. Here is the full project_specification.md. I want to start with Phase 1: Core Infrastructure.

Generate a bash script to create the directory structure cruiseplan/core, cruiseplan/data, etc.

Write core/cruise.py and core/validation.py using Pydantic models that strictly adhere to the YAML Schema in the spec.

Include the fix for the missing start_date and reversible fields we discussed."

Your Action: Run the script, save the Python files. Run pytest on the validation logic with a sample YAML.

Phase 2: The Logic Engines (Week 2)

Goal: Implement the math (Distance, Duration, Routing).

Prompt Gemini:

"We are moving to calculators/. Here is the core/operations.py file we built in Phase 1. Write calculators/distance.py (Haversine) and calculators/duration.py. Crucial: In duration.py, implement the logic that if a task arrives outside its allowed time window (Day/Night), calculate the wait_time required to start."

Phase 3: The Optimizer (Week 3)

Goal: The TSP and Zipper logic.

Prompt Gemini:

"Now write calculators/routing.py. It must implement the three strategies defined in the spec: sequential, day_night_split, and spatial_interleaved. Use the python-tsp library for the spatial optimization. Ensure day_night_split uses the 'Lookahead' logic: Calculate travel time; if Arrival is Night, add Wait Time."

Phase 4: The Interactive CLI (Week 4)

Goal: Tying it together.

Prompt Gemini:

"Write cli/main.py and cli/schedule.py. It should parse the YAML, instantiate the Cruise object, run the optimizer, and print a text summary. Do not worry about HTML/LaTeX output yet. Just prove the schedule works."
