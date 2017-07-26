#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import logging
import re

from bs4 import BeautifulSoup

from olx.utils import get_content_for_url

try:
    from __builtin__ import unicode
except ImportError:
    unicode = lambda x, *args: x

log = logging.getLogger(__file__)


def get_title(offer_markup):
    """ Searches for offer title on offer page

    :param offer_markup: Class "offerbody" from offer page markup
    :type offer_markup: str
    :return: Title of offer
    :rtype: str
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    return html_parser.h1.text.replace("\n", "").replace("  ", "")


def get_price(offer_markup):
    """ Searches for price on offer page

    Assumes price is in PLN

    :param offer_markup: Class "offerbody" from offer page markup
    :type offer_markup: str
    :return: Price
    :rtype: int
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    price = html_parser.find(class_="xxxx-large").text
    output = ""
    for char in price:
        if char.isdigit():
            output += char
    return int(output)


def get_surface(offer_markup):
    """ Searches for surface in offer markup

    :param offer_markup: Class "offerbody" from offer page markup
    :type offer_markup: str
    :return: Surface
    :rtype: float

    :except: When there is no offer surface it will return None
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    try:
        surface = html_parser.sup.parent.text
    except AttributeError as e:
        log.debug(e)
        return None
    return float(surface.replace(" m2", "").replace("\t", "").replace("\n", "").replace(",", "."))


def parse_description(offer_markup):
    """ Searches for description if offer markup

    :param offer_markup: Body from offer page markup
    :type offer_markup: str
    :return: Description of offer
    :rtype: str
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    return html_parser.find(id="textContent").text.replace("  ", "").replace("\n", " ").replace("\r", "")


def get_img_url(offer_markup):
    """ Searches for images in offer markup

    :param offer_markup: Class "offerbody" from offer page markup
    :type offer_markup: str
    :return: Images of offer in list
    :rtype: list
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    images = html_parser.find_all(class_="bigImage")
    output = []
    for img in images:
        output.append(img.attrs["src"])
    return output


def get_date_added(offer_markup):
    """ Searches of date of adding offer

    :param offer_markup: Class "offerbody" from offer page markup
    :type offer_markup: str
    :return: Date of adding offer
    :rtype: str
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    date = html_parser.find(class_="offer-titlebox__details").em.contents
    if len(date) > 4:
        date = date[4]
    else:
        date = date[0]
    return date.replace("Dodane", "").replace("\n", "").replace("  ", "").replace("o ", "").replace(", ", " ")


def parse_flat_data(offer_markup):
    """ Parses flat data from script of Google Tag Manager

    Data includes if offer private or business, number of floor, number of rooms, built type and furniture.

    :param offer_markup: Body from offer page markup
    :type offer_markup: str
    :return: Dictionary of flat data
    :rtype: dict
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    scripts = html_parser.find_all('script')
    for script in scripts:
        if "GPT.targeting" in script.string:
            data = script.string
            break
    data_dict = json.loads((re.split('GPT.targeting = |;', data))[3].replace(";", ""))
    translate = {"one": 1, "two": 2, "three": 3, "four": 4}
    rooms = data_dict.get("rooms", None)
    if rooms is not None:
        rooms = translate[rooms[0]]
    return {
        "private_business": data_dict.get("private_business", None),
        "floor": int(data_dict.get("floor_select", [None])[0].replace("floor_", "")),
        "rooms": rooms,
        "builttype": data_dict.get("builttype", [None])[0],
        "furniture": data_dict.get("furniture", [None])[0] == 'yes'
    }


def parse_offer(markup, url):
    """ Parses data from offer page markup

    :param markup: Offer page markup
    :param url: Url of current offer page
    :type markup: str
    :type url: str
    :return: Dictionary with all offer details
    :rtype: dict
    """
    html_parser = BeautifulSoup(markup, "html.parser")
    offer_content = str(html_parser.body)
    offer_data = parse_flat_data(offer_content)
    offer_content = str(html_parser.find(class_='offerbody'))
    data_keys = list(offer_data.keys())
    data_values = list(offer_data.values())
    return {
        "title": get_title(offer_content),
        "price": get_price(offer_content),
        "surface": get_surface(offer_content),
        # **offer_data,
        data_keys[0]: data_values[0],
        data_keys[1]: data_values[1],
        data_keys[2]: data_values[2],
        data_keys[3]: data_values[3],
        data_keys[4]: data_values[4],
        "description": parse_description(offer_content),
        "url": url,
        "date": get_date_added(offer_content),
        "images": get_img_url(offer_content)
    }


def get_descriptions(parsed_urls):
    """ Parses details of categories

    :param parsed_urls: List of offers urls
    :type parsed_urls: list
    :return: List of details of offers
    :rtype: list
    """
    descriptions = []
    for url in parsed_urls:
        response = get_content_for_url(url)
        try:
            descriptions.append(parse_offer(response.content, url))
        except AttributeError as e:
            log.info("This offer is not available anymore.")
            log.debug("Error: {0}".format(e))
    return descriptions
