import time
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import board
import neopixel
from astral import LocationInfo, moon
from astral.sun import sun

LED_COUNT = 2

# GPIO18 (physical pin 12) is required for WS2812 LEDs because it supports hardware PWM timing.
PIXEL_PIN = board.D18
TIMEZONE = "Europe/Rome"

# Approximate coordinates of the Colosseum, Rome.
# Change these to your own location if needed.
LATITUDE = 41.89
LONGITUDE = 12.49

# Base colors for the day/night cycle.
DEEP_NIGHT = (0, 0, 2)
PRE_DAWN = (40, 10, 4)
SUNRISE = (255, 90, 30)
MORNING = (255, 130, 55)
DAY = (255, 170, 90)
SUNSET = (255, 70, 20)
NIGHT_RETURN = (0, 0, 3)

# Moon color tuned to look soft and not too blue.
MOON_COLOR = (30, 30, 45)

# Brightness levels for the sun cycle.
B_DEEP_NIGHT = 0.02
B_PRE_DAWN = 0.05
B_SUNRISE = 0.11
B_MORNING = 0.18
B_DAY = 0.28
B_SUNSET = 0.10
B_NIGHT_RETURN = 0.02

# Refresh interval in seconds.
REFRESH_SECONDS = 20

pixels = neopixel.NeoPixel(PIXEL_PIN, LED_COUNT, auto_write=False)


def set_all(rgb, brightness):
    pixels.brightness = max(0.0, min(1.0, brightness))
    for i in range(LED_COUNT):
        pixels[i] = rgb
    pixels.show()


def scale_color(color, factor):
    factor = max(0.0, min(1.0, factor))
    return tuple(int(c * factor) for c in color)


def set_moon_phase(left_factor, right_factor, brightness):
    pixels.brightness = max(0.0, min(1.0, brightness))
    pixels[0] = scale_color(MOON_COLOR, left_factor)   # left side
    pixels[1] = scale_color(MOON_COLOR, right_factor)  # right side
    pixels.show()


def lerp(a, b, t):
    return a + (b - a) * t


def blend_color(c1, c2, t):
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )


def blend_value(v1, v2, t):
    return lerp(v1, v2, t)


def phase_progress(now, start, end):
    total = (end - start).total_seconds()
    if total <= 0:
        return 1.0
    current = (now - start).total_seconds()
    return max(0.0, min(1.0, current / total))


def get_today_sun_times():
    tz = ZoneInfo(TIMEZONE)
    city = LocationInfo(
        name="Raspberrarium",
        region="Local",
        timezone=TIMEZONE,
        latitude=LATITUDE,
        longitude=LONGITUDE,
    )
    return sun(city.observer, date=date.today(), tzinfo=tz)


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

    # New moon
    if p < 1.5 or p >= 26.5:
        return 0.0, 0.0, 0.0, p, "New moon"

    # Waxing crescent
    if p < 7.0:
        return 0.03, 0.65, 0.045, p, "Waxing crescent"

    # First quarter
    if p < 10.5:
        return 0.15, 0.85, 0.055, p, "First quarter"

    # Waxing gibbous
    if p < 14.0:
        return 0.50, 1.00, 0.065, p, "Waxing gibbous"

    # Full moon
    if p < 15.5:
        return 1.00, 1.00, 0.08, p, "Full moon"

    # Waning gibbous
    if p < 21.0:
        return 1.00, 0.50, 0.065, p, "Waning gibbous"

    # Last quarter
    if p < 24.0:
        return 0.85, 0.15, 0.055, p, "Last quarter"

    # Waning crescent
    return 0.65, 0.03, 0.045, p, "Waning crescent"


