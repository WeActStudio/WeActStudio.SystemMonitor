import os
import library.config as config
from library.display import display
from pathlib import Path
from library.log import logger

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager,
)
from winsdk.windows.storage.streams import DataReader, Buffer
import re
import io
from PIL import Image
import asyncio
import threading
import datetime

_session_manager = None
_session = None
_loop = None
_loop_thread = None

def simplify_title(title):
    if not title:
        return title
    patterns = [
        (r"\s*\([^)]+\)", ""),
        (r"\s*\[[^\]]+\]", ""),
        (
            r"\s*[-–]\s*(slowed|reverb|remix|remaster|remastered|official|official video|official audio|lyrics|extended|feat\..*|ft\..*|HD|HQ|4K).*$",
            "",
        ),
        (r"\s+\d{3,4}k$", ""),
        (r"\s*[-–]\s*$", ""),
    ]
    simplified = title
    for pattern, replacement in patterns:
        simplified = re.sub(pattern, replacement, simplified, flags=re.IGNORECASE)
    simplified = " ".join(simplified.split())
    if not simplified.strip():
        return title
    return simplified

def init_event_loop():
    """Initialize and run the event loop in a separate thread"""
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

async def get_media_info_async():
    global _session_manager, _session
    if _session_manager is None:
        try:
            _session_manager = (
                await GlobalSystemMediaTransportControlsSessionManager.request_async()
            )
        except Exception:
            _session_manager = None
    if _session_manager:
        try:
            current = _session_manager.get_current_session()
            if current:
                _session = current
        except Exception:
            _session = None
    if _session:
        info = await _session.try_get_media_properties_async()
        original_title = info.title
        simplified_title = simplify_title(original_title)
        thumbnail = None
        if info.thumbnail:
            thumbnail_stream = None
            reader = None
            try:
                thumbnail_stream = await info.thumbnail.open_read_async()
                buffer = Buffer(thumbnail_stream.size)
                await thumbnail_stream.read_async(buffer, buffer.capacity, 0)
                reader = DataReader.from_buffer(buffer)
                bytes_array = bytearray(buffer.length)
                reader.read_bytes(bytes_array)

                # thumbnail = base64.b64encode(bytes_array).decode()

                image = Image.open(io.BytesIO(bytes_array))
                png_buffer = io.BytesIO()
                png_buffer.truncate(0)
                image.save(png_buffer, format="PNG")
                image.close()
                png_buffer.seek(0)
                thumbnail = png_buffer
            except:
                thumbnail = None
            finally:
                if reader:
                    reader.close()
                if thumbnail_stream:
                    thumbnail_stream.close()
                    
        timeline_properties = _session.get_timeline_properties()
    
        info_dict = {
            "title": original_title,
            "title_simple": simplified_title,
            "artist": info.artist,
            "album": info.album_title,
            "thumbnail": thumbnail,
            "start_time": timeline_properties.start_time,
            "position": timeline_properties.position,
            "end_time": timeline_properties.end_time,
        }

        return info_dict
    return {
        "title": "None",
        "title_simple": "None",
        "artist": "None",
        "album": "None",
        "thumbnail": None,
        "start_time": datetime.timedelta(seconds=0),
        "position": datetime.timedelta(seconds=0),
        "end_time": datetime.timedelta(seconds=0),
    }

def get_media_info():
    """Wrapper to run the async function in the event loop"""
    global _loop, _loop_thread
    
    # Initialize event loop if not already running
    if _loop is None:
        _loop_thread = threading.Thread(target=init_event_loop, daemon=True)
        _loop_thread.start()
        # Wait for the loop to initialize
        while _loop is None:
            import time
            time.sleep(0.01)
    
    # Run the async function in the event loop
    try:
        return asyncio.run_coroutine_threadsafe(get_media_info_async(), _loop).result(timeout=5.0)
    except Exception as e:
        print(f"Error in get_media_info: {e}")
        return {
            "title": "None",
            "title_simple": "None",
            "artist": "None",
            "album": "None",
            "thumbnail": None,
            "start_time": datetime.timedelta(seconds=0),
            "position": datetime.timedelta(seconds=0),
            "end_time": datetime.timedelta(seconds=0),
        }

def timedelta_to_minutes_seconds(td):
    """Convert datetime.timedelta to 'MM:SS' string format"""
    total_seconds = td.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

