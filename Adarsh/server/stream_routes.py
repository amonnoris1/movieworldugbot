# Taken from megadlbot_oss <https://github.com/eyaadh/megadlbot_oss/blob/master/mega/webserver/routes.py>
# Thanks to Eyaadh <https://github.com/eyaadh>

import re
import time
import math
import logging
import secrets
import mimetypes
import hmac
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from Adarsh.bot import multi_clients, work_loads, StreamBot
from Adarsh.server.exceptions import FIleNotFound, InvalidHash
from Adarsh import StartTime, __version__
from ..utils.time_format import get_readable_time
from ..utils.custom_dl import ByteStreamer, offset_fix, chunk_size
from Adarsh.utils.render_template import render_page
from Adarsh.utils.database import MediaLinkRepository
from Adarsh.vars import Var


routes = web.RouteTableDef()
media_links = MediaLinkRepository(Var.DB_CONFIG)


async def require_media_key(request: web.Request, message_id: int, file_hash: str) -> str:
    """Accept a key only for the exact file it was created for."""
    access_key = request.query.get("key", "")
    if not await media_links.is_valid(message_id, file_hash, access_key):
        # Do not reveal whether the file, hash, or key was guessed incorrectly.
        raise web.HTTPNotFound()
    return access_key


def parse_stream_path(request: web.Request) -> tuple[int, str]:
    path = request.match_info["path"]
    match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
    if match:
        return int(match.group(2)), match.group(1)
    message_id = int(re.search(r"(\d+)(?:/\S+)?", path).group(1))
    return message_id, request.rel_url.query.get("hash", "")

@routes.get("/healthz", allow_head=True)
async def health_route_handler(request):
    supplied_token = request.query.get("token", "")
    if not hmac.compare_digest(supplied_token, Var.HEALTHCHECK_TOKEN):
        raise web.HTTPNotFound()
    return web.json_response({"status": "ok"})


@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        id, secure_hash = parse_stream_path(request)
        access_key = await require_media_key(request, id, secure_hash)
        return web.Response(
            text=await render_page(id, secure_hash, access_key),
            content_type='text/html',
        )
    except web.HTTPException:
        raise
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

@routes.get(r"/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        id, secure_hash = parse_stream_path(request)
        await require_media_key(request, id, secure_hash)
        return await media_streamer(request, id, secure_hash)
    except web.HTTPException:
        raise
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

class_cache = {}

async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)
    
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    
    if Var.MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.remote}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
        logging.debug(f"Using cached ByteStreamer object for client {index}")
    else:
        logging.debug(f"Creating new ByteStreamer object for client {index}")
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
    logging.debug("before calling get_file_properties")
    file_id = await tg_connect.get_file_properties(id)
    logging.debug("after calling get_file_properties")
    
    if file_id.unique_id[:6] != secure_hash:
        logging.debug(f"Invalid hash for message with ID {id}")
        raise InvalidHash
    
    file_size = file_id.file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = request.http_range.stop or file_size - 1

    req_length = until_bytes - from_bytes
    new_chunk_size = await chunk_size(req_length)
    offset = await offset_fix(from_bytes, new_chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = (until_bytes % new_chunk_size) + 1
    part_count = math.ceil(req_length / new_chunk_size)
    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, new_chunk_size
    )

    mime_type = file_id.mime_type
    file_name = file_id.file_name
    disposition = "attachment"
    if mime_type:
        if not file_name:
            try:
                file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
            except (IndexError, AttributeError):
                file_name = f"{secrets.token_hex(2)}.unknown"
    else:
        if file_name:
            mime_type = mimetypes.guess_type(file_id.file_name)
        else:
            mime_type = "application/octet-stream"
            file_name = f"{secrets.token_hex(2)}.unknown"
    return_resp = web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Range": f"bytes={from_bytes}-{until_bytes}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )

    if return_resp.status == 200:
        return_resp.headers.add("Content-Length", str(file_size))

    return return_resp
