"""SSE transport around the same validated and transactional API handlers."""
import asyncio
import json
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute

from packages.agent_core.streaming import stream_sink
from services.api.auth import current_user


class AIStreamingRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request):
            if request.method != 'POST' or 'text/event-stream' not in request.headers.get('accept', ''):
                return await handler(request)
            # Keep HTTP 401 available to the existing refresh-token mechanism.
            if request.headers.get('authorization'):
                await asyncio.to_thread(current_user, request)
            # Read before StreamingResponse starts its disconnect listener; both
            # otherwise compete for the same ASGI receive channel.
            await request.body()
            queue = asyncio.Queue(maxsize=64)
            loop = asyncio.get_running_loop()
            disconnected = threading.Event()

            def publish(event):
                if disconnected.is_set():
                    raise HTTPException(499, '回答连接已关闭')
                pending = asyncio.run_coroutine_threadsafe(queue.put(event), loop)
                while True:
                    try:
                        pending.result(timeout=0.5)
                        return
                    except FutureTimeoutError:
                        if disconnected.is_set():
                            pending.cancel()
                            raise HTTPException(499, '回答连接已关闭')

            async def produce():
                token = stream_sink.set(publish)
                try:
                    response = await handler(request)
                    value = json.loads(response.body)
                    if response.status_code >= 400:
                        await queue.put({'type': 'error', 'status': response.status_code, 'detail': '请求未完成，请检查输入后重试'})
                    else:
                        await queue.put({'type': 'result', 'value': value})
                except HTTPException as error:
                    await queue.put({'type': 'error', 'status': error.status_code, 'detail': error.detail if isinstance(error.detail, str) else '请求未完成，请检查输入后重试'})
                except RequestValidationError:
                    await queue.put({'type': 'error', 'status': 422, 'detail': '输入格式不正确，请检查内容后重试'})
                except Exception:
                    await queue.put({'type': 'error', 'status': 500, 'detail': '回答未完成，请保留输入后重试'})
                finally:
                    stream_sink.reset(token)

            async def events():
                task = asyncio.create_task(produce())
                try:
                    yield ': connected\n\n'
                    while True:
                        try:
                            event = await asyncio.wait_for(queue.get(), timeout=10)
                        except asyncio.TimeoutError:
                            yield ': heartbeat\n\n'
                            continue
                        yield 'data: ' + json.dumps(event, ensure_ascii=False) + '\n\n'
                        if event['type'] in {'result', 'error'}:
                            break
                finally:
                    disconnected.set()
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            return StreamingResponse(events(), media_type='text/event-stream', headers={
                'Cache-Control': 'no-store, no-transform', 'X-Accel-Buffering': 'no', 'Content-Encoding': 'identity',
            })
        return handle
