import argparse
import time

import board
import neopixel

LED_COUNT = 2
PIXEL_PIN = board.D18

BRIGHTNESS_LEVELS = {
    1: 0.60,
    2: 0.80,
    3: 1.00,
}

pixels = neopixel.NeoPixel(PIXEL_PIN, LED_COUNT, auto_write=False)


def parse_args():
    parser = argparse.ArgumentParser(description="Raspberrarium day/night demo")
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


def set_all(rgb, brightness):
    pixels.brightness = max(0.0, min(1.0, brightness))
    for i in range(LED_COUNT):
        pixels[i] = rgb
    pixels.show()


def main():
    args = parse_args()

    phases = [
        ("Deep night", (0, 0, 2), 0.02, 2),
        ("Pre-dawn", (40, 10, 4), 0.05, 2),
        ("Sunrise", (255, 90, 30), 0.11, 2),
        ("Morning", (255, 130, 55), 0.18, 2),
        ("Day", (255, 170, 90), 0.28, 3),
        ("Sunset", (255, 70, 20), 0.10, 2),
        ("Night return", (0, 0, 3), 0.03, 2),
        # Full moon baseline at the end so both LEDs can be checked clearly
        ("Full moon baseline", (30, 30, 45), 0.08, 3),
    ]

    while True:
        for name, rgb, base_brightness, seconds in phases:
            final_brightness = apply_project_brightness(base_brightness, args.brightness)
            print(f"{name} | RGB={rgb} | brightness={final_brightness:.3f}")
            set_all(rgb, final_brightness)
            time.sleep(seconds)


if __name__ == "__main__":
    main()