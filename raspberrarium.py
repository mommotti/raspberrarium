import argparse
import itertools
import sys
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import board
import neopixel
from astral import moon

from time_steps import (
    TIMEZONE,
    LATITUDE,
    LONGITUDE,
    STEPS_PER_DAY,
    build_daily_steps,
    get_current_step_index,
)

LED_COUNT = 2

# GPIO18 (physical pin 12) is required for WS2812 LEDs because it supports hardware PWM timing.
PIXEL_PIN = board.D18

# Moon color tuned to look soft and not too blue.
MOON_COLOR = (30, 30, 45)

# Moon is shown in the hours before dawn.
MOON_WINDOW_HOURS = 3

# Polling interval in seconds.
REFRESH_SECONDS = 10

# Project brightness presets.
# 1 = dimmest, 3 = brightest
BRIGHTNESS_LEVELS = {
    1: 0.60,
    2: 0.80,
    3: 1.00,
}

pixels = neopixel.NeoPixel(PIXEL_PIN, LED_COUNT, auto_write=False)

STATUS_LOCK = threading.Lock()
STATUS_MESSAGE = "Your Raspberrarium is running..."
SHOW_LOGS = True


def status_loop():
    moon_cycle = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
    day_cycle = ["🌙", "🌅", "☀️", "🌇", "🌌"]

    day_iter = itertools.cycle(day_cycle)
    moon_iter = itertools.cycle(moon_cycle)

    while True:
        day = next(day_iter)
        moon_phase = next(moon_iter)

        with STATUS_LOCK:
            sys.stdout.write(
                f"\r{STATUS_MESSAGE} {day} 💚🫙🌱 {moon_phase}   "
            )
            sys.stdout.flush()

        time.sleep(0.8)


def print_log(message):
    if not SHOW_LOGS:
        return

    with STATUS_LOCK:
        sys.stdout.write("\r" + " " * 120 + "\r")
        print(message)
        sys.stdout.flush()


def parse_args():
    parser = argparse.ArgumentParser(description="Raspberrarium lighting controller")
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Suppress console output",
    )
    parser.add_argument(
        "--brightness",
        type=int,
        choices=[1, 2, 3],
        default=3,
        help="Project brightness level from 1 to 3",
    )
    return parser.parse_args()


def scale_color(color, factor):
    factor = max(0.0, min(1.0, factor))
    return tuple(int(c * factor) for c in color)


def apply_project_brightness(base_brightness, level):
    multiplier = BRIGHTNESS_LEVELS.get(level, 1.0)
    return max(0.0, min(1.0, base_brightness * multiplier))


def set_all(rgb, brightness):
    pixels.brightness = max(0.0, min(1.0, brightness))
    for i in range(LED_COUNT):
        pixels[i] = rgb
    pixels.show()


def set_moon_phase(left_factor, right_factor, brightness):
    pixels.brightness = max(0.0, min(1.0, brightness))
    pixels[0] = scale_color(MOON_COLOR, left_factor)
    pixels[1] = scale_color(MOON_COLOR, right_factor)
    pixels.show()


def get_moon_led_state(current_date):
    """
    Map Astral's moon phase value to two LEDs.

    LED 0 is the left side of the moon.
    LED 1 is the right side of the moon.

    This mapping is tuned for a small jar with only two LEDs, so it favors
    readability over astronomical precision.

    New moon is completely off.
    """
    p = moon.phase(current_date)

    if p < 1.5 or p >= 26.5:
        return 0.0, 0.0, 0.0, p, "New moon"

    if p < 7.0:
        return 0.03, 0.65, 0.045, p, "Waxing crescent"

    if p < 10.5:
        return 0.15, 0.85, 0.055, p, "First quarter"

    if p < 14.0:
        return 0.50, 1.00, 0.065, p, "Waxing gibbous"

    if p < 15.5:
        return 1.00, 1.00, 0.08, p, "Full moon"

    if p < 21.0:
        return 1.00, 0.50, 0.065, p, "Waning gibbous"

    if p < 24.0:
        return 0.85, 0.15, 0.055, p, "Last quarter"

    return 0.65, 0.03, 0.045, p, "Waning crescent"


def main():
    global STATUS_MESSAGE, SHOW_LOGS

    args = parse_args()
    tz = ZoneInfo(TIMEZONE)

    SHOW_LOGS = not args.silent
    STATUS_MESSAGE = (
        "Your Raspberrarium is running silently..."
        if args.silent
        else "Your Raspberrarium is running..."
    )

    threading.Thread(target=status_loop, daemon=True).start()

    last_day = None
    daily_states = None
    sun_times = None

    while True:
        now = datetime.now(tz)

        if last_day != now.date():
            daily_states, sun_times = build_daily_steps(
                current_date=now.date(),
                timezone=TIMEZONE,
                latitude=LATITUDE,
                longitude=LONGITUDE,
                steps_per_day=STEPS_PER_DAY,
            )
            last_day = now.date()

            left, right, moon_brightness, moon_value, moon_name = get_moon_led_state(now.date())

            print_log("Loaded new day:")
            print_log(f"Dawn   : {sun_times['dawn']}")
            print_log(f"Sunrise: {sun_times['sunrise']}")
            print_log(f"Noon   : {sun_times['noon']}")
            print_log(f"Sunset : {sun_times['sunset']}")
            print_log(f"Dusk   : {sun_times['dusk']}")
            print_log(
                f"Moon   : {moon_name} | value={moon_value:.2f} | "
                f"left={left:.2f} right={right:.2f} | brightness={moon_brightness:.3f}"
            )

        moon_window_start = sun_times["dawn"] - timedelta(hours=MOON_WINDOW_HOURS)
        moon_window_end = sun_times["dawn"]

        if moon_window_start <= now < moon_window_end:
            left, right, moon_brightness, moon_value, moon_name = get_moon_led_state(now.date())
            final_brightness = apply_project_brightness(moon_brightness, args.brightness)
            set_moon_phase(left, right, final_brightness)

            print_log(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"MOON {moon_name} | value={moon_value:.2f} | "
                f"L={left:.2f} R={right:.2f} | brightness={final_brightness:.3f}"
            )
        else:
            step_index = get_current_step_index(now, STEPS_PER_DAY)
            state = daily_states[step_index]

            rgb = state["rgb"]
            brightness = apply_project_brightness(state["brightness"], args.brightness)

            set_all(rgb, brightness)

            print_log(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"STEP={step_index:02d} | RGB={rgb} | brightness={brightness:.3f}"
            )

        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    main()