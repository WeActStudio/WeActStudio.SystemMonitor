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

# theme-editor.py: Allow to easily edit themes for System Monitor (main.py) in a preview window on the computer
# The preview window is refreshed as soon as the theme file is modified

import locale
import logging
import os
import platform
import sys
import time
import copy
from pathlib import Path

import tkinter
from tkinter import ttk
from tkinter import colorchooser
from tkinter import scrolledtext
from tkinter import messagebox
from PIL import ImageTk

if getattr(sys, "frozen", False):
    executable_name = os.path.splitext(os.path.basename(sys.executable))[0]
    executable_dir = Path(sys.executable).parent
else:
    executable_name = os.path.splitext(os.path.basename(__file__))[0]
    executable_dir = Path(__file__).parent

sys.path.append(str(executable_dir.parent))

import lib.utils as utils
os.chdir(utils.get_root_dir())
config_file = "config.yaml"

import argparse
parser = argparse.ArgumentParser(description="WeActStudio System Monitor theme-editor")
parser.add_argument(
    "theme_name",
    type=str,
    help="Theme name",
)

args = parser.parse_args()

if getattr(sys, "frozen", False):
    utils.std_redirect_logfile(executable_name)

import lib.log
# Hardcode specific configuration for theme editor
from lib import config
config.load_config(config_file)

config.CONFIG_DATA["config"][
    "HW_SENSORS"
] = "STATIC"  # For theme editor always use stub data

theme_name = args.theme_name.strip('"')
config.CONFIG_DATA["config"]["THEME"] = theme_name  # Theme is given as argument
config.load_theme_edit()
config.load_theme()

# For theme editor, always use simulated LCD
if config.THEME_DATA["display"].get("DISPLAY_SIZE", "320x480") == "480x800":
    config.CONFIG_DATA["display"]["REVISION"] = "SIMU_480x800"
elif config.THEME_DATA["display"].get("DISPLAY_SIZE", "320x480") == "80x160":
    config.CONFIG_DATA["display"]["REVISION"] = "SIMU_80x160"
else:
    config.CONFIG_DATA["display"]["REVISION"] = "SIMU_320x480"
from lib.display import display  # Only import display after hardcoded config is set
display.init()

class dict_tools:
    def sort_dict_by_order(d, order):
        """
        根据指定的顺序对字典的键进行排序，并返回一个新的字典。
        如果原始字典中有不在指定顺序中的键，它们将被添加到结果字典的末尾（保持插入顺序）。

        参数:
        d (dict): 原始字典。
        order (list): 包含排序顺序的键的列表。

        返回:
        dict: 按键排序后的新字典。
        """
        # 初始化一个空字典来存储排序后的键值对
        sorted_dict = {}

        # 遍历order列表，如果键在字典d中，则添加到sorted_dict中
        for key in order:
            if key in d:
                sorted_dict[key] = d[key]

        # 遍历字典d的剩余键（即那些不在order中的键），并将它们添加到sorted_dict中
        # 注意：这将保持这些键在sorted_dict中的添加顺序（Python 3.7+）
        for key in d:
            if key not in sorted_dict:
                sorted_dict[key] = d[key]

        return sorted_dict


class file_tools:
    res_fonts_path = config.FONTS_DIR

    @staticmethod
    def list_res_fonts():
        fonts = []
        for file in file_tools.res_fonts_path.rglob('*'):
            if file.suffix.lower() in ['.ttf', '.otf']:
                relative_path = file.relative_to(file_tools.res_fonts_path)
                fonts.append(str(relative_path))
        return fonts

    def list_theme_pic():
        pic = list()
        for root, dirs, files in os.walk(config.CURRENT_THEME_PATH):
            for file in files:
                file_l = file.lower()
                if (
                    file_l.endswith(".png")
                    or file_l.endswith(".jpg")
                    or file_l.endswith(".bmp")
                ):
                    relative_path = Path(root).relative_to(config.CURRENT_THEME_PATH)
                    pic.append(str(relative_path / file))
        return pic

