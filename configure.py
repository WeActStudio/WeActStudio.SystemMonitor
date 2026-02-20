#!/usr/bin/env python
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

# This file is the system monitor configuration GUI

import os
import subprocess
import sys
import webbrowser
import traceback
import shutil

sys.path.append(os.path.dirname(__file__))
MIN_PYTHON = (3, 8)
if sys.version_info < MIN_PYTHON:
    print("[ERROR] Python %s.%s or later is required." % MIN_PYTHON)
    try:
        sys.exit(0)
    except:
        os._exit(0)

try:
    import tkinter.ttk as ttk
    import tkinter
    from tkinter import messagebox
    from tkinter import filedialog
    from PIL import ImageTk
    from pathlib import Path
    import geocoder
except:
    print("[ERROR] Python dependencies not installed.")
    try:
        sys.exit(0)
    except:
        os._exit(0)

try:
    import platform
    import psutil
    import ruamel.yaml
    import sv_ttk
    from PIL import Image
    from serial.tools.list_ports import comports
    from tktooltip import ToolTip

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
    title = _("WeAct Studio System Monitor Configuration") + " " + utils.get_version()
    message = _("Error: Another instance of the program is already running.")
    utils.show_messagebox(message=message,title=title,delay=3000)
    time.sleep(3)
    try:
        sys.exit(0)
    except:
        os._exit(0)
else:
    utils.app_set_running(LOCKFILE)

def app_exit():
    global LOCKFILE
    utils.app_end_running(LOCKFILE)
    try:
        sys.exit(0)
    except:
        os._exit(0)

from library.sensors.sensors_python import sensors_fans, is_cpu_fan
from library.lcd.lcd_comm import Orientation

WEACT_A_MODEL = "WeAct Studio Display FS V1"
WEACT_B_MODEL = "WeAct Studio Display FS 0.96 Inch"
SIMULATED_A_MODEL = "Simulated 320x480"
SIMULATED_B_MODEL = "Simulated 480x800"
SIMULATED_C_MODEL = "Simulated 80x160"

SIZE_1 = "320x480"
SIZE_2 = "480x800"
SIZE_3 = "80x160"

size_list = (SIZE_1, SIZE_2, SIZE_3)
orientation_list = (_("portrait"), _("landscape"))

# Maps between config.yaml values and GUI description
revision_to_model_map = {
    "A_320x480": WEACT_A_MODEL,
    "B_80x160": WEACT_B_MODEL,
    "SIMU_320x480": SIMULATED_A_MODEL,
    "SIMU_480x800": SIMULATED_B_MODEL,
    "SIMU_80x160": SIMULATED_C_MODEL,
}

model_to_revision_map = {
    WEACT_A_MODEL: "A_320x480",
    WEACT_B_MODEL: "B_80x160",
    SIMULATED_A_MODEL: "SIMU_320x480",
    SIMULATED_B_MODEL: "SIMU_480x800",
    SIMULATED_C_MODEL: "SIMU_80x160",
}

model_to_size_map = {
    WEACT_A_MODEL: SIZE_1,
    WEACT_B_MODEL: SIZE_3,
    SIMULATED_A_MODEL: SIZE_1,
    SIMULATED_B_MODEL: SIZE_2,
    SIMULATED_C_MODEL: SIZE_3,
}

hw_lib_map = {
    "AUTO": _("Automatic"),
    "LHM": "LibreHardwareMonitor",
    "PYTHON": "Python libraries",
    "STUB": _("Fake random data"),
    "STATIC": _("Fake static data"),
}
reverse_map = {False: _("Classic"), True: _("Reverse")}

class get_theme:
    def __init__(self, path):
        self.path = path

    def get_theme_data(self, name: str):
        # Use Path object methods consistently
        dir_path = self.path / name
        # Check if it is a directory
        if dir_path.is_dir():
            # Check if a theme.yaml file exists
            theme_path = dir_path / "theme.yaml"
            if theme_path.is_file():
                try:
                    # Get display size from theme.yaml
                    with theme_path.open("rt", encoding="utf8") as stream:
                        theme_data, ind, bsi = ruamel.yaml.util.load_yaml_guess_indent(stream)
                        return theme_data
                except Exception as e:
                    # You can add more specific exception handling as needed
                    print(f"Error reading theme.yaml: {e}")
        return None

    def get_themes(self, size: str):
        themes = []
        themes_path = self.path
        # Iterate over all items in the themes directory
        for item in themes_path.iterdir():
            if item.is_dir():
                try:
                    theme_data = self.get_theme_data(item.name)
                    # Check if theme data exists and the display size matches
                    if theme_data and theme_data["display"].get("DISPLAY_SIZE", SIZE_1) == size:
                        themes.append(item.name)
                except (KeyError, TypeError):
                    # Handle cases where theme data is missing or malformed
                    continue
        return sorted(themes, key=str.casefold)

    def get_theme_size(self, name: str) -> str:
        try:
            theme_data = self.get_theme_data(name)
            return theme_data["display"].get("DISPLAY_SIZE", SIZE_1)
        except (KeyError, TypeError):
            # Handle cases where theme data is missing or malformed
            return None


def get_com_ports():
    com_ports_names = [
        _("Automatic detection")
    ]  # Add manual entry on top for automatic detection
    com_ports = comports()
    for com_port in com_ports:
        com_ports_names.append(com_port.name)
    return com_ports_names


def get_net_if():
    if_list = list(psutil.net_if_addrs().keys())
    if_list.insert(
        0, "None"
    )  # Add manual entry on top for unavailable/not selected interface
    return if_list


def get_fans():
    fan_list = list()
    auto_detected_cpu_fan = "None"
    for name, entries in sensors_fans().items():
        for entry in entries:
            fan_list.append(
                "%s/%s (%d%% - %d RPM)"
                % (name, entry.label, entry.percent, entry.current)
            )
            if (
                is_cpu_fan(entry.label) or is_cpu_fan(name)
            ) and auto_detected_cpu_fan == "None":
                auto_detected_cpu_fan = "Auto-detected: %s/%s" % (name, entry.label)

    fan_list.insert(
        0, auto_detected_cpu_fan
    )  # Add manual entry on top if auto-detection succeeded
    return fan_list

