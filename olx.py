# python modules
import json
from urllib.parse import urlparse
import logging

# third party
import requests
from bs4 import BeautifulSoup

# own modules
from scrapper_helpers.utils import caching

BASE_URL = 'https://www.olx.pl/'
OFFERS_FEATURED_PER_PAGE = 3
POLISH_CHARACTERS_MAPPING = {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z"}
DEBUG = True
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

log = logging.getLogger(__file__)

WHITELISTED_DOMAINS = [
    'olx.pl',
    'www.olx.pl',
]


def flatten(container):
    for i in container:
        if isinstance(i, (list, tuple)):
            for j in flatten(i):
                yield j
        else:
            yield i


def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text


def city_name(city):
    return replace_all(city.lower(), POLISH_CHARACTERS_MAPPING).replace(" ", "-")


def url_price_from(price):
    return "search%5Bfilter_float_price%3Afrom%5D={0}".format(str(price))


def url_price_to(price):
    return "search%5Bfilter_float_price%3Ato%5D={0}".format(str(price))


def url_rooms(number):
    # 4 and more rooms as 4
    if number > 4:
        number = 4
    numbers = {1: "one", 2: "two", 3: "three", 4: "four"}
    try:
        return "search%5Bfilter_enum_rooms%5D%5B0%5D={0}".format(numbers[number])
    except KeyError:
        log.warning("Incorrect number of rooms")
        pass


def url_yardage_from(minimum):
    return "search%5Bfilter_float_m%3Afrom%5D={0}".format(str(minimum))


def url_yardage_to(maximum):
    return "search%5Bfilter_float_m%3Ato%5D={0}".format(str(maximum))


def url_furniture(furniture):
    if furniture:
        return "search%5Bfilter_enum_furniture%5D%5B0%5D=yes"
    else:
        return "search%5Bfilter_enum_furniture%5D%5B0%5D=no"


def url_floor(floor):
    # 11 means above 10, 17 means "poddasze"
    if floor > 10 and floor != 17:
        floor = 11
    return "search%5Bfilter_enum_floor_select%5D%5B0%5D=floor_{0}".format(str(floor))


def url_builttype(builttype):
    available = ["blok", "kamienica", "szeregowiec", "apartamentowiec", "wolnostojacy", "loft"]
    if builttype in available:
        return "search%5Bfilter_enum_builttype%5D%5B0%5D={0}".format(builttype)
    else:
        log.warning("This built type isn't available")
        pass


def get_url(page=None, *args):
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
    html_parser = BeautifulSoup(markup, "html.parser")
    script = html_parser.head.script.next_sibling.next_sibling.next_sibling.text.split(",")
    for element in script:
        if "page_count" in element:
            tmp = element.split(":")
            out = ""
            for char in tmp[len(tmp) - 1]:
                if char.isdigit():
                    out += char
            return int(out)
    log.warning("Error no page number found. Please check if it's valid olx page.")
    return 0


# TODO: Caching for long urls
@caching
def get_content_for_url(url):
    response = requests.get(url, allow_redirects=False)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        log.warning('Request for {0} failed. Error: '.format(url, e))
        return None
    return response


def parse_offer_url(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    url = html_parser.find(class_="linkWithHash").attrs['href']
    if not url:
        # detail url is not present
        return []
    if urlparse(url).hostname not in WHITELISTED_DOMAINS:
        # domain is not supported by this backend
        return []
    return url


def get_title(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    title = html_parser.h1.text
    return title.replace("\n", "").replace("  ", "")


def get_price(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    price = html_parser.find(class_="xxxx-large").text
    output = ""
    for char in price:
        if char.isdigit():
            output += char
    return int(output)


def get_yardage(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    try:
        yardage = html_parser.sup.parent.text
        return int(yardage.replace("\t", "").replace("\n", "").replace(" m", ""))
    except AttributeError:
        return None


def parse_description(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    description = html_parser.find(class_="large").text
    return description.replace("  ", "").replace("\n", "").replace("\r", "")


def get_img_url(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    img = html_parser.find_all(class_="bigImage")
    output = []
    for element in img:
        output.append(element.attrs["src"])
    return output


def get_date_added(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    date = html_parser.find(class_="offer-titlebox__details").em.contents
    try:
        # If offer has been added from mobile there will be longer date details including information about it so date
        # itself will be on 4th place
        return date[4].replace("Dodane", "").replace("\n", "").replace("  ", "").replace("o ", "").replace(", ", "")
    except IndexError:
        # If offer was added from computer index 4 will raise an exception and function will return index 0 so it's date
        return date[0].replace("Dodane", "").replace("\n", "").replace("  ", "").replace("o ", "").replace(", ", " ")


# parses flat data from google tag manager script
def parse_flat_data(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    data = html_parser.find_all('script')
    output = {"private_business": None, "floor": None, "rooms": None, "furniture": None, "builttype": None}
    for element in data:
        if element.string is not None:
            current = element.string.split()
            for ele in current:
                if "private_business" in ele:
                    tmp = ele.split(",")
                    for i, value in enumerate(tmp):
                        if "private_business" in value and "google" not in value:
                            output["private_business"] = value.split('"')[3]
                        elif "floor_select" in value:
                            floor = value.split('"')
                            floor_number = ""
                            for char in floor[3]:
                                if char.isdigit():
                                    floor_number += char
                            output["floor"] = int(floor_number)
                        elif "rooms" in value:
                            translate = {"one": 1, "two": 2, "three": 3, "four": 4}
                            output["rooms"] = translate[value.split('"')[3]]
                        elif "builttype" in value:
                            output["builttype"] = value.split('"')[3]
                        elif "furniture" in value:
                            if value.split('"')[3] == "yes":
                                output["furniture"] = True
                            else:
                                output["furniture"] = False
    return output


def parse_available_offers(markup):
    html_parser = BeautifulSoup(markup, "html.parser")
    not_found = html_parser.find(class_="emptynew")
    if not_found is not None:
        log.warning("No offers found")
        return
    offers = html_parser.find_all(class_='offer')
    parsed_offers = [parse_offer_url(str(offer)) for offer in offers if offer][OFFERS_FEATURED_PER_PAGE:]
    return parsed_offers


def parse_offer(markup, url):
    html_parser = BeautifulSoup(markup, "html.parser")
    offer_content = html_parser.find(class_='offerbody')
    parsed_title = get_title(str(offer_content))
    parsed_price = get_price(str(offer_content))
    parsed_imgs = get_img_url(str(offer_content))
    parsed_date = get_date_added(str(offer_content))
    parsed_yardage = get_yardage(str(offer_content))
    description = parse_description(str(offer_content))
    offer_content = html_parser.body
    offer_data = parse_flat_data(str(offer_content))
    keys = list(offer_data.keys())
    values = list(offer_data.values())
    return {
        "title": parsed_title,
        "price": parsed_price,
        "yardage": parsed_yardage,
        keys[0]: values[0],
        keys[1]: values[1],
        keys[2]: values[2],
        keys[3]: values[3],
        keys[4]: values[4],
        "description": description,
        "url": url,
        "date": parsed_date,
        "images": parsed_imgs
    }


def get_category(main_category, subcategory, detail_category, region, *args):
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
    log.info("Loaded " + str(len(parsed_content)) + " offers")
    return parsed_content


def get_description(parsed_urls):
    # so it parses just few offers for debugging
    if DEBUG:
        i = 0
    descriptions = []
    for url in parsed_urls:
        response = get_content_for_url(url)
        try:
            descriptions.append(parse_offer(response.content, url))
        except AttributeError:
            log.warning("This offer is not available anymore")
        if DEBUG:
            i += 1
            if i > 3:
                break
    return descriptions


def parse_url(markup):
    html_parser = BeautifulSoup(markup, "html.parser")
    try:
        output = {}
        urls = html_parser.find_all(class_="parent")
        for element in urls:
            if element.attrs['data-id'].isdigit():
                output[element.attrs['data-id']] = []
                output[element.attrs['data-id']].extend(
                    [element.span.text, element.attrs["href"].split("/")[len(element.attrs["href"].split("/")) - 2]])
        return output
    except AttributeError:
        pass


# everything on olx (ignore for now)
def parse_cat(markup, parsed_urls):
    html_parser = BeautifulSoup(markup, "html.parser")
    sub_cats = html_parser.find_all(class_="link-relatedcategory")
    for element in sub_cats:
        parsed_urls[element.attrs['data-category-id']].append({element.attrs['data-id']: [element.span.span.text,
                                                                                          element.attrs['href'].split(
                                                                                              "/")[
                                                                                              len(element.attrs[
                                                                                                  'href'].split(
                                                                                                  "/")) - 2]]})
    return parsed_urls


# everything on olx
def get_available_main_sub_categories():
    url = get_url()
    response = get_content_for_url(url).content
    html_parser = BeautifulSoup(response, "html.parser")
    page_content = html_parser.find(class_='maincategories')
    parsed_urls = parse_url(str(page_content))
    log.info(json.dumps(parsed_urls))
    log.info("\n")
    sub_urls = parse_cat(str(page_content), parsed_urls)
    log.info(sub_urls)
    return sub_urls


if __name__ == '__main__':
    # get_available_main_sub_categories()
    city = city_name("Gdańsk")
    p_from = url_price_from(1000)
    p_to = url_price_to(3000)
    furniture = url_furniture(True)
    typ = url_builttype("blok")
    rooms = url_rooms(3)
    yard_min = url_yardage_from(100)
    yard_max = url_yardage_to(40)
    floor = url_floor(4)
    parsed_urls = get_category("nieruchomosci", "mieszkania", "wynajem", city)
    # parsed_urls = get_category("nieruchomosci", "mieszkania", "wynajem", city, p_from, p_to, typ, rooms)
    # parsed_urls = get_category("nieruchomosci", "mieszkania", "wynajem",city)
    descriptions = get_description(parsed_urls)
    for element in descriptions:
        log.info("\n")
        # json dumps doesn't work with polish chars
        # log.info(json.dumps(element))
        print(element)
