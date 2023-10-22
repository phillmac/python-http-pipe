import hashlib
import os
import requests

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Create a named pipe for reading the file on the client side

CLIENT_PIPE_PATH = os.environ.get('CLIENT_PIPE_PATH', '/tmp/client_file.pipe')
os.mkfifo(CLIENT_PIPE_PATH, 0o777)

def calculate_chunk_checksum(chunk):
    sha256 = hashlib.sha256()
    sha256.update(chunk)
    return sha256.hexdigest()

def send_chunk(url, data, headers):
    session = requests.Session()
    retries = Retry(total=10000, backoff_factor=0.1, status_forcelist=[400, 500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))

    try:
        response = session.post(url, data=data, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending chunk: {e}")
        return False

    return True

def send_file_in_chunks(pipe_path, server_url, chunk_size=1024):
    chunk_number = 0

    with open(pipe_path, 'rb') as pipe_file:
        while True:
            chunk = pipe_file.read(chunk_size)
            if not chunk:
                break

            checksum = calculate_chunk_checksum(chunk)
            headers = {'Chunk-Number': str(chunk_number), 'Checksum': checksum}
            chunk_url = f"{server_url}/upload_chunk"

            success = False
            while not success:
                success = send_chunk(chunk_url, chunk, headers)

            chunk_number += 1

    return True

# Open the client pipe for writing the file data
# with open(CLIENT_PIPE_PATH, 'wb') as client_pipe:
#     with open('your_file_to_send.txt', 'rb') as file:
#         client_pipe.write(file.read())

# Call send_file_in_chunks to send data from the client pipe to the server
upload_server = os.environ.get('UPLOAD_SERVER')

if send_file_in_chunks(CLIENT_PIPE_PATH, upload_server):
    print("File sent successfully")
else:
    print("File transfer failed")