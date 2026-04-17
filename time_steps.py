"""
Raspberrarium — shared configuration, light cycle logic, and moon phases.

This module is the single source of truth for all constants, brightness
presets, color values, and calculation functions used by the main script
and the demo scripts.
"""

import os
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from astral import LocationInfo, moon
from astral.sun import sun
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Environment (.env)
# ---------------------------------------------------------------------------

load_dotenv()

TIMEZONE = os.environ.get("TIMEZONE", "Europe/Rome")
LATITUDE = float(os.environ.get("LATITUDE", 0.0))
LONGITUDE = float(os.environ.get("LONGITUDE", 0.0))


# ---------------------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------------------

LED_COUNT = 2


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

STEPS_PER_DAY = 96
MOON_WINDOW_HOURS = 3
REFRESH_SECONDS = 10


# ---------------------------------------------------------------------------
# Brightness presets (1 = dimmest, 3 = brightest)
# ---------------------------------------------------------------------------

BRIGHTNESS_LEVELS = {
    1: 0.70,
    2: 0.85,
    3: 1.00,
}


# ---------------------------------------------------------------------------
# Day-cycle colors and base brightness
# ---------------------------------------------------------------------------

DEEP_NIGHT   = (0,   0,   2)
PRE_DAWN     = (40,  10,  4)
SUNRISE      = (255, 90,  30)
MORNING      = (255, 130, 55)
DAY          = (255, 170, 90)
SUNSET       = (255, 70,  20)
NIGHT_RETURN = (0,   0,   3)

B_DEEP_NIGHT   = 0.04
B_PRE_DAWN     = 0.12
B_SUNRISE      = 0.35
B_MORNING      = 0.60
B_DAY          = 1.00
B_SUNSET       = 0.30
B_NIGHT_RETURN = 0.04


# ---------------------------------------------------------------------------
# Moon
# ---------------------------------------------------------------------------

MOON_COLOR = (30, 30, 45)

# (left_factor, right_factor, base_brightness, name)
_MOON_PHASES = (
    (1.5,  7.0,  0.03, 0.65, 0.08, "Waxing crescent"),
    (7.0,  10.5, 0.15, 0.85, 0.10, "First quarter"),
    (10.5, 14.0, 0.50, 1.00, 0.13, "Waxing gibbous"),
    (14.0, 15.5, 1.00, 1.00, 0.16, "Full moon"),
    (15.5, 21.0, 1.00, 0.50, 0.13, "Waning gibbous"),
    (21.0, 24.0, 0.85, 0.15, 0.10, "Last quarter"),
    (24.0, 26.5, 0.65, 0.03, 0.08, "Waning crescent"),
)


# ---------------------------------------------------------------------------
# Demo phase data (used by demo scripts, derived from constants above)
# ---------------------------------------------------------------------------

DAY_DEMO_PHASES = (
    ("Deep night",        DEEP_NIGHT,   B_DEEP_NIGHT,   2),
    ("Pre-dawn",          PRE_DAWN,     B_PRE_DAWN,     2),
    ("Sunrise",           SUNRISE,      B_SUNRISE,      2),
    ("Morning",           MORNING,      B_MORNING,      2),
    ("Day",               DAY,          B_DAY,          3),
    ("Sunset",            SUNSET,       B_SUNSET,       2),
    ("Night return",      NIGHT_RETURN, B_NIGHT_RETURN, 2),
    ("Full moon baseline", MOON_COLOR,  0.16,           3),
)

MOON_DEMO_PHASES = (
    ("New moon",         0.0,  0.0,  0.0),
    ("Waxing crescent",  0.03, 0.65, 0.08),
    ("First quarter",    0.15, 0.85, 0.10),
    ("Waxing gibbous",   0.50, 1.00, 0.13),
    ("Full moon",        1.00, 1.00, 0.16),
    ("Waning gibbous",   1.00, 0.50, 0.13),
    ("Last quarter",     0.85, 0.15, 0.10),
    ("Waning crescent",  0.65, 0.03, 0.08),
)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def clamp01(value):
    """Clamp a float to the 0.0–1.0 range."""
    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    return value


def lerp(a, b, t):
    """Linear interpolation from a to b by factor t."""
    return a + (b - a) * t


def blend_color(c1, c2, t):
    """Blend two RGB tuples by factor t (0.0 = c1, 1.0 = c2)."""
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )


def scale_color(color, factor):
    """Multiply each channel of an RGB tuple by factor (clamped 0–1)."""
    factor = clamp01(factor)
    return (int(color[0] * factor), int(color[1] * factor), int(color[2] * factor))


