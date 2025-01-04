from __future__ import annotations

import tkinter as tk
import platform
from logging import warning
from ..core.url import lex, URLFactory

width, height = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
OS = platform.system()

class Browser:
    def __init__(self):
        self.display_list = []
        self.scroll = 0
        self.window = tk.Tk()
        self.canvas = tk.Canvas(
            self.window,
            width=width,
            height=height,
        )
        self.canvas.pack(fill=tk.BOTH, expand=tk.YES)
        self.setup_binds()
    
    
    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + height: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)
        self.draw_scrollbar()
        
    def draw_scrollbar(self):
        doc_height = len(self.display_list)
        if doc_height <= height: return
        
        bar_height = max(100, height * height / doc_height)
        max_scroll = doc_height - height
        scroll_ratio = self.scroll / max_scroll
        bar_y = scroll_ratio * (height - bar_height)
        
        self.canvas.create_rectangle(
            width - 20, 0,
            width - 10, height,
            fill="lightgrey"
        ) 
        self.canvas.create_rectangle(
            width - 20, bar_y,
            width - 10, bar_y + bar_height,
            fill="blue"
        )
      
    def load(self, url):
        body = url.request()
        if isinstance(body, bytes):
            body = body.decode("utf8", errors="replace")
        if url.scheme == "view-source":
            text = lex(body, raw=True)
        else:
            text = lex(body)
        self.display_list = layout(text)
        self.draw()
    
    # === BINDS SETUP ===    
    def windows_bindings(self):
        self.window.bind("<MouseWheel>", self.wheelscroll)
    
    def linux_bindings(self):
        self.window.bind("<Button-4>", self.scrolldown)
        self.window.bind("<Button-5>", self.scrollup)
    
    def mac_bindings(self):
        self.window.bind("<MouseWheel>", self.wheelscroll)
    
    def generic_bindings(self):
        self.window.bind("<Configure>", self.on_resize)
    
    def setup_binds(self):
        _platform_bindings = {
            "Windows": self.windows_bindings,
            "Linux": self.linux_bindings,
            "Darwin": self.mac_bindings,
        }
        bind_setup_hook = _platform_bindings.get(OS)
        if not bind_setup_hook:
            warning(f"Unsupported OS: {OS} - Using Windows Bindings")
            bind_setup_hook = self.windows_bindings
            
        bind_setup_hook()
        self.generic_bindings()
        
        
    # === BINDS TRIGGERS ===
    def on_resize(self, event):
        global width, height
        width, height = event.width, event.height
        self.draw()
    
    def wheelscroll(self, event):
        if event.delta < 0:
            self.scrolldown(event)
        else:
            self.scrollup(event)
        
    def scrolldown(self, event):
        self.scroll += SCROLL_STEP
        if self.scroll > len(self.display_list) * VSTEP - height:
            self.scroll = len(self.display_list) * VSTEP - height
        self.draw()
        
    def scrollup(self, event):
        self.scroll -= SCROLL_STEP
        if self.scroll < 0:
            self.scroll = 0
        self.draw()

def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        if c == "\n": # Paragraph break
            cursor_y += VSTEP * 2
            cursor_x = HSTEP
        else: # Normal character
            display_list.append((cursor_x, cursor_y, c))
            cursor_x += HSTEP
            if cursor_x > width - HSTEP:
                cursor_y += VSTEP
                cursor_x = HSTEP
    return display_list

if __name__ == "__main__":
    import sys
    url = URLFactory.create(sys.argv[1])
    Browser().load(url)
    tk.mainloop()
    