

.. _user_workflow_path_3:

Path 3: Configuration-Only Workflow
====================================

**Best for:** Power users with existing YAML configurations, batch processing, automated workflows

**Use cases:**

- Processing existing cruise configurations
- Updating configurations with new bathymetry data
- Re-running analysis with different parameters
- Integration with external planning tools

Start with Step 4: Enrichment
------------------------------

If you have an existing YAML configuration (created manually or from external tools):

.. code-block:: bash

   cruiseplan enrich -c existing_cruise.yaml --add-depths --add-coords --expand-sections

Continue with Validation and Scheduling
---------------------------------------

.. code-block:: bash

   cruiseplan validate -c enriched_cruise.yaml --check-depths
   cruiseplan schedule -c enriched_cruise.yaml --format all