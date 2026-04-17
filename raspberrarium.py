"""
Raspberrarium — main lighting controller.

Runs a continuous loop that drives two WS2812 LEDs through a realistic
24-hour day/night cycle with moon-phase simulation.
"""

import argparse
import itertools
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import board
import neopixel

from time_steps import (
    TIMEZONE,
    LATITUDE,
    LONGITUDE,
    LED_COUNT,
    STEPS_PER_DAY,
    MOON_WINDOW_HOURS,
    MOON_COLOR,
    REFRESH_SECONDS,
    apply_brightness,
    scale_color,
    get_moon_led_state,
    build_daily_steps,
    get_current_step_index,
)


# ---------------------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------------------

# GPIO18 (physical pin 12) is required for WS2812 LEDs — hardware PWM.
PIXEL_PIN = board.D18

pixels = neopixel.NeoPixel(PIXEL_PIN, LED_COUNT, auto_write=False)


# ---------------------------------------------------------------------------
# Status line (fixed header with animated spinner)
# ---------------------------------------------------------------------------

_status_lock = threading.Lock()
_status_message = ""
_show_logs = True
_has_tty = sys.stdout.isatty()


def _setup_fixed_header():
    """Reserve line 1 for the spinner; scroll region starts at line 2."""
    if not _has_tty:
        return
    rows = os.get_terminal_size().lines
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write(f"{_status_message} 💚🌱🫙🌱\n")
    sys.stdout.write(f"\033[2;{rows}r")
    sys.stdout.write("\033[2;1H")
    sys.stdout.flush()


def _status_loop():
    """Background spinner pinned to line 1."""
    if not _has_tty:
        return
    icons = ("🌙", "🌅", "☀️", "🌇", "🌌", "🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘")
    it = itertools.cycle(icons)
    while True:
        icon = next(it)
        with _status_lock:
            sys.stdout.write(f"\033[s\033[1;1H\033[2K{_status_message} 💚{icon}🫙🌱   \033[u")
            sys.stdout.flush()
        time.sleep(0.8)


def _log(message):
    """Print a log line below the fixed header."""
    if not _show_logs:
        return
    with _status_lock:
        print(message)
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# LED helpers
# ---------------------------------------------------------------------------

def set_all(rgb, brightness):
    """Set both LEDs to the same color and brightness."""
    pixels.brightness = max(0.0, min(1.0, brightness))
    pixels[0] = rgb
    pixels[1] = rgb
    pixels.show()


def set_moon(left_factor, right_factor, brightness):
    """Set each LED independently to simulate a moon phase."""
    pixels.brightness = max(0.0, min(1.0, brightness))
    pixels[0] = scale_color(MOON_COLOR, left_factor)
    pixels[1] = scale_color(MOON_COLOR, right_factor)
    pixels.show()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Raspberrarium lighting controller")
    parser.add_argument("--silent", action="store_true", help="Suppress console output")
    parser.add_argument(
        "--brightness", type=int, choices=[1, 2, 3], default=3,
        help="Project brightness level (1 = dimmest, 3 = brightest)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    global _status_message, _show_logs

    args = parse_args()
    tz = ZoneInfo(TIMEZONE)
    brightness_level = args.brightness

    _show_logs = not args.silent
    _status_message = (
        "Your Raspberrarium is running silently..."
        if args.silent
        else "Your Raspberrarium is running..."
    )

    _setup_fixed_header()
    threading.Thread(target=_status_loop, daemon=True).start()

    last_day = None
    daily_states = None
    sun_times = None
    cached_moon = None

    while True:
        now = datetime.now(tz)
        today = now.date()

        # Recalculate once per day.
        if last_day != today:
            daily_states, sun_times = build_daily_steps(
                current_date=today,
                timezone=TIMEZONE,
                latitude=LATITUDE,
                longitude=LONGITUDE,
                steps_per_day=STEPS_PER_DAY,
            )
            cached_moon = get_moon_led_state(today)
            last_day = today

            left, right, moon_br, moon_val, moon_name = cached_moon
            _log("Loaded new day:")
            _log(f"Dawn   : {sun_times['dawn']}")
            _log(f"Sunrise: {sun_times['sunrise']}")
            _log(f"Noon   : {sun_times['noon']}")
            _log(f"Sunset : {sun_times['sunset']}")
            _log(f"Dusk   : {sun_times['dusk']}")
            _log(
                f"Moon   : {moon_name} | value={moon_val:.2f} | "
                f"left={left:.2f} right={right:.2f} | brightness={moon_br:.3f}"
            )

        # Moon window: the hours just before dawn.
        moon_start = sun_times["dawn"] - timedelta(hours=MOON_WINDOW_HOURS)
        moon_end = sun_times["dawn"]

        if moon_start <= now < moon_end:
            left, right, moon_br, moon_val, moon_name = cached_moon
            final = apply_brightness(moon_br, brightness_level)
            set_moon(left, right, final)
            _log(
                f"{now:%Y-%m-%d %H:%M:%S} | MOON {moon_name} | "
                f"value={moon_val:.2f} | L={left:.2f} R={right:.2f} | "
                f"brightness={final:.3f}"
            )
        else:
            idx = get_current_step_index(now, STEPS_PER_DAY)
            rgb, base_br = daily_states[idx]
            final = apply_brightness(base_br, brightness_level)
            set_all(rgb, final)
            _log(
                f"{now:%Y-%m-%d %H:%M:%S} | STEP={idx:02d} | "
                f"RGB={rgb} | brightness={final:.3f}"
            )

        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    try:
        main()
    finally:
        if _has_tty:
            sys.stdout.write("\033[r\033[2J\033[H")
            sys.stdout.flush()
