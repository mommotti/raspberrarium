import board
import neopixel
import time

pixels = neopixel.NeoPixel(board.D18, 2, auto_write=False)

# softer + less intense
MOON_COLOR = (30, 30, 45)

def scale_color(color, factor):
    return tuple(int(c * factor) for c in color)

def set_moon(left, right, brightness):
    pixels.brightness = brightness
    pixels[0] = scale_color(MOON_COLOR, left)
    pixels[1] = scale_color(MOON_COLOR, right)
    pixels.show()

phases = [
    ("New moon",         0.0, 0.0, 0.0),   # moon off.

    ("Waxing crescent",  0.03, 0.65, 0.045),

    ("First quarter",    0.15, 0.85, 0.055),

    ("Waxing gibbous",   0.50, 1.00, 0.065),

    ("Full moon",        1.00, 1.00, 0.08),

    ("Waning gibbous",   1.00, 0.50, 0.065),

    ("Last quarter",     0.85, 0.15, 0.055),

    ("Waning crescent",  0.65, 0.03, 0.045),
]

while True:
    for name, left, right, brightness in phases:
        print(name)
        set_moon(left, right, brightness)
        time.sleep(3)