.. _output-latex:

============
LaTeX Output
============

LaTeX format generates professional tables specifically designed for cruise proposals and funding applications. The output follows academic standards and integrates seamlessly with proposal documents.

.. note::
   LaTeX output is only available from the **schedule command** (``cruiseplan schedule --format latex``). For configuration-based visualization, use :doc:`png` output via the map command.

Purpose and Use Cases
======================

**Primary Uses**:
  - DFG (German Research Foundation) cruise proposals
  - NSF (National Science Foundation) funding applications
  - Academic cruise planning documents
  - Professional cruise operation reports

**Target Audiences**:
  - Principal Investigators writing proposals
  - Funding agency reviewers
  - Academic institutions and review panels
  - Ship scheduling coordinators

LaTeX Table Structure
=====================

Generated LaTeX files contain multiple specialized tables:

**1. Working Areas and Profiles Table**
  - Geographic regions and operational zones
  - Station counts and profile types by area
  - Depth ranges and operational requirements
  - Scientific objectives for each working area

**2. Work Days at Sea Table**
  - Operational days broken down by activity type
  - Transit days between working areas
  - Weather contingency and buffer time allocation
  - Total sea time calculations

**3. Station List Table**
  - Complete station catalog with coordinates
  - Operation types and scientific parameters
  - Estimated durations and equipment requirements
  - Sequential numbering and geographic organization

**4. Equipment and Resource Summary**
  - Scientific equipment deployment schedule
  - Personnel requirements by operation type
  - Vessel resource utilization
  - Technical specifications and constraints

DFG-Style Proposal Format
=========================

Working Areas and Profiles
---------------------------

The LaTeX output includes a comprehensive working areas table following DFG proposal standards:

.. code-block:: latex

   \begin{table}[h]
   \centering
   \caption{Working areas, stations and profiles}
   \label{tab:working_areas}
   \begin{tabular}{p{3cm}p{2cm}p{2cm}p{3cm}p{4cm}}
   \hline
   \textbf{Working Area} & \textbf{Stations} & \textbf{Profiles} & \textbf{Depth Range} & \textbf{Scientific Objectives} \\
   \hline
   North Atlantic Gyre & 15 & CTD: 15 & 2000-4000m & Deep water mass analysis \\
   OSNAP Array & 8 & CTD: 6, Mooring: 2 & 1500-3500m & Overturning circulation \\
   Irminger Sea & 12 & CTD: 10, LADCP: 12 & 1000-3000m & Convection processes \\
   \hline
   \textbf{Total} & \textbf{35} & \textbf{CTD: 31, Mooring: 2} & & \\
   \hline
   \end{tabular}
   \end{table}

Work Days at Sea Calculation
-----------------------------

Standard DFG format for sea time breakdown:

.. code-block:: latex

   \begin{table}[h]
   \centering
   \caption{Work days at sea}
   \label{tab:sea_days}
   \begin{tabular}{lcc}
   \hline
   \textbf{Activity} & \textbf{Days} & \textbf{Remarks} \\
   \hline
   Transit to working area & 2.5 & Reykjavik to first station \\
   CTD stations and profiles & 8.2 & Including setup and recovery \\
   Mooring operations & 1.8 & Deployment and recovery \\
   Scientific transits & 2.1 & Between working areas \\
   Weather contingency & 1.4 & 10\% buffer time \\
   Transit to port & 2.0 & Last station to St. Johns \\
   \hline
   \textbf{Total sea days} & \textbf{18.0} & \\
   \hline
   \end{tabular}
   \end{table}

Professional Formatting
========================

Academic Standards Compliance
------------------------------

**Typography**:
  - Standard LaTeX fonts (Computer Modern)
  - Proper mathematical typesetting
  - Consistent spacing and alignment
  - Professional table formatting

**Table Design**:
  - Clear column headers and separators
  - Logical grouping and subtotals
  - Proper use of horizontal rules
  - Consistent number formatting and units

**Document Integration**:
  - Standard LaTeX packages and dependencies
  - Compatible with common document classes
  - Proper figure and table referencing
  - Cross-reference support

Table Customization
--------------------

**Column Specifications**:

.. list-table:: Standard Column Types
   :widths: 20 30 50
   :header-rows: 1

   * - **Column Type**
     - **LaTeX Spec**
     - **Usage**
   * - Station Names
     - ``p{2.5cm}``
     - Fixed-width for consistent alignment
   * - Coordinates
     - ``c``
     - Centered numeric values
   * - Durations
     - ``r``
     - Right-aligned for easy summation
   * - Descriptions
     - ``p{4cm}``
     - Text wrapping for detailed information

**Formatting Options**:
  - Bold headers with ``\textbf{}``
  - Italics for scientific names with ``\textit{}``
  - Horizontal rules with ``\hline``
  - Multi-column headers with ``\multicolumn{}``

Detailed Table Examples
=======================

Station List Format
--------------------

