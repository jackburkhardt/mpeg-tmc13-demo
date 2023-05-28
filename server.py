import socket
import re
import sys
import os
import subprocess

conn = None
port = 0
path = ""
busy = False
display = True

def open_socket():
    """Opens and binds a socket on the given port and listens for connections."""
    global conn
    global port
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.bind(('', port))
    conn.listen(0)
    try_accept()

def try_accept():
    """Tries to accept a connection. If it fails, it tries again."""
    # if we have more than one connection, we don't want to accept it
    global busy
    while not busy:
        try:
            client, addr = conn.accept()
            read(client)
            busy = True
        except socket.error:
            pass

def read(client):
    """Reads the data from the client and sends the requested file."""
    global conn
    response = b""
    print("Getting data...\n")
    while True:
        try:
            data = conn.recv(4096)
            response += data
            if not data:
                break
        except socket.error:
            break

    decode(response)
    try_accept()

def send_buffer(queue):
    global conn
    counter = 1
# send the entire array of data at once
    while queue:
        sys.stdout.write("Sending frame " + str(counter) + " of " + str(len(queue)) + "\n")
        conn.sendall(queue.pop(0))
        counter += 1


def decode(data):
    frames = data.split(b"\0")
    decoded_frames = []
    
    for frame in frames:
        frame.replace(b"\0", b"")
        if frame == b"":
            continue

        out = subprocess.run(["cd /codecs/tmc13/tmc3 && ./tmc3 --mode=1 --compressedStreamPath=\"/dev/stdin\" --reconstructedDataPath=\"/dev/stdout\""], shell=True, input=frame, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        decoded_frames.append(out.stdout)

    display

def encode():
    # get list of paths every .ply file in the directory
    paths = []
    for filename in os.listdir(path):
        if filename.endswith(".ply"):
            paths.append(os.path.join(path, filename))
        else:
            continue

    queue = []
    for path in paths:
        out = subprocess.run(["cd /codecs/tmc13/tmc3 && ./tmc3 --mode=0 --uncompressedDataPath=\"" + path + "\" --compressedStreamPath=\"/dev/stdout\""], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        queue.append(out.stdout + b"\0")

    send_buffer(queue)
    
def display_frame(frame):
    # display the frame
    pass

if __name__ == '__main__':
    if len(sys.argv) < 3: 
        sys.stderr.write("Usage: python3 server.py <int: port> <bool: display> <string (optional): path_to_point_clouds>\n")
        sys.exit(8)
    port = int(sys.argv[1])
    display = bool(sys.argv[2])
    path = sys.argv[3]
    open_socket()