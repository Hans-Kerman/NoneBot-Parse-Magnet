import re
from urllib.parse import urlparse, parse_qsl

MAGNET_RE = re.compile(
    r'magnet:\?xt=urn:btih:(?:[0-9a-fA-F]{40}|[A-Za-z2-7]{32})'
    r'(?:&[a-zA-Z0-9]+=[^&#"\s]*)*'
)

def extract_magnet_links(text: str):
    candidates = MAGNET_RE.findall(text)
    result = []

    for m in candidates:
        parsed = urlparse(m)
        if parsed.scheme != "magnet":
            continue
        
        params = dict(parse_qsl(parsed.query))
        
        # 至少要有 xt 且是 btih
        if 'xt' not in params:
            continue
        if not params['xt'].startswith('urn:btih:'):
            continue

        result.append(m)

    return result