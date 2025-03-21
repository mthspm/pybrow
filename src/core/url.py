from __future__ import annotations

import socket
import ssl
import os
import base64
import gzip
import time
import re
from datetime import datetime, timedelta
from enum import Enum

SCHEMES = (
    "http", "https", "file", "data", "view-source", "about"
)


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

URL_REGEX = re.compile(r'^(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*):/{0,3}(?P<url>.*)$')

class URL:
    def __init__(self, scheme: str, url: str) -> None:
        self.scheme = scheme
        self.url = url
        self.socket = None
        
    def request(self, max_redirects=5):
        raise NotImplementedError("Subclasses must implement this method")
    

class HTTPURL(URL):
    def __init__(self, scheme: str, url: str) -> None:
        super().__init__(scheme, url)
        if "/" not in self.url:
            self.url = self.url + "/"
        self.host, self.url = self.url.split("/", 1)
        self.path = "/" + self.url
        self.port = 80 if self.scheme == "http" else 443
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
    
    def handle_redirect(self, response_headers: dict, max_redirects: int):
        assert max_redirects != 0, "Too many redirects"
        location = response_headers.get("location")
        assert location, "Redirect status without location"
        if location.startswith("/"):
            location = f"{self.scheme}://{self.host}{location}"
        elif not location.startswith("http"):
            location = f"{self.scheme}://{location}"
        return URLFactory.create(location).request(max_redirects - 1)
    
    def request(self, max_redirects=5):
        url = f"{self.scheme}://{self.host}{self.path}"
        cached_response = cache.get(url)
        if cached_response:
            print("Using cached response")
            return cached_response
        
        if self.socket is None:
            self.socket = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                # proto=socket.IPPROTO_TCP
            )
            self.socket.connect((self.host, self.port))
            if self.scheme == "https":
                ctx = ssl.create_default_context()
                self.socket = ctx.wrap_socket(self.socket, server_hostname=self.host)
        
        # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers to find more examples
        headers = {
            "Host": self.host,
            "User-Agent": "pybrow/1.0",
            "Accept-Encoding": "gzip",
        }
        
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        for k, v in headers.items():
            request += "{}: {}\r\n".format(k, v)
        request += "\r\n"
        self.socket.send(request.encode("utf8"))
        
        response = self.socket.makefile("rb", newline="\r\n")
        statusline = response.readline().decode("utf8")
        version, status, explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline().decode("utf8")
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
            
        if 300 <= int(status) < 400:
            return self.handle_redirect(response_headers, max_redirects)
        
        assert "transfer-encoding" not in response_headers, "Transfer encoding not supported"
        assert "content-enconding" not in response_headers, "Content encoding not supported"
        
        content_length = int(response_headers.get("content-length", 0))
        content = response.read(content_length)
        
        if response_headers.get("content-encoding") == "gzip":
            content = gzip.decompress(content)
        
        cache.set(url, content, max_age=3600)
        return content
    

class FileURL(URL):
    def __init__(self, scheme: str, url: str) -> None:
        super().__init__(scheme, url)
        self.path = self.url
        
    def request(self, max_redirects=5):
        with open(self.path, "r", encoding="utf8") as f:
            return f.read()
        

class DataURL(URL):
    def __init__(self, scheme: str, url: str) -> None:
        super().__init__(scheme, url)
        assert "," in self.url, "Missing comma in data URL - data URLs should be in the form data:mimetype/base64,data"
        self.metadata, self.data = self.url.split(",", 1)
        
    def request(self, max_redirects=5):
        if self.metadata.endswith("base64"):
            return base64.b64decode(self.data).decode("utf8")
        elif self.metadata.endswith("text/colored"):
            return "\033[31m" + self.data + "\033[0m"
        return self.data

 
class ViewSourceURL(URL):
    def __init__(self, scheme: str, url: str) -> None:
        super().__init__(scheme, url)
        self.inner_url = URLFactory.create(self.url)
        
    def request(self, max_redirects=5):
        return self.inner_url.request(max_redirects)


class AboutBlankURL(URL):
    def __init__(self, scheme: str, url: str) -> None:
        super().__init__(scheme, url)
        
    def request(self, max_redirects=5):
        return ""


class URLFactory:
    @staticmethod
    def create(url: str) -> URL:
        match = URL_REGEX.match(url)
        assert match, f"Invalid URL format: {url}"
        scheme = match.group("scheme")
        url = match.group("url")
        assert scheme in SCHEMES, f"Unknown scheme: {scheme}"
        
        print(f"Creating URL object for scheme={scheme} url={url}")
        if scheme == "http" or scheme == "https": # http://www.google.com
            return HTTPURL(scheme, url)
        if scheme == "file": # file:///path/to/file.html
            return FileURL(scheme, url)
        if scheme == "data": # data:text/plain;base64,SGVsbG8sIFdvcmxkIQ%3D%3D
            return DataURL(scheme, url)
        if scheme == "view-source": # view-source:http://www.google.com
            return ViewSourceURL(scheme, url)
        if scheme == "about": # about:blank
            return AboutBlankURL(scheme, url)
    
    
def lex(body, raw=False) -> str:
    text = ""
    if raw:
        return body
    
    body = body.replace("&lt;", "<").replace("&gt;", ">")
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            text += c
    return text

def _load(url: URL) -> None:
    body = url.request()
    if isinstance(body, bytes):
        body = body.decode("utf8", errors="replace")
    if url.scheme == "view-source":
        print(lex(body, raw=True))
    else:
        print(lex(body))
  
if __name__ == "__main__":
    import sys
    
    ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
    TEST_DEFAULT = os.path.join(ASSETS_DIR, "example.html")
    TEST_ENTITIES = os.path.join(ASSETS_DIR, "entities.html")
    
    if len(sys.argv) > 1:
        full_url = " ".join(sys.argv[1:])
        _load(URLFactory.create(full_url))
    else:
        _load(URLFactory.create(f"file://{TEST_ENTITIES}"))