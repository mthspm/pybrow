import socket
import ssl
import os
import base64
from enum import Enum

# https://www.site.com:443/path/to/file.html

SCHEMES = ["http", "https", "file", "data", "view-source"]

class URL:
    def __init__(self, url: str) -> None:
        self.scheme, url = url.split("://", 1)
        assert self.scheme in SCHEMES
        self.socket = None
        if self.scheme == "view-source":
            self.inner_url = URL(url)
        elif self.scheme == "data":
            self.data = url
        elif self.scheme == "file":
            self.path = url
        elif self.scheme in ["http", "https"]:
            if "/" not in url:
                url = url + "/"
            self.host, url = url.split("/", 1)
            self.path = "/" + url
            if self.scheme == "http":
                self.port = 80
            elif self.scheme == "https":
                self.port = 443
            if ":" in self.host:
                self.host, port = self.host.split(":", 1)
                self.port = int(port)
    
    def request(self):
        if self.scheme == "view-source":
            return self.inner_url.request()
        if self.scheme == "file":
            with open(self.path, "r", encoding="utf8") as f:
                return f.read()
        if self.scheme == "data":
            assert "," in self.data
            metadata, data = self.data.split(",", 1)
            if metadata.endswith("base64"):
                return base64.b64decode(data).decode("utf8")
            elif metadata.endswith("text/colored"):
                return "\033[31m" + data + "\033[0m"
            return data
        
        if self.socket is None:
            self.socket = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP
            )
            self.socket.connect((self.host, self.port))
            if self.scheme == "https":
                ctx = ssl.create_default_context()
                self.socket = ctx.wrap_socket(self.socket, server_hostname=self.host)
        
        # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers to find more examples
        headers = {
            "Host": self.host,
            "User-Agent": "pybrow/1.0"
        }
        
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        for k, v in headers.items():
            request += "{}: {}\r\n".format(k, v)
        request += "\r\n"
        self.socket.send(request.encode("utf8"))
        
        response = self.socket.makefile("r", encoding="utf8", newline="\r\n")
        
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        
        assert "transfer-encoding" not in response_headers
        assert "content-enconding" not in response_headers
        
        content_length = int(response_headers.get("content-length", 0))
        content = response.read(content_length)
        return content
    
def show(body, raw=False) -> None:
    if raw:
        print(body)
        return
    
    body = body.replace("&lt;", "<").replace("&gt;", ">")
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")

def load(url: URL) -> None:
    body = url.request()
    if url.scheme == "view-source":
        show(body, raw=True)
    else:
        show(body)
  
if __name__ == "__main__":
    import sys
    
    ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
    TEST_DEFAULT = os.path.join(ASSETS_DIR, "example.html")
    TEST_ENTITIES = os.path.join(ASSETS_DIR, "entities.html")
    
    if len(sys.argv) > 1:
        full_url = " ".join(sys.argv[1:])
        load(URL(full_url))
    else:
        load(URL(f"file://{TEST_ENTITIES}"))