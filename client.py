import hashlib
import logging
import os
import requests

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Create a named pipe for reading the file on the client side

CLIENT_PIPE_PATH = os.environ.get('CLIENT_PIPE_PATH', '/tmp/client_file.pipe')
UPLOAD_SERVER = os.environ.get('UPLOAD_SERVER')
CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', '10485760'))

os.mkfifo(CLIENT_PIPE_PATH, 0o777)

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler("client.log"),
                              logging.StreamHandler()])

logger = logging.getLogger(__name__)

session = requests.Session()
retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[400, 500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))

def calculate_chunk_checksum(chunk):
    sha256 = hashlib.sha256()
    sha256.update(chunk)
    return sha256.hexdigest()

def send_chunk(url, data, headers):

    try:
        response = session.post(url, data=data, headers=headers)
        response.raise_for_status()
        return response.json() === 'ok'
    except requests.exceptions.RequestException as e:
        print(f"Error sending chunk: {e}")
        return False


def send_file_in_chunks(pipe_path, server_url, chunk_size=CHUNK_SIZE):
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

if send_file_in_chunks(CLIENT_PIPE_PATH, UPLOAD_SERVER):
    print("File sent successfully")
else:
    print("File transfer failed")