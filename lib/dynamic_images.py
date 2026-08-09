import lib.config as config
from lib.display import display

class dynamic_images:
    theme_data = []
    theme_data_ok = False
    id_now = 0
    id_min = 255
    background_image = ''
    background_color = ''
    show = False
    time_now = 0
    time_out = 0
    first_image_dict = None
    @classmethod
    def init(cls):
        cls.id_min = 255
        cls.id_now = 0
        cls.time_now = 0
        cls.time_out = 0
        if config.THEME_DATA.get('dynamic_images', False):
            cls.theme_data = config.THEME_DATA['dynamic_images']
            cls.background_image = config.get_theme_file_path(cls.theme_data.get("BACKGROUND_IMAGE", None))
            cls.background_color = cls.theme_data.get("BACKGROUND_COLOR", (0, 0, 0))
            cls.show = cls.theme_data.get("SHOW", False)
            if cls.show != False:
                cls.theme_data_ok = True
                for image in cls.theme_data:
                    if isinstance(cls.theme_data[image],dict):
                        id = cls.theme_data[image].get("ID", -1)
                        if id >= 0:
                            if id < cls.id_min:
                                cls.id_min = id
                cls.id_now = cls.id_min
                return
        cls.theme_data_ok = False

    @classmethod
    def handle(cls):
        refresh = False
        if cls.theme_data_ok:
            cls.time_now = cls.time_now + 1
            if cls.time_now >= cls.time_out:
                cls.time_now = 0

                if config.update_queue.qsize() > 50:
                    print(f"serial queue overload: {config.update_queue.qsize()}")
                    return refresh
                
                find_id = False
                image_dict = ''
                for image in cls.theme_data:
                    if isinstance(cls.theme_data[image],dict):
                        id_t = cls.theme_data[image].get("ID", -1)
                        if id_t == cls.id_now:
                            image_dict = image
                            cls.time_out = cls.theme_data[image_dict].get("INTERVAL_100mS", 10)
                            if cls.id_now == cls.id_min:
                                cls.first_image_dict = image_dict
                            cls.id_now = cls.id_now + 1
                            if cls.id_now > 255:
                                cls.id_now = cls.id_min
                            find_id = True
                            break

                if find_id == False:
                    if cls.first_image_dict == None:
                        return refresh
                    image_dict = cls.first_image_dict
                    cls.time_out = cls.theme_data[image_dict].get("INTERVAL_100mS", 10)
                    cls.id_now = cls.id_min + 1
                    
                display.lcd.DisplayImage(
                    x=cls.theme_data[image_dict].get("X", 0),
                    y=cls.theme_data[image_dict].get("Y", 0),
                    width=cls.theme_data[image_dict].get("WIDTH", 0),
                    height=cls.theme_data[image_dict].get("HEIGHT", 0),
                    image=config.get_theme_file_path(cls.theme_data[image_dict].get("PATH", None)),
                    background_color=cls.background_color,
                    background_image=cls.background_image)
                
                refresh = True

        return refresh