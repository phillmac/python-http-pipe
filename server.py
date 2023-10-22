import asyncio
import hashlib
import logging
import os

import aiohttp
from aiohttp import web

from JSONHTTPErrors import JSONHTTPBadRequest



ASSEMBLED_PIPE_PATH = os.environ.get(
    'ASSEMBLED_PIPE_PATH', '/tmp/assembled_file.pipe')

CLIENT_MAX_SIZE = 1024**2 * int(os.environ.get('CLIENT_MAX_SIZE', '1024'))

LISTEN_HOST = os.environ.get('LISTEN_HOST', '0.0.0.0')
LISTEN_PORT = int(os.environ.get('LISTEN_PORT', '3000'))


def calculate_chunk_checksum(chunk):
    sha256 = hashlib.sha256()
    sha256.update(chunk)
    return sha256.hexdigest()


async def upload_chunk(request):
    chunk_number = int(request.headers.get('Chunk-Number'))
    checksum = request.headers.get('Checksum')
    chunk_data = await request.read()
    chunck_len = len(chunk_data)
    request.app['logger'].info(f'Got chuck data {chunck_len} bytes')

    calculated_checksum = calculate_chunk_checksum(chunk_data)
    if calculated_checksum != checksum:
        raise JSONHTTPBadRequest(reason='not ok: integrity mismatch')

    assembled_pipe = open(ASSEMBLED_PIPE_PATH, 'ab')
    assembled_pipe.write(chunk_data)
    assembled_pipe.close()

    return web.json_response('ok')



async def run_app():
    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler("server.log"),
                              logging.StreamHandler()])

    logger = logging.getLogger(__name__)

    app = web.Application(client_max_size=CLIENT_MAX_SIZE)

    app.router.add_post('/upload_chunk', upload_chunk)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, LISTEN_HOST, port=LISTEN_PORT)
    await site.start()

    names = sorted(str(s.name) for s in runner.sites)
    print(
        "======== Running on {} ========\n"
        "(Press CTRL+C to quit)".format(", ".join(names))
    )

    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    os.mkfifo(ASSEMBLED_PIPE_PATH, 0o777)  # Create the named pipe
    asyncio.run(run_app())