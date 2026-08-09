# Copyright (C) 2024-2024  WeAct Studio
import serial
from serial.tools import list_ports
import time
import threading 
import sys ,os
from enum import IntEnum
from PIL import Image, ImageDraw, ImageFont
import struct
import traceback
from pathlib import Path
from typing import Iterator, Literal
import fastlz
import numpy as np

class Command(IntEnum):
    CMD_WHO_AM_I = 0x01  # Establish communication before driving the screen
    CMD_SET_ORIENTATION = 0x02  # Sets the screen orientation
    CMD_SET_BRIGHTNESS = 0x03  # Sets the screen brightness
    CMD_FULL = 0x04  # Displays an image on the screen
    CMD_SET_BITMAP = 0x05  # Displays an image on the screen
    CMD_ENABLE_HUMITURE_REPORT = 0x06
    CMD_FREE = 0x07
    CMD_SET_UNCONNECT_BRIGHTNESS = 0x10
    CMD_SET_UNCONNECT_ORIENTATION = 0x11
    CMD_SET_BITMAP_WITH_FASTLZ = 0x15
    CMD_SYSTEM_RESET = 0x40
    CMD_SYSTEM_VERSION = 0x42
    CMD_SYSTEM_SERIAL_NUM = 0x43
    CMD_END = 0x0A  # Displays an image on the screen
    CMD_READ = 0x80


class Color(IntEnum):
    WHITE = 0xFFFF
    BLACK = 0x0000
    BLUE = 0x001F
    BRED = 0xF81F
    GRED = 0xFFE0
    GBLUE = 0x07FF
    RED = 0xF800
    MAGENTA = 0xF81F
    GREEN = 0x07E0
    CYAN = 0x7FFF
    YELLOW = 0xFFE0
    BROWN = 0xBC40
    BRRED = 0xFC07
    GRAY = 0x8430
    DARKBLUE = 0x01CF
    LIGHTBLUE = 0x7D7C
    GRAYBLUE = 0x5458
    LIGHTGREEN = 0x841F
    LGRAY = 0xC618
    LGRAYBLUE = 0xA651
    LBBLUE = 0x2B12


class Orientation(IntEnum):
    PORTRAIT = 0
    LANDSCAPE = 2
    REVERSE_PORTRAIT = 1
    REVERSE_LANDSCAPE = 3
    ANY = 4


