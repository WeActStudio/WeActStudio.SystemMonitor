#!/usr/bin/env python
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/

# Copyright (C) 2021-2023  Matthieu Houdebine (mathoudebine)
# Copyright (C) 2022-2023  Rollbacke
# Copyright (C) 2022-2023  Ebag333
# Copyright (C) 2022-2023  w1ld3r
# Copyright (C) 2022-2023  Charles Ferguson (gerph)
# Copyright (C) 2022-2023  Russ Nelson (RussNelson)
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

# This file is the system monitor main program to display HW sensors on your screen using themes (see README)
import os
import sys
from pathlib import Path
sys.path.append(os.path.dirname(__file__))
MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    print("[ERROR] Python %s.%s or later is required." % MIN_PYTHON)
    try:
        sys.exit(0)
    except:
        os._exit(0)

try:
    import atexit
    import locale
    import platform
    import signal
    import subprocess
    import time
    from PIL import Image
    from tkinter import messagebox
    import tkinter as tk
    from pynput import keyboard, mouse
    if platform.system() == 'Windows':
        import win32api
        import win32con
        import win32gui

    try:
        import pystray
    except:
        pass
except:
    print("[ERROR] Python dependencies not installed.")
    try:
        sys.exit(0)
    except:
        os._exit(0)

# Loading Language
from library.utils import set_language
_ = set_language(__file__)

import library.utils as utils
import time
LOCKFILE = os.path.join(os.path.dirname(__file__), os.path.basename(__file__)+".lock")
if utils.app_is_running(LOCKFILE):
    print("Error: Another instance of the program is already running.")
    title = _("WeAct Studio System Monitor") + " " + utils.get_version()
    message = _("Error: Another instance of the program is already running.")
    utils.show_messagebox(message=message,title=title,delay=3000)
    time.sleep(3)
    try:
        sys.exit(0)
    except:
        os._exit(0)
else:
    utils.app_set_running(LOCKFILE)

def app_clean():
    global LOCKFILE
    utils.app_end_running(LOCKFILE)
def app_exit():
    try:
        sys.exit(0)
    except:
        os._exit(0)

# Show Start Frame
msg_close_handler = utils.show_messagebox(message=_("Starting ..."),title=_('WeAct Studio System Monitor') + " " + utils.get_version(),delay=0)

from library.log import logger
import library.scheduler as scheduler
from library.display import display
from library.display import get_config_display_free_off
from library.display import get_config_display_brightness

# Start ...

if get_config_display_free_off() == True:
    display_free_off_tick = 0
    IDLE_THRESHOLD = 180  
    activity = True
    display_off = False

    def reset_activity():  
        global activity  
        activity = True  
    
    def on_key_press(key):  
        reset_activity()  
    
    def on_mouse_move(x, y):  
        reset_activity()  
    
    def on_mouse_click(x, y, button, pressed):  
        reset_activity()  
    
    def on_mouse_scroll(x, y, dx, dy):  
        reset_activity()  
    
    keyboard_listener = keyboard.Listener(on_press=on_key_press)  
    mouse_listener = mouse.Listener(  
        on_move=on_mouse_move,
        on_click=on_mouse_click,
        on_scroll=on_mouse_scroll
    )
    
    keyboard_listener.daemon = True
    mouse_listener.daemon = True
    
    keyboard_listener.start()
    mouse_listener.start()
    logger.info('display free off enabled')

# Apply system locale to this program
locale.setlocale(locale.LC_ALL, '')

logger.debug("Using Python %s" % sys.version)

def wait_for_empty_queue(timeout: int = 5):
        # Waiting for all pending request to be sent to display
        logger.info(f"Waiting for {scheduler.get_queue_size()} pending request to be sent to display ({timeout}s max)...")

        wait_time = 0
        while not scheduler.is_queue_empty() and wait_time < timeout and display.lcd.lcd_serial != None and display.lcd.lcd_serial.is_open == True:
            time.sleep(0.1)
            wait_time = wait_time + 0.1

        logger.debug("(Waited %.1fs)" % wait_time)

def clean(tray_icon=None):
    # Remove tray icon just before exit
    if tray_icon:
        tray_icon.visible = False

    # Turn screen and LEDs off before stopping
    display.turn_off()

    # Do not stop the program now in case data transmission was in progress
    # Instead, ask the scheduler to empty the action queue before stopping
    scheduler.STOPPING = True

    # Allow 5 seconds max. delay in case scheduler is not responding
    wait_for_empty_queue(5)

