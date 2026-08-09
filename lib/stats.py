# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
# Copyright (C) 2022-2023  Rollbacke
# Copyright (C) 2022-2023  Ebag333
# Copyright (C) 2022-2023  w1ld3r
# Copyright (C) 2022-2023  Charles Ferguson (gerph)
# Copyright (C) 2024-2024  WeAct Studio
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import datetime
import locale
import math
import os
import platform
import sys
from typing import List
from pathlib import Path
import babel.dates
from psutil._common import bytes2human
from uptime import uptime

import lib.config as config
from lib.display import display
from lib.log import logger
from lib import utils

DEFAULT_HISTORY_SIZE = 10

ETH_CARD = config.CONFIG_DATA["config"].get("ETH", "")
WLO_CARD = config.CONFIG_DATA["config"].get("WLO", "")
HW_SENSORS = config.CONFIG_DATA["config"].get("HW_SENSORS", "AUTO")
CPU_FAN = config.CONFIG_DATA["config"].get("CPU_FAN", "AUTO")

if HW_SENSORS == "PYTHON":
    if platform.system() == 'Windows':
        logger.warning("It is recommended to use LibreHardwareMonitor integration for Windows instead of Python "
                       "libraries (require admin. rights)")
    import lib.sensors.sensors_python as sensors
elif HW_SENSORS == "LHM":
    if platform.system() == 'Windows':
        import lib.sensors.sensors_librehardwaremonitor as sensors
        sensors.init(utils.get_root_dir() / config.CONFIG_DATA["config"]["LIBREHARDWAREMONITORLIB_DIR"])
    else:
        logger.error("LibreHardwareMonitor integration is only available on Windows")
        try:
            sys.exit(0)
        except:
            os._exit(0)
elif HW_SENSORS == "STUB":
    logger.warning("Stub sensors, not real HW sensors")
    import lib.sensors.sensors_stub_random as sensors
elif HW_SENSORS == "STATIC":
    logger.warning("Stub sensors, not real HW sensors")
    import lib.sensors.sensors_stub_static as sensors
elif HW_SENSORS == "AUTO":
    if platform.system() == 'Windows':
        import lib.sensors.sensors_librehardwaremonitor as sensors
        sensors.init(utils.get_root_dir() / config.CONFIG_DATA["config"]["LIBREHARDWAREMONITORLIB_DIR"])
    else:
        import lib.sensors.sensors_python as sensors
else:
    logger.error("Unsupported HW_SENSORS value in config.yaml")
    try:
        sys.exit(0)
    except:
        os._exit(0)

import lib.sensors.sensors_custom as sensors_custom

def display_themed_value(theme_data, value, min_size=0, unit=''):
    if not theme_data.get("SHOW", False):
        return

    if value is None:
        return

    # overridable MIN_SIZE from theme with backward compatibility
    min_size_t = theme_data.get("MIN_SIZE", min_size)
    mini_size_t = theme_data.get("MINI_SIZE", min_size)
    if min_size_t != 0:
        min_size = min_size_t
    elif mini_size_t != 0:
        min_size = mini_size_t
    text = f"{{:>{min_size}}}".format(value)
    anchor = theme_data.get("ANCHOR", "lt")
    if theme_data.get("SHOW_UNIT", True) and unit:
        if theme_data.get("UNIT_ML", False):
            text += '\n' + str(unit)
            # anchor = None
        else:
            text += str(unit)

    display.lcd.DisplayText(
        text=text,
        x=theme_data.get("X", 0),
        y=theme_data.get("Y", 0),
        width=theme_data.get("WIDTH", 0),
        height=theme_data.get("HEIGHT", 0),
        font=config.get_font_path(theme_data.get("FONT", None)),
        font_size=theme_data.get("FONT_SIZE", 10),
        font_color=theme_data.get("FONT_COLOR", (0, 0, 0)),
        background_color=theme_data.get("BACKGROUND_COLOR", (255, 255, 255)),
        background_image=config.get_theme_file_path(theme_data.get("BACKGROUND_IMAGE", None)),
        align=theme_data.get("ALIGN", "justify"),
        anchor=anchor,
        rotation=theme_data.get("ROTATION", 0),
    )


def display_themed_percent_value(theme_data, value):
    display_themed_value(
        theme_data=theme_data,
        value=int(value),
        min_size=3,
        unit="%"
    )


def display_themed_temperature_value(theme_data, value):
    display_themed_value(
        theme_data=theme_data,
        value=int(value),
        min_size=3,
        unit="°C"
    )

def display_themed_progress_bar(theme_data, value):
    if not theme_data.get("SHOW", False):
        return

    display.lcd.DisplayProgressBar(
        x=theme_data.get("X", 0),
        y=theme_data.get("Y", 0),
        width=theme_data.get("WIDTH", 0),
        height=theme_data.get("HEIGHT", 0),
        value=int(value),
        min_value=theme_data.get("MIN_VALUE", 0),
        max_value=theme_data.get("MAX_VALUE", 100),
        bar_color=theme_data.get("BAR_COLOR", (0, 0, 0)),
        bar_outline=theme_data.get("BAR_OUTLINE", False),
        background_color=theme_data.get("BACKGROUND_COLOR", (255, 255, 255)),
        background_image=config.get_theme_file_path(theme_data.get("BACKGROUND_IMAGE", None))
    )


def display_themed_radial_bar(theme_data, value, min_size=0, unit='', custom_text=None):
    if not theme_data.get("SHOW", False):
        return

    if theme_data.get("SHOW_TEXT", False):
        if custom_text:
            text = custom_text
        else:
            text = f"{{:>{min_size}}}".format(value)
            if theme_data.get("SHOW_UNIT", True) and unit:
                text += str(unit)
    else:
        text = ""

    display.lcd.DisplayRadialProgressBar(
        xc=theme_data.get("X", 0),
        yc=theme_data.get("Y", 0),
        radius=theme_data.get("RADIUS", 1),
        bar_width=theme_data.get("WIDTH", 1),
        min_value=theme_data.get("MIN_VALUE", 0),
        max_value=theme_data.get("MAX_VALUE", 100),
        angle_start=theme_data.get("ANGLE_START", 0),
        angle_end=theme_data.get("ANGLE_END", 360),
        angle_steps=theme_data.get("ANGLE_STEPS", 1),
        angle_sep=theme_data.get("ANGLE_SEP", 0),
        clockwise=theme_data.get("CLOCKWISE", False),
        value=float(value),
        bar_color=theme_data.get("BAR_COLOR", (0, 0, 0)),
        text=text,
        font=config.get_font_path(theme_data.get("FONT", None)),
        font_size=theme_data.get("FONT_SIZE", 10),
        font_color=theme_data.get("FONT_COLOR", (0, 0, 0)),
        background_color=theme_data.get("BACKGROUND_COLOR", (0, 0, 0)),
        background_image=config.get_theme_file_path(theme_data.get("BACKGROUND_IMAGE", None)),
        custom_bbox=theme_data.get("CUSTOM_BBOX", (0, 0, 0, 0)),
        text_offset=theme_data.get("TEXT_OFFSET", (0, 0)),
        bar_background_color = theme_data.get("BAR_BACKGROUND_COLOR", (0, 0, 0)),
        draw_bar_background = theme_data.get("DRAW_BAR_BACKGROUND", False),
        bar_decoration = theme_data.get("BAR_DECORATION", "")
    )


