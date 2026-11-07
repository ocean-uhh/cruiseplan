"""
Independent hand calculation of cruise schedules for expected-value tests.

Nothing here imports from ``cruiseplan``: positions are read from the YAML
files with ``yaml.safe_load`` and every number follows the written rules:

- distance: haversine on a sphere of radius 6371 km, nm = km / 1.852
- transit minutes: nm / knots * 60
- CTD cast minutes: depth / (descent * 60) + depth / (ascent * 60) + turnaround
- a leg starts at the previous leg's end + the leg's ``delay_start``
- an operation's ``delay_start`` (either sign) is added to the actual minutes
  of the operation before it in the same leg (the nearest earlier row that
  is not a transit or a buffer; the departure port when there is none), never
  below zero; within a leg each row starts where the one before ends, so the
  transit between them keeps its length and only moves (``hand_actual``)
- a leg's ``buffer_time`` is a stationary block at the last operation's exit
  position, after the last operation and before the transit to the arrival port
- an area is entered at its first corner and left at its last corner; a line
  is entered at its first route point and left at its last
- a transit of zero length is not scheduled
- an operation's ``transit_minutes`` replaces the minutes of the transit
  into it (distance unchanged; planned minutes kept)

Forecast (at-sea re-anchoring), ``hand_forecast``:

- without a current position the anchor is the row at the given index and
  it starts at the start time; on a transit row the ship starts that
  transit at the start time
- with a current position the position wins: a transit row anchors on the
  row after it, and a transit from the position to the anchored row's entry
  (at the leg speed) comes first
- every later row keeps its offset from the anchored row in the schedule
"""

import math
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

R_EARTH_KM = 6371.0
KM_PER_NM = 1.852
FILL_MIN = 999 * 60.0  # 999 h fill duration
FILL_DEPTH = -9999.0

# Coordinates of the registry ports used by the fixtures (cruiseplan port registry)
REGISTRY_PORTS = {
    "port_halifax": ("Halifax", 44.6488, -63.5752),
    "port_cadiz": ("Cadiz", 36.5298, -6.2923),
    "port_st_johns": ("St. John's", 47.5615, -52.7126),
    "port_bremerhaven": ("Bremerhaven", 53.5395, 8.5809),
    "port_reykjavik": ("Reykjavik", 64.1466, -21.9426),
}


# Pre-0.6.0 key names, read from configs that still use them
OLD_KEYS = {
    "duration_minutes": "duration",
    "delay_start_minutes": "delay_start",
    "buffer_time_minutes": "buffer_time",
    "turnaround_time_minutes": "turnaround_time",
    "water_depth_m": "water_depth",
    "operation_depth_m": "operation_depth",
    "vessel_speed_kt": "vessel_speed",
    "default_vessel_speed_kt": "default_vessel_speed",
    "ctd_descent_rate_m_s": "ctd_descent_rate",
    "ctd_ascent_rate_m_s": "ctd_ascent_rate",
}


def key(d: dict, name: str, default: object = None) -> object:
    """Value of the key *name* in a YAML mapping, or of its pre-0.6.0 name."""
    if name in d:
        return d[name]
    return d.get(OLD_KEYS.get(name, name), default)


