import library.config as config
from library.display import display
import requests
import re
import threading,time
from io import BytesIO
import traceback
from library.log import logger
from queue import Queue

class requests_get:
    requests_theme_data = {}
    theme_data_ok = False
    last_request_time = {}
    thread_running = False
    theme_value = {}
    error = ''
    queue = Queue()
    @classmethod
    def init(cls):
        cls.theme_data_ok = False
        cls.requests_theme_data = config.THEME_DATA.get('requests_get', False)
        if cls.requests_theme_data != False:
            if cls.requests_theme_data.get('SHOW', False) == True:
                for key in cls.requests_theme_data:
                    cls.last_request_time[key] = 0
                cls.theme_data_ok = True
                logger.info('requests_get init ok')
                if cls.thread_running == False:
                    cls.thread_running = True
                    cls.thread = threading.Thread(target=cls.run,daemon=True)
                    cls.thread.start()
            
    @classmethod
    def run(cls):
        logger.info('requests_get run now')
        while True:
            theme_value = cls.queue.get()
            try:
                type = theme_value.get('GET_TYPE', '')
                url = theme_value.get('URL', '')
                args1 = theme_value.get('ARGS1', '')
                args2 = theme_value.get('ARGS2', '')
                return_value_set = theme_value.get('RETURN_SETTING', '')
                params = {}
                if args1 != '':
                    for pair in args1.split(','):
                        key, args1_value = pair.split('=')
                        params[key] = args1_value
                if args2 != '':
                    for pair in args2.split(','):
                        key, args2_value = pair.split('=')
                        params[key] = args2_value
                print(params)
                headers={
                    'user-agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2882.18 Safari/537.36'
                }
                try:
                    if params != {}:
                        response = requests.get(url, params=params,timeout=10,headers=headers)
                    else:
                        response = requests.get(url,timeout=10,headers=headers)
                except Exception as e:
                    cls.error = 'get error:' + str(e)
                    continue

                response_is_image = False
                response_is_text = False
                try:
                    data = response.json(strict=False)
                    print(f'type:{type}, response data: {data}')

                except Exception as e:
                    if response.headers.get('Content-Type', '').startswith('image') and type == 'image':
                        response_is_image = True
                    else:
                        if type == 'text':
                            response_is_text = True
                            print(response.content)
                        else:
                            cls.error = 'response.json error:' + str(e)
                            continue 

                def get_value(data, path):
                    parts = path.strip().split('[')
                    current = data
                    for part in parts:
                        part = part.strip(']').strip('\'').strip('"')
                        if part.isdigit():
                            current = current[int(part)]
                        elif part:
                            current = current[part]
                    return current

                def replace_with_data(match):
                    expression = match.group(1).strip()
                    try:
                        return str(get_value(data, expression))
                    except Exception:
                        return match.group(0)

                pattern = r'{(.+?)}'
                if response.status_code == 200:
                    if type == 'text':
                        if response_is_text == False:
                            try:
                                result = re.sub(pattern, replace_with_data, return_value_set)
                                result = result.replace('\\n', '\n')
                            except Exception as e:
                                cls.error = type + ' match error:' + str(e)
                                continue
                            print('text: ' + result)
                        else:
                            result = response.content.decode('utf-8')
                        display.lcd.DisplayText(
                            text=result,
                            x=theme_value.get("X", 0),
                            y=theme_value.get("Y", 0),
                            width=theme_value.get("WIDTH", 0),
                            height=theme_value.get("HEIGHT", 0),
                            font=config.get_font_path(theme_value.get("FONT", None)),
                            font_size=theme_value.get("FONT_SIZE", 10),
                            font_color=theme_value.get("FONT_COLOR", (255, 255, 255)),
                            background_color=theme_value.get("BACKGROUND_COLOR", (0, 0, 0)),
                            background_image=config.get_theme_file_path(theme_value.get("BACKGROUND_IMAGE", None)),
                            align=theme_value.get("ALIGN", "justify"),
                            anchor=theme_value.get("ANCHOR", "lt"),
                            rotation=theme_value.get("ROTATION", 0),
                        )
                    else:
                        image_get_ok = False
                        if response_is_image == False:
                            try:
                                pic_addr = re.sub(pattern, replace_with_data, return_value_set)
                            except Exception as e:
                                cls.error = type + ' match error:' + str(e)
                                continue
                            if pic_addr != return_value_set:
                                try:
                                    # send request get image data
                                    response = requests.get(pic_addr, timeout=10)
                                    response.raise_for_status()
                                    # check response content type is image
                                    if not response.headers.get('Content-Type', '').startswith('image'):
                                        cls.error = type + ' return data not image'
                                        continue
                                    image_get_ok = True
                                except requests.exceptions.RequestException as req_e:
                                    cls.error = type + ' RequestException:' + str(req_e)
                                except ValueError as value_e:
                                    cls.error = type + ' ValueError:' + str(value_e)
                                except IOError as io_e:
                                    cls.error = type + ' IOError:' + str(io_e)
                                except Exception as e:
                                    cls.error = type + ' error:' + str(e)
                                    traceback.print_exc()
                        else:
                            image_get_ok = True
                        if image_get_ok:
                            # convert response content to image object
                            image = BytesIO(response.content)
                            # display image, assume DisplayPILImage method exists, adjust parameters as needed
                            display.lcd.DisplayImage2(
                                x=theme_value.get("X", 0),
                                y=theme_value.get("Y", 0),
                                max_width=theme_value.get("WIDTH", 0),
                                max_height=theme_value.get("HEIGHT", 0),
                                image_data=image,
                                align=theme_value.get("ALIGN", "left"),
                                background_color=theme_value.get("BACKGROUND_COLOR", (0, 0, 0)),
                                background_image=config.get_theme_file_path(theme_value.get("BACKGROUND_IMAGE", None)),
                                radius=theme_value.get("RADIUS", 0),
                                alpha=theme_value.get("ALPHA", 255),
                                overlay_display=theme_value.get("OVERLAY_BG", False),
                                )
                else:
                    cls.error = type + ' return data error:' + str(response.status_code)

            except Exception as e:
                traceback.print_exc()
                cls.error = 'error:' + str(e)

    @classmethod
    def get(cls,raise_error=False):
        refresh = False
        current_time = time.time()
        if cls.theme_data_ok:
            if cls.queue.empty(): 
                if cls.error != '':
                    error = 'requests_get:' + cls.error
                    logger.error(error)
                    cls.error = ''
                    if raise_error:
                        raise Exception(error)
                    
                for key,theme_value in cls.requests_theme_data.items():
                    if isinstance(theme_value,dict):
                        if theme_value.get("SHOW", False):
                            interval = theme_value.get('INTERVAL_100mS', 100) / 10  # 将 100ms 转换为秒
                            if current_time - cls.last_request_time[key] >= interval:
                                cls.queue.put(theme_value)
                                cls.last_request_time[key] = current_time
        
                refresh = True
        return refresh