def stop():
    global keyboard_listener,mouse_listener
    if get_config_display_free_off() == True:
        keyboard_listener.stop()  
        time.sleep(0.1)
        keyboard_listener.join(timeout=0.5)
        mouse_listener.stop()
        time.sleep(0.1)
        mouse_listener.join(timeout=0.5)
    # We force the exit to avoid waiting for other scheduled tasks: they may have a long delay!
    app_clean()
    app_exit()

def clean_stop(tray_icon=None):
    utils.show_messagebox(message=_('Exit') + " ...",title=_('WeAct Studio System Monitor') + " " + utils.get_version(),delay=5000)
    time.sleep(0.5)
    clean(tray_icon)
    stop()

def on_signal_caught(signum, frame=None):
    logger.info("Caught signal %d, exiting" % signum)
    clean_stop()

def start_configure():
    utils.run().configure()

def start_main():
    utils.run().main()

def on_configure_tray(tray_icon, item):
    logger.info("Configure from tray icon")
    utils.show_messagebox(message=_('Configure') + ' ' + _("Starting ..."),title=_('WeAct Studio System Monitor') + " " + utils.get_version(),delay=5000)
    time.sleep(0.5)
    clean(tray_icon)
    start_configure()
    stop()

def on_exit_tray(tray_icon, item):
    logger.info("Exit from tray icon")
    clean_stop(tray_icon)

def on_clean_exit(*args):
    logger.info("Program will now exit")
    clean_stop()

def display_init():
    # Initialize the display
    logger.info("Initialize display")
    display.initialize_display()

    # Initialize lcd sensor
    display.initialize_sensor()

    # Start serial queue handler
    scheduler.QueueHandler()

    # Create all static images
    display.display_static_images()

    # Create all static texts
    display.display_static_text()

def scheduler_init():
    # Start sensor scheduled reading. Avoid starting them all at the same time to optimize load
    logger.info("Starting system monitor")
    # Run our jobs that update data
    import library.stats as stats

    scheduler.CPUPercentage()
    time.sleep(0.15)
    scheduler.CPUPower()
    time.sleep(0.15)
    scheduler.CPUFrequency()
    time.sleep(0.15)
    scheduler.CPULoad()
    time.sleep(0.15)
    scheduler.CPUTemperature()
    time.sleep(0.15)
    scheduler.CPUFanSpeed()
    time.sleep(0.15)
    if stats.Gpu.is_available():
        scheduler.GpuStats()
    time.sleep(0.15)
    scheduler.MemoryStats()
    time.sleep(0.15)
    scheduler.DiskStats()
    time.sleep(0.15)
    scheduler.NetStats()
    time.sleep(0.15)
    scheduler.DateStats()
    time.sleep(0.15)
    scheduler.SystemUptimeStats()
    time.sleep(0.15)
    scheduler.CustomStats()
    time.sleep(0.15)
    scheduler.VolumeStats()
    time.sleep(0.15)
    scheduler.LcdSensorTemperature()
    time.sleep(0.15)
    scheduler.LcdSensorHumidness()
    time.sleep(0.15)
    scheduler.LcdRxHandler()
    time.sleep(0.15)
    scheduler.dynamic_images_Init()
    time.sleep(0.15)
    scheduler.dynamic_images_Handler()
    time.sleep(0.15)
    scheduler.dynamic_texts_Init()
    scheduler.dynamic_texts_Handler()
    time.sleep(0.15)
    scheduler.photo_album_Init()
    scheduler.photo_album_Handler()
    time.sleep(0.15)
    scheduler.WeatherStats()
    time.sleep(0.15)
    scheduler.PingStats()
    time.sleep(0.15)
    scheduler.InputMonitorStats()
    time.sleep(0.15)
    scheduler.requests_get_Init()
    scheduler.requests_get_Handler()
    time.sleep(0.15)
    scheduler.media_get_Init()
    scheduler.media_get_Handler()
    time.sleep(0.15)

