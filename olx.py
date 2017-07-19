# python modules
from urllib.parse import urlparse

# third party
import requests
from bs4 import BeautifulSoup

# own modules

BASE_URL = 'https://www.olx.pl/'

WHITELISTED_DOMAINS = [
    'olx.pl',
    'www.olx.pl',
]


def get_url(main_category, subcategory, detail_category, region, **filters):
    return "/".join([BASE_URL, main_category, subcategory, detail_category, region])


def get_content_for_url(url):
    return requests.get(url).content


def parse_offer(offer_markup):
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    url = html_parser.find(class_="linkWithHash").attrs['href']
    if not url:
        # detail url is not present
        return {}
    if urlparse(url).hostname not in WHITELISTED_DOMAINS:
        # domain is not supported by this backend
        return {}

    return {
        'detail_url': url
    }


def parse_content(markup):
    html_parser = BeautifulSoup(markup, "html.parser")
    offers = html_parser.find_all(class_='offer')
    parsed_offers = [parse_offer(str(offer)) for offer in offers if offer]
    print(parsed_offers)


def get_category(main_category, subcategory, detail_category, region, **filters):
    url = get_url(main_category, subcategory, detail_category, region, **filters)
    content = get_content_for_url(url)
    parsed_content = parse_content(content)
    return content


if __name__ == '__main__':
    get_category("nieruchomosci", "mieszkania", "wynajem", "gdansk")
