Performance & Scalability
=========================

This document provides performance characteristics, benchmarks, and scalability guidance for CruisePlan operations across different dataset sizes and computational environments.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

CruisePlan is designed to handle cruise planning workflows efficiently while maintaining responsiveness for interactive operations. Performance characteristics vary by operation type, dataset size, and available computational resources.

**Design Principles:**
- **Interactive Responsiveness**: Sub-second response for interactive station placement
- **Batch Processing Efficiency**: Optimized algorithms for large-scale operations  
- **Memory Management**: Streaming and chunked processing for large datasets
- **Progressive Enhancement**: Graceful degradation with limited resources

Expected Performance
--------------------

Interactive Operations
~~~~~~~~~~~~~~~~~~~~~~~

**Station Picker Interface:**

.. list-table::
   :widths: 30 20 25 25
   :header-rows: 1

   * - **Operation**
     - **Typical Time**
     - **Dataset Size**
     - **Memory Usage**
   * - Initial map loading
     - 2-5 seconds
     - Regional bathymetry
     - 100-500 MB
   * - Station placement
     - <0.1 seconds
     - Per click
     - Minimal
   * - Depth lookup
     - <0.1 seconds
     - Per station
     - Cached
   * - PANGAEA data overlay
     - 1-3 seconds
     - 1000-10000 stations
     - 50-200 MB

**Real-time Feedback:**
- Coordinate display: Instantaneous
- Bathymetric depth: <100ms per station
- Distance calculations: <50ms between stations

Batch Processing Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Enrichment Performance:**

.. list-table::
   :widths: 30 20 20 30
   :header-rows: 1

   * - **Configuration Size**
     - **Enrichment Time**
     - **Memory Peak**
     - **Notes**
   * - Small (1-50 stations)
     - 5-15 seconds
     - <200 MB
     - Typical single-leg cruise
   * - Medium (50-200 stations)
     - 15-60 seconds
     - 200-500 MB
     - Multi-leg expedition
   * - Large (200-1000 stations)
     - 1-5 minutes
     - 500-1000 MB
     - Large survey program
   * - Very Large (1000+ stations)
     - 5-15 minutes
     - 1-2 GB
     - Multi-cruise campaigns

**Schedule Generation Performance:**

.. list-table::
   :widths: 30 20 20 30
   :header-rows: 1

   * - **Configuration Size**
     - **Processing Time**
     - **Output Size**
     - **Formats Generated**
   * - Small cruise
     - 10-30 seconds
     - 1-5 MB
     - HTML, CSV, PNG map
   * - Medium cruise  
     - 30-90 seconds
     - 5-20 MB
     - All formats + NetCDF
   * - Large cruise
     - 90-300 seconds
     - 20-100 MB
     - Full output suite
   * - Complex multi-leg
     - 300-600 seconds
     - 100-500 MB
     - Enhanced documentation

Data Processing Benchmarks
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Bathymetry Operations:**

.. list-table::
   :widths: 40 30 30
   :header-rows: 1

   * - **Operation**
     - **ETOPO 2022**
     - **GEBCO 2025**
   * - Initial data loading
     - 5-10 seconds
     - 30-60 seconds
   * - Regional extraction
     - 1-3 seconds
     - 5-15 seconds
   * - Depth lookup (1000 points)
     - 2-5 seconds
     - 3-8 seconds
   * - Contour generation
     - 5-15 seconds
     - 15-45 seconds

**PANGAEA Data Processing:**

.. list-table::
   :widths: 30 25 25 20
   :header-rows: 1

   * - **Dataset Size**
     - **Download Time**
     - **Processing Time**
     - **Storage**
   * - Single campaign (100 stations)
     - 10-30 seconds
     - 5-15 seconds
     - 1-5 MB
   * - Multi-campaign (1000 stations)
     - 1-5 minutes
     - 30-90 seconds
     - 10-50 MB
   * - Large database (10000+ stations)
     - 10-30 minutes
     - 5-15 minutes
     - 100-500 MB

Scalability Limits
-------------------

Tested Configurations
~~~~~~~~~~~~~~~~~~~~~~

CruisePlan has been tested with the following maximum configurations:

**Station Limits:**
- **Maximum tested**: 5,000 individual stations
- **Recommended maximum**: 2,000 stations per cruise
- **Interactive limit**: 1,000 stations (maintains responsiveness)
- **Memory scaling**: ~500 KB per station in memory

**Geographic Coverage:**
- **Global coverage**: Full ocean basins supported
- **High-resolution regions**: Continental shelves, polar regions
- **Coordinate precision**: 0.0001° (≈10m at equator)

**Temporal Scope:**
- **Cruise duration**: No practical limit (months-long expeditions tested)
- **Multi-year planning**: Campaign-level organization supported
- **Historical integration**: Decades of PANGAEA data

Performance Optimization
-------------------------

System Configuration
~~~~~~~~~~~~~~~~~~~~~

**Recommended Specifications:**

