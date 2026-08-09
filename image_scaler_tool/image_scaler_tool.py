# Copyright (C) 2024-2024  WeAct Studio
import tkinter as tk  
from tkinter import filedialog, ttk, messagebox  
from PIL import Image, ImageTk  
import os
from pathlib import Path

import sys

if getattr(sys, "frozen", False):
    executable_name = os.path.splitext(os.path.basename(sys.executable))[0]
    executable_dir = Path(sys.executable).parent
else:
    executable_name = os.path.splitext(os.path.basename(__file__))[0]
    executable_dir = Path(__file__).parent

sys.path.append(str(executable_dir.parent))

import lib.utils as utils
os.chdir(utils.get_root_dir())

class ImageScaler:  
    def __init__(self,frame=None):  
        if frame == None:
            self.frame = tk.Tk()
        else:
            self.frame = frame

        self.frame.title(_("ImageScaler Tool"))  
        self.frame.iconphoto(True, tk.PhotoImage(file=utils.get_root_dir() / "res" / "icons" / "logo.png"))
        self.frame.geometry('320x80')
        # 图片显示  
        self.label_image = ttk.Label(self.frame)  
        self.label_image.place(x=10,y=70)  
  
        # 宽度和高度输入框  
        self.width_label = ttk.Label(self.frame, text=_("Width:"))  
        self.width_label.place(x=10,y=10)  
        self.width_var = tk.StringVar()  
        self.width_entry = ttk.Entry(self.frame, textvariable=self.width_var)  
        self.width_entry.place(x=60,y=10, width=60,relwidth=0)  
  
        self.height_label = tk.Label(self.frame, text=_("Height:"))  
        self.height_label.place(x=10,y=40)  
        self.height_var = tk.StringVar()  
        self.height_entry = ttk.Entry(self.frame, textvariable=self.height_var)  
        self.height_entry.place(x=60,y=40, width=60,relwidth=0)  

        self.size_label = ttk.Label(self.frame, text="")  
        self.size_label.place(x=128,y=40,width=100,relwidth=0)

        # 打开文件按钮  
        self.open_button = ttk.Button(self.frame, text=_("Open Pic"), command=self.open_image)  
        self.open_button.place(x=220,y=8,width=80,relwidth=0)  
  
        # 缩放按钮  
        self.scale_button = ttk.Button(self.frame, text=_("Scale Pic"), command=self.apply_scale)  
        self.scale_button.place(x=128,y=8,width=80,relwidth=0)  
  
        # 保存按钮  
        self.save_button = ttk.Button(self.frame, text=_("Save Pic"), command=self.save_image)  
        self.save_button.place(x=220,y=38,width=80,relwidth=0)  
  
        # 初始时没有图片  
        self.original_image = None  
        self.scaled_image = None  # 用于保存缩放后的PIL Image对象  
        
        if frame == None:
            self.frame.mainloop()
  
    def open_image(self):  
        file_path = filedialog.askopenfilename()  
        self.frame.focus_force()
        if file_path:  
            self.original_image = Image.open(file_path)  
            self.scaled_image = self.original_image.copy()  # 初始时，缩放后的图片是原始图片的副本 
            width_set = 480
            height_set = 480
            if self.scaled_image.width > width_set:
                # 仅指定宽度，高度按比例缩放  
                ratio = width_set / self.scaled_image.width  
                height = int(self.scaled_image.height * ratio)  
                self.scaled_image = self.scaled_image.resize((width_set, height), Image.LANCZOS)  
            if self.scaled_image.height > height_set:  
                # 仅指定高度，宽度按比例缩放  
                ratio = height_set / self.scaled_image.height  
                width = int(self.scaled_image.width * ratio)  
                self.scaled_image = self.scaled_image.resize((width, height_set), Image.LANCZOS) 
            self.photo = ImageTk.PhotoImage(self.scaled_image)  
            self.label_image.config(image=self.photo)  
            self.label_image.image = self.photo  # 防止垃圾回收

            if self.scaled_image.width < 320:
                width = 295
            else:
                width = self.scaled_image.width  
            self.frame.geometry(str(width + 25) + 'x' + str(self.scaled_image.height + 80))
            self.size_label['text'] = str(self.original_image.width) + 'x' + str(self.original_image.height)
  
    def apply_scale(self):  
        width = int(self.width_var.get()) if self.width_var.get() else None  
        height = int(self.height_var.get()) if self.height_var.get() else None  
    
        if width is None and height is None:  
            messagebox.showerror(_("Error"), _("Please specify width or height."))  
            self.frame.focus_force()
            return  
    
        if width is not None and height is not None:  
            self.scaled_image = self.original_image.resize((width, height), Image.LANCZOS)  
        elif width is not None:  
            # 仅指定宽度，高度按比例缩放  
            ratio = width / self.original_image.width  
            height = int(self.original_image.height * ratio)  
            self.scaled_image = self.original_image.resize((width, height), Image.LANCZOS)  
        elif height is not None:  
            # 仅指定高度，宽度按比例缩放  
            ratio = height / self.original_image.height  
            width = int(self.original_image.width * ratio)  
            self.scaled_image = self.original_image.resize((width, height), Image.LANCZOS)  

        self.scaled_image_d= self.scaled_image.copy()  # 初始时，缩放后的图片是原始图片的副本 
        width_set = 480
        height_set = 480
        if self.scaled_image_d.width > width_set:
            # 仅指定宽度，高度按比例缩放  
            ratio = width_set / self.scaled_image_d.width  
            height = int(self.scaled_image_d.height * ratio)  
            self.scaled_image_d = self.scaled_image_d.resize((width_set, height), Image.LANCZOS)  
        if self.scaled_image_d.height > height_set:  
            # 仅指定高度，宽度按比例缩放  
            ratio = height_set / self.scaled_image_d.height  
            width = int(self.scaled_image_d.width * ratio)  
            self.scaled_image_d = self.scaled_image_d.resize((width, height_set), Image.LANCZOS) 

        self.photo = ImageTk.PhotoImage(self.scaled_image_d)  
        self.label_image.config(image=self.photo)  
        self.label_image.image = self.photo  # 防止垃圾回收  
        
        if self.scaled_image_d.width < 320:
            width = 295
        else:
            width = self.scaled_image_d.width
        self.frame.geometry(str(width + 25) + 'x' + str(self.scaled_image_d.height + 80))
        self.size_label['text'] = str(self.scaled_image.width) + 'x' + str(self.scaled_image.height)
  
    def save_image(self):  
        if self.scaled_image is None:  
            messagebox.showerror(_("Error"), _("Please open and scale the image before saving."))  
            self.frame.focus_force()
            return  
  
        save_path = filedialog.asksaveasfilename(defaultextension=".png",  
                                                 filetypes=[("PNG files", "*.png"),  
                                                            ("JPEG files", "*.jpg"),  
                                                            ("All files", "*.*")])  
        self.frame.focus_force()
        if not save_path:  
            return  
  
        try:  
            self.scaled_image.save(save_path)  
            messagebox.showinfo(_("Successful"), _("Pic has been saved to: ") + save_path)  
        except Exception as e:  
            messagebox.showerror("Error", str(e))  
  
if __name__ == "__main__":  
    # Loading Language
    _ = utils.set_language(executable_name)

    app = ImageScaler()  