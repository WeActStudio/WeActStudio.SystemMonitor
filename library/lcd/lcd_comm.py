# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

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

import copy
import math
import queue
import threading
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Tuple, List, Optional, Dict
from pathlib import Path
import serial
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from library.log import logger
from library.lcd.color import Color, parse_color

class Orientation(IntEnum):
    PORTRAIT = 0
    LANDSCAPE = 2
    REVERSE_PORTRAIT = 1
    REVERSE_LANDSCAPE = 3


class LcdComm(ABC):
    def __init__(self, com_port: str = "AUTO", display_width: int = 320, display_height: int = 480,
                 update_queue: Optional[queue.Queue] = None):
        self.lcd_serial = None

        # String containing absolute path to serial port e.g. "COM3", "/dev/ttyACM1" or "AUTO" for auto-discovery
        self.com_port = com_port

        # Display always start in portrait orientation by default
        self.orientation = Orientation.PORTRAIT
        # Display width in default orientation (portrait)
        self.display_width = display_width
        # Display height in default orientation (portrait)
        self.display_height = display_height

        # Queue containing the serial requests to send to the screen. An external thread should run to process requests
        # on the queue. If you want serial requests to be done in sequence, set it to None
        self.update_queue = update_queue

        # Mutex to protect the queue in case a thread want to add multiple requests (e.g. image data) that should not be
        # mixed with other requests in-between
        self.update_queue_mutex = threading.Lock()

        # Create a cache to store opened images, to avoid opening and loading from the filesystem every time
        self.image_cache = {}  # { key=path, value=PIL.Image }

        # Create a cache to store opened fonts, to avoid opening and loading from the filesystem every time
        self.font_cache: Dict[
            Tuple[str, int],  # key=(font, size)
            ImageFont.FreeTypeFont # value= a loaded freetype font
        ] = {}

    def get_width(self) -> int:
        if self.orientation == Orientation.PORTRAIT or self.orientation == Orientation.REVERSE_PORTRAIT:
            return self.display_width
        else:
            return self.display_height

    def get_height(self) -> int:
        if self.orientation == Orientation.PORTRAIT or self.orientation == Orientation.REVERSE_PORTRAIT:
            return self.display_height
        else:
            return self.display_width

    def openSerial(self):
        if self.com_port == 'AUTO':
            self.com_port = self.auto_detect_com_port()
            if not self.com_port:
                logger.error(
                    "Cannot find COM port automatically, please run Configuration again and select COM port manually")
                self.com_port = 'AUTO'
                return False
            else:
                logger.debug(f"Auto detected COM port: {self.com_port}")
        else:
            logger.debug(f"Static COM port: {self.com_port}")
        
        try:
            self.lcd_serial = serial.Serial(self.com_port, 115200, timeout=1, rtscts=True)
        except Exception as e:
            logger.error(f"Cannot open COM port {self.com_port}: {e}")
            return False
        return True

    def closeSerial(self):
        try:
            self.lcd_serial.close()
        except:
            pass

    def serial_write(self, data: bytes):
        assert self.lcd_serial is not None
        self.lcd_serial.write(data)

    def serial_read(self, size: int) -> bytes:
        assert self.lcd_serial is not None
        return self.lcd_serial.read(size)
    
    def serial_readall(self) -> bytes:
        assert self.lcd_serial is not None
        return self.lcd_serial.readall()

    def serial_flush_input(self):
        if self.lcd_serial is not None:
            self.lcd_serial.reset_input_buffer()

    def WriteData(self, byteBuffer: bytearray):
        self.WriteLine(bytes(byteBuffer))

    def SendLine(self, line: bytes):
        if self.update_queue:
            # Queue the request. Mutex is locked by caller to queue multiple lines
            self.update_queue.put((self.WriteLine, [line]))
        else:
            # If no queue for async requests: do request now
            self.WriteLine(line)

    def WriteLine(self, line: bytes):
        if self.lcd_serial.is_open:
            try:
                self.lcd_serial.write(line)
            except serial.serialutil.SerialTimeoutException:
                # We timed-out trying to write to our device, slow things down.
                logger.warning("(Write line) Too fast! Slow down!")
            except serial.serialutil.SerialException:
                # Error writing data to device: close and reopen serial port, try to write again
                logger.error(
                    "SerialException: Failed to send serial data to device. Closing and reopening COM port before retrying once.")
                self.closeSerial()
                # time.sleep(1)
                # self.openSerial()
                # self.lcd_serial.write(line)

    def ReadData(self, readSize: int):
        if self.lcd_serial.is_open:
            try:
                response = self.lcd_serial.read(readSize)
                # logger.debug("Received: [{}]".format(str(response, 'utf-8')))
                return response
            except serial.serialutil.SerialTimeoutException:
                # We timed-out trying to read from our device, slow things down.
                logger.warning("(Read data) Too fast! Slow down!")
            except serial.serialutil.SerialException:
                # Error writing data to device: close and reopen serial port, try to read again
                logger.error(
                    "SerialException: Failed to read serial data from device. Closing and reopening COM port before retrying once.")
                self.closeSerial()
                # time.sleep(1)
                # self.openSerial()
                # return self.lcd_serial.read(readSize)
        else:
            return None

    @staticmethod
    @abstractmethod
    def auto_detect_com_port():
        pass

    @abstractmethod
    def InitializeComm(self,use_compress:int = 0):
        pass

    @abstractmethod
    def Reset(self):
        pass

    @abstractmethod
    def Clear(self):
        pass
    
    @abstractmethod
    def Full(self,color: Color = (0, 0, 0)):
        pass

    @abstractmethod
    def ScreenOff(self):
        pass

    @abstractmethod
    def ScreenOn(self):
        pass

    @abstractmethod
    def SetBrightness(self, level: int):
        pass

    def SetBackplateLedColor(self, led_color: Tuple[int, int, int] = (255, 255, 255)):
        pass

    @abstractmethod
    def SetOrientation(self, orientation: Orientation):
        pass

    def SetSensorReportTime(self, time_ms: int):
        pass

    def HandleSensorReport(self):
        return 25,50

    @abstractmethod
    def DisplayPILImage(
            self,
            image: Image.Image,
            x: int = 0, y: int = 0,
            image_width: int = 0,
            image_height: int = 0
    ):
        pass

    def DisplayBitmap(self, bitmap_path: str, x: int = 0, y: int = 0, width: int = 0, height: int = 0):
        image = self.open_image(bitmap_path)
        self.DisplayPILImage(image, x, y, width, height)

    def DisplayBitmap2(self, bitmap_path: str, x: int = 0, y: int = 0, max_width: int = 0, max_height: int = 0,align: str = 'left'):
        
        assert x <= self.get_width(), f'Display Image X {x} coordinate must be <= display width {self.get_width()}'
        assert y <= self.get_height(), f'Display Image Y {y} coordinate must be <= display height {self.get_height()}'
        assert x + max_width <= self.get_width(), f'Display Bitmap max_width+x exceeds display width {self.get_width()}'
        assert y + max_height <= self.get_height(), f'Display Bitmap max_height+y exceeds display height {self.get_height()}'

        image = self.open_image(bitmap_path,max_width,max_height)

        if max_width > 0 and max_height > 0:
            if align == 'right':
                x = max_width - image.width + x
            elif align == 'center':
                x = (max_width - image.width) // 2 + x
                y = (max_height - image.height) // 2 + y
                
        self.DisplayPILImage(image, x, y)

    def DisplayText(
            self,
            text: str,
            x: int = 0,
            y: int = 0,
            width: int = 0,
            height: int = 0,
            font: str = str(Path(__file__).parent.parent.parent / "res" / "fonts" / "roboto-mono" / "RobotoMono-Regular.ttf"),
            font_size: int = 20,
            font_color: Color = (0, 0, 0),
            background_color: Color = (255, 255, 255),
            background_image: Optional[str] = None,
            align: str = 'justify',
            anchor: str = 'la',
            rotation: int = 0
    ):
        # Convert text to bitmap using PIL and display it
        # Provide the background image path to display text with transparent background

        font_color = parse_color(font_color)

        assert x <= self.get_width(), 'Text X coordinate ' + str(x) + ' must be <= display width ' + str(
            self.get_width())
        assert y <= self.get_height(), 'Text Y coordinate ' + str(y) + ' must be <= display height ' + str(
            self.get_height())
        assert len(text) > 0, 'Text must not be empty'
        assert font_size > 0, "Font size must be > 0"

        anchor_set = None if '\n' in text else anchor

        text_image = None
        if background_image is None:
            background_color = parse_color(background_color)
            # A text bitmap is created with max width/height by default : text with solid background
            text_image = Image.new(
                'RGB',
                (self.get_width(), self.get_height()),
                background_color
            )
        else:
            # The text bitmap is created from provided background image : text with transparent background
            text_image = self.open_image(background_image)

        # Get text bounding box
        try:
            ttfont = self.open_font(font, font_size)
        except:
            raise Exception(f"Font {font} open failed")
        d = ImageDraw.Draw(text_image)

        # Split text into lines based on width
        current_line = ''
        lines = []
        screen_width = self.get_width()
        font_height = ttfont.size
        # initialize coordinates, ensure left and top initial values are large enough, and right and bottom initial values are small enough
        left = float('inf')
        top = float('inf')
        right = float('-inf')
        bottom = float('-inf')
        # initialize current line y coordinate, update it when line break
        current_y = y

        for char in text:
            test_line = current_line + char
            x0, y0, x1, y1 = d.textbbox((x, current_y), test_line, font=ttfont, align=align, anchor=anchor_set)
            width_now = x1 - x0
            
            # ensure current line does not exceed width limit
            width_limit = width if width != 0 else (screen_width-x0)
            # check if current line exceeds width limit or screen width
            if x0 >= 0 and width_now <= width_limit and x1 <= screen_width and char != '\n':
                current_line = test_line
            else:
                if current_line:
                    # record current line text box information
                    x0, y0, x1, y1 = d.textbbox((x, current_y), current_line, font=ttfont, align=align, anchor=anchor)
                    if anchor_set is not None:
                        height_now = y1 - y0
                        height_error = (font_height-height_now)/2
                        if anchor_set.endswith('m'):
                            y0 = y0 - height_error
                            y1 = y1 + height_error
                        elif anchor_set.endswith('b') or anchor_set.endswith('d') or anchor_set.endswith('s'):
                            y0 = y0 - (font_height-height_now)
                        else:
                            y1 = y1 + (font_height-height_now)
                    left = min(left, x0)
                    top = min(top, y0)
                    right = max(right, x1)
                    bottom = max(bottom, y1)
                    lines.append(current_line)
                    # update current line y coordinate
                    current_y += font_height
                if char == '\n':
                   current_line = ''
                else:
                    current_line = char

        # handle last line
        if current_line:
            x0, y0, x1, y1 = d.textbbox((x, current_y), current_line, font=ttfont, align=align, anchor=anchor)
            # print(f'x0: {x0} y0: {y0} x1: {x1} y1: {y1}')
            if anchor_set is not None:
                height_now = y1 - y0
                height_error = (font_height-height_now)/2
                if anchor_set.endswith('m'):
                    y0 = y0 - height_error
                    y1 = y1 + height_error
                elif anchor_set.endswith('b') or anchor_set.endswith('d') or anchor_set.endswith('s'):
                    y0 = y0 - (font_height-height_now)
                else:
                    y1 = y1 + (font_height-height_now)
            left = min(left, x0)
            top = min(top, y0)
            right = max(right, x1)
            bottom = max(bottom, y1)
            lines.append(current_line)

        # calculate actual text width and height
        # print(f'left: {left} top: {top} right: {right} bottom: {bottom}')
        text_width = right - left
        text_height = len(lines) * font_height
        # print(text_width,text_height,lines,font_height,len(lines))

        # when width or height is 0, set it to actual text width or height
        if width == 0:
            width = text_width
        if height == 0:
            height = text_height

        # calculate offset to center text
        offset_x = 0
        offset_y = 0

        error_left = 0
        error_right = 0
        error_top = 0
        error_bottom = 0

        if anchor is not None:
            if width > text_width:
                if anchor.startswith('m'):
                    error_left = (width - text_width) // 2
                    error_right = width - text_width - error_left
                elif anchor.startswith('l'):
                    error_left = 0
                    error_right = width - text_width
                else:
                    error_left = width - text_width
                    error_right = 0

            if height > font_height:
                if anchor.endswith('m'):
                    error_top = (height - text_height) // 2
                    error_bottom = height - text_height - error_top
                elif anchor.endswith('b') or anchor.endswith('d') or anchor.endswith('s'):
                    error_top = height - text_height
                    error_bottom = 0
                else:
                    error_top = 0
                    error_bottom = height - text_height

        # calculate new display area and offset
        new_left = left - error_left
        new_top = top - error_top
        new_right = right + error_right
        new_bottom = bottom + error_bottom
        
        # print(f'new_left: {new_left} new_top: {new_top} new_right: {new_right} new_bottom: {new_bottom}')

        if anchor is not None:
            if anchor.startswith('l'):
                if align == 'center':
                    offset_x = offset_x - (width - text_width) // 2
                elif align == 'right':
                    offset_x = offset_x - (width - text_width)
            elif anchor.startswith('r'):
                if align == 'center':
                    offset_x = offset_x + (width - text_width) // 2
                elif align == 'left':
                    offset_x = offset_x + (width - text_width)
            elif anchor.startswith('m'):
                if align == 'left':
                    offset_x = offset_x + (width - text_width) // 2
                elif align == 'right':
                    offset_x = offset_x - (width - text_width) // 2
                
            # if height > text_height:
            #     offset_y = offset_y - (new_bottom - new_top - text_height) // 2

        if rotation != 0:
            # create a temporary image to draw text
            tmp_img = Image.new(
                'RGBA',
                (self.get_width(), self.get_height()),
                (0, 0, 0, 0)
            )
            tmp_draw = ImageDraw.Draw(tmp_img)
            for line_idx, line in enumerate(lines):
                line_y = y + line_idx * font_height - offset_y
                tmp_draw.text((x-offset_x, line_y), line, fill=font_color, font=ttfont, align=align, anchor=anchor_set)
            tmp_img = tmp_img.crop((new_left, new_top, new_right, new_bottom))
            # rotate image
            tmp_img = tmp_img.rotate(rotation, expand=True)
            # calculate new coordinates
            if anchor is not None:
                if anchor.startswith('m') or align == 'center':
                    x -= tmp_img.width // 2
                elif anchor.startswith('r') or align == 'right':
                    x -= tmp_img.width
                if anchor.endswith('m'):
                    y -= tmp_img.height // 2
                elif anchor.endswith('b'):
                    y -= tmp_img.height
            text_image.paste(tmp_img, (x, y), tmp_img)
            new_left, new_top, new_right, new_bottom = x, y, x + tmp_img.width, y + tmp_img.height
        else:
            # draw text on image
            for line_idx, line in enumerate(lines):
                line_y = y + line_idx * font_height - offset_y
                d.text((x-offset_x, line_y), line, fill=font_color, font=ttfont, align=align, anchor=anchor)

        # crop text image to get actual text area
        text_image = text_image.crop((new_left, new_top, new_right, new_bottom))
        try:
            self.DisplayPILImage(text_image, int(new_left), int(new_top))
        except:
            raise Exception(f"Text display failed, x: {new_left}, y: {new_top}, width: {text_image.width}, height: {text_image.height}")

    def DisplayText2(
            self,
            text: str,
            x: int = 0,
            y: int = 0,
            width: int = 0,
            height: int = 0,
            font: str = str(Path(__file__).parent.parent.parent / "res" / "fonts" / "roboto-mono" / "RobotoMono-Regular.ttf"),
            font_size: int = 20,
            font_color: Color = (0, 0, 0),
            background_color: Color = (255, 255, 255),
            background_image: Optional[str] = None,
            anchor: str = 'la',
            width_last: int = 0
    ):
        # Convert text to bitmap using PIL and display it
        # Provide the background image path to display text with transparent background

        font_color = parse_color(font_color)

        assert x <= self.get_width(), 'Text X coordinate ' + str(x) + ' must be <= display width ' + str(
            self.get_width())
        assert y <= self.get_height(), 'Text Y coordinate ' + str(y) + ' must be <= display height ' + str(
            self.get_height())
        assert len(text) > 0, 'Text must not be empty'
        assert font_size > 0, "Font size must be > 0"

        anchor_set = None if '\n' in text else anchor

        text_image = None
        if background_image is None:
            background_color = parse_color(background_color)
            # A text bitmap is created with max width/height by default : text with solid background
            text_image = Image.new(
                'RGB',
                (self.get_width(), self.get_height()),
                background_color
            )
        else:
            # The text bitmap is created from provided background image : text with transparent background
            text_image = self.open_image(background_image)

        # Get text bounding box
        try:
            ttfont = self.open_font(font, font_size)
        except:
            raise Exception(f"Font {font} open failed")
        d = ImageDraw.Draw(text_image)

        screen_width = self.get_width()
        current_line = ''
        display_char_size = 0
        display_char_width = 0
        display_char_height = 0
        new_left = 0
        new_top = 0
        new_right = 0
        new_bottom = 0
        for char in text:
            test_line = current_line + char
            x0, y0, x1, y1 = d.textbbox((x, y), test_line, font=ttfont, anchor=anchor_set)
            width_now = x1 - x0
            
            # ensure current line does not exceed width limit
            width_limit = width if width != 0 else (screen_width-x0)
            # check if current line exceeds width limit or screen width
            if x0 >= 0 and width_now <= width_limit and x1 <= screen_width and char != '\n':
                current_line = test_line
                display_char_width = width_now
                new_left = x0
                new_top = y0
                new_right = x1
                new_bottom = y1
            else:
                break
        display_char_width = new_right - new_left
        display_char_height = new_bottom - new_top
        display_char_size = len(current_line)
        d.text((x, y), current_line, fill=font_color, font=ttfont, anchor=anchor_set)
        
        if width == 0:
            if width_last > display_char_width:
                width = width_last
                
        if width:
            if anchor_set.startswith('m'):
                error_left = (width - display_char_width) // 2
                error_right = width - display_char_width - error_left
            elif anchor_set.startswith('l'):
                error_left = 0
                error_right = width - display_char_width
            else:
                error_left = width - display_char_width
                error_right = 0
            new_left -= error_left
            new_right += error_right

        if height < ttfont.size:
            height = ttfont.size
        if anchor_set.endswith('m'):
            error_top = (height - display_char_height) // 2
            error_bottom = height - display_char_height - error_top
        elif anchor_set.endswith('b') or anchor_set.endswith('d') or anchor_set.endswith('s'):
            error_top = height - display_char_height
            error_bottom = 0
        else:
            error_top = 0
            error_bottom = height - display_char_height
        new_top -= error_top
        new_bottom += error_bottom

        # crop text image to get actual text area
        text_image = text_image.crop((new_left, new_top, new_right, new_bottom))
        try:
            self.DisplayPILImage(text_image, int(new_left), int(new_top))
        except:
            display_char_size = 0
            display_char_width = 0
            display_char_height = 0
            raise Exception(f"Text display failed, x: {new_left}, y: {new_top}, width: {text_image.width}, height: {text_image.height}")

        return display_char_size, display_char_width


    def DisplayProgressBar(self, x: int, y: int, width: int, height: int, min_value: int = 0, max_value: int = 100,
                           value: int = 50,
                           bar_color: Color = (0, 0, 0),
                           bar_outline: bool = True,
                           background_color: Color = (255, 255, 255),
                           background_image: Optional[str] = None):
        # Generate a progress bar and display it
        # Provide the background image path to display progress bar with transparent background

        bar_color = parse_color(bar_color)
        background_color = parse_color(background_color)

        assert x <= self.get_width(), 'Progress bar X coordinate must be <= display width'
        assert y <= self.get_height(), 'Progress bar Y coordinate must be <= display height'
        assert x + width <= self.get_width(), 'Progress bar width exceeds display width'
        assert y + height <= self.get_height(), 'Progress bar height exceeds display height'

        # Don't let the set value exceed our min or max value, this is bad :)
        if value < min_value:
            value = min_value
        elif max_value < value:
            value = max_value

        assert min_value <= value <= max_value, 'Progress bar value shall be between min and max'

        if background_image is None:
            # A bitmap is created with solid background
            bar_image = Image.new('RGB', (width, height), background_color)
        else:
            # A bitmap is created from provided background image
            bar_image = self.open_image(background_image)

            # Crop bitmap to keep only the progress bar background
            bar_image = bar_image.crop(box=(x, y, x + width, y + height))

        # Draw progress bar
        bar_filled_width = (value / (max_value - min_value) * width) - 1
        if bar_filled_width < 0:
            bar_filled_width = 0
        draw = ImageDraw.Draw(bar_image)
        draw.rectangle([0, 0, bar_filled_width, height - 1], fill=bar_color, outline=bar_color)

        if bar_outline:
            # Draw outline
            draw.rectangle([0, 0, width - 1, height - 1], fill=None, outline=bar_color)

        self.DisplayPILImage(bar_image, x, y)

    def DisplayLineGraph(self, x: int, y: int, width: int, height: int,
                         values: List[float],
                         min_value: float = 0,
                         max_value: float = 100,
                         autoscale: bool = False,
                         line_color: Color = (0, 0, 0),
                         line_width: int = 2,
                         graph_axis: bool = True,
                         axis_color: Color = (0, 0, 0),
                         axis_font: str = str(Path(__file__).parent.parent.parent / "res" / "fonts" / "roboto" / "Roboto-Black.ttf"),
                         axis_font_size: int = 10,
                         background_color: Color = (255, 255, 255),
                         background_image: Optional[str] = None,
                         axis_minmax_format: str = "{:0.0f}"):
        # Generate a plot graph and display it
        # Provide the background image path to display plot graph with transparent background

        line_color = parse_color(line_color)
        axis_color = parse_color(axis_color)
        background_color = parse_color(background_color)

        assert x <= self.get_width(), 'Line graph X coordinate must be <= display width'
        assert y <= self.get_height(), 'Line graph Y coordinate must be <= display height'
        assert x + width <= self.get_width(), 'Line graph width exceeds display width'
        assert y + height <= self.get_height(), 'Line graph height exceeds display height'

        if background_image is None:
            # A bitmap is created with solid background
            graph_image = Image.new('RGB', (width, height), background_color)
        else:
            # A bitmap is created from provided background image
            graph_image = self.open_image(background_image)

            # Crop bitmap to keep only the plot graph background
            graph_image = graph_image.crop(box=(x, y, x + width, y + height))

        # if autoscale is enabled, define new min/max value to "zoom" the graph
        if autoscale:
            trueMin = max_value
            trueMax = min_value
            for value in values:
                if not math.isnan(value):
                    if trueMin > value:
                        trueMin = value
                    if trueMax < value:
                        trueMax = value

            if trueMin != max_value and trueMax != min_value:
                min_value = max(trueMin - 5, min_value)
                max_value = min(trueMax + 5, max_value)

        step = width / len(values)
        # pre compute yScale multiplier value
        yScale = height / (max_value - min_value) if (max_value - min_value) != 0 else 0

        plotsX = []
        plotsY = []
        count = 0
        for value in values:
            if not math.isnan(value):
                # Don't let the set value exceed our min or max value, this is bad :)                
                if value < min_value:
                    value = min_value
                elif max_value < value:
                    value = max_value

                assert min_value <= value <= max_value, 'Plot point value shall be between min and max'

                plotsX.append(count * step)
                plotsY.append(height - (value - min_value) * yScale)

                count += 1

        # Draw plot graph
        draw = ImageDraw.Draw(graph_image)
        draw.line(list(zip(plotsX, plotsY)), fill=line_color, width=line_width)

        if graph_axis:
            # Draw axis
            draw.line([0, height - 1, width - 1, height - 1], fill=axis_color)
            draw.line([0, 0, 0, height - 1], fill=axis_color)

            # Draw Legend
            draw.line([0, 0, 1, 0], fill=axis_color)
            text = axis_minmax_format.format(max_value)
            ttfont = self.open_font(axis_font, axis_font_size)
            _, top, right, bottom = ttfont.getbbox(text)
            draw.text((2, 0 - top), text,
                      font=ttfont, fill=axis_color)

            text = axis_minmax_format.format(min_value)
            _, top, right, bottom = ttfont.getbbox(text)
            draw.text((width - 1 - right, height - 2 - bottom), text,
                      font=ttfont, fill=axis_color)

        self.DisplayPILImage(graph_image, x, y)

    def DrawRadialDecoration(self, draw: ImageDraw.ImageDraw, angle: float, radius: float, width: float, color: Tuple[int, int, int] = (0, 0, 0)):
        i_cos = math.cos(angle*math.pi/180)
        i_sin = math.sin(angle*math.pi/180)
        x_f = (i_cos * (radius - width/2)) + radius
        if math.modf(x_f) == 0.5:
            if i_cos > 0:
                x_f = math.floor(x_f)
            else:
                x_f = math.ceil(x_f)
        else:
             x_f = math.floor(x_f + 0.5) 
            
        y_f = (i_sin * (radius - width/2)) + radius 
        if math.modf(y_f) == 0.5:
            if i_sin > 0:
                y_f = math.floor(y_f)
            else:
                y_f = math.ceil(y_f)
        else:
            y_f = math.floor(y_f + 0.5)            
        draw.ellipse([x_f - width/2, y_f - width/2, x_f + width/2, y_f - 1 + width/2 - 1], outline=color, fill=color, width=1)   
      

    def DisplayRadialProgressBar(self, xc: int, yc: int, radius: int, bar_width: int,
                                 min_value: int = 0,
                                 max_value: int = 100,
                                 angle_start: float = 0,
                                 angle_end: float = 360,
                                 angle_sep: int = 5,
                                 angle_steps: int = 10,
                                 clockwise: bool = True,
                                 value: int = 50,
                                 text: Optional[str] = None,
                                 with_text: bool = True,
                                 font: str = str(Path(__file__).parent.parent.parent / "res" / "fonts" / "roboto" / "Roboto-Black.ttf"),
                                 font_size: int = 20,
                                 font_color: Color = (0, 0, 0),
                                 bar_color: Color = (0, 0, 0),
                                 background_color: Color = (255, 255, 255),
                                 background_image: Optional[str] = None,
                                 custom_bbox: Tuple[int, int, int, int] = (0, 0, 0, 0),
                                 text_offset: Tuple[int, int] = (0,0),
                                 bar_background_color: Color = (0, 0, 0),
                                 draw_bar_background: bool = False,
                                 bar_decoration: str = ""):                                 
        # Generate a radial progress bar and display it
        # Provide the background image path to display progress bar with transparent background

        bar_color = parse_color(bar_color)
        background_color = parse_color(background_color)
        font_color = parse_color(font_color)
        bar_background_color = parse_color(bar_background_color)

        if isinstance(custom_bbox, str):
            custom_bbox = tuple(map(int, custom_bbox.split(', ')))

        if isinstance(text_offset, str):
            text_offset = tuple(map(int, text_offset.split(', ')))

        if angle_start % 361 == angle_end % 361:
            if clockwise:
                angle_start += 0.1
            else:
                angle_end += 0.1

        assert xc - radius >= 0 and xc + radius <= self.get_width(), 'Radial is out of screen (left/right)'
        assert yc - radius >= 0 and yc + radius <= self.get_height(), 'Radial is out of screen (up/down)'
        assert 0 < bar_width <= radius, f'Radial linewidth is {bar_width}, must be > 0 and <= radius'
        assert angle_end % 361 != angle_start % 361, f'Invalid angles values, start = {angle_start}, end = {angle_end}'
        assert isinstance(angle_steps, int), 'angle_steps value must be an integer'
        assert angle_sep >= 0, 'Provide an angle_sep value >= 0'
        assert angle_steps > 0, 'Provide an angle_step value > 0'
        assert angle_sep * angle_steps < 360, 'Given angle_sep and angle_steps values are not correctly set'

        # Don't let the set value exceed our min or max value, this is bad :)
        if value < min_value:
            value = min_value
        elif max_value < value:
            value = max_value

        assert min_value <= value <= max_value, 'Radial value shall be between min and max'

        diameter = 2 * radius
        bbox = (xc - radius, yc - radius, xc + radius, yc + radius)
        #
        if background_image is None:
            # A bitmap is created with solid background
            bar_image = Image.new('RGB', (diameter, diameter), background_color)
        else:
            # A bitmap is created from provided background image
            bar_image = self.open_image(background_image)

            # Crop bitmap to keep only the progress bar background
            bar_image = bar_image.crop(box=bbox)

        # Draw progress bar
        pct = (value - min_value) / (max_value - min_value)
        draw = ImageDraw.Draw(bar_image)

        # PIL arc method uses angles with
        #  . 3 o'clock for 0
        #  . clockwise from angle start to angle end
        angle_start %= 361
        angle_end %= 361
        #
        if clockwise:
            if angle_end < angle_start:
                ecart = 360 - angle_start + angle_end
            else:
                ecart = angle_end - angle_start

            # draw bar background
            if draw_bar_background:
                if angle_end < angle_start:
                    angleE = angle_start + ecart
                    angleS = angle_start
                else:
                    angleS = angle_start
                    angleE = angle_start + ecart
                draw.arc([0, 0, diameter - 1, diameter - 1], angleS, angleE, fill=bar_background_color, width=bar_width) 
                
            # draw bar decoration
            if bar_decoration == "Ellipse":
                self.DrawRadialDecoration(draw = draw, angle = angle_end, radius = radius, width = bar_width, color = bar_background_color)
                self.DrawRadialDecoration(draw = draw, angle = angle_start, radius = radius, width = bar_width, color = bar_color)
                self.DrawRadialDecoration(draw = draw, angle = angle_start + pct * ecart, radius = radius, width = bar_width, color = bar_color)

            #
            # solid bar case
            if angle_sep == 0:
                if angle_end < angle_start:
                    angleE = angle_start + pct * ecart
                    angleS = angle_start
                else:
                    angleS = angle_start
                    angleE = angle_start + pct * ecart
                draw.arc([0, 0, diameter - 1, diameter - 1], angleS, angleE,
                         fill=bar_color, width=bar_width)
            # discontinued bar case
            else:
                angleE = angle_start + pct * ecart
                angle_complet = ecart / angle_steps
                etapes = int((angleE - angle_start) / angle_complet)
                for i in range(etapes):
                    draw.arc([0, 0, diameter - 1, diameter - 1],
                             angle_start + i * angle_complet,
                             angle_start + (i + 1) * angle_complet - angle_sep,
                             fill=bar_color,
                             width=bar_width)

                draw.arc([0, 0, diameter - 1, diameter - 1],
                         angle_start + etapes * angle_complet,
                         angleE,
                         fill=bar_color,
                         width=bar_width)
        else:
            if angle_end < angle_start:
                ecart = angle_start - angle_end
            else:
                ecart = 360 - angle_end + angle_start

            # draw bar background
            if draw_bar_background:
                if angle_end < angle_start:
                    angleE = angle_start
                    angleS = angle_start - ecart
                else:
                    angleS = angle_start - ecart
                    angleE = angle_start
                draw.arc([0, 0, diameter - 1, diameter - 1], angleS, angleE, fill=bar_background_color, width=bar_width) 


            # draw bar decoration
            if bar_decoration == "Ellipse":
                self.DrawRadialDecoration(draw = draw, angle = angle_end, radius = radius, width = bar_width, color = bar_background_color)
                self.DrawRadialDecoration(draw = draw, angle = angle_start, radius = radius, width = bar_width, color = bar_color)
                self.DrawRadialDecoration(draw = draw, angle = angle_start - pct * ecart, radius = radius, width = bar_width, color = bar_color)

            #      
            # solid bar case
            if angle_sep == 0:
                if angle_end < angle_start:
                    angleE = angle_start
                    angleS = angle_start - pct * ecart
                else:
                    angleS = angle_start - pct * ecart
                    angleE = angle_start
                draw.arc([0, 0, diameter - 1, diameter - 1], angleS, angleE,
                         fill=bar_color, width=bar_width)
            # discontinued bar case
            else:
                angleS = angle_start - pct * ecart
                angle_complet = ecart / angle_steps
                etapes = int((angle_start - angleS) / angle_complet)
                for i in range(etapes):
                    draw.arc([0, 0, diameter - 1, diameter - 1],
                             angle_start - (i + 1) * angle_complet + angle_sep,
                             angle_start - i * angle_complet,
                             fill=bar_color,
                             width=bar_width)

                draw.arc([0, 0, diameter - 1, diameter - 1],
                         angleS,
                         angle_start - etapes * angle_complet,
                         fill=bar_color,
                         width=bar_width)

        # Draw text
        if with_text:
            if text is None:
                text = f"{int(pct * 100 + .5)}%"
            ttfont = self.open_font(font, font_size)
            left, top, right, bottom = ttfont.getbbox(text)
            w, h = right - left, bottom - top
            draw.text((radius - w / 2 + text_offset[0], radius - top - h / 2 + text_offset[1]), text,
                      font=ttfont, fill=font_color)

        if custom_bbox[0] != 0 or custom_bbox[1] != 0 or custom_bbox[2] != 0 or custom_bbox[3] != 0:
            bar_image = bar_image.crop(box=custom_bbox)

        self.DisplayPILImage(bar_image, xc - radius + custom_bbox[0], yc - radius + custom_bbox[1])
       # self.DisplayPILImage(bar_image, xc - radius, yc - radius)
    def resize_image(self, image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        width_set = max_width
        height_set = max_height
        if image.width > width_set: 
            ratio = width_set / image.width  
            height = int(image.height * ratio)  
            image = image.resize((width_set, height), Image.LANCZOS)  
        if image.height > height_set:   
            ratio = height_set / image.height  
            width = int(image.width * ratio)  
            image = image.resize((width, height_set), Image.LANCZOS) 
        return image

    # Load image from the filesystem, or get from the cache if it has already been loaded previously
    def open_image(self, bitmap_path: str,max_width: int=0,max_height:int=0,id:int=-1) -> Image.Image:
        bitmap_path_with_id = str(bitmap_path) + f" {id}"
        if bitmap_path_with_id not in self.image_cache:
            image = Image.open(bitmap_path)
            if max_width > 0 and max_height > 0:
                image = self.resize_image(image, max_width, max_height)
            else:
                assert image.width <= self.get_width(), "Bitmap " + bitmap_path_with_id + f' width {image.width} exceeds display width {self.get_width()}'
                assert image.height <= self.get_height(), "Bitmap " + bitmap_path_with_id + f' height {image.height} exceeds display height {self.get_height()}'
            logger.debug("Bitmap " + bitmap_path_with_id + " is now loaded in the cache")
            self.image_cache[bitmap_path_with_id] = image
        return copy.copy(self.image_cache[bitmap_path_with_id])
    
    def save_image(self, bitmap_path: str, bitmap: Image.Image, id:int=-1):
        bitmap_path_with_id = str(bitmap_path) + f" {id}"
        self.image_cache[bitmap_path_with_id] = bitmap

    def DisplayImage(self, x: int, y: int,width: int,height: int,color: Tuple[int, int, int] = (255, 255, 255),image: str = None,
                           background_color: Tuple[int, int, int] = (255, 255, 255),
                           background_image: str = None):
        # display a image

        if isinstance(color, str):
            color = tuple(map(int, color.split(', ')))

        if image is None:
            # A bitmap is created with solid display
            display_image = Image.new('RGB', (width, height), color)
        else:
            # A bitmap is created from provided display image
            display_image = self.open_image(image)
            width = display_image.size[0]
            height = display_image.size[1]
            
        assert x <= self.get_width(), f'Display Image X {x} coordinate must be <= display width {self.get_width()}'
        assert y <= self.get_height(), f'Display Image Y {y} coordinate must be <= display height {self.get_height()}'
        assert x + width <= self.get_width(), f'Display Image width+x exceeds display width {self.get_width()}'
        assert y + height <= self.get_height(), f'Display Image height+y exceeds display height {self.get_height()}'

        if isinstance(background_color, str):
            background_color = tuple(map(int, background_color.split(', ')))

        if background_image is None:
            # A bitmap is created with solid background
            bg_image = Image.new('RGB', (width, height), background_color)
        else:
            # A bitmap is created from provided background image
            bg_image = self.open_image(background_image)

            # Crop bitmap to keep only the image background
            bg_image = bg_image.crop(box=(x, y, x + width, y + height))

        if 'A' in display_image.mode:
            bg_image.paste(display_image,(0, 0),display_image)
        else:
            bg_image.paste(display_image,(0, 0))
            
        self.DisplayPILImage(bg_image, x, y)

    def DisplayImage2(self, x: int, y: int,max_width: int,max_height: int,image: str = None,align: str = 'left',
                        background_color: Tuple[int, int, int] = (255, 255, 255),background_image: str = None, 
                        color: Tuple[int, int, int] = (255, 255, 255), radius: int = 0, alpha: int = 255, 
                        overlay_display=False, id:int=0,image_data:BytesIO=None):
        # display a image
        width_set = max_width
        height_set = max_height
        if image is None and image_data is None:
            display_image = Image.new('RGBA', (width_set, height_set), (0, 0, 0, 0))
            draw = ImageDraw.Draw(display_image)
            if isinstance(color, str):
                color = tuple(map(int, color.split(', ')))
            r, g, b = color
            fill_color = (r, g, b, alpha)
            draw.rounded_rectangle((0, 0, width_set, height_set), radius=radius, fill=fill_color)
        else:
            # A bitmap is created from provided display image
            if overlay_display:
                if max_width == 0:
                    width_set = self.get_width()
                if max_height == 0:
                    height_set = self.get_height()
            if image_data is None:
                display_image = self.open_image(image,width_set,height_set,id)
            else:
                display_image = Image.open(image_data)
                display_image = self.resize_image(display_image,width_set,height_set)
            mask = Image.new('L', display_image.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, display_image.size[0], display_image.size[1]), radius=radius, fill=alpha)
            display_image = Image.composite(display_image, Image.new('RGBA', display_image.size, (0, 0, 0)), mask)

        width = display_image.size[0]
        height = display_image.size[1]
        if overlay_display:
            if max_width == 0:
                width_set = width
            if max_height == 0:
                height_set = height
            
        assert x <= self.get_width(), f'Display Image X {x} coordinate must be <= display width {self.get_width()}'
        assert y <= self.get_height(), f'Display Image Y {y} coordinate must be <= display height {self.get_height()}'
        assert x + width_set <= self.get_width(), f'Display Bitmap width+x exceeds display width {self.get_width()}'
        assert y + height_set <= self.get_height(), f'Display Bitmap height+y exceeds display height {self.get_height()}'

        if isinstance(background_color, str):
            background_color = tuple(map(int, background_color.split(', ')))

        if background_image is None:
            # A bitmap is created with solid background
            r, g, b = background_color
            background_fill_color = (r, g, b, 255)
            bg_image = Image.new('RGBA', (self.get_width(), self.get_height()), background_fill_color)
        else:
            # A bitmap is created from provided background image
            bg_image = self.open_image(background_image)

            if overlay_display:
                self.save_image(background_image, bg_image)
                # self.image_cache[background_image] = bg_image

        x_d = 0
        y_d = 0
        if width_set > 0 and height_set > 0:
            if align == 'right':
                x_d = width_set - width
            elif align == 'center':
                x_d = (width_set - width) // 2
                y_d = (height_set - height) // 2

        if 'A' in display_image.mode:
            bg_image.paste(display_image,(x_d+x, y_d+y),display_image)
        else:
            bg_image.paste(display_image,(x_d+x, y_d+y))

        # Crop bitmap to keep only the image background
        bg_image_c = bg_image.crop(box=(x, y, x + width_set, y + height_set))
        self.DisplayPILImage(bg_image_c, x, y)

    def open_font(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        if (name, size) not in self.font_cache:
            self.font_cache[(name, size)] = ImageFont.truetype(name, size)
        return self.font_cache[(name, size)]