if platform.system() == "Windows":
    def on_win32_ctrl_event(event):
        """Handle Windows console control events (like Ctrl-C)."""
        if event in (win32con.CTRL_C_EVENT, win32con.CTRL_BREAK_EVENT, win32con.CTRL_CLOSE_EVENT):
            logger.debug("Caught Windows control event %s, exiting" % event)
            clean_stop()
        return 0


    def on_win32_wm_event(hWnd, msg, wParam, lParam):
        """Handle Windows window message events (like ENDSESSION, CLOSE, DESTROY)."""
        logger.debug("Caught Windows window message event %s" % msg)
        if msg == win32con.WM_POWERBROADCAST:
            # WM_POWERBROADCAST is used to detect computer going to/resuming from sleep
            if wParam == win32con.PBT_APMSUSPEND:
                logger.info("Computer is going to sleep, display will turn off")
                display.turn_off()
                scheduler.STOPPING = True
                return 0
            elif wParam == win32con.PBT_APMRESUMEAUTOMATIC:
                logger.info("Computer is resuming from sleep, display will turn on")
                app_clean()
                start_main()
                app_exit()
                return 0
        else:
            # For any other events, the program will stop
            logger.info("Program will now exit")
            clean_stop()
            return 0
        return win32gui.DefWindowProc(hWnd, msg, wParam, lParam)

# Create a tray icon for the program, with an Exit entry in menu
try:
    tray_icon = pystray.Icon(
        name=_('WeAct Studio System Monitor') + " " + utils.get_version(),
        title=_('WeAct Studio System Monitor') + " " + utils.get_version(),
        icon=Image.open(Path(__file__).parent / "res" / "icons" / "logo.png"),
        menu=pystray.Menu(
            pystray.MenuItem(
                text=_('Configure'),
                action=on_configure_tray,default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                text=_('Exit'),
                action=on_exit_tray)
        )
    )
    # For platforms != macOS, display the tray icon now with non-blocking function
    if platform.system() != "Darwin":
        tray_icon.run_detached()
        logger.info("Tray icon has been displayed")
except:
    tray_icon = None
    logger.warning("Tray icon is not supported on your platform")

# Set the different stopping event handlers, to send a complete frame to the LCD before exit
atexit.register(on_clean_exit)
signal.signal(signal.SIGINT, on_signal_caught)
signal.signal(signal.SIGTERM, on_signal_caught)
is_posix = os.name == 'posix'
if is_posix:
    signal.signal(signal.SIGQUIT, on_signal_caught)
if platform.system() == "Windows":
    win32api.SetConsoleCtrlHandler(on_win32_ctrl_event, True)

try:
    display_init()
    wait_for_empty_queue(10)
    scheduler_init()
except Exception as e:
    messagebox.showerror(_("Error"), _("Error: ") + f'{e}')
    logger.error(f'init error {e}')
    start_configure()
    clean_stop(tray_icon)

close_windowtoast = utils.WindowToast(_('WeAct Studio System Monitor') + " " + utils.get_version(),_("The icon has been displayed in the tray. Click the icon to open the configuration."),icon=Path(__file__).parent / "res" / "icons" / "logo.png")
msg_close_handler()
if close_windowtoast:
    time.sleep(5)
    close_windowtoast()
if tray_icon and platform.system() == "Darwin":  # macOS-specific
    from AppKit import NSBundle, NSApp, NSApplicationActivationPolicyProhibited

    # Hide Python Launcher icon from macOS dock
    info = NSBundle.mainBundle().infoDictionary()
    info["LSUIElement"] = "1"
    NSApp.setActivationPolicy_(NSApplicationActivationPolicyProhibited)

    # For macOS: display the tray icon now with blocking function
    tray_icon.run_detached()

    tick = 0
    step = 0
    retry_connect_count = 0
    while True:
        if not display.is_LcdSimulated:
            tick  = tick + 1
            if step == 0 :
                if tick > 4:
                    tick = 0
                    if display.lcd.lcd_serial.is_open == False:
                        scheduler.STOPPING = True
                        logger.debug('scheduler stopping')
                        step = 1
            elif step == 1:
                if scheduler.is_queue_empty() or tick > 10:
                    tick = 0
                    step = 2
            elif step == 2:
                if tick > 6:
                    tick = 0
                    try:
                        display.lcd.lcd_serial.open()
                        logger.debug('Re-open Serial Successful')
                        step = 3
                    except Exception as e:
                        retry_connect_count = retry_connect_count + 1
                        logger.debug('Re-open Serial Fail')
                        if retry_connect_count >= 20:
                            logger.error(f'Re-open Serial Fail Count {retry_connect_count}')
                            messagebox.showerror(_("Error"), _("Error: ") + f'{e}')
                            start_configure()
                            clean_stop(tray_icon)
            elif step == 3:
                logger.debug('Re-init Display')
                display.lcd.lcd_serial.close()
                app_clean()
                start_main()
                app_exit()

            if get_config_display_free_off() == True:
                display_free_off_tick = display_free_off_tick + 1
                if activity == False:
                    if display_free_off_tick > IDLE_THRESHOLD * 2:
                        display_free_off_tick = 0
                        if display_off == False:
                            display.lcd.SetBrightness(0)
                            logger.info('display off')
                            display_off = True
                else:
                    activity = False
                    display_free_off_tick = 0
                    if display_off == True:
                        display.lcd.SetBrightness(get_config_display_brightness())
                        logger.info('display on')
                        display_off = False

        time.sleep(0.5)

