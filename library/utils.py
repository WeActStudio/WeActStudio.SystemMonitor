import os
import sys
import requests,datetime
import subprocess
from pathlib import Path
import threading
import platform
import time
try:
    import tkinter as tk
    import tkinter.ttk as ttk
    import psutil
    import ping3
except:
    print("[ERROR] Python dependencies not installed.")
    try:
        sys.exit(0)
    except:
        os._exit(0)

def apply_theme_to_titlebar(root,is_dark):
    if platform.system() != "Windows":
        return
    
    import pywinstyles, sys
    version = sys.getwindowsversion()

    if version.major == 10 and version.build >= 22000:
        # Set the title bar color to the background color on Windows 11 for better appearance
        if is_dark:
            pywinstyles.change_header_color(root, "#1c1c1c")
    elif version.major == 10:
        if is_dark:
            pywinstyles.apply_style(root, "dark")

            # A hacky way to update the title bar's color on Windows 10 (it doesn't update instantly like on Windows 11)
            root.wm_attributes("-alpha", 0.99)
            root.wm_attributes("-alpha", 1)

def show_messagebox(message, title="", delay=3000):
    def create_and_run_messagebox():
        nonlocal root
        root = tk.Tk()
        root.title(title)

        style = ttk.Style()
        style = ttk.Style()

        theme_is_dark = False
        if platform.system() == "Windows" and sys.getwindowsversion().major >= 10:
            import darkdetect
            theme_is_dark = darkdetect.theme() == "Dark"
            if theme_is_dark:
                root.tk.call("source", Path(__file__).parent.parent / "res" / "tk_themes" / "sv_ttk" / "theme" / "dark.tcl")
                style.theme_use("sun-valley-dark")
            else:
                root.tk.call("source", Path(__file__).parent.parent / "res" / "tk_themes" / "sv_ttk" / "theme" / "light.tcl")
                style.theme_use("sun-valley-light")
        else:
            root.tk.call("source", Path(__file__).parent.parent / "res" / "tk_themes" / "sv_ttk" / "theme" / "light.tcl")
            style.theme_use("sun-valley-light")

        root.resizable(False, False)
        root.attributes('-topmost', True)
        root.attributes("-toolwindow", True)

        label = tk.Label(root, text=message, anchor="w")
        label.grid(row=1, column=0, padx=5, pady=10, sticky="w")
        
        # Center the window on the screen
        root.withdraw()
        apply_theme_to_titlebar(root,theme_is_dark)
        root.update_idletasks()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        main_window_width = root.winfo_reqwidth() if root.winfo_reqwidth() > 250 else 250
        main_window_height = root.winfo_reqheight()
        x = (screen_width - main_window_width) // 2
        y = (screen_height - main_window_height) // 2
        root.geometry(f"{main_window_width}x{main_window_height}+{x}+{y}")
        root.deiconify()

        apply_theme_to_titlebar(root,theme_is_dark)

        if delay > 0:
            root.after(delay, root.destroy)

        root.mainloop()

    root = None
    messagebox_thread = threading.Thread(target=create_and_run_messagebox)
    messagebox_thread.start()

    while root is None:
        pass

    def close_messagebox():
        if root and root.winfo_exists():
            print("Closing message box...") 
            root.after(0, root.destroy)

    return close_messagebox

def app_is_running(lockfile):
    if not os.path.exists(lockfile):
        return False
        
    try:
        with open(lockfile) as f:
            pid = int(f.read().strip())
            
        p = psutil.Process(pid)
        process_path = Path(p.exe()).parent
        expected_path = Path(__file__).resolve().parent.parent / "Python"
        cmdline = p.cmdline()
        lockfile_name = Path(lockfile).stem
        if cmdline and len(cmdline) > 1 and lockfile_name in cmdline[1] and process_path.samefile(expected_path) and p.is_running():
            print("Process is running")
            return True
            
    except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    try:
        os.remove(lockfile)
    except OSError:
        pass
        
    return False

def app_set_running(lockfile):
    with open(lockfile, 'w') as f:  
        f.write(str(os.getpid()))

def app_end_running(lockfile):
    os.remove(lockfile)

LANGUAGE_MAPPING = {
    "Chinese": "zh",
    "Chinese (Simplified)": "zh",
    "English": "en",
    "Japanese": "ja",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Russian": "ru",
    "Portuguese": "pt",
    "Italian": "it",
    "Korean": "ko",
    "Arabic": "ar",
    "Hindi": "hi",
    "Turkish": "tr",
    "Dutch": "nl",
    "Swedish": "sv",
    "Polish": "pl",
    "Thai": "th",
    "Vietnamese": "vi",
    "Greek": "el",
    "Czech": "cs",
    "Danish": "da",
    "Finnish": "fi",
    "Hebrew": "he",
    "Hungarian": "hu",
    "Indonesian": "id",
    "Norwegian": "no",
    "Romanian": "ro",
    "Slovak": "sk",
    "Ukrainian": "uk"
}

