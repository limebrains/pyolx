#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

from olx import BASE_URL
from olx.category import get_category
from olx.offer import parse_offer

log = logging.getLogger(__file__)

if __name__ == '__main__':
    search_filters = {
        "[filter_float_price:from]": 2000
    }
    # parsed_urls = get_category(url="https://www.olx.pl/sopot/q-imac/",**search_filters)[:10]
    parsed_urls = get_category("nieruchomosci", "mieszkania", "wynajem", "Gdańsk", **search_filters)[:3]
    for element in (parse_offer(url) for url in parsed_urls if url and BASE_URL in url):
        print()
        print(element)
