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
    title = html_parser.find(class_="linkWithHash").child
    if not url:
        # detail url is not present
        return []

    if urlparse(url).hostname not in WHITELISTED_DOMAINS:
        # domain is not supported by this backend
        return []
    # print(urlparse(url).hostname, url)
    return {
        'detail_url': url
    }


def parse_content(markup):
    html_parser = BeautifulSoup(markup, "html.parser")
    offers = html_parser.find_all(class_='offer')
    parsed_offers = [parse_offer(str(offer)) for offer in offers if offer]
    # delete featured offers (always first 3)
    for i in range(3):
        del parsed_offers[0]
    return parsed_offers


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
        parsed_content.append(parse_content(response.content))
        page += 1
        page_attr = "?page={}".format(page)

    parsed_content = list(flatten(parsed_content))
    print(len(parsed_content))
    print(parsed_content)
    return parsed_content


if __name__ == '__main__':
    parsed_urls = get_category("nieruchomosci", "mieszkania", "wynajem", "gdansk")
