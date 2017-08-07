#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

from olx.category import get_category, get_offers_for_page
from olx.offer import get_descriptions

log = logging.getLogger(__file__)

if __name__ == '__main__':
    search_filters = {
        "[filter_float_price:from]": 1000
    }
    parsed_urls = get_category("nieruchomosci", "mieszkania", "wynajem", "Gdańsk", **search_filters)[:3]
    parsed_urls[1] = "https://www.olx.pl/oferta/komfortowe-3-pokoje-wejherowska-CID3-IDnO0LV.html#04fc6b796b"
    descriptions = get_descriptions(parsed_urls)
    for element in descriptions:
        print()
        print(element)
