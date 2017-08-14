#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import sys

from bs4 import BeautifulSoup

from olx import OFFERS_FEATURED_PER_PAGE, WHITELISTED_DOMAINS
from olx.utils import city_name, get_content_for_url, get_url
from scrapper_helpers.utils import flatten

if sys.version_info < (3, 3):
    from urlparse import urlparse
else:
    from urllib.parse import urlparse

log = logging.getLogger(__file__)
logging.basicConfig(level=logging.DEBUG)


def get_page_count(markup):
    """ Reads total page number from OLX search page

    :param markup: OLX search page markup
    :type markup: str
    :return: Total page number extracted from js script
    :rtype: int
    """
    html_parser = BeautifulSoup(markup, "html.parser")
    script = html_parser.head.script.next_sibling.next_sibling.next_sibling.text.split(",")
    for element in script:
        if "page_count" in element:
            current = element.split(":")
            out = ""
            for char in current[len(current) - 1]:
                if char.isdigit():
                    out += char
            return int(out)
    log.warning("Error no page number found. Please check if it's valid olx page.")
    return 1


def get_page_count_for_filters(main_category, sub_category, detail_category, region, **filters):
    """ Reads total page number for given search filters

    :param main_category: Main category
    :param sub_category: Sub category
    :param detail_category: Detail category
    :param region: Region of search
    :param filters: See :meth category.get_category for reference
    :type main_category: str
    :type sub_category: str
    :type detail_category: str
    :type region: str
    :return: Total page number
    :rtype: int
    """
    url = get_url(main_category, sub_category, detail_category, region, **filters)
    response = get_content_for_url(url)
    html_parser = BeautifulSoup(response.content, "html.parser")
    script = html_parser.head.script.next_sibling.next_sibling.next_sibling.text.split(",")
    for element in script:
        if "page_count" in element:
            current = element.split(":")
            out = ""
            for char in current[len(current) - 1]:
                if char.isdigit():
                    out += char
            return int(out)
    log.warning("Error no page number found. Please check if it's valid olx page.")
    return 1


def parse_offer_url(markup):
    """ Searches for offer links in markup

    Offer links on OLX are in class "linkWithHash".
    Only www.olx.pl domain is whitelisted.

    :param markup: Search page markup
    :type markup: str
    :return: Url with offer
    :rtype: str
    """
    html_parser = BeautifulSoup(markup, "html.parser")
    url = html_parser.find(class_="linkWithHash").attrs['href']
    if not url or urlparse(url).hostname not in WHITELISTED_DOMAINS:
        return
    return url


def parse_available_offers(markup):
    """ Collects all offer links on search page markup

    :param markup: Search page markup
    :type markup: str
    :return: Links to offer on given search page
    :rtype: list
    """
    html_parser = BeautifulSoup(markup, "html.parser")
    not_found = html_parser.find(class_="emptynew")
    if not_found is not None:
        log.warning("No offers found")
        return
    offers = html_parser.find_all(class_='offer')
    parsed_offers = [parse_offer_url(str(offer)) for offer in offers if offer][OFFERS_FEATURED_PER_PAGE:]
    return parsed_offers


def get_category(main_category=None, sub_category=None, detail_category=None, region=None,
                 search_query=None, user_url=None, **filters):
    """ Parses available offer urls from given category from every page

    :param user_url: User defined url for OLX page with offers. It overrides rest of search filers.
    :param main_category: Main category
    :param sub_category: Sub category
    :param detail_category: Detail category
    :param region: Region of search
    :param search_query: Additional search query
    :param filters: Dictionary with additional filters. Following example dictionary contains every possible filter
    with examples of it's values.

    :Example:

    input_dict = {
        "[filter_float_price:from]": 2000, # minimal price
        "[filter_float_price:to]": 3000, # maximal price
        "[filter_enum_floor_select][0]": 3, # desired floor, enum: from -1 to 11 (10 and more) and 17 (attic)
        "[filter_enum_furniture][0]": True, # furnished or unfurnished offer
        "[filter_enum_builttype][0]": "blok", # valid build types:
        #                                             blok, kamienica, szeregowiec, apartamentowiec, wolnostojacy, loft
        "[filter_float_m:from]": 25, # minimal surface
        "[filter_float_m:to]": 50, # maximal surface
        "[filter_enum_rooms][0]": 2 # desired number of rooms, enum: from 1 to 4 (4 and more)
    }

    :type user_url: str
    :type main_category: str
    :type sub_category: str
    :type detail_category: str
    :type region: str
    :type search_query: str
    :type filters: dict
    :return: List of all offers for given parameters
    :rtype: list
    """
    parsed_content, page = [], None
    city = city_name(region) if region else None
    if user_url is None:
        url = get_url(main_category, sub_category, detail_category, city, search_query, **filters)
    else:
        url = user_url
    response = get_content_for_url(url)
    page_max = get_page_count(response.content)
    while page is None or page <= page_max:
        if page is not None:
            if user_url is None:
                url = get_url(main_category, sub_category, detail_category, city, search_query, page, **filters)
            else:
                url = user_url + "&page={0}".format(page)
        log.debug(url)
        response = get_content_for_url(url)
        if response.status_code > 300:
            break
        log.info("Loaded page {0} of offers".format(page))
        offers = parse_available_offers(response.content)
        if offers is None:
            break
        parsed_content.append(offers)
        if page is None:
            page = 1
        page += 1
    parsed_content = list(flatten(parsed_content))
    log.info("Loaded {0} offers".format(str(len(parsed_content))))
    return parsed_content


def get_offers_for_page(main_category, sub_category, detail_category, region, page, **filters):
    """ Parses offers for one specific page of given category with filters.

    :param main_category: Main category
    :param sub_category: Sub category
    :param detail_category: Detail category
    :param region: Region of search
    :param page: Page number
    :param filters: See :meth category.get_category for reference
    :type main_category: str
    :type sub_category: str
    :type detail_category: str
    :type region: str
    :type page: int
    :type filters: dict
    :return: List of all offers for given page and parameters
    :rtype: list
    """
    city = city_name(region)
    url = get_url(main_category, sub_category, detail_category, city, page=page, **filters)
    response = get_content_for_url(url)
    log.info("Loaded page {0} of offers".format(page))
    offers = parse_available_offers(response.content)
    log.info("Loaded {0} offers".format(str(len(offers))))
    return offers