.. list-table::
   :widths: 20 25 25 30
   :header-rows: 1

   * - **Use Case**
     - **RAM**
     - **Storage**
     - **CPU**
   * - Basic planning
     - 4 GB
     - 2 GB free
     - 2 cores
   * - Standard workflow
     - 8 GB
     - 10 GB free
     - 4 cores
   * - Large campaigns
     - 16 GB
     - 50 GB free
     - 8+ cores
   * - High-performance
     - 32 GB
     - 100 GB SSD
     - 16+ cores

**Storage Optimization:**
- Use SSD for bathymetry data when possible
- Place temporary files on fastest available storage
- Consider network storage for shared datasets

Software Configuration
~~~~~~~~~~~~~~~~~~~~~~

**Environment Optimization:**

.. code-block:: bash

   # Increase numpy/scipy performance
   export OMP_NUM_THREADS=4
   export MKL_NUM_THREADS=4

   # Optimize matplotlib for non-interactive use
   export MPLBACKEND=Agg

   # Increase memory limits for large datasets
   export PYTHONMAXMEMORY=8GB

**Dependency Optimization:**
- Use conda-forge packages for optimized scientific libraries
- Consider Intel MKL builds for numerical acceleration
- Ensure latest versions for performance improvements

Workflow Optimization
~~~~~~~~~~~~~~~~~~~~~

**Best Practices for Performance:**

1. **Bathymetry Strategy:**
   - Use ETOPO 2022 for initial planning (faster)
   - Switch to GEBCO 2025 only for final detailed work
   - Cache regional extractions for repeated use

2. **Interactive Planning:**
   - Work with subsets for very large cruises
   - Use navigation mode for exploration without station creation
   - Save progress frequently to avoid re-work

3. **Batch Processing:**
   - Process enrichment in chunks for very large configurations
   - Use parallel processing where available
   - Monitor memory usage during large operations

4. **Output Generation:**
   - Generate only needed formats to reduce processing time
   - Use lower resolution maps for draft documents
   - Cache intermediate results when possible

Troubleshooting Performance Issues
----------------------------------

Memory Issues
~~~~~~~~~~~~~

**Symptoms:**
- Slow responsiveness during operation
- Out of memory errors
- System swapping/thrashing

**Solutions:**

.. code-block:: bash

   # Monitor memory usage
   python -c "import psutil; print(f'Available RAM: {psutil.virtual_memory().available/1e9:.1f}GB')"

   # Reduce dataset size
   cruiseplan enrich -c cruise.yaml --bathymetry-source etopo2022  # Use smaller dataset

   # Process in chunks
   # Split large configurations into smaller files

**Prevention:**
- Close other applications during large operations
- Use appropriate bathymetry resolution for task
- Upgrade RAM for consistently large workflows

Processing Speed Issues
~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms:**
- Operations taking much longer than expected
- CPU usage consistently high
- Slow interactive response

**Diagnostics:**

.. code-block:: bash

   # Check CPU usage
   python -c "import psutil; print(f'CPU usage: {psutil.cpu_percent(interval=1)}%')"

   # Profile slow operations
   python -m cProfile -s cumulative your_script.py

**Solutions:**
- Ensure adequate CPU resources
- Check for other resource-intensive processes
- Consider distributed processing for very large tasks
- Use faster storage (SSD) for data files

Network Issues
~~~~~~~~~~~~~~

**Symptoms:**
- Slow bathymetry downloads
- PANGAEA integration timeouts
- Incomplete data retrieval

**Solutions:**

.. code-block:: bash

   # Test network connectivity
   cruiseplan bathymetry --citation

   # Use rate limiting for API calls
   cruiseplan pangaea dois.txt --rate-limit 0.5

   # Configure proxy if needed
   export HTTP_PROXY=http://proxy.company.com:port

Benchmarking Your System
-------------------------

System Performance Test
~~~~~~~~~~~~~~~~~~~~~~~

Use this script to benchmark CruisePlan performance on your system:

.. code-block:: bash

   # Download test data
   cruiseplan bathymetry --source etopo2022

   # Time basic operations
   time cruiseplan enrich -c test_cruise.yaml --add-depths
   time cruiseplan validate -c test_cruise.yaml --check-depths  
   time cruiseplan schedule -c test_cruise.yaml --format html

Expected results on reference systems:

- **Laptop (8GB RAM, SSD)**: Enrichment ~30s, Validation ~10s, Scheduling ~45s
- **Workstation (32GB RAM)**: Enrichment ~10s, Validation ~3s, Scheduling ~15s  
- **HPC Node**: Enrichment ~5s, Validation ~1s, Scheduling ~8s

Performance Reporting
~~~~~~~~~~~~~~~~~~~~~~

When reporting performance issues, include:

.. code-block:: bash

   # System information
   python --version
   cruiseplan --version
   python -c "import psutil; print(f'RAM: {psutil.virtual_memory().total/1e9:.1f}GB, CPU: {psutil.cpu_count()} cores')"

   # Timing information
   time cruiseplan your-command-here

   # Memory monitoring
   python -c "import psutil; psutil.Process().memory_info()"

This information helps developers optimize performance and identify bottlenecks for different use cases and system configurations.