from src.Config import *
from tkinter import LEFT, SOLID, Toplevel
from tkinter.ttk import Label


class ToolTip(object):
    ACTIVE_TOOLTIPS = []
    def __init__(self, widget, text):
        """Binds a tooltip popup to a widget on <Enter> and <Leave>
        
        Args:
            widget (tkinter.Widget): element to attach tip to.
            text (str): tool tip string to display.
        """
        widget.bind('<Enter>', self.enter)
        widget.bind('<Leave>', self.leave)
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        ToolTip.ACTIVE_TOOLTIPS.append(self)
    
    def __del__(self):
        try:
            self.hidetip()
            ToolTip.ACTIVE_TOOLTIPS.remove(self)
        except:
            pass
    
    @staticmethod
    def hideall():
        for tt in ToolTip.ACTIVE_TOOLTIPS:
            try:
                tt.hidetip()
            except:
                pass
    
    def showtip(self, text):
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 57
        y = y + cy + self.widget.winfo_rooty() +27
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(tw, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1,
                      font=TOOLTIP_FONT)
        label.pack(ipadx=1)
    
    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()
    
    def enter(self, event):
        self.showtip(self.text)
    
    def leave(self, event):
        self.hidetip()