class ConfigWindow:
    def __init__(self):

        self.theme_editor_process = None
        self.display_other_config_process = None

        self.window = tkinter.Tk()
        self.window.title(_("WeAct Studio System Monitor Configuration") + " " + utils.get_version())
        self.window.iconphoto(True, tkinter.PhotoImage(file=Path(__file__).parent / "res" / "icons" / "logo.png"))
        style = ttk.Style()

        self.theme_is_dark = False
        if platform.system() == "Windows" and sys.getwindowsversion().major >= 10:
            import darkdetect
            self.theme_is_dark = darkdetect.theme() == "Dark"
            if self.theme_is_dark:
                self.window.tk.call("source", Path(__file__).parent / "res" / "tk_themes" / "sv_ttk" / "theme" / "dark.tcl")
                style.theme_use("sun-valley-dark")
            else:
                self.window.tk.call("source", Path(__file__).parent / "res" / "tk_themes" / "sv_ttk" / "theme" / "light.tcl")
                style.theme_use("sun-valley-light")
        else:
            self.window.tk.call("source", Path(__file__).parent / "res" / "tk_themes" / "sv_ttk" / "theme" / "light.tcl")
            style.theme_use("sun-valley-light")

        utils.apply_theme_to_titlebar(self.window,self.theme_is_dark)
        self.window.update()

        self.entry_label_text = {}
        self.entry_label_text['Copy'] = _('Copy')
        self.entry_label_text['Paste'] = _('Paste')
        self.entry_label_text['Cut'] = _('Cut')
        self.entry_label_text['Undo'] = _('Undo')
        self.entry_label_text['Redo'] = _('Redo')

        self.theme_preview_img = None

        # Theme preview
        self.theme_preview_frame = tkinter.Frame(self.window)
        self.theme_preview_frame.grid(row=0, column=0, rowspan=5, columnspan=2, padx=10, pady=10,sticky="n")
        self.theme_preview = ttk.Label(self.theme_preview_frame)
        self.theme_preview.grid(row=0, column=0, rowspan=4, columnspan=2, padx=5, pady=5)
        self.theme_author = ttk.Label(self.theme_preview_frame)
        self.theme_author.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Display configuration
        self.display_config_frame = tkinter.Frame(self.window)
        self.display_config_frame.grid(row=0, column=2, columnspan=3, padx=10, pady=10,sticky="nw")

        sysmon_label = ttk.Label(
            self.display_config_frame, text=_("Display configuration"), font=("Arial", 13, "bold")
        )
        sysmon_label.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        self.model_label = ttk.Label(self.display_config_frame, text=_("Screen model"))
        self.model_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.model_cb = ttk.Combobox(
            self.display_config_frame,
            values=list(dict.fromkeys((revision_to_model_map.values()))),
            state="readonly",
        )
        self.model_cb.bind("<<ComboboxSelected>>", self.on_model_change)
        self.model_cb.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="w"+"e")

        self.size_label = ttk.Label(self.display_config_frame, text=_("Screen size"))
        self.size_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.size_select_label = ttk.Label(
            self.display_config_frame,
            text=model_to_size_map[WEACT_A_MODEL],
            font=("Arial", 12, "bold"),
        )
        self.size_select_label.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        self.com_label = ttk.Label(self.display_config_frame, text=_("COM port"))
        self.com_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.com_cb = ttk.Combobox(
            self.display_config_frame, values=get_com_ports(), state="readonly"
        )
        self.com_cb.grid(row=3, column=1, padx=5, pady=5, sticky="w"+"e")
        self.com_refresh_button = ttk.Button(
            self.display_config_frame, text=_("Refresh"), command=lambda: self.on_com_refresh_button()
        )
        self.com_refresh_button.grid(row=3, column=2, padx=5, pady=5, sticky="w")

        self.orient_label = ttk.Label(self.display_config_frame, text=_("Orientation"))
        self.orient_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.orient_cb = ttk.Combobox(
            self.display_config_frame, values=list(reverse_map.values()), state="readonly"
        )
        self.orient_cb.grid(row=4, column=1, columnspan=2, padx=5, pady=5, sticky="w"+"e")

        self.brightness_string = tkinter.StringVar()
        self.brightness_label = ttk.Label(self.display_config_frame, text=_("Brightness"))
        self.brightness_label.grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.brightness_slider_frame = tkinter.Frame(self.display_config_frame)
        self.brightness_slider_frame.grid(row=5, column=1, columnspan=2, sticky="w"+"e")
        self.brightness_slider_frame.columnconfigure(1, weight=1)
        self.brightness_slider = ttk.Scale(
            self.brightness_slider_frame,
            from_=0,
            to=100,
            orient=tkinter.HORIZONTAL,
            command=self.on_brightness_change,
        )
        self.brightness_slider.grid(row=0, column=1, padx=5, pady=5, sticky="w"+"e")
        self.brightness_val_label = ttk.Label(
            self.brightness_slider_frame, textvariable=self.brightness_string
        )
        self.brightness_val_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.live_display_bool_var = tkinter.BooleanVar()
        self.live_display_bool_var.set(False)
        self.live_display_checkbox = ttk.Checkbutton(
            self.display_config_frame,
            text=_("Theme Preview, Auto Save"),
            variable=self.live_display_bool_var,
        )
        self.live_display_checkbox.grid(row=6, column=1, columnspan=2, padx=5, sticky="w")

        self.other_setting_button = ttk.Button(
            self.display_config_frame,
            text=_("Other Config"),
            command=lambda: self.on_display_other_config_click(),
        )
        self.other_setting_button.grid(row=6, column=0, padx=5, sticky="w"+"e")

        self.free_off_bool_var = tkinter.BooleanVar()
        self.free_off_bool_var.set(False)
        self.free_off_checkbox = ttk.Checkbutton(
            self.display_config_frame,
            text=_("Free Off(3 min)"),
            variable=self.free_off_bool_var,
        )
        self.free_off_checkbox.grid(row=7, column=1, columnspan=2, padx=5, sticky="w")

        self.pic_compress_bool_var = tkinter.BooleanVar()
        self.pic_compress_bool_var.set(False)
        self.pic_compress_checkbox = ttk.Checkbutton(
            self.display_config_frame,
            text=_("Picture Compress"),
            variable=self.pic_compress_bool_var,
        )
        self.pic_compress_checkbox.grid(row=8, column=1, columnspan=2, padx=5, sticky="w")

        # System Monitor Configuration
        self.system_monitor_frame = tkinter.Frame(self.window)
        self.system_monitor_frame.columnconfigure(1, weight=1)
        self.system_monitor_frame.grid(row=1, column=2, columnspan=3, padx=10, pady=10,sticky="nwe")
        sysmon_label = ttk.Label(
            self.system_monitor_frame, text=_("System Monitor Configuration"), font=("Arial", 13, "bold")
        )
        sysmon_label.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        self.theme_label = ttk.Label(self.system_monitor_frame, text=_("Theme"))
        self.theme_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.theme_cb = ttk.Combobox(self.system_monitor_frame, state="readonly")
        self.theme_cb.grid(row=1, column=1, columnspan=1, padx=5, pady=5, sticky="w"+"e")
        self.theme_cb.bind("<<ComboboxSelected>>", self.on_theme_change)
        self.theme_refresh_button = ttk.Button(
            self.system_monitor_frame, text=_("Refresh"), command=lambda: self.on_model_change()
        )
        self.theme_refresh_button.grid(row=1, column=2, padx=5, pady=5, sticky="w")

        self.hwlib_label = ttk.Label(self.system_monitor_frame, text=_("Hardware monitoring"))
        self.hwlib_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        if sys.platform != "win32":
            del hw_lib_map["LHM"]  # LHM is for Windows platforms only
        self.hwlib_cb = ttk.Combobox(
            self.system_monitor_frame, values=list(hw_lib_map.values()), state="readonly"
        )
        self.hwlib_cb.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="w"+"e")
        self.hwlib_cb.bind("<<ComboboxSelected>>", self.on_hwlib_change)

        self.eth_label = ttk.Label(self.system_monitor_frame, text=_("Ethernet interface"))
        self.eth_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.eth_cb = ttk.Combobox(self.system_monitor_frame, values=get_net_if(), state="readonly")
        self.eth_cb.grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky="w"+"e")

        self.wl_label = ttk.Label(self.system_monitor_frame, text=_("Wi-Fi interface"))
        self.wl_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.wl_cb = ttk.Combobox(self.system_monitor_frame, values=get_net_if(), state="readonly")
        self.wl_cb.grid(row=4, column=1, columnspan=2, padx=5, pady=5, sticky="w"+"e")

        # For Windows platform only
        self.lhm_admin_warning = ttk.Label(
            self.system_monitor_frame,
            text="❌ " + _("Restart as admin. or select another Hardware monitoring"),
            foreground="#f00",
        )
        # For platform != Windows
        self.cpu_fan_label = ttk.Label(self.system_monitor_frame, text="CPU fan (？)")
        self.cpu_fan_label.config(foreground="#a3a3ff", cursor="hand2")
        self.cpu_fan_cb = ttk.Combobox(self.system_monitor_frame, values=get_fans(), state="readonly")

        self.tooltip = ToolTip(
            self.cpu_fan_label,
            msg='If "None" is selected, CPU fan was not auto-detected.\n'
            "Manually select your CPU fan from the list.\n\n"
            "Fans missing from the list? Install lm-sensors package\n"
            "and run 'sudo sensors-detect' command, then reboot.",
        )

        if platform.system() == "Windows":
            import ctypes
            from library import schedule_service

            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if is_admin == True:
                self.schedule_task_name = "WeAct Studio System Monitor"
                self.schedule_task_path = (
                    '"' + os.path.dirname(__file__) + r"\System Monitor Main.bat" + '"'
                )
                schedule_task_exist, schedule_task_path_get = (
                    schedule_service.task_exists(self.schedule_task_name)
                )
                if (
                    schedule_task_exist == True
                    and schedule_task_path_get != self.schedule_task_path
                ):
                    print(f"error schedule task path {schedule_task_path_get}")
                    schedule_service.delete_task(self.schedule_task_name)
                    schedule_task_exist = False
                self.bootstrap_label = ttk.Label(self.system_monitor_frame, text=_("Bootstrap"))
                self.bootstrap_label.grid(row=6, column=0, padx=5, pady=5, sticky="w")
                self.bootstrap_checkbutton_var = tkinter.IntVar()
                self.bootstrap_checkbutton_var.set(schedule_task_exist)
                self.bootstrap_checkbutton = ttk.Checkbutton(
                    self.system_monitor_frame,
                    text=_("Enable"),
                    variable=self.bootstrap_checkbutton_var,
                    command=self.on_bootstrap_checkbutton_toggle,
                )
                self.bootstrap_checkbutton.grid(row=6, column=1, columnspan=2, padx=5, pady=5, sticky="w")
        
        self.button_frame = tkinter.Frame(self.window)
        for i in range(5):
            self.button_frame.columnconfigure(i, weight=1)
        self.button_frame.grid(row=5, column=0, columnspan=5, padx=10, pady=10, sticky="ew")
        
        self.edit_theme_btn = ttk.Button(
            self.button_frame, text=_("Edit theme"), command=lambda: self.on_theme_editor_click()
        )
        self.edit_theme_btn.grid(row=1, column=2, padx=5, pady=5, sticky="nsew", ipady=10)

        self.new_theme_btn = ttk.Button(
            self.button_frame,
            text=_("New theme"),
            command=lambda: self.on_new_theme_editor_click(),
        )
        self.new_theme_btn.grid(row=1, column=1, padx=5, pady=5, sticky="nsew", ipady=10)

        self.delete_theme_btn = ttk.Button(
            self.button_frame,
            text=_("Delete theme"),
            command=lambda: self.on_delete_theme_click(),
        )
        self.delete_theme_btn.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.theme_dir_btn = ttk.Button(
            self.button_frame,
            text=_("Theme dir"),
            command=lambda: self.on_theme_dir_click(),
        )
        self.theme_dir_btn.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.copy_theme_btn = ttk.Button(
            self.button_frame,
            text=_("Copy theme"),
            command=lambda: self.on_copy_theme_editor_click(),
        )
        self.copy_theme_btn.grid(row=0, column=1, padx=5, pady=5, sticky="nsew", ipady=10)

        self.workspace_settings_btn = ttk.Button(
            self.button_frame,
            text=_("Workspace Settings"),
            command=lambda: self.on_workspace_settings_click()
        )
        self.workspace_settings_btn.grid(row=0, column=2, padx=5, pady=5, sticky="nsew", ipady=10)


        self.weather_ping_btn = ttk.Button(self.button_frame, text=_("Ping & Weather"),
                                           command=lambda: self.on_weatherping_click())
        self.weather_ping_btn.grid(row=0, column=3, padx=5, pady=5, sticky="nsew", ipady=10)

        self.save_btn = ttk.Button(
            self.button_frame, text=_("Save settings"), command=lambda: self.on_save_click()
        )
        self.save_btn.grid(row=1, column=3, padx=5, pady=5, sticky="nsew")

        self.save_run_btn = ttk.Button(
            self.button_frame, text=_("Save and run"), command=lambda: self.on_saverun_click()
        )
        self.save_run_btn.grid(row=1, column=4, padx=5, pady=5, sticky="nsew")

        self.config = None
        self.theme_get = None
        self.themes_dir_path = None
        self.load_config_values()

        # When window gets focus again, reload theme preview in case it has been updated by theme editor
        self.window.bind("<FocusIn>", self.on_theme_change)

        self.window.after(0, self.on_fan_speed_update)
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        utils.apply_theme_to_titlebar(self.window,self.theme_is_dark)

        # Center the window on the screen
        # self.window.withdraw()
        # self.window.update()
        # screen_width = self.window.winfo_screenwidth()
        # screen_height = self.window.winfo_screenheight()
        # main_window_width = self.window.winfo_width()
        # main_window_height = self.window.winfo_height()
        # x = (screen_width - main_window_width) // 2
        # y = (screen_height - main_window_height) // 2
        # self.window.geometry(f"{main_window_width}x{main_window_height}+{x}+{y}")
        # self.window.deiconify()

        self.display_init = False
        self.display_setting_change = True
        self.display_brightness_change = True
        self.display_step = 0
        self.display_orientation_last = reverse_map[False]
        self.display_brightness_last = int(self.brightness_slider.get())
        self.pic_compress_bool_var_last = self.pic_compress_bool_var.get()
        self.theme_select_last = self.theme_cb.get()
        self.model_select_last = self.model_cb.get()
        self.theme_setting_change = True
        self.window_after_time = 1000

    def run(self):
        self.window_refresh()
        self.window.mainloop()

    def on_closing(self):
        if self.is_theme_editor_process():
            return
        self.on_closing_confirm()

    def on_closing_confirm(self):
        self.closing_confirm_frame = tkinter.Toplevel(self.window)
        self.closing_confirm_frame.title(_("Close Confirm"))
        self.closing_confirm_frame.withdraw()

        def on_closing_confirm_frame_closing():
            self.closing_confirm_frame.grab_release()
            self.closing_confirm_frame.destroy()

        self.closing_confirm_frame.protocol(
            "WM_DELETE_WINDOW", on_closing_confirm_frame_closing
        )
        self.closing_confirm_frame.resizable(False, False)
        self.closing_confirm_frame.grab_set()

        self.closing_confirm_label = ttk.Label(
            self.closing_confirm_frame, text=_("Do you want to run theme?")
        )
        self.closing_confirm_label.pack(
            side=tkinter.TOP, padx=5, pady=10, ipadx=50, anchor=tkinter.W
        )

        def on_closing_confirm_frame_no():
            if self.display_init == True:
                self.live_display_checkbox.state(["disabled"])
                self.display_off()
                self.display_init = False
            print("Exiting System Monitor Configuration...")
            self.closing_confirm_frame.grab_release()
            self.closing_confirm_frame.destroy()
            self.window.destroy()
            app_exit()

        cancel_button = ttk.Button(
            self.closing_confirm_frame, text=_("NO"), command=on_closing_confirm_frame_no
        )
        cancel_button.pack(side=tkinter.RIGHT, padx=5, pady=5)

        self.closing_confirm_frame.update()
        main_window_x = self.window.winfo_x()
        main_window_y = self.window.winfo_y()
        main_window_width = self.window.winfo_width()
        main_window_height = self.window.winfo_height()
        width = self.closing_confirm_frame.winfo_width()
        height = self.closing_confirm_frame.winfo_height()
        x = main_window_x + (main_window_width // 2) - (width // 2)
        y = main_window_y + (main_window_height // 2) - (height // 2)
        self.closing_confirm_frame.geometry(f"{width}x{height}+{x}+{y}")
        self.closing_confirm_frame.deiconify()

        self.closing_confirm_frame.focus_force()

        def on_closing_confirm_frame_ok():
            if self.display_init == True:
                self.live_display_checkbox.state(["disabled"])
                self.display_off()
                self.display_init = False
            print("Exiting System Monitor Configuration...")
            self.closing_confirm_frame.grab_release()
            self.closing_confirm_frame.destroy()
            utils.run.main()
            self.window.destroy()
            app_exit()

        ok_button = ttk.Button(
            self.closing_confirm_frame, text=_("OK"), command=on_closing_confirm_frame_ok
        )
        ok_button.pack(side=tkinter.RIGHT, padx=5, pady=5)
        ok_button['state'] = self.save_run_btn['state']

        utils.apply_theme_to_titlebar(self.closing_confirm_frame,self.theme_is_dark)

    def display_off(self):
        print('display.turn_off')
        try:
            self.display.turn_off()
            if self.scheduler.STOPPING != True:
                # Do not stop the program now in case data transmission was in progress
                # Instead, ask the scheduler to empty the action queue before stopping
                self.scheduler.STOPPING = True

                # Allow 5 seconds max. delay in case scheduler is not responding
                wait_time = 5

                while not self.scheduler.is_queue_empty() and wait_time > 0:
                    import time
                    time.sleep(0.1)
                    wait_time = wait_time - 0.1
            print('display.lcd.lcd_serial.close')
            self.display.lcd.lcd_serial.close()
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(_("Error"), _("error: ") + f'{e}')

    def window_refresh(self):
        if self.live_display_bool_var.get() == True:
            if self.is_theme_editor_process():
                self.live_display_bool_var.set(False)
                self.window.after(self.window_after_time, self.window_refresh)
                return
            self.model_cb['state'] = "disabled"
            self.com_cb['state'] = "disabled"
            self.com_refresh_button['state'] = "disabled"
            # check setting change
            if self.display_orientation_last != self.orient_cb.get():
                self.display_orientation_last = self.orient_cb.get()
                self.display_setting_change = True
                self.theme_setting_change = True
            if self.display_brightness_last != int(self.brightness_slider.get()):
                self.display_brightness_last = int(self.brightness_slider.get())
                self.display_setting_change = True
                self.display_brightness_change = True
            if self.theme_select_last != self.theme_cb.get():
                self.theme_select_last = self.theme_cb.get()
                self.display_setting_change = True
                self.theme_setting_change = True
            if self.pic_compress_bool_var_last!= self.pic_compress_bool_var.get():
                self.pic_compress_bool_var_last = self.pic_compress_bool_var.get()
                self.live_display_bool_var.set(False)
                self.save_config_values()
                
            if self.theme_setting_change == True or self.display_setting_change == True:
                self.save_config_values()
            # init display
            if self.display_init == False:
                try:
                    import library.scheduler as scheduler
                    import library.display
                    from library import config
                
                    if self.model_select_last != self.model_cb.get():
                        self.model_select_last = self.model_cb.get()
                        config.load_config()
                        library.display.display = library.display.Display()

                    self.scheduler = scheduler
                    self.display = library.display.display
                    
                    self.display.use_compress = 1 if self.pic_compress_bool_var.get() == True else 0
                    self.on_com_refresh_button()
                    if self.com_cb.current() == 0:
                        self.display.lcd.com_port = "AUTO"
                    else:
                        self.display.lcd.com_port = self.com_cb.get()
                    if self.display.lcd.lcd_serial == None or self.display.lcd.lcd_serial.is_open == False:
                        print("Open Display LCD Serial")
                        r = self.display.lcd.openSerial()
                    else:
                        print("Reopen Display LCD Serial")
                        self.display.lcd.closeSerial()
                        r = self.display.lcd.openSerial()
                    if not r:
                        messagebox.showerror(_("Error"), _("Error: ") + f'Serial Open Failed')
                        self.live_display_bool_var.set(False)
                        self.display_init = False
                    else:
                        print("Initialize display")
                        self.display.initialize_display()
                        print("Enable QueueHandler")
                        self.scheduler.STOPPING = False
                        self.scheduler.QueueHandler()
                        print("display_init Ok")
                        self.display_init = True
                except Exception as e:
                    traceback.print_exc()
                    messagebox.showerror(_("Error"), _("Error: ") + f'{e}')
                    self.live_display_bool_var.set(False)
                    self.display_init = True
            else:
                # display comport is open
                if self.display.lcd.lcd_serial != None:
                    if self.display.lcd.lcd_serial.is_open == False:
                        self.live_display_bool_var.set(False)
                        messagebox.showerror(_("Error"), _("error: COM Port is closed"))
            # display something
            if self.display_setting_change == True:
                try:
                    if self.display_step == 0:
                        self.display_step = 1
                        self.window_after_time = 200
                    elif self.display_step == 1:
                        if self.display_brightness_change == True:
                            print(f"display.lcd.SetBrightness {int(self.brightness_slider.get())}")
                            self.display.lcd.SetBrightness(
                                int(self.brightness_slider.get())
                            )
                            self.display_brightness_change = False
                        if self.theme_setting_change == True:
                            try:
                                theme_preview = Image.open(
                                    Path(self.themes_dir_path) / self.theme_cb.get() / "preview.png"
                                )
                                print("Show preview.png")
                            except:
                                theme_preview = Image.open(Path(__file__).parent / "res" / "configs" / "no-preview.png")
                                print("Show no-preview.png")
                            theme_data = self.theme_get.get_theme_data(self.theme_cb.get())
                            print("display.lcd.SetOrientation")
                            d_o = theme_data.get("display")
                            if d_o["DISPLAY_ORIENTATION"] == "portrait":
                                if self.orient_cb.get() == reverse_map[True]:
                                    self.display.lcd.SetOrientation(
                                        Orientation.REVERSE_PORTRAIT
                                    )
                                else:
                                    self.display.lcd.SetOrientation(
                                        Orientation.PORTRAIT
                                    )
                            else:
                                if self.orient_cb.get() == reverse_map[True]:
                                    self.display.lcd.SetOrientation(
                                        Orientation.REVERSE_LANDSCAPE
                                    )
                                else:
                                    self.display.lcd.SetOrientation(
                                        Orientation.LANDSCAPE
                                    )
                            theme_preview_d = theme_preview.resize(
                                (
                                    self.display.lcd.get_width(),
                                    self.display.lcd.get_height(),
                                )
                            )
                            print("display.lcd.DisplayPILImage")
                            self.display.lcd.DisplayPILImage(
                                theme_preview_d,
                                image_width=theme_preview_d.width,
                                image_height=theme_preview_d.height,
                            )
                            self.theme_setting_change = False

                        self.display_setting_change = False
                except Exception as e:
                    traceback.print_exc()
                    messagebox.showerror(_("Error"), _("error: ") + f'{e}')
                    self.live_display_bool_var.set(False)
        else:
            model = self.model_cb.get()
            if "Simulated" not in model:
                self.model_cb['state'] = "readonly"
                self.com_cb['state'] = "readonly"
                self.com_refresh_button['state'] = "normal"
            if self.display_init == True:
                self.display_off()
                self.display_init = False
            self.display_setting_change = True
            self.theme_setting_change = True
            self.display_brightness_change = True
            self.display_orientation_last = -1
            self.pic_compress_bool_var_last = self.pic_compress_bool_var.get()
            self.display_step = 0
            self.window_after_time = 1000
        self.window.after(self.window_after_time, self.window_refresh)

    def load_theme_preview(self):
        if self.theme_cb.get() != "":
            try:
                theme_preview = Image.open(
                    Path(self.themes_dir_path) / self.theme_cb.get() / "preview.png"
                )
            except Exception as e:
                traceback.print_exc()
                theme_preview = Image.open(Path(__file__).parent / "res" / "configs" / "no-preview.png")
            finally:
                # Set the fixed width for the preview image
                fixed_width = 300
                fixed_height = 450
                # Get the original width and height of the image
                width, height = theme_preview.size
                if width < fixed_width and height < fixed_height:
                    # Create a new image with fixed dimensions
                    new_image = Image.new('RGB', (fixed_width, fixed_height), (85, 85, 85))
                    # Calculate position to center the original image
                    x_offset = (fixed_width - width) // 2
                    y_offset = (fixed_height - height) // 2
                    # Paste the original image centered on the new image
                    new_image.paste(theme_preview, (x_offset, y_offset))
                    theme_preview = new_image
                else:
                    # Original scaling logic
                    width_ratio = fixed_width / width
                    height_ratio = fixed_height / height
                    ratio = min(width_ratio, height_ratio)
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    theme_preview = theme_preview.resize(
                        (new_width, new_height), Image.Resampling.LANCZOS
                    )
                self.theme_preview_img = ImageTk.PhotoImage(theme_preview)
                self.theme_preview.config(image=self.theme_preview_img)

                theme_data = self.theme_get.get_theme_data(self.theme_cb.get())
                author_name = theme_data.get("author", "unknown")
                self.theme_author.config(text=_("Author: ") + author_name)
                if author_name.startswith("@"):
                    self.theme_author.config(foreground="#a3a3ff", cursor="hand2")
                    self.theme_author.bind(
                        "<Button-1>",
                        lambda e: webbrowser.open_new_tab(
                            "https://github.com/" + author_name[1:]
                        ),
                    )
                else:
                    self.theme_author.config(foreground="#a3a3a3", cursor="")
                    self.theme_author.unbind("<Button-1>")
        else:
            theme_preview = Image.open(Path(__file__).parent / "res" / "configs" / "no-preview.png")
            # Set the fixed width for the preview image
            fixed_width = 300
            # Get the original width and height of the image
            width, height = theme_preview.size
            # Calculate the ratio to maintain the aspect ratio
            ratio = fixed_width / width
            # Calculate the new height based on the ratio
            new_height = int(height * ratio)
            # Resize the image with the fixed width and calculated height
            theme_preview = theme_preview.resize(
                (fixed_width, new_height), Image.Resampling.LANCZOS
            )
            self.theme_preview_img = ImageTk.PhotoImage(theme_preview)
            self.theme_preview.config(image=self.theme_preview_img)
                

    def load_config_values(self):
        try:
            with open(Path(__file__).parent / "config.yaml", "rt", encoding="utf8") as stream:
                self.config, ind, bsi = ruamel.yaml.util.load_yaml_guess_indent(stream)
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(_("Error"), _("error: ") + f'{e}')
            self.config = {}
        # Check if theme is valid
        if self.config is None:
            self.config = {}

        # Display config
        # Guess model from revision and size
        display = self.config.get("display",None)
        if display is None:
            print("display config not found!!")
            self.config["display"] = {}
        try:
            revision = self.config["display"]["REVISION"]
            self.model_cb.set(revision_to_model_map[revision])
        except:
            self.model_cb.current(0)

        try:
            self.orient_cb.set(reverse_map[self.config["display"]["DISPLAY_REVERSE"]])
        except:
            self.orient_cb.current(0)

        try:
            self.brightness_slider.set(int(self.config["display"]["BRIGHTNESS"]))
        except:
            self.brightness_slider.set(50)

        try:
            if self.config["config"]["CPU_FAN"] == "AUTO":
                self.cpu_fan_cb.current(0)
            else:
                self.cpu_fan_cb.set(self.config["config"]["CPU_FAN"])
        except:
            self.cpu_fan_cb.current(0)

        try:
            self.free_off_bool_var.set(self.config["display"].get("FREE_OFF",False))
        except:
            self.free_off_bool_var.set(False)

        try:
            self.pic_compress_bool_var.set(self.config["display"].get("PIC_COMPRESS",False))
        except:
            self.pic_compress_bool_var.set(False)

        # Config config
        config = self.config.get("config",None)
        if config is None:
            print("Config not found!!")
            self.config["config"] = {}

        fonts_dir_path = self.config["config"].get("FONTS_DIR",None)
        if fonts_dir_path is None or fonts_dir_path == "":
            self.config["config"]["FONTS_DIR"] = str(Path("res/fonts"))

        self.themes_dir_path = self.config["config"].get("THEMES_DIR",None)
        if self.themes_dir_path is None or self.themes_dir_path == "":
            self.themes_dir_path = "res/themes"
            self.config["config"]["THEMES_DIR"] = str(Path(self.themes_dir_path))
        else:
            try:
                # Check if the path exists
                if not Path(self.themes_dir_path).exists():
                    print(f"THEMES_DIR path {self.themes_dir_path} does not exist, using default.")
                    self.themes_dir_path = "res/themes"
                    self.config["config"]["THEMES_DIR"] = self.themes_dir_path
            except Exception as e:
                print(f"Error checking themes directory path: {e}, using default.")
                self.themes_dir_path = "res/themes"
                self.config["config"]["THEMES_DIR"] = str(Path(self.themes_dir_path))
        
        self.theme_get = get_theme(Path(self.themes_dir_path))
        theme = config.get("THEME",None)
        themes_list = self.theme_get.get_themes(model_to_size_map[self.model_cb.get()])
        if theme is None or theme == "" or theme not in themes_list:
            # Theme from config.yaml is not valid: use first theme available default size 320x480
            theme_get = self.theme_get.get_themes(model_to_size_map[self.model_cb.get()])
            if len(theme_get) > 0:
                self.config["config"]["THEME"] = theme_get[0]
            else:
                self.config["config"]["THEME"] = ""
        
        try:
            self.theme_cb.set(config.get("THEME",None))
        except:
            self.theme_cb.set("")

        self.load_theme_preview()

        try:
            self.hwlib_cb.set(hw_lib_map[config.get("HW_SENSORS","LHM")])
        except:
            self.hwlib_cb.current(0)

        try:
            if config.get("ETH","") == "":
                self.eth_cb.current(0)
            else:
                self.eth_cb.set(self.config["config"]["ETH"])
        except:
            self.eth_cb.current(0)

        try:
            if config.get("WLO","") == "":
                self.wl_cb.current(0)
            else:
                self.wl_cb.set(self.config["config"]["WLO"])
        except:
            self.wl_cb.current(0)

        try:
            if config.get("COM_PORT","AUTO") == "AUTO":
                self.com_cb.current(0)
            else:
                self.com_cb.set(self.config["config"]["COM_PORT"])
        except:
            self.com_cb.current(0)

        # Guess display size from theme in the configuration
        size = self.theme_get.get_theme_size(self.config["config"]["THEME"])
        try:
            self.size_select_label["text"] = size
        except:
            self.size_select_label["text"] = SIZE_1

        # Reload content on screen
        self.on_model_change()
        self.on_theme_change()
        self.on_brightness_change()
        self.on_hwlib_change()

    def save_config_values(self):
        self.config["config"]["THEME"] = self.theme_cb.get()
        self.config["config"]["HW_SENSORS"] = [
            k for k, v in hw_lib_map.items() if v == self.hwlib_cb.get()
        ][0]
        if self.eth_cb.current() == 0:
            self.config["config"]["ETH"] = ""
        else:
            self.config["config"]["ETH"] = self.eth_cb.get()
        if self.wl_cb.current() == 0:
            self.config["config"]["WLO"] = ""
        else:
            self.config["config"]["WLO"] = self.wl_cb.get()
        if self.com_cb.current() == 0:
            self.config["config"]["COM_PORT"] = "AUTO"
        else:
            self.config["config"]["COM_PORT"] = self.com_cb.get()
        if self.cpu_fan_cb.current() == 0:
            self.config["config"]["CPU_FAN"] = "AUTO"
        else:
            self.config["config"]["CPU_FAN"] = self.cpu_fan_cb.get().split(" ")[0]
        self.config["display"]["REVISION"] = model_to_revision_map[self.model_cb.get()]
        self.config["display"]["DISPLAY_REVERSE"] = [
            k for k, v in reverse_map.items() if v == self.orient_cb.get()
        ][0]
        self.config["display"]["BRIGHTNESS"] = int(self.brightness_slider.get())
        self.config["display"]["FREE_OFF"] = self.free_off_bool_var.get()
        self.config["display"]["PIC_COMPRESS"] = self.pic_compress_bool_var.get()
        
        with open("config.yaml", "w", encoding="utf-8") as file:
            ruamel.yaml.YAML().dump(self.config, file)

    def save_additional_config(self, ping: str = None, api_key: str = None, lat: str = None, long: str = None, unit: str = None, lang: str = None, theme_dir: str = None, font_dir: str = None):
        if ping is not None:
            self.config['config']['PING'] = ping
        if api_key is not None:
            self.config['config']['WEATHER_API_KEY'] = api_key
        if lat is not None:
            self.config['config']['WEATHER_LATITUDE'] = lat
        if long is not None:
            self.config['config']['WEATHER_LONGITUDE'] = long
        if unit is not None:
            self.config['config']['WEATHER_UNITS'] = unit
        if lang is not None:
            self.config['config']['WEATHER_LANGUAGE'] = lang
        if theme_dir is not None:
            self.config['config']['THEMES_DIR'] = theme_dir
        if font_dir is not None:
            self.config['config']['FONTS_DIR'] = font_dir

        with open("config.yaml", "w", encoding='utf-8') as file:
            ruamel.yaml.YAML().dump(self.config, file)

        if theme_dir is not None or font_dir is not None:
            self.load_config_values()

    def on_theme_change(self, e=None):
        self.load_theme_preview()

    def on_workspace_settings_click(self):
        # Subwindow for workspace settings.
        self.workspace_settings_window = WorkspaceSettingsWindow(self)
        self.workspace_settings_window.show()

    def on_weatherping_click(self):
        # Subwindow for weather/ping config.
        self.weatherping_config_window = PingWeatherConfigWindow(self)
        self.weatherping_config_window.show()

    def is_theme_editor_process(self):
        if self.theme_editor_process is not None:
            if self.theme_editor_process.poll() is None:
                messagebox.showerror(_("Error"), _("theme editor is running !"))
                return True
            else:
                self.theme_editor_process = None
        return False
    
    def on_new_theme_editor_click(self):
        if self.is_theme_editor_process():
            return
        self.new_theme_editor = tkinter.Toplevel(self.window)
        self.new_theme_editor.title(_("New theme"))
        self.new_theme_editor.withdraw()
        
        self.new_theme_editor.protocol(
            "WM_DELETE_WINDOW", self.on_new_theme_editor_closing
        )
        self.new_theme_editor.resizable(False, False)
        self.new_theme_editor.grab_set()
        self.new_theme_editor_label = ttk.Label(self.new_theme_editor, text=_("Name"))
        self.new_theme_editor_label.pack(
            side=tkinter.TOP, padx=10, pady=10, anchor=tkinter.W
        )

        self.new_theme_editor_entry = utils.EnhancedEntry(self.new_theme_editor,label_text=self.entry_label_text)
        self.new_theme_editor_entry.pack(fill=tkinter.X, expand=True, padx=10, ipadx=30)
        self.new_theme_editor_entry.bind(
            "<KeyRelease>", self.new_theme_editor_entry_change
        )

        self.new_theme_editor_orientation_label = ttk.Label(
            self.new_theme_editor, text=_("Orientation")
        )
        self.new_theme_editor_orientation_label.pack(
            side=tkinter.TOP, padx=10, pady=10, anchor=tkinter.W
        )
        self.new_theme_editor_orientation_combobox = ttk.Combobox(
            self.new_theme_editor, values=orientation_list, state="readonly"
        )
        self.new_theme_editor_orientation_combobox.current(0)
        self.new_theme_editor_orientation_combobox.pack(
            fill=tkinter.X, expand=True, padx=10, ipadx=30
        )

        cancel_button = ttk.Button(
            self.new_theme_editor,
            text=_("Cancel"),
            command=self.on_new_theme_editor_closing,
        )
        cancel_button.pack(side=tkinter.RIGHT, padx=10, pady=10)

        self.new_theme_editor_ok_button = ttk.Button(
            self.new_theme_editor, text="OK", command=self.on_new_theme_editor_button_ok
        )
        self.new_theme_editor_ok_button.pack(side=tkinter.RIGHT, padx=5, pady=10)
        self.new_theme_editor_ok_button.state(["disabled"])

        self.new_theme_editor.update()
        main_window_x = self.window.winfo_x()
        main_window_y = self.window.winfo_y()
        main_window_width = self.window.winfo_width()
        main_window_height = self.window.winfo_height()
        width = self.new_theme_editor.winfo_width()
        height = self.new_theme_editor.winfo_height()
        x = main_window_x + (main_window_width // 2) - (width // 2)
        y = main_window_y + (main_window_height // 2) - (height // 2)
        self.new_theme_editor.geometry(f"{width}x{height}+{x}+{y}")
        self.new_theme_editor.deiconify()
        self.new_theme_editor.focus_force()

        utils.apply_theme_to_titlebar(self.new_theme_editor,self.theme_is_dark)

    def on_new_theme_editor_closing(self):
        self.new_theme_editor.grab_release()
        self.new_theme_editor.destroy()

    def list_theme_dir(self):
        current_directory = Path(self.themes_dir_path)
        try:
            folders = [entry.name for entry in current_directory.iterdir() if entry.is_dir()]
            return folders
        except FileNotFoundError:
            print(f"Error: Directory {current_directory} not found.")
            return []
        except PermissionError:
            print(f"Error: Permission denied when accessing {current_directory}.")
            return []

    def validate_entry(self, P):
        import re

        pattern = r"^[a-zA-Z0-9_\- .&']+$"
        if re.match(pattern, P):
            return True
        else:
            return False

    def new_theme_editor_entry_change(self, event=None):
        content = self.new_theme_editor_entry.get()
        if self.validate_entry(content):
            if content in self.list_theme_dir():
                self.new_theme_editor_label["text"] = _("Theme name already exists.")
                self.new_theme_editor_label["foreground"] = "red"
                self.new_theme_editor_ok_button.state(["disabled"])
            else:
                self.new_theme_editor_ok_button.state(["!disabled"])
                self.new_theme_editor_label["text"] = _("Name")
                self.new_theme_editor_label["foreground"] = "white" if self.theme_is_dark else "black"
        else:
            self.new_theme_editor_ok_button.state(["disabled"])
            self.new_theme_editor_label["text"] = _("Error input: ") + r"^[a-zA-Z0-9_\- .&']+$"
            self.new_theme_editor_label["foreground"] = "red"
            pass

    def on_new_theme_editor_button_ok(self):
        current_directory = Path(self.themes_dir_path)
        configs_directory = Path("res/configs/")
        theme_name = self.new_theme_editor_entry.get()
        new_dir = current_directory / theme_name
        try:
            new_dir.mkdir()
            print(f"Directory '{new_dir}' created")
            # copy yaml
            if model_to_size_map[self.model_cb.get()] == SIZE_1:
                if (
                    self.new_theme_editor_orientation_combobox.get()
                    == orientation_list[0]
                ):
                    template_name = "theme_template_320x480.yaml"
                else:
                    template_name = "theme_template_480x320.yaml"
            elif model_to_size_map[self.model_cb.get()] == SIZE_2:
                if (
                    self.new_theme_editor_orientation_combobox.get()
                    == orientation_list[0]
                ):
                    template_name = "theme_template_480x800.yaml"
                else:
                    template_name = "theme_template_800x480.yaml"
            elif model_to_size_map[self.model_cb.get()] == SIZE_3:
                if (
                    self.new_theme_editor_orientation_combobox.get()
                    == orientation_list[0]
                ):
                    template_name = "theme_template_80x160.yaml"
                else:
                    template_name = "theme_template_160x80.yaml"
            else:
                messagebox.showerror(_("Error"), f"Unknown model")
                return

            dst_name = "theme.yaml"
            src_file = configs_directory / template_name
            dst_file = new_dir / dst_name
            try:
                shutil.copy2(src_file, dst_file)
                print(f"File '{src_file}' copy to '{dst_file}'")
            except FileNotFoundError:
                messagebox.showerror(_("Error"), f"Source '{src_file}' no found")
                self.new_theme_editor.destroy()
                return
            except Exception as e:
                messagebox.showerror(_("Error"), f"Error: {e}")
                self.new_theme_editor.destroy()
                return
            # new png
            template_name = "background.png"
            dst_file = new_dir / template_name
            if model_to_size_map[self.model_cb.get()] == SIZE_1:
                if (
                    self.new_theme_editor_orientation_combobox.get()
                    == orientation_list[0]
                ):
                    new_image = Image.new("RGB", (320, 480), "black")
                else:
                    new_image = Image.new("RGB", (480, 320), "black")
            elif model_to_size_map[self.model_cb.get()] == SIZE_2:
                if (
                    self.new_theme_editor_orientation_combobox.get()
                    == orientation_list[0]
                ):
                    new_image = Image.new("RGB", (480, 800), "black")
                else:
                    new_image = Image.new("RGB", (800, 480), "black")
            elif model_to_size_map[self.model_cb.get()] == SIZE_3:
                if (
                    self.new_theme_editor_orientation_combobox.get()
                    == orientation_list[0]
                ):
                    new_image = Image.new("RGB", (80, 160), "black")
                else:
                    new_image = Image.new("RGB", (160, 80), "black")
            else:
                messagebox.showerror(_("Error"), f"Unknown model")
                return

            new_image.save(dst_file)

            # save theme change
            self.on_model_change()
            self.theme_cb.set(theme_name)
            self.save_config_values()
            self.on_theme_editor_click()
            self.new_theme_editor.destroy()

        except FileExistsError:
            messagebox.showerror(_("Error"), f"Directory '{new_dir}' already exists")
            self.new_theme_editor.destroy()
            return

    def on_delete_theme_click(self):
        if self.is_theme_editor_process():
            return
        self.delete_theme_frame = tkinter.Toplevel(self.window)
        self.delete_theme_frame.title(_("Delete theme"))
        self.delete_theme_frame.withdraw()

        def on_delete_theme_frame_closing():
            self.delete_theme_frame.grab_release()
            self.delete_theme_frame.destroy()

        self.delete_theme_frame.protocol(
            "WM_DELETE_WINDOW", on_delete_theme_frame_closing
        )
        self.delete_theme_frame.resizable(False, False)
        self.delete_theme_frame.grab_set()

        self.delete_theme_label = ttk.Label(
            self.delete_theme_frame, text=_("Delete theme: ") + f"{self.theme_cb.get()} ?",wraplength = 340
        )
        self.delete_theme_label.pack(
            side=tkinter.TOP, padx=5, pady=10, ipadx=30, anchor=tkinter.W
        )

        cancel_button = ttk.Button(
            self.delete_theme_frame, text=_("NO"), command=on_delete_theme_frame_closing
        )
        cancel_button.pack(side=tkinter.RIGHT, padx=5, pady=5)

        self.delete_theme_frame.update()
        main_window_x = self.window.winfo_x()
        main_window_y = self.window.winfo_y()
        main_window_width = self.window.winfo_width()
        main_window_height = self.window.winfo_height()
        width = self.delete_theme_frame.winfo_width()
        height = self.delete_theme_frame.winfo_height()
        x = main_window_x + (main_window_width // 2) - (width // 2)
        y = main_window_y + (main_window_height // 2) - (height // 2)
        self.delete_theme_frame.geometry(f"{width}x{height}+{x}+{y}")
        self.delete_theme_frame.deiconify()

        self.delete_theme_frame.focus_force()

        utils.apply_theme_to_titlebar(self.delete_theme_frame,self.theme_is_dark)

        def on_delete_theme_frame_ok():
            current_directory = Path(self.themes_dir_path)
            theme_name = self.theme_cb.get()
            delete_dir = current_directory / theme_name
            try:
                if delete_dir.exists() and delete_dir.is_dir():
                    import shutil
                    shutil.rmtree(delete_dir)
                    print(f"Directory {delete_dir} and all of its contents have been deleted")
                else:
                    print(f"Directory {delete_dir} does not exist or is not a valid directory.")
            except OSError as error:
                print(f"Error deleting directory: {error}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

            self.on_model_change()
            self.theme_cb.current(0)
            self.save_config_values()
            self.delete_theme_frame.grab_release()
            self.delete_theme_frame.destroy()

        ok_button = ttk.Button(
            self.delete_theme_frame, text=_("OK"), command=on_delete_theme_frame_ok
        )
        ok_button.pack(side=tkinter.RIGHT, padx=5, pady=5)

    def on_theme_editor_click(self):
        if self.is_theme_editor_process():
            return
        self.save_config_values()
        self.theme_editor_process = utils.run.theme_editor(self.theme_cb.get())

    def on_theme_dir_click(self):
        dir_path = Path(self.themes_dir_path) / self.theme_cb.get()
        if dir_path.exists():
            if platform.system() == "Windows":  
                os.startfile(str(dir_path))  
            elif platform.system() == "Darwin":  # macOS  
                os.system(f'open "{dir_path}"')  
            else:  # Linux  
                os.system(f'xdg-open "{dir_path}"')

    def on_copy_theme_editor_click(self):
        if self.is_theme_editor_process():
            return
        self.copy_theme_editor = tkinter.Toplevel(self.window)
        self.copy_theme_editor.title(_("Copy theme"))
        self.copy_theme_editor.withdraw()
        
        self.copy_theme_editor.protocol(
            "WM_DELETE_WINDOW", self.on_copy_theme_editor_closing
        )
        self.copy_theme_editor.resizable(False, False)
        self.copy_theme_editor.grab_set()
        self.copy_theme_editor_label = ttk.Label(self.copy_theme_editor, text=_("Name"))
        self.copy_theme_editor_label.pack(
            side=tkinter.TOP, padx=10, pady=10, anchor=tkinter.W
        )

        self.copy_theme_editor_entry = utils.EnhancedEntry(self.copy_theme_editor,label_text=self.entry_label_text)
        self.copy_theme_editor_entry.pack(fill=tkinter.X, expand=True, padx=10,ipadx=30)
        self.copy_theme_editor_entry.bind(
            "<KeyRelease>", self.copy_theme_editor_entry_change
        )

        cancel_button = ttk.Button(
            self.copy_theme_editor,
            text=_("Cancel"),
            command=self.on_copy_theme_editor_closing,
        )
        cancel_button.pack(side=tkinter.RIGHT, padx=10, pady=10)

        self.copy_theme_editor_ok_button = ttk.Button(
            self.copy_theme_editor, text="OK", command=self.on_copy_theme_editor_button_ok
        )
        self.copy_theme_editor_ok_button.pack(side=tkinter.RIGHT, padx=5, pady=10)
        self.copy_theme_editor_ok_button.state(["disabled"])

        self.copy_theme_editor.update()
        main_window_x = self.window.winfo_x()
        main_window_y = self.window.winfo_y()
        main_window_width = self.window.winfo_width()
        main_window_height = self.window.winfo_height()
        width = self.copy_theme_editor.winfo_width()
        height = self.copy_theme_editor.winfo_height()
        x = main_window_x + (main_window_width // 2) - (width // 2)
        y = main_window_y + (main_window_height // 2) - (height // 2)
        self.copy_theme_editor.geometry(f"{width}x{height}+{x}+{y}")
        self.copy_theme_editor.deiconify()

        self.copy_theme_editor_entry.insert(0,self.theme_cb.get()+'_0')
        self.copy_theme_editor_entry_change()
        self.copy_theme_editor.focus_force()

        utils.apply_theme_to_titlebar(self.copy_theme_editor,self.theme_is_dark)

    def on_copy_theme_editor_closing(self):
        self.copy_theme_editor.grab_release()
        self.copy_theme_editor.destroy()

    def copy_theme_editor_entry_change(self, event=None):
        content = self.copy_theme_editor_entry.get()
        if self.validate_entry(content):
            if content in self.list_theme_dir():
                self.copy_theme_editor_label["text"] = _("Theme name already exists.")
                self.copy_theme_editor_label["foreground"] = "red"
                self.copy_theme_editor_ok_button.state(["disabled"])
            else:
                self.copy_theme_editor_ok_button.state(["!disabled"])
                self.copy_theme_editor_label["text"] = _("Name")
                self.copy_theme_editor_label["foreground"] = "white" if self.theme_is_dark else "black"
        else:
            self.copy_theme_editor_ok_button.state(["disabled"])
            self.copy_theme_editor_label["text"] = _("Error input: ") + r"^[a-zA-Z0-9_\- ]+$"
            self.copy_theme_editor_label["foreground"] = "red"
            pass

    def on_copy_theme_editor_button_ok(self):
        current_directory = Path(self.themes_dir_path)
        src_dir = current_directory / self.theme_cb.get()
        dst_dir = current_directory / self.copy_theme_editor_entry.get()

        try:
            # Check if the source directory exists and is a valid directory
            if src_dir.exists() and src_dir.is_dir():
                # Copy the source directory to the destination directory
                shutil.copytree(src_dir, dst_dir)
                print(f"Directory '{src_dir}' copied to '{dst_dir}'")
            else:
                # Show an error message if the source directory does not exist
                messagebox.showerror(_("Error"), f"Source '{src_dir}' not found")
                self.copy_theme_editor.destroy()
                return
        except FileExistsError:
            # Show an error message if the destination directory already exists
            messagebox.showerror(_("Error"), f"Destination '{dst_dir}' already exists")
            self.copy_theme_editor.destroy()
            return
        except PermissionError:
            # Show an error message if permission is denied during the copy operation
            messagebox.showerror(_("Error"), f"Permission denied when copying to '{dst_dir}'")
            self.copy_theme_editor.destroy()
            return
        except Exception as e:
            # Show a generic error message for other exceptions
            messagebox.showerror(_("Error"), f"Error: {e}")
            self.copy_theme_editor.destroy()
            return
        
        # save theme change
        self.on_model_change()
        self.theme_cb.set(self.copy_theme_editor_entry.get())
        self.save_config_values()
        self.on_theme_editor_click()
        self.copy_theme_editor.destroy()

    def on_save_click(self):
        if self.is_theme_editor_process():
            return
        self.save_config_values()

    def on_display_other_config_click(self):
        if self.display_other_config_process != None:
            if self.display_other_config_process.poll() == None:
                messagebox.showerror(_("Error"), _("display other config is running !"))
                return
            
        if self.display_init == True:
            self.display_off()
            self.display_init = False
            self.live_display_bool_var.set(False)
            time.sleep(1)
        model = self.model_cb.get()
        if model == WEACT_A_MODEL:
            self.display_other_config_process = utils.run.weact_device_setting(0)
        else:
            self.display_other_config_process = utils.run.weact_device_setting(1)

    def on_saverun_click(self):
        if self.is_theme_editor_process():
            return
        if self.display_init == True:
            self.display_off()
            self.display_init = False
            self.live_display_bool_var.set(False)
        self.save_config_values()
        utils.run.main()
        self.window.destroy()

    def on_brightness_change(self, e=None):
        self.brightness_string.set(str(int(self.brightness_slider.get())) + "%")

    def on_model_change(self, e=None):
        model = self.model_cb.get()
        if "Simulated" in model:
            self.com_cb.configure(state="disabled")
            self.orient_cb.configure(state="disabled")
            self.brightness_slider.configure(state="disabled")
            self.brightness_val_label.configure(state="disabled")
            self.com_refresh_button.configure(state="disabled")
        else:
            self.com_cb.configure(state="readonly")
            self.orient_cb.configure(state="readonly")
            self.brightness_slider.configure(state="normal")
            self.brightness_val_label.configure(state="normal")
            self.com_refresh_button.configure(state="normal")

            if model == WEACT_A_MODEL or model == WEACT_B_MODEL:
                self.other_setting_button.configure(state="normal")
            else:
                self.other_setting_button.configure(state="disabled")

        themes = self.theme_get.get_themes(model_to_size_map[model])
        self.theme_cb.config(values=themes)

        if not self.theme_cb.get() in themes:
            # The selected theme does not exist anymore / is not allowed for this screen model : select 1st theme avail.
            if len(themes) > 0:
                self.theme_cb.set(themes[0])
            else:
                self.theme_cb.set("")

        self.size_select_label["text"] = model_to_size_map[model]

    def on_hwlib_change(self, e=None):
        hwlib = [k for k, v in hw_lib_map.items() if v == self.hwlib_cb.get()][0]
        if hwlib == "STUB" or hwlib == "STATIC":
            self.eth_cb.configure(state="disabled")
            self.wl_cb.configure(state="disabled")
        else:
            self.eth_cb.configure(state="readonly")
            self.wl_cb.configure(state="readonly")

        if sys.platform == "win32":
            import ctypes

            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if (hwlib == "LHM" or hwlib == "AUTO") and not is_admin:
                self.lhm_admin_warning.grid(row=7, column=0, columnspan=3, padx=5, pady=5,sticky="w")
                self.save_run_btn['state'] = "disabled"
                self.live_display_bool_var.set(False)
                self.live_display_checkbox['state'] = "disabled"
            else:
                self.lhm_admin_warning.grid_forget()
                self.save_run_btn['state'] = "normal"
                self.live_display_checkbox['state'] = "normal"
        else:
            if hwlib == "PYTHON" or hwlib == "AUTO":
                self.cpu_fan_label.grid(row=5, column=0, padx=5, pady=5,sticky="w")
                self.cpu_fan_cb.grid(row=5, column=1, columnspan=2, padx=5, pady=5,sticky="w"+"e")
            else:
                self.cpu_fan_label.grid_forget()
                self.cpu_fan_cb.grid_forget()

        self.theme_setting_change = True
        self.display_setting_change = True

    def on_fan_speed_update(self):
        # Update fan speed periodically
        prev_value = self.cpu_fan_cb.current()  # Save currently selected index
        self.cpu_fan_cb.config(values=get_fans())
        if prev_value != -1:
            self.cpu_fan_cb.current(
                prev_value
            )  # Force select same index to refresh displayed value
        self.window.after(500, self.on_fan_speed_update)

    def on_bootstrap_checkbutton_toggle(self):
        from library import schedule_service

        schedule_task_exist, schedule_task_path_get = schedule_service.task_exists(
            self.schedule_task_name
        )
        if schedule_task_exist == True:
            print(f"schedule service delete task: {self.schedule_task_name}")
            schedule_service.delete_task(self.schedule_task_name)
        v = self.bootstrap_checkbutton_var.get()
        if v == True:
            print(f"schedule service add task: {self.schedule_task_name}")
            schedule_service.create_login_task(
                self.schedule_task_name, self.schedule_task_path
            )

    def on_com_refresh_button(self):
        com_now = self.com_cb.get()
        self.com_cb['values'] = get_com_ports()
        if com_now not in self.com_cb['values']:
            self.com_cb.current(0)

class PingWeatherConfigWindow:
    def __init__(self, main_window: ConfigWindow):
        self.window = tkinter.Toplevel()
        self.window.withdraw()
        self.window.title(_("Ping & Weather Configure"))

        self.main_window = main_window

        self.entry_label_text = {}
        self.entry_label_text['Copy'] = _('Copy')
        self.entry_label_text['Paste'] = _('Paste')
        self.entry_label_text['Cut'] = _('Cut')
        self.entry_label_text['Undo'] = _('Undo')
        self.entry_label_text['Redo'] = _('Redo')

        # ping frame
        self.ping_frame = tkinter.Frame(self.window)
        self.ping_frame.grid(row=0, column=0, columnspan=4, padx=5, pady=5,sticky="w")
        self.ping_label = ttk.Label(self.ping_frame, text="Ping", font=("Arial", 13, "bold"))
        self.ping_label.grid(row=0, column=0, padx=5, pady=5,sticky="w")
        self.ping_label1 = ttk.Label(self.ping_frame, text=_("Hostname / IP to ping"))
        self.ping_label1.grid(row=1, column=0, padx=5, pady=5,sticky="w")
        self.ping_entry = utils.EnhancedEntry(self.ping_frame,label_text=self.entry_label_text)
        self.ping_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5,sticky="w"+"e")

        # weather frame
        self.weather_frame = tkinter.Frame(self.window)
        self.weather_frame.columnconfigure(1,weight=1)
        self.weather_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=5,sticky="w")
        weather_label = ttk.Label(self.weather_frame, text=_("Weather forecast (OpenWeatherMap API)"), font=("Arial", 13, "bold"))
        weather_label.grid(row=0, column=0, columnspan=3, padx=5, pady=5,sticky="w")

        weather_info_label = ttk.Label(self.weather_frame,
                                       text=_("To display weather forecast on themes that support it, you need an OpenWeatherMap API key."
                                            "\nIt use \"Current weather data api\": https://openweathermap.org/current .\n"
                                            "You will get 1,000 API calls per day for free. This program is configured to stay under this threshold (~300 calls/day)."))
        weather_info_label.grid(row=1, column=0, columnspan=3, padx=5, pady=5,sticky="w")
        weather_api_link_label = ttk.Label(self.weather_frame,
                                           text=_("Click here to Create an OpenWeatherMap Account."))
        weather_api_link_label.grid(row=2, column=0, columnspan=3, padx=5, pady=5,sticky="w")
        weather_api_link_label.config(foreground="#a3a3ff", cursor="hand2")
        weather_api_link_label.bind("<Button-1>",
                                    lambda e: webbrowser.open_new_tab("https://home.openweathermap.org/users/sign_up"))

        self.api_label = ttk.Label(self.weather_frame, text="OpenWeatherMap API key")
        self.api_label.grid(row=3, column=0, padx=5, pady=5,sticky="w")
        self.api_entry = utils.EnhancedEntry(self.weather_frame,label_text=self.entry_label_text)
        self.api_entry.grid(row=3, column=1, columnspan=2, padx=5, pady=5,sticky="w"+"e")

        # latlong frame
        self.latlong_frame = tkinter.Frame(self.window)
        self.latlong_frame.grid(row=2, column=0, columnspan=4, padx=5, pady=5,sticky="w")
        latlong_label = ttk.Label(self.latlong_frame,
                                  text=_("You can use online services to get your latitude/longitude e.g. latlong.net (click here)"))
        latlong_label.grid(row=0, column=0, columnspan=4, padx=5, pady=5,sticky="w")
        latlong_label.config(foreground="#a3a3ff", cursor="hand2")
        latlong_label.bind("<Button-1>",
                           lambda e: webbrowser.open_new_tab("https://www.latlong.net/"))

        self.lat_label = ttk.Label(self.latlong_frame, text=_("Latitude"))
        self.lat_label.grid(row=1, column=0, padx=5, pady=5,sticky="w")
        self.lat_entry = utils.EnhancedEntry(self.latlong_frame,label_text=self.entry_label_text, validate="key",
                                   validatecommand=(self.window.register(self.validateCoord), "%P"))
        self.lat_entry.grid(row=1, column=1, padx=5, pady=5,sticky="w"+"e")

        self.long_label = ttk.Label(self.latlong_frame, text=_("Longitude"))
        self.long_label.grid(row=1, column=2, padx=5, pady=5,sticky="w")
        self.long_entry = utils.EnhancedEntry(self.latlong_frame,label_text=self.entry_label_text, validate="key",
                                    validatecommand=(self.window.register(self.validateCoord), "%P"))
        self.long_entry.grid(row=1, column=3, padx=5, pady=5,sticky="w"+"e")
        
        self.get_latlong_btn = ttk.Button(self.latlong_frame, text=_("Get via IP"), command=lambda: self.on_get_latlong_click())
        self.get_latlong_btn.grid(row=1, column=4, padx=5, pady=5,sticky="e")

        self.unit_label = ttk.Label(self.latlong_frame, text=_("Units"))
        self.unit_label.grid(row=2, column=0, padx=5, pady=5,sticky="w")
        self.unit_cb = ttk.Combobox(self.latlong_frame, values=list(utils.TEMPERATURE_UNIT_MAP.values()), state="readonly")
        self.unit_cb.grid(row=2, column=1,columnspan=4, padx=5, pady=5,sticky="w")

        self.lang_label = ttk.Label(self.latlong_frame, text=_("Language"))
        self.lang_label.grid(row=3, column=0, padx=5, pady=5,sticky="w")
        self.lang_cb = ttk.Combobox(self.latlong_frame, values=list(utils.WEATHER_LANG_MAP.values()), state="readonly")
        self.lang_cb.grid(row=3, column=1,columnspan=4, padx=5, pady=5,sticky="w")

        # test and save frame
        self.test_and_save_frame = tkinter.Frame(self.window)
        self.test_and_save_frame.columnconfigure(0,weight=1)
        self.test_and_save_frame.grid(row=3, column=0, columnspan=4, padx=5, pady=5,sticky="we")

        self.test_result_label = ttk.Label(self.test_and_save_frame, text='\n\n\n\n')
        self.test_result_label.grid(row=0, column=0, padx=5, pady=5,sticky="w")

        self.ping_test_btn = ttk.Button(self.test_and_save_frame, text=_("Test Ping"), command=lambda: self.on_ping_test_btn_click())
        self.ping_test_btn.grid(row=0, column=1, padx=5, pady=5, ipady=10,sticky="e")

        self.weather_api_test_btn = ttk.Button(self.test_and_save_frame, text=_("Test API"), command=lambda: self.on_weather_api_test_btn_click())
        self.weather_api_test_btn.grid(row=0, column=2, padx=5, pady=5, ipady=10,sticky="e")

        self.save_btn = ttk.Button(self.test_and_save_frame, text=_("Save settings"), command=lambda: self.on_save_click())
        self.save_btn.grid(row=0, column=3, padx=5, pady=5, ipady=10, sticky="e")

        # bind events
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    def validateCoord(self, coord: str):
        if not coord:
            return True
        try:
            float(coord)
        except:
            return False
        return True

    def show(self):
        self.load_config_values(self.main_window.config)
        self.window.withdraw()
        self.window.update()
        main_window_x = self.main_window.window.winfo_x()
        main_window_y = self.main_window.window.winfo_y()
        main_window_width = self.main_window.window.winfo_width()
        main_window_height = self.main_window.window.winfo_height()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = main_window_x + (main_window_width // 2) - (width // 2)
        y = main_window_y + (main_window_height // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.resizable(False, False)
        self.window.deiconify()
        self.window.focus_force()
        self.window.grab_set()

        utils.apply_theme_to_titlebar(self.window,self.main_window.theme_is_dark)

    def on_closing(self):
        self.window.grab_release()
        self.window.destroy()

    def load_config_values(self, config):
        self.config = config

        try:
            self.ping_entry.insert(0, self.config['config']['PING'])
        except:
            self.ping_entry.insert(0, "8.8.8.8")

        try:
            self.api_entry.insert(0, self.config['config']['WEATHER_API_KEY'])
        except:
            pass

        try:
            self.lat_entry.insert(0, self.config['config']['WEATHER_LATITUDE'])
        except:
            self.lat_entry.insert(0, "45.75")

        try:
            self.long_entry.insert(0, self.config['config']['WEATHER_LONGITUDE'])
        except:
            self.long_entry.insert(0, "45.75")

        try:
            self.unit_cb.set(utils.TEMPERATURE_UNIT_MAP[self.config['config']['WEATHER_UNITS']])
        except:
            self.unit_cb.set(0)

        try:
            self.lang_cb.set(utils.WEATHER_LANG_MAP[self.config['config']['WEATHER_LANGUAGE']])
        except:
            self.lang_cb.set(utils.WEATHER_LANG_MAP["en"])

    def on_ping_test_btn_click(self):
        host = self.ping_entry.get()
        if host == "":
            self.test_result_label.config(text=_("\n\nPlease enter a hostname or IP address.\n\n"))
            return
        delay = utils.get_ping_delay(host)
        if delay == -1:
            self.test_result_label.config(text=_("\n\nPing failed!\n\n"))
        else:
            self.test_result_label.config(text=_("\n\nPing successful!") + f" {delay:.2f} ms\n\n")

    def on_weather_api_test_btn_click(self):
        api_key = self.api_entry.get()
        lat = self.lat_entry.get()
        long = self.long_entry.get()
        unit = [k for k, v in utils.TEMPERATURE_UNIT_MAP.items() if v == self.unit_cb.get()][0]
        lang = [k for k, v in utils.WEATHER_LANG_MAP.items() if v == self.lang_cb.get()][0]
        temp, feel, desc, humidity, time, result= utils.get_weather(lat, long, api_key, unit, lang)
        self.test_result_label.config(text=_("Temperature: ")+f"{temp}\n"+_("Temperature Felt: ")+f"{feel}\n"+_("Humidity: ")+f"{humidity}\n"+_("Description: ")+f"{desc}\n"+_("Update Time: ")+f"{time}")

    def on_get_latlong_click(self):
        g = geocoder.ip('me')
        if g.ok:
            self.lat_entry.delete(0, 'end')
            self.lat_entry.insert(0, str(g.latlng[0]))
            self.long_entry.delete(0, 'end')
            self.long_entry.insert(0, str(g.latlng[1]))

    def on_save_click(self):
        self.save_config_values()
        self.on_closing()

    def save_config_values(self):
        ping = self.ping_entry.get()
        api_key = self.api_entry.get()
        lat = self.lat_entry.get()
        long = self.long_entry.get()
        unit = [k for k, v in utils.TEMPERATURE_UNIT_MAP.items() if v == self.unit_cb.get()][0]
        lang = [k for k, v in utils.WEATHER_LANG_MAP.items() if v == self.lang_cb.get()][0]

        self.main_window.save_additional_config(ping=ping, api_key=api_key, lat=lat, long=long, unit=unit, lang=lang)

class WorkspaceSettingsWindow:
    def __init__(self, main_window: ConfigWindow):
        self.window = tkinter.Toplevel()
        self.window.withdraw()
        self.window.title(_("Workspace Settings"))

        self.main_window = main_window
        
        self.entry_label_text = {}
        self.entry_label_text['Copy'] = _('Copy')
        self.entry_label_text['Paste'] = _('Paste')
        self.entry_label_text['Cut'] = _('Cut')
        self.entry_label_text['Undo'] = _('Undo')
        self.entry_label_text['Redo'] = _('Redo')

        # theme folder 
        theme_folder_label = ttk.Label(self.window, text=_("Themes Folder:"))
        theme_folder_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.theme_folder_path = tkinter.StringVar()
        self.theme_folder_entry = utils.EnhancedEntry(self.window,label_text=self.entry_label_text, textvariable=self.theme_folder_path, width=50)
        self.theme_folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")

        theme_folder_button = ttk.Button(self.window, text=_("Select Folder"), command=self.select_theme_folder)
        theme_folder_button.grid(row=0, column=2, padx=5, pady=5, sticky="we")

        # font folder
        font_folder_label = ttk.Label(self.window, text=_("Fonts Folder:"))
        font_folder_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.font_folder_path = tkinter.StringVar()
        self.font_folder_entry = utils.EnhancedEntry(self.window,label_text=self.entry_label_text, textvariable=self.font_folder_path, width=50)
        self.font_folder_entry.grid(row=1, column=1, padx=5, pady=5, sticky="we")

        font_folder_button = ttk.Button(self.window, text=_("Select Folder"), command=self.select_font_folder)
        font_folder_button.grid(row=1, column=2, padx=5, pady=5, sticky="we")

        self.save_btn = ttk.Button(self.window, text=_("Save settings"), command=lambda: self.on_save_click())
        self.save_btn.grid(row=2, column=2, padx=5, pady=5, sticky="We")

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    def show(self):
        self.load_config_values(self.main_window.config)
        self.window.withdraw()
        self.window.update()
        main_window_x = self.main_window.window.winfo_x()
        main_window_y = self.main_window.window.winfo_y()
        main_window_width = self.main_window.window.winfo_width()
        main_window_height = self.main_window.window.winfo_height()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = main_window_x + (main_window_width // 2) - (width // 2)
        y = main_window_y + (main_window_height // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.resizable(False, False)
        self.window.deiconify()
        self.window.focus_force()
        self.window.grab_set()

        utils.apply_theme_to_titlebar(self.window,self.main_window.theme_is_dark)
    
    def on_closing(self):
        self.window.grab_release()
        self.window.destroy()
    
    def load_config_values(self, config):
        self.config = config
        try:
            self.theme_folder_path.set(self.config['config']['THEMES_DIR'])
        except:
            self.theme_folder_path.set("res/themes")
        
        try:
            self.font_folder_path.set(self.config['config']['FONTS_DIR'])
        except:
            self.font_folder_path.set("res/fonts")

    def select_theme_folder(self):
        folder = filedialog.askdirectory(initialdir = Path.cwd(), title=_("Themes Folder:"))
        if folder:
            self.theme_folder_path.set(folder)

    def select_font_folder(self):
        folder = filedialog.askdirectory(initialdir = Path.cwd(), title=_("Fonts Folder:"))
        if folder:
            self.font_folder_path.set(folder)

    def on_save_click(self):
        if self.save_config_values():
            self.on_closing()

    def save_config_values(self):
        theme = self.theme_folder_path.get()
        font = self.font_folder_path.get()
        if theme == "":
            theme = str(Path("res/themes"))
        if font == "":
            font = str(Path("res/fonts"))
        if Path(theme).is_dir() and Path(theme).exists() and Path(font).is_dir() and Path(font).exists():
            self.main_window.save_additional_config(theme_dir=theme, font_dir=font)
        else:
            messagebox.showerror(_("Error"), _("Theme or Font folder is not valid!"))
            return False
        return True
        
if __name__ == "__main__":
    configurator = ConfigWindow()
    configurator.run()
    app_exit()
