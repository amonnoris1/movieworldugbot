from Adarsh.vars import Var
from Adarsh.bot import StreamBot
from Adarsh.utils.human_readable import humanbytes
from Adarsh.utils.file_properties import get_file_ids
from Adarsh.server.exceptions import InvalidHash
import urllib.parse
import html
import aiofiles
import logging


async def render_page(id, secure_hash, access_key):
    file_data=await get_file_ids(StreamBot, int(Var.BIN_CHANNEL), int(id))
    if file_data.unique_id[:6] != secure_hash:
        logging.debug(f'link hash: {secure_hash} - {file_data.unique_id[:6]}')
        logging.debug(f"Invalid hash for message with - ID {id}")
        raise InvalidHash
    src = urllib.parse.urljoin(
        Var.URL,
        f'{secure_hash}{str(id)}?{urllib.parse.urlencode({"key": access_key})}',
    )
    if str(file_data.mime_type.split('/')[0].strip()) == 'video':
        async with aiofiles.open('Adarsh/template/req.html') as r:
            heading = 'Watch {}'.format(html.escape(file_data.file_name or 'video'))
            tag = file_data.mime_type.split('/')[0].strip()
            page_html = (await r.read())
            page_html = page_html.replace('{{TITLE}}', heading)
            page_html = page_html.replace('{{NAME}}', html.escape(file_data.file_name or 'video'))
            page_html = page_html.replace('{{SOURCE}}', html.escape(src, quote=True))
            page_html = page_html.replace('{{MEDIA_TAG}}', tag)
    elif str(file_data.mime_type.split('/')[0].strip()) == 'audio':
        async with aiofiles.open('Adarsh/template/req.html') as r:
            heading = 'Listen {}'.format(html.escape(file_data.file_name or 'audio'))
            tag = file_data.mime_type.split('/')[0].strip()
            page_html = (await r.read())
            page_html = page_html.replace('{{TITLE}}', heading)
            page_html = page_html.replace('{{NAME}}', html.escape(file_data.file_name or 'audio'))
            page_html = page_html.replace('{{SOURCE}}', html.escape(src, quote=True))
            page_html = page_html.replace('{{MEDIA_TAG}}', tag)
    else:
        async with aiofiles.open('Adarsh/template/dl.html') as r:
            heading = 'Download {}'.format(html.escape(file_data.file_name or 'file'))
            file_size = humanbytes(int(file_data.file_size))
            page_html = (await r.read())
            page_html = page_html.replace('{{TITLE}}', heading)
            page_html = page_html.replace('{{NAME}}', html.escape(file_data.file_name or 'file'))
            page_html = page_html.replace('{{FILE_SIZE}}', html.escape(file_size))
            page_html = page_html.replace('{{SOURCE}}', html.escape(src, quote=True))
    return page_html