class lcd_weact:
    def __init__(self, port_name="", port_timeout=0.2,type=None) -> None:
        self.port_name = port_name
        self.port_timeout = port_timeout
        self.type = type
        self.port = None
        if self.type == 0:
            self.width = 320
            self.height = 480
        else:
            self.width = 80
            self.height = 160
        self.serial_rx_thread_quit = 0
        self.temperature = 0
        self.humidness = 0
        self.serial_rx_result = 0
        self.serial_rx_cmd = None
        self.serial_rx_length = 0
        self.serial_rx_data = bytearray()
        self.print_tag = ">> lcd_weact: "

    def auto_open(self):
        port_list = list(list_ports.comports())
        self.port_name = ""
        for i in port_list:
            if "AB" in i[2]:
                print(f"{self.print_tag} find device", i[0])
                if self.type == 0 or self.type == None:
                    self.port_name = i[0]
                    self.type = 0
                    break
            if "AD" in i[2]:
                print(f"{self.print_tag} find device", i[0])
                if self.type == 1 or self.type == None:
                    self.port_name = i[0]
                    self.type = 1
                    break
        if self.type == 0:
            self.width = 320
            self.height = 480
        else:
            self.width = 80
            self.height = 160
        if self.port_name != "":
            time.sleep(1)
            return self.open()
        return False

    def open(self):
        try:
            if self.port != None:
                self.close()
            self.port = serial.Serial(
                self.port_name, 1152000, 8, "N", 1, timeout=self.port_timeout
            )
            self.serial_rx_thread_quit = 0
            receive_thread = threading.Thread(target=self.receive_data, args=(self.port,))  
            receive_thread.start()
            print(f"{self.print_tag} Rx Thread Start.")
            return True
        except Exception as e:
            print(f"{self.print_tag} {e}")
            self.port = None
            return False

    def receive_data(self,ser:serial.Serial):  
        while self.serial_rx_thread_quit == 0:  
            try:
                if ser.in_waiting > 0:  
                    cmd = ser.read(1)
                    if cmd[0] == Command.CMD_ENABLE_HUMITURE_REPORT | Command.CMD_READ:
                        data = ser.read(5)
                        if len(data) == 5 and data[4] == Command.CMD_END:
                            unpack = struct.unpack("<Hh", data[0:4])
                            self.temperature = unpack[0]
                            self.humidness = unpack[1]
                    elif self.serial_rx_cmd != None:
                        if cmd[0] == self.serial_rx_cmd:
                            if self.serial_rx_length:
                                length = self.serial_rx_length-1
                                data = ser.read(length)
                                if len(data) == length:
                                    if data[length-1] == Command.CMD_END:
                                        self.serial_rx_data = data
                                        self.serial_rx_result = 1
                                        self.serial_rx_cmd = None
                                    else:
                                        self.serial_rx_result = -1
                                        self.serial_rx_cmd = None
                                else:
                                    self.serial_rx_result = -1
                                    self.serial_rx_cmd = None
                            else:
                                data = ser.readline()
                                if len(data) > 1:
                                    if int(data[-1]) == Command.CMD_END:
                                        self.serial_rx_data = data
                                        self.serial_rx_result = 1
                                        self.serial_rx_cmd = None
                                    else:
                                        self.serial_rx_result = -1
                                        self.serial_rx_cmd = None
                                else:
                                    self.serial_rx_result = -1
                                    self.serial_rx_cmd = None
            except:
                traceback.print_exc()
                break
            time.sleep(0.1)
        self.serial_rx_thread_quit = 2
        print(f"{self.print_tag} Rx Thread Quit.")

    def close(self):
        try:
            if self.port != None:
                if self.port.is_open:
                    print(f"{self.print_tag} Quit Rx Thread...")
                    if self.serial_rx_thread_quit == 0:
                        self.serial_rx_thread_quit = 1
                        timeout = 0
                        while self.serial_rx_thread_quit == 1:
                            time.sleep(0.1)
                            timeout = timeout + 1
                            if timeout > 20:
                                break
                    self.port.close()
            self.port = None
        except:
            traceback.print_exc()
            self.port = None

    def write_cmd(self, cmd: bytearray):
        self.port.write(cmd)
        return True

    def read_cmd_result(self):
        read = self.port.readline()
        return read

    def read_cmd_result(self, cmd,length):
        self.serial_rx_result = 0
        self.serial_rx_length = length
        self.serial_rx_cmd = cmd
        timeout = 0
        while True:
            if self.serial_rx_result == 1:
                self.serial_rx_result = 0
                return self.serial_rx_data
            elif self.serial_rx_result == -1:
                return None
            time.sleep(0.01)
            timeout = timeout + 1
            if timeout > 20:
                self.serial_rx_cmd = None
                self.serial_rx_result = 0
                return None

    def get_device_info(self):
        byteBuffer = bytearray(2)
        byteBuffer[0] = Command.CMD_WHO_AM_I | Command.CMD_READ
        byteBuffer[1] = Command.CMD_END
        self.write_cmd(byteBuffer)
        result = self.read_cmd_result(byteBuffer[0],0)
        if result != None and len(result) > 1:
            return result[:-1]
        else:
            return None

    def get_device_version(self):
        byteBuffer = bytearray(2)
        byteBuffer[0] = Command.CMD_SYSTEM_VERSION | Command.CMD_READ
        byteBuffer[1] = Command.CMD_END
        self.write_cmd(byteBuffer)
        result = self.read_cmd_result(byteBuffer[0],0)
        if result != None and len(result) > 1:
            return result[:-1]
        else:
            return None
    
    def get_device_serial_num(self):
        byteBuffer = bytearray(2)
        byteBuffer[0] = Command.CMD_SYSTEM_SERIAL_NUM | Command.CMD_READ
        byteBuffer[1] = Command.CMD_END
        self.write_cmd(byteBuffer)
        result = self.read_cmd_result(byteBuffer[0],0)
        if result != None and len(result) > 1:
            return result[:-1]
        else:
            return None
    
    def set_device_orientation(self, orientation: Orientation = Orientation.PORTRAIT):
        if orientation > 4 or orientation < 0:
            return False
        byteBuffer = bytearray(3)
        byteBuffer[0] = Command.CMD_SET_ORIENTATION
        byteBuffer[1] = orientation & 0xFF
        byteBuffer[2] = Command.CMD_END
        if self.write_cmd(byteBuffer) == True:
            if orientation <= 1:
                if self.type == 0:
                    self.width = 320
                    self.height = 480
                else:
                    self.width = 80
                    self.height = 160
            else:
                if self.type == 0:
                    self.width = 480
                    self.height = 320
                else:
                    self.width = 160
                    self.height = 80
            return True
        else:
            return False

    def get_device_orientation(self):
        byteBuffer = bytearray(2)
        byteBuffer[0] = Command.CMD_SET_ORIENTATION | Command.CMD_READ
        byteBuffer[1] = Command.CMD_END
        self.write_cmd(byteBuffer)
        result = self.read_cmd_result(byteBuffer[0],3)
        if result != None and len(result) == 2:
            if result[0] <= 1:
                if self.type == 0:
                    self.width = 320
                    self.height = 480
                else:
                    self.width = 80
                    self.height = 160
            else:
                if self.type == 0:
                    self.width = 480
                    self.height = 320
                else:
                    self.width = 160
                    self.height = 80
            return result[0]
        else:
            return None

    def set_device_brightness(self, brightness: int, change_time_ms: int):
        if brightness > 256 or brightness < 0:
            return False
        if change_time_ms > 5000 or change_time_ms < 0:
            return False
        byteBuffer = bytearray(5)
        byteBuffer[0] = Command.CMD_SET_BRIGHTNESS
        byteBuffer[1] = brightness & 0xFF
        byteBuffer[2] = change_time_ms & 0xFF
        byteBuffer[3] = change_time_ms >> 8 & 0xFF
        byteBuffer[4] = Command.CMD_END
        return self.write_cmd(byteBuffer)

    def get_device_brightness(self):
        byteBuffer = bytearray(2)
        byteBuffer[0] = Command.CMD_SET_BRIGHTNESS | Command.CMD_READ
        byteBuffer[1] = Command.CMD_END
        self.write_cmd(byteBuffer)
        result = self.read_cmd_result(byteBuffer[0],3)
        if result != None and len(result) == 2:
            return result[0]
        else:
            return None
        
    def set_device_free(self):
        byteBuffer = bytearray(2)
        byteBuffer[0] = Command.CMD_FREE
        byteBuffer[1] = Command.CMD_END
        return self.write_cmd(byteBuffer)
        
    def set_device_unconnect_brightness(self, brightness: int):
        if brightness > 256 or brightness < 0:
            return False
        byteBuffer = bytearray(3)
        byteBuffer[0] = Command.CMD_SET_UNCONNECT_BRIGHTNESS
        byteBuffer[1] = brightness & 0xFF
        byteBuffer[2] = Command.CMD_END
        return self.write_cmd(byteBuffer)

    def get_device_unconnect_brightness(self):
        byteBuffer = bytearray(2)
        byteBuffer[0] = Command.CMD_SET_UNCONNECT_BRIGHTNESS | Command.CMD_READ
        byteBuffer[1] = Command.CMD_END
        self.write_cmd(byteBuffer)
        result = self.read_cmd_result(byteBuffer[0],3)
        if result != None and len(result) == 2:
            return result[0]
        else:
            return None

    def set_device_unconnect_orientation(self, orientation: int):
        if orientation > 4 or orientation < 0:
            return False
        byteBuffer = bytearray(3)
        byteBuffer[0] = Command.CMD_SET_UNCONNECT_ORIENTATION
        byteBuffer[1] = orientation & 0xFF
        byteBuffer[2] = Command.CMD_END
        return self.write_cmd(byteBuffer)

    def get_device_unconnect_orientation(self):
        byteBuffer = bytearray(2)
        byteBuffer[0] = Command.CMD_SET_UNCONNECT_ORIENTATION | Command.CMD_READ
        byteBuffer[1] = Command.CMD_END
        self.write_cmd(byteBuffer)
        result = self.read_cmd_result(byteBuffer[0],3)
        if result != None and len(result) == 2:
            return result[0]
        else:
            return None

    def set_device_humiture_report_time(self, time_ms: int):
        if time_ms > 0xFFFF or (time_ms < 500 and time_ms != 0):
            return False
        byteBuffer = bytearray(4)
        byteBuffer[0] = Command.CMD_ENABLE_HUMITURE_REPORT
        byteBuffer[1] = time_ms & 0xFF
        byteBuffer[2] = time_ms >> 8 & 0xFF
        byteBuffer[3] = Command.CMD_END
        return self.write_cmd(byteBuffer)
    
    def get_device_humiture_report(self):
        return self.temperature, self.humidness

    def device_reset(self):
        byteBuffer = bytearray(2)
        byteBuffer[0] = Command.CMD_SYSTEM_RESET
        byteBuffer[1] = Command.CMD_END
        if self.write_cmd(byteBuffer) == True:
            self.close()
            time.sleep(3)
            self.open()

    def full(self, color: int):
        if color > 0xFFFF or color < 0:
            return False
        
        xe = self.width
        ye = self.height

        byteBuffer = bytearray(12)
        byteBuffer[0] = Command.CMD_FULL
        byteBuffer[1] = 0
        byteBuffer[2] = 0
        byteBuffer[3] = 0
        byteBuffer[4] = 0
        byteBuffer[5] = (xe-1) & 0xff
        byteBuffer[6] = (xe >> 8) & 0xff
        byteBuffer[7] = (ye-1) & 0xff
        byteBuffer[8] = (ye >> 8) & 0xff
        byteBuffer[9] = color & 0xFF
        byteBuffer[10] = color >> 8 & 0xFF
        byteBuffer[11] = Command.CMD_END
        return self.write_cmd(byteBuffer)

    def set_xy_address(self, xs: int, ys: int, xe: int, ye: int):
        if xs >= self.width or xs < 0:
            return False
        if xe >= self.width or xe < 0:
            return False
        if ys >= self.height or ys < 0:
            return False
        if ye >= self.height or ye < 0:
            return False
        if xs >= xe:
            return False
        if ys >= ye:
            return False

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

        return self.write_cmd(byteBuffer)
    
    def chunked(self, data: bytes, chunk_size: int) -> Iterator[bytes]:
        for i in range(0, len(data), chunk_size):
            yield data[i : i + chunk_size]

    def image_to_RGB565(self, image: Image.Image, endianness: Literal["big", "little"]) -> bytes:
        if image.mode not in ["RGB", "RGBA"]:
            # we need the first 3 channels to be R, G and B
            image = image.convert("RGB")

        rgb = np.asarray(image)

        # flatten the first 2 dimensions (width and height) into a single stream
        # of RGB pixels
        rgb = rgb.reshape((image.size[1] * image.size[0], -1))

        # extract R, G, B channels and promote them to 16 bits
        r = rgb[:, 0].astype(np.uint16)
        g = rgb[:, 1].astype(np.uint16)
        b = rgb[:, 2].astype(np.uint16)

        # construct RGB565
        r = r >> 3
        g = g >> 2
        b = b >> 3
        rgb565 = (r << 11) | (g << 5) | b

        # serialize to the correct endianness
        if endianness == "big":
            typ = ">u2"
        else:
            typ = "<u2"
        return rgb565.astype(typ).tobytes()

    def show_bitmap(self, xs: int, ys: int, bitmap: Image, use_fastlz:bool = False):

        result = False

        image_height = bitmap.height
        image_width = bitmap.width

        if image_height > self.height or image_width > self.width:
            return False

        xe = image_width + xs - 1
        ye = image_height + ys - 1

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

        line_to_send_size = self.width * 4

        rgb565le = self.image_to_RGB565(bitmap,'little')

        if use_fastlz:
            chunk_size = line_to_send_size
            byteBuffer[0] = Command.CMD_SET_BITMAP_WITH_FASTLZ
            self.write_cmd(byteBuffer)
            # declare the chunk size
            for i in range(0, len(rgb565le), chunk_size):
                chunk = rgb565le[i:i+chunk_size]
                compressed_chunk = fastlz.compress(chunk)
                chunk_with_header = struct.pack("<HH", len(chunk), len(compressed_chunk[4:])) + compressed_chunk[4:]
                result = self.write_cmd(chunk_with_header)
        else:
            self.write_cmd(byteBuffer)
            for chunk in self.chunked(rgb565le,line_to_send_size):
                result = self.write_cmd(chunk)

        return result

    def show_bitmap_comp(self, xs: int, ys: int, bitmap: Image, use_fastlz:bool = False, last_bitmap: Image = None, n: int = 4, m: int = 4):
        if last_bitmap is None or last_bitmap.size != bitmap.size:
            return self.show_bitmap(xs, ys, bitmap, use_fastlz)
        result = False
        width, height = bitmap.size
        block_width = width // n
        block_height = height // m
        
        arr1 = np.array(last_bitmap)
        arr2 = np.array(bitmap)
        
        for j in range(m):
            for i in range(n):
                x1 = i * block_width
                y1 = j * block_height
                x2 = x1 + block_width if i < n-1 else width
                y2 = y1 + block_height if j < m-1 else height
                
                block1 = arr1[y1:y2, x1:x2]
                block2 = arr2[y1:y2, x1:x2]
                
                if not np.array_equal(block1, block2):
                    diff_block = bitmap.crop((x1, y1, x2, y2))
                    self.show_bitmap(xs + x1, ys + y1, diff_block, use_fastlz)
                    result = True
        return result

    def show_text(
        self,
        xs: int,
        ys: int,
        text: str,
        color,
        size: int,
        align: str,
        anchor: str,
        bitmap: Image,
    ):
        image = bitmap.copy()
        draw = ImageDraw.Draw(image)
        if self.type == 0 or size > 12:
            font = ImageFont.truetype(utils.get_root_dir() / "res" / "fonts" / "SourceHanSansCN" / "SourceHanSansCN-Normal.otf", size)
        else:
            if size == 12:
                font = ImageFont.truetype(utils.get_root_dir() / "res" / "fonts" / "fusion-pixel" / "fusion-pixel-12px-monospaced-zh_hans.otf", size)
            elif size == 10:
                font = ImageFont.truetype(utils.get_root_dir() / "res" / "fonts" / "fusion-pixel" / "fusion-pixel-10px-monospaced-zh_hans.otf", size)  
            elif size == 8:
                font = ImageFont.truetype(utils.get_root_dir() / "res" / "fonts" / "fusion-pixel" / "fusion-pixel-8px-monospaced-zh_hans.otf", size)
            else:
                font = ImageFont.truetype(utils.get_root_dir() / "res" / "fonts" / "SourceHanSansCN" / "SourceHanSansCN-Normal.otf", size)
        left, top, right, bottom = draw.textbbox(
            (xs, ys), text, font=font, align=align, anchor=anchor
        )
        draw.text((xs, ys), text, font=font, fill=color)
        left = max(left, 0)
        top = max(top, 0)
        right = min(right, self.width)
        bottom = min(bottom, self.height)
        image = image.crop(box=(left, top, right, bottom))
        return self.show_bitmap(xs, ys, image)
    
