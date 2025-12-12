Installation
============

CruisePlan can be installed using several methods. Choose the one that best fits your environment.

Prerequisites
-------------

- Python 3.9 or higher
- Git (for cloning the repository)

Installation from PyPI
----------------------

Install CruisePlan directly from PyPI:

.. code-block:: bash

   pip install cruiseplan

Installation for Development
-----------------------------

For development or to access the latest features, clone and install from source:

.. code-block:: bash

   git clone https://github.com/ocean-uhh/cruiseplan.git
   cd cruiseplan

   # Option A: Using conda/mamba (recommended)
   conda env create -f environment.yml
   conda activate cruiseplan
   pip install -e .

   # Option B: Using pip
   pip install -r requirements-dev.txt
   pip install -e .

Verification
------------

After installation, verify CruisePlan is working:

.. code-block:: bash

   cruiseplan --help

This should display the command-line help for CruisePlan.