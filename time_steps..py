from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral.sun import sun


TIMEZONE = "Europe/Rome"    # 🌱 Change this
LATITUDE = 00.00            # 🌱 Change this
LONGITUDE = 00.00           # 🌱 Change this

STEPS_PER_DAY = 96
STEP_MINUTES = 15

DEEP_NIGHT = (0, 0, 2)
PRE_DAWN = (40, 10, 4)
SUNRISE = (255, 90, 30)
MORNING = (255, 130, 55)
DAY = (255, 170, 90)
SUNSET = (255, 70, 20)
NIGHT_RETURN = (0, 0, 3)

B_DEEP_NIGHT = 0.02
B_PRE_DAWN = 0.05
B_SUNRISE = 0.11
B_MORNING = 0.18
B_DAY = 0.28
B_SUNSET = 0.10
B_NIGHT_RETURN = 0.02


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


def clamp01(value):
    return max(0.0, min(1.0, value))


def get_today_sun_times(
    current_date=None,
    timezone=TIMEZONE,
    latitude=LATITUDE,
    longitude=LONGITUDE,
):
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


def state_at_time(now, sun_times):
    dawn = sun_times["dawn"]
    sunrise = sun_times["sunrise"]
    noon = sun_times["noon"]
    sunset = sun_times["sunset"]
    dusk = sun_times["dusk"]

    morning_mid = sunrise + (noon - sunrise) / 2
    afternoon_mid = noon + (sunset - noon) / 2

    if now < dawn:
        return DEEP_NIGHT, B_DEEP_NIGHT

    if dawn <= now < sunrise:
        total = (sunrise - dawn).total_seconds()
        progress = clamp01((now - dawn).total_seconds() / total)
        return (
            blend_color(PRE_DAWN, SUNRISE, progress),
            blend_value(B_PRE_DAWN, B_SUNRISE, progress),
        )

    if sunrise <= now < morning_mid:
        total = (morning_mid - sunrise).total_seconds()
        progress = clamp01((now - sunrise).total_seconds() / total)
        return (
            blend_color(SUNRISE, MORNING, progress),
            blend_value(B_SUNRISE, B_MORNING, progress),
        )

    if morning_mid <= now < noon:
        total = (noon - morning_mid).total_seconds()
        progress = clamp01((now - morning_mid).total_seconds() / total)
        return (
            blend_color(MORNING, DAY, progress),
            blend_value(B_MORNING, B_DAY, progress),
        )

    if noon <= now < afternoon_mid:
        return DAY, B_DAY

    if afternoon_mid <= now < sunset:
        total = (sunset - afternoon_mid).total_seconds()
        progress = clamp01((now - afternoon_mid).total_seconds() / total)
        return (
            blend_color(DAY, SUNSET, progress),
            blend_value(B_DAY, B_SUNSET, progress),
        )

    if sunset <= now < dusk:
        total = (dusk - sunset).total_seconds()
        progress = clamp01((now - sunset).total_seconds() / total)
        return (
            blend_color(SUNSET, NIGHT_RETURN, progress),
            blend_value(B_SUNSET, B_NIGHT_RETURN, progress),
        )

    return DEEP_NIGHT, B_DEEP_NIGHT


def build_daily_steps(
    current_date=None,
    timezone=TIMEZONE,
    latitude=LATITUDE,
    longitude=LONGITUDE,
    steps_per_day=STEPS_PER_DAY,
):
    tz = ZoneInfo(timezone)
    if current_date is None:
        current_date = date.today()

    sun_times = get_today_sun_times(current_date, timezone, latitude, longitude)
    day_start = datetime.combine(current_date, datetime.min.time(), tz)

    step_minutes = 1440 // steps_per_day
    states = []

    for index in range(steps_per_day):
        step_time = day_start + timedelta(minutes=index * step_minutes)
        rgb, brightness = state_at_time(step_time, sun_times)
        states.append(
            {
                "index": index,
                "time": step_time,
                "rgb": rgb,
                "brightness": brightness,
            }
        )

    return states, sun_times


def get_current_step_index(now, steps_per_day=STEPS_PER_DAY):
    minutes_since_midnight = now.hour * 60 + now.minute
    step_minutes = 1440 // steps_per_day
    index = minutes_since_midnight // step_minutes
    return min(steps_per_day - 1, index)