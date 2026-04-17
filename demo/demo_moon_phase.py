"""Raspberrarium — moon phase demo."""

import argparse
import sys
import time

import board
import neopixel

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from time_steps import LED_COUNT, MOON_COLOR, MOON_DEMO_PHASES, apply_brightness, scale_color


PIXEL_PIN = board.D18
pixels = neopixel.NeoPixel(PIXEL_PIN, LED_COUNT, auto_write=False)


def parse_args():
    parser = argparse.ArgumentParser(description="Raspberrarium moon phase demo")
    parser.add_argument(
        "--brightness", type=int, choices=[1, 2, 3], default=3,
        help="Project brightness level (1 = dimmest, 3 = brightest)",
    )
    return parser.parse_args()


def set_moon(left_factor, right_factor, brightness):
    pixels.brightness = max(0.0, min(1.0, brightness))
    pixels[0] = scale_color(MOON_COLOR, left_factor)
    pixels[1] = scale_color(MOON_COLOR, right_factor)
    pixels.show()


def main():
    args = parse_args()

    while True:
        for name, left, right, base_brightness in MOON_DEMO_PHASES:
            final = apply_brightness(base_brightness, args.brightness)
            print(
                f"{name} | left={left:.2f} right={right:.2f} | "
                f"brightness={final:.3f}"
            )
            set_moon(left, right, final)
            time.sleep(3)


if __name__ == "__main__":
    main()