def get_language_code(language_name: str) -> str:
    return LANGUAGE_MAPPING.get(language_name, "Unknown")

import locale, gettext
from library.utils import get_language_code

def set_language(file_path):
    lang, encoding = locale.getlocale()
    lang = lang.split("_")
    _file_name = os.path.basename(file_path)
    file_name = os.path.splitext(_file_name)[0]
    print(f"Language: {lang[0]}, Country: {lang[1]}, Encoding: {encoding}")
    lang_set = get_language_code(lang[0])
    localedir = os.path.join(os.path.dirname(file_path), f"res\\language\\{file_name}")
    available_languages = []
    if os.path.exists(localedir):
        for item in os.listdir(localedir):
            if os.path.isdir(os.path.join(localedir, item)):
                available_languages.append(item)
    if lang_set in available_languages:
        print(f"Use language: {lang_set}")
        language = lang_set
        domain = lang_set
    else:
        print(f"No found language: {lang[0]}, use the default language: English")
        language = "en"
        domain = "en"
    lang_translation = gettext.translation(domain, localedir, languages=[language], fallback=True)
    lang_translation.install(domain)
    return lang_translation.gettext

TEMPERATURE_UNIT_MAP = {"metric": "metric - °C", "imperial": "imperial - °F", "standard": "standard - °K"}

WEATHER_LANG_MAP = {"sq": "Albanian", "af": "Afrikaans", "ar": "Arabic", "az": "Azerbaijani", "eu": "Basque",
                    "be": "Belarusian", "bg": "Bulgarian", "ca": "Catalan", "zh_cn": "Chinese Simplified",
                    "zh_tw": "Chinese Traditional", "hr": "Croatian", "cz": "Czech", "da": "Danish", "nl": "Dutch",
                    "en": "English", "fi": "Finnish", "fr": "French", "gl": "Galician", "de": "German", "el": "Greek",
                    "he": "Hebrew", "hi": "Hindi", "hu": "Hungarian", "is": "Icelandic", "id": "Indonesian",
                    "it": "Italian", "ja": "Japanese", "kr": "Korean", "ku": "Kurmanji (Kurdish)", "la": "Latvian",
                    "lt": "Lithuanian", "mk": "Macedonian", "no": "Norwegian", "fa": "Persian (Farsi)", "pl": "Polish",
                    "pt": "Portuguese", "pt_br": "Português Brasil", "ro": "Romanian", "ru": "Russian", "sr": "Serbian",
                    "sk": "Slovak", "sl": "Slovenian", "sp": "Spanish", "sv": "Swedish", "th": "Thai", "tr": "Turkish",
                    "ua": "Ukrainian", "vi": "Vietnamese", "zu": "Zulu"}

def get_weather(lat, lon, api_key, units, lang):
    WEATHER_UNITS = {'metric': '°C', 'imperial': '°F', 'standard': '°K'}
    url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units={units}&lang={lang}'
    desc = ''
    result = False
    deg = WEATHER_UNITS.get(units, '°?')
    temp = f"{0}{deg}"
    feel = f"({0}{deg})"
    humidity = f"{0}%"
    now = datetime.datetime.now()
    time = f"@{now.hour:02d}:{now.minute:02d}"
    if api_key:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                temp = f"{data['main']['temp']:.1f}{deg}"
                feel = f"({data['main']['feels_like']:.1f}{deg})"
                desc = data['weather'][0]['description'].capitalize()
                humidity = f"{data['main']['humidity']:.0f}%"
                result = True
            else:
                print(f"Error {response.status_code} fetching OpenWeatherMap API:")
                desc = response.json().get('message')
        except Exception as e:
            print(f"Error fetching OpenWeatherMap API: {str(e)}")
            desc = "Error fetching OpenWeatherMap API"
    else:
        print("No OpenWeatherMap API key provided in config.yaml")
        desc = "No OpenWeatherMap API key"
    return temp, feel, desc, humidity, time, result

def get_ping_delay(host):
    delay = ping3.ping(host)
    if delay is not False:
        return delay
    else:
        return -1
    