if __name__ == "__main__":
    import tkinter
    from tkinter import ttk

    if getattr(sys, "frozen", False):
        executable_name = os.path.splitext(os.path.basename(sys.executable))[0]
        executable_dir = Path(sys.executable).parent
    else:
        executable_name = os.path.splitext(os.path.basename(__file__))[0]
        executable_dir = Path(__file__).parent

    sys.path.append(str(executable_dir.parent))

    import lib.utils as utils
    os.chdir(utils.get_root_dir())

    import argparse
    parser = argparse.ArgumentParser(description="WeActStudio System Monitor configure")
    parser.add_argument(
        "type",
        type=int,
        help="Type",
    )

    args = parser.parse_args()
    
    if getattr(sys, "frozen", False):
        utils.std_redirect_logfile(executable_name)

    # Loading Language
    _ = utils.set_language(executable_name)

    class tk_gui:
        def __init__(self, lcd: lcd_weact) -> None:
            self.lcd = lcd
            self.device_connected = False
            if self.lcd.auto_open() == False:
                device_state = _("Device not connected !")
                self.device_connected = False
            else:
                device_state = _("Device connected !")
                self.device_connected = True

            self.window = tkinter.Tk()
            self.window.title(_("WeAct Studio Display Configuration"))
            # self.window.geometry("350x285")
            self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.window.iconphoto(True, tkinter.PhotoImage(file=utils.get_root_dir() / "res" / "icons" / "logo.png"))
            self.window.resizable(False, False)
            self.main_frame = tkinter.Frame(self.window)
            self.main_frame.pack()

            self.device_state_string = tkinter.StringVar()
            self.device_state_string.set(device_state)
            device_state_label = ttk.Label(
                self.main_frame, textvariable=self.device_state_string
            )
            device_state_label.grid(
                row=0, column=0, columnspan=2, padx=5, pady=5, sticky="W"
            )

            device_refresh_button = ttk.Button(
                self.main_frame, text=_("Refresh"), command=self.on_refresh_device_open
            )
            device_refresh_button.grid(row=0, column=2, padx=5, pady=5, sticky="W" + "E")

            orient_label = ttk.Label(self.main_frame, text=_("Orientation"))
            orient_label.grid(row=4, column=0, padx=5, pady=5, sticky="W")

            self.orient_map = [
                "PORTRAIT",
                "REVERSE_PORTRAIT",
                "LANDSCAPE",
                "REVERSE_LANDSCAPE",
                "ANY",
            ]
            self.orient_cb = ttk.Combobox(
                self.main_frame, values=self.orient_map[0:-1], state="readonly"
            )
            self.orient_cb.grid(row=4, column=1, columnspan=2, padx=5, pady=5, sticky="W" + "E")

            self.brightness_label = ttk.Label(self.main_frame, text=_("Brightness"))
            self.brightness_label.grid(row=6, column=0, padx=5, pady=5, sticky="W")
            self.brightness_slider = ttk.Scale(
                self.main_frame,
                from_=0,
                to=100,
                orient=tkinter.HORIZONTAL,
            )
            self.brightness_slider.grid(row=6, column=2)
            self.brightness_string = tkinter.StringVar()
            self.brightness_string.set("10%")
            brightness_val_label = ttk.Label(
                self.main_frame, width=10, textvariable=self.brightness_string
            )
            brightness_val_label.grid(row=6, column=1, padx=5, pady=5)

            u_orient_label = ttk.Label(self.main_frame, text=_("Unconnect Orientation"))
            u_orient_label.grid(row=7, column=0, padx=5, pady=5, sticky="W")

            self.u_orient_cb = ttk.Combobox(
                self.main_frame, value=self.orient_map, state="readonly"
            )
            self.u_orient_cb.grid(row=7, column=1, columnspan=2, padx=5, pady=5, sticky="W" + "E")

            self.u_brightness_label = ttk.Label(self.main_frame, text=_("Unconnect Brightness"))
            self.u_brightness_label.grid(row=8, column=0, padx=5, pady=5, sticky="W")
            self.u_brightness_slider = ttk.Scale(
                self.main_frame,
                from_=0,
                to=100,
                orient=tkinter.HORIZONTAL,
                
            )
            self.u_brightness_slider.grid(row=8, column=2)
            self.u_brightness_string = tkinter.StringVar()
            self.u_brightness_string.set("10%")
            u_brightness_val_label = ttk.Label(
                self.main_frame, width=10, textvariable=self.u_brightness_string
            )
            u_brightness_val_label.grid(row=8, column=1, padx=5, pady=5)

            self.device_reset_button = ttk.Button(
                self.main_frame, text=_("Device Reset"), command=self.on_device_reset
            )
            self.device_reset_button.grid(row=9, column=0, padx=5, pady=5, sticky="W" + "E")

            self.WHO_AM_I_string = tkinter.StringVar()
            self.WHO_AM_I_string.set("WHO_AM_I: ")
            WHO_AM_I_label = ttk.Label(
                self.main_frame, textvariable=self.WHO_AM_I_string
            )
            WHO_AM_I_label.grid(row=1, column=0,columnspan=3, padx=5, pady=5, sticky="W")

            self.Version_string = tkinter.StringVar()
            self.Version_string.set(_("Version: "))
            Version_label = ttk.Label(
                self.main_frame, textvariable=self.Version_string
            )
            Version_label.grid(row=2, column=0,columnspan=3, padx=5, pady=5, sticky="W")

            self.Serial_Num_string = tkinter.StringVar()
            self.Serial_Num_string.set(_("Serial Num: "))
            Serial_Num_label = ttk.Label(
                self.main_frame, textvariable=self.Serial_Num_string
            )
            Serial_Num_label.grid(row=3, column=0,columnspan=3, padx=5, pady=5, sticky="W")

            self.device_unconnect_orientation_last = 0
            self.device_orientation_last = 0
            self.device_brightness_last = 0
            self.device_unconnect_brightness_last = 0
            image = Image.open(utils.get_root_dir() / "res" / "backgrounds" / "logo.png")
            if self.lcd.type == 0:
                self.image_logo = image.resize((200,200))
            else:
                self.image_logo = image.resize((80,80))

            self.refresh_device_state()
            self.window_refresh_tick = 0
            self.window_refresh()

            self.window.mainloop()
            pass

        def on_refresh_device_open(self):
            if self.lcd.auto_open() == False:
                device_state = _("Device not connected !")
                self.device_connected = False
            else:
                device_state = _("Device connected !")
                self.device_connected = True
                self.refresh_device_state()
            self.device_state_string.set(device_state)

        def on_device_reset(self):
            if self.device_connected == True:
                self.lcd.device_reset()
                self.refresh_device_state()

        def refresh_device_state(self):
            if self.device_connected == True:
                try:
                    value = self.lcd.get_device_unconnect_orientation()
                    if value != None and self.device_connected:
                        self.u_orient_cb.current(value)
                        self.device_unconnect_orientation_last = value
                    else:
                        self.device_connected = False

                    value = self.lcd.get_device_orientation()
                    if value != None and self.device_connected:
                        self.orient_cb.current(value)
                        self.device_orientation_last = value
                    else:
                        self.device_connected = False

                    self.lcd.full(Color.BLACK)
                    time.sleep(0.05)

                    self.lcd.set_device_brightness(10,1000)
                    value = 10
                    converted_level = round((value / 255) * 100)
                    if value != None and self.device_connected:
                        self.brightness_string.set(str(converted_level) + "%")
                        self.brightness_slider.set(converted_level)
                        self.device_brightness_last = converted_level
                    else:
                        self.device_connected = False

                    value = self.lcd.get_device_unconnect_brightness()
                    converted_level = round((value / 255) * 100)
                    if converted_level != None and self.device_connected:
                        self.u_brightness_string.set(str(converted_level) + "%")
                        self.u_brightness_slider.set(converted_level)
                        self.device_unconnect_brightness_last = converted_level
                    else:
                        self.device_connected = False
                    
                    value = self.lcd.get_device_info()
                    if value != None:
                        self.WHO_AM_I_string.set(value.decode())

                    value = self.lcd.get_device_version()
                    if value != None:
                        self.Version_string.set(_("Version: ") + value.decode())

                    value = self.lcd.get_device_serial_num()
                    if value != None:
                        self.Serial_Num_string.set(_("Serial Num: ") + value.decode())
                    
                    if self.lcd.type == 0:
                        self.lcd.set_device_humiture_report_time(1000)

                    if self.device_orientation_last <= 1:
                        self.device_show_image_portrait()
                    else:
                        self.device_show_image_landscape()
                except:
                    traceback.print_exc()

        def device_show_image_portrait(self):
            if self.device_connected == True:
                if self.lcd.type == 0:
                    image_r = Image.new(
                                'RGB',
                                (100, 100),
                                0x0000ff
                            )
                    image_g = Image.new(
                                'RGB',
                                (100, 100),
                                0x00ff00
                            )
                    image_b = Image.new(
                                'RGB',
                                (100, 100),
                                0xff0000
                            )

                    # full lcd color
                    self.lcd.full(Color.BLACK)

                    # show red color
                    self.lcd.show_bitmap(0,0,image_r)
                    # show green color
                    self.lcd.show_bitmap(110,0,image_g)
                    # show blue color
                    self.lcd.show_bitmap(220,0,image_b)
                    # show pic
                    lcd.show_bitmap(lcd.width//2-self.image_logo.width//2,110,self.image_logo)
                    # show text
                    image = Image.new(
                                'RGB',
                                (320, 480),
                                0x000000
                            )
                    lcd.show_text(10,320,_("Hello World !"),(255,255,255),20,'left',None,image)
                    lcd.show_text(10,350,_("Hello WeAct Studio !"),(255,255,255),20,'left',None,image)
                else:
                    image_r = Image.new(
                                'RGB',
                                (10, 10),
                                0x0000ff
                            )
                    image_g = Image.new(
                                'RGB',
                                (10, 10),
                                0x00ff00
                            )
                    image_b = Image.new(
                                'RGB',
                                (10, 10),
                                0xff0000
                            )
                    
                    # full lcd color
                    self.lcd.full(Color.BLACK)
                    
                    # show red color
                    self.lcd.show_bitmap(0,0,image_r,True)

                    # show green color
                    self.lcd.show_bitmap(20,0,image_g,True)
                    # show blue color
                    self.lcd.show_bitmap(40,0,image_b,True)
                    # show pic
                    lcd.show_bitmap(lcd.width//2-self.image_logo.width//2,20,self.image_logo,True)
                    # show text
                    image = Image.new(
                                'RGB',
                                (80, 160),
                                0x000000
                            )
                    lcd.show_text(2,105,"Hello World!",(255,255,255),12,'left',None,image)
                    lcd.show_text(2,117,"你好世界!",(255,255,255),12,'left',None,image)
                    lcd.show_text(2,131,"Hello WeAct!",(255,255,255),12,'left',None,image)
                    lcd.show_text(2,143,"你好微行!",(255,255,255),12,'left',None,image)


        def device_show_image_landscape(self):
            if self.device_connected == True:
                if self.lcd.type == 0:
                    image_r = Image.new(
                                'RGB',
                                (100, 100),
                                0x0000ff
                            )
                    image_g = Image.new(
                                'RGB',
                                (100, 100),
                                0x00ff00
                            )
                    image_b = Image.new(
                                'RGB',
                                (100, 100),
                                0xff0000
                            )

                    # full lcd color
                    self.lcd.full(Color.BLACK)

                    # show red color
                    self.lcd.show_bitmap(0,0,image_r)
                    # show green color
                    self.lcd.show_bitmap(110,0,image_g)
                    # show blue color
                    self.lcd.show_bitmap(220,0,image_b)
                    # show pic
                    lcd.show_bitmap(10,110,self.image_logo)
                    # show text
                    image = Image.new(
                                'RGB',
                                (480, 320),
                                0x000000
                            )
                    lcd.show_text(250,200,_("Hello World !"),(255,255,255),20,'left',None,image)
                    lcd.show_text(250,230,_("Hello WeAct Studio !"),(255,255,255),20,'left',None,image)
                else:
                    image_r = Image.new(
                                'RGB',
                                (10, 10),
                                0x0000ff
                            )
                    image_g = Image.new(
                                'RGB',
                                (10, 10),
                                0x00ff00
                            )
                    image_b = Image.new(
                                'RGB',
                                (10, 10),
                                0xff0000
                            )

                    # full lcd color
                    self.lcd.full(Color.BLACK)

                    # show red color
                    self.lcd.show_bitmap(0,0,image_r)
                    # show green color
                    self.lcd.show_bitmap(0,20,image_g,True)
                    # show blue color
                    self.lcd.show_bitmap(0,40,image_b,True)
                    # show pic
                    lcd.show_bitmap(lcd.width//2-self.image_logo.width//2-20,lcd.height//2-self.image_logo.height//2,self.image_logo,True)
                    # show text
                    image = Image.new(
                                'RGB',
                                (160, 80),
                                0x000000
                            )
                    lcd.show_text(105,22,"Hello World!",(255,255,255),8,'left',None,image)
                    lcd.show_text(105,32,"你好世界!",(255,255,255),8,'left',None,image)
                    lcd.show_text(105,42,"Hello WeAct!",(255,255,255),8,'left',None,image)
                    lcd.show_text(105,52,"你好微行!",(255,255,255),8,'left',None,image)


        def on_closing(self):
            if self.lcd.port != None:
                if self.lcd.port.is_open == True:
                    if self.lcd.type == 0:
                        self.lcd.set_device_humiture_report_time(0)
                    self.lcd.set_device_brightness(0,500)
                    self.lcd.set_device_free()
                    self.lcd.close()
            try:
                sys.exit(0)
            except:
                os._exit(0)

        def window_refresh(self):
            if self.device_connected == True:
                try:
                    if self.lcd.serial_rx_thread_quit == 2:
                        raise Exception("serial_rx_thread_quit")
                    device_need_refresh = False
                    value = self.u_orient_cb.current()
                    if self.device_unconnect_orientation_last != value:
                        self.lcd.set_device_unconnect_orientation(value)
                        self.device_unconnect_orientation_last = value

                    value = self.orient_cb.current()
                    if self.device_orientation_last != value:
                        self.lcd.set_device_orientation(value)
                        self.device_orientation_last = value
                        device_need_refresh = True

                    value = self.brightness_slider.get()
                    if self.device_brightness_last != value:
                        converted_level = round((value / 100) * 255)
                        self.lcd.set_device_brightness(converted_level, 500)
                        self.brightness_string.set(str(round(value)) + "%")
                        self.device_brightness_last = value

                    value = self.u_brightness_slider.get()
                    if self.device_unconnect_brightness_last != value:
                        converted_level = round((value / 100) * 255)
                        self.lcd.set_device_unconnect_brightness(converted_level)
                        self.u_brightness_string.set(str(round(value)) + "%")
                        self.device_unconnect_brightness_last = value

                    if device_need_refresh:
                        if self.device_orientation_last <= 1:
                            self.device_show_image_portrait()
                        else:
                            self.device_show_image_landscape()
                    
                    if self.window_refresh_tick >= 2 and self.lcd.type == 0:
                        self.window_refresh_tick = 0
                        temperature,humidness = self.lcd.get_device_humiture_report()
                        if self.device_orientation_last <= 1:
                            if temperature != None and humidness != None:
                                image = Image.new(
                                    'RGB',
                                    (320, 480),
                                    0x000000
                                )
                                lcd.show_text(10,380,_("Temperature: ")+'{:.2f}'.format(temperature/100)+"℃",(255,255,255),20,'left',None,image)
                                lcd.show_text(10,410,_("Humidness: ")+'{:.2f}'.format(humidness/100,2)+"%",(255,255,255),20,'left',None,image)
                        else:
                            if temperature != None and humidness != None:
                                image = Image.new(
                                    'RGB',
                                    (480, 320),
                                    0x000000
                                )
                                lcd.show_text(250,260,_("Temperature: ")+'{:.2f}'.format(temperature/100)+"℃",(255,255,255),20,'left',None,image)
                                lcd.show_text(250,290,_("Humidness: ")+'{:.2f}'.format(humidness/100,2)+"%",(255,255,255),20,'left',None,image)
                except:
                    traceback.print_exc()
                    self.lcd.close()
                    device_state = _("Device Unconnected !")
                    self.device_connected = False
                    self.device_state_string.set(device_state)

                self.window_refresh_tick = self.window_refresh_tick + 1
            self.window.after(500, self.window_refresh)

    type = args.type
    lcd = lcd_weact(port_name="",port_timeout=0.2,type=type)
    gui = tk_gui(lcd)
