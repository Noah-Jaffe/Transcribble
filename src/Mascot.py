import tkinter as tk
from tkinter import CENTER, ttk
from PIL import Image, ImageTk

from src.Config import *

class Mascot():
    """Show a mascot with a custom message."""
    def __init__(self, parent = None, message: str = None):
        """Display the mascot window with a message

        Args:
            message ([optional]str): Message to overlay on the mascot.
        """
        super().__init__()
        self.is_root = False if parent else True
        
        if self.is_root is None:
            parent = tk.Tk()
        
        if message is not None:
            message = str(message)
        
        self.popup = tk.Toplevel(parent)
        self.popup.overrideredirect(True)  # Remove window borders
        #self.popup.attributes('-topmost', True)  # Keep on top
        self.popup.configure(background='')

        # Get screen dimensions
        screen_width = self.popup.winfo_screenwidth()
        screen_height = self.popup.winfo_screenheight()

        # Load image or fallback
        if MASCOT_FILENAME.is_file():
            img = Image.open(MASCOT_FILENAME).convert("RGBA")
        else:
            img = Image.new('RGBA', (200, 200), (255, 0, 0, 0))

        # Resize if needed
        img_ratio = img.width / img.height
        max_width, max_height = screen_width - 100, screen_height - 100
        if img.width > max_width or img.height > max_height:
            if img_ratio > 1:
                img = img.resize((max_width, int(max_width / img_ratio)), Image.LANCZOS)
            else:
                img = img.resize((int(max_height * img_ratio), max_height), Image.LANCZOS)

        # Save transparent color (only works on Windows)
        transparent_color = "#%02x%02x%02x" % img.getpixel((0, 0))[:3]

        # Convert to Tkinter image
        self.img_tk = ImageTk.PhotoImage(img)

        # Set transparency if on Windows
        if sys.platform.startswith("win"):
            self.popup.wm_attributes('-transparentcolor', transparent_color)
        elif sys.platform == 'darwin':
            self.popup.attributes('-alpha', 1.0)  # No per-pixel transparency on mac
            # On macOS Big Sur+ you can get a similar effect
            self.popup.attributes("-transparent", True)
            self.popup.configure(background='systemTransparent')
        else:
            self.popup.attributes('-alpha', 1.0)  # Linux fallback

        # Create canvas and show image
        canvas = tk.Canvas(self.popup, width=img.width, height=img.height, highlightthickness=0, bg=transparent_color)
        canvas.pack()
        canvas.create_image(0, 0, anchor="nw", image=self.img_tk)

        if message is not None:
            # Overlay text
            text_label = tk.Label(self.popup, text=message, font=(DEFAULT_FONT, 16, "bold"),
                            fg="#010101", bg="white", wraplength=img.width - 20)
            text_label.place(anchor=CENTER, y=(img.height // 3) * 2, x = img.width//2, width=img.width - 20)
        
        # Position window
        x_position = (screen_width - img.width) // 2
        y_position = (screen_height - img.height) // 2
        self.popup.geometry(f"{img.width}x{img.height}+{x_position}+{y_position}")

        self.popup.wm_protocol("WM_DELETE_WINDOW", self.popup.destroy)
        self.popup.after(10, self.popup.lift)  # Raise above other windows
        self.popup.wait_visibility()
    
    def close(self):
        self.popup.destroy()
    
    def mainloop(self):
        self.popup.mainloop()

if __name__ == '__main__':
    m = Mascot("hi")
    m.mainloop()