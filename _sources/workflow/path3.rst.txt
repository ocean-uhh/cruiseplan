

.. _user_workflow_path_3:

Path 3: Configuration-Only Workflow
====================================

**Best for:** Power users with existing YAML configurations, batch processing, automated workflows

**Use cases:**

- Processing existing cruise configurations
- Updating configurations with new bathymetry data
- Re-running analysis with different parameters
- Integration with external planning tools

Phase 2, Step 2.2: Process Existing Configuration
------------------------------------------------

If you have an existing YAML configuration (created manually or from external tools):

.. code-block:: bash

   cruiseplan process -c existing_cruise.yaml 

Phase 3: Scheduling
-------------------

.. code-block:: bash

   cruiseplan schedule -c enriched_cruise.yaml  