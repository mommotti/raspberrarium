import argparse
import time

import board
import neopixel

LED_COUNT = 2
PIXEL_PIN = board.D18

MOON_COLOR = (30, 30, 45)

BRIGHTNESS_LEVELS = {
    1: 0.60,
    2: 0.80,
    3: 1.00,
}

pixels = neopixel.NeoPixel(PIXEL_PIN, LED_COUNT, auto_write=False)


def parse_args():
    parser = argparse.ArgumentParser(description="Raspberrarium moon phase demo")
    parser.add_argument(
        "--brightness",
        type=int,
        choices=[1, 2, 3],
        default=3,
        help="Project brightness level from 1 to 3",
    )
    return parser.parse_args()


def apply_project_brightness(base_brightness, level):
    multiplier = BRIGHTNESS_LEVELS.get(level, 1.0)
    return max(0.0, min(1.0, base_brightness * multiplier))


def scale_color(color, factor):
    factor = max(0.0, min(1.0, factor))
    return tuple(int(c * factor) for c in color)


def set_moon(left_factor, right_factor, brightness):
    pixels.brightness = max(0.0, min(1.0, brightness))
    pixels[0] = scale_color(MOON_COLOR, left_factor)
    pixels[1] = scale_color(MOON_COLOR, right_factor)
    pixels.show()


def main():
    args = parse_args()

    phases = [
        ("New moon", 0.0, 0.0, 0.0),
        ("Waxing crescent", 0.03, 0.65, 0.045),
        ("First quarter", 0.15, 0.85, 0.055),
        ("Waxing gibbous", 0.50, 1.00, 0.065),
        ("Full moon", 1.00, 1.00, 0.08),
        ("Waning gibbous", 1.00, 0.50, 0.065),
        ("Last quarter", 0.85, 0.15, 0.055),
        ("Waning crescent", 0.65, 0.03, 0.045),
    ]

    while True:
        for name, left, right, base_brightness in phases:
            final_brightness = apply_project_brightness(base_brightness, args.brightness)
            print(
                f"{name} | left={left:.2f} right={right:.2f} | "
                f"brightness={final_brightness:.3f}"
            )
            set_moon(left, right, final_brightness)
            time.sleep(3)


if __name__ == "__main__":
    main()