class run:
    python_name = 'WeActStudioSystemMonitor'
    current_file = Path(__file__).resolve()
    parent_dir = current_file.parent
    grandparent_dir = parent_dir.parent

    @classmethod
    def get_executable_name(cls):
        if sys.platform == 'win32':
            exec_name = f"{cls.python_name}_w.exe"
        else:
            exec_name = cls.python_name
        python_cmd = cls.grandparent_dir / "Python" / exec_name
        if not python_cmd.exists():
            print(f"[Info] {python_cmd} not found. Using python.exe")
            python_cmd = cls.grandparent_dir / "Python" / "python.exe"
        return python_cmd
        
    @classmethod
    def main(cls):
        exec_name = cls.get_executable_name()
        main_py = cls.grandparent_dir / "main.py"
        return subprocess.Popen([exec_name, str(main_py)], shell=True)

    @classmethod
    def configure(cls):
        exec_name = cls.get_executable_name()
        configure_py = cls.grandparent_dir / "configure.py"
        return subprocess.Popen([exec_name, str(configure_py)], shell=True)
    
    @classmethod
    def weact_device_setting(cls,type=0):
        exec_name = cls.get_executable_name()
        weact_device_setting_py = cls.grandparent_dir / "weact_device_setting.py"
        return subprocess.Popen([exec_name, str(weact_device_setting_py),f"{type}"], shell=True)
    
    @classmethod
    def theme_editor(cls,theme_name):
        exec_name = cls.get_executable_name()
        theme_editor_py = cls.grandparent_dir / "theme-editor.py"
        return subprocess.Popen([exec_name, str(theme_editor_py),f"\"{theme_name}\""], shell=True)
    
    @classmethod
    def image_scaler_tool(cls):
        exec_name = cls.get_executable_name()
        image_scaler_tool_py = cls.grandparent_dir / "image_scaler_tool.py"
        return subprocess.Popen([exec_name, str(image_scaler_tool_py)], shell=True)
    
    @classmethod
    def image_gif2png_scaler_tool(cls):
        exec_name = cls.get_executable_name()
        image_gif2png_scaler_tool_py = cls.grandparent_dir / "image_gif2png_scaler_tool.py"
        return subprocess.Popen([exec_name, str(image_gif2png_scaler_tool_py)], shell=True)
    
def get_version():
    version_file = Path(__file__).parent.parent / "version"
    try:
        with open(version_file, 'r') as f:
            version = f.read().strip()
            return version
    except Exception as e:
        print(f"Error reading version file: {e}")
        return "V0.0.0"

def WindowToast(title, message, icon=None):
    import platform, sys
    if platform.system() == "Windows" and sys.getwindowsversion().major >= 10 and sys.version_info >= (3, 9):
        from windows_toasts import Toast, WindowsToaster,ToastDisplayImage
        toaster = WindowsToaster(title)
        # Initialise the toast
        newToast = Toast()
        # Set the body of the notification
        newToast.text_fields = [message]
        if icon:
            newToast.AddImage(ToastDisplayImage.fromPath(icon))
        toaster.show_toast(newToast)
        def close():
            toaster.remove_toast(newToast)
        
        return close
    else:
        return None
    
