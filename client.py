import socket
import re
import sys

conn = None
redirect_count = 0

# Exit codes:
# 0: success
# 1: received a 4xx response
# 2: URL does not start with http or https
# 3: URL is https
# 4: incorrect content type
# 10: redirected more than 10 times

def connect(url):
    """Connects to the given url."""
    url = re.sub(r'\r', '', url)
    # give up after 10 redirects
    global redirect_count
    if redirect_count >= 10:
        sys.stderr.write("Error (10): Redirected more than 10 times!\n")
        sys.exit(10)

    # if url does not start with http or https, exit
    if not re.search(r'http', url):
        sys.stderr.write("Error (2): URL must start with http or https!\n")
        sys.exit(2)

    # if the url is https, exit
    if re.search(r'https', url):
        sys.stderr.write("Error (3): Attempted to visit or redirect to https!\n")
        sys.exit(3)

    global conn

    # grab the port number (if any) and remove it from the url
    port = re.search(r':\d+', url)
    if port:
        url = re.sub(r':\d+','', url)
        port = int(port.group(0)[1:])
    else:
        port = 80

    # remove the http(s):// from the url and grab the host and path
    url = re.sub(r'http(s)?://', '', url)
    host = re.search(r'[^/]+', url).group(0)
    path = re.sub(host, '', url)
    if path == '':
        path = '/'

    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #conn.setblocking(False)
    #conn.settimeout(0.3)
    conn.connect((host, port))

    send_request(path, host)

def send_request(path, host):
    """Sends a request to the given host and path."""
    global conn
    request = f"GET {path} HTTP/1.0\r\nHost: {host}\r\n\r\n"
    conn.sendall(request.encode())
    get_response()

def get_response():
    """Gets the response from the server."""
    global conn
    response = b""
    #print("Getting data...\n")
    while True:
        try:
            data = conn.recv(4096)
            response += data
            if not data:
                break
        except socket.error:
            break

    conn.close()
    parse_response(response.decode(errors='ignore'))

def parse_response(response):
    """Parses the response from the server."""
    # check the content type is text/html
    content_type = re.search(r'Content-Type: text/html', response)
    if not content_type:
        sys.stderr.write("Error (4): Content type is not text/html!\n")
        sys.exit(4)

    # grab the response code
    response_code = int(re.search(r'\d{3}', response).group(0))

    # 200 = all good! print body and exit
    if response_code == 200:
        headers, body = response.split('\r\n\r\n', 1)
        sys.stdout.write(body)
        sys.exit(0)
    # 301 or 302 = redirect, so grab the location and try again
    elif response_code == 301 or response_code == 302:
        location = re.search(r'Location: (.*)', response)
        location = location.group(1)
        sys.stderr.write(f"Redirected to: {location}\n")
        global redirect_count
        redirect_count += 1
        connect(location)
    # 4xx = error, print the body and exit
    elif response_code >= 400:
        headers, body = response.split('\r\n\r\n', 1)
        sys.stdout.write(body)
        sys.stderr.write(f"Error: Received a {response_code} response!\n")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2: 
        sys.exit(8)
    connect(sys.argv[1])