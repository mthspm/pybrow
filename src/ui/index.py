from __future__ import annotations

import os
import tkinter as tk
import platform
import argparse
from logging import warning
from pathlib import Path
from ..core.url import URL, lex, URLFactory

width, height = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
OS = platform.system()
ASSETS_DIR = Path(__file__).parent.parent / "assets"
test_file = ASSETS_DIR / "default.html"
test_file2 = ASSETS_DIR / "entities.html"

class Browser:
    def __init__(self, direction="ltr"):
        self.display_list = []
        self.scroll = 0
        self.direction = direction
        self.window = tk.Tk()
        self.canvas = tk.Canvas(
            self.window,
            width=width,
            height=height,
        )
        self.canvas.pack(fill=tk.BOTH, expand=tk.YES)
        self.emoji_images = self.load_emoji_images()
        self.setup_binds()
    
    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + height: continue
            if y + VSTEP < self.scroll: continue
            if c in self.emoji_images:
                self.canvas.create_image(x, y - self.scroll, image=self.emoji_images[c], anchor="nw")
            else:
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
      
    def load(self, url: str):
        try:
            url = URLFactory.create(url)
            body = url.request()
        except Exception as e:
            warning(f"Failed to load {url}: {e}")
            url = URLFactory.create("about://blank")
            body = url.request()

        if isinstance(body, bytes):
            body = body.decode("utf8", errors="replace")
            
        if url.scheme == "view-source":
            text = lex(body, raw=True)
        else:
            text = lex(body)
        self.display_list = layout(text, self.direction)
        self.draw()
    
    def load_emoji_images(self):
        emoji_dir = ASSETS_DIR / "emojis"
        files = [f for f in os.listdir(emoji_dir) if f.endswith("_color.png")]
        images = {}
        for emoji_file in files:
            emoji_code = os.path.splitext(emoji_file)[0].split('_')[0]
            path = os.path.join(emoji_dir, emoji_file)
            images[emoji_code] = tk.PhotoImage(file=path)
        return images
    
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

def layout(text, direction="ltr"):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    if direction == "rtl":
        cursor_x = width - HSTEP
    for c in text:
        if c == "\n":  # Paragraph break
            cursor_y += VSTEP * 2
            cursor_x = HSTEP if direction != "rtl" else width - HSTEP
        else:  # Normal character
            display_list.append((cursor_x, cursor_y, c))
            if direction == "ltr":
                cursor_x += HSTEP
                if cursor_x > width - HSTEP:
                    cursor_y += VSTEP
                    cursor_x = HSTEP
            elif direction == "rtl":
                cursor_x -= HSTEP
                if cursor_x < HSTEP:
                    cursor_y += VSTEP
                    cursor_x = width - HSTEP
            elif direction == "ttb":
                cursor_y += VSTEP
                if cursor_y > height - VSTEP:
                    cursor_x += HSTEP
                    cursor_y = VSTEP
    return display_list

def parse_args():
    parser = argparse.ArgumentParser(
        prog="pybrow",
        description="A simple web browser inspired on the book Web Browser Engineering.",
        epilog="Maded by @mthspm",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=None,
        help="URL to load (e.g., http://example.com or file:///path/to/file.html)"
    )
    parser.add_argument(
        "--direction", "-d",
        choices=["ltr", "rtl", "ttb"],
        default="ltr",
        help="Text direction: ltr (left-to-right), rtl (right-to-left), ttb (top-to-bottom)"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 1.0"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    browser = Browser(direction=args.direction)
    if args.url:
        browser.load(args.url)
    else:
        test_file = ASSETS_DIR / "default.html"
        test_file2 = ASSETS_DIR / "entities.html"
        browser.load(f"file:///{test_file2}")
    tk.mainloop()
    