def gc_nm(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in nm between (lat, lon) points."""
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = math.radians(b[0] - a[0])
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH_KM * math.asin(math.sqrt(h)) / KM_PER_NM


def transit_min(nm: float, knots: float) -> float:
    """Transit time in minutes."""
    return nm / knots * 60.0


def ctd_min(
    depth: float, descent: float = 1.0, ascent: float = 1.0, turnaround: float = 30.0
) -> float:
    """CTD cast time in minutes (rates in m/s)."""
    return depth / (descent * 60.0) + depth / (ascent * 60.0) + turnaround


@dataclass
class Stop:
    """One operation (or port, or buffer) in a hand-built leg."""

    name: str
    entry: tuple[float, float]
    exit: tuple[float, float]
    minutes: float
    delay: float = 0.0
    kind: str = "op"  # "op", "port", "buffer", "line"
    depth: float | None = None
    is_fill: bool = False
    speed: float | None = None  # line operations: own speed
    transit: float | None = None  # transit_minutes: actual minutes of the transit in


@dataclass
class Row:
    """One hand-computed schedule row."""

    name: str
    kind: str
    leg: str
    start: datetime
    end: datetime
    minutes: float
    nm: float = 0.0
    depth: float | None = None
    is_fill: bool = False
    entry: tuple[float, float] | None = None
    delay: float = 0.0  # the row's own delay_start (operations and ports)
    planned: float | None = None  # planned minutes, when the actual differs


@dataclass
class HandLeg:
    """A leg: ordered stops, speed, optional buffer and leg delay."""

    name: str
    stops: list[Stop]
    speed: float = 10.0
    buffer: float | None = None
    delay: float = 0.0
    rows: list[Row] = field(default_factory=list)


def run_legs(start: datetime, legs: list[HandLeg]) -> list[Row]:
    """Chain legs: transit between consecutive stops, ops, buffer, arrival."""
    t = start
    out: list[Row] = []
    for leg in legs:
        t += timedelta(minutes=leg.delay)
        stops = list(leg.stops)
        if leg.buffer:
            last = stops[-2]
            stops.insert(
                len(stops) - 1,
                Stop(
                    f"Contingency ({leg.buffer:.0f} min)",
                    last.exit,
                    last.exit,
                    leg.buffer,
                    kind="buffer",
                ),
            )
        prev = None
        for stop in stops:
            if prev is not None and stop.kind != "buffer":
                src = prev.exit
                nm = gc_nm(src, stop.entry)
                minutes = transit_min(nm, leg.speed)
                if minutes > 0:
                    planned = None
                    if stop.transit is not None:
                        planned, minutes = minutes, stop.transit
                    out.append(
                        Row(
                            f"Transit to {stop.name}",
                            "transit",
                            leg.name,
                            t,
                            t + timedelta(minutes=minutes),
                            minutes,
                            nm,
                            entry=src,
                            planned=planned,
                        )
                    )
                    t += timedelta(minutes=minutes)
            begin = t + timedelta(minutes=stop.delay)
            end = begin + timedelta(minutes=stop.minutes)
            nm = 0.0
            if stop.kind == "line":
                nm = gc_nm(stop.entry, stop.exit)
            out.append(
                Row(
                    stop.name,
                    stop.kind,
                    leg.name,
                    begin,
                    end,
                    stop.minutes,
                    nm,
                    stop.depth,
                    stop.is_fill,
                    stop.entry,
                    stop.delay,
                )
            )
            t = end
            if stop.kind != "buffer":
                prev = stop
    return out


# -----------------------------------------------------------------------------
# Building stops from a YAML dict (read with yaml.safe_load)
# -----------------------------------------------------------------------------


def port_stop(cfg: dict, ref: str | dict) -> Stop:
    """Resolve a port reference: inline dict, YAML ports catalog, or registry."""
    if isinstance(ref, dict):
        return Stop(
            ref.get("display_name", ref["name"]).split(",")[0].strip(),
            (ref["latitude"], ref["longitude"]),
            (ref["latitude"], ref["longitude"]),
            float(key(ref, "duration_minutes") or 0.0),
            float(key(ref, "delay_start_minutes") or 0.0),
            kind="port",
        )
    for p in cfg.get("ports") or []:
        if p["name"] == ref:
            return port_stop(cfg, p)
    label, lat, lon = REGISTRY_PORTS[ref]
    return Stop(label, (lat, lon), (lat, lon), 0.0, kind="port")


def activity_stop(
    cfg: dict,
    name: str,
    leg_speed: float,
    turnaround: float | None = None,
) -> Stop:
    """Resolve an activity name to a Stop using the documented duration rules."""
    descent = float(key(cfg, "ctd_descent_rate_m_s", 1.0))
    ascent = float(key(cfg, "ctd_ascent_rate_m_s", 1.0))
    if turnaround is None:
        turnaround = float(key(cfg, "turnaround_time_minutes", 30.0))
    for p in cfg.get("points") or []:
        if p["name"] != name:
            continue
        pos = (p["latitude"], p["longitude"])
        depth = key(p, "operation_depth_m", key(p, "water_depth_m"))
        if depth == FILL_DEPTH:
            depth = key(p, "water_depth_m")
        op_type = str(p.get("operation_type", "")).lower()
        delay = float(key(p, "delay_start_minutes") or 0.0)
        if key(p, "duration_minutes"):
            minutes = float(key(p, "duration_minutes"))
            return Stop(
                name, pos, pos, minutes, delay, depth=depth, is_fill=minutes == FILL_MIN
            )
        if op_type == "ctd" and depth not in (None, 0, FILL_DEPTH) and depth > 0:
            return Stop(
                name,
                pos,
                pos,
                ctd_min(depth, descent, ascent, turnaround),
                delay,
                depth=depth,
            )
        return Stop(name, pos, pos, FILL_MIN, delay, depth=depth, is_fill=True)
    for area in cfg.get("areas") or []:
        if area["name"] == name:
            first, last = area["corners"][0], area["corners"][-1]
            return Stop(
                name,
                (first["latitude"], first["longitude"]),
                (last["latitude"], last["longitude"]),
                float(key(area, "duration_minutes")),
            )
    for line in cfg.get("lines") or []:
        if line["name"] == name:
            route = [(r["latitude"], r["longitude"]) for r in line["route"]]
            nm = sum(gc_nm(route[i], route[i + 1]) for i in range(len(route) - 1))
            speed = float(key(line, "vessel_speed_kt") or leg_speed)
            return Stop(
                name,
                route[0],
                route[-1],
                transit_min(nm, speed),
                kind="line",
                speed=speed,
            )
    raise KeyError(name)


def transit_override(cfg: dict, name: str) -> float | None:
    """``transit_minutes`` of the point, line, area or port called *name*."""
    for catalog in ("points", "lines", "areas", "ports"):
        for item in cfg.get(catalog) or []:
            if item.get("name") == name:
                return key(item, "transit_minutes")
    return None


def leg_activities(leg: dict) -> list[str]:
    """Activities of a leg in order: cluster lists concatenated, else activities."""
    if leg.get("clusters"):
        return [a for c in leg["clusters"] for a in c["activities"]]
    return list(leg.get("activities") or [])


def hand_legs(cfg: dict, leg_speed_for_lines: bool = True) -> list[HandLeg]:
    """Build HandLeg objects for every leg in a YAML config."""
    default_speed = float(key(cfg, "default_vessel_speed_kt", 10.0))
    legs = []
    for leg in cfg["legs"]:
        speed = float(key(leg, "vessel_speed_kt") or default_speed)
        line_speed = speed if leg_speed_for_lines else default_speed
        turnaround = key(leg, "turnaround_time_minutes")
        stops = [port_stop(cfg, leg["departure_port"])]
        stops += [
            activity_stop(cfg, a, line_speed, turnaround) for a in leg_activities(leg)
        ]
        stops.append(port_stop(cfg, leg["arrival_port"]))
        for stop, name in zip(
            stops[1:],
            [*leg_activities(leg), leg["arrival_port"]],
            strict=True,
        ):
            if isinstance(name, str):
                stop.transit = transit_override(cfg, name)
        legs.append(
            HandLeg(
                leg["name"],
                stops,
                speed,
                key(leg, "buffer_time_minutes"),
                float(key(leg, "delay_start_minutes") or 0.0),
            )
        )
    return legs


def cruise_start(cfg: dict) -> datetime:
    """Cruise start: start_date (+ start_time, default 08:00), else 1970-01-01."""
    date = str(cfg.get("start_date", "1970-01-01T00:00:00"))
    if "T" in date:
        return datetime.fromisoformat(date.replace("Z", "").replace("+00:00", ""))
    return datetime.strptime(
        f"{date} {cfg.get('start_time', '08:00')}", "%Y-%m-%d %H:%M"
    )


def hand_schedule(cfg: dict, **kwargs: bool) -> list[Row]:
    """Full hand schedule for a YAML config dict."""
    return hand_actual(run_legs(cruise_start(cfg), hand_legs(cfg, **kwargs)))


def hand_actual(rows: list[Row]) -> list[Row]:
    """Move each operation's delay into the operation before it (same leg)."""
    minutes = [r.minutes for r in rows]
    prev_op = None
    for i, row in enumerate(rows):
        if i == 0 or row.leg != rows[i - 1].leg:
            prev_op = None
        if row.kind in ("transit", "buffer"):
            continue
        if row.delay and prev_op is not None:
            minutes[prev_op] = max(0.0, minutes[prev_op] + row.delay)
        prev_op = i
    out: list[Row] = []
    for i, row in enumerate(rows):
        if i == 0:
            start = row.start
        elif row.leg != rows[i - 1].leg:
            gap = row.start - rows[i - 1].end
            start = out[-1].end + max(gap, timedelta(0))
        else:
            start = out[-1].end
        planned = row.planned
        if planned is None and minutes[i] != row.minutes:
            planned = row.minutes
        out.append(
            replace(
                row,
                start=start,
                end=start + timedelta(minutes=minutes[i]),
                minutes=minutes[i],
                planned=planned,
            )
        )
    return out


# -----------------------------------------------------------------------------
# Forecast
# -----------------------------------------------------------------------------


@dataclass
class ForecastRow:
    """One hand-computed forecast row; index -1 is the current-position transit."""

    index: int
    start: datetime
    minutes: float


def hand_anchor(
    rows: list[Row], index: int, position: tuple[float, float] | None = None
) -> int:
    """Anchored row: the index itself; with a position, the row after a transit."""
    if position is None:
        return index
    while rows[index].kind == "transit":
        index += 1
    return index


def hand_forecast(
    rows: list[Row],
    index: int,
    start: datetime,
    position: tuple[float, float] | None = None,
    knots: float = 10.0,
) -> list[ForecastRow]:
    """Re-anchored forecast of a hand schedule (no forecast window)."""
    k = hand_anchor(rows, index, position)
    out = []
    t_k = start
    if position is not None:
        minutes = transit_min(gc_nm(position, rows[k].entry), knots)
        out.append(ForecastRow(-1, start, minutes))
        t_k = start + timedelta(minutes=minutes)
    for j in range(k, len(rows)):
        out.append(
            ForecastRow(j, t_k + (rows[j].start - rows[k].start), rows[j].minutes)
        )
    return out