def apply_brightness(base_brightness, level):
    """Apply a project brightness level to a base brightness value."""
    multiplier = BRIGHTNESS_LEVELS.get(level, 1.0)
    return clamp01(base_brightness * multiplier)


# ---------------------------------------------------------------------------
# Moon logic
# ---------------------------------------------------------------------------

def get_moon_led_state(current_date):
    """
    Map Astral's moon phase value to two LEDs.

    LED 0 = left side, LED 1 = right side.
    Tuned for readability in a small jar, not astronomical precision.

    Returns (left_factor, right_factor, brightness, phase_value, name).
    """
    p = moon.phase(current_date)

    for low, high, left, right, brightness, name in _MOON_PHASES:
        if low <= p < high:
            return left, right, brightness, p, name

    return 0.0, 0.0, 0.0, p, "New moon"


# ---------------------------------------------------------------------------
# Sun / day-cycle logic
# ---------------------------------------------------------------------------

def get_today_sun_times(current_date=None, timezone=TIMEZONE,
                        latitude=LATITUDE, longitude=LONGITUDE):
    """Return Astral sun times dict for the given date and location."""
    tz = ZoneInfo(timezone)
    if current_date is None:
        current_date = date.today()

    city = LocationInfo(
        name="Raspberrarium",
        region="Local",
        timezone=timezone,
        latitude=latitude,
        longitude=longitude,
    )
    return sun(city.observer, date=current_date, tzinfo=tz)


def state_at_time(now, sun_times):
    """Return (rgb, brightness) for a specific moment given today's sun times."""
    dawn    = sun_times["dawn"]
    sunrise = sun_times["sunrise"]
    noon    = sun_times["noon"]
    sunset  = sun_times["sunset"]
    dusk    = sun_times["dusk"]

    morning_mid   = sunrise + (noon - sunrise) / 2
    afternoon_mid = noon + (sunset - noon) / 2

    if now < dawn:
        return DEEP_NIGHT, B_DEEP_NIGHT

    if now < sunrise:
        t = clamp01((now - dawn).total_seconds() / (sunrise - dawn).total_seconds())
        return blend_color(PRE_DAWN, SUNRISE, t), lerp(B_PRE_DAWN, B_SUNRISE, t)

    if now < morning_mid:
        t = clamp01((now - sunrise).total_seconds() / (morning_mid - sunrise).total_seconds())
        return blend_color(SUNRISE, MORNING, t), lerp(B_SUNRISE, B_MORNING, t)

    if now < noon:
        t = clamp01((now - morning_mid).total_seconds() / (noon - morning_mid).total_seconds())
        return blend_color(MORNING, DAY, t), lerp(B_MORNING, B_DAY, t)

    if now < afternoon_mid:
        return DAY, B_DAY

    if now < sunset:
        t = clamp01((now - afternoon_mid).total_seconds() / (sunset - afternoon_mid).total_seconds())
        return blend_color(DAY, SUNSET, t), lerp(B_DAY, B_SUNSET, t)

    if now < dusk:
        t = clamp01((now - sunset).total_seconds() / (dusk - sunset).total_seconds())
        return blend_color(SUNSET, NIGHT_RETURN, t), lerp(B_SUNSET, B_NIGHT_RETURN, t)

    return DEEP_NIGHT, B_DEEP_NIGHT


def build_daily_steps(current_date=None, timezone=TIMEZONE,
                      latitude=LATITUDE, longitude=LONGITUDE,
                      steps_per_day=STEPS_PER_DAY):
    """
    Pre-compute the full day as a tuple of (rgb, brightness) pairs.

    Returns (states, sun_times) where states is a tuple of length steps_per_day.
    Each entry is (rgb_tuple, brightness_float).
    """
    tz = ZoneInfo(timezone)
    if current_date is None:
        current_date = date.today()

    sun_times = get_today_sun_times(current_date, timezone, latitude, longitude)
    day_start = datetime.combine(current_date, datetime.min.time(), tz)
    step_minutes = 1440 // steps_per_day

    states = tuple(
        state_at_time(day_start + timedelta(minutes=i * step_minutes), sun_times)
        for i in range(steps_per_day)
    )

    return states, sun_times


def get_current_step_index(now, steps_per_day=STEPS_PER_DAY):
    """Return the current step index (0-based) for the given time."""
    minutes = now.hour * 60 + now.minute
    step_minutes = 1440 // steps_per_day
    return min(steps_per_day - 1, minutes // step_minutes)
