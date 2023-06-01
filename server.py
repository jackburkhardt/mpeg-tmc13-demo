import socket
import io
import sys
import os
import subprocess
import open3d as o3d
import time

in_conn = None
src_port = 0
dst_port = 0
busy = False
display = True

def open_socket():
    """Opens and binds a socket on the given port and listens for connections."""
    global in_conn
    in_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    in_conn.bind(('localhost', src_port))
    in_conn.listen(0)
    try_accept()

def try_accept():
    """Tries to accept a connection. If it fails, it tries again."""
    # if we have more than one connection, we don't want to accept it
    global busy
    global in_conn
    while not busy:
        try:
            client, addr = in_conn.accept()
            read(client)
            busy = True
        except socket.error:
            pass

def read(client):
    """Reads the data from the client and sends the requested file."""
    global in_conn
    global busy
    response = b""
    print("Getting data...\n")
    while True:
        try:
            data = in_conn.recv(4096)
            response += data
            if not data:
                break
        except socket.error:
            break

    decode(response)
    busy = False
    try_accept()

def send_buffer(queue):
    out_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    out_conn.connect(('localhost', dst_port))
    counter = 1
    total = len(queue)
# send the entire array of data at once
    while queue:
        sys.stdout.write("Sending frame " + str(counter) + " of " + str(total) + "\n")
        out_conn.sendall(queue.pop(0))
        counter += 1

    out_conn.close()


def decode(data):
    frames = data.split(b"\0")
    decoded_frames = []
    
    for frame in frames:
        frame.replace(b"\0", b"")
        if frame == b"":
            continue

        out = subprocess.run(["cd /codecs/tmc13/tmc3 && ./tmc3 --mode=1 --compressedStreamPath=\"/dev/stdin\" --reconstructedDataPath=\"/dev/stdout\""], shell=True, input=frame, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        decoded_frames.append(out.stdout)

    sys.stdout.write("Decoded " + str(len(decoded_frames)) + " frames\n")

    if display: display_frames(decoded_frames)

def encode(src_path):
    paths = []
    for filename in os.listdir(src_path):
        if filename.endswith(".ply"):
            paths.append(os.path.join(src_path, filename))
        else:
            continue

    queue = []
    counter = 1
    for path in paths:
        out = subprocess.run(["cd /codecs/tmc13/tmc3 && ./tmc3 --mode=0 --uncompressedDataPath=\"" + path + "\" --compressedStreamPath=\"/dev/stdout\""], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        queue.append(out.stdout + b"\0") # null bytes are used to separate frames
        sys.stdout.write("Encoded frame " + str(counter) + " of " + str(len(paths)) + "\n")
        counter += 1

    send_buffer(queue)

def display_frames_from_file(path):
    # convert the frames to point clouds
    point_clouds = []
    paths = []

    for filename in os.listdir(path):
        if filename.endswith(".ply"):
            paths.append(os.path.join(path, filename))
        else:
            continue
    
    for path in paths:
        pcd = o3d.io.read_point_cloud(path)
        point_clouds.append(pcd)

    vis = o3d.visualization.Visualizer()
    vis.create_window()

    for pc in point_clouds:
        # clear the visualizer
        vis.clear_geometries()
        # transform to face upwards and flip 180 degrees
        pc.transform([[1, 0, 0, 0], [0, 1, 1, 0], [0, 0, 1, 0], [0,0,0,1]])
        vis.add_geometry(pc)


        
        
        vis.poll_events()
        vis.update_renderer()

    #vis.destroy_window()
    
def display_frames(frames):
    # convert the frames to point clouds
    point_clouds = []
    for frame in frames:
        pcd = o3d.io.read_point_cloud(io.BytesIO(frame))
        point_clouds.append(pcd)

    vis = o3d.visualization.Visualizer()
    vis.create_window()

    for pcd in point_clouds:
        # clear the visualizer
        vis.clear_geometries()
        vis.add_geometry(pcd)
        vis.update_geometry()
        vis.poll_events()
        vis.update_renderer()

    vis.destroy_window()

if __name__ == '__main__':
    display_frames_from_file("datasets/sarah9")

    if len(sys.argv) < 4: 
        sys.stderr.write("Usage: python3 server.py <int: src_port> <int: dst_port> <bool: display_on_receive> <string (optional): path_to_point_clouds>\n")
        sys.exit(8)
    src_port = int(sys.argv[1])
    dst_port = int(sys.argv[2])
    display = bool(sys.argv[3])
    if len(sys.argv) == 5:
        path = str(sys.argv[4])
        encode(path)
    open_socket()