.. _migrating-0-6-0:

=========================
Upgrading from 0.5 to 0.6
=========================

0.6.0 renames the numeric YAML keys so each one names its unit, writes the
NetCDF schedule in CF units, and returns timeline records instead of
dictionaries. The old names still work for one release: they warn and are
removed in 0.7.0. ``cruiseplan enrich`` writes the new keys, so enriching a
configuration once updates it.

YAML keys (removed in 0.7.0)
----------------------------

The same old key has the same new name wherever it appears (cruise, leg,
point, port, line, area). An old key logs a warning naming the new one, once
per key per file. A mapping with both the old and the new key and different
values is an error.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Old key
     - New key
   * - ``duration``
     - ``duration_minutes``
   * - ``delay_start``
     - ``delay_start_minutes``
   * - ``buffer_time``
     - ``buffer_time_minutes``
   * - ``turnaround_time``
     - ``turnaround_time_minutes``
   * - ``water_depth``
     - ``water_depth_m``
   * - ``operation_depth``
     - ``operation_depth_m``
   * - ``vessel_speed``
     - ``vessel_speed_kt``
   * - ``default_vessel_speed``
     - ``default_vessel_speed_kt``
   * - ``distance_between_stations``
     - ``distance_between_stations_km``
   * - ``default_distance_between_stations``
     - ``default_distance_between_stations_km``
   * - ``ctd_descent_rate``
     - ``ctd_descent_rate_m_s``
   * - ``ctd_ascent_rate``
     - ``ctd_ascent_rate_m_s``

Removed keys
------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key
     - What to do
   * - ``delay_end``
     - It was never read, so it never changed a schedule. It is ignored with a
       warning (rejected from 0.7.0): use ``delay_start_minutes`` on the next
       operation, ``buffer_time_minutes`` on the leg, or a longer
       ``duration_minutes``.

Keys no model knows (for example ``description`` on an area, or
``start_date`` on a leg) are reported, one warning per key per file, and are
rejected in the release after 0.6.0. An activity listed more than once in a
leg is scheduled each time, with a warning naming it and its clusters.

Timeline records (removed in 0.7.0)
-----------------------------------

``cruiseplan.schedule(...).timeline`` and ``generate_timeline`` return a
``Timeline``: a list of ``ActivityRecord`` objects, frozen, with a ``kind``
(``station``, ``mooring``, ``line``, ``area``, ``transit``, ``port``,
``buffer``). Read fields as attributes: ``record.label``,
``record.duration_minutes``. Reading a record like a dictionary still works and
warns; the keys that changed name:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Old dictionary key
     - Attribute
   * - ``time``
     - ``start_time``
   * - ``lat``
     - ``entry_lat``
   * - ``lon``
     - ``entry_lon``
   * - ``operation_type``
     - ``op_type``
   * - ``delay_start``
     - ``delay_start_minutes``
   * - ``water_depth``
     - ``water_depth_m``
   * - ``operation_depth``
     - ``operation_depth_m``

Each record has ``duration_minutes`` (actual: end minus start) and
``planned_duration_minutes`` (from the planning rules). An operation's
``delay_start_minutes`` (either sign) now changes the actual duration of the
operation before it in the same leg (the departure port when there is none);
the transit between them keeps its length and moves in time. Records no longer
overlap or leave gaps, and the forecast uses the same durations. Schedules
written before 0.6.0 are retimed this way when read.

Renamed API names (removed in 0.7.0)
------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Old
     - Use instead
   * - ``cruiseplan.CruiseSchedule``
     - ``cruiseplan.Timeline``
   * - ``cruiseplan.timeline.CruiseSchedule``
     - ``cruiseplan.timeline.Timeline``
   * - ``cruiseplan.timeline.scheduler.CruiseSchedule``
     - ``cruiseplan.timeline.Timeline``

NetCDF schedule
---------------

- ``duration`` is in minutes (was hours) and is the actual duration;
  ``planned_duration`` (minutes) is new.
- ``dist_nm`` is renamed ``distance`` (``units = "nautical_mile"``).
- ``time`` and ``end_time`` are CF-encoded UTC seconds since 1970-01-01.
- Every numeric variable has a UDUNITS-2 ``units`` attribute (``minute``,
  ``nautical_mile``, ``knot``, ``m``, degrees). Read the unit from the
  attribute.
- ``cruiseplan list`` and ``cruiseplan forecast`` still read schedules written
  by 0.5.0 (hours, ``dist_nm``) until 0.7.0.

Schedule results that change
----------------------------

- A leg's ``turnaround_time_minutes`` now applies to its CTD casts (it was
  read and ignored).
- The schedule total (CLI, HTML, ``ScheduleResult.summary["total_duration_hours"]``)
  is the elapsed time, including waiting from positive delays.
- CSV and KML times are rounded to the nearest minute (they were truncated).
  TeX plans and waypoints round to 10 minutes on the full time, halves up.
- Line records report the speed the line is run at (they reported the cruise
  default).
- ``cruiseplan forecast`` on a transit row starts that transit at
  ``--start-time`` (it used to start the operation after it); see the
  anchoring rule in :doc:`reference/cli-commands`.