elif platform.system() == "Windows":  # Windows-specific
    # Create a hidden window just to be able to receive window message events (for shutdown/logoff clean stop)
    hinst = win32api.GetModuleHandle(None)
    wndclass = win32gui.WNDCLASS()
    wndclass.hInstance = hinst
    wndclass.lpszClassName = "SystemMonitorEventWndClass"
    messageMap = {win32con.WM_QUERYENDSESSION: on_win32_wm_event,
                    win32con.WM_ENDSESSION: on_win32_wm_event,
                    win32con.WM_QUIT: on_win32_wm_event,
                    win32con.WM_DESTROY: on_win32_wm_event,
                    win32con.WM_CLOSE: on_win32_wm_event,
                    win32con.WM_POWERBROADCAST: on_win32_wm_event}

    wndclass.lpfnWndProc = messageMap

    try:
        myWindowClass = win32gui.RegisterClass(wndclass)
        hwnd = win32gui.CreateWindowEx(win32con.WS_EX_LEFT,
                                        myWindowClass,
                                        "SystemMonitorEventWnd",
                                        0,
                                        0,
                                        0,
                                        win32con.CW_USEDEFAULT,
                                        win32con.CW_USEDEFAULT,
                                        0,
                                        0,
                                        hinst,
                                        None)
        tick = 0
        step = 0
        retry_connect_count = 0
        while True:
            # Receive and dispatch window messages
            win32gui.PumpWaitingMessages()

            if not display.is_LcdSimulated:
                tick  = tick + 1
                if step ==0 :
                    if tick > 4:
                        tick = 0
                        if display.lcd.lcd_serial != None:
                            if display.lcd.lcd_serial.is_open == False:
                                scheduler.STOPPING = True
                                logger.debug('scheduler stopping')
                                step = 1
                        else:
                            messagebox.showerror(_("Error"), _("Error: ") + f'No COM Port Find')
                            start_configure()
                            clean_stop(tray_icon)
                elif step == 1:
                    if scheduler.is_queue_empty() or tick > 10:
                        tick = 0
                        step = 2
                elif step == 2:
                    if tick > 6:
                        tick = 0
                        try:
                            display.lcd.lcd_serial.open()
                            logger.debug('Re-open Serial Successful')
                            step = 3
                        except Exception as e:
                            retry_connect_count = retry_connect_count + 1
                            logger.debug('Re-open Serial Fail')
                            if retry_connect_count >= 20:
                                logger.error(f'Re-open Serial Fail Count {retry_connect_count}')
                                messagebox.showerror(_("Error"), _("Error: ") + f'{e}')
                                start_configure()
                                clean_stop(tray_icon)
                elif step == 3:
                    logger.debug('Re-init Display')
                    display.lcd.lcd_serial.close()
                    app_clean()
                    start_main()
                    app_exit()
                
                if get_config_display_free_off() == True:
                    display_free_off_tick = display_free_off_tick + 1
                    if activity == False:
                        if display_free_off_tick > IDLE_THRESHOLD * 2:
                            display_free_off_tick = 0
                            if display_off == False:
                                display.lcd.SetBrightness(0)
                                logger.info('display off')
                                display_off = True
                    else:
                        activity = False
                        display_free_off_tick = 0
                        if display_off == True:
                            display.lcd.SetBrightness(get_config_display_brightness())
                            logger.info('display on')
                            display_off = False

            time.sleep(0.5)

    except Exception as e:
        logger.error("Exception while creating event window: %s" % str(e))