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

MOON_WINDOW_HOURS = 3
REFRESH_SECONDS = 10

# How long the new transitional phases last (in minutes).
FIRST_LIGHT_MINUTES = 45   # gradual blue glow before dawn
TWILIGHT_MINUTES = 60       # blue hour after dusk


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
#
# The full day progression (11 segments, 9 anchor colors):
#
#   DEEP_NIGHT ──→ FIRST_LIGHT ──→ PRE_DAWN ──→ SUNRISE ──→ MORNING
#        ──→ DAY (hold) ──→ SUNSET ──→ TWILIGHT ──→ DEEP_NIGHT
#
# ---------------------------------------------------------------------------

DEEP_NIGHT   = (0,   0,   2)     # near-black
FIRST_LIGHT  = (5,   5,   25)    # very faint cool blue (pre-dawn sky)
PRE_DAWN     = (40,  10,  4)     # warm horizon glow
SUNRISE      = (255, 90,  30)    # golden sunrise
MORNING      = (255, 130, 55)    # warm morning light
DAY          = (255, 170, 90)    # full daylight
SUNSET       = (255, 70,  20)    # warm sunset
TWILIGHT     = (12,  8,   30)    # blue hour after dusk

B_DEEP_NIGHT   = 0.04
B_FIRST_LIGHT  = 0.06
B_PRE_DAWN     = 0.12
B_SUNRISE      = 0.35
B_MORNING      = 0.60
B_DAY          = 1.00
B_SUNSET       = 0.30
B_TWILIGHT     = 0.07


# ---------------------------------------------------------------------------
# Moon
# ---------------------------------------------------------------------------

MOON_COLOR = (30, 30, 45)

# (phase_start, phase_end, left_factor, right_factor, base_brightness, name)
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
    ("Deep night",         DEEP_NIGHT,   B_DEEP_NIGHT,   2),
    ("First light",        FIRST_LIGHT,  B_FIRST_LIGHT,  2),
    ("Pre-dawn",           PRE_DAWN,     B_PRE_DAWN,     2),
    ("Sunrise",            SUNRISE,      B_SUNRISE,      2),
    ("Morning",            MORNING,      B_MORNING,      2),
    ("Day",                DAY,          B_DAY,          3),
    ("Sunset",             SUNSET,       B_SUNSET,       2),
    ("Twilight",           TWILIGHT,     B_TWILIGHT,     2),
    ("Full moon baseline", MOON_COLOR,   0.16,           3),
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


def _blend_segment(now, start, end, color_a, bright_a, color_b, bright_b):
    """Compute blended (rgb, brightness) for a time between start and end."""
    t = clamp01((now - start).total_seconds() / (end - start).total_seconds())
    return blend_color(color_a, color_b, t), lerp(bright_a, bright_b, t)


def state_at_time(now, sun_times):
    """
    Return (rgb, brightness) for a specific moment given today's sun times.

    Day progression (11 segments):

      deep night
        → first light (45 min before dawn — faint blue)
        → pre-dawn (dawn — warm horizon glow)
        → sunrise
        → morning
        → day (holds steady around noon)
        → sunset
        → twilight (dusk — blue hour)
        → deep night
    """
    dawn    = sun_times["dawn"]
    sunrise = sun_times["sunrise"]
    noon    = sun_times["noon"]
    sunset  = sun_times["sunset"]
    dusk    = sun_times["dusk"]

    # Computed waypoints
    first_light_start = dawn - timedelta(minutes=FIRST_LIGHT_MINUTES)
    dawn_mid          = dawn + (sunrise - dawn) / 2
    morning_mid       = sunrise + (noon - sunrise) / 2
    afternoon_mid     = noon + (sunset - noon) / 2
    twilight_end      = dusk + timedelta(minutes=TWILIGHT_MINUTES)

    # ── Night (before first light) ──
    if now < first_light_start:
        return DEEP_NIGHT, B_DEEP_NIGHT

    # ── First light: deep night → faint blue ──
    if now < dawn:
        return _blend_segment(now, first_light_start, dawn,
                              DEEP_NIGHT, B_DEEP_NIGHT, FIRST_LIGHT, B_FIRST_LIGHT)

    # ── Dawn first half: first light → pre-dawn warm glow ──
    if now < dawn_mid:
        return _blend_segment(now, dawn, dawn_mid,
                              FIRST_LIGHT, B_FIRST_LIGHT, PRE_DAWN, B_PRE_DAWN)

    # ── Dawn second half: pre-dawn → sunrise ──
    if now < sunrise:
        return _blend_segment(now, dawn_mid, sunrise,
                              PRE_DAWN, B_PRE_DAWN, SUNRISE, B_SUNRISE)

    # ── Sunrise → morning ──
    if now < morning_mid:
        return _blend_segment(now, sunrise, morning_mid,
                              SUNRISE, B_SUNRISE, MORNING, B_MORNING)

    # ── Morning → day ──
    if now < noon:
        return _blend_segment(now, morning_mid, noon,
                              MORNING, B_MORNING, DAY, B_DAY)

    # ── Day (hold steady) ──
    if now < afternoon_mid:
        return DAY, B_DAY

    # ── Day → sunset ──
    if now < sunset:
        return _blend_segment(now, afternoon_mid, sunset,
                              DAY, B_DAY, SUNSET, B_SUNSET)

    # ── Sunset → twilight (blue hour) ──
    if now < dusk:
        return _blend_segment(now, sunset, dusk,
                              SUNSET, B_SUNSET, TWILIGHT, B_TWILIGHT)

    # ── Twilight → deep night ──
    if now < twilight_end:
        return _blend_segment(now, dusk, twilight_end,
                              TWILIGHT, B_TWILIGHT, DEEP_NIGHT, B_DEEP_NIGHT)

    # ── Full night ──
    return DEEP_NIGHT, B_DEEP_NIGHT


def get_today_sun_times_for_date(current_date=None, timezone=TIMEZONE,
                                 latitude=LATITUDE, longitude=LONGITUDE):
    """
    Return sun times for a given date.

    Returns sun_times dict from Astral.
    The main loop calls state_at_time() directly each cycle for
    minute-accurate color, so no pre-computed step table is needed.
    """
    return get_today_sun_times(current_date, timezone, latitude, longitude)
