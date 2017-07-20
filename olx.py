# python modules
from urllib.parse import urlparse

# third party
import requests
from bs4 import BeautifulSoup

# own modules
from scrapper_helpers.utils import caching

BASE_URL = 'https://www.olx.pl/'
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

# TODO: remove polish chars
def city_name(input):
    out = ""
    for char in input:
        if char == " ":
            out += "-"
        else:
            out += char.lower()
    return out

def url_price_from(price):
    return "search%5Bfilter_float_price%3Afrom%5D=" + str(price)

def url_price_to(price):
    return "search%5Bfilter_float_price%3Ato%5D=800" + str(price)

def get_url(page=None, *args):
    url = BASE_URL
    for element in args:
        if element is not None:
            if "filter" in url and "filter" in element:
                url += element + "&"
            elif "filter" in element:
                url += "?" + element + "&"
            else:
                url += element + "/"
    if page is not None:
        if "filter" in url:
            url += "&" + page
        else:
            url += "?" + page
    return url

def url_buildtype(type):
    return "search%5Bfilter_enum_builttype%5D%5B0%5D=" + type

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
    except ValueError:
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
        return date[4].replace("Dodane", "").replace("\n", "").replace("  ", "").replace("o ", "").replace(", ", "")
    except IndexError:
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
    page_attr = None
    while True:
        url = get_url(page_attr, main_category, subcategory, detail_category, region, *args)
        print(url)
        response = get_content_for_url(url)
        if response.status_code > 300:
            break
        print("Loaded page {} of offers".format(page))
        parsed_content.append(parse_available_offers(response.content))
        page += 1
        page_attr = "page={}".format(page)
    parsed_content = list(flatten(parsed_content))
    print("Loaded " + str(len(parsed_content)) + " offers")
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
    print(parsed_urls)
    print()
    sub_urls = parse_cat(str(page_content), parsed_urls)
    print(sub_urls)
    return sub_urls



if __name__ == '__main__':
    # get_available_main_sub_categories()
    p_from = url_price_from(2000)
    p_to = url_price_to(3000)
    typ = "apartamentowiec"
    parsed_urls = get_category("nieruchomosci", "mieszkania", "wynajem", "gdansk",p_from,p_to,typ)
    descriptions = get_description(parsed_urls)
    for element in descriptions:
        print()
        print(element)
