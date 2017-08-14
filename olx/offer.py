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
    :rtype: str, None
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    return html_parser.h1.text.strip()


def parse_tracking_data(offer_markup):
    """ Parses price and add_id from OLX tracking data script

    :param offer_markup: Head from offer page
    :type offer_markup: str
    :return: Tuple of int price and it's currency or None if this offer page got deleted
    :rtype: tuple, None

    :except: This offer page got deleted and has no tracking script.
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    try:
        script = html_parser.find('script').next_sibling.next_sibling.next_sibling.text
    except AttributeError:
        return
    data_dict = json.loads(re.split("pageView|;", script)[3].replace('":{', "{").replace("}}'", "}"))
    return int(data_dict.get("ad_price", 0)), data_dict.get("price_currency"), data_dict["ad_id"]


def get_additional_rent(offer_markup):
    """ Searches for additional rental costs

    :param offer_markup:
    :type offer_markup: str
    :return: Additional rent
    :rtype: int
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    table = html_parser.find_all(class_="item")
    for element in table:
        if "Czynsz" in element.text:
            return int(("".join(re.findall(r'\d+', element.text))))
    return


def get_gps(offer_markup):
    """ Searches for gps coordinates (latitude and longitude)

    :param offer_markup: Class "offerbody" from offer page markup
    :type offer_markup: str
    :return: Tuple of gps coordinates
    :rtype: tuple
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    gps_lat = html_parser.find(class_="mapcontainer").attrs['data-lat']
    gps_lon = html_parser.find(class_="mapcontainer").attrs['data-lon']
    return gps_lat, gps_lon


def get_poster_name(offer_markup):
    """ Searches for poster name

    :param offer_markup: Class "offerbody" from offer page markup
    :type offer_markup: str
    :return: Poster name or None if poster name was not found (offer is outdated)
    :rtype: str, None

    :except: Poster name not found
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    try:
        return html_parser.find(class_="offer-user__details").a.text.strip()
    except AttributeError:
        return


def get_surface(offer_markup):
    """ Searches for surface in offer markup

    :param offer_markup: Class "offerbody" from offer page markup
    :type offer_markup: str
    :return: Surface or None if there is no surface
    :rtype: float, None

    :except: When there is no offer surface it will return None
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    try:
        surface = html_parser.sup.parent.text
    except AttributeError:
        return
    return float(surface.replace("m2", "").strip().replace(",", ".").replace(" ", "")) if "m2" in surface else None


def parse_description(offer_markup):
    """ Searches for description if offer markup

    :param offer_markup: Body from offer page markup
    :type offer_markup: str
    :return: Description of offer
    :rtype: str
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    return html_parser.find(id="textContent").text.replace("  ", "").replace("\n", " ").replace("\r", "").strip()


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
    date = date[4] if len(date) > 4 else date[0]
    return date.replace("Dodane", "").replace("\n", "").replace("  ", "").replace("o ", "").replace(", ", " ")


def parse_region(offer_markup):
    """ Parses region information

    :param offer_markup: Class "offerbody" from offer page markup
    :type offer_markup: str
    :return: Region of offer
    :rtype: list
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    region = html_parser.find(class_="show-map-link").text
    return region.replace(", ", ",").split(",")


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
    try:
        data_dict = json.loads((re.split('GPT.targeting = |;', data))[3].replace(";", ""))
    except json.JSONDecodeError as e:
        logging.info("JSON failed to parse GPT offer attributes. Error: {0}".format(e))
        return {}
    translate = {"one": 1, "two": 2, "three": 3, "four": 4}
    rooms = data_dict.get("rooms", None)
    if rooms is not None:
        rooms = translate[rooms[0]]
    floor = data_dict.get("floor_select", [None])[0]
    if floor is not None:
        floor = int(floor.replace("floor_", ""))
    return {
        "private_business": data_dict.get("private_business", None),
        "floor": floor,
        "rooms": rooms,
        "built_type": data_dict.get("builttype", [None])[0],
        "furniture": data_dict.get("furniture", [None])[0] == 'yes'
    }


def parse_offer(url):
    """ Parses data from offer page url

    :param url: Offer page markup
    :param url: Url of current offer page
    :type url: str
    :return: Dictionary with all offer details or None if offer is not available anymore
    :rtype: dict, None
    """
    log.info(url)
    response = get_content_for_url(url)
    html_parser = BeautifulSoup(response.content, "html.parser")
    offer_tracking_data = parse_tracking_data(str(html_parser.head))
    if offer_tracking_data is None:
        log.info("Offer {0} is not available anymore.".format(url))
        return
    offer_content = str(html_parser.body)
    offer_data = parse_flat_data(offer_content)
    gps_coordinates = get_gps(offer_content)
    offer_content = str(html_parser.find(class_='offerbody'))
    poster_name = get_poster_name(offer_content)
    if poster_name is None:
        return
    region = parse_region(offer_content)
    district = region[2] if len(region) == 3 else None
    return {
        "title": get_title(offer_content),
        "add_id": offer_tracking_data[2],
        "price": offer_tracking_data[0] if offer_tracking_data[0] != 0 else None,
        "additional_rent": get_additional_rent(offer_content),
        "currency": offer_tracking_data[1],
        "city": region[0],
        "district": district,
        "voivodeship": region[1],
        "gps": gps_coordinates,
        "surface": get_surface(offer_content),
        # **offer_data,
        "private_business": offer_data.get("private_business"),
        "floor": offer_data.get("floor"),
        "rooms": offer_data.get("rooms"),
        "built_type": offer_data.get("built_type"),
        "furniture": offer_data.get("furniture"),
        "description": parse_description(offer_content),
        "poster_name": poster_name,
        "url": url,
        "date": get_date_added(offer_content),
        "images": get_img_url(offer_content)
    }


def get_descriptions(parsed_urls):
    """ Parses details of offers in category

    :param parsed_urls: List of offers urls
    :type parsed_urls: list
    :return: List of details of offers
    :rtype: list

    :except: If this offer is not available anymore
    """
    descriptions = []
    for url in parsed_urls:
        if url is None:
            continue
        current_offer = parse_offer(url)
        if current_offer is not None:
            descriptions.append(current_offer)
    return descriptions
