"""Raspberrarium — moon phase demo."""

import argparse
import itertools
import sys
import threading
import time

import board
import neopixel

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from time_steps import LED_COUNT, MOON_COLOR, MOON_DEMO_PHASES, apply_brightness, scale_color


PIXEL_PIN = board.D18
pixels = neopixel.NeoPixel(PIXEL_PIN, LED_COUNT, auto_write=False)

TOTAL_PHASES = len(MOON_DEMO_PHASES)

_lock = threading.Lock()
_status = "Moon phase demo running..."


def _status_loop():
    icons = ("🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘")
    it = itertools.cycle(icons)
    while True:
        icon = next(it)
        with _lock:
            sys.stdout.write(f"\r{_status} {icon} 💚🫙🌱 {icon}   ")
            sys.stdout.flush()
        time.sleep(0.8)


def _log(message):
    with _lock:
        sys.stdout.write("\r" + " " * 120 + "\r")
        print(message)
        sys.stdout.flush()


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
    threading.Thread(target=_status_loop, daemon=True).start()

    while True:
        for i, (name, left, right, base_brightness) in enumerate(MOON_DEMO_PHASES, 1):
            final = apply_brightness(base_brightness, args.brightness)
            _log(
                f"Phase {i} of {TOTAL_PHASES} | {name} | "
                f"left={left:.2f} right={right:.2f} | brightness={final:.3f}"
            )
            set_moon(left, right, final)
            time.sleep(3)


if __name__ == "__main__":
    main()
