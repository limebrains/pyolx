# python modules
import json
import re
from urllib.parse import urlparse
import logging
import os

# third party
import requests
from bs4 import BeautifulSoup

# own modules
from scrapper_helpers.utils import caching

BASE_URL = 'https://www.olx.pl/'
OFFERS_FEATURED_PER_PAGE = 3
POLISH_CHARACTERS_MAPPING = {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z"}
DEBUG = os.environ.get('DEBUG')
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

log = logging.getLogger(__file__)

WHITELISTED_DOMAINS = [
    'olx.pl',
    'www.olx.pl',
]


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


def replace_all(text, input_dict):
    """ Replace specific strings in string

    :param text: string with strings to be replaced
    :param input_dict: dictionary with elements in format string: string to be replaced with
    :type text: str
    :type input_dict: dict
    :return: String with replaced strings
    :rtype: str
    """
    for i, j in input_dict.items():
        text = text.replace(i, j)
    return text


def city_name(city):
    """ Creates valid oxl url city name

    Olx city name can't include polish characters, upper case letters.
    It also should replace white spaces with dashes.

    :param city: City name not in olx url format
    :type city: str
    :return: Valid olx url city name
    :rtype: str

    :Example:

    city_name("Ruda Śląska") >> "ruda-slaska"
    """
    return replace_all(city.lower(), POLISH_CHARACTERS_MAPPING).replace(" ", "-")


def url_price_from(price):
    """ Generates olx search filter for minimal price

    :param price: Minimal price for filter offers
    :type price: int
    :return: Olx url search filter for minimal price
    :rtype: str
    """
    return "search%5Bfilter_float_price%3Afrom%5D={0}".format(str(price))


def url_price_to(price):
    """ Generates olx search filter for maximal price

    :param price: Maximal price for filter offers
    :type price: int
    :return: Olx url search filter for maximal price
    :rtype: str
    """
    return "search%5Bfilter_float_price%3Ato%5D={0}".format(str(price))


def url_rooms(number):
    """ Generates olx search filter for number of rooms

    Number of rooms can be in range 1 to 4.
    4 means "4 and more"

    :param number: Number of rooms
    :type number: int
    :return: Olx url search filer for number of rooms
    :rtype: str
    """
    numbers = {1: "one", 2: "two", 3: "three", 4: "four"}
    return "search%5Bfilter_enum_rooms%5D%5B0%5D={0}".format(numbers.get(number, "four"))


def url_surface_from(minimum):
    """ Generates olx search filter for minimal surface

    :param minimum: Minimal surface
    :type minimum: int
    :return: Olx url search filter for minimal surface
    :rtype: str
    """
    return "search%5Bfilter_float_m%3Afrom%5D={0}".format(str(minimum))


def url_surface_to(maximum):
    """ Generates olx search filter for maximal surface

    :param maximum: Maximal surface
    :type maximum: int
    :return: Olx url search filter for maximal surface
    :rtype: str
    """
    return "search%5Bfilter_float_m%3Ato%5D={0}".format(str(maximum))


def url_furniture(furniture):
    """ Generates olx search filter for either furnished or unfurnished offer

    :param furniture: Search for furnished or unfurnished offers
    :type furniture: bool
    :return: Olx url search filter
    :rtype: str
    """
    return "search%5Bfilter_enum_furniture%5D%5B0%5D={0}".format('yes' if furniture else 'no')


def url_floor(floor):
    """ Generates olx search filter for desired floor of offer

    Floor number can range from -1 to 11 and 17
    -1 means basement
    0 means ground floor
    11 means "10 and more"
    17 means attic

    :param floor: Desired offer floor
    :type floor: int
    :return: Olx url search filter for floor
    :rtype: str
    """
    floor_id = 11 if floor > 10 and floor != 17 else str(floor)
    return "search%5Bfilter_enum_floor_select%5D%5B0%5D=floor_{0}".format(floor_id)


def url_builttype(builttype):
    """ Generates olx search filter for built type

    :param builttype: Built type of offers
    :type builttype: str
    :return: Olx url search filter for built type
    """
    available = ["blok", "kamienica", "szeregowiec", "apartamentowiec", "wolnostojacy", "loft"]
    if builttype in available:
        return "search%5Bfilter_enum_builttype%5D%5B0%5D={0}".format(builttype)
    log.warning("This built type isn't available")


def get_url(page=None, *args):
    """ Creates olx url for category and search parameters

    :param page: page number in format "page=2"
    :type page: str
    :param args: Additional search parameters
    :return: Olx search url
    :rtype: str
    """
    url = BASE_URL
    for element in args:
        if element is not None:
            if "filter" in url and "filter" in element:
                url += element + "&"
            elif "filter" in element:
                if page is not None:
                    url += "?" + page + "&" + element + "&"
                else:
                    url += "?" + element + "&"
            else:
                url += element + "/"
    if "page" not in url:
        if page is not None:
            url += "?" + page
    return url


def get_page_count(markup):
    """ Reads page number from olx search page

    :param markup: Olx search page markup
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


# TODO: Caching for long urls
@caching
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
        log.warning('Request for {0} failed. Error: '.format(url, e))
        return None
    return response


def parse_offer_url(markup):
    """ Searches for offer links in markup

    Offer links on olx are in class "linkWithHash".
    Only olx.pl domain is whitelisted.

    :param markup: Search page markup
    :return: Url with offer
    :rtype: str
    """
    html_parser = BeautifulSoup(markup, "html.parser")
    url = html_parser.find(class_="linkWithHash").attrs['href']
    if not url or urlparse(url).hostname not in WHITELISTED_DOMAINS:
        # detail url is not present or not supported
        return None
    return url


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
    return html_parser.find(id="textContent").text.replace("  ", "").replace("\n", "").replace("\r", "")


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
    floor_number = ""
    floor = data_dict.get("floor_select", None)
    furniture = data_dict.get("furniture", None)
    built_type = data_dict.get("builttype", None)
    rooms = data_dict.get("rooms", None)
    if floor is not None:
        for char in data_dict.get("floor_select", None)[0]:
            if char.isdigit():
                floor_number += char
        floor = int(floor_number)
    if furniture is not None:
        if furniture[0] == "yes":
            furniture = True
        else:
            furniture = False
    if rooms is not None:
        rooms = translate[rooms[0]]
    if built_type is not None:
        built_type = built_type[0]
    return {
        "private_business": data_dict.get("private_business", None),
        "floor": floor,
        "rooms": rooms,
        "builttype": built_type,
        "furniture": furniture
    }


def parse_available_offers(markup):
    """ Collects all offer links on search page markup

    :param markup: Search page markup
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
    offer_content = html_parser.body
    offer_data = parse_flat_data(str(offer_content))
    offer_content = html_parser.find(class_='offerbody')
    return {
        "title": get_title(str(offer_content)),
        "price": get_price(str(offer_content)),
        "surface": get_surface(str(offer_content)),
        **offer_data,
        "description": parse_description(str(offer_content)),
        "url": url,
        "date": get_date_added(str(offer_content)),
        "images": get_img_url(str(offer_content))
    }


def get_category(main_category, subcategory, detail_category, region, *args):
    """ Parses all offers pages in given category

    :param main_category: Main category
    :param subcategory: Sub category
    :param detail_category: Detail category
    :param region: Region
    :param args: Additional search filters
    :return: List of all offer urls for category
    :rtype: list
    """
    parsed_content = []
    page = 1
    url = get_url(None, main_category, subcategory, detail_category, region, *args)
    response = get_content_for_url(url)
    page_max = get_page_count(response.content)
    page_attr = None
    while page <= page_max:
        url = get_url(page_attr, main_category, subcategory, detail_category, region, *args)
        log.debug(url)
        response = get_content_for_url(url)
        if response.status_code > 300:
            break
        log.info("Loaded page {0} of offers".format(page))
        offers = parse_available_offers(response.content)
        if offers is None:
            break
        parsed_content.append(offers)
        page += 1
        page_attr = "page={0}".format(page)
    parsed_content = list(flatten(parsed_content))
    log.info("Loaded {0} offers".format(str(len(parsed_content))))
    return parsed_content


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
            log.warning("This offer is not available anymore. Error: {0}".format(e))
    return descriptions


if __name__ == '__main__':
    city = city_name("Gdańsk")
    price_from = url_price_from(1000)
    price_to = url_price_to(3000)
    furniture = url_furniture(True)
    built_type = url_builttype("blok")
    rooms = url_rooms(3)
    surface_min = url_surface_from(100)
    surface_max = url_surface_to(40)
    floor = url_floor(4)
    parsed_urls = get_category("nieruchomosci", "mieszkania", "wynajem", city)[:3]
    # parsed_urls = get_category("nieruchomosci", "mieszkania", "wynajem", city, price_from, price_to, built_type, rooms)
    descriptions = get_descriptions(parsed_urls)
    for element in descriptions:
        log.info("\n")
        # json dumps doesn't work with polish chars
        # log.info(json.dumps(element))
        print(element)
