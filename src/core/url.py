import socket
import ssl
import os
import base64
import time
from datetime import datetime, timedelta
from enum import Enum

# https://www.site.com:443/path/to/file.html

SCHEMES = ("http", "https", "file", "data", "view-source")


class CacheEntry:
    def __init__(self, response, expiry):
        self.response = response
        self.expiry = expiry
        

class Cache:
    def __init__(self):
        self.cache = {}
        
    def get(self, url):
        entry = self.cache.get(url)
        if entry is None:
            return None
        if entry.expiry < datetime.now():
            del self.cache[url]
            return None
        return entry.response
    
    def set(self, url, response, max_age):
        expiry = datetime.now() + timedelta(seconds=max_age)
        self.cache[url] = CacheEntry(response, expiry)


cache = Cache()

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
    
    def request(self, max_redirects=5):
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
        
        url = f"{self.scheme}://{self.host}{self.path}"
        cached_response = cache.get(url)
        if cached_response:
            print("Using cached response")
            return cached_response
        
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
        
        if 300 <= int(status) < 400:
            if max_redirects == 0:
                raise Exception("Too many redirects")
            location: str = response_headers.get("location")
            assert location, "Redirect status without location"
            if location.startswith("/"):
                location = f"{self.scheme}://{self.host}{location}"
            elif not location.startswith("http"):
                location = f"{self.scheme}://{location}"
            return URL(location).request(max_redirects - 1)
        
        assert "transfer-encoding" not in response_headers
        assert "content-enconding" not in response_headers
        
        content_length = int(response_headers.get("content-length", 0))
        content = response.read(content_length)
        
        cache.set(url, content, max_age=3600)
                
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