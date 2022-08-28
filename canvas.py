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

    size = 8

    pen = {0: 'x', 1: 'y', 24: 'z'}

    val = {
       pen[0]:  collections.deque([float('nan')]*size, maxlen=size),
       pen[1]:  collections.deque([float('nan')]*size, maxlen=size),
       pen[24]: collections.deque([float('nan')]*size, maxlen=size)
    }

    msg, nav = {}, {}

    try:

        while proc.returncode == None:

            buf = await proc.stdout.read(16)

            a, b, c = buf[4:8], buf[8:12], buf[12:16]

            typ, code = b[0], b[2] + b[3] * 0x100

            if typ == 3 and code in pen:  # absolute pen position

                for _, k in pen.items():
                    val[k].append(val[k][-1])
              
                val[pen[code]][-1] = c[0] + c[1] * 0x100 + c[2] * 0x10000 + c[3] * 0x1000000

                x, y, z = [val[k][-1] for _, k in pen.items()]

                if   (z > 0) and \
                     (((   50 < x <  1150) and (6700 < y < 7800)) or \
                      ((12950 < x < 14150) and (  50 < y < 1200))):

                    if 'act' in msg and 'undo' in msg['act']:
                        continue

                    msg = {'act': 'undo'}

                elif (z > 0) and \
                     (((   50 < x <  1150) and (7900 < y < 9000)) or \
                      ((11550 < x < 12750) and (  50 < y < 1200))):

                    if 'act' in msg and 'redo' in msg['act']:
                        continue

                    msg = {'act': 'redo'}

                elif (z > 0) and \
                     (((50 < x < 1150) and (14450 < y < 15550)) or \
                      ((50 < x < 1250) and (   50 < y <  1350))):

                    if 'nav' in msg and 'book' in msg['nav']:
                        continue

                    nav = {'book': None}

                elif (z > 0) and ('book' in nav) and \
                     (((1200 < x < 6800) and (14450 < y < 15550)) or \
                      ((  50 < x < 1250) and ( 1350 < y <  6800))):

                    msg = {'act': 'new'}

                else:

                    msg = {}

                    if (z > 0):

                        x, y = sum(val['x']) / size, sum(val['y']) / size
                        msg = {'pen': (x, y, z)}

                    else:

                        msg = {'cur': (x, y)}

                try:
                    await websocket.send(json.dumps(msg))
                except:
                    pass

                if 'act' in msg or 'pen' in msg:
                    nav = {}

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
