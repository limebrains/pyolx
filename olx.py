# python modules
from urllib.parse import urlparse

# third party
import requests
from bs4 import BeautifulSoup

# own modules
from scrapper_helpers.utils import caching

BASE_URL = 'https://www.olx.pl'
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


def parse_offer(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    url = html_parser.find(class_="linkWithHash").attrs['href']
    if not url:
        # detail url is not present
        return []
    if urlparse(url).hostname not in WHITELISTED_DOMAINS:
        # domain is not supported by this backend
        return []
    return url
    # return {
    #     'detail_url': url
    # }


def get_title(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    title = html_parser.h1.contents
    return title[0].replace("\n", "").replace("  ", "")


def get_price(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    price = html_parser.find(class_="xxxx-large").contents
    return price[0]


def get_img_url(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    img = html_parser.find(class_="bigImage").attrs["src"]
    return img


def get_date_added(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    date = html_parser.find(class_="offer-titlebox__details").em.contents
    try:
        return date[4].replace("Dodane", "").replace("\n", "").replace("  ", "").replace("o ", "").replace(", ", "")
    except IndexError:
        return date[0].replace("Dodane", "").replace("\n", "").replace("  ", "").replace("o ", "").replace(", ", " ")


def parse_avalible_offers(markup):
    html_parser = BeautifulSoup(markup, "html.parser")
    offers = html_parser.find_all(class_='offer')
    parsed_offers = [parse_offer(str(offer)) for offer in offers if offer]
    # delete featured offers (always first 3)
    for i in range(3):
        del parsed_offers[0]
    return parsed_offers


def parse_description(markup, url):
    html_parser = BeautifulSoup(markup, "html.parser")
    offer_content = html_parser.find_all(class_='offerbody')
    parsed_titles = [get_title(str(desc)) for desc in offer_content if desc]
    parsed_prices = [get_price(str(desc)) for desc in offer_content if desc]
    parsed_imgs = [get_img_url(str(desc)) for desc in offer_content if desc]
    parsed_dates = [get_date_added(str(desc)) for desc in offer_content if desc]
    return {
        "title": parsed_titles[0],
        "price": parsed_prices[0],
        "url": url,
        "date": parsed_dates[0],
        "img": parsed_imgs[0]
    }


def get_category(main_category, subcategory, detail_category, region, **filters):
    parsed_content = []
    page = 1
    page_attr = None
    while True:
        url = get_url(main_category, subcategory, detail_category, region, page_attr, **filters)
        response = get_content_for_url(url)
        print(url)
        if response.status_code > 300:
            break
        parsed_content.append(parse_avalible_offers(response.content))
        page += 1
        page_attr = "?page={}".format(page)

    parsed_content = list(flatten(parsed_content))
    print(str(len(parsed_content)) + "offers")
    # print(parsed_content)
    return parsed_content


def get_description(parsed_urls):
    i = 0
    descriptions = []
    for url in parsed_urls:
        response = get_content_for_url(url)
        descriptions.append(parse_description(response.content, url))
        i += 1
        if i > 5:
            break
    return descriptions


if __name__ == '__main__':
    parsed_urls = get_category("nieruchomosci", "mieszkania", "wynajem", "gdansk")
    descriptions = get_description(parsed_urls)
    for element in descriptions:
        print(element)
