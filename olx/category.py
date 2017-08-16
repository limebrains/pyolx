#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import logging
import re

from bs4 import BeautifulSoup

from olx.utils import city_name, get_content_for_url, get_url
from scrapper_helpers.utils import flatten

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


def get_page_count_for_filters(main_category=None, sub_category=None, detail_category=None, region=None,
                               search_query=None, url=None, **filters):
    """ Reads total page number for given search filters

    :param url: User defined url for OLX page with offers. It overrides category parameters and applies search filters.
    :param main_category: Main category
    :param sub_category: Sub category
    :param detail_category: Detail category
    :param region: Region of search
    :param search_query: Additional search query
    :param filters: See :meth category.get_category for reference
    :type url: str, None
    :type main_category: str, None
    :type sub_category: str, None
    :type detail_category: str, None
    :type region: str, None
    :type search_query: str, None
    :return: Total page number
    :rtype: int
    """
    city = city_name(region) if region else None
    if url is None:
        url = get_url(main_category, sub_category, detail_category, city, search_query, **filters)
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


def parse_ads_count(markup):
    """ Reads total number of adds

    :param markup: OLX search page markup
    :type markup: str
    :return: Total ads count from script
    :rtype: int
    """
    html_parser = BeautifulSoup(markup, "html.parser")
    scripts = html_parser.find_all('script')
    for script in scripts:
        try:
            if "GPT.targeting" in script.string:
                data = script.string
                break
        except TypeError:
            continue
    try:
        data_dict = json.loads((re.split('GPT.targeting = |;', data))[3].replace(";", ""))
    except json.JSONDecodeError as e:
        logging.info("JSON failed to parse GPT offer attributes. Error: {0}".format(e))
        return 0
    return int(data_dict.get("ads_count"))


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
    url = html_parser.find("a").attrs['href']
    return url if url else None


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
    ads_count = parse_ads_count(markup)
    offers = html_parser.find_all(class_='offer')
    if len(offers) == 0:
        offers = html_parser.select("li.wrap.tleft")
    parsed_offers = [parse_offer_url(str(offer)) for offer in offers if offer][:ads_count]
    return parsed_offers


def get_category(main_category=None, sub_category=None, detail_category=None, region=None, search_query=None, url=None,
                 **filters):
    """ Parses available offer urls from given category from every page

    :param url: User defined url for OLX page with offers. It overrides category parameters and applies search filters.
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

    :type url: str, None
    :type main_category: str, None
    :type sub_category: str, None
    :type detail_category: str, None
    :type region: str, None
    :type search_query: str, None
    :type filters: dict
    :return: List of all offers for given parameters
    :rtype: list
    """
    parsed_content, page, start_url = [], 0, None
    city = city_name(region) if region else None
    if url is None:
        url = get_url(main_category, sub_category, detail_category, city, search_query, **filters)
    else:
        start_url = url
    response = get_content_for_url(url)
    page_max = get_page_count(response.content)
    while page < page_max:
        if start_url is None:
            url = get_url(main_category, sub_category, detail_category, city, search_query, page, **filters)
        else:
            url = get_url(page=page, user_url=start_url, **filters)
        log.debug(url)
        response = get_content_for_url(url)
        log.info("Loaded page {0} of offers".format(page))
        offers = parse_available_offers(response.content)
        if offers is None:
            break
        parsed_content.append(offers)
        page += 1
    parsed_content = list(flatten(parsed_content))
    log.info("Loaded {0} offers".format(str(len(parsed_content))))
    return parsed_content


def get_offers_for_page(page, main_category=None, sub_category=None, detail_category=None, region=None,
                        search_query=None, url=None, **filters):
    """ Parses offers for one specific page of given category with filters.

    :param page: Page number
    :param url: User defined url for OLX page with offers. It overrides category parameters and applies search filters.
    :param main_category: Main category
    :param sub_category: Sub category
    :param detail_category: Detail category
    :param region: Region of search
    :param filters: See :meth category.get_category for reference
    :type page: int
    :type url: str, None
    :type main_category: str, None
    :type sub_category: str, None
    :type detail_category: str, None
    :type region: str, None
    :type search_query: str, None
    :type filters: dict
    :return: List of all offers for given page and parameters
    :rtype: list
    """
    city = city_name(region) if region else None
    if url is None:
        url = get_url(main_category, sub_category, detail_category, city, search_query, page=page, **filters)
    else:
        url = get_url(page=page, user_url=url, **filters)
    response = get_content_for_url(url)
    log.info("Loaded page {0} of offers".format(page))
    offers = parse_available_offers(response.content)
    log.info("Loaded {0} offers".format(str(len(offers))))
    return offers
