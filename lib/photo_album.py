import os
import lib.config as config
from lib.display import display
import random 
from pathlib import Path
from lib.log import logger

def list_theme_pic():
    # List to store the paths of picture files
    pic = []
    # Define the allowed picture file extensions
    valid_extensions = ('.png', '.jpg', '.bmp')
    # Convert the configuration paths to Path objects
    theme_path = Path(config.CURRENT_THEME_PATH)
    # Traverse all files and folders under the theme path
    for root, _, files in os.walk(theme_path):
        root_path = Path(root)
        # Check if it is a 'Photos' folder
        if 'Photos' in root_path.parts:
            for file in files:
                # Convert the file name to lowercase
                file_l = file.lower()
                # Check if the file extension is an allowed picture extension
                if file_l.endswith(valid_extensions):
                    # Construct the relative path of the file
                    relative_path = root_path.relative_to(theme_path) / file
                    # Get the full path of the theme file
                    pic_path = config.get_theme_file_path(str(relative_path))
                    # Add the picture path to the list
                    pic.append(pic_path)
    return pic

class photo_album:
    theme_data = []
    theme_data_ok = False
    background_image = ''
    background_color = ''
    show = False
    show_sequential = True
    x = 0
    y = 0
    align = ''
    max_width = 0
    max_height = 0
    auto_refresh = False
    interval = 3
    theme_pic_list = []
    theme_pic_id = 0
    first_run = True
    @classmethod
    def init(cls):
        cls.show = False
        cls.theme_data_ok = False
        cls.theme_pic_id = 0
        cls.show_sequential = True
        cls.align = 'left'
        cls.auto_refresh = False
        cls.first_run = True
        if config.THEME_DATA.get('photo_album', False):
            cls.theme_data = config.THEME_DATA['photo_album']
            cls.show = cls.theme_data.get("SHOW", False)
            if cls.show == True:
                cls.background_image = config.get_theme_file_path(cls.theme_data.get("BACKGROUND_IMAGE", None))
                cls.background_color = cls.theme_data.get("BACKGROUND_COLOR", (0, 0, 0))
                cls.show_sequential = not cls.theme_data.get("SHOW_RANDOM", False)
                cls.interval = cls.theme_data.get("INTERVAL", 3)
                cls.x = cls.theme_data.get("X", 0)
                cls.y = cls.theme_data.get("Y", 0)
                cls.align = cls.theme_data.get("ALIGN",'left')
                cls.max_width = cls.theme_data.get("MAX_WIDTH", 0)
                cls.max_height = cls.theme_data.get("MAX_HEIGHT", 0)
                if cls.max_width == 0:
                    cls.max_width = display.lcd.get_width()
                if cls.max_height == 0:
                    cls.max_height = display.lcd.get_height()
                cls.auto_refresh = cls.theme_data.get("AUTO_REFRESH", False)
                cls.theme_pic_list = list_theme_pic()
                cls.theme_data_ok = True
                logger.info("photo_album init ok")
                return
        cls.theme_data_ok = False

    @classmethod
    def handle(cls):
        refresh = False
        if cls.theme_data_ok:

            if config.update_queue.qsize() > 50 and cls.first_run == False:
                print(f"serial queue overload: {config.update_queue.qsize()}")
                return refresh
            else:
                cls.first_run = False
                
            if cls.auto_refresh == True:
                cls.theme_pic_list = list_theme_pic()

            if  len(cls.theme_pic_list) == 0:
                cls.theme_pic_id = 0
                return refresh
            
            if cls.show_sequential == True:
                pic_path = cls.theme_pic_list[cls.theme_pic_id]
                cls.theme_pic_id = cls.theme_pic_id + 1
                if cls.theme_pic_id > len(cls.theme_pic_list) - 1:
                    cls.theme_pic_id = 0
            else:
                pic_path= random.choice(cls.theme_pic_list)

            display.lcd.DisplayImage2(
                    x=cls.x,
                    y=cls.y,
                    max_width=cls.max_width,
                    max_height=cls.max_height,
                    image=pic_path,
                    align=cls.align,
                    background_color=cls.background_color,
                    background_image=cls.background_image)
            refresh = True

        return refresh