def compute_state(now, s):
    dawn = s["dawn"]
    sunrise = s["sunrise"]
    noon = s["noon"]
    sunset = s["sunset"]
    dusk = s["dusk"]

    morning_mid = sunrise + (noon - sunrise) / 2
    afternoon_mid = noon + (sunset - noon) / 2

    # The moon is shown in the hours before dawn.
    moon_window_start = dawn - timedelta(hours=3)
    moon_window_end = dawn

    # Deep night, including the late night fade after dusk.
    if now < moon_window_start or now >= dusk:
        if now >= dusk:
            late_night_end = dusk + timedelta(hours=1)
            t = phase_progress(now, dusk, late_night_end)
            color = blend_color(NIGHT_RETURN, DEEP_NIGHT, t)
            bright = blend_value(B_NIGHT_RETURN, B_DEEP_NIGHT, t)
            return "sun", color, bright, None
        return "sun", DEEP_NIGHT, B_DEEP_NIGHT, None

    # Moon window before dawn.
    if moon_window_start <= now < moon_window_end:
        left, right, brightness, moon_value, moon_name = get_moon_led_state(now.date())
        return "moon", (left, right), brightness, (moon_value, moon_name)

    # Dawn to sunrise.
    if dawn <= now < sunrise:
        t = phase_progress(now, dawn, sunrise)
        color = blend_color(PRE_DAWN, SUNRISE, t)
        bright = blend_value(B_PRE_DAWN, B_SUNRISE, t)
        return "sun", color, bright, None

    # Sunrise to mid-morning.
    if sunrise <= now < morning_mid:
        t = phase_progress(now, sunrise, morning_mid)
        color = blend_color(SUNRISE, MORNING, t)
        bright = blend_value(B_SUNRISE, B_MORNING, t)
        return "sun", color, bright, None

    # Mid-morning to noon.
    if morning_mid <= now < noon:
        t = phase_progress(now, morning_mid, noon)
        color = blend_color(MORNING, DAY, t)
        bright = blend_value(B_MORNING, B_DAY, t)
        return "sun", color, bright, None

    # Brightest part of the day.
    if noon <= now < afternoon_mid:
        return "sun", DAY, B_DAY, None

    # Afternoon toward sunset.
    if afternoon_mid <= now < sunset:
        t = phase_progress(now, afternoon_mid, sunset)
        color = blend_color(DAY, SUNSET, t)
        bright = blend_value(B_DAY, B_SUNSET, t)
        return "sun", color, bright, None

    # Sunset to dusk.
    if sunset <= now < dusk:
        t = phase_progress(now, sunset, dusk)
        color = blend_color(SUNSET, NIGHT_RETURN, t)
        bright = blend_value(B_SUNSET, B_NIGHT_RETURN, t)
        return "sun", color, bright, None

    return "sun", DEEP_NIGHT, B_DEEP_NIGHT, None


def main():
    tz = ZoneInfo(TIMEZONE)
    last_day = None
    sun_times = None

    while True:
        now = datetime.now(tz)

        if last_day != now.date():
            sun_times = get_today_sun_times()
            last_day = now.date()

            left, right, moon_brightness, moon_value, moon_name = get_moon_led_state(now.date())

            print("Loaded new day:")
            print("Dawn   :", sun_times["dawn"])
            print("Sunrise:", sun_times["sunrise"])
            print("Noon   :", sun_times["noon"])
            print("Sunset :", sun_times["sunset"])
            print("Dusk   :", sun_times["dusk"])
            print(
                f"Moon   : {moon_name} | value={moon_value:.2f} | "
                f"left={left:.2f} right={right:.2f} | brightness={moon_brightness:.3f}"
            )

        mode, payload, brightness, moon_info = compute_state(now, sun_times)

        if mode == "moon":
            left, right = payload
            set_moon_phase(left, right, brightness)
            moon_value, moon_name = moon_info
            print(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"MOON {moon_name} | value={moon_value:.2f} | "
                f"L={left:.2f} R={right:.2f} | brightness={brightness:.3f}"
            )
        else:
            color = payload
            set_all(color, brightness)
            print(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"RGB={color} | brightness={brightness:.3f}"
            )

        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    main()