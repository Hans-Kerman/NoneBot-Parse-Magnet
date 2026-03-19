import re

def extract_magnet_links(text: str):
    pattern = r'magnet:\?xt=urn:btih:(?:[0-9a-fA-F]{40}|[A-Z2-7]{32})[^ \n\r\t"]*'
    return re.findall(pattern, text)
