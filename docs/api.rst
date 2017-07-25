Introduction
============
pyolx supplies two methods to scrape data from www.olx.pl website

.. _categories:

======================
Scraping category data
======================
This method scrapes available offer urls from OLX search results with parameters

.. autofunction:: olx.category.get_category

It can be used like this:

::

    input_dict = {'[filter_float_price:from]': 2000}
    parsed_urls = olx.category.get_category("nieruchomosci", "mieszkania", "wynajem", "Gdańsk", **input_dict)

The above code will put a list of urls containing all the apartments found in the given category into the parsed_url variable

===================
Scraping offer data
===================
This method scrapes all offer details from

.. autofunction:: olx.offer.get_descriptions

It can be used like this:

::

    descriptions = olx.offer.get_descriptions(parsed_urls)

The above code will put a list of offer details for each offer url provided in parsed_urls into the descriptions variable
