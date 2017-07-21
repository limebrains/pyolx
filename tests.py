from unittest import mock
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup

import olx

GDANSK_URL = "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/gdansk/"
OFFER_URL = "https://www.olx.pl/oferta/dwupokojowe-w-pelni-wyposazone-mieszkanie-do-wynajecia-gdansk-chelm-CID3-IDnyMBq.html#1d9db51b24"


@pytest.mark.parametrize("a,b", [("Ruda Śląska", olx.POLISH_CHARACTERS_MAPPING), ])
def test_replace_all(a, b):
    assert olx.replace_all(a.lower(), b) == "ruda slaska"


@pytest.mark.parametrize("a", [[[2], [[3], [1]], [4, [0]]]])
def test_flatten(a):
    result = olx.flatten(a)
    for element in result:
        assert not isinstance(element, list)


# just temporary test for coverage
def test_get_main_sub():
    olx.get_available_main_sub_categories()


@pytest.mark.parametrize('a', [
    (range(3200)),
])
def test_get_paraments(a):
    assert olx.url_price_from(a) == "search%5Bfilter_float_price%3Afrom%5D={0}".format(str(a))
    assert olx.url_price_to(a) == "search%5Bfilter_float_price%3Ato%5D={0}".format(str(a))
    assert olx.url_yardage_from(a) == "search%5Bfilter_float_m%3Afrom%5D={0}".format(str(a))
    assert olx.url_yardage_to(a) == "search%5Bfilter_float_m%3Ato%5D={0}".format(str(a))


@pytest.mark.parametrize('a', ["blok", "apartamentowiec", "kamienica", "cos", "niepoprawny"])
def test_builttype(a):
    olx.url_builttype(a)


@pytest.mark.parametrize("a", range(-2, 25))
def test_url_rooms(a):
    olx.url_rooms(a)
    olx.url_floor(a)


response = olx.get_content_for_url(GDANSK_URL)
html_parser = BeautifulSoup(response.content, "html.parser")
offers = html_parser.find_all(class_='offer')


@pytest.mark.parametrize("a", [
    "Gdańsk", "Sopot", "Gdynia", "Ruda Śląska", "Łódź"
])
def test_city_name(a):
    result = olx.city_name(a)
    for value in olx.POLISH_CHARACTERS_MAPPING.keys():
        if value in result:
            assert False
    assert " " not in result and result.islower()


@pytest.mark.parametrize("a", [response.content])
def test_parse_available_offers(a):
    assert olx.parse_available_offers(a)


@pytest.mark.parametrize("a", ["nieruchomosci", "mieszkania", "wynajem", "gdansk", olx.url_floor(2)])
def test_get_url(a):
    assert olx.get_url(None, a)
    assert olx.get_url("page=1&", a)


@pytest.mark.parametrize("a", [response.content])
def test_get_page_count(a):
    assert olx.get_page_count(a)


@pytest.mark.parametrize("a", [ele for ele in
                               ['https://www.olx.pl/', GDANSK_URL]])
def test_get_conntent_for_url(a):
    assert olx.get_content_for_url(a)


# @pytest.mark.parametrize(
#     "a", [
#         str(offer) for offer in offers if offer
#     ]
# )
# def test_parse_offer_url(a):
#     olx.parse_offer_url(a)


@pytest.fixture(scope='session')
def sample_offer():
    response = olx.get_content_for_url(OFFER_URL)
    html_parser = BeautifulSoup(response.content, "html.parser")
    offer_content = html_parser.find(class_='offerbody')
    return str(offer_content)

def test_parse_description(sample_offer):
    assert type(olx.parse_description(sample_offer)) == str



def test_get_title(sample_offer):
    assert type(olx.get_title(sample_offer)) == str


def test_get_price(sample_offer):
    assert type(olx.get_price(sample_offer)) == int


def test_get_yardage(sample_offer):
    assert type(olx.get_yardage(sample_offer)) == int


def test_get_img_url(sample_offer):
    assert isinstance(olx.get_img_url(sample_offer), list)


def test_get_date_added(sample_offer):
    assert olx.get_date_added(sample_offer)


def test_parse_flat_data(sample_offer):
    assert olx.parse_flat_data(sample_offer)


def test_parse_offer(sample_offer):
    assert olx.parse_offer(sample_offer, OFFER_URL)


@pytest.mark.parametrize('main_category,subcategory,detail_category,region', [
    ("nieruchomosci", "mieszkania", "wynajem", 'tczew'),
    ("nieruchomosci", "mieszkania", "wynajem", 'gdansk'),
    ("nieruchomosci", "mieszkania", "wynajem", 'gdynia'),
    ("nieruchomosci", "mieszkania", "wynajem", 'sopot'),
])
def test_get_category(main_category, subcategory, detail_category, region):
    with mock.patch("olx.get_category") as get_url:
        get_url.retrun_value = olx.get_url
        olx.get_category(main_category, subcategory, detail_category, region)

@pytest.mark.skipif(True)
@pytest.mark.parametrize("a", )
def test_get_description(a):
    assert olx.get_description(a)