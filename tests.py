from unittest import mock

import pytest
from bs4 import BeautifulSoup

import olx

GDANSK_URL = "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/gdansk/"
OFFER_URL = "https://www.olx.pl/oferta/mieszkanie-dwupokojowe-na-lawendowym-wzgorzu-CID3-IDnBKeu.html#1d9db51b24"


@pytest.mark.parametrize("a,b", [("Ruda Śląska", olx.POLISH_CHARACTERS_MAPPING), ])
def test_replace_all(a, b):
    assert olx.replace_all(a.lower(), b) == "ruda slaska"


@pytest.mark.parametrize("list1", [[[2], [[3], [1]], [4, [0]]]])
def test_flatten(list1):
    result = olx.flatten(list1)
    for element in result:
        assert not isinstance(element, list)


response = olx.get_content_for_url(GDANSK_URL)
html_parser = BeautifulSoup(response.content, "html.parser")
offers = html_parser.find_all(class_='offer')
parsed_urls = ["https://www.olx.pl/oferta/mieszkanie-dwupokojowe-na-lawendowym-wzgorzu-CID3-IDnBKeu.html#1d9db51b24"]


@pytest.mark.parametrize("city", [
    "Gdańsk", "Sopot", "Gdynia", "Ruda Śląska", "Łódź"
])
def test_city_name(city):
    result = olx.city_name(city)
    for value in olx.POLISH_CHARACTERS_MAPPING.keys():
        if value in result:
            assert False
    assert " " not in result and result.islower()


@pytest.mark.parametrize("offers", [response.content])
def test_parse_available_offers(offers):
    assert olx.parse_available_offers(offers)


@pytest.mark.parametrize("url_info", ["nieruchomosci", "mieszkania", "wynajem", "gdansk", olx.url_floor(2)])
def test_get_url(url_info):
    assert olx.get_url(filters=url_info)
    assert olx.get_url("page=1&", url_info)


@pytest.mark.parametrize("page_count", [response.content])
def test_get_page_count(page_count):
    assert olx.get_page_count(page_count) == 11


@pytest.mark.parametrize("test_url", ['https://www.olx.pl/', GDANSK_URL])
def test_get_conntent_for_url(test_url):
    assert olx.get_content_for_url(test_url)


@pytest.mark.parametrize("offer_url", [
    str(offer) for offer in offers if offer
])
def test_parse_offer_url(offer_url):
    olx.parse_offer_url(offer_url)


@pytest.fixture
def offer_parser():
    response = olx.get_content_for_url(OFFER_URL)
    html_parser = BeautifulSoup(response.content, "html.parser")
    return html_parser


@pytest.fixture
def offer_content(offer_parser):
    return str(offer_parser.find(class_='offerbody'))


@pytest.fixture
def parsed_body(offer_parser):
    return str(offer_parser.find("body"))


def test_parse_description(offer_content):
    assert type(olx.parse_description(offer_content)) == str


def test_get_title(offer_content):
    assert olx.get_title(offer_content) == "Mieszkanie dwupokojowe na Lawendowym Wzgórzu"


def test_get_price(offer_content):
    assert olx.get_price(offer_content) == 1700


def test_get_surface(offer_content):
    assert olx.get_surface(offer_content) == 38.0


def test_get_img_url(offer_content):
    images = olx.get_img_url(offer_content)
    assert isinstance(images, list)
    for img in images:
        assert "https://" in img


def test_get_date_added(parsed_body):
    assert olx.get_date_added(parsed_body)


def test_parse_offer(parsed_body):
    assert olx.parse_offer(parsed_body, OFFER_URL)


def test_parse_flat_data(parsed_body):
    test = olx.parse_flat_data(parsed_body)
    assert test["private_business"] == "private"
    assert test["floor"] == 3
    assert test["rooms"] == 2
    assert test["builttype"] == "blok"
    assert test["furniture"]


@pytest.mark.parametrize("urls", [parsed_urls])
def test_get_descriptions(urls):
    assert isinstance(olx.get_descriptions(urls), list)


@pytest.mark.para
@pytest.mark.parametrize('main_category,subcategory,detail_category,region', [
    ("nieruchomosci", "mieszkania", "wynajem", 'tczew'),
    ("nieruchomosci", "mieszkania", "wynajem", 'gdansk'),
    ("nieruchomosci", "mieszkania", "wynajem", 'gdynia'),
    ("nieruchomosci", "mieszkania", "wynajem", 'sopot'),
])
def test_get_category(main_category, subcategory, detail_category, region):
    with mock.patch("olx.get_category") as get_url:
        with mock.patch("olx.get_content_for_url") as get_content_for_url:
            get_content_for_url.return_value = response
            get_url.retrun_value = olx.get_url
            olx.get_category(main_category, subcategory, detail_category, region)
