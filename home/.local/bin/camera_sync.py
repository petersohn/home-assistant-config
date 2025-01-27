#!/usr/bin/env python3

from urllib.request import urlopen, Request
from urllib.parse import urlparse
from html.parser import HTMLParser
import argparse
import traceback
import os
import base64
from typing import override

def convert(tag: str, attrs: list[tuple[str, str | None]]):
    return (tag.casefold(), {key.casefold(): value for key, value in attrs})

class LinkParser(HTMLParser):
    def __init__(self):
        super(LinkParser, self).__init__()
        self.links: list[str] = []

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag, attrs2 = convert(tag, attrs)
        if tag == 'a':
            href = attrs2.get('href')
            if href is not None and not '://' in href and not href.startswith('../'):
                self.links.append(href)

def process(url: str, headers: dict[str, str]) -> list[str]:
    print(url)
    response: str = urlopen(Request(url, headers=headers)).read().decode()
    parser = LinkParser()
    parser.feed(response)

    result: list[str] = []
    for link in parser.links:
        url2 = url + link
        if link.endswith('/'):
            try:
                result.extend(process(url2, headers))
            except Exception:
                traceback.print_exc()
        else:
            print('Found', url2)
            result.append(url2)

    return result


parser = argparse.ArgumentParser()
parser.add_argument('--url') # pyright:ignore[reportUnusedCallResult]
parser.add_argument('--auth') # pyright:ignore[reportUnusedCallResult]
parser.add_argument('--target') # pyright:ignore[reportUnusedCallResult]
args = parser.parse_args()

headers: dict[str, str] = {'Authorization': 'Basic ' + base64.b64encode(args.auth.encode()).decode()}
files = process(args.url, headers)

os.makedirs(args.target, exist_ok=True)
for url in files:
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    target_path = os.path.join(args.target, filename)

    if os.path.exists(target_path):
        continue

    print('Download', url)
    response: bytes = urlopen(Request(url, headers=headers)).read()
    length = len(response)
    with open(target_path, 'wb') as f:
        i = 0
        while i < length:
            count = f.write(response)
            i += count
            response = response[count:]