.. code-block:: latex

   \begin{longtable}{lccccl}
   \caption{Station list with coordinates and operations} \\
   \hline
   \textbf{Station} & \textbf{Latitude} & \textbf{Longitude} & \textbf{Depth} & \textbf{Duration} & \textbf{Operation} \\
   \textbf{Name} & \textbf{(°N)} & \textbf{(°W)} & \textbf{(m)} & \textbf{(hrs)} & \textbf{Type} \\
   \hline
   \endfirsthead
   
   \multicolumn{6}{c}{\textit{...continued from previous page}} \\
   \hline
   \textbf{Station} & \textbf{Latitude} & \textbf{Longitude} & \textbf{Depth} & \textbf{Duration} & \textbf{Operation} \\
   \textbf{Name} & \textbf{(°N)} & \textbf{(°W)} & \textbf{(m)} & \textbf{(hrs)} & \textbf{Type} \\
   \hline
   \endhead
   
   CTD\_001 & 63.333 & 28.167 & 2847 & 2.8 & CTD Profile \\
   CTD\_002 & 62.500 & 29.833 & 3124 & 3.1 & CTD Profile \\
   MOOR\_A & 61.750 & 31.250 & 2956 & 4.0 & Mooring Deploy \\
   \hline
   \end{longtable}

Resource Utilization Table
---------------------------

.. code-block:: latex

   \begin{table}[h]
   \centering
   \caption{Equipment and personnel requirements}
   \label{tab:resources}
   \begin{tabular}{lccc}
   \hline
   \textbf{Resource Type} & \textbf{Quantity} & \textbf{Duration} & \textbf{Utilization} \\
   \hline
   CTD/Rosette System & 1 & 31 operations & 85\% \\
   Deep-sea Winch & 1 & 156 hours & 92\% \\
   Scientific Personnel & 8 & 18 days & 100\% \\
   Ship Operations Crew & 12 & 18 days & 100\% \\
   Laboratory Space & 2 labs & 18 days & 75\% \\
   \hline
   \end{tabular}
   \end{table}

Compilation and Integration
===========================

LaTeX Dependencies
------------------

**Required Packages**:

.. code-block:: latex

   \usepackage{booktabs}      % Professional table formatting
   \usepackage{longtable}     % Multi-page tables
   \usepackage{array}         % Extended column types
   \usepackage{multirow}      % Multi-row cells
   \usepackage{siunitx}       % Scientific notation and units
   \usepackage{geometry}      % Page layout control

**Document Class Compatibility**:
  - ``article`` - Standard academic papers
  - ``report`` - Extended cruise planning documents
  - ``book`` - Multi-expedition planning volumes
  - ``scrartcl`` - KOMA-Script for European proposals

Integration with Proposal Documents
------------------------------------

**Standalone Compilation**:

.. code-block:: bash

   # Compile LaTeX tables independently
   pdflatex cruise_schedule.tex
   
   # With bibliography and cross-references
   pdflatex cruise_schedule.tex
   bibtex cruise_schedule
   pdflatex cruise_schedule.tex
   pdflatex cruise_schedule.tex

**Inclusion in Main Documents**:

.. code-block:: latex

   % In main proposal document
   \input{cruise_schedule.tex}
   
   % Or with path specification
   \input{tables/cruise_schedule.tex}
   
   % For specific tables only
   \input{working_areas_table.tex}
   \input{sea_days_table.tex}

Customization and Styling
=========================

Table Appearance Modification
------------------------------

**Color Schemes**:

.. code-block:: latex

   \usepackage{xcolor}
   \definecolor{headercolor}{RGB}{220,220,220}
   
   % Colored headers
   \rowcolor{headercolor}
   \textbf{Station} & \textbf{Latitude} & \textbf{Longitude} \\

**Custom Formatting**:

.. code-block:: latex

   % Scientific notation for coordinates
   \usepackage{siunitx}
   \sisetup{round-mode=places,round-precision=3}
   
   % Consistent decimal alignment
   \num{63.333} & \num{-28.167} & \num{2847}

Content Organization
--------------------

**Multi-Section Documents**:
  - Separate files for different table types
  - Consistent numbering and referencing
  - Modular structure for easy updates
  - Version control friendly format

**Cross-Reference Integration**:

.. code-block:: latex

   % Reference tables from text
   The working areas (Table~\ref{tab:working_areas}) show...
   
   % Total calculations
   As shown in Table~\ref{tab:sea_days}, the total cruise duration 
   is \ref{total_days} days at sea.

Best Practices
==============

Proposal Writing Guidelines
---------------------------

**DFG Proposal Standards**:
  - Include all required table categories
  - Follow standard German academic formatting
  - Provide detailed cost justifications
  - Include weather contingency calculations

**International Proposal Compatibility**:
  - Adapt table headers for different funding agencies
  - Include metric and imperial unit conversions
  - Provide equipment specifications and constraints
  - Document safety and environmental considerations

**Review and Approval Process**:
  - Generate drafts for internal review
  - Incorporate feedback from scientific collaborators
  - Validate calculations and resource estimates
  - Archive final versions for submission

Quality Assurance
-----------------

**Compilation Testing**:
  - Test with multiple LaTeX distributions
  - Verify table formatting across different page sizes
  - Check cross-reference integrity
  - Validate mathematical calculations

**Content Verification**:
  - Cross-check station coordinates and depths
  - Verify duration calculations and totals
  - Confirm equipment requirements and availability
  - Review scientific objectives and methodologies

The LaTeX output format ensures that CruisePlan generates publication-ready tables that meet the professional standards required for academic cruise proposals and funding applications.