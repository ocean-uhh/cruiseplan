Installation
============

CruisePlan can be installed using several methods. Choose the one that best fits your environment and use case.

System Requirements
-------------------

**Operating Systems:**

- Linux  
- macOS  
- Windows 10+ 

**Required Software:**

- **Python 3.9 or higher (<3.14)** (3.11+ recommended for best performance)
- **Git** (for development installation)

**Hardware Requirements:**

- **RAM**: 4GB minimum, 8GB+ recommended for large datasets
- **Storage**: 10GB free space (includes bathymetry data)
- **Internet**: Required for initial bathymetry download and PANGAEA integration

Plan for adequate storage space:

.. list-table::
   :widths: 30 20 50
   :header-rows: 1

   * - **Component**
     - **Size**
     - **Purpose**
   * - CruisePlan package
     - ~50MB
     - Core software installation
   * - ETOPO 2022 bathymetry
     - ~500MB
     - Standard resolution depth data (recommended)
   * - GEBCO 2025 bathymetry
     - ~7.5GB
     - High resolution depth data (optional)
   * - PANGAEA datasets
     - Variable
     - Historical cruise data (optional)
   * - Generated outputs
     - ~10-100MB
     - Maps, schedules, configurations per cruise



Install options (PyPI, GitHub)
------------------------------

Option 1: Install from PyPI (Most Users)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For general use, install the latest stable release from PyPI:

.. code-block:: bash

   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

   # Install CruisePlan
   pip install cruiseplan

Then verify installation: run the steps in :ref:`verification_testing`


Option 2: Install Latest from GitHub
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For the latest features and bug fixes:

.. code-block:: bash

   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

   # Install directly from GitHub
   pip install git+https://github.com/ocean-uhh/cruiseplan.git

Then verify installation: run the steps in :ref:`verification_testing`

Option 3: Development Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For development or contributing to CruisePlan:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/ocean-uhh/cruiseplan.git
   cd cruiseplan

   # Option A: Using conda/mamba
   conda env create -f environment.yml
   conda activate cruiseplan
   pip install -e ".[dev]"

   # Option B: Using pip with virtual environment
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"

Then verify installation: run the steps in :ref:`verification_testing`

.. _verification_testing:

Verification & Testing
~~~~~~~~~~~~~~~~~~~~~~

After installation, verify CruisePlan is working correctly:

.. code-block:: bash

   # Check version and core functionality
   cruiseplan --version

   # Display help and available commands
   cruiseplan --help

   # Test bathymetry download (requires internet)
   cruiseplan bathymetry --help

   # Verify interactive components
   python -c "import matplotlib; print('✓ Matplotlib available')"
   python -c "import folium; print('✓ Folium available')"

Expected output should show version information and available subcommands without errors.

.. figure:: _static/screenshots/installation_terminal.png
   :alt: Successful CruisePlan installation verification
   :width: 600px
   :align: center

   Successful CruisePlan installation showing version information and available commands


Core Dependencies
-----------------

Core dependencies are listed in ``requirements.txt``, development tools in ``requirements-dev.txt``. The conda ``environment.yml`` loads from these files automatically.  CruisePlan automatically installs these core dependencies:

**Scientific Computing:**

- `numpy <https://numpy.org/>`_ >= 1.21 (numerical computing)
- `pandas <https://pandas.pydata.org/>`_ >= 1.3.0 (data manipulation)
- `scipy <https://scipy.org/>`_ >= 1.7.0 (scientific algorithms)
- `xarray <https://docs.xarray.dev/>`_ >= 2023.12.0 (multi-dimensional data)
- `netCDF4 <https://unidata.github.io/netcdf4-python/>`_ >= 1.5.8 (scientific data format)

**Web & Data Sources:**

- `requests <https://docs.python-requests.org/>`_ >= 2.25.0 (HTTP requests)
- `pangaeapy <https://github.com/pangaea-data-publisher/pangaeapy>`_ >= 1.0.7 (PANGAEA database integration)

**Configuration & Validation:**

- `pydantic <https://docs.pydantic.dev/>`_ >= 2.0.0 (data validation)
- `ruamel.yaml <https://yaml.readthedocs.io/>`_ >= 0.18.0 (YAML processing)

**Visualization:**

- `matplotlib <https://matplotlib.org/>`_ >= 3.7 (plotting)
- `folium <https://python-visualization.github.io/folium/>`_ (interactive maps)
- `branca <https://github.com/python-visualization/branca>`_ (map styling)

**User Interface:**

- `tqdm <https://tqdm.github.io/>`_ >= 4.65 (progress bars)
- `jinja2 <https://jinja.palletsprojects.com/>`_ (template rendering)




Troubleshooting
---------------

**Issue: "No module named 'cruiseplan'"**

.. code-block:: text

   ImportError: No module named 'cruiseplan'

*Solution:*

- Verify Python environment: ``which python`` and ``python --version``
- Reinstall: ``pip install --force-reinstall cruiseplan``
- Check virtual environment activation

**Issue: Permission denied during installation**

.. code-block:: text

   ERROR: Could not install packages due to an EnvironmentError

*Solution:*

- Use user installation: ``pip install --user cruiseplan``
- Or use virtual environment: ``python -m venv .venv``

**Issue: Dependency conflicts**

.. code-block:: text

   ERROR: pip's dependency resolver does not currently consider all the packages

*Solution:*

- Create fresh virtual environment
- Update pip: ``pip install --upgrade pip setuptools``
- Install in isolated environment


Getting Help
------------

If installation issues persist:

1. **Check existing issues**: `GitHub Issues <https://github.com/ocean-uhh/cruiseplan/issues>`_
2. **Create new issue**: Include Python version, OS, and complete error message
3. **Discussion forum**: `GitHub Discussions <https://github.com/ocean-uhh/cruiseplan/discussions>`_ for usage questions and community support

Include the output of:

.. code-block:: bash

   python --version
   pip show cruiseplan
   cruiseplan --version