file_tools.list_res_fonts()

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if self.tooltip is None:
            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25
            self.tooltip = tkinter.Toplevel(self.widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            label = ttk.Label(self.tooltip, text=self.text)
            label.pack()

    def hide_tooltip(self, event):
        if self.tooltip is not None:
            self.tooltip.destroy()
            self.tooltip = None


class theme_editor:
    def __init__(self) -> None:
        self.image_scaler_process = None

        self.RGB_LED_MARGIN = 12

        self.x0 = 0
        self.y0 = 0

        if display.lcd.get_width() < display.lcd.get_height():
            self.image_width = 320
            self.image_height = 480
        elif display.lcd.get_width() > display.lcd.get_height():
            self.image_width = 480
            self.image_height = 320
        else:
            self.image_width = 320
            self.image_height = 320

        self.theme_preview_path = config.CURRENT_THEME_PATH / "preview.png"
        
        self.theme_file_change = False
        self.theme_refresh = True
        self.theme_file_unsave = False

        self.image_scaler = None

        self.entry_label_text = {}
        self.entry_label_text['Copy'] = _('Copy')
        self.entry_label_text['Paste'] = _('Paste')
        self.entry_label_text['Cut'] = _('Cut')
        self.entry_label_text['Undo'] = _('Undo')
        self.entry_label_text['Redo'] = _('Redo')

        self.main_refresh_tick = 0

        lib.log.logger.setLevel(
            logging.NOTSET
        )  # Disable system monitor logging for the editor

        # Create a logger for the editor
        self.logger = logging.getLogger("theme-editor")
        self.logger.setLevel(logging.DEBUG)

        # Apply system locale to this program
        locale.setlocale(locale.LC_ALL, "")

        self.logger.debug("Starting WeAct Studio System Monitor Theme Editor...")

        # Get theme file to edit
        self.theme_file = config.CURRENT_THEME_PATH / "theme.yaml"
        self.last_edit_time = os.path.getmtime(self.theme_file)
        self.logger.debug("Using theme file " + str(self.theme_file))

        # Open theme in default editor. You can also open the file manually in another program
        # self.logger.debug(
        #     "Opening theme file in your default editor. If it does not work, open it manually in the "
        #     "editor of your choice"
        # )
        # if platform.system() == 'Darwin':  # macOS
        #     subprocess.call(('open', "./" + self.theme_file))
        # elif platform.system() == 'Windows':  # Windows
        #     os.startfile(".\\" + self.theme_file)
        # else:  # linux variants
        #     subprocess.call(('xdg-open', "./" + self.theme_file))

        # Create preview window
        self.logger.debug("Opening theme preview window with static data")

        self.main = tkinter.Tk()

        self.main.title(_("WeAct Studio System Monitor Theme Editor") + f" - {theme_name}")

        self.main.iconphoto(True, tkinter.PhotoImage(file=utils.get_root_dir() / "res" / "icons" / "logo.png"))
        self.main.geometry(
            str(self.image_width + 3 * self.RGB_LED_MARGIN + 600)
            + "x"
            + str(self.image_height + 4 * self.RGB_LED_MARGIN + 40 + 100)
        )
        self.main.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.main.resizable(False, False)

        style = ttk.Style()
        self.theme_is_dark = False
        if platform.system() == "Windows" and sys.getwindowsversion().major >= 10:
            import darkdetect
            self.theme_is_dark = darkdetect.theme() == "Dark"
            if self.theme_is_dark:
                self.main.tk.call("source", utils.get_root_dir() / "res" / "tk_themes" / "sv_ttk" / "theme" / "dark.tcl")
                style.theme_use("sun-valley-dark")
            else:
                self.main.tk.call("source", utils.get_root_dir() / "res" / "tk_themes" / "sv_ttk" / "theme" / "light.tcl")
                style.theme_use("sun-valley-light")
        else:
            self.main.tk.call("source", utils.get_root_dir() / "res" / "tk_themes" / "sv_ttk" / "theme" / "light.tcl")
            style.theme_use("sun-valley-light")
        utils.apply_theme_to_titlebar(self.main,self.theme_is_dark)
        self.main.update()

        self.viewer = tkinter.Frame(self.main)
        self.viewer.config(cursor="cross")
        # Display RGB backplate LEDs color as background color
        led_color = config.THEME_DATA["display"].get("DISPLAY_RGB_LED", (255, 255, 255))
        if isinstance(led_color, str):
            led_color = tuple(map(int, led_color.split(", ")))
        self.viewer.configure(bg="#%02x%02x%02x" % led_color)
        # viewer.pack(fill=tkinter.BOTH, expand=True)
        self.viewer.place(
            x=0,
            y=0,
            width=self.image_width + 2 * self.RGB_LED_MARGIN,
            height=self.image_height + 2 * self.RGB_LED_MARGIN + 40,
        )

        # Display preview in the window
        self.display_image = ImageTk.PhotoImage(display.lcd.screen_image)
        self.viewer_picture = tkinter.Label(
            self.viewer, image=self.display_image, borderwidth=0
        )
        self.viewer_picture.place(x=self.RGB_LED_MARGIN + (self.image_width-display.lcd.get_width())/2, y=self.RGB_LED_MARGIN + (self.image_height-display.lcd.get_height())/2)

        # Allow to click on preview to show coordinates and draw zones
        self.viewer_picture.bind("<ButtonPress-1>", self.on_button1_press)
        self.viewer_picture.bind("<B1-Motion>", self.on_button1_press_and_drag)
        self.viewer_picture.bind("<ButtonRelease-1>", self.on_button1_release)

        self.label_coord = tkinter.Label(
            self.viewer, text=_("Click or draw a zone to show coordinates")
        )
        self.label_coord.place(
            x=0,
            y=self.image_height + 2 * self.RGB_LED_MARGIN,
            width=self.image_width + 2 * self.RGB_LED_MARGIN,
        )

        self.label_info = tkinter.Label(
            self.viewer,
            text=_("This preview size: ")
            + f"{display.lcd.get_height()}x{display.lcd.get_width()}",
        )
        self.label_info.place(
            x=0,
            y=self.image_height + 2 * self.RGB_LED_MARGIN + 20,
            width=self.image_width + 2 * self.RGB_LED_MARGIN,
        )

        self.label_zone = tkinter.Label(
            self.viewer, bg="#%02x%02x%02x" % tuple(map(lambda x: 255 - x, led_color))
        )
        self.label_zone.bind("<ButtonRelease-1>", self.on_zone_click)

        self.file_frame_init()
        self.theme_init()
        self.editor_init()
        self.logger_frame_init()

        # Load theme file and generate first preview
        self.refresh_theme()

        self.main_refresh()

        self.theme_file_unsave = False

        self.logger.debug(
            "You can now edit the theme file in the editor. When you save your changes, the preview window will "
            "update automatically"
        )

        self.main.mainloop()

    def file_frame_init(self):
        self.file_frame = tkinter.Frame(self.main)
        self.file_frame.place(
            x=self.image_width + 3 * self.RGB_LED_MARGIN,
            y=0,
            width=600,
            height=40,
        )
        button = ttk.Button(
            self.file_frame,
            text=_("Save to file"),
            command=self.on_file_save_button_press,
        )
        button.pack(side="left", padx=5, pady=5)

        button_image = ttk.Button(
            self.file_frame,
            text=_("Image Scaler"),
            command=self.on_file_image_scaler_button_press,
        )
        button_image.pack(side="left", padx=5, pady=5)

        button_image = ttk.Button(
            self.file_frame,
            text=_("GIF Scaler"),
            command=self.on_file_gif_scaler_button_press,
        )
        button_image.pack(side="left", padx=5, pady=5)

        button_open_theme_dir = ttk.Button(
            self.file_frame,
            text=_("Theme Dir"),
            command=self.on_file_open_theme_dir_button_press,
        )
        button_open_theme_dir.pack(side="left", padx=5, pady=5)

    def on_file_save_button_press(self):
        self.logger.info("Start Save THEME_DATA_EDIT To File")
        config.save_to_file(config.THEME_DATA_EDIT)

    def on_file_image_scaler_button_press(self):
        if self.image_scaler_process != None:
            if self.image_scaler_process.poll() == None:
                messagebox.showerror("Error", "image scaler tool is running !")
                return
        self.image_scaler_process = utils.run.image_scaler_tool()

    def on_file_gif_scaler_button_press(self):
        if self.image_scaler_process != None:
            if self.image_scaler_process.poll() == None:
                messagebox.showerror("Error", "gif scaler tool is running !")
                return
        self.image_scaler_process = utils.run.image_gif2png_scaler_tool()

    def on_file_open_theme_dir_button_press(self):
        dir_path = config.CURRENT_THEME_PATH
        if dir_path.exists():
            if platform.system() == "Windows":  
                os.startfile(str(dir_path))  
            elif platform.system() == "Darwin":  # macOS  
                os.system(f'open "{dir_path}"')  
            else:  # Linux  
                os.system(f'xdg-open "{dir_path}"')

    def logger_frame_init(self):
        self.logger_frame = tkinter.Frame(self.main)
        self.logger_frame.place(
            x=self.RGB_LED_MARGIN,
            y=self.image_height + 3 * self.RGB_LED_MARGIN + 40,
            width=self.image_width + 2 * self.RGB_LED_MARGIN,
            height=100,
        )
        self.log_text = scrolledtext.ScrolledText(
            self.logger_frame, wrap=tkinter.WORD, state="disabled"
        )
        self.log_text.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)

        def clear_log():
            self.log_text.config(state="normal")  # 允许修改文本
            self.log_text.delete(1.0, tkinter.END)
            self.log_text.config(state="disabled")

        popup_menu = tkinter.Menu(self.logger_frame, tearoff=0)
        popup_menu.add_command(label=_("Clear log"), command=clear_log)

        def show_popup(event):
            try:
                # 尝试获取当前选中的文本区域（如果没有选中的话，则为None）
                text_widget = event.widget
                popup_menu.tk_popup(event.x_root, event.y_root)
            finally:
                # 确保菜单在点击其他位置时消失
                popup_menu.grab_release()

        self.log_text.bind("<Button-3>", show_popup)

        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("normal", foreground="black" if not self.theme_is_dark else "white")

        self.logger_normal_message("Start System Monitor Theme Editor")

    def logger_normal_message(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(
            tkinter.END, f"{time.strftime('%H:%M:%S')}> {message}\n", "normal"
        )
        self.log_text.config(state="disabled")
        self.log_text.yview(tkinter.END)

    def logger_error_message(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(
            tkinter.END, f"{time.strftime('%H:%M:%S')}> {message}\n", "error"
        )
        self.log_text.config(state="disabled")
        self.log_text.yview(tkinter.END)

    def theme_init(self):
        self.theme = tkinter.Frame(self.main)
        self.theme_tree = ttk.Treeview(self.theme, show="tree")
        self.theme_tree.pack(side="left", fill=tkinter.BOTH, expand=True)
        # self.theme_tree.bind("<Double-1>", self.on_theme_tree_item_double_click)
        self.theme_tree.bind(
            "<Button-3>",
            lambda e, f=self.theme: self.on_theme_tree_item_right_click(
                event=e, frame=f
            ),
        )
        self.theme_tree.bind("<<TreeviewSelect>>", self.on_theme_tree_select)
        vsb = ttk.Scrollbar(
            self.theme, orient="vertical", command=self.theme_tree.yview
        )
        vsb.pack(side="right", fill=tkinter.Y, expand=False)
        self.theme_tree.configure(yscrollcommand=vsb.set)

        self.theme_tree_root_node = self.theme_tree.insert(
            "", "end", text=self.theme_file
        )

        order = ["author", "display", "static_images", "static_text", "dynamic_images", "dynamic_texts", "photo_album", "requests_get", "media_get", "STATS", "PATH"]
        sorted_d = dict_tools.sort_dict_by_order(config.THEME_DATA_EDIT, order)
        import copy

        config.THEME_DATA_EDIT = copy.deepcopy(sorted_d)

        self.theme_tree_add_data(self.theme_tree_root_node, config.THEME_DATA_EDIT)
        self.theme_tree.item(self.theme_tree_root_node, open=True)

        self.theme.place(
            x=self.image_width + 3 * self.RGB_LED_MARGIN,
            y=28 + self.RGB_LED_MARGIN,
            width=600,
            height=self.image_height
            + 2 * self.RGB_LED_MARGIN
            - 50
            - (28 + self.RGB_LED_MARGIN),
        )

    def theme_tree_add_data(self, node, data):
        for index, key in enumerate(data):
            iid = f"{node}-{index}"  # 生成唯一的iid
            children_data = data[key]
            if isinstance(children_data, dict):
                children_node = self.theme_tree.insert(node, "end", iid=iid, text=key)
                self.theme_tree_add_data(children_node, children_data)
            elif isinstance(children_data, str):
                self.theme_tree.insert(
                    node, "end", iid=iid, text=key + ": " + children_data
                )
            else:
                self.theme_tree.insert(
                    node, "end", iid=iid, text=key + ": " + str(children_data)
                )

    def theme_tree_get_item_id_split_length(self, item_id):
        length = len(item_id.split("-"))
        return length

    def theme_tree_item_get_setting_config_value(self, item_id):
        item_id_split = item_id.split("-")
        config_theme = item_id_split[0]
        config_data = config.THEME_DATA_EDIT
        config_value = ""
        length = len(item_id_split) - 1
        for i, path in enumerate(item_id_split[1:]):
            config_theme = config_theme + "-" + path
            config_id = self.theme_tree.item(config_theme, "text").split(": ")[0]
            if i == length - 1:
                break
            else:
                config_value = config_data[config_id]
                if isinstance(config_value, dict):
                    config_data = config_value
        try:
            return config.THEME_SETTING[config_id]
        except:
            return None

    def theme_tree_item_get_config_value(self, config_data, item_id):
        item_id_split = item_id.split("-")
        config_theme = item_id_split[0]
        config_value = ""
        for path in item_id_split[1:]:
            config_theme = config_theme + "-" + path
            config_id = self.theme_tree.item(config_theme, "text").split(": ")[0]
            config_value = config_data[config_id]
            if isinstance(config_value, dict):
                config_data = config_value
        return config_value

    def theme_tree_item_get_config_dict(self, config_data, item_id):
        item_id_split = item_id.split("-")
        config_theme = item_id_split[0]
        config_value = ""
        length = len(item_id_split) - 1
        config_key = None
        for i, path in enumerate(item_id_split[1:]):
            config_theme = config_theme + "-" + path
            config_key = self.theme_tree.item(config_theme, "text").split(": ")[0]
            if i == length - 1:
                break
            else:
                config_value = config_data[config_key]
                if isinstance(config_value, dict):
                    config_data = config_value
                else:
                    return None
        try:
            if length:
                return config_data[config_key]
            else:
                return config_data
        except:
            return None

    def theme_tree_item_get_config_last_dict(self, config_data, item_id):
        item_id_split = item_id.split("-")
        config_theme = item_id_split[0]
        config_value = ""
        length = len(item_id_split) - 1
        if length == 1:
            return config_data
        config_key = None
        for i, path in enumerate(item_id_split[1:]):
            config_theme = config_theme + "-" + path
            config_key = self.theme_tree.item(config_theme, "text").split(": ")[0]

            if i == length - 2:
                break
            else:
                config_value = config_data[config_key]
                if isinstance(config_value, dict):
                    config_data = config_value
                else:
                    return None
        try:
            if length:
                return config_data[config_key]
            else:
                return config_data
        except:
            return None

    def theme_tree_item_set_config_value(self, config_data, item_id, value):
        item_id_split = item_id.split("-")
        config_theme = item_id_split[0]
        config_value = ""
        length = len(item_id_split) - 1
        for i, path in enumerate(item_id_split[1:]):
            config_theme = config_theme + "-" + path
            config_id = self.theme_tree.item(config_theme, "text").split(": ")[0]
            if i == length - 1:
                config_data[config_id] = value
            else:
                config_value = config_data[config_id]
                if isinstance(config_value, dict):
                    config_data = config_value

    def theme_tree_item_delete_config_value(self, config_data, item_id):
        item_id_split = item_id.split("-")
        config_theme = item_id_split[0]
        config_value = ""
        length = len(item_id_split) - 1
        for i, path in enumerate(item_id_split[1:]):
            config_theme = config_theme + "-" + path
            config_id = self.theme_tree.item(config_theme, "text").split(": ")[0]
            if i == length - 1:
                del config_data[config_id]
            else:
                config_value = config_data[config_id]
                if isinstance(config_value, dict):
                    config_data = config_value

    def on_theme_tree_delete_item(self):
        # 获取被右键点击的项的iid
        selection = self.theme_tree.selection()[0]
        if selection:
            selection_s = selection.split("-")
            # 不删除主节点
            if len(selection_s) > 1:
                # 删除选中的项
                self.theme_tree_item_delete_config_value(
                    config.THEME_DATA_EDIT, selection
                )
                # 删除所有节点
                children = self.theme_tree.get_children("")
                for child in children:
                    self.theme_tree.delete(child)
                self.theme_tree_root_node = self.theme_tree.insert(
                    "", "end", text=self.theme_file
                )
                self.theme_tree_add_data(
                    self.theme_tree_root_node, config.THEME_DATA_EDIT
                )
                # 重新打开节点
                selection_s[0] = self.theme_tree_root_node
                node = selection_s[0]
                self.theme_tree.item(node, open=True)
                for i in selection_s[1:-1]:
                    node = node + "-" + i
                    print(node)
                    self.theme_tree.item(node, open=True)
                self.theme_refresh = True

    def on_theme_tree_add_item(self, config_dict, item_key, item_value):
        config_dict[item_key] = item_value
        print("add item")
        selection = self.theme_tree.selection()[0]
        if selection:
            print('reopen node')
            selection_s = selection.split("-")
            # 删除所有节点
            children = self.theme_tree.get_children("")
            for child in children:
                self.theme_tree.delete(child)
            self.theme_tree_root_node = self.theme_tree.insert(
                "", "end", text=self.theme_file
            )
            # 重新排序
            order = ["author", "display", "static_images", "static_text", "dynamic_images", "dynamic_texts", "photo_album", "requests_get", "media_get", "STATS", "PATH"]

            if item_key in order and len(selection_s) == 1:
                print('reorder theme data edit')
                sorted_d = dict_tools.sort_dict_by_order(config.THEME_DATA_EDIT, order)
                config.THEME_DATA_EDIT = copy.deepcopy(sorted_d)
            self.theme_tree_add_data(self.theme_tree_root_node, config.THEME_DATA_EDIT)
            # 重新打开节点
            selection_s[0] = self.theme_tree_root_node
            node = selection_s[0]
            try:
                self.theme_tree.item(node, open=True)
                for i in selection_s[1:]:
                    node = node + "-" + i
                    self.theme_tree.item(node, open=True)
                self.theme_tree.selection_set(node)
                self.theme_tree.see(node)
            except:
                print("reopen error")
            self.theme_refresh = True

    def on_theme_tree_item_right_click(self, event, frame):
        item = self.theme_tree.identify("item", event.x, event.y)
        if item:
            selection = self.theme_tree.selection()
            if selection:
                if selection[0] == item:
                    selection_length = self.theme_tree_get_item_id_split_length(
                        selection[0]
                    )
                    config_value = self.theme_tree_item_get_config_value(
                        config.THEME_DATA_EDIT, selection[0]
                    )
                    item_text = self.theme_tree.item(selection[0], "text")

                    self.theme_tree.focus_set()
                    popup_menu = tkinter.Menu(frame, tearoff=0)

                    if True:
                        if selection_length > 1:
                            can_add_delete = False
                            if selection_length == 2:
                                if (
                                    isinstance(config_value, dict)
                                    and item_text != "display"
                                ):
                                    can_add_delete = True
                            else:
                                can_add_delete = True

                            if can_add_delete:
                                popup_menu.add_command(
                                    label=_("Delete"),
                                    command=self.on_theme_tree_delete_item,
                                )

                        if isinstance(config_value, dict) or selection_length == 1:
                            show_add_menu = True
                            s = False
                            parent_item = self.theme_tree.parent(selection[0])
                            parent_text = None
                            if parent_item != "":
                                parent_text = self.theme_tree.item(parent_item, "text")
                                if (
                                    selection_length == 3
                                    and parent_text == "static_images"
                                ):
                                    theme_example = config.THEME_EXAMPLE[parent_text][
                                        "IMAGE_EXAMPLE"
                                    ]
                                    s = True
                                elif (
                                    selection_length == 3
                                    and parent_text == "static_text"
                                ):
                                    theme_example = config.THEME_EXAMPLE[parent_text][
                                        "TEXT_EXAMPLE"
                                    ]
                                    s = True
                                elif (
                                    selection_length == 3
                                    and parent_text == "dynamic_images"
                                ):
                                    theme_example = config.THEME_EXAMPLE[parent_text][
                                        "dynamic_x"
                                    ]
                                    s = True
                                elif (
                                    selection_length == 3
                                    and parent_text == "dynamic_texts"
                                ):
                                    theme_example = config.THEME_EXAMPLE[parent_text][
                                        "dynamic_x"
                                    ]
                                    s = True
                                elif (
                                    selection_length == 3
                                    and parent_text == "requests_get"
                                ):
                                    if config_value.get('GET_TYPE', 'text') == 'text':
                                        theme_example = config.THEME_EXAMPLE[parent_text][
                                            "get_text_x"
                                        ]
                                    else:
                                        theme_example = config.THEME_EXAMPLE[parent_text][
                                            "get_image_x"
                                        ]
                                    s = True
                            if s == False:
                                theme_example = self.theme_tree_item_get_config_dict(
                                    config.THEME_EXAMPLE, selection[0]
                                )
                            # print(item_text,selection_length,selection[0],self.theme_tree.parent(selection[0]))
                            if theme_example != None:

                                theme_example_keys = theme_example.keys()

                                theme_edit = self.theme_tree_item_get_config_dict(
                                    config.THEME_DATA_EDIT, selection[0]
                                )
                                theme_edit_keys = theme_edit.keys()

                                for key in theme_example_keys:
                                    if key not in theme_edit_keys:
                                        if selection_length >= 2:
                                            item_value = copy.deepcopy(theme_example[key])
                                        elif selection_length == 1 and key != "STATS":
                                            item_value = copy.deepcopy(theme_example[key])
                                        else:
                                            item_value = dict()

                                        if show_add_menu:
                                            show_add_menu = False
                                            add_menu = tkinter.Menu(
                                                popup_menu, tearoff=0
                                            )
                                            popup_menu.add_cascade(
                                                label=_("Add"), menu=add_menu
                                            )

                                        add_menu.add_command(
                                            label=key,
                                            command=lambda c=theme_edit, k=key, i=item_value: self.on_theme_tree_add_item(
                                                config_dict=c, item_key=k, item_value=i
                                            ),
                                        )
                    try:
                        popup_menu.tk_popup(event.x_root, event.y_root)
                    finally:
                        popup_menu.grab_release()

    def on_theme_tree_select(self, event):
        self.editor_refresh()

    def editor_init(self):
        self.editor = tkinter.Frame(self.main)
        self.editor_set_free()
        self.theme_tree_selection = None
        self.theme_tree_selection_last = None

    def editor_set_free(self,text_show = None):
        self.editor.destroy()
        self.editor = tkinter.Frame(self.main)

        label_top = tkinter.Label(
            self.editor, text=_("Waiting selection"), font=("Arial", 12, "bold")
        )
        label_top.grid(row=0, column=0, columnspan=10, sticky="w", padx=5, pady=5)

        if text_show != None:
            label_tips = ttk.Label(self.editor, text="",foreground="#00a6ff")
            label_tips["text"] = text_show
            label_tips.grid(row=1, column=0, columnspan=10, sticky="w", padx=10, pady=5)

        self.editor.place(
            x=self.image_width + 3 * self.RGB_LED_MARGIN,
            y=self.image_height + 2 * self.RGB_LED_MARGIN - 50 + 100,
            width=600,
            height=100,
        )

    def editor_display(self, selection, title, value):
        # Destroy the old editor frame
        self.editor.destroy()

        # Create a new editor frame
        self.editor = tkinter.Frame(self.main)
        self.editor.place(
            x=self.image_width + 3 * self.RGB_LED_MARGIN,
            y=self.image_height + 2 * self.RGB_LED_MARGIN + 50,
            width=600,
            height=100
        )

        # Create a title label
        title_label = ttk.Label(
            self.editor, text=_(title) + _(" Editor"), font=("Arial", 12, "bold")
        )
        title_label.place(x=5, y=5)

        # Create a tips label
        tips_label = ttk.Label(self.editor, text="")
        tips_label["text"] = _("Please input")
        tips_label.place(x=5, y=30)

        # Define the position of input controls
        setting_x = 5
        setting_y = 60
        confirm_x = 475
        confirm_y = 58

        setting_value = None
        is_color_chooser = False
        is_combobox = False

        # Get standard settings
        try:
            setting_value = self.theme_tree_item_get_setting_config_value(selection)
        except Exception as e:
            # Log detailed error information
            self.logger.debug(f"No Found Setting Value: {e}")

        from ruamel.yaml.comments import CommentedMap
        # Check if there are standard settings
        if setting_value and isinstance(setting_value, (dict, CommentedMap)):
            print("standard settings")
            # Prepare combobox options
            combobox_list = list(setting_value.values())
            combobox_select = combobox_list.index(value) if value in combobox_list else 0

            # Create a combobox
            combobox = ttk.Combobox(self.editor, state="readonly" if title != "FORMAT" else None)
            combobox["value"] = combobox_list
            combobox.current(combobox_select)
            combobox.place(x=setting_x, y=setting_y, width=465)

            # Update tips information
            tips_label["text"] = _("Please Select")

            def on_confirm(event=None):
                print("standard settings combobox confirm")
                new_value = combobox.get()
                if new_value != value:
                    self._update_config_and_refresh(selection, title, new_value)

            combobox.bind("<<ComboboxSelected>>", on_confirm)
            # Create a confirm button
            confirm_button = ttk.Button(
                self.editor, text=_("Confirm"), command=on_confirm
            )
            confirm_button.place(x=confirm_x, y=confirm_y)
        else:
            print("unstandard settings")
            if isinstance(value, bool):
                print("Value is bool")
                # Create a checkbox
                bool_var = tkinter.BooleanVar()
                bool_var.set(value)
                check_button = ttk.Checkbutton(
                    self.editor, text=title, variable=bool_var
                )
                check_button.place(x=setting_x, y=setting_y)
            elif isinstance(value, int):
                print("Value is int")
                # Create an entry box
                entry = utils.EnhancedEntry(self.editor,label_text=self.entry_label_text,restrict_digit=True)
                # entry.bind("<Key>", restrict_entry)
                entry.place(x=setting_x, y=setting_y, width=465)
                entry.insert(0, str(value))
                entry.focus_set()
            elif isinstance(value, str):
                print("Value is str")
                if title == "FONT":
                    tips_label["text"] = _("Select the font in the fonts_dir/")
                    is_combobox = True
                    res_list = file_tools.list_res_fonts()
                elif title in ("PATH", "BACKGROUND_IMAGE"):
                    tips_label["text"] = _("Select the picture in ") + str(config.THEME_DATA_EDIT["PATH"])
                    is_combobox = True
                    res_list = file_tools.list_theme_pic()
                elif title.endswith("COLOR") or title == "DISPLAY_RGB_LED":
                    tips_label["text"] = _("Select the color you like")
                    is_color_chooser = True
                else:
                    is_color_chooser = False
                    is_combobox = False

                if is_combobox:
                    # Prepare combobox options
                    combobox_list = res_list
                    combobox_select = combobox_list.index(value) if value in combobox_list else 0

                    # Create a combobox
                    combobox = ttk.Combobox(self.editor, state="readonly")
                    combobox["value"] = combobox_list
                    combobox.current(combobox_select)
                    combobox.place(x=setting_x, y=setting_y, width=465)
                elif is_color_chooser:
                    # Parse color value
                    color_values = [int(x) for x in value.split(", ")]
                    color = "#{:02x}{:02x}{:02x}".format(*color_values)

                    def on_canvas_click(event, init_color):
                        new_color = colorchooser.askcolor(initialcolor=init_color)
                        if new_color and new_color[0]:
                            new_value = "{:0d}, {:0d}, {:0d}".format(*new_color[0])
                            self._update_config_and_refresh(selection, title, new_value)

                    # Create a color selection canvas
                    canvas = tkinter.Canvas(self.editor, width=75, height=25)
                    canvas.delete("all")
                    canvas.create_rectangle(2, 2, 75, 25, fill=color, outline="black")
                    canvas.place(x=setting_x, y=setting_y)
                    canvas.bind("<Button-1>", lambda e, c=color: on_canvas_click(e, c))
                else:
                    # Create an entry box
                    entry = utils.EnhancedEntry(self.editor,label_text=self.entry_label_text)
                    entry.place(x=setting_x, y=setting_y, width=465)
                    entry.insert(0, value)
                    entry.focus_set()

            if not is_color_chooser:
                def on_confirm(event=None):
                    print_str = ''
                    if isinstance(value, str):
                        new_value = combobox.get() if is_combobox else entry.get()
                        print_str = "unstandard settings str confirm"
                    elif isinstance(value, bool):
                        new_value = bool_var.get()
                        print_str = "unstandard settings bool confirm"
                    elif isinstance(value, int):
                        if entry.get() == '':
                            return
                        else:
                            new_value = int(entry.get())
                        print_str = "unstandard settings int confirm"

                    if new_value != value:
                        print(print_str)
                        self._update_config_and_refresh(selection, title, new_value)

                if isinstance(value, bool):
                    check_button["command"] = on_confirm
                else:
                    if 'entry' in locals():
                        try:
                            entry.bind("<Return>", on_confirm)
                            entry.bind("<FocusOut>", on_confirm)
                        except NameError:
                            print("entry NameError")
                            pass
                    elif 'combobox' in locals():
                        try:
                            combobox.bind("<<ComboboxSelected>>", on_confirm)
                        except NameError:
                            print("combobox NameError")
                            pass

                    # Create a confirm button
                    confirm_button = ttk.Button(
                        self.editor, text=_("Confirm"), command=on_confirm
                    )
                    confirm_button.place(x=confirm_x, y=confirm_y)

    def _update_config_and_refresh(self, selection, title, new_value):
        # Update configuration data
        self.theme_tree_item_set_config_value(
            config.THEME_DATA_EDIT, selection, new_value
        )
        # Update tree item
        self.theme_tree.item(selection, text=title + ": " + str(new_value))
        # Redisplay the editor
        self.editor_display(selection, title, new_value)
        # Mark the theme for refresh
        self.theme_refresh = True

    def editor_display_dict(self, selection, title):
        self.editor.destroy()

        self.editor = tkinter.Frame(self.main)
        self.editor.place(
            x=self.image_width + 3 * self.RGB_LED_MARGIN,
            y=self.image_height + 2 * self.RGB_LED_MARGIN - 50 + 100,
            width=600,
            height=100,
        )

        label = ttk.Label(
            self.editor, text=_("Name Editor"), font=("Arial", 12, "bold")
        )
        label.grid(row=0, column=0, columnspan=10, sticky="w", padx=5, pady=5)

        entry = utils.EnhancedEntry(self.editor,label_text=self.entry_label_text,restrict_alnum=True, width=25)
        entry.grid(row=1, column=0, columnspan=10, sticky="w" + "e", padx=5, pady=5)
        entry.insert(0, title)
        entry.focus_set()

        def on_confirm(event=None):
            selcection_value = dict(
                self.theme_tree_item_get_config_dict(config.THEME_DATA_EDIT, selection)
            )
            selcection_up_value = self.theme_tree_item_get_config_last_dict(
                config.THEME_DATA_EDIT, selection
            )
            if entry.get() not in selcection_up_value.keys():
                self.theme_tree_item_delete_config_value(
                    config.THEME_DATA_EDIT, selection
                )

                self.on_theme_tree_add_item(
                    selcection_up_value, entry.get(), selcection_value
                )
                self.theme_refresh = True
            else:
                if title != entry.get():
                    self.logger.error(f"{entry.get()} already exists")
                    self.logger_error_message(f"{entry.get()} already exists")

        entry.bind("<Return>", on_confirm)
        entry.bind("<FocusOut>", on_confirm)
        
        confirm_button = ttk.Button(self.editor, text=_("Confirm"), command=on_confirm)
        confirm_button.grid(row=1, column=11, columnspan=1, sticky="w" + "e")

    def editor_refresh(self):
        selection = self.theme_tree.selection()
        if selection:
            self.theme_tree_selection = selection[0]
            if self.theme_tree_selection != self.theme_tree_selection_last:
                self.theme_tree_selection_last = self.theme_tree_selection
                length = self.theme_tree_get_item_id_split_length(
                    self.theme_tree_selection
                )
                if length > 1:
                    config_value = self.theme_tree_item_get_config_value(
                        config.THEME_DATA_EDIT, self.theme_tree_selection
                    )
                    selection_item_text = self.theme_tree.item(
                        self.theme_tree_selection, "text"
                    )
                    if not isinstance(config_value, dict):
                        
                        title = selection_item_text.split(": ")[0]

                        if length == 2 and title == "PATH":
                            self.editor_set_free()
                        else:
                            self.editor_display(
                                self.theme_tree_selection,
                                title,
                                config_value,
                            )
                    else:
                        parent_item = self.theme_tree.parent(self.theme_tree_selection)
                        if parent_item != "":
                            parent_text = self.theme_tree.item(parent_item, "text")
                            if length == 3 and (
                                parent_text == "static_images"
                                or parent_text == "static_text"
                                or parent_text == "dynamic_images"
                                or parent_text == "dynamic_texts"
                                or parent_text == "requests_get"
                            ):
                                self.editor_display_dict(
                                    self.theme_tree_selection, selection_item_text
                                )
                            else:
                                tip_show = _(selection_item_text) + '\n'
                                if selection_item_text == "photo_album":
                                    tip_show = tip_show + _("You need to create a new folder called Photos \nand place your pictures in it.")
                                elif selection_item_text == "dynamic_images":
                                    tip_show = tip_show + _("If you want to add more image,\nchange the dynamic_x name first")
                                elif selection_item_text == "dynamic_texts":
                                    tip_show = tip_show + _("If you want to add more text,\nchange the dynamic_x name first")
                                elif selection_item_text == "static_text":
                                    tip_show = tip_show + _("If you want to add more text,\nchange the TEXT_EXAMPLE name first")
                                elif selection_item_text == "static_images":
                                    tip_show = tip_show + _("If you want to add more image,\nchange the IMAGE_EXAMPLE name first")
                                elif selection_item_text == "requests_get":
                                    tip_show = tip_show + _("If you want to add more requests_get,\nchange the get_xx name first")
                                self.editor_set_free(tip_show)
                        else:
                            self.editor_set_free()
                else:
                    self.editor_set_free()
        else:
            self.theme_tree_selection_last = None
            self.editor_set_free()

    def main_resize(self):
        if display.lcd.get_width() < display.lcd.get_height():
            self.image_width = 320
            self.image_height = 480
        elif display.lcd.get_width() > display.lcd.get_height():
            self.image_width = 480
            self.image_height = 320
        else:
            self.image_width = 320
            self.image_height = 320

        self.main.geometry(
            str(self.image_width + 3 * self.RGB_LED_MARGIN + 600)
            + "x"
            + str(self.image_height + 4 * self.RGB_LED_MARGIN + 40 + 100)
        )

        self.viewer.place(
            x=0,
            y=0,
            width=self.image_width + 2 * self.RGB_LED_MARGIN,
            height=self.image_height + 2 * self.RGB_LED_MARGIN + 40,
        )

        self.viewer_picture.place(x=self.RGB_LED_MARGIN + (self.image_width-display.lcd.get_width())/2, y=self.RGB_LED_MARGIN + (self.image_height-display.lcd.get_height())/2)

        self.label_coord.place(
            x=0,
            y=self.image_height + 2 * self.RGB_LED_MARGIN,
            width=self.image_width + 2 * self.RGB_LED_MARGIN,
        )

        self.label_info.place(
            x=0,
            y=self.image_height + 2 * self.RGB_LED_MARGIN + 20,
            width=self.image_width + 2 * self.RGB_LED_MARGIN,
        )

        self.theme.place(
            x=self.image_width + 3 * self.RGB_LED_MARGIN,
            y=28 + self.RGB_LED_MARGIN,
            width=600,
            height=self.image_height
            + 2 * self.RGB_LED_MARGIN
            - 50
            - (28 + self.RGB_LED_MARGIN)
            + 100,
        )

        self.editor.place(
            x=self.image_width + 3 * self.RGB_LED_MARGIN,
            y=self.image_height + 2 * self.RGB_LED_MARGIN - 50 + 100,
            width=600,
            height=100,
        )

        self.file_frame.place(
            x=self.image_width + 3 * self.RGB_LED_MARGIN,
            y=0,
            width=600,
            height=40,
        )

        self.logger_frame.place(
            x=self.RGB_LED_MARGIN,
            y=self.image_height + 3 * self.RGB_LED_MARGIN + 40,
            width=self.image_width + 2 * self.RGB_LED_MARGIN,
            height=100,
        )

    def main_refresh(self):
        if (
            os.path.exists(self.theme_file)
            and os.path.getmtime(self.theme_file) > self.last_edit_time
        ):
            self.theme_file_change = True
            self.main_refresh_tick = 0
            # Update the preview.png that is in the theme folder
            if self.theme_refresh != True or not self.theme_preview_path.exists():
                print("update preview")
                display.lcd.screen_image.save(self.theme_preview_path)
        else:
            self.theme_file_change = False

        self.refresh_theme()
        self.main_refresh_tick = self.main_refresh_tick + 1

        if self.theme_file_change == True or self.theme_refresh == True:

            if self.theme_refresh == True:
                log = "The preview window will refresh"
                self.theme_file_unsave = True
            else:
                log = "The theme file has been updated, the preview window will refresh"
                self.theme_file_unsave = False
                self.theme.destroy()
                self.theme_init()

            self.logger.debug(log)

            self.logger_normal_message(log)

            self.main_resize()

            self.last_edit_time = os.path.getmtime(self.theme_file)

            # Display new picture
            self.display_image = ImageTk.PhotoImage(display.lcd.screen_image)
            self.viewer_picture.config(image=self.display_image)

            # Refresh RGB backplate LEDs color
            self.led_color = config.THEME_DATA["display"].get(
                "DISPLAY_RGB_LED", (255, 255, 255)
            )
            if isinstance(self.led_color, str):
                self.led_color = tuple(map(int, self.led_color.split(", ")))
            self.viewer.configure(bg="#%02x%02x%02x" % self.led_color)
            self.label_zone.configure(
                bg="#%02x%02x%02x" % tuple(map(lambda x: 255 - x, self.led_color))
            )

            self.theme_refresh = False

        # Regularly update the viewer window even if content unchanged
        self.main.after(100, self.main_refresh)

    def refresh_theme(self):
        need_refresh = False
        if self.theme_refresh == True:
            config.load_edit(config.THEME_DATA_EDIT)
            need_refresh = True
        elif self.theme_file_change == True:
            config.load_theme()
            config.load_theme_edit()
            need_refresh = True

        import traceback

        error_text = ""
        try:
            import lib.dynamic_images as dynamic_images
            import lib.dynamic_texts as dynamic_texts
            import lib.photo_album as photo_album
            import lib.requests_get as requests_get
            import lib.media_get as media_get

            if need_refresh == True:
                error_text = "initialize_display"
                # Initialize the display
                display.initialize_display()
                error_text = "display_static_images"
                # Create all static images
                display.lcd.image_cache = {}
                display.display_static_images()
                error_text = "display_static_text"
                # Create all static texts
                display.display_static_text()

                # Display all data on screen once
                import lib.stats as stats

                if config.THEME_DATA["STATS"]["CPU"]["PERCENTAGE"].get("INTERVAL", 0) > 0:
                    error_text = "CPU percentage"
                    stats.CPU.percentage(True)
                if config.THEME_DATA["STATS"]["CPU"]["POWER"].get("INTERVAL", 0) > 0:
                    error_text = "CPU power"
                    stats.CPU.power(True)
                if config.THEME_DATA["STATS"]["CPU"]["FREQUENCY"].get("INTERVAL", 0) > 0:
                    error_text = "CPU frequency"
                    stats.CPU.frequency(True)
                if config.THEME_DATA["STATS"]["CPU"]["LOAD"].get("INTERVAL", 0) > 0:
                    error_text = "CPU load"
                    stats.CPU.load()
                if config.THEME_DATA["STATS"]["CPU"]["TEMPERATURE"].get("INTERVAL", 0) > 0:
                    error_text = "CPU temperature"
                    stats.CPU.temperature(True)
                if config.THEME_DATA["STATS"]["CPU"]["FAN_SPEED"].get("INTERVAL", 0) > 0:
                    error_text = "CPU fan_speed"
                    stats.CPU.fan_speed(True)
                if config.THEME_DATA["STATS"]["GPU"].get("INTERVAL", 0) > 0:
                    error_text = "Gpu stats"
                    stats.Gpu.stats(True)
                if config.THEME_DATA["STATS"]["MEMORY"].get("INTERVAL", 0) > 0:
                    error_text = "Memory stats"
                    stats.Memory.stats(True)
                if config.THEME_DATA["STATS"]["DISK"].get("INTERVAL", 0) > 0:
                    error_text = "Disk stats"
                    stats.Disk.stats(True)
                if config.THEME_DATA["STATS"]["NET"].get("INTERVAL", 0) > 0:
                    error_text = "Net stats"
                    stats.Net.stats()
                if config.THEME_DATA["STATS"]["DATE"].get("INTERVAL", 0) > 0:
                    error_text = "Date stats"
                    stats.Date.stats(True)
                if config.THEME_DATA["STATS"]["UPTIME"].get("INTERVAL", 0) > 0:
                    error_text = "SystemUptime stats"
                    stats.SystemUptime.stats()
                if config.THEME_DATA["STATS"]["CUSTOM"].get("INTERVAL", 0) > 0:
                    error_text = "Custom stats"
                    stats.Custom.stats()
                if config.THEME_DATA["STATS"]["VOLUME"].get("INTERVAL", 0) > 0:
                    error_text = "Volume stats"
                    stats.Volume.stats(True)
                if (config.THEME_DATA["STATS"]["LCD_SENSOR"]["TEMPERATURE"].get("INTERVAL", 0) > 0):
                    error_text = "LcdSensor temperature"
                    stats.LcdSensor.temperature(True)
                if (
                    config.THEME_DATA["STATS"]["LCD_SENSOR"]["HUMIDNESS"].get("INTERVAL", 0)
                    > 0
                ):
                    error_text = "LcdSensor humidness"
                    stats.LcdSensor.humidness(True)
                if config.THEME_DATA['STATS']['WEATHER'].get("INTERVAL", 0) > 0:
                    error_text = "Weather stats"
                    stats.Weather.stats()
                if config.THEME_DATA['STATS']['PING'].get("INTERVAL", 0) > 0:
                    error_text = "Ping stats"
                    stats.Ping.stats()
                if config.THEME_DATA['STATS']['INPUT_MONITOR'].get("INTERVAL", 0) > 0:
                    error_text = "Input monitor stats"
                    stats.InputMonitor.stats(True)

                error_text = "dynamic_images"
                dynamic_images.dynamic_images.init()
                error_text = "dynamic_texts"
                dynamic_texts.dynamic_texts.init()
                error_text = "photo_album"
                photo_album.photo_album.init()
                error_text = "requests_get"
                if config.THEME_DATA['requests_get'].get("SHOW", False) == True:
                    requests_get.requests_get.init()
                error_text = "media_get"
                media_get.media_get.init()

            need_refresh_img = False
            
            if dynamic_images.dynamic_images.handle():
                need_refresh_img = True
            if dynamic_texts.dynamic_texts.handle():
                need_refresh_img = True
            if config.THEME_DATA["photo_album"].get("INTERVAL", 0) > 0:
                if self.main_refresh_tick % (config.THEME_DATA["photo_album"].get("INTERVAL", 0) * 10) == 0:
                    if photo_album.photo_album.handle():
                        need_refresh_img = True
            if config.THEME_DATA['requests_get'].get("SHOW", False) == True:
                if requests_get.requests_get.get(True):
                    need_refresh_img = True
            
            if config.THEME_DATA.get("media_get", None):
                if self.main_refresh_tick % 10 == 0:
                    error_text = "media_get"
                    if media_get.media_get.handle(True):
                        need_refresh_img = True 
            
            if need_refresh_img == True:
                self.display_image = ImageTk.PhotoImage(display.lcd.screen_image)
                self.viewer_picture.config(image=self.display_image)
        except AssertionError as e:
            self.logger_error_message(error_text + ": " + str(e))
            traceback.print_exc()
        except Exception as e:
            self.logger_error_message(error_text + ": " + str(e))
            traceback.print_exc()

    def on_closing(self):
        if self.theme_file_unsave == False:
            self.logger.debug("Exit Theme Editor...")
            try:
                sys.exit(0)
            except:
                os._exit(0)
        else:
            self.close_theme_frame = tkinter.Toplevel(self.main)
            self.close_theme_frame.title(_("Confirm"))
            self.close_theme_frame.withdraw()

            def on_close_theme_frame_closing():
                self.close_theme_frame.grab_release()
                self.close_theme_frame.destroy()

            self.close_theme_frame.protocol(
                "WM_DELETE_WINDOW", on_close_theme_frame_closing
            )
            self.close_theme_frame.resizable(False, False)
            self.close_theme_frame.grab_set()

            self.delete_theme_label = ttk.Label(
                self.close_theme_frame, text=_("Do you need to save it?")
            )
            self.delete_theme_label.grid(
                row=0, column=0, columnspan=3, sticky="w", padx=5, pady=5
            )

            def on_close_theme_frame_no():
                self.close_theme_frame.grab_release()
                self.close_theme_frame.destroy()
                self.logger.debug("Exit Theme Editor...")
                try:
                    sys.exit(0)
                except:
                    os._exit(0)

            cancel_button = ttk.Button(
                self.close_theme_frame,
                text=_("Cancel"),
                command=on_close_theme_frame_closing,
            )
            cancel_button.grid(row=1, column=2, pady=5, padx=5)

            no_button = ttk.Button(
                self.close_theme_frame, text=_("NO"), command=on_close_theme_frame_no
            )
            no_button.grid(row=1, column=1, pady=5, padx=5)

            def on_close_theme_frame_ok():
                self.on_file_save_button_press()
                self.main_refresh()
                self.close_theme_frame.grab_release()
                self.close_theme_frame.destroy()
                self.logger.debug("Exit Theme Editor...")
                try:
                    sys.exit(0)
                except:
                    os._exit(0)

            ok_button = ttk.Button(
                self.close_theme_frame, text=_("OK"), command=on_close_theme_frame_ok
            )
            ok_button.grid(row=1, column=0, pady=5, padx=5)

            self.close_theme_frame.update()
            main_window_x = self.main.winfo_x()
            main_window_y = self.main.winfo_y()
            main_window_width = self.main.winfo_width()
            main_window_height = self.main.winfo_height()
            width = self.close_theme_frame.winfo_width()
            height = self.close_theme_frame.winfo_height()
            x = main_window_x + (main_window_width // 2) - (width // 2)
            y = main_window_y + (main_window_height // 2) - (height // 2)
            self.close_theme_frame.geometry(f"{width}x{height}+{x}+{y}")
            self.close_theme_frame.deiconify()

            self.close_theme_frame.focus_force()

            utils.apply_theme_to_titlebar(self.close_theme_frame,self.theme_is_dark)

    def draw_zone(self, x0, y0, x1, y1):
        x_err = (self.image_width - display.lcd.get_width())/2
        y_err = (self.image_height - display.lcd.get_height())/2

        x = min(self.x0, x1)
        y = min(self.y0, y1)
        width = max(self.x0, x1) - min(x0, x1) + 1
        height = max(self.y0, y1) - min(y0, y1) + 1
        if width > 0 and height > 0:
            self.label_zone.place(
                x=x + self.RGB_LED_MARGIN + x_err,
                y=y + self.RGB_LED_MARGIN + y_err,
                width=width,
                height=height,
            )
        else:
            self.label_zone.place_forget()

    def on_button1_press(self, event):
        self.x0, self.y0 = event.x, event.y
        self.label_zone.place_forget()

    def on_button1_press_and_drag(self, event):
        x1, y1 = event.x, event.y

        # Do not draw zone outside of theme preview
        if x1 < 0:
            x1 = 0
        elif x1 >= display.lcd.get_width():
            x1 = display.lcd.get_width() - 1
        if y1 < 0:
            y1 = 0
        elif y1 >= display.lcd.get_height():
            y1 = display.lcd.get_height() - 1

        self.label_coord.config(
            text=_("Drawing zone from [{},{}] to [{},{}]").format(
                self.x0, self.y0, x1, y1
            )
        )

        self.draw_zone(self.x0, self.y0, x1, y1)

    def on_button1_release(self, event):
        x1, y1 = event.x, event.y
        if x1 != self.x0 or y1 != self.y0:
            # Do not draw zone outside of theme preview
            if x1 < 0:
                x1 = 0
            elif x1 >= display.lcd.get_width():
                x1 = display.lcd.get_width() - 1
            if y1 < 0:
                y1 = 0
            elif y1 >= display.lcd.get_height():
                y1 = display.lcd.get_height() - 1

            # Display drawn zone and coordinates
            self.draw_zone(self.x0, self.y0, x1, y1)

            # Display relative zone coordinates, to set in theme
            x = min(self.x0, x1)
            y = min(self.y0, y1)
            width = max(self.x0, x1) - min(self.x0, x1)
            height = max(self.y0, y1) - min(self.y0, y1)
            self.label_coord.config(
                text=_("Zone: X={}, Y={}, width={} height={}").format(
                    x, y, width, height
                )
            )
        else:
            # Display click coordinates
            self.label_coord.config(
                text=("X={}, Y={}" + " (R,G,B)={}").format(
                    self.x0,
                    self.y0,
                    display.lcd.screen_image.getpixel((self.x0, self.y0)),
                )
            )

    def on_zone_click(self, event):
        self.label_zone.place_forget()

if __name__ == "__main__":
    # Loading Language
    from lib.utils import set_language
    _ = set_language(executable_name)
    try:
        te = theme_editor()
    except Exception as e:
        import traceback
        traceback.print_exc()
        messagebox.showerror(
            _("Error"), _("An error occurred while starting the Theme Editor.")
        )
        try:
            sys.exit(0)
        except:
            os._exit(0)