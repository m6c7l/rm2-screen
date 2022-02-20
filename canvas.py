import os
import sys
import json
import collections

import asyncio
import subprocess

import http
import websockets


def device_model_input():
    try:
        proc = subprocess.run(
            ['cat', '/proc/device-tree/model',],
            check=True,
            capture_output=True,
        )
        model = proc.stdout[:14].decode('latin-1')
        if 'reMarkable' in model:
            if '2.0' in model:
                return '/dev/input/event1'
            elif '1.0' in model:
                return '/dev/input/event0'
            else:
                raise Exception('unsupported model')
        else:
            raise Exception('unknown device')
    except Exception as e:
        print('[error]', e, file=sys.stderr, flush=True)
        os._exit(1)


async def pipe_to_websocket(websocket, pipe):

    proc = await asyncio.create_subprocess_shell(
        f'cat {pipe}',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    print(f'[info] forwarding {pipe} to {websocket.remote_address}')

    size = 5

    pen = {
         0: collections.deque([float('nan')], maxlen=size),  # x
         1: collections.deque([float('nan')], maxlen=size),  # y
        24: collections.deque([float('nan')], maxlen=1)      # pressure
    }

    last = [float('nan'), float('nan'), 0]

    try:

        while proc.returncode == None:

            buf = await proc.stdout.read(16)

            a = buf[4:8]
            b = buf[8:12]
            c = buf[12:16]

            typ = b[0]
            code = b[2] + b[3] * 0x100

            if typ == 3 and code in pen:  # absolute pen position

                val = c[0] + c[1] * 0x100 + c[2] * 0x10000 + c[3] * 0x1000000                    
                
                pen[code].append(val)
        
                loc = [sum(v) / len(v) for _, v in pen.items()]

                if last != loc:

                    if sum([(a-b)**2 for a, b in zip(last, loc)])**0.5 < 50:
                        continue

                    last = loc

                    try:
                        await websocket.send(json.dumps(loc))
                    except Exception as e:
                        pass

    finally:
        proc.kill()


async def http_handler(path, request):
    
    if path == '/pen':
        return None
    
    elif path != '/':
        return (http.HTTPStatus.NOT_FOUND, [], "")

    body = open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'canvas.html'), 'rb').read()
    headers = [
        ('Content-Type', 'text/html'),
        ('Content-Length', str(len(body))),
        ('Connection', 'close'),
    ]

    return (http.HTTPStatus.OK, headers, body)


def run(host="0.0.0.0", port=12345):

    pipe = device_model_input()

    forward = lambda ws: pipe_to_websocket(ws, pipe)

    start_server = websockets.serve(
        forward,
        host, port,
        ping_interval=1000,
        process_request=http_handler
    )

    print(f'[info] serving on {host}:{port}')

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    run()