def display_themed_percent_radial_bar(theme_data, value):
    display_themed_radial_bar(
        theme_data=theme_data,
        value=int(value),
        unit="%",
        min_size=3
    )


def display_themed_temperature_radial_bar(theme_data, value):
    display_themed_radial_bar(
        theme_data=theme_data,
        value=int(value),
        min_size=3,
        unit="°C"
    )


def display_themed_line_graph(theme_data, values):
    if not theme_data.get("SHOW", False):
        return

    line_color = theme_data.get("LINE_COLOR", (0, 0, 0))

    display.lcd.DisplayLineGraph(
        x=theme_data.get("X", 0),
        y=theme_data.get("Y", 0),
        width=theme_data.get("WIDTH", 1),
        height=theme_data.get("HEIGHT", 1),
        values=values,
        min_value=theme_data.get("MIN_VALUE", 0),
        max_value=theme_data.get("MAX_VALUE", 100),
        autoscale=theme_data.get("AUTOSCALE", False),
        line_color=line_color,
        line_width=theme_data.get("LINE_WIDTH", 2),
        graph_axis=theme_data.get("AXIS", False),
        axis_color=theme_data.get("AXIS_COLOR", line_color),  # If no color specified, use line color for axis
        axis_font=config.get_font_path(theme_data.get("AXIS_FONT", None)),
        axis_font_size=theme_data.get("AXIS_FONT_SIZE", 10),
        background_color=theme_data.get("BACKGROUND_COLOR", (0, 0, 0)),
        background_image=config.get_theme_file_path(theme_data.get("BACKGROUND_IMAGE", None))
    )


def save_last_value(value: float, last_values: List[float], history_size: int):
    # Initialize last values list the first time with given size
    if len(last_values) != history_size:
        last_values[:] = last_values_list(size=history_size)
    # Store the value to the list that can then be used for line graph
    last_values.append(value)
    # Also remove the oldest value from list
    last_values.pop(0)


def last_values_list(size: int) -> List[float]:
    return [math.nan] * size


