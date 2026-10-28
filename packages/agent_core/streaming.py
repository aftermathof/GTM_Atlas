"""Request-local model progress; ordinary JSON callers do not install a sink."""
import json
import re
from contextvars import ContextVar

stream_sink = ContextVar('ai_stream_sink', default=None)


def emit_stream(event):
    sink = stream_sink.get()
    if sink:
        sink(event)


def json_preview(raw):
    """Read only user-facing string fields, including an unfinished JSON string."""
    texts = []
    for match in re.finditer(r'"(?:text|analysis|questions|feedback|advice)"\s*:\s*"((?:[^"\\]|\\.)*)', raw):
        value = match[1]
        for trim in range(7):
            try:
                decoded = json.loads('"' + (value[:-trim] if trim else value) + '"')
                texts.append(decoded.encode('utf-16-le', 'surrogatepass').decode('utf-16-le', 'ignore'))
                break
            except ValueError:
                continue
    return '\n\n'.join(texts)
