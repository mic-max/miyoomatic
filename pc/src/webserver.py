import asyncio
import http.server
import websockets
import socketserver

async def handler(websocket):
    clients.add(websocket)
    try:
        async for message in websocket:
            for client in clients:
                if client != websocket:
                    await client.send(message)
    finally:
        clients.remove(websocket)

async def ws_server():
    async with websockets.serve(handler, 'localhost', 8765):
        await asyncio.Future()

def run_ws_server():
    asyncio.run(ws_server())

def start_http_server():
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(('', 8000), handler) as httpd:
        httpd.serve_forever()
        # TODO: when i serve this html can i include the current database values on first launch