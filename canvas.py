import os
import sys

import time

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


async def pipe_to_websocket(websocket, pipe, orientation):

    proc = await asyncio.create_subprocess_shell(
        f'cat {pipe}',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    print(f'[info] forwarding {pipe} to {websocket.remote_address} as {orientation}')

    portrait = orientation == 'portrait'
    landscape = orientation == 'landscape'

    size = 8

    pen = {0: 'x', 1: 'y', 24: 'z'}

    val = {
       pen[0]:  collections.deque([float('nan')]*size, maxlen=size),
       pen[1]:  collections.deque([float('nan')]*size, maxlen=size),
       pen[24]: collections.deque([float('nan')]*size, maxlen=size)
    }

    try:

        msg, nav = {}, {'book': 0, 'hover': True}

        while proc.returncode == None:

            buf = await proc.stdout.read(16)

            a, b, c = buf[4:8], buf[8:12], buf[12:16]

            typ, code = b[0], b[2] + b[3] * 0x100  # typ 1 = close 

            if typ == 3 and code in pen:  # absolute pen position

                for _, k in pen.items():
                    val[k].append(val[k][-1])
              
                val[pen[code]][-1] = c[0] + c[1] * 0x100 + c[2] * 0x10000 + c[3] * 0x1000000

                x, y, z = [val[k][-1] for _, k in pen.items()]

                if   (z > 0) and \
                     ((landscape and (   50 < x <  1150) and ( 6700 < y <  7800)) or \
                      (portrait  and (12950 < x < 14150) and (   50 < y <  1200))):

                    if 'undo' in msg.get('act', ()):
                        continue

                    msg['act'] = ('undo',)

                elif (z > 0) and \
                     ((landscape and (   50 < x <  1150) and ( 7900 < y <  9000)) or \
                      (portrait  and (11550 < x < 12750) and (   50 < y <  1200))):

                    if 'redo' in msg.get('act', ()):
                        continue

                    msg['act'] = ('redo',)

                elif (z > 0) and \
                     ((landscape and (   50 < x <  1150) and (14450 < y < 15550)) or \
                      (portrait  and (   50 < x <  1250) and (   50 < y <  1350))):

                    nav['book'] += int(not nav['book'])

                    if nav['book'] > 1:
                       nav['book'] = -1

                elif (z > 0) and (nav['book']) and \
                     ((landscape and ( 1200 < x <  6800) and (14450 < y < 15550)) or \
                      (portrait  and (   50 < x <  1250) and ( 1350 < y <  6800))):

                    if 'new' in msg.get('act', ()):
                        continue

                    msg['act'] = ('new',)

                    nav['book'] = -1

                else:

                    if (z > 0):

                        if not nav['hover'] and int(time.time()*1000) % 2 == 0:
                            continue

                        x, y = sum(val['x']) / size, sum(val['y']) / size
                        try: x = int(x)
                        except: pass
                        try: y = int(y)
                        except: pass
                        msg['pen'] = (x, y, z)

                        nav['hover'] = False

                    else:

                        if nav['hover'] and int(time.time()*1000) % 2 == 0:
                            continue

                        msg['cur'] = (x, y)

                        nav['hover'] = True

                    for k in ('act',):
                        msg.pop(k, None)

                    for k in nav:
                        if nav[k]:
                            nav[k] += nav[k] % 2

                try:
                    for k in msg:
                        await websocket.send('{} {}'.format(k, ' '.join((str(item) for item in msg[k]))))
                except:
                    pass

                for k in ('pen', 'cur',):
                    msg.pop(k, None)

    finally:
        proc.kill()


async def http_handler(path, request, orientation):
    
    if path == '/pen':
        return None
    
    elif path != '/':
        return (http.HTTPStatus.NOT_FOUND, [], "")

    body = open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'canvas.html'), 'rb').read()

    landscape = str(orientation == 'landscape').lower()
    portrait = str(orientation == 'portrait').lower()
 
    body = body.replace(b'{landscape}', bytes(landscape, 'latin-1'))
    body = body.replace(b'{portrait}', bytes(portrait, 'latin-1'))

    headers = [
        ('Content-Type', 'text/html'),
        ('Content-Length', str(len(body))),
        ('Connection', 'close'),
    ]

    return (http.HTTPStatus.OK, headers, body)


def run(host, orientation, port):

    pipe = device_model_input()

    forward = lambda ws: pipe_to_websocket(ws, pipe, orientation)

    start_server = websockets.serve(
        forward,
        host,
        port,
        ping_interval=1000,
        process_request=lambda p, r : http_handler(p, r, orientation)
    )

    print(f'[info] serving on {host}:{port}')

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()


def usage():
    print('usage: {} <landscape|portrait> <port>'.format(os.path.basename(sys.argv[0])))
    os._exit(1)


if __name__ == "__main__":

    print('!!!!!!', sys.argv)
    args = sys.argv[1:]
    try:
       if args[0] not in ('landscape', 'portrait'):
           raise Exception()
       run('0.0.0.0', args[0], int(args[1]))
    except:
       usage()

