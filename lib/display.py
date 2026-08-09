# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
import os
import sys

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
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

from lib import config
from lib.lcd.lcd_comm import Orientation
from lib.lcd.lcd_comm_weact_a import LcdComm_WeAct_A
from lib.lcd.lcd_comm_weact_b import LcdComm_WeAct_B
from lib.lcd.lcd_simulated import LcdSimulated
from lib.log import logger
    
def _get_theme_orientation() -> Orientation:
    if config.THEME_DATA["display"]["DISPLAY_ORIENTATION"] == 'portrait':
        if config.CONFIG_DATA["display"].get("DISPLAY_REVERSE", False):
            return Orientation.REVERSE_PORTRAIT
        else:
            return Orientation.PORTRAIT
    elif config.THEME_DATA["display"]["DISPLAY_ORIENTATION"] == 'landscape':
        if config.CONFIG_DATA["display"].get("DISPLAY_REVERSE", False):
            return Orientation.REVERSE_LANDSCAPE
        else:
            return Orientation.LANDSCAPE
    else:
        logger.warning("Orientation '", config.THEME_DATA["display"]["DISPLAY_ORIENTATION"],
                       "' unknown, using portrait")
        return Orientation.PORTRAIT

def get_config_display_free_off() -> bool:
    return config.CONFIG_DATA["display"].get("FREE_OFF", False)

def get_config_display_brightness() -> int:
    return config.CONFIG_DATA["display"].get("BRIGHTNESS", 0)