class CPU:
    last_values_cpu_percentage = []
    last_values_cpu_power = []
    last_values_cpu_temperature = []
    last_values_cpu_fan_speed = []
    last_values_cpu_frequency = []

    @classmethod
    def percentage(cls,forced_refresh = False):
        theme_data = config.THEME_DATA['STATS']['CPU']['PERCENTAGE']
        cpu_percentage = sensors.Cpu.percentage(
            interval=theme_data.get("INTERVAL", None)
        )

        if math.isnan(cpu_percentage):
            cpu_percentage = 0

        save_last_value(cpu_percentage, cls.last_values_cpu_percentage,
                        theme_data['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        
        need_refresh = True
        if math.isnan(cls.last_values_cpu_percentage[-2]) == False:
            if int(cpu_percentage) == int(cls.last_values_cpu_percentage[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_progress_bar(theme_data['GRAPH'], cpu_percentage)
            display_themed_percent_radial_bar(theme_data['RADIAL'], cpu_percentage)
            display_themed_percent_value(theme_data['TEXT'], cpu_percentage)    
        display_themed_line_graph(theme_data['LINE_GRAPH'], cls.last_values_cpu_percentage)

    @classmethod
    def power(cls,forced_refresh = False):
        theme_data = config.THEME_DATA['STATS']['CPU']['POWER']
        cpu_power = sensors.Cpu.power()
        if math.isnan(cpu_power):
            cpu_power = 0

        save_last_value(cpu_power, cls.last_values_cpu_power,
                        theme_data['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        
        need_refresh = True
        if math.isnan(cls.last_values_cpu_power[-2]) == False:
            if int(cpu_power) == int(cls.last_values_cpu_power[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_value(
                theme_data=theme_data['TEXT'],
                value=f'{cpu_power:.1f}',
                unit="W",
                min_size=5
            )
            display_themed_progress_bar(theme_data['GRAPH'], cpu_power)
            display_themed_radial_bar(
                theme_data=theme_data['RADIAL'],
                value=f'{cpu_power:.1f}',
                unit="W",
                min_size=5
            )
        display_themed_line_graph(theme_data['LINE_GRAPH'], cls.last_values_cpu_power)

    @classmethod
    def frequency(cls,forced_refresh = False):
        freq_ghz = sensors.Cpu.frequency() / 1000
        theme_data = config.THEME_DATA['STATS']['CPU']['FREQUENCY']

        if math.isnan(freq_ghz):
            freq_ghz = 0
            
        save_last_value(freq_ghz, cls.last_values_cpu_frequency,
                        theme_data['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))

        need_refresh = True
        if freq_ghz == cls.last_values_cpu_frequency[-2]:
            need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_value(
                theme_data=theme_data['TEXT'],
                value=f'{freq_ghz:.2f}',
                unit=" GHz",
                min_size=4
            )
            display_themed_progress_bar(theme_data['GRAPH'], freq_ghz)
            display_themed_radial_bar(
                theme_data=theme_data['RADIAL'],
                value=f'{freq_ghz:.2f}',
                unit="GHz",
                min_size=4
            )
        display_themed_line_graph(theme_data['LINE_GRAPH'], cls.last_values_cpu_frequency)

    @classmethod
    def load(cls):
        cpu_load = sensors.Cpu.load()
        # logger.debug(f"CPU Load: ({cpu_load[0]},{cpu_load[1]},{cpu_load[2]})")
        load_theme_data = config.THEME_DATA['STATS']['CPU']['LOAD']

        display_themed_percent_value(load_theme_data['ONE']['TEXT'], cpu_load[0])
        display_themed_percent_value(load_theme_data['FIVE']['TEXT'], cpu_load[1])
        display_themed_percent_value(load_theme_data['FIFTEEN']['TEXT'], cpu_load[2])

    @classmethod
    def temperature(cls,forced_refresh = False):
        temperature = sensors.Cpu.temperature(config.THEME_DATA['STATS']['CPU']['TEMPERATURE'].get("TEMP_TYPE", "Core"))
        save_last_value(temperature, cls.last_values_cpu_temperature,
                        config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['LINE_GRAPH'].get("HISTORY_SIZE",
                                                                                           DEFAULT_HISTORY_SIZE))

        cpu_temp_text_data = config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['TEXT']
        cpu_temp_radial_data = config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['RADIAL']
        cpu_temp_graph_data = config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['GRAPH']
        cpu_temp_line_graph_data = config.THEME_DATA['STATS']['CPU']['TEMPERATURE']['LINE_GRAPH']

        if math.isnan(temperature):
            temperature = 0
            if cpu_temp_text_data['SHOW'] or cpu_temp_radial_data['SHOW'] or cpu_temp_graph_data[
                'SHOW'] or cpu_temp_line_graph_data['SHOW']:
                logger.warning("Your CPU temperature is not supported yet")
                cpu_temp_text_data['SHOW'] = False
                cpu_temp_radial_data['SHOW'] = False
                cpu_temp_graph_data['SHOW'] = False
                cpu_temp_line_graph_data['SHOW'] = False
                return
            
        need_refresh = True
        if math.isnan(cls.last_values_cpu_temperature[-2]) == False:
            if int(temperature) == int(cls.last_values_cpu_temperature[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_temperature_value(cpu_temp_text_data, temperature)
            display_themed_progress_bar(cpu_temp_graph_data, temperature)
            display_themed_temperature_radial_bar(cpu_temp_radial_data, temperature)
        display_themed_line_graph(cpu_temp_line_graph_data, cls.last_values_cpu_temperature)

    @classmethod
    def fan_speed(cls,forced_refresh = False):
        if CPU_FAN != "AUTO":
            fan_percent = sensors.Cpu.fan_percent(CPU_FAN)
        else:
            fan_percent = sensors.Cpu.fan_percent()

        save_last_value(fan_percent, cls.last_values_cpu_fan_speed,
                        config.THEME_DATA['STATS']['CPU']['FAN_SPEED']['LINE_GRAPH'].get("HISTORY_SIZE",
                                                                                         DEFAULT_HISTORY_SIZE))

        cpu_fan_text_data = config.THEME_DATA['STATS']['CPU']['FAN_SPEED']['TEXT']
        cpu_fan_radial_data = config.THEME_DATA['STATS']['CPU']['FAN_SPEED']['RADIAL']
        cpu_fan_graph_data = config.THEME_DATA['STATS']['CPU']['FAN_SPEED']['GRAPH']
        cpu_fan_line_graph_data = config.THEME_DATA['STATS']['CPU']['FAN_SPEED']['LINE_GRAPH']

        if math.isnan(fan_percent):
            fan_percent = 0
            if cpu_fan_text_data['SHOW'] or cpu_fan_radial_data['SHOW'] or cpu_fan_graph_data[
                'SHOW'] or cpu_fan_line_graph_data['SHOW']:
                if sys.platform == "win32":
                    logger.warning("Your CPU Fan sensor could not be auto-detected")
                else:
                    logger.warning("Your CPU Fan sensor could not be auto-detected. Select it from Configuration UI.")
                cpu_fan_text_data['SHOW'] = False
                cpu_fan_radial_data['SHOW'] = False
                cpu_fan_graph_data['SHOW'] = False
                cpu_fan_line_graph_data['SHOW'] = False

        need_refresh = True
        if math.isnan(cls.last_values_cpu_fan_speed[-2]) == False:
            if int(fan_percent) == int(cls.last_values_cpu_fan_speed[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_percent_value(cpu_fan_text_data, fan_percent)
            display_themed_progress_bar(cpu_fan_graph_data, fan_percent)
            display_themed_percent_radial_bar(cpu_fan_radial_data, fan_percent)
        display_themed_line_graph(cpu_fan_line_graph_data, cls.last_values_cpu_fan_speed)


class Gpu:
    last_values_gpu_percentage = []
    last_values_gpu_mem_percentage = []
    last_values_gpu_temperature = []
    last_values_gpu_fps = []
    last_values_gpu_fan_speed = []
    last_values_gpu_frequency = []
    last_values_gpu_power = []
    last_memory_used_mb = -1
    last_total_memory_mb = -1
    @classmethod
    def stats(cls,forced_refresh = False):
        load, memory_percentage, memory_used_mb, total_memory_mb, temperature = sensors.Gpu.stats()
        fps = sensors.Gpu.fps()
        fan_percent = sensors.Gpu.fan_percent()
        freq_ghz = sensors.Gpu.frequency() / 1000

        theme_gpu_data = config.THEME_DATA['STATS']['GPU']

        save_last_value(load, cls.last_values_gpu_percentage,
                        theme_gpu_data['PERCENTAGE']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        save_last_value(memory_percentage, cls.last_values_gpu_mem_percentage,
                        theme_gpu_data['MEMORY_PERCENT']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        save_last_value(temperature, cls.last_values_gpu_temperature,
                        theme_gpu_data['TEMPERATURE']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        save_last_value(fps, cls.last_values_gpu_fps,
                        theme_gpu_data['FPS']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        save_last_value(fan_percent, cls.last_values_gpu_fan_speed,
                        theme_gpu_data['FAN_SPEED']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        save_last_value(freq_ghz, cls.last_values_gpu_frequency,
                        theme_gpu_data['FREQUENCY']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))

        # GPU usage (%)
        gpu_percent_graph_data = theme_gpu_data['PERCENTAGE']['GRAPH']
        gpu_percent_radial_data = theme_gpu_data['PERCENTAGE']['RADIAL']
        gpu_percent_text_data = theme_gpu_data['PERCENTAGE']['TEXT']
        gpu_percent_line_graph_data = theme_gpu_data['PERCENTAGE']['LINE_GRAPH']

        if math.isnan(load):
            load = 0
            if gpu_percent_graph_data['SHOW'] or gpu_percent_text_data['SHOW'] or gpu_percent_radial_data['SHOW'] or \
                    gpu_percent_line_graph_data['SHOW']:
                logger.warning("Your GPU load is not supported yet")
                gpu_percent_graph_data['SHOW'] = False
                gpu_percent_text_data['SHOW'] = False
                gpu_percent_radial_data['SHOW'] = False
                gpu_percent_line_graph_data['SHOW'] = False

        need_refresh = True
        if math.isnan(cls.last_values_gpu_percentage[-2]) == False:
            if int(load) == int(cls.last_values_gpu_percentage[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_progress_bar(gpu_percent_graph_data, load)
            display_themed_percent_radial_bar(gpu_percent_radial_data, load)
            display_themed_percent_value(gpu_percent_text_data, load)
        display_themed_line_graph(gpu_percent_line_graph_data, cls.last_values_gpu_percentage)

        # for backward compatibility only
        gpu_mem_graph_data = theme_gpu_data['MEMORY']['GRAPH']
        gpu_mem_radial_data = theme_gpu_data['MEMORY']['RADIAL']
        gpu_mem_text_data = theme_gpu_data['MEMORY']['TEXT']

        # GPU mem. usage (%)
        gpu_mem_percent_graph_data = theme_gpu_data['MEMORY_PERCENT']['GRAPH']
        gpu_mem_percent_radial_data = theme_gpu_data['MEMORY_PERCENT']['RADIAL']
        gpu_mem_percent_text_data = theme_gpu_data['MEMORY_PERCENT']['TEXT']
        gpu_mem_percent_line_graph_data = theme_gpu_data['MEMORY_PERCENT']['LINE_GRAPH']

        if math.isnan(memory_percentage):
            memory_percentage = 0
            if gpu_mem_percent_graph_data['SHOW'] or gpu_mem_percent_radial_data['SHOW'] or gpu_mem_percent_text_data[
                'SHOW'] or gpu_mem_percent_line_graph_data['SHOW']:
                logger.warning("Your GPU memory relative usage (%) is not supported yet")
                gpu_mem_percent_graph_data['SHOW'] = False
                gpu_mem_percent_radial_data['SHOW'] = False
                gpu_mem_percent_text_data['SHOW'] = False
            # for backward compatibility only
            if gpu_mem_graph_data['SHOW'] or gpu_mem_radial_data['SHOW']:
                logger.warning("Your GPU memory relative usage (%) is not supported yet")
                gpu_mem_graph_data['SHOW'] = False
                gpu_mem_radial_data['SHOW'] = False

        need_refresh = True
        if math.isnan(cls.last_values_gpu_mem_percentage[-2]) == False:
            if int(memory_percentage) == int(cls.last_values_gpu_mem_percentage[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_progress_bar(gpu_mem_percent_graph_data, memory_percentage)
            display_themed_percent_radial_bar(gpu_mem_percent_radial_data, memory_percentage)
            display_themed_percent_value(gpu_mem_percent_text_data, memory_percentage)
            # for backward compatibility only
            display_themed_progress_bar(gpu_mem_graph_data, memory_percentage)
            display_themed_percent_radial_bar(gpu_mem_radial_data, memory_percentage)

        display_themed_line_graph(gpu_mem_percent_line_graph_data, cls.last_values_gpu_mem_percentage)

        # GPU mem. absolute usage (M)
        gpu_mem_used_text_data = theme_gpu_data['MEMORY_USED']['TEXT']
        if math.isnan(memory_used_mb):
            memory_used_mb = 0
            if gpu_mem_used_text_data['SHOW']:
                logger.warning("Your GPU memory absolute usage (M) is not supported yet")
                gpu_mem_used_text_data['SHOW'] = False
            # for backward compatibility only
            if gpu_mem_text_data['SHOW']:
                logger.warning("Your GPU memory absolute usage (M) is not supported yet")
                gpu_mem_text_data['SHOW'] = False

        memory_used_mb_t = int(memory_used_mb)
        if cls.last_memory_used_mb != memory_used_mb_t or forced_refresh:
            cls.last_memory_used_mb = memory_used_mb_t
            display_themed_value(
                theme_data=gpu_mem_used_text_data,
                value=memory_used_mb_t,
                min_size=5,
                unit=" M"
            )
            # for backward compatibility only
            display_themed_value(
                theme_data=gpu_mem_text_data,
                value=memory_used_mb_t,
                min_size=5,
                unit=" M"
            )

        # GPU mem. total memory (M)
        gpu_mem_total_text_data = theme_gpu_data['MEMORY_TOTAL']['TEXT']
        if math.isnan(total_memory_mb):
            total_memory_mb = 0
            if gpu_mem_total_text_data['SHOW']:
                logger.warning("Your GPU total memory capacity (M) is not supported yet")
                gpu_mem_total_text_data['SHOW'] = False

        total_memory_mb_t = int(total_memory_mb)
        if cls.last_total_memory_mb != total_memory_mb_t or forced_refresh:
            cls.last_total_memory_mb = total_memory_mb_t
            display_themed_value(
                theme_data=gpu_mem_total_text_data,
                value=total_memory_mb_t,
                min_size=5,  # Adjust min_size as necessary for your display
                unit=" M"  # Assuming the unit is in Megabytes
            )

        # GPU temperature (°C)
        gpu_temp_text_data = theme_gpu_data['TEMPERATURE']['TEXT']
        gpu_temp_radial_data = theme_gpu_data['TEMPERATURE']['RADIAL']
        gpu_temp_graph_data = theme_gpu_data['TEMPERATURE']['GRAPH']
        gpu_temp_line_graph_data = theme_gpu_data['TEMPERATURE']['LINE_GRAPH']

        if math.isnan(temperature):
            temperature = 0
            if gpu_temp_text_data['SHOW'] or gpu_temp_radial_data['SHOW'] or gpu_temp_graph_data[
                'SHOW'] or gpu_temp_line_graph_data['SHOW']:
                logger.warning("Your GPU temperature is not supported yet")
                gpu_temp_text_data['SHOW'] = False
                gpu_temp_radial_data['SHOW'] = False
                gpu_temp_graph_data['SHOW'] = False
                gpu_temp_line_graph_data['SHOW'] = False

        need_refresh = True
        if math.isnan(cls.last_values_gpu_temperature[-2]) == False:
            if int(temperature) == int(cls.last_values_gpu_temperature[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_temperature_value(gpu_temp_text_data, temperature)
            display_themed_progress_bar(gpu_temp_graph_data, temperature)
            display_themed_temperature_radial_bar(gpu_temp_radial_data, temperature)
        display_themed_line_graph(gpu_temp_line_graph_data, cls.last_values_gpu_temperature)

        # GPU FPS
        gpu_fps_text_data = theme_gpu_data['FPS']['TEXT']
        gpu_fps_radial_data = theme_gpu_data['FPS']['RADIAL']
        gpu_fps_graph_data = theme_gpu_data['FPS']['GRAPH']
        gpu_fps_line_graph_data = theme_gpu_data['FPS']['LINE_GRAPH']

        if fps < 0:
            fps = 0
            if gpu_fps_text_data['SHOW'] or gpu_fps_radial_data['SHOW'] or gpu_fps_graph_data[
                'SHOW'] or gpu_fps_line_graph_data['SHOW']:
                logger.warning("Your GPU FPS is not supported yet")
                gpu_fps_text_data['SHOW'] = False
                gpu_fps_radial_data['SHOW'] = False
                gpu_fps_graph_data['SHOW'] = False
                gpu_fps_line_graph_data['SHOW'] = False

        if math.isnan(cls.last_values_gpu_fps[-2]) == False:
            if int(fps) == int(cls.last_values_gpu_fps[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_progress_bar(gpu_fps_graph_data, fps)
            display_themed_value(
                theme_data=gpu_fps_text_data,
                value=int(fps),
                min_size=4,
                unit=" FPS"
            )
            display_themed_radial_bar(
                theme_data=gpu_fps_radial_data,
                value=int(fps),
                min_size=4,
                unit="FPS"
            )
        display_themed_line_graph(gpu_fps_line_graph_data, cls.last_values_gpu_fps)

        # GPU Fan Speed (%)
        gpu_fan_text_data = theme_gpu_data['FAN_SPEED']['TEXT']
        gpu_fan_radial_data = theme_gpu_data['FAN_SPEED']['RADIAL']
        gpu_fan_graph_data = theme_gpu_data['FAN_SPEED']['GRAPH']
        gpu_fan_line_graph_data = theme_gpu_data['FAN_SPEED']['LINE_GRAPH']

        if math.isnan(fan_percent):
            fan_percent = 0
            if gpu_fan_text_data['SHOW'] or gpu_fan_radial_data['SHOW'] or gpu_fan_graph_data[
                'SHOW'] or gpu_fan_line_graph_data['SHOW']:
                logger.warning("Your GPU Fan Speed is not supported yet")
                gpu_fan_text_data['SHOW'] = False
                gpu_fan_radial_data['SHOW'] = False
                gpu_fan_graph_data['SHOW'] = False
                gpu_fan_line_graph_data['SHOW'] = False
                
        if math.isnan(cls.last_values_gpu_fan_speed[-2]) == False:
            if int(fan_percent) == int(cls.last_values_gpu_fan_speed[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_percent_value(gpu_fan_text_data, fan_percent)
            display_themed_progress_bar(gpu_fan_graph_data, fan_percent)
            display_themed_percent_radial_bar(gpu_fan_radial_data, fan_percent)
        display_themed_line_graph(gpu_fan_line_graph_data, cls.last_values_gpu_fan_speed)

        # GPU Frequency (Ghz)
        gpu_freq_text_data = theme_gpu_data['FREQUENCY']['TEXT']
        gpu_freq_radial_data = theme_gpu_data['FREQUENCY']['RADIAL']
        gpu_freq_graph_data = theme_gpu_data['FREQUENCY']['GRAPH']
        gpu_freq_line_graph_data = theme_gpu_data['FREQUENCY']['LINE_GRAPH']
        if math.isnan(freq_ghz):
            freq_ghz = 0
            if gpu_freq_text_data['SHOW'] or gpu_freq_radial_data['SHOW'] or gpu_freq_graph_data[
                'SHOW'] or gpu_freq_line_graph_data['SHOW']:
                logger.warning("Your GPU Frequency (Ghz) is not supported yet")
                gpu_freq_text_data['SHOW'] = False
                gpu_freq_radial_data['SHOW'] = False
                gpu_freq_graph_data['SHOW'] = False
                gpu_freq_line_graph_data['SHOW'] = False

        if math.isnan(cls.last_values_gpu_frequency[-2]) == False:
            if int(freq_ghz) == int(cls.last_values_gpu_frequency[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_value(
                theme_data=gpu_freq_text_data,
                value=f'{freq_ghz:.2f}',
                unit=" GHz",
                min_size=4
            )
            display_themed_progress_bar(gpu_freq_graph_data, freq_ghz)
            display_themed_radial_bar(
                theme_data=gpu_freq_radial_data,
                value=f'{freq_ghz:.2f}',
                unit="GHz",
                min_size=4
            )
        display_themed_line_graph(gpu_freq_line_graph_data, cls.last_values_gpu_frequency)

        # GPU Power (W)
        theme_data = theme_gpu_data['POWER']
        gpu_power = sensors.Gpu.power()
        if math.isnan(gpu_power):
            gpu_power = 0

        save_last_value(gpu_power, cls.last_values_gpu_power,
                        theme_data['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        
        need_refresh = True
        if math.isnan(cls.last_values_gpu_power[-2]) == False:
            if int(gpu_power) == int(cls.last_values_gpu_power[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_value(
                theme_data=theme_data['TEXT'],
                value=f'{gpu_power:.1f}',
                unit="W",
                min_size=5
            )
            display_themed_progress_bar(theme_data['GRAPH'], gpu_power)
            display_themed_radial_bar(
                theme_data=theme_data['RADIAL'],
                value=f'{gpu_power:.1f}',
                unit="W",
                min_size=5
            )
        display_themed_line_graph(theme_data['LINE_GRAPH'], cls.last_values_gpu_power)

    @staticmethod
    def is_available():
        return sensors.Gpu.is_available()


class Memory:
    last_values_memory_swap = []
    last_values_memory_virtual = []
    last_values_memory_total = []
    last_virtual_used = -1
    last_virtual_free = -1
    last_virtual_total = -1
    last_total_used = -1
    last_total_free = -1
    last_total_total = -1
    @classmethod
    def stats(cls,forced_refresh = False):
        memory_stats_theme_data = config.THEME_DATA['STATS']['MEMORY']

        swap_percent = sensors.Memory.swap_percent()
        save_last_value(swap_percent, cls.last_values_memory_swap,
                        memory_stats_theme_data['SWAP']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        need_refresh = True
        if math.isnan(cls.last_values_memory_swap[-2]) == False:
            if int(swap_percent) == int(cls.last_values_memory_swap[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_progress_bar(memory_stats_theme_data['SWAP']['GRAPH'], swap_percent)
            display_themed_percent_radial_bar(memory_stats_theme_data['SWAP']['RADIAL'], swap_percent)
        display_themed_line_graph(memory_stats_theme_data['SWAP']['LINE_GRAPH'], cls.last_values_memory_swap)

        virtual_percent = sensors.Memory.virtual_percent()
        save_last_value(virtual_percent, cls.last_values_memory_virtual,
                        memory_stats_theme_data['VIRTUAL']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        need_refresh = True
        if math.isnan(cls.last_values_memory_virtual[-2]) == False:
            if int(virtual_percent) == int(cls.last_values_memory_virtual[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_progress_bar(memory_stats_theme_data['VIRTUAL']['GRAPH'], virtual_percent)
            display_themed_percent_radial_bar(memory_stats_theme_data['VIRTUAL']['RADIAL'], virtual_percent)
            display_themed_percent_value(memory_stats_theme_data['VIRTUAL']['PERCENT_TEXT'], virtual_percent)
        display_themed_line_graph(memory_stats_theme_data['VIRTUAL']['LINE_GRAPH'], cls.last_values_memory_virtual)

        virtual_used = sensors.Memory.virtual_used()
        virtual_free = sensors.Memory.virtual_free()
        virtual_total = virtual_used + virtual_free
        
        if virtual_used != cls.last_virtual_used or forced_refresh:
            cls.last_virtual_used = virtual_used
            display_themed_value(
                theme_data=memory_stats_theme_data['VIRTUAL']['USED'],
                value=virtual_used,
                min_size=5,
                unit=" M"
            )
        
        if virtual_free != cls.last_virtual_free or forced_refresh:
            cls.last_virtual_free = virtual_free
            display_themed_value(
                theme_data=memory_stats_theme_data['VIRTUAL']['FREE'],
                value=virtual_free,
                min_size=5,
                unit=" M"
            )

        if virtual_total != cls.last_virtual_total or forced_refresh:
            cls.last_virtual_total = virtual_total
            display_themed_value(
                theme_data=memory_stats_theme_data['VIRTUAL']['TOTAL'],
                value=virtual_total,
                min_size=5,
                unit=" M"
            )

        total_percent = sensors.Memory.total_percent()
        save_last_value(total_percent, cls.last_values_memory_total,
                        memory_stats_theme_data['TOTAL']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        need_refresh = True
        if math.isnan(cls.last_values_memory_total[-2]) == False:
            if int(total_percent) == int(cls.last_values_memory_total[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_progress_bar(memory_stats_theme_data['TOTAL']['GRAPH'], total_percent)
            display_themed_percent_radial_bar(memory_stats_theme_data['TOTAL']['RADIAL'], total_percent)
            display_themed_percent_value(memory_stats_theme_data['TOTAL']['PERCENT_TEXT'], total_percent)
        display_themed_line_graph(memory_stats_theme_data['TOTAL']['LINE_GRAPH'], cls.last_values_memory_total)

        total_used = sensors.Memory.total_used()
        total_free = sensors.Memory.total_free()
        total_total = total_used + total_free
        
        if total_used != cls.last_total_used or forced_refresh:
            cls.last_total_used = total_used
            display_themed_value(
                theme_data=memory_stats_theme_data['TOTAL']['USED'],
                value=total_used,
                min_size=5,
                unit=" M"
            )
        
        if total_free != cls.last_total_free or forced_refresh:
            cls.last_total_free = total_free
            display_themed_value(
                theme_data=memory_stats_theme_data['TOTAL']['FREE'],
                value=total_free,
                min_size=5,
                unit=" M"
            )
            
        if total_total != cls.last_total_total or forced_refresh:
            cls.last_total_total = total_total
            display_themed_value(
                theme_data=memory_stats_theme_data['TOTAL']['TOTAL'],
                value=total_total,
                min_size=5,
                unit=" M"
            )

class Disk:
    last_values_disk_usage = []
    last_used = -1
    last_free = -1
    last_total = -1
    @classmethod
    def stats(cls,forced_refresh = False):
        used,free,percent = sensors.Disk.disk_used_free_and_usage_percent()
        used = int(used / (1024*1024*1024))
        free = int(free / (1024*1024*1024))
        usage_percent = percent
        total = free + used

        disk_theme_data = config.THEME_DATA['STATS']['DISK']

        
        save_last_value(usage_percent, cls.last_values_disk_usage,
                        disk_theme_data['USED']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        need_refresh = True
        if math.isnan(cls.last_values_disk_usage[-2]) == False:
            if int(usage_percent) == int(cls.last_values_disk_usage[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_progress_bar(disk_theme_data['USED']['GRAPH'], usage_percent)
            display_themed_percent_radial_bar(disk_theme_data['USED']['RADIAL'], usage_percent)
            display_themed_percent_value(disk_theme_data['USED']['PERCENT_TEXT'], usage_percent)
        display_themed_line_graph(disk_theme_data['USED']['LINE_GRAPH'], cls.last_values_disk_usage)

        if used != cls.last_used or forced_refresh:
            cls.last_used = used
            display_themed_value(
                theme_data=disk_theme_data['USED']['TEXT'],
                value=used,
                min_size=5,
                unit=" G"
            )

        if free != cls.last_free or forced_refresh:
            cls.last_free = free
            display_themed_value(
                theme_data=disk_theme_data['FREE']['TEXT'],
                value=free,
                min_size=5,
                unit=" G"
            )

        if total != cls.last_total or forced_refresh:
            cls.last_total = total
            display_themed_value(
                theme_data=disk_theme_data['TOTAL']['TEXT'],
                value=total,
                min_size=5,
                unit=" G"
            )


class Net:
    last_values_wlo_upload = []
    last_values_wlo_download = []
    last_values_eth_upload = []
    last_values_eth_download = []

    @classmethod
    def stats(cls):
        net_theme_data = config.THEME_DATA['STATS']['NET']
        interval = net_theme_data.get("INTERVAL", None)
        upload_wlo, uploaded_wlo, download_wlo, downloaded_wlo = sensors.Net.stats(WLO_CARD, interval)

        save_last_value(upload_wlo, cls.last_values_wlo_upload,
                        net_theme_data['WLO']['UPLOAD']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        Net._show_themed_tax_rate(net_theme_data['WLO']['UPLOAD']['TEXT'], upload_wlo)
        Net._show_themed_total_data(net_theme_data['WLO']['UPLOADED']['TEXT'], uploaded_wlo)
        display_themed_line_graph(net_theme_data['WLO']['UPLOAD']['LINE_GRAPH'], cls.last_values_wlo_upload)

        save_last_value(download_wlo, cls.last_values_wlo_download,
                        net_theme_data['WLO']['DOWNLOAD']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        Net._show_themed_tax_rate(net_theme_data['WLO']['DOWNLOAD']['TEXT'], download_wlo)
        Net._show_themed_total_data(net_theme_data['WLO']['DOWNLOADED']['TEXT'], downloaded_wlo)
        display_themed_line_graph(net_theme_data['WLO']['DOWNLOAD']['LINE_GRAPH'], cls.last_values_wlo_download)
        upload_eth, uploaded_eth, download_eth, downloaded_eth = sensors.Net.stats(ETH_CARD, interval)

        save_last_value(upload_eth, cls.last_values_eth_upload,
                        net_theme_data['ETH']['UPLOAD']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        Net._show_themed_tax_rate(net_theme_data['ETH']['UPLOAD']['TEXT'], upload_eth)
        Net._show_themed_total_data(net_theme_data['ETH']['UPLOADED']['TEXT'], uploaded_eth)
        display_themed_line_graph(net_theme_data['ETH']['UPLOAD']['LINE_GRAPH'], cls.last_values_eth_upload)

        save_last_value(download_eth, cls.last_values_eth_download,
                        net_theme_data['ETH']['DOWNLOAD']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        Net._show_themed_tax_rate(net_theme_data['ETH']['DOWNLOAD']['TEXT'], download_eth)
        Net._show_themed_total_data(net_theme_data['ETH']['DOWNLOADED']['TEXT'], downloaded_eth)
        display_themed_line_graph(net_theme_data['ETH']['DOWNLOAD']['LINE_GRAPH'], cls.last_values_eth_download)
        
    @staticmethod
    def _show_themed_total_data(theme_data, amount):
        display_themed_value(
            theme_data=theme_data,
            value=f"{bytes2human(amount)}",
            min_size=6
        )

    @staticmethod
    def _show_themed_tax_rate(theme_data, rate):
        value = f"{bytes2human(rate, '%(value).1f %(symbol)s/s')}"
        value_split = value.split(' ')
        rate = value_split[0]
        unit = value_split[1]
        display_themed_value(
            theme_data=theme_data,
            value=rate,
            unit=unit,
            min_size=10
        )


class Date:
    last_data_date = 0
    @classmethod
    def stats(cls,forced_refresh = False):
        # if HW_SENSORS == "STATIC":
        #     # For static sensors, use predefined date/time
        #     date_now = datetime.datetime.fromtimestamp(1694014609)
        # else:
        date_now = datetime.datetime.now()
        
        if platform.system() == "Windows":
            # Windows does not have LC_TIME environment variable, use deprecated getdefaultlocale() that returns language code following RFC 1766
            lc_time = locale.getdefaultlocale()[0]
        else:
            lc_time = babel.dates.LC_TIME
        date_theme_data = config.THEME_DATA['STATS']['DATE']

        day_theme_data = date_theme_data['DAY']['TEXT']
        date_format = day_theme_data.get("FORMAT", 'medium')
        if cls.last_data_date != date_now.date() or forced_refresh:
            cls.last_data_date = date_now.date()
            display_themed_value(
                theme_data=day_theme_data,
                value=f"{babel.dates.format_date(date_now, format=date_format, locale=lc_time)}"
            )

        hour_theme_data = date_theme_data['HOUR']['TEXT']
        time_format = hour_theme_data.get("FORMAT", 'medium')
        display_themed_value(
            theme_data=hour_theme_data,
            value=f"{babel.dates.format_time(date_now, format=time_format, locale=lc_time)}"
        )


class SystemUptime:
    @staticmethod
    def stats():
        if HW_SENSORS == "STATIC":
            # For static sensors, use predefined uptime
            uptimesec = 4294036
        else:
            uptimesec = int(uptime())

        uptimeformatted = str(datetime.timedelta(seconds=uptimesec))

        systemuptime_theme_data = config.THEME_DATA['STATS']['UPTIME']

        systemuptime_sec_theme_data = systemuptime_theme_data['SECONDS']['TEXT']
        display_themed_value(
            theme_data=systemuptime_sec_theme_data,
            value=uptimesec
        )

        systemuptime_formatted_theme_data = systemuptime_theme_data['FORMATTED']['TEXT']
        display_themed_value(
            theme_data=systemuptime_formatted_theme_data,
            value=uptimeformatted
        )


class Custom:
    @staticmethod
    def stats():
        for custom_stat in config.THEME_DATA['STATS']['CUSTOM']:
            if custom_stat != "INTERVAL":

                # Load the custom sensor class from sensors_custom.py based on the class name
                try:
                    custom_stat_class = getattr(sensors_custom, str(custom_stat))()
                    numeric_value = custom_stat_class.as_numeric()
                    string_value = custom_stat_class.as_string()
                    last_values = custom_stat_class.last_values()
                except Exception as e:
                    logger.error(
                        "Error loading custom sensor class " + str(custom_stat) + " from sensors_custom.py : " + str(e))
                    return

                if string_value is None:
                    string_value = str(numeric_value)

                # Display text
                theme_data = config.THEME_DATA['STATS']['CUSTOM'][custom_stat].get("TEXT", None)
                if theme_data is not None and string_value is not None:
                    display_themed_value(theme_data=theme_data, value=string_value)

                # Display graph from numeric value
                theme_data = config.THEME_DATA['STATS']['CUSTOM'][custom_stat].get("GRAPH", None)
                if theme_data is not None and numeric_value is not None and not math.isnan(numeric_value):
                    display_themed_progress_bar(theme_data=theme_data, value=numeric_value)

                # Display radial from numeric and text value
                theme_data = config.THEME_DATA['STATS']['CUSTOM'][custom_stat].get("RADIAL", None)
                if theme_data is not None and numeric_value is not None and not math.isnan(
                        numeric_value) and string_value is not None:
                    display_themed_radial_bar(
                        theme_data=theme_data,
                        value=numeric_value,
                        custom_text=string_value
                    )

                # Display plot graph from histo values
                theme_data = config.THEME_DATA['STATS']['CUSTOM'][custom_stat].get("LINE_GRAPH", None)
                if theme_data is not None and last_values is not None:
                    display_themed_line_graph(theme_data=theme_data, values=last_values)
                    
class Volume:
    last_volume_percent = -1
    @classmethod
    def stats(cls,forced_refresh = False):
        volume_theme_data = config.THEME_DATA['STATS']['VOLUME']

        volume_percent = sensors.Volume.volume_percent()

        if volume_percent != cls.last_volume_percent or forced_refresh:
            cls.last_volume_percent = volume_percent
            display_themed_progress_bar(volume_theme_data['GRAPH'], volume_percent)
            display_themed_percent_radial_bar(volume_theme_data['RADIAL'], volume_percent)
            display_themed_percent_value(volume_theme_data['PERCENT_TEXT'], volume_percent)

class LcdSensor:
    last_values_temperature = []
    last_values_humidness = []
    _temperature = 0
    _humidness = 0
    @classmethod
    def temperature(cls,forced_refresh = False):
        save_last_value(cls._temperature, cls.last_values_temperature,
                        config.THEME_DATA['STATS']['LCD_SENSOR']['TEMPERATURE']['LINE_GRAPH'].get("HISTORY_SIZE",
                                                                                           DEFAULT_HISTORY_SIZE))

        temp_text_data = config.THEME_DATA['STATS']['LCD_SENSOR']['TEMPERATURE']['TEXT']
        temp_radial_data = config.THEME_DATA['STATS']['LCD_SENSOR']['TEMPERATURE']['RADIAL']
        temp_graph_data = config.THEME_DATA['STATS']['LCD_SENSOR']['TEMPERATURE']['GRAPH']
        temp_line_graph_data = config.THEME_DATA['STATS']['LCD_SENSOR']['TEMPERATURE']['LINE_GRAPH']

        if math.isnan(cls._temperature):
            cls._temperature = 0
            if temp_text_data['SHOW'] or temp_radial_data['SHOW'] or temp_graph_data[
                'SHOW'] or temp_line_graph_data['SHOW']:
                logger.warning("Your CPU temperature is not supported yet")
                temp_text_data['SHOW'] = False
                temp_radial_data['SHOW'] = False
                temp_graph_data['SHOW'] = False
                temp_line_graph_data['SHOW'] = False

        need_refresh = True
        if math.isnan(cls.last_values_temperature[-2]) == False:
            if int(cls._temperature) == int(cls.last_values_temperature[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_value(
                theme_data=temp_text_data,
                value=f'{cls._temperature:.1f}',
                unit="°C",
                min_size=5
            )
            display_themed_progress_bar(temp_graph_data, cls._temperature)
            display_themed_radial_bar(
                theme_data=temp_radial_data,
                value=f'{cls._temperature:.1f}',
                unit="°C",
                min_size=5
            )
        display_themed_line_graph(temp_line_graph_data, cls.last_values_temperature)

    @classmethod
    def humidness(cls,forced_refresh = False):
        save_last_value(cls._humidness, cls.last_values_humidness,
                        config.THEME_DATA['STATS']['LCD_SENSOR']['HUMIDNESS']['LINE_GRAPH'].get("HISTORY_SIZE",
                                                                                           DEFAULT_HISTORY_SIZE))

        humid_text_data = config.THEME_DATA['STATS']['LCD_SENSOR']['HUMIDNESS']['TEXT']
        humid_radial_data = config.THEME_DATA['STATS']['LCD_SENSOR']['HUMIDNESS']['RADIAL']
        humid_graph_data = config.THEME_DATA['STATS']['LCD_SENSOR']['HUMIDNESS']['GRAPH']
        humid_line_graph_data = config.THEME_DATA['STATS']['LCD_SENSOR']['HUMIDNESS']['LINE_GRAPH']

        if math.isnan(cls._humidness):
            cls._humidness = 0
            if humid_text_data['SHOW'] or humid_radial_data['SHOW'] or humid_graph_data[
                'SHOW'] or humid_line_graph_data['SHOW']:
                logger.warning("Your humidness is not supported yet")
                humid_text_data['SHOW'] = False
                humid_radial_data['SHOW'] = False
                humid_graph_data['SHOW'] = False
                humid_line_graph_data['SHOW'] = False

        need_refresh = True
        if math.isnan(cls.last_values_humidness[-2]) == False:
            if int(cls._humidness) == int(cls.last_values_humidness[-2]):
                need_refresh = False
        if need_refresh or forced_refresh:
            display_themed_value(
                theme_data=humid_text_data,
                value=f'{cls._humidness:.1f}',
                unit="%",
                min_size=5
            )
            display_themed_progress_bar(humid_graph_data, cls._humidness)
            display_themed_radial_bar(
                theme_data=humid_radial_data,
                value=f'{cls._humidness:.1f}',
                unit="%",
                min_size=5
            )
        display_themed_line_graph(humid_line_graph_data, cls.last_values_humidness)
    
    @classmethod
    def handle(cls):
        try:
            cls._temperature,cls._humidness = display.lcd.HandleSensorReport()
        except:
            cls._temperature = 0
            cls._humidness = 0

class Weather:
    @staticmethod
    def stats():
        weather_theme_data = config.THEME_DATA['STATS'].get('WEATHER', {})
        wtemperature_theme_data = weather_theme_data.get('TEMPERATURE', {}).get('TEXT', {})
        wfelt_theme_data = weather_theme_data.get('TEMPERATURE_FELT', {}).get('TEXT', {})
        wupdatetime_theme_data = weather_theme_data.get('UPDATE_TIME', {}).get('TEXT', {})
        wdescription_theme_data = weather_theme_data.get('WEATHER_DESCRIPTION', {}).get('TEXT', {})
        whumidity_theme_data = weather_theme_data.get('HUMIDITY', {}).get('TEXT', {})

        activate = True if wtemperature_theme_data.get("SHOW") or wfelt_theme_data.get(
            "SHOW") or wupdatetime_theme_data.get("SHOW") or wdescription_theme_data.get(
            "SHOW") or whumidity_theme_data.get("SHOW") else False

        if activate:
            temp = None
            feel = None
            time = None
            humidity = None
            if HW_SENSORS in ["STATIC", "STUB"]:
                temp = "17.5°C"
                feel = "(17.2°C)"
                desc = "Cloudy"
                time = "@15:33"
                humidity = "45%"
            else:
                # API Parameters
                lat = config.CONFIG_DATA['config'].get('WEATHER_LATITUDE', "")
                lon = config.CONFIG_DATA['config'].get('WEATHER_LONGITUDE', "")
                api_key = config.CONFIG_DATA['config'].get('WEATHER_API_KEY', "")
                units = config.CONFIG_DATA['config'].get('WEATHER_UNITS', "metric")
                lang = config.CONFIG_DATA['config'].get('WEATHER_LANGUAGE', "en")
                temp, feel, desc, humidity, time, result = utils.get_weather(lat, lon, api_key, units, lang)
                if not result:
                    desc = "Error"
        if activate:
            # Display Temperature
            display_themed_value(theme_data=wtemperature_theme_data, value=temp)
            # Display Temperature Felt
            display_themed_value(theme_data=wfelt_theme_data, value=feel)
            # Display Update Time
            display_themed_value(theme_data=wupdatetime_theme_data, value=time)
            # Display Humidity
            display_themed_value(theme_data=whumidity_theme_data, value=humidity)
            # Display Weather Description (or error message)
            display_themed_value(theme_data=wdescription_theme_data, value=desc)


class Ping:
    last_values_ping = []

    @classmethod
    def stats(cls):
        theme_data = config.THEME_DATA['STATS']['PING']

        if HW_SENSORS in ["STATIC", "STUB"]:
            delay = 10.25
        else:
            delay = utils.get_ping_delay(config.CONFIG_DATA["config"].get("PING", "127.0.0.1"))

        save_last_value(delay, cls.last_values_ping,
                        theme_data['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))

        display_themed_progress_bar(theme_data['GRAPH'], delay)
        display_themed_radial_bar(
            theme_data=theme_data['RADIAL'],
            value=f"{delay:.2f}",
            unit="ms",
            min_size=6
        )
        display_themed_value(
            theme_data=theme_data['TEXT'],
            value=f"{delay:.2f}",
            unit="ms",
            min_size=2
        )
        display_themed_line_graph(theme_data['LINE_GRAPH'], cls.last_values_ping)

class InputMonitor:
    handle = None
    last_values_mouse_click_count = []
    last_values_keyboard_press_count = []
    @classmethod
    def stats(cls,forced_refresh = False):
        mouse_click_count = 0
        keyboard_press_count = 0
        if HW_SENSORS in ["STATIC", "STUB"]:
            mouse_click_count = 99999
            keyboard_press_count = 99999
        else:
            if cls.handle is None:
                try:
                    cls.handle = utils.InputMonitor()
                    cls.handle.start()
                except:
                    cls.handle = None
                    logger.error("Error initializing input monitor")
            else:
                mouse_click_count = cls.handle.get_mouse_press_count()
                keyboard_press_count = cls.handle.get_key_press_count()
        theme_data = config.THEME_DATA['STATS']['INPUT_MONITOR']
        save_last_value(mouse_click_count, cls.last_values_mouse_click_count,
                        theme_data['MOUSE_CLICK_COUNT']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        save_last_value(keyboard_press_count, cls.last_values_keyboard_press_count,
                        theme_data['KEYBOARD_PRESS_COUNT']['LINE_GRAPH'].get("HISTORY_SIZE", DEFAULT_HISTORY_SIZE))
        if cls.last_values_mouse_click_count[-2] != mouse_click_count or forced_refresh:
            display_themed_value(theme_data=theme_data['MOUSE_CLICK_COUNT']['TEXT'], value=mouse_click_count, unit=" t",min_size=8)
        if cls.last_values_keyboard_press_count[-2]!= keyboard_press_count or forced_refresh:
            display_themed_value(theme_data=theme_data['KEYBOARD_PRESS_COUNT']['TEXT'], value=keyboard_press_count, unit=" t",min_size=8)
        display_themed_line_graph(theme_data['MOUSE_CLICK_COUNT']['LINE_GRAPH'], cls.last_values_mouse_click_count)
        display_themed_line_graph(theme_data['KEYBOARD_PRESS_COUNT']['LINE_GRAPH'], cls.last_values_keyboard_press_count)
    
    @classmethod
    def stop(cls):
        if cls.handle is not None:
            print("Stopping input monitor")
            cls.handle.stop()
            cls.handle = None