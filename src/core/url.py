import socket
import ssl
import os

class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https", "file"]
        if self.scheme == "file":
            self.path = url
            self.host = None
            self.port = None
        else:
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
        if self.scheme == "file":
            with open(self.path, "r", encoding="utf8") as f:
                return f.read()
        
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP
        )
        s.connect((self.host, self.port))
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        
        # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers to find more examples
        headers = {
            "Host": self.host,
            "Connection": "close",
            "User-Agent": "pybrow/1.0"
        }
        
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        for k, v in headers.items():
            request += "{}: {}\r\n".format(k, v)
        request += "\r\n"
        s.send(request.encode("utf8"))
        
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        
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
        
        content = response.read()
        s.close()
        return content
    
def show(body):
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")
            

def load(url):
    body = url.request()
    show(body)
  
if __name__ == "__main__":
    import sys
    
    TEST_FILE = os.path.join(os.path.dirname(__file__), "..", "assets", "example.html")
    
    if len(sys.argv) > 1:
        load(URL(sys.argv[1]))
    else:
        load(URL(f"file://{TEST_FILE}"))