# Copyright (C) 2024-2024  WeAct Studio
import tkinter as tk  
from tkinter import filedialog, ttk, messagebox  
from PIL import Image, ImageTk, ImageSequence
import os
import sys
from pathlib import Path

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

        self.frame.title(_("Gif to png, ImageScaler Tool"))  
        self.frame.iconphoto(True, tk.PhotoImage(file=utils.get_root_dir() / "res" / "icons" / "logo.png"))
        self.frame.geometry('320x110')
        # 图片显示  
        self.label_image = ttk.Label(self.frame)  
        self.label_image.place(x=10,y=100)  
  
        # 宽度和高度输入框  
        self.width_label = ttk.Label(self.frame, text=_("Width:"))  
        self.width_label.place(x=10,y=10)  
        self.width_var = tk.StringVar()  
        self.width_entry = ttk.Entry(self.frame, textvariable=self.width_var)  
        self.width_entry.bind("<Key>", self.restrict_entry)
        self.width_entry.place(x=60,y=10, width=60,relwidth=0)  
  
        self.height_label = tk.Label(self.frame, text=_("Height:"))  
        self.height_label.place(x=10,y=40)  
        self.height_var = tk.StringVar()  
        self.height_entry = ttk.Entry(self.frame, textvariable=self.height_var)  
        self.height_entry.bind("<Key>", self.restrict_entry)
        self.height_entry.place(x=60,y=40, width=60,relwidth=0)  

        self.size_label = ttk.Label(self.frame, text="")  
        self.size_label.place(x=128,y=40,width=100,relwidth=0)

        self.frame_num_label = tk.Label(self.frame, text=_("Frame num:"))  
        self.frame_num_label.place(x=10,y=70)  
        self.frame_num_var = tk.StringVar()  
        self.frame_num_entry = ttk.Entry(self.frame, textvariable=self.frame_num_var)  
        self.frame_num_entry.bind("<Key>", self.restrict_entry)
        self.frame_num_entry.place(x=100,y=70, width=60,relwidth=0) 

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
        self.photo = None
        self.scaled_image_frames = []
        self.scaled_image_d_frames = []
        self.scaled_image_d_num_frames=0
        
        self.scaled_image_frames_step = 1

        self.main_refresh()

        if frame == None:
            self.frame.mainloop()
    
    def main_refresh(self):
        if len(self.scaled_image_d_frames) > 0:
            if self.scaled_image_d_num_frames == 0:
                self.scaled_image_d_num_frames = len(self.scaled_image_d_frames)
            else:
                self.photo = ImageTk.PhotoImage(self.scaled_image_d_frames[len(self.scaled_image_d_frames)-self.scaled_image_d_num_frames])  
                self.label_image.config(image=self.photo)  
                self.label_image.image = self.photo  # 防止垃圾回收

                self.scaled_image_frames_step = 1 if len(self.scaled_image_d_frames) <= int(self.frame_num_var.get()) else len(self.scaled_image_d_frames) // int(self.frame_num_var.get())
                if self.scaled_image_d_num_frames > self.scaled_image_frames_step:
                    self.scaled_image_d_num_frames = self.scaled_image_d_num_frames - self.scaled_image_frames_step
                else:
                    self.scaled_image_d_num_frames = 0
        self.frame.after(100*self.scaled_image_frames_step,self.main_refresh)

    def restrict_entry(self,event):
        current_text = event.widget.get()
        new_char = event.char

        # 如果用户按下的是Backspace键（ASCII码为8）或Delete键（在Mac上可能是127）
        # 则允许删除操作
        if new_char in ("", "\x7f", "\x08"):
            return

        if event.char.isdigit():
            return
        else:
            event.widget.delete(len(current_text), tk.END)
            return "break"
                    
    def open_image(self):  
        file_path = filedialog.askopenfilename(defaultextension=".gif",  
                                                 filetypes=[("Gif files", "*.gif")])  
        self.frame.focus_force()
        if file_path:  
            self.original_image = Image.open(file_path)  
            self.scaled_image_d_frames = []
            for frame in ImageSequence.Iterator(self.original_image):  
                # 缩放当前帧  
                width_set = 480
                height_set = 480
                resized_frame = frame.copy()
                if resized_frame.width > width_set:
                    # 仅指定宽度，高度按比例缩放  
                    ratio = width_set / resized_frame.width  
                    height = int(resized_frame.height * ratio)  
                    resized_frame = resized_frame.resize((width_set, height), Image.LANCZOS)  
                if resized_frame.height > height_set:  
                    # 仅指定高度，宽度按比例缩放  
                    ratio = height_set / resized_frame.height  
                    width = int(resized_frame.width * ratio)  
                    resized_frame  = resized_frame.resize((width, height_set), Image.LANCZOS) 
                # 将缩放后的帧添加到列表中  
                self.scaled_image_d_frames.append(resized_frame)
            self.frame_num_var.set(str(len(self.scaled_image_d_frames)))
            self.photo = ImageTk.PhotoImage(self.scaled_image_d_frames[0])  
            self.label_image.config(image=self.photo)  
            self.label_image.image = self.photo  # 防止垃圾回收

            if self.scaled_image_d_frames[0].width < 320:
                width = 295
            else:
                width = self.scaled_image_d_frames[0].width  
            self.frame.geometry(str(width + 25) + 'x' + str(self.scaled_image_d_frames[0].height + 110))
            self.size_label['text'] = str(self.original_image.width) + 'x' + str(self.original_image.height)
  
    def apply_scale(self):  
        width = int(self.width_var.get()) if self.width_var.get() else None  
        height = int(self.height_var.get()) if self.height_var.get() else None  
    
        if width is None and height is None:  
            messagebox.showerror(_("Error"), _("Please specify width or height."))  
            self.frame.focus_force()
            return  
    
        if width is not None and height is not None:  
            self.scaled_image_frames = []
            for frame in ImageSequence.Iterator(self.original_image):  
                 resized_frame = frame.copy()
                 resized_frame = resized_frame.resize((width, height), Image.LANCZOS)  
                 self.scaled_image_frames.append(resized_frame)
        elif width is not None:  
            # 仅指定宽度，高度按比例缩放  
            ratio = width / self.original_image.width  
            height = int(self.original_image.height * ratio)  
            self.scaled_image_frames = []
            for frame in ImageSequence.Iterator(self.original_image):  
                 resized_frame = frame.copy()
                 resized_frame = resized_frame.resize((width, height), Image.LANCZOS)  
                 self.scaled_image_frames.append(resized_frame) 
        elif height is not None:  
            # 仅指定高度，宽度按比例缩放  
            ratio = height / self.original_image.height  
            width = int(self.original_image.width * ratio)  
            self.scaled_image_frames = []
            for frame in ImageSequence.Iterator(self.original_image):  
                 resized_frame = frame.copy()
                 resized_frame = resized_frame.resize((width, height), Image.LANCZOS)  
                 self.scaled_image_frames.append(resized_frame)

        self.scaled_image_d_frames = []
        for frame in self.scaled_image_frames:  
            # 缩放当前帧  
            width_set = 480
            height_set = 480
            resized_frame = frame.copy()
            if resized_frame.width > width_set:
                # 仅指定宽度，高度按比例缩放  
                ratio = width_set / resized_frame.width  
                height = int(resized_frame.height * ratio)  
                resized_frame = resized_frame.resize((width_set, height), Image.LANCZOS)  
            if resized_frame.height > height_set:  
                # 仅指定高度，宽度按比例缩放  
                ratio = height_set / resized_frame.height  
                width = int(resized_frame.width * ratio)  
                resized_frame  = resized_frame.resize((width, height_set), Image.LANCZOS) 
            # 将缩放后的帧添加到列表中  
            self.scaled_image_d_frames.append(resized_frame)
        
        self.photo = ImageTk.PhotoImage(self.scaled_image_d_frames[0])  
        self.label_image.config(image=self.photo)  
        self.label_image.image = self.photo  # 防止垃圾回收

        if self.scaled_image_d_frames[0].width < 320:
            width = 295
        else:
            width = self.scaled_image_d_frames[0].width  
        self.frame.geometry(str(width + 25) + 'x' + str(self.scaled_image_d_frames[0].height + 110))
        self.size_label['text'] = str(self.scaled_image_frames[0].width) + 'x' + str(self.scaled_image_frames[0].height)
  
    def save_image(self):  
        if len(self.scaled_image_frames) == 0:  
            messagebox.showerror(_("Error"), _("Please open and scale the image before saving."))  
            self.frame.focus_force()
            return  
  
        save_path = filedialog.asksaveasfilename(defaultextension=".png",  
                                                 filetypes=[("PNG files", "*.png"),  
                                                            ("JPEG files", "*.jpg")])  
        self.frame.focus_force()
        if not save_path:  
            return  
  
        try:  
            base_name = os.path.basename(save_path)
            file_name, file_extension = os.path.splitext(base_name)
            dir_path = os.path.dirname(save_path)
            count = 0
            for i in range(0,len(self.scaled_image_frames),self.scaled_image_frames_step):
                path = dir_path+f"//{file_name}_{count}{file_extension}"
                self.scaled_image_frames[i].save(path)
                count = count + 1
            messagebox.showinfo(_("Successful"), _("Pic has been saved to: ") + dir_path)  
        except Exception as e:  
            messagebox.showerror("Error", str(e))  
  
if __name__ == "__main__":  
    # Loading Language
    _ = utils.set_language('image_scaler_tool')

    app = ImageScaler()  