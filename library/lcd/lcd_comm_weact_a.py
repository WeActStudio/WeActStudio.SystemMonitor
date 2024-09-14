# Copyright (C) 2024-2024  WeAct Studio

import struct

from serial.tools.list_ports import comports

from library.lcd.lcd_comm import *
from library.log import logger


class Command(IntEnum):
    CMD_WHO_AM_I = 0x81  # Establish communication before driving the screen
    CMD_SET_ORIENTATION = 0x02  # Sets the screen orientation
    CMD_SET_BRIGHTNESS = 0x03  # Sets the screen brightness
    CMD_FULL = 0x04  # Displays an image on the screen
    CMD_SET_BITMAP = 0x05  # Displays an image on the screen
    CMD_ENABLE_HUMITURE_REPORT = 0x06
    CMD_FREE = 0x07
    CMD_END = 0x0A  # Displays an image on the screen
    CMD_READ = 0x80


class LcdComm_WeAct_A(LcdComm):
    def __init__(
        self,
        com_port: str = "AUTO",
        display_width: int = 320,
        display_height: int = 480,
        update_queue: queue.Queue = None,
    ):
        LcdComm.__init__(self, com_port, display_width, display_height, update_queue)
        self.brightness = 0
        self.temperature = 0
        self.humidness = 0
        self.openSerial()

    def __del__(self):
        self.closeSerial()

    @staticmethod
    def auto_detect_com_port():
        com_ports = comports()
        auto_com_port = None

        for com_port in com_ports:
            if com_port.serial_number.startswith("AB"):
                auto_com_port = com_port.device
                break

        return auto_com_port

    def Send_Bitmap_xy_Command(self, xs, ys, xe, ye, bypass_queue: bool = False):
        byteBuffer = bytearray(10)
        byteBuffer[0] = Command.CMD_SET_BITMAP
        byteBuffer[1] = xs & 0xFF
        byteBuffer[2] = xs >> 8 & 0xFF
        byteBuffer[3] = ys & 0xFF
        byteBuffer[4] = ys >> 8 & 0xFF
        byteBuffer[5] = xe & 0xFF
        byteBuffer[6] = xe >> 8 & 0xFF
        byteBuffer[7] = ye & 0xFF
        byteBuffer[8] = ye >> 8 & 0xFF
        byteBuffer[9] = Command.CMD_END

        # If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
        if not self.update_queue or bypass_queue:
            self.WriteData(byteBuffer)
        else:
            # Lock queue mutex then queue the request
            with self.update_queue_mutex:
                self.update_queue.put((self.WriteData, [byteBuffer]))

    def SendCommand(self, byteBuffer, bypass_queue: bool = False):
        # If no queue for async requests, or if asked explicitly to do the request sequentially: do request now
        if not self.update_queue or bypass_queue:
            self.WriteData(byteBuffer)
        else:
            # Lock queue mutex then queue the request
            with self.update_queue_mutex:
                self.update_queue.put((self.WriteData, [byteBuffer]))

    def _who_am_i(self):
        byteBuffer = bytearray(2)
        byteBuffer[0] = Command.CMD_WHO_AM_I | Command.CMD_READ
        byteBuffer[1] = Command.CMD_END

        # This command reads LCD answer on serial link, so it bypasses the queue
        self.SendCommand(byteBuffer, bypass_queue=True)
        self.lcd_serial.flushInput()
        response = self.lcd_serial.readline()

        logger.info("Who Am I: %s" % (str(response[1:])))

    def InitializeComm(self):
        self._who_am_i()

    def Reset(self):
        self.Clear()

    def Clear(self):
        color = 0x0000
        byteBuffer = bytearray(4)
        byteBuffer[0] = Command.CMD_FULL
        byteBuffer[1] = color & 0xFF
        byteBuffer[2] = color >> 8 & 0xFF
        byteBuffer[3] = Command.CMD_END
        self.SendCommand(byteBuffer)

    def ScreenOff(self):
        self.SetBrightness(0)
        self.SetSensorReportTime(0)

    def ScreenOn(self):
        self.SetBrightness(self.brightness)

    def SetBrightness(self, level: int = 0):
        assert 0 <= level <= 100, "Brightness level must be [0-100]"

        converted_level = int((level / 100) * 255)
        brightness_ms = 1000
        byteBuffer = bytearray(5)
        byteBuffer[0] = Command.CMD_SET_BRIGHTNESS
        byteBuffer[1] = converted_level & 0xFF
        byteBuffer[2] = brightness_ms & 0xFF
        byteBuffer[3] = brightness_ms >> 8 & 0xFF
        byteBuffer[4] = Command.CMD_END

        self.SendCommand(byteBuffer)

        self.brightness = level

    def SetOrientation(self, orientation: Orientation = Orientation.PORTRAIT):
        self.orientation = orientation
        byteBuffer = bytearray(3)
        byteBuffer[0] = Command.CMD_SET_ORIENTATION
        byteBuffer[1] = self.orientation
        byteBuffer[2] = Command.CMD_END

        self.SendCommand(byteBuffer)

    def SetSensorReportTime(self, time_ms: int):
        if time_ms > 0xFFFF or (time_ms < 500 and time_ms != 0):
            return False
        byteBuffer = bytearray(4)
        byteBuffer[0] = Command.CMD_ENABLE_HUMITURE_REPORT
        byteBuffer[1] = time_ms & 0xFF
        byteBuffer[2] = time_ms >> 8 & 0xFF
        byteBuffer[3] = Command.CMD_END
        self.SendCommand(byteBuffer)

    def HandleSensorReport(self):
        if self.lcd_serial.in_waiting > 0:
            cmd = self.ReadData(1)
            if (
                cmd != None
                and cmd[0] == Command.CMD_ENABLE_HUMITURE_REPORT | Command.CMD_READ
            ):
                data = self.ReadData(5)
                if data != None and len(data) == 5 and data[4] == Command.CMD_END:
                    unpack = struct.unpack("<Hh", data[0:4])
                    self.temperature = float(unpack[0]) / 100
                    self.humidness = float(unpack[1]) / 100
            else:
                self.lcd_serial.read_all()
        return self.temperature, self.humidness

    def DisplayPILImage(
        self,
        image: Image,
        x: int = 0,
        y: int = 0,
        image_width: int = 0,
        image_height: int = 0,
    ):
        # If the image height/width isn't provided, use the native image size
        if not image_height:
            image_height = image.size[1]
        if not image_width:
            image_width = image.size[0]

        # If our image is bigger than our display, resize it to fit our screen
        if image.size[1] > self.get_height():
            image_height = self.get_height()
        if image.size[0] > self.get_width():
            image_width = self.get_width()

        assert x <= self.get_width(), "Image X coordinate must be <= display width"
        assert y <= self.get_height(), "Image Y coordinate must be <= display height"
        assert image_height > 0, "Image height must be > 0"
        assert image_width > 0, "Image width must be > 0"

        pix = image.load()
        line = bytes()

        (x0, y0) = (x, y)
        (x1, y1) = (x + image_width - 1, y + image_height - 1)

        byteBuffer = bytearray(10)
        byteBuffer[0] = Command.CMD_SET_BITMAP
        byteBuffer[1] = x0 & 0xFF
        byteBuffer[2] = x0 >> 8 & 0xFF
        byteBuffer[3] = y0 & 0xFF
        byteBuffer[4] = y0 >> 8 & 0xFF
        byteBuffer[5] = x1 & 0xFF
        byteBuffer[6] = x1 >> 8 & 0xFF
        byteBuffer[7] = y1 & 0xFF
        byteBuffer[8] = y1 >> 8 & 0xFF
        byteBuffer[9] = Command.CMD_END

        self.SendCommand(byteBuffer)

        # Lock queue mutex then queue all the requests for the image data
        with self.update_queue_mutex:
            for h in range(image_height):
                for w in range(image_width):
                    R = pix[w, h][0] >> 3
                    G = pix[w, h][1] >> 2
                    B = pix[w, h][2] >> 3

                    # Color information is 0bRRRRRGGGGGGBBBBB
                    # Encode in Little-Endian
                    rgb = (R << 11) | (G << 5) | B
                    line += struct.pack("<H", rgb)

                    # Send image data by multiple of "display width" bytes
                    # if len(line) >= self.get_width() * 32:
                    #     self.SendLine(line)
                    #     line = bytes()

            # Write last line if needed
            if len(line) > 0:
                self.SendLine(line)
