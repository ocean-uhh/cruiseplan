===================
Forecasts at sea
===================

At sea the plan changes every day. ``cruiseplan forecast`` re-times the
schedule from where the ship is now, without editing the YAML. You need the
schedule NetCDF file written by ``cruiseplan schedule`` and the row you are
at, from ``cruiseplan list``:

.. code-block:: bash

   cruiseplan list MSM142_schedule.nc
   cruiseplan forecast MSM142_schedule.nc --start-index 18 \
       --start-time 2026-08-30T14:00-03:00 --format tex

``--start-index`` is the row in ``cruiseplan list``; ``--start-time`` is when
that row starts. See :doc:`../reference/cli-commands` for every option.

Ship time and UTC
=================

cruiseplan works in UTC. The printed plan (``--format tex``) can be in ship
time, so you can see what falls at breakfast, lunch and dinner. Give the start
time with the ship's offset from UTC, as the ship clock shows it:

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - ``--start-time``
     - TeX table rows
     - Time column
   * - ``2026-08-30T14:00-03:00``
     - ship time (UTC−3)
     - ``LT (UTC-03:00)``
   * - ``2026-08-30T14:00+13:00``
     - ship time (UTC+13)
     - ``LT (UTC+13:00)``
   * - ``2026-08-30T17:00`` or ``2026-08-30T17:00Z``
     - UTC
     - ``UTC``

The first and last rows are the same moment:
14:00 ship time at UTC−3 is 17:00 UTC.

Writing the offset
------------------

- Put the offset straight after the time, with no space: ``14:00-03:00``.
- **West of Greenwich the offset is negative** (Labrador Sea ``-03:00``,
  Newfoundland ``-02:30``); east of it, positive (Ross Sea on New Zealand
  time ``+13:00``).
- ``-03:00``, ``-0300`` and ``-03`` are the same. Half-hour offsets need the
  minutes: ``-02:30``.
- To check: ship time minus the offset is UTC. 14:00 at ``-03:00`` is
  14:00 + 3 h = 17:00 UTC.
- ``Z`` or ``+00:00`` means UTC; the table is then labelled ``UTC``.
- A time without an offset is taken as UTC.

When the ship's clock changes
-----------------------------

Ship time changes during a cruise when the captain sets the clocks. The
offset you give applies to the whole printed table, so after a clock change
print the plan again with the new offset. A table that spans a clock change
shows every row in the offset you gave.

What is in ship time
--------------------

Only the TeX table. The text output, waypoints, KML and PNG stay in UTC, as
does the NetCDF schedule. The text output's header gives the start time in
UTC.
