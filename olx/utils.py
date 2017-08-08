#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import sys

import requests
from scrapper_helpers.utils import caching, key_sha1, replace_all

from olx import BASE_URL

if sys.version_info < (3, 2):
    from urllib import quote
else:
    from urllib.parse import quote

POLISH_CHARACTERS_MAPPING = {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z"}

log = logging.getLogger(__file__)


def flatten(container):
    """ Flatten a list

    :param container: list with nested lists
    :type container: list
    :return: list with elements that were nested in container
    :rtype: list
    """
    for i in container:
        if isinstance(i, (list, tuple)):
            for j in flatten(i):
                yield j
        else:
            yield i


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


def get_url(main_category, sub_category, detail_category, region, page=None, **filters):
    """ Creates url for given parameters

    :param main_category: Main category
    :param sub_category: Sub category
    :param detail_category: Detail category
    :param region: Region of search
    :param page: Page number
    :param filters: Dictionary with additional filters. See :meth:'olx.get_category' for reference
    :type main_category: str
    :type sub_category: str
    :type detail_category: str
    :type region: str
    :type page: int
    :type filters: dict
    :return: Url for given parameters
    :rtype: str
    """
    if page == 0:
        page = None
    url = "/".join([BASE_URL, main_category, sub_category, detail_category, region, "?"])
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
    response = requests.get(url, allow_redirects=False)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        log.warning('Request for {0} failed. Error: {1}'.format(url, e))
        return None
    return response