class Display:
    def __init__(self):
        self.lcd = None
        self.is_LcdSimulated = False

    def init(self):
        self.use_compress = 1 if config.CONFIG_DATA['display']['PIC_COMPRESS']==True else 0
        if config.CONFIG_DATA["display"]["REVISION"] == "A_320x480":
            self.lcd = LcdComm_WeAct_A(com_port=config.CONFIG_DATA['config']['COM_PORT'],
                                   update_queue=config.update_queue)
            self.is_LcdSimulated = False
        elif config.CONFIG_DATA["display"]["REVISION"] == "B_80x160":
            self.lcd = LcdComm_WeAct_B(com_port=config.CONFIG_DATA['config']['COM_PORT'],
                                   update_queue=config.update_queue)
            self.is_LcdSimulated = False
        elif config.CONFIG_DATA["display"]["REVISION"] == "SIMU_320x480":
            self.lcd = LcdSimulated(display_width=320,
                                    display_height=480)
            self.is_LcdSimulated = True
        elif config.CONFIG_DATA["display"]["REVISION"] == "SIMU_480x800":
            self.lcd = LcdSimulated(display_width=480,
                                    display_height=800)
            self.is_LcdSimulated = True
        elif config.CONFIG_DATA["display"]["REVISION"] == "SIMU_80x160":
            self.lcd = LcdSimulated(display_width=80,
                                    display_height=160)
            self.is_LcdSimulated = True
        else:
            logger.error("Unknown display revision '", config.CONFIG_DATA["display"]["REVISION"], "'")

    def initialize_display(self):
        # Reset screen in case it was in an unstable state (screen is also cleared)
        self.lcd.Reset()

        # Send initialization commands
        self.lcd.InitializeComm(self.use_compress)

        # Set orientation
        self.lcd.SetOrientation(_get_theme_orientation())

        # Clear Lcd
        self.lcd.Clear()

        # Turn on display, set brightness and LEDs for supported HW
        self.turn_on()

    def turn_on(self):
        # Turn screen on in case it was turned off previously
        self.lcd.ScreenOn()

        # Set brightness
        self.lcd.SetBrightness(config.CONFIG_DATA["display"]["BRIGHTNESS"])

        # Set backplate RGB LED color (for supported HW only)
        self.lcd.SetBackplateLedColor(config.THEME_DATA['display'].get("DISPLAY_RGB_LED", (255, 255, 255)))

    def turn_off(self):
        # Turn screen off
        self.lcd.ScreenOff()

        # Turn off backplate RGB LED
        self.lcd.SetBackplateLedColor(led_color=(0, 0, 0))

    def display_static_images(self):
        if config.THEME_DATA.get('static_images', False):
            image_with_id = []
            image_no_id = []
            for image in config.THEME_DATA['static_images']:
                if isinstance(config.THEME_DATA['static_images'][image], dict):
                    id = config.THEME_DATA['static_images'][image].get("ID", -1)
                    if id >= 0:
                        image_with_id.append(image)
                    elif id < 0:
                        image_no_id.append(image)

            image_with_id.sort(key=lambda x: config.THEME_DATA['static_images'][x].get("ID", 0))
            
            def draw_image(image):
                logger.debug(f"Drawing Static Image {'With ID' if 'ID' in config.THEME_DATA['static_images'][image] else 'Without ID'}: {image}")
                width = config.THEME_DATA['static_images'][image].get("WIDTH", 0)
                height = config.THEME_DATA['static_images'][image].get("HEIGHT", 0)
                x = config.THEME_DATA['static_images'][image].get("X", 0)
                y = config.THEME_DATA['static_images'][image].get("Y", 0)
                bitmap_path = config.get_theme_file_path(config.THEME_DATA['static_images'][image].get("PATH", None))
                background_image = config.get_theme_file_path(config.THEME_DATA['static_images'][image].get("BACKGROUND_IMAGE", None))
                background_color = config.THEME_DATA['static_images'][image].get("BACKGROUND_COLOR", (0, 0, 0))
                color = config.THEME_DATA['static_images'][image].get("COLOR", (0, 0, 0))
                radius = config.THEME_DATA['static_images'][image].get("RADIUS", 0)
                alpha = config.THEME_DATA['static_images'][image].get("ALPHA", 255)
                id = config.THEME_DATA['static_images'][image].get("ID", -1)

                assert x <= self.lcd.get_width(), f"{bitmap_path} Image X {x} coordinate must be <= display width {self.lcd.get_width()}"
                assert y <= self.lcd.get_height(), f"{bitmap_path} Image Y {y} coordinate must be <= display height {self.lcd.get_height()}"
                assert radius >= 0, "Radius must be >= 0"
                assert 0 <= alpha <= 255, "Alpha must be >= 0 and <= 255"

                self.lcd.DisplayImage2(
                    x=x,
                    y=y,
                    max_width=width,
                    max_height=height,
                    image=bitmap_path,
                    background_color=background_color,
                    background_image=background_image,
                    color=color,
                    radius=radius,
                    alpha=alpha,
                    overlay_display=True,
                    id=id
                )

            for image in image_no_id:
                draw_image(image)
            for image in image_with_id:
                draw_image(image)

    def display_static_text(self):
        if config.THEME_DATA.get('static_text', False):
            for text in config.THEME_DATA['static_text']:
                logger.debug(f"Drawing Static Text: {text}")
                self.lcd.DisplayText(
                    text=config.THEME_DATA['static_text'][text].get("TEXT"),
                    x=config.THEME_DATA['static_text'][text].get("X", 0),
                    y=config.THEME_DATA['static_text'][text].get("Y", 0),
                    width=config.THEME_DATA['static_text'][text].get("WIDTH", 0),
                    height=config.THEME_DATA['static_text'][text].get("HEIGHT", 0),
                    font=config.get_font_path(config.THEME_DATA['static_text'][text].get("FONT", None)),
                    font_size=config.THEME_DATA['static_text'][text].get("FONT_SIZE", 10),
                    font_color=config.THEME_DATA['static_text'][text].get("FONT_COLOR", (0, 0, 0)),
                    background_color=config.THEME_DATA['static_text'][text].get("BACKGROUND_COLOR", (255, 255, 255)),
                    background_image=config.get_theme_file_path(config.THEME_DATA['static_text'][text].get("BACKGROUND_IMAGE", None)),
                    align=config.THEME_DATA['static_text'][text].get("ALIGN", "justify"),
                    anchor=config.THEME_DATA['static_text'][text].get("ANCHOR", "lt"),
                    rotation=config.THEME_DATA['static_text'][text].get("ROTATION", 0),
                )

    def initialize_sensor(self):
        error = True
        if config.THEME_DATA.get('STATS', False):
            if config.THEME_DATA['STATS'].get('LCD_SENSOR', False):
                logger.debug(f"Initialize LCD Sensor")
                temp_interval = 0
                humid_interval = 0
                time_set = 0
                if config.THEME_DATA['STATS']['LCD_SENSOR'].get('TEMPERATURE', False):
                    temp_interval = config.THEME_DATA['STATS']['LCD_SENSOR']['TEMPERATURE'].get('INTERVAL',0)
                if config.THEME_DATA['STATS']['LCD_SENSOR'].get('HUMIDNESS', False):
                    humid_interval = config.THEME_DATA['STATS']['LCD_SENSOR']['HUMIDNESS'].get('INTERVAL',0)
                if temp_interval > humid_interval:
                    if humid_interval > 0:
                        time_set = humid_interval
                    else:
                        time_set = temp_interval
                elif temp_interval < humid_interval:
                    if temp_interval > 0:
                        time_set = temp_interval
                    else:
                        time_set = humid_interval
                else:
                    if temp_interval > 0:
                        time_set = temp_interval
                if time_set > 0:
                    logger.debug(f'Set LCD Sensor Report Time {time_set}s')
                    self.lcd.SetSensorReportTime(time_set*1000)
                    error = False
        if error == True:
            self.lcd.SetSensorReportTime(0)

display = Display()
