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

import os
import queue
import sys
from pathlib import Path
# import yaml
import ruamel.yaml
from lib.log import logger
from lib import utils
import traceback


def load_yaml(configfile):
    yaml = ruamel.yaml.YAML()
    with open(configfile, "rt", encoding='utf8') as stream:
        yamlconfig = yaml.load(stream)
        return yamlconfig

THEMES_DIR = None
FONTS_DIR = None
CONFIG_DIR = None

CONFIG_DATA = None
THEME_DEFAULT = None
THEME_SETTING = None
THEME_EXAMPLE = None
THEME_DATA = None
THEME_DATA_EDIT = None

CURRENT_THEME_PATH = None

def load_config(configfile_path):
    global CONFIG_DATA,THEMES_DIR,FONTS_DIR,CONFIG_DIR
    global THEME_DEFAULT,THEME_SETTING,THEME_EXAMPLE
    try:
        CONFIG_DATA = load_yaml(configfile_path)

        CONFIG_DIR = Path(CONFIG_DATA['config']['CONFIG_DIR'])
        THEMES_DIR = Path(CONFIG_DATA['config']['THEMES_DIR'])
        FONTS_DIR =  Path(CONFIG_DATA['config']['FONTS_DIR'])
        
        THEME_DEFAULT = load_yaml(CONFIG_DIR / "default.yaml")
        THEME_SETTING = load_yaml(CONFIG_DIR / "theme_setting.yaml")
        THEME_EXAMPLE = load_yaml(CONFIG_DIR / "theme_example.yaml")
        
        logger.info("THEMES_DIR: %s" % str(THEMES_DIR))
        logger.info("FONTS_DIR: %s" % str(FONTS_DIR))
    except Exception as e:
        traceback.print_exc()
        logger.error('Load config:'+ str(e))
        try:
            sys.exit(0)
        except:
            os._exit(0)

def copy_default(default, theme):
    """recursively supply default values into a dict of dicts of dicts ...."""
    for k, v in default.items():
        if k not in theme:
            theme[k] = v
        if isinstance(v, dict):
            if k not in theme:
                theme[k] = {}
            copy_default(v, theme[k])

def load_theme_edit():
    global THEME_DATA_EDIT
    try:
        theme_path = THEMES_DIR / CONFIG_DATA['config']['THEME']
        logger.info("Loading edit theme %s from %s" % (CONFIG_DATA['config']['THEME'], theme_path / "theme.yaml"))
        THEME_DATA_EDIT = load_yaml(theme_path / "theme.yaml")
        THEME_DATA_EDIT['PATH'] = Path(CONFIG_DATA['config']['THEME'])
        THEME_SETTING['PATH'] = None
    except Exception as e:
        logger.error('Load edit theme: ' + str(e))
        try:
            sys.exit(0)
        except:
            os._exit(0)

def load_theme():
    global THEME_DATA,CURRENT_THEME_PATH
    try:
        theme_path = THEMES_DIR / CONFIG_DATA['config']['THEME']
        logger.info("Loading theme %s from %s" % (CONFIG_DATA['config']['THEME'], theme_path / "theme.yaml"))
        THEME_DATA = load_yaml(theme_path / "theme.yaml")
        THEME_DATA['PATH'] = Path(CONFIG_DATA['config']['THEME'])
        CURRENT_THEME_PATH = theme_path
    except Exception as e:
        logger.error('Load theme: ' + str(e))
        try:
            sys.exit(0)
        except:
            os._exit(0)
    copy_default(THEME_DEFAULT, THEME_DATA)

def load_edit(edit):
    global THEME_DATA
    import copy
    THEME_DATA = copy.deepcopy(edit)
    copy_default(THEME_DEFAULT, THEME_DATA)

def save_to_file(edit):
    theme_path = THEMES_DIR / CONFIG_DATA['config']['THEME']
    yaml_path = theme_path / 'theme.yaml'
    import copy
    save = copy.deepcopy(edit)
    del save['PATH']
    yaml = ruamel.yaml.YAML()
    with open(yaml_path, 'w' ,encoding='utf-8') as file:  
        yaml.dump(save, file)

def check_theme_compatible(display_size: str):
    global THEME_DATA
    # Check if theme is compatible with hardware revision
    if display_size != THEME_DATA['display'].get("DISPLAY_SIZE", '320x480'):
        logger.error("The selected theme " + CONFIG_DATA['config'][
            'THEME'] + " is not compatible with your display revision " + CONFIG_DATA["display"]["REVISION"])
        try:
            sys.exit(0)
        except:
            os._exit(0)

def get_theme_file_path(name):
    global CURRENT_THEME_PATH
    if name:
        return CURRENT_THEME_PATH / name
    else:
        return None

def get_font_path(name):
    global FONTS_DIR
    if name:
        return FONTS_DIR / name
    else:
        return Path(__file__).parent.parent / "res" / "fonts" / "roboto-mono" / "RobotoMono-Regular.ttf"


# # Load config on import
# load_config()
# # Load theme edit on import
# load_theme_edit()
# # Load theme on import
# load_theme()

# Queue containing the serial requests to send to the screen
update_queue = queue.Queue()