class media_get:
    _session_manager = None
    _session = None

    theme_data = []
    tick = 0
    info = {}
    title_last = ""
    artist_last = ""
    album_last = ""
    thumbnail_retry_count = 5

    display_char_size_now = {"title": 0, "title_simple": 0, "artist": 0, "album": 0, "start_time": 0, "position": 0, "end_time": 0}
    display_char_size_last = {"title": 0, "title_simple": 0, "artist": 0, "album": 0, "start_time": 0, "position": 0, "end_time": 0}
    display_char_width_now = {"title": 0, "title_simple": 0, "artist": 0, "album": 0, "start_time": 0, "position": 0, "end_time": 0}
    display_char_width_last = {"title": 0, "title_simple": 0, "artist": 0, "album": 0, "start_time": 0, "position": 0, "end_time": 0}
    display_text_step = {"title": 0, "title_simple": 0, "artist": 0, "album": 0, "start_time": 0, "position": 0, "end_time": 0}
    display_text_value_index = {"title": 0, "title_simple": 0, "artist": 0, "album": 0, "start_time": 0, "position": 0, "end_time": 0}
    display_text_value_last = {"title": "", "title_simple": "", "artist": "", "album": "", "start_time": "", "position": "", "end_time": ""}

    thumbnail = {}
    title = {}
    title_simple = {}
    artist = {}
    album = {}
    start_time = {}
    position = {}
    end_time = {}
    progress_bar = {}

    @classmethod
    def init(cls):
        cls._session_manager = None
        cls._session = None
        cls.tick = 0
        cls.info = {}
        cls.title_last = ""
        cls.artist_last = ""
        cls.album_last = ""
        cls.thumbnail_retry_count = 5
        
        cls.display_char_size_now = {"title": 0, "title_simple": 0, "artist": 0, "album": 0, "start_time": 0, "position": 0, "end_time": 0}
        cls.display_char_size_last = {"title": 0, "title_simple": 0, "artist": 0, "album": 0, "start_time": 0, "position": 0, "end_time": 0}
        cls.display_char_width_now = {"title": 0, "title_simple": 0, "artist": 0, "album": 0, "start_time": 0, "position": 0, "end_time": 0}
        cls.display_char_width_last = {"title": 0, "title_simple": 0, "artist": 0, "album": 0, "start_time": 0, "position": 0, "end_time": 0}
        cls.display_text_step = {"title": 0, "title_simple": 0, "artist": 0, "album": 0, "start_time": 0, "position": 0, "end_time": 0}
        cls.display_text_value_index = {"title": 0, "title_simple": 0, "artist": 0, "album": 0, "start_time": 0, "position": 0, "end_time": 0}
        cls.display_text_value_last = {"title": "", "title_simple": "", "artist": "", "album": "", "start_time": "", "position": "", "end_time": ""}

        if config.THEME_DATA.get("media_get", None):
            cls.theme_data = config.THEME_DATA["media_get"]
            cls.thumbnail = cls.theme_data.get("thumbnail", {})
            cls.title = cls.theme_data.get("title", {})
            cls.title_simple = cls.theme_data.get("title_simple", {})
            cls.artist = cls.theme_data.get("artist", {})
            cls.album = cls.theme_data.get("album", {})
            cls.start_time = cls.theme_data.get("start_time", {})
            cls.position = cls.theme_data.get("position", {})
            cls.end_time = cls.theme_data.get("end_time", {})
            cls.progress_bar = cls.theme_data.get("progress_bar", {})
    
    @classmethod
    def display_text(cls, item_theme, item_name, item_value, scroll_speed=1):
        if cls.display_text_value_last.get(item_name, "") != item_value:
            cls.display_text_step[item_name] = 0
            cls.display_text_value_last[item_name] = item_value

        if cls.display_text_step[item_name] == 0:
            cls.display_char_size_now[item_name] = 0
            cls.display_text_value_index[item_name] = 0
            cls.display_text_step[item_name] = 1
        else:
            cls.display_text_value_index[item_name] = cls.display_text_value_index[item_name] + scroll_speed
            if cls.display_text_value_index[item_name] + cls.display_char_size_now[item_name] - scroll_speed >= len(item_value):
                cls.display_text_value_index[item_name] = 0

        cls.display_char_size_now[item_name], cls.display_char_width_now[item_name] = display.lcd.DisplayText2(
            text=item_value[cls.display_text_value_index[item_name]:],
            x=item_theme.get("X", 0),
            y=item_theme.get("Y", 0),
            width=item_theme.get("WIDTH", 0),
            height=item_theme.get("HEIGHT", 0),
            font=config.get_font_path(item_theme.get("FONT", None)),
            font_size=item_theme.get("FONT_SIZE", 12),
            font_color=item_theme.get("FONT_COLOR", (0, 0, 0)),
            background_color=item_theme.get("BACKGROUND_COLOR", (255, 255, 255)),
            background_image=config.get_theme_file_path(item_theme.get("BACKGROUND_IMAGE", None)),
            anchor=item_theme.get("ANCHOR", 'lt'),
            width_last= cls.display_char_width_last[item_name],
        )
        cls.display_char_width_last[item_name] = cls.display_char_width_now[item_name]

    @classmethod
    def handle(cls,is_static_show=False):
        refresh = False
        can_show_progress_bar = 0

        if not is_static_show:
            cls.info = get_media_info()
        else:
            bytes_array = bytearray()
            with open(Path(__file__).parent.parent / "res" / "backgrounds" / "music.png", "rb") as f:
                bytes_array = f.read()
            cls.info = {
            "title": "Media Get Base GSMTC",
            "title_simple": "Media Get",
            "artist": "artist: WeAct Studio",
            "album": "album: WeAct Studio",
            "thumbnail": io.BytesIO(bytes_array),
            "start_time": datetime.timedelta(seconds=0),
            "position": datetime.timedelta(seconds=35),
            "end_time": datetime.timedelta(seconds=168),
        }
        
        if cls.thumbnail.get("SHOW", False):
            if type(cls.info["thumbnail"]) == io.BytesIO:
                image_data = cls.info["thumbnail"]
            else:
                bytes_array = bytearray()
                with open(Path(__file__).parent.parent / "res" / "backgrounds" / "music.png", "rb") as f:
                    bytes_array = f.read()
                image_data = io.BytesIO(bytes_array)
                
            if cls.thumbnail_retry_count > 0:
                cls.thumbnail_retry_count -= 1

            if (cls.info["title"] != cls.title_last) or (cls.info["artist"] != cls.artist_last) or (cls.info["album"] != cls.album_last) or (cls.thumbnail_retry_count == 0):
                cls.title_last = cls.info["title"]
                cls.artist_last = cls.info["artist"]
                cls.album_last = cls.info["album"]
                cls.thumbnail_retry_count = 5
                display.lcd.DisplayImage2(
                    x=cls.thumbnail.get("X", 0),
                    y=cls.thumbnail.get("Y", 0),
                    max_width=cls.thumbnail.get("MAX_WIDTH", 0),
                    max_height=cls.thumbnail.get("MAX_HEIGHT", 0),
                    image_data=image_data,
                    align=cls.thumbnail.get("ALIGN", 'left'),
                    background_color=cls.thumbnail.get("BACKGROUND_COLOR", (0, 0, 0)),
                    background_image=config.get_theme_file_path(cls.thumbnail.get("BACKGROUND_IMAGE", None)),
                    radius=cls.thumbnail.get("RADIUS", 0),
                )
                image_data.close()
                refresh = True

        if cls.title.get("SHOW", False):
            if cls.info["title"]:
                value = cls.info["title"]
            else:
                value = "None"
            cls.display_text(cls.title, "title", value, scroll_speed=cls.title.get("SCROLL_SPEED", 1))
            refresh = True

        if cls.title_simple.get("SHOW", False):
            if cls.info["title_simple"]:
                value = cls.info["title_simple"]
            else:
                value = "None"
            cls.display_text(cls.title_simple, "title_simple", value, scroll_speed=cls.title_simple.get("SCROLL_SPEED", 1))
            refresh = True

        if cls.artist.get("SHOW", False):
            if cls.info["artist"]:
                value = cls.info["artist"]
            else:
                value = "None"
            cls.display_text(cls.artist, "artist", value, scroll_speed=cls.artist.get("SCROLL_SPEED", 1))
            refresh = True
        
        if cls.album.get("SHOW", False):
            if cls.info["album"]:
                value = cls.info["album"]
            else:
                value = "None"
            cls.display_text(cls.album, "album", value, scroll_speed=cls.album.get("SCROLL_SPEED", 1))
            refresh = True
                
        if cls.start_time.get("SHOW", False):
            if type(cls.info["start_time"]) == datetime.timedelta:
                can_show_progress_bar += 1
                cls.display_text(cls.start_time, "start_time", timedelta_to_minutes_seconds(cls.info["start_time"]))
                refresh = True

        if cls.position.get("SHOW", False):
            if type(cls.info["position"]) == datetime.timedelta:
                can_show_progress_bar += 1
                cls.display_text(cls.position, "position", timedelta_to_minutes_seconds(cls.info["position"]))
                refresh = True

        if cls.end_time.get("SHOW", False):
            if type(cls.info["end_time"]) == datetime.timedelta:
                can_show_progress_bar += 1
                cls.display_text(cls.end_time, "end_time", timedelta_to_minutes_seconds(cls.info["end_time"]))
                refresh = True
        
        if cls.progress_bar.get("SHOW", False):
            start_time_seconds = cls.info["start_time"].total_seconds()
            end_time_seconds = cls.info["end_time"].total_seconds()
            position_seconds = cls.info["position"].total_seconds()
            if end_time_seconds == start_time_seconds:
                progress_value = 0
            else:
                progress_value = int((position_seconds - start_time_seconds) / (end_time_seconds - start_time_seconds) * 100)

            display.lcd.DisplayProgressBar(
                x=cls.progress_bar.get("X", 0),
                y=cls.progress_bar.get("Y", 0),
                width=cls.progress_bar.get("WIDTH", 0),
                height=cls.progress_bar.get("HEIGHT", 0),
                value=progress_value,
                min_value=0,
                max_value=100,
                bar_color=cls.progress_bar.get("BAR_COLOR", (0, 0, 0)),
                bar_outline=cls.progress_bar.get("BAR_OUTLINE", False),
                background_color=cls.progress_bar.get("BACKGROUND_COLOR", (255, 255, 255)),
                background_image=config.get_theme_file_path(cls.progress_bar.get("BACKGROUND_IMAGE", None))
            )
            refresh = True
        return refresh
