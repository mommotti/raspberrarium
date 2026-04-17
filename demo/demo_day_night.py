"""Raspberrarium — day/night cycle demo."""

import argparse
import sys
import time

import board
import neopixel

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from time_steps import LED_COUNT, DAY_DEMO_PHASES, apply_brightness


PIXEL_PIN = board.D18
pixels = neopixel.NeoPixel(PIXEL_PIN, LED_COUNT, auto_write=False)

TOTAL_PHASES = len(DAY_DEMO_PHASES)


def parse_args():
    parser = argparse.ArgumentParser(description="Raspberrarium day/night demo")
    parser.add_argument(
        "--brightness", type=int, choices=[1, 2, 3], default=3,
        help="Project brightness level (1 = dimmest, 3 = brightest)",
    )
    return parser.parse_args()


def set_all(rgb, brightness):
    pixels.brightness = max(0.0, min(1.0, brightness))
    pixels[0] = rgb
    pixels[1] = rgb
    pixels.show()


def main():
    args = parse_args()

    while True:
        for i, (name, rgb, base_brightness, seconds) in enumerate(DAY_DEMO_PHASES, 1):
            final = apply_brightness(base_brightness, args.brightness)
            print(f"Phase {i} of {TOTAL_PHASES} | {name} | RGB={rgb} | brightness={final:.3f}")
            set_all(rgb, final)
            time.sleep(seconds * 1.5)


if __name__ == "__main__":
    main()
