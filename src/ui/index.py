import tkinter as tk
from ..core.url import lex, URLFactory

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100

class Browser:
    def __init__(self):
        self.window = tk.Tk()
        self.canvas = tk.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
        )
        self.canvas.pack()
        self.display_list = []
        self.scroll = 0
        
        self.window.bind("<Down>", self.scrolldown)
    
    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            self.canvas.create_text(x, y - self.scroll, text=c)
      
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
        
    def scrolldown(self, event):
        self.scroll += SCROLL_STEP
        self.draw()

def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x > WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP
    return display_list

if __name__ == "__main__":
    import sys
    url = URLFactory.create(sys.argv[1])
    Browser().load(url)
    tk.mainloop()
    