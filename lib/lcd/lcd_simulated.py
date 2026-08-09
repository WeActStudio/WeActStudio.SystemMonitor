# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
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

from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO

from lib.lcd.lcd_comm import *

screenshot_lock = threading.Lock()
SCREENSHOT_FILE = BytesIO()  
WEBSERVER_PORT = 5678


# This webserver offer a blank page displaying simulated screen with auto-refresh
class SimulatedLcdWebServer(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes("""
            <style>
                body {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background-color: #f4f4f4;
                }
                #setBlackBtn {
                    padding: 12px 24px;
                    font-size: 16px;
                    border: none;
                    border-radius: 8px;
                    background-color: #007BFF;
                    color: white;
                    cursor: pointer;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    transition: all 0.3s ease;
                }
                #setBlackBtn:hover {
                    background-color: #0056b3;
                    box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
                }
            </style>
            """, "utf-8"))
            self.wfile.write(bytes("<body>", "utf-8"))
            self.wfile.write(bytes("<img src=\"image\" id=\"myImage\" onerror=\"this.src=''; this.alt='Get Fail';\" />", "utf-8"))
            self.wfile.write(bytes("<button id='setBlackBtn' style='margin-top: 20px;'>Set Background to Black</button>", "utf-8"))
            self.wfile.write(bytes("<script>", "utf-8"))
            js_code = """
            let isBlack = false;
            const button = document.getElementById('setBlackBtn');
            button.addEventListener('click', function() {
                if (isBlack) {
                    document.body.style.backgroundColor = 'white';
                    isBlack = false;
                    button.textContent = 'Set Background to Black';
                } else {
                    document.body.style.backgroundColor = 'black';
                    isBlack = true;
                    button.textContent = 'Set Background to White';
                }
            });
            setInterval(function() {
                var myImageElement = document.getElementById('myImage');
                myImageElement.src = `image?rand=${Math.random()}`;
            }, 250);
            """
            self.wfile.write(bytes(js_code, "utf-8"))
            self.wfile.write(bytes("</script>", "utf-8"))
            self.wfile.write(bytes("</body>", "utf-8"))
        elif self.path.startswith("/" + "image"):
            self.send_response(200)
            self.send_header('Content-type', 'image/png')
            self.end_headers()
            with screenshot_lock:
                SCREENSHOT_FILE.seek(0)
                self.wfile.write(SCREENSHOT_FILE.getvalue())


# Simulated display: write on a file instead of serial port
class LcdSimulated(LcdComm):
    def __init__(self, com_port: str = "AUTO", display_width: int = 320, display_height: int = 480,
                 update_queue: queue.Queue = None):
        LcdComm.__init__(self, com_port, display_width, display_height, update_queue)
        self.screen_image = Image.new("RGB", (self.get_width(), self.get_height()), (0, 0, 0))
        with screenshot_lock:
            SCREENSHOT_FILE.truncate(0)
            SCREENSHOT_FILE.seek(0)
            self.screen_image.save(SCREENSHOT_FILE, "PNG")
        self.orientation = Orientation.PORTRAIT

        try:
            self.webServer = HTTPServer(("localhost", WEBSERVER_PORT), SimulatedLcdWebServer)
            logger.debug("To see your simulated screen, open http://%s:%d in a browser" % ("localhost", WEBSERVER_PORT))
            threading.Thread(target=self.webServer.serve_forever).start()
        except OSError:
            logger.error("Error starting webserver! An instance might already be running on port %d." % WEBSERVER_PORT)

    def __del__(self):
        self.closeSerial()

    @staticmethod
    def auto_detect_com_port():
        return None

    def closeSerial(self):
        logger.debug("Shutting down web server")
        self.webServer.shutdown()

    def InitializeComm(self,use_compress:int = 0):
        pass

    def Reset(self):
        pass

    def Clear(self):
        self.SetOrientation(self.orientation)

    def Full(self,color: Tuple[int, int, int] = (0, 0, 0)):
        with self.update_queue_mutex:
            self.screen_image = Image.new("RGB", (self.get_width(), self.get_height()), color)
            with screenshot_lock:
                SCREENSHOT_FILE.truncate(0)
                SCREENSHOT_FILE.seek(0)
                self.screen_image.save(SCREENSHOT_FILE, "PNG")

    def ScreenOff(self):
        pass

    def ScreenOn(self):
        pass

    def SetBrightness(self, level: int = 25):
        pass

    def SetBackplateLedColor(self, led_color: Tuple[int, int, int] = (0, 0, 0)):
        pass

    def SetOrientation(self, orientation: Orientation = Orientation.PORTRAIT):
        self.orientation = orientation
        # Just draw the screen again with the new width/height based on orientation
        with self.update_queue_mutex:
            self.screen_image = Image.new("RGB", (self.get_width(), self.get_height()), (0, 0, 0))
            with screenshot_lock:
                SCREENSHOT_FILE.truncate(0)
                SCREENSHOT_FILE.seek(0)
                self.screen_image.save(SCREENSHOT_FILE, "PNG")

    def DisplayPILImage(
            self,
            image: Image.Image,
            x: int = 0, y: int = 0,
            image_width: int = 0,
            image_height: int = 0
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

        assert x >= 0, f"Display Image X {x} coordinate must be >= 0"
        assert y >= 0, f"Display Image Y {y} coordinate must be >= 0"
        assert x <= self.get_width(), f'Display Image X {x} coordinate must be <= display width {self.get_width()}'
        assert y <= self.get_height(), 'Image Y coordinate must be <= display height'
        assert image_height > 0, 'Image height must be > 0'
        assert image_width > 0, 'Image width must be > 0'
        assert x + image_width <= self.get_width(), f'Display Bitmap width exceeds display width {self.get_width()}'
        assert y + image_height <= self.get_height(), f'Display Bitmap height exceeds display height {self.get_height()}'

        with self.update_queue_mutex:
            if image.mode != "RGB":
                image = image.convert("RGB")
            self.screen_image.paste(image, (x, y))
            with screenshot_lock:
                SCREENSHOT_FILE.truncate(0)
                SCREENSHOT_FILE.seek(0)
                self.screen_image.save(SCREENSHOT_FILE, "PNG")
