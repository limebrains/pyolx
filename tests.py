#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys

import pytest
from bs4 import BeautifulSoup

import olx
import olx.utils
import olx.category
import olx.offer

if sys.version_info < (3, 3):
    from mock import mock
else:
    from unittest import mock

GDANSK_URL = "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/gdansk/"
OFFER_URL = "https://www.olx.pl/oferta/mieszkanie-gdank-5-wzgorz-wysoki-standard-od-sierpnia-2017-CID3-IDnOYSv.html#1d9db51b24"


@pytest.mark.parametrize("list1", [[[2], [[3], [1]], [4, [0]]]])
def test_flatten(list1):
    result = olx.utils.flatten(list1)
    for element in result:
        assert not isinstance(element, list)


@pytest.mark.parametrize("filter_name,filter_value", [
    ("[filter_float_price:from]", 2000),
    ("[filter_enum_floor_select][0]", 2),
    ("[filter_enum_furniture][0]", True),
    ("[filter_enum_builttype][0]", "blok"),
    ("[filter_enum_rooms][0]", 3)
])
def test_get_search_filter(filter_name, filter_value):
    assert "search%5B" in olx.utils.get_search_filter(filter_name, filter_value)


response = olx.utils.get_content_for_url(GDANSK_URL)
html_parser = BeautifulSoup(response.content, "html.parser")
offers = html_parser.find_all(class_='offer')
parsed_urls = [OFFER_URL]


@pytest.mark.parametrize("city", [
    "Gdańsk", "Sopot", "Gdynia", "Ruda Śląska", "Łódź"
])
def test_city_name(city):
    result = olx.utils.city_name(city)
    for value in olx.utils.POLISH_CHARACTERS_MAPPING.keys():
        if value in result:
            assert False
    assert " " not in result and result.islower()


@pytest.mark.parametrize("offers", [response.content])
def test_parse_available_offers(offers):
    assert olx.category.parse_available_offers(offers)


@pytest.mark.parametrize("maincat,subcat,detailcat,region,filters", [
    ("nieruchomosci", "mieszkania", "wynajem", "gdansk", {"[filter_float_price:from]": 2000}),
])
def test_get_url(maincat, subcat, detailcat, region, filters):
    assert olx.utils.get_url(maincat, subcat, detailcat, region, **filters) == \
           "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/gdansk/?search%5Bfilter_float_price%3Afrom%5D=2000&"


@pytest.mark.parametrize("page_count", [response.content])
def test_get_page_count(page_count):
    assert olx.category.get_page_count(page_count) == 11


@pytest.mark.parametrize("test_url", ['https://www.olx.pl/', GDANSK_URL])
def test_get_conntent_for_url(test_url):
    assert olx.utils.get_content_for_url(test_url)


@pytest.mark.parametrize("offer_url", [
    str(offer) for offer in offers if offer
])
def test_parse_offer_url(offer_url):
    olx.category.parse_offer_url(offer_url)


@pytest.fixture
def offer_parser():
    response = olx.utils.get_content_for_url(OFFER_URL)
    html_parser = BeautifulSoup(response.content, "html.parser")
    return html_parser


@pytest.fixture
def offer_content(offer_parser):
    return str(offer_parser.find(class_='offerbody'))


@pytest.fixture
def parsed_body(offer_parser):
    return str(offer_parser.find("body"))


@pytest.mark.skipif(sys.version_info < (3, 1), reason="requires Python3")
def test_parse_description(offer_content):
    assert olx.offer.parse_description(offer_content)


@pytest.mark.skipif(sys.version_info < (3, 1), reason="requires Python3")
def test_get_title(offer_content):
    assert olx.offer.get_title(offer_content) == "Mieszkanie Gdańk 5 Wzgórz - wysoki standard, od sierpnia 2017"


def test_get_surface(offer_content):
    assert olx.offer.get_surface(offer_content) == 49.0


def test_get_img_url(offer_content):
    images = olx.offer.get_img_url(offer_content)
    assert isinstance(images, list)
    for img in images:
        assert "https://" in img


def test_get_date_added(parsed_body):
    assert olx.offer.get_date_added(parsed_body)


def test_parse_offer(parsed_body):
    assert olx.offer.parse_offer(parsed_body, OFFER_URL)


def test_parse_flat_data(parsed_body):
    test = olx.offer.parse_flat_data(parsed_body)
    assert test["private_business"] == "private"
    assert test["floor"] == 2
    assert test["rooms"] == 2
    assert test["builttype"] == "blok"
    assert test["furniture"]


@pytest.mark.parametrize("urls", [parsed_urls])
def test_get_descriptions(urls):
    assert isinstance(olx.offer.get_descriptions(urls), list)


@pytest.mark.parametrize('main_category,subcategory,detail_category,region', [
    ("nieruchomosci", "mieszkania", "wynajem", 'tczew'),
    ("nieruchomosci", "mieszkania", "wynajem", 'gdansk'),
    ("nieruchomosci", "mieszkania", "wynajem", 'gdynia'),
    ("nieruchomosci", "mieszkania", "wynajem", 'sopot'),
])
def test_get_category(main_category, subcategory, detail_category, region):
    with mock.patch("olx.utils.get_url") as get_url:
        with mock.patch("olx.utils.get_content_for_url") as get_content_for_url:
            with mock.patch("olx.category.parse_available_offers") as parse_available_offers:
                parse_available_offers.return_value = olx.category.parse_available_offers(response.content)
                get_content_for_url.return_value = response
                get_url.return_value = olx.utils.get_url
                olx.category.get_category(main_category, subcategory, detail_category, region)
