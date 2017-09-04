#!/usr/bin/python
# -*- coding: utf-8 -*-
import datetime as dt
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
        return None, None, None
    data_dict = json.loads(re.split("pageView|;", script)[3].replace('":{', "{").replace("}}'", "}"))
    return int(data_dict.get("ad_price", 0)) or None, data_dict.get("price_currency"), data_dict["ad_id"]


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
    poster_name_parser = BeautifulSoup(offer_markup, "html.parser").find(class_="offer-user__details")
    try:
        if poster_name_parser.a is not None:
            found_name = poster_name_parser.a.text.strip()
        else:
            found_name = poster_name_parser.h4.text.strip()
    except AttributeError:
        return
    return found_name


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


def get_month_num_for_string(value):
    value = value.lower()[:3]
    return {
        'sty': 1,
        'lut': 2,
        'mar': 3,
        'kwi': 4,
        'maj': 5,
        'cze': 6,
        'lip': 7,
        'sie': 8,
        'wrz': 9,
        'paź': 10,
        'lis': 11,
        'gru': 12,
    }.get(value)


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
    date = date.replace("Dodane", "").replace("\n", "").replace("  ", "").replace("o ", "").replace(", ", " ")
    # 10:09 04 września 2017
    date_parts = date.split(' ')
    hour, minute = map(int, date_parts[0].split(':'))
    month = get_month_num_for_string(date_parts[2])
    year = int(date_parts[3])
    day = int(date_parts[1])
    date_added = dt.datetime(year=year, hour=hour, minute=minute, day=day, month=month)
    return int((date_added - dt.datetime(1970, 1, 1)).total_seconds())


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


def get_gpt_script(offer_markup):
    """ Parses data from script of Google Tag Manager

    :param offer_markup: Body from offer page markup
    :type offer_markup: str
    :return: GPT dict data
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
        data_dict = {}
    return data_dict


def parse_flat_data(offer_markup, data_dict):
    """ Parses flat data

    Data includes if offer private or business, number of floor, number of rooms, built type and furniture.

    :param offer_markup: Body from offer page markup
    :param data_dict: Dict with GPT script data
    :type offer_markup: str
    :type data_dict: dict
    :return: Dictionary of flat data
    :rtype: dict
    """

    translate = {"one": 1, "two": 2, "three": 3, "four": 4}
    rooms = data_dict.get("rooms")
    if rooms is not None:
        rooms = translate[rooms[0]]
    floor = data_dict.get("floor_select", [None])[0]
    if floor is not None:
        floor = int(floor.replace("floor_", ""))
    return {
        "floor": floor,
        "rooms": rooms,
        "built_type": data_dict.get("builttype", [None])[0],
        "furniture": data_dict.get("furniture", [None])[0] == 'yes',
        "surface": get_surface(offer_markup),
        "additional_rent": get_additional_rent(offer_markup),
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
    html_parser = BeautifulSoup(get_content_for_url(url).content, "html.parser")
    offer_content = str(html_parser.body)
    poster_name = get_poster_name(offer_content)
    price, currency, add_id = parse_tracking_data(str(html_parser.head))
    if not all([add_id, poster_name]):
        log.info("Offer {0} is not available anymore.".format(url))
        return
    region = parse_region(offer_content)
    if len(region) == 3:
        city, voivodeship, district = region
    else:
        city, voivodeship = region
        district = None
    data_dict = get_gpt_script(offer_content)
    result = {
        "title": get_title(offer_content),
        "add_id": add_id,
        "price": price,
        "currency": currency,
        "city": city,
        "district": district,
        "voivodeship": voivodeship,
        "gps": get_gps(offer_content),
        "description": parse_description(offer_content),
        "poster_name": poster_name,
        "url": url,
        "date_added": get_date_added(offer_content),
        "images": get_img_url(offer_content),
        "private_business": data_dict.get("private_business"),
    }
    flat_data = parse_flat_data(offer_content, data_dict)
    if flat_data and any(flat_data.values()):
        result.update(flat_data)
    return result
