# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
# Copyright (C) 2022-2023  Rollbacke
# Copyright (C) 2022-2023  Ebag333
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

import sched
import threading
import time
from datetime import timedelta
from functools import wraps

import lib.config as config
import lib.stats as stats
import lib.dynamic_images as dynamic_images
import lib.dynamic_texts as dynamic_texts
import lib.photo_album as photo_album
import lib.requests_get as requests_get
import lib.media_get as media_get

STOPPING = False

def async_job(threadname=None):
    """ wrapper to handle asynchronous threads """

    def decorator(func):
        """ Decorator to extend async_func """

        @wraps(func)
        def async_func(*args, **kwargs):
            """ create an asynchronous function to wrap around our thread """
            func_hl = threading.Thread(target=func, name=threadname, args=args, kwargs=kwargs)
            func_hl.start()
            return func_hl

        return async_func

    return decorator


def schedule(interval):
    """ wrapper to schedule asynchronous threads """

    def decorator(func):
        """ Decorator to extend periodic """

        def periodic(scheduler, periodic_interval, action, actionargs=()):
            """ Wrap the scheduler with our periodic interval """
            global STOPPING
            if not STOPPING:
                # If the program is not stopping: re-schedule the task for future execution
                scheduler.enter(periodic_interval, 1, periodic,
                                (scheduler, periodic_interval, action, actionargs))
            action(*actionargs)

        @wraps(func)
        def wrap(
                *args,
                **kwargs
        ):
            """ Wrapper to create our schedule and run it at the appropriate time """
            if interval == 0:
                return
            scheduler = sched.scheduler(time.time, time.sleep)
            periodic(scheduler, interval, func)
            scheduler.run()

        return wrap

    return decorator


@async_job("CPU_Percentage")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['CPU']['PERCENTAGE'].get("INTERVAL", 0)).total_seconds())
def CPUPercentage():
    """ Refresh the CPU Percentage """
    # logger.debug("Refresh CPU Percentage")
    stats.CPU.percentage()

@async_job("CPU_Power")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['CPU']['POWER'].get("INTERVAL", 0)).total_seconds())
def CPUPower():
    """ Refresh the CPU Power """
    # logger.debug("Refresh CPU Power")
    stats.CPU.power()


@async_job("CPU_Frequency")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['CPU']['FREQUENCY'].get("INTERVAL", 0)).total_seconds())
def CPUFrequency():
    """ Refresh the CPU Frequency """
    # logger.debug("Refresh CPU Frequency")
    stats.CPU.frequency()


@async_job("CPU_Load")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['CPU']['LOAD'].get("INTERVAL", 0)).total_seconds())
def CPULoad():
    """ Refresh the CPU Load """
    # logger.debug("Refresh CPU Load")
    stats.CPU.load()


@async_job("CPU_Load")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['CPU']['TEMPERATURE'].get("INTERVAL", 0)).total_seconds())
def CPUTemperature():
    """ Refresh the CPU Temperature """
    # logger.debug("Refresh CPU Temperature")
    stats.CPU.temperature()


@async_job("CPU_FanSpeed")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['CPU']['FAN_SPEED'].get("INTERVAL", 0)).total_seconds())
def CPUFanSpeed():
    """ Refresh the CPU Fan Speed """
    # logger.debug("Refresh CPU Fan Speed")
    stats.CPU.fan_speed()


