#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import sys

import requests

from olx import BASE_URL
from scrapper_helpers.utils import caching, get_random_user_agent, key_sha1, replace_all

if sys.version_info < (3, 2):
    from urllib import quote
else:
    from urllib.parse import quote

POLISH_CHARACTERS_MAPPING = {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z"}

log = logging.getLogger(__file__)


def city_name(city):
    """ Creates valid OLX url city name

    OLX city name can't include polish characters, upper case letters.
    It also should replace white spaces with dashes.

    :param city: City name not in OLX url format
    :type city: str
    :return: Valid OLX url city name
    :rtype: str

    :Example:

    >> city_name("Ruda Śląska")
    "ruda-slaska"
    """
    output = replace_all(city.lower(), POLISH_CHARACTERS_MAPPING).replace(" ", "-")
    if sys.version_info < (3, 3):
        return output.encode('utf-8')
    else:
        return output


def get_search_filter(filter_name, filter_value):
    """ Generates url search filter

    :param filter_name: Filter name in OLX format. See :meth:'olx.get_category' for reference
    :param filter_value: Correct value for filter
    :type filter_name: str
    :return: Percent-encoded url search filter
    :rtype str

    :Example:

    >> get_search_filter([filter_float_price:from], 2000)
    "search%5Bfilter_float_price%3Afrom%5D=2000"
    """
    if "rooms" in filter_name:
        numbers = {1: "one", 2: "two", 3: "three", 4: "four"}
        value = numbers.get(filter_value, "one")
    elif "furniture" in filter_name:
        value = ('yes' if filter_value else 'no')
    elif "floor" in filter_name:
        value = "floor_{0}".format(11 if filter_value > 10 and filter_value != 17 else str(filter_value))
    elif "builttype" in filter_name:
        available = ["blok", "kamienica", "szeregowiec", "apartamentowiec", "wolnostojacy", "loft"]
        if filter_value in available:
            value = filter_value
        else:
            log.warning("This built type isn't available")
            pass
    else:
        value = filter_value
    output = "{0}={1}".format(quote("search{0}".format(filter_name, value)), value)
    return output


def get_url(main_category=None, sub_category=None, detail_category=None, region=None, search_query=None, page=None,
            user_url=None, **filters):
    """ Creates url for given parameters

    :param user_url: User defined OLX search url
    :param main_category: Main category
    :param sub_category: Sub category
    :param detail_category: Detail category
    :param region: Region of search
    :param search_query: Search query string
    :param page: Page number
    :param filters: Dictionary with additional filters. See :meth:'olx.get_category' for reference
    :type main_category: str, None
    :type sub_category: str, None
    :type detail_category: str, None
    :type region: str, None
    :type search_query: str
    :type page: int, None
    :type filters: dict
    :return: Url for given parameters
    :rtype: str
    """
    if page == 0:
        page = None
    parameters = list(filter(None, [BASE_URL, main_category, sub_category, detail_category, region,
                                    "q-{0}".format(search_query.replace(" ", "-")) if search_query else None, "?"]))
    # When just query string is given - url needs to contain olx.pl/ofery/search_query
    if len(parameters) == 3 and search_query is not None:
        url = "{0}/oferty/q-{1}".format(BASE_URL, search_query.replace(" ", "-"))
    else:
        url = "/".join(parameters)
    if user_url:
        url = user_url + "?" if "search" not in user_url else user_url + "&"
    for k, v in filters.items():
        url += get_search_filter(k, v) + "&"
    if page is not None:
        url += "page={0}".format(page)
    return url


@caching(key_func=key_sha1)
def get_content_for_url(url):
    """ Connects with given url

    If environmental variable DEBUG is True it will cache response for url in /var/temp directory

    :param url: Website url
    :type url: str
    :return: Response for requested url
    """
    response = requests.get(url, headers={'User-Agent': get_random_user_agent()})
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        log.warning('Request for {0} failed. Error: {1}'.format(url, e))
        return None
    return response