from pynput import mouse, keyboard
class InputMonitor:
    """
    A class to monitor keyboard and mouse activities with automatic resource cleanup.
    Tracks key presses and mouse movements.
    """
    def __init__(self):
        """Initialize counters and flags"""
        self.key_press_count = 0
        self.mouse_press_count = 0
        self.mouse_moved = False
        self.key_pressed = False
        self._running = False
        self._listeners = []
        
    def _on_move(self, x, y):
        """Callback for mouse movement"""
        self.mouse_moved = True
        
    def _on_click(self, x, y, button, pressed):
        """Callback for mouse click"""
        if pressed:
            self.mouse_press_count += 1
            
    def _on_press(self, key):
        """Callback for keyboard press"""
        self.key_press_count += 1
        self.key_pressed = True
        
    def start(self):
        """Start monitoring input events"""
        if not self._running:
            self._running = True
            # Start mouse listener
            mouse_listener = mouse.Listener(
                on_move=self._on_move,
                on_click=self._on_click
            )
            mouse_listener.daemon = True
            mouse_listener.start()
            self._listeners.append(mouse_listener)
            
            # Start keyboard listener
            keyboard_listener = keyboard.Listener(
                on_press=self._on_press
            )
            keyboard_listener.daemon = True
            keyboard_listener.start()
            self._listeners.append(keyboard_listener)
            
    def stop(self):
        """Stop all listeners and cleanup resources"""
        for listener in self._listeners:
            if listener.is_alive():
                listener.stop()
                time.sleep(0.1)
                listener.join(timeout=0.5)
        self._listeners.clear()
        self._running = False
                
    def get_key_press_count(self):
        """Get total key press count"""
        return self.key_press_count
    
    def get_mouse_press_count(self):
        """Get total key press count"""
        return self.mouse_press_count
    
    def is_key_pressed(self):
        """Check if any key has been pressed since last call"""
        pressed = self.key_pressed
        self.key_pressed = False  # Reset flag after checking
        return pressed

    def is_mouse_moved(self):
        """Check if mouse has moved since last call"""
        moved = self.mouse_moved
        self.mouse_moved = False  # Reset movement flag
        return moved
    
    def reset_key_counters(self):
        """Reset key counters to zero"""
        self.key_press_count = 0
        self.key_pressed = False
        
    def reset_mouse_counters(self):
        """Reset mouse counters to zero"""
        self.mouse_press_count = 0
        self.mouse_moved = False
        
    def __enter__(self):
        """Context manager entry point"""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point - ensures cleanup"""
        self.stop()

class EnhancedEntry(ttk.Entry):
    def __init__(self, master=None,restrict_alnum=False,restrict_digit=False, label_text=None,**kwargs):
        super().__init__(master, **kwargs)
        self._undo_stack = []
        self._redo_stack = []
        self.label_text = label_text
        if self.label_text == None:
            self.label_text = {}
            self.label_text['Copy'] = 'Copy'
            self.label_text['Paste'] = 'Paste'
            self.label_text['Cut'] = 'Cut'
            self.label_text['Undo'] = 'Undo'
            self.label_text['Redo'] = 'Redo'
        self._setup_context_menu()
        self.bind('<Control-z>', self.undo)
        self.bind('<Control-x>', self.cut)
        self.bind('<Control-c>', self.copy)
        self.bind('<Control-v>', self.paste)
        self.bind('<Control-y>', self.redo)
        self.bind('<Control-a>', self.select_all)
        self.bind('<Key>', self._record_change)
        self._restrict_alnum = restrict_alnum
        self._restrict_digit = restrict_digit

    def _setup_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label=self.label_text['Copy'], command=self.copy)
        self.context_menu.add_command(label=self.label_text['Paste'], command=self.paste)
        self.context_menu.add_command(label=self.label_text['Cut'], command=self.cut)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=self.label_text['Undo'], command=self.undo)
        self.context_menu.add_command(label=self.label_text['Redo'], command=self.redo)
        self.bind('<Button-3>', self._show_context_menu)

    def _show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def _record_change(self, event):
        if event.state != 8:
            return
        if event.keysym not in ('Control_L', 'Control_R', 'Shift_L', 'Shift_R', 
                              'Alt_L', 'Alt_R', 'Left', 'Right', 'Up', 'Down',
                              'Home', 'End', 'Page_Up', 'Page_Down'):
            if event.keysym not in ('Delete','BackSpace'):
                if self._restrict_alnum:
                    if not event.char.isalnum() and event.char not in ('_', '-', ' '):
                        return 'break'
                if self._restrict_digit:
                    cursor_index = event.widget.index(tk.INSERT)
                    if (cursor_index == 0 and event.char == "-") or event.char.isdigit():
                        return
                    else:
                        return 'break'

            current_text = self.get()
            if not self._undo_stack or self._undo_stack[-1] != current_text:
                self._undo_stack.append(current_text)
                self._redo_stack.clear()

    def set_restrict_alnum(self, restrict):
        self._restrict_alnum = restrict

    def set_restrict_digit(self, restrict):
        self._restrict_digit = restrict

    def copy(self, event=None):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.selection_get())
        except tk.TclError:
            pass
        return 'break'

    def paste(self, event=None):
        try:
            if self.selection_present():
                self.delete(tk.SEL_FIRST, tk.SEL_LAST)
            
            if not self._undo_stack or self._undo_stack[-1] != self.get():
                self._undo_stack.append(self.get())
                self._redo_stack.clear()
                
            self.insert(tk.INSERT, self.clipboard_get())
        except tk.TclError:
            pass
        return 'break'

    def cut(self, event=None):
        if self.selection_present():
            self._undo_stack.append(self.get())
            self._redo_stack.clear()
            self.copy()
            self.delete(tk.SEL_FIRST, tk.SEL_LAST)
        return 'break'

    def undo(self, event=None):
        if self._undo_stack:
            self._redo_stack.append(self.get())
            self.delete(0, tk.END)
            self.insert(0, self._undo_stack.pop())

    def redo(self, event=None):
        if self._redo_stack:
            self._undo_stack.append(self.get())
            self.delete(0, tk.END)
            self.insert(0, self._redo_stack.pop())

    def select_all(self, event=None):
        self.selection_range(0, tk.END)
        self.icursor(tk.END)
        return 'break'