@async_job("GPU_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['GPU'].get("INTERVAL", 0)).total_seconds())
def GpuStats():
    """ Refresh the GPU Stats """
    # logger.debug("Refresh GPU Stats")
    stats.Gpu.stats()


@async_job("Memory_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['MEMORY'].get("INTERVAL", 0)).total_seconds())
def MemoryStats():
    # logger.debug("Refresh memory stats")
    stats.Memory.stats()


@async_job("Disk_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['DISK'].get("INTERVAL", 0)).total_seconds())
def DiskStats():
    # logger.debug("Refresh disk stats")
    stats.Disk.stats()


@async_job("Net_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['NET'].get("INTERVAL", 0)).total_seconds())
def NetStats():
    # logger.debug("Refresh net stats")
    stats.Net.stats()


@async_job("Date_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['DATE'].get("INTERVAL", 0)).total_seconds())
def DateStats():
    # logger.debug("Refresh date stats")
    stats.Date.stats()

@async_job("SystemUptime_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['UPTIME'].get("INTERVAL", 0)).total_seconds())
def SystemUptimeStats():
    # logger.debug("Refresh system uptime stats")
    stats.SystemUptime.stats()

@async_job("Custom_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['CUSTOM'].get("INTERVAL", 0)).total_seconds())
def CustomStats():
    # print("Refresh custom stats")
    stats.Custom.stats()

@async_job("Volume_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['VOLUME'].get("INTERVAL", 0)).total_seconds())
def VolumeStats():
    # logger.debug("Refresh volume stats")
    stats.Volume.stats()

@async_job("LcdSensor_Temperature")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['LCD_SENSOR']['TEMPERATURE'].get("INTERVAL", 0)).total_seconds())
def LcdSensorTemperature():
    """ Refresh the Humiture Temperature """
    stats.LcdSensor.temperature()

@async_job("LcdSensor_Humidness")
@schedule(timedelta(seconds=config.THEME_DATA['STATS']['LCD_SENSOR']['HUMIDNESS'].get("INTERVAL", 0)).total_seconds())
def LcdSensorHumidness():
    """ Refresh the Humiture Humidness """
    stats.LcdSensor.humidness()

def is_queue_empty() -> bool:
    return config.update_queue.empty()

def get_queue_size() -> int:
    return config.update_queue.qsize()

@async_job("LcdRx_Handler")
@schedule(timedelta(milliseconds=(250 if (config.THEME_DATA['STATS']['LCD_SENSOR']['TEMPERATURE'].get("INTERVAL", 0) != 0) or (config.THEME_DATA['STATS']['LCD_SENSOR']['HUMIDNESS'].get("INTERVAL", 0) != 0) else 0)).total_seconds())
def LcdRxHandler():
    stats.LcdSensor.handle()

def dynamic_images_Init():
    dynamic_images.dynamic_images.init()
    
@async_job("dynamic_images_Handler")
@schedule(timedelta(milliseconds=(100 if config.THEME_DATA['dynamic_images'].get("SHOW", False) == True else 0)).total_seconds())
def dynamic_images_Handler():
    dynamic_images.dynamic_images.handle()

def dynamic_texts_Init():
    dynamic_texts.dynamic_texts.init()
    
@async_job("dynamic_texts_Handler")
@schedule(timedelta(milliseconds=(100 if config.THEME_DATA['dynamic_texts'].get("SHOW", False) == True else 0)).total_seconds())
def dynamic_texts_Handler():
    dynamic_texts.dynamic_texts.handle()

def photo_album_Init():
    photo_album.photo_album.init()

@async_job("photo_album_Handler")
@schedule(timedelta(seconds=(config.THEME_DATA['photo_album'].get("INTERVAL", 0))).total_seconds())
def photo_album_Handler():
    photo_album.photo_album.handle()

@async_job("Weather_Stats")
@schedule(timedelta(seconds=max(300.0, config.THEME_DATA['STATS'].get('WEATHER', {}).get("INTERVAL", 0))).total_seconds())
def WeatherStats():
    stats.Weather.stats()

@async_job("Ping_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS'].get('PING', {}).get("INTERVAL", 0)).total_seconds())
def PingStats():
    stats.Ping.stats()

@async_job("InputMonitor_Stats")
@schedule(timedelta(seconds=config.THEME_DATA['STATS'].get('INPUT_MONITOR', {}).get("INTERVAL", 0)).total_seconds())
def InputMonitorStats():
    stats.InputMonitor.stats()

@async_job("requests_get_Handler")
@schedule(timedelta(milliseconds=(100 if config.THEME_DATA['requests_get'].get("SHOW", False) == True else 0)).total_seconds())
def requests_get_Handler():
    requests_get.requests_get.get()

def requests_get_Init():
    requests_get.requests_get.init()

@async_job("media_get_Handler")
@schedule(timedelta(seconds=(1 if config.THEME_DATA.get("media_get", None) is not None else 0)).total_seconds())
def media_get_Handler():
    media_get.media_get.handle()

def media_get_Init():
    media_get.media_get.init()

@async_job("Queue_Handler")
@schedule(timedelta(milliseconds=1).total_seconds())
def QueueHandler():
    # Do next action waiting in the queue
    global STOPPING
    if STOPPING:
        stats.InputMonitor.stop()
        # Empty the action queue to allow program to exit cleanly
        while not config.update_queue.empty():
            f, args = config.update_queue.get()
            f(*args)
    else:
        # Execute first action in the queue
        f, args = config.update_queue.get()
        if f:
            f(*args)