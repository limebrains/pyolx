# python modules
from urllib.parse import urlparse

# third party
import requests
from bs4 import BeautifulSoup

# own modules
from scrapper_helpers.utils import caching

BASE_URL = 'https://www.olx.pl'
OFFERS_FEATURED_PER_PAGE = 3
DEBUG = True

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


def get_url(main_category, subcategory, detail_category, region, page, **filters):
    return "/".join([BASE_URL, main_category, subcategory, detail_category, region, page or ""])


@caching
def get_content_for_url(url):
    response = requests.get(url, allow_redirects=False)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        print('Request for {} failed.'.format(url))
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
    return price


def get_yardage(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    try:
        yardage = html_parser.sup.parent.text
        return int(yardage.replace("\t", "").replace("\n", "").replace(" m", ""))
    except ValueError:
        return None


def parse_description(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    description = html_parser.find(class_="large").text
    return description.replace("  ", "")


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
        return date[4].replace("Dodane", "").replace("\n", "").replace("  ", "").replace("o ", "").replace(", ", "")
    except IndexError:
        return date[0].replace("Dodane", "").replace("\n", "").replace("  ", "").replace("o ", "").replace(", ", " ")


# parses data from google tag manager script
def parse_data(offer_markup):
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
    offer_data = parse_data(str(offer_content))
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


def get_category(main_category, subcategory, detail_category, region, **filters):
    parsed_content = []
    page = 1
    page_attr = None
    while True:
        url = get_url(main_category, subcategory, detail_category, region, page_attr, **filters)
        response = get_content_for_url(url)
        if response.status_code > 300:
            break
        print("Loaded page {} of offers".format(page))
        parsed_content.append(parse_available_offers(response.content))
        page += 1
        page_attr = "?page={}".format(page)
    parsed_content = list(flatten(parsed_content))
    print(str(len(parsed_content)) + " offers")
    return parsed_content


def get_description(parsed_urls):
    i = 0
    descriptions = []
    for url in parsed_urls:
        response = get_content_for_url(url)
        try:
            descriptions.append(parse_offer(response.content, url))
        except AttributeError:
            print("This offer is not available anymore")
        if DEBUG:
            i += 1
            if i > 5:
                break
    return descriptions


if __name__ == '__main__':
    parsed_urls = get_category("nieruchomosci", "mieszkania", "wynajem", "gdansk")
    descriptions = get_description(parsed_urls)