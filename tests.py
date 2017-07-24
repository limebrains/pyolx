from unittest import mock

import pytest
from bs4 import BeautifulSoup

import olx

GDANSK_URL = "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/gdansk/"
OFFER_URL = "https://www.olx.pl/oferta/mieszkanie-dwupokojowe-na-lawendowym-wzgorzu-CID3-IDnBKeu.html#1d9db51b24"


@pytest.mark.parametrize("a,b", [("Ruda Śląska", olx.POLISH_CHARACTERS_MAPPING), ])
def test_replace_all(a, b):
    assert olx.replace_all(a.lower(), b) == "ruda slaska"


@pytest.mark.parametrize("c", [[[2], [[3], [1]], [4, [0]]]])
def test_flatten(c):
    result = olx.flatten(c)
    for element in result:
        assert not isinstance(element, list)


@pytest.mark.parametrize('d', [
    (range(3200)),
])
def test_get_paraments(d):
    assert olx.url_price_from(d) == "search%5Bfilter_float_price%3Afrom%5D={0}".format(str(d))
    assert olx.url_price_to(d) == "search%5Bfilter_float_price%3Ato%5D={0}".format(str(d))
    assert olx.url_surface_from(d) == "search%5Bfilter_float_m%3Afrom%5D={0}".format(str(d))
    assert olx.url_surface_to(d) == "search%5Bfilter_float_m%3Ato%5D={0}".format(str(d))


@pytest.mark.parametrize('e', ["blok", "apartamentowiec", "kamienica"])
def test_builttype(e):
    assert "search%5Bfilter_enum_builttype%5D%5B0%5D=" in olx.url_builttype(e)


@pytest.mark.parametrize("f", range(-2, 25))
def test_url_rooms(f):
    assert "search%5Bfilter_enum_rooms%5D%5B0%5D=" in olx.url_rooms(f)


response = olx.get_content_for_url(GDANSK_URL)
html_parser = BeautifulSoup(response.content, "html.parser")
offers = html_parser.find_all(class_='offer')
parsed_urls = ["https://www.olx.pl/oferta/mieszkanie-dwupokojowe-na-lawendowym-wzgorzu-CID3-IDnBKeu.html#1d9db51b24"]


@pytest.mark.parametrize("g", [
    "Gdańsk", "Sopot", "Gdynia", "Ruda Śląska", "Łódź"
])
def test_city_name(g):
    result = olx.city_name(g)
    for value in olx.POLISH_CHARACTERS_MAPPING.keys():
        if value in result:
            assert False
    assert " " not in result and result.islower()


@pytest.mark.parametrize("h", [response.content])
def test_parse_available_offers(h):
    assert olx.parse_available_offers(h)


@pytest.mark.parametrize("i", ["nieruchomosci", "mieszkania", "wynajem", "gdansk", olx.url_floor(2)])
def test_get_url(i):
    assert olx.get_url(None, i)
    assert olx.get_url("page=1&", i)


@pytest.mark.parametrize("j", [response.content])
def test_get_page_count(j):
    assert olx.get_page_count(j) == 11


@pytest.mark.parametrize("k", ['https://www.olx.pl/', GDANSK_URL])
def test_get_conntent_for_url(k):
    assert olx.get_content_for_url(k)


@pytest.mark.parametrize("l", [
    str(offer) for offer in offers if offer
])
def test_parse_offer_url(l):
    olx.parse_offer_url(l)


response = olx.get_content_for_url(OFFER_URL)
html_parser = BeautifulSoup(response.content, "html.parser")
offer_content = str(html_parser.find(class_='offerbody'))


@pytest.mark.parametrize("m", [offer_content])
def test_parse_description(m):
    assert type(olx.parse_description(m)) == str


@pytest.mark.parametrize("o", [offer_content])
def test_get_title(o):
    assert olx.get_title(o) == "Mieszkanie dwupokojowe na Lawendowym Wzgórzu"


@pytest.mark.parametrize("p", [offer_content])
def test_get_price(p):
    assert olx.get_price(p) == 1700


@pytest.mark.parametrize("a", [offer_content])
def test_get_surface(a):
    assert olx.get_surface(a) == 38.0


@pytest.mark.parametrize("a", [offer_content])
def test_get_img_url(a):
    images = olx.get_img_url(a)
    assert isinstance(images, list)
    for img in images:
        assert "https://" in img


@pytest.mark.parametrize("a", [offer_content])
def test_get_date_added(a):
    assert olx.get_date_added(a)


offer_content = str(html_parser.body)


@pytest.mark.parametrize("a", [offer_content])
def test_parse_offer(a):
    assert olx.parse_offer(a, OFFER_URL)


@pytest.mark.parametrize("a", [offer_content])
def test_parse_flat_data(a):
    test = olx.parse_flat_data(a)
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
