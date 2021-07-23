import datetime
import re
import urllib.parse as urlparse
from urllib.parse import parse_qs

import lxml
import scrapy
from parsel import Selector

from sellgo_core.constants import AmazonMarketplacesConst
from sellgo_core.webcrawl.scrapy.utils import clean


def parse_data(cp, offer_listing_list, price_list, sales_rank_list, product_id):
    if isinstance(cp, (list,)):
        for i in cp:
            parse_single(offer_listing_list, price_list, i, sales_rank_list, product_id)
    else:
        parse_single(offer_listing_list, price_list, cp, sales_rank_list, product_id)


def parse_single(offer_listing_list, price_list, i, sales_rank_list, product_id):
    c_pricing = i["Product"]["CompetitivePricing"]

    # CompetitivePrice
    if "CompetitivePrice" in c_pricing["CompetitivePrices"]:
        cp_list = c_pricing["CompetitivePrices"]["CompetitivePrice"]
        if isinstance(cp_list, (list,)):
            for j in cp_list:
                price_dict = competitive_pricing_single(j, product_id)
                price_list.append(price_dict)
        else:
            price_dict = competitive_pricing_single(cp_list, product_id)
            price_list.append(price_dict)

    # OfferListings
    if "OfferListingCount" in c_pricing["NumberOfOfferListings"]:
        offer_listings = c_pricing["NumberOfOfferListings"]["OfferListingCount"]
        for offer_listing in offer_listings:
            offer_l_dict = {}
            offer_l_dict["count"] = offer_listing["value"]
            offer_l_dict["condition"] = offer_listing["condition"]["value"]
            offer_l_dict["cdate"] = datetime.datetime.now()
            offer_l_dict["udate"] = datetime.datetime.now()
            offer_l_dict["product_id"] = product_id
            offer_listing_list.append(offer_l_dict)

    # SalesRankings
    if "SalesRank" in i["Product"]["SalesRankings"]:
        sales_ranks = i["Product"]["SalesRankings"]["SalesRank"]
        if isinstance(sales_ranks, (list,)):
            for sales_rank in sales_ranks:
                sales_rank_single(product_id, sales_rank, sales_rank_list)
        else:
            sales_rank = sales_ranks
            sales_rank_single(product_id, sales_rank, sales_rank_list)


def sales_rank_single(product_id, sales_rank, sales_rank_list):
    sales_rank_dict = {}
    sales_rank_dict["product_category_id"] = sales_rank["ProductCategoryId"]["value"]
    sales_rank_dict["rank"] = sales_rank["Rank"]["value"]
    sales_rank_dict["cdate"] = datetime.datetime.now()
    sales_rank_dict["udate"] = datetime.datetime.now()
    sales_rank_dict["product_id"] = product_id
    sales_rank_list.append(sales_rank_dict)


def competitive_pricing_single(j, product_id):
    price_dict = {}
    price_dict["condition"] = j["condition"]["value"]
    price_dict["subcondition"] = j["subcondition"]["value"]
    price_dict["competitive_price_id"] = j["CompetitivePriceId"]["value"]
    price_dict["landed_price_currency"] = j["Price"]["LandedPrice"]["CurrencyCode"][
        "value"
    ]
    price_dict["landed_price_amount"] = j["Price"]["LandedPrice"]["Amount"]["value"]
    price_dict["listing_price_currency"] = j["Price"]["ListingPrice"]["CurrencyCode"][
        "value"
    ]
    price_dict["listing_price_amount"] = j["Price"]["ListingPrice"]["Amount"]["value"]
    price_dict["shipping_currency"] = j["Price"]["Shipping"]["CurrencyCode"]["value"]
    price_dict["shipping_amount"] = j["Price"]["Shipping"]["Amount"]["value"]
    price_dict["cdate"] = datetime.datetime.now()
    price_dict["udate"] = datetime.datetime.now()
    price_dict["product_id"] = product_id
    return price_dict


def parse_sales_estimation(sales_estimation_data):
    sales_estimation_dict = {}
    if sales_estimation_data["result_1day"]:
        sales_estimation_dict["daily_max_sales"] = sales_estimation_data["result_1day"][
            "max"
        ]["sales"]
        sales_estimation_dict["daily_max_rank"] = sales_estimation_data["result_1day"][
            "max"
        ]["rank"]
        sales_estimation_dict["daily_est_sales"] = sales_estimation_data["result_1day"][
            "estimation"
        ]["sales"]
        sales_estimation_dict["daily_est_rank"] = sales_estimation_data["result_1day"][
            "estimation"
        ]["rank"]
        sales_estimation_dict["daily_min_sales"] = sales_estimation_data["result_1day"][
            "min"
        ]["sales"]
        sales_estimation_dict["daily_min_rank"] = sales_estimation_data["result_1day"][
            "min"
        ]["rank"]
    if sales_estimation_data["result_30day"]:
        sales_estimation_dict["monthly_max_sales"] = sales_estimation_data[
            "result_30day"
        ]["max"]["sales"]
        sales_estimation_dict["monthly_max_rank"] = sales_estimation_data[
            "result_30day"
        ]["max"]["rank"]
        sales_estimation_dict["monthly_est_sales"] = sales_estimation_data[
            "result_30day"
        ]["estimation"]["sales"]
        sales_estimation_dict["monthly_est_rank"] = sales_estimation_data[
            "result_30day"
        ]["estimation"]["rank"]
        sales_estimation_dict["monthly_min_sales"] = sales_estimation_data[
            "result_30day"
        ]["min"]["sales"]
        sales_estimation_dict["monthly_min_rank"] = sales_estimation_data[
            "result_30day"
        ]["min"]["rank"]
    return sales_estimation_dict


def parse_inventory_monitoring_report(monitoring_report, asin_id_map):
    inventory_list = []
    for i in monitoring_report:
        inventory_count = i[2]
        if i[0] not in asin_id_map:
            continue
        product_id = asin_id_map[i[0]]
        inventory_dict = {
            "vendor_id": None,
            "merchant_name": None,
            "merchant_id": None,
            "condition": None,
            "price": None,
            "fulfillment": None,
            "inventory": inventory_count,
            "cdate": datetime.datetime.now(),
            "udate": datetime.datetime.now(),
            "product_id": product_id,
        }
        inventory_list.append(inventory_dict)
    return inventory_list


def parse_fees_estimate(fees_estimate_parsed):
    total_amount = float(
        fees_estimate_parsed["FeesEstimate"]["TotalFeesEstimate"]["Amount"]["value"]
    )

    # If there is Per Item Fee (FBM sellers) we need to subtract it from total fees
    for fee in fees_estimate_parsed["FeesEstimate"]["FeeDetailList"]["FeeDetail"]:
        if fee["FeeType"]["value"] == "PerItemFee":
            per_item_fee = float(fee["FinalFee"]["Amount"]["value"])
            if per_item_fee > 0:
                total_amount = total_amount - per_item_fee

    return {
        "total_amount": str(total_amount),
        "total_currency": fees_estimate_parsed["FeesEstimate"]["TotalFeesEstimate"][
            "CurrencyCode"
        ]["value"],
    }


def parse_offer_sellers_page_count(response_text):
    selector = Selector(response_text)
    pinned_count = 0
    pinned_offers = selector.css("#aod-pinned-offer")
    for ind, pinned_offer in enumerate(pinned_offers):
        if pinned_offer.css(
            "#aod-price-{} > span > span.a-offscreen::text".format(ind)
        ).get():
            pinned_count += 1

    return (
        int(clean(selector.css("#aod-total-offer-count").attrib["value"])) or 0
    ) + pinned_count


def parse_amazon_product_listing_page(response_text):
    tree = lxml.html.fromstring(response_text)

    # regular expressions
    PT_NON_NUMERALS = re.compile(r"\D+")
    PT_CUSTOMER_RATING = re.compile(r"([\d\.]+) out of 5 stars")
    PT_BSR = re.compile(r"#([\d].*) in (.*)")
    PT_NR_OF_SELLERS = re.compile(r"New \(([\d\.]+)\) from")

    try:
        answered_questions_text = tree.xpath('//a[@id="askATFLink"]/span')
        answered_questions_text = (
            answered_questions_text[0].text.replace("answered questions", "").strip()
        )
        answered_questions_text = PT_NON_NUMERALS.sub("", answered_questions_text)
        answered_questions = int(answered_questions_text)
    except (IndexError, ValueError):
        answered_questions = 0

    try:
        customer_reviews_text = tree.xpath('//span[@id="acrCustomerReviewText"]')
        customer_reviews_text = (
            customer_reviews_text[0].text.replace("customer reviews", "").strip()
        )
        customer_reviews_text = PT_NON_NUMERALS.sub("", customer_reviews_text)
        customer_reviews = int(customer_reviews_text)
    except (IndexError, ValueError):
        customer_reviews = 0

    try:
        customer_rating_text = tree.xpath(
            '//span[@id="acrPopover"]//span[@class="a-icon-alt"]'
        )[0].text.strip()
        match = PT_CUSTOMER_RATING.search(customer_rating_text)
        customer_rating = match and float(match.group(1))
    except (IndexError, ValueError):
        customer_rating = 0

    try:
        amazon_choice_keyword = tree.xpath(
            '//div[@id="acBadge_feature_div"]//span[@class="ac-keyword-link"]/a'
        )[0].text.strip()
        amazon_choice = amazon_choice_keyword
    except (IndexError, ValueError):
        amazon_choice = None

    try:
        bsr_text = ""
        rank = None
        category = None
        if tree.xpath('//a[contains(text(), "See Top 100 in ")]//..'):
            bsr_element = tree.xpath('//a[contains(text(), "See Top 100 in ")]//..')[0]
            if bsr_element.tag == "li":
                bsr_text = (
                    bsr_element[0].tail.replace("\n", "").replace("(", "").strip()
                )
            elif bsr_element.tag in ("span", "td"):
                bsr_text = bsr_element.text.replace("\n", "").replace("(", "").strip()
            if not bsr_text and tree.xpath(
                '//a[contains(text(), "See Top 100 in ")]//..//span'
            ):
                bsr_element = tree.xpath(
                    '//a[contains(text(), "See Top 100 in ")]//..//span'
                )
                bsr_text = (
                    bsr_element[0].tail.replace("\n", "").replace("(", "").strip()
                )
            match = PT_BSR.search(bsr_text)
            rank = match and int(match.group(1).replace(",", ""))
            category = match and match.group(2)
        elif tree.xpath('//th[contains(text(), "Best Sellers Rank")]//..//span'):
            bsr_text = (
                tree.xpath('//th[contains(text(), "Best Sellers Rank")]//..//span')[1]
                .text.replace("\n", "")
                .replace("(", "")
            )
            match = PT_BSR.search(bsr_text)
            rank = match and int(match.group(1).replace(",", ""))
            category = tree.xpath(
                '//th[contains(text(), "Best Sellers Rank")]//..//span//a'
            )[0].text.strip()
        elif tree.xpath('//span[@class="zg_hrsr_rank"]'):
            rank = int(
                tree.xpath('//span[@class="zg_hrsr_rank"]')[0]
                .text.replace("#", "")
                .strip()
            )
            category = tree.xpath('//span[@class="zg_hrsr_ladder"]//a')[0].text.strip()
    except (IndexError, ValueError):
        rank = None
        category = None

    selector = Selector(response_text)
    is_amazon_selling = False
    amazon_price = None
    buy_box_css = (
        ".buybox-tabular-column ::text, #moreBuyingChoices_feature_div ::text, #newAccordionRow ::text,"
        " #tabular-buybox ::text"
    )
    sold_by_amazon_text = ["sold by amazon.com", "sold by: amazon.com"]

    if (
        any(
            t in clean(" ".join(selector.css(buy_box_css).getall())).lower()
            for t in sold_by_amazon_text
        )
        or "amazon warehouse"
        in clean(
            " ".join(selector.css("#sellerProfileTriggerId ::text").getall())
        ).lower()
    ):
        is_amazon_selling = True

        try:
            if any(
                t
                in clean(
                    " ".join(
                        selector.css("#moreBuyingChoices_feature_div ::text").getall()
                    )
                ).lower()
                for t in sold_by_amazon_text
            ):
                merchant_name_paths = tree.xpath(
                    '//span[@class="a-size-small mbcMerchantName"]'
                )
                if merchant_name_paths:
                    ix = 0
                    found = False
                    for i in merchant_name_paths:
                        if "Amazon.com" in i.text:
                            found = True
                            break
                        ix += 1
                    if found:
                        amazon_price_path = tree.xpath(
                            '//span[@class="a-size-small mbcMerchantName"]//..//..//'
                            'span[@class="a-size-medium a-color-price"]'
                        )
                        if amazon_price_path:
                            amazon_price = float(
                                amazon_price_path[ix]
                                .text.replace("\n", "")
                                .replace("$", "")
                            )
            elif any(
                t
                in clean(
                    " ".join(selector.css("#newAccordionRow ::text").getall())
                ).lower()
                for t in sold_by_amazon_text
            ):
                amazon_price_path = tree.xpath(
                    '//div[@id="buyBoxAccordion"]//span[@id="newBuyBoxPrice"]'
                )
                if amazon_price_path:
                    amazon_price = float(amazon_price_path[0].text.replace("$", ""))
            elif any(
                t
                in clean(
                    " ".join(selector.css("#tabular-buybox ::text").getall())
                ).lower()
                for t in sold_by_amazon_text
            ):
                amazon_price_path = tree.xpath('//span[@id="price_inside_buybox"]')
                if amazon_price_path:
                    amazon_price = float(
                        amazon_price_path[0].text.replace("\n", "").replace("$", "")
                    )
                else:
                    amazon_price_path = tree.xpath('//span[@id="price"]')
                    if amazon_price_path:
                        amazon_price = float(
                            amazon_price_path[0].text.replace("\n", "").replace("$", "")
                        )
            elif (
                "amazon warehouse"
                in clean(
                    " ".join(selector.css("#sellerProfileTriggerId ::text").getall())
                ).lower()
            ):
                amazon_price_path = tree.xpath('//span[@id="gsbbUsedPrice"]')
                if amazon_price_path:
                    amazon_price = float(
                        amazon_price_path[0].text.replace("\n", "").replace("$", "")
                    )
        except (IndexError, ValueError):
            amazon_price = None

    try:
        best_seller = None
        bs_path = tree.xpath('//a[@class="badge-link"]')
        if bs_path:
            if "title" in bs_path[0].attrib:
                best_seller = bs_path[0].attrib["title"]
    except (IndexError, ValueError):
        best_seller = None

    try:
        subscribe_save = None
        sns_path = tree.xpath('//span[contains(text(), "Subscribe & Save:")]')
        if sns_path and sns_path[0].attrib["class"] == "a-text-bold":
            subscribe_save = True
    except (IndexError, ValueError):
        subscribe_save = None

    try:
        upcs = None
        upcs_path = tree.xpath('//span[contains(text(), "UPC\n:\n")]')
        if upcs_path and upcs_path[0].attrib["class"] == "a-text-bold":
            upcs_path = tree.xpath('//span[contains(text(), "UPC\n:\n")]/../span')
        if upcs_path:
            upcs = upcs_path[1].text
    except (IndexError, ValueError):
        upcs = None

    try:
        number_of_sellers = None
        number_of_sellers_path = tree.xpath('//span[contains(text(), "New (")]')
        if number_of_sellers_path:
            number_of_sellers_text = number_of_sellers_path[0].text
            match = PT_NR_OF_SELLERS.search(number_of_sellers_text)
            number_of_sellers = match and int(match.group(1))
    except (IndexError, ValueError):
        number_of_sellers = None

    return {
        "marketplace_id": AmazonMarketplacesConst.US["id"],
        "answered_questions": answered_questions,
        "customer_reviews": customer_reviews,
        "rating": customer_rating,
        "amazon_choice": amazon_choice,
        "rank": rank,
        "category": category,
        "is_amazon_selling": is_amazon_selling,
        "best_seller": best_seller,
        "subscribe_save": subscribe_save,
        "upcs": upcs,
        "number_of_sellers": number_of_sellers,
        "amazon_price": amazon_price,
    }


def get_offer(asin, raw_html):
    selector = scrapy.Selector(text=raw_html)
    seller = selector.xpath("//div[@id='aod-offer-soldBy']")
    data = {
        "asin": asin,
        "seller_name": None,
        "seller_id": None,
        "seller_url": None,
        "amazon_as_seller": False,
        "price": None,
        "condition": None,
        "fulfillment": None,
    }

    data["price"] = (
        selector.xpath("//span[@class='a-price']/span[@class='a-offscreen']")
        .css("::text")
        .get()
    )
    data["condition"] = (
        selector.xpath("//div[@id='aod-offer-heading']/h5").css("::text").get()
    )
    data["condition"] = (
        data["condition"].replace("\n", "") if data.get("condition") else None
    )

    # Normal Seller
    seller_name = "".join(
        seller.xpath("//div[@class='a-fixed-left-grid-col a-col-right']/a")
        .css("::text")
        .extract()
    )
    seller_name = seller_name.replace("\n", "")

    # Amazon as Seller
    if not seller_name:
        seller_name = "".join(
            seller.xpath("//div[@class='a-fixed-left-grid-col a-col-right']")
            .css("::text")
            .extract()
        )
        seller_name = seller_name.replace("\n", "")
    data["seller_name"] = seller_name if seller_name else None

    if seller_name and "amazon.com" in seller_name.lower():
        data["seller_name"] = "Amazon.com"
        data["amazon_as_seller"] = True
        data["seller_id"] = "ATVPDKIKX0DER"
        data["fulfillment"] = "FBA"
    elif seller_name and "amazon warehouse" in seller_name.lower():
        data["seller_name"] = "Amazon Warehouse"
        data["amazon_as_seller"] = True
        data["seller_id"] = "ATVPDKIKX0DER"
        data["fulfillment"] = "FBA"

    if data.get("amazon_as_seller"):
        return data

    seller = seller.xpath("//a[@role='link']")
    seller_url = f"https://www.amazon.com{seller.xpath('@href').get()}"

    url_params = urlparse.urlparse(seller_url)
    url_params = parse_qs(url_params.query)

    seller_id = url_params.get("seller")
    seller_id = seller_id[0] if seller_id else None
    data["seller_id"] = seller_id

    is_amazon_fulfilled = url_params.get("isAmazonFulfilled")
    if is_amazon_fulfilled:
        is_amazon_fulfilled = int(is_amazon_fulfilled[0])
    else:
        is_amazon_fulfilled = None

    url = f"https://www.amazon.com/sp?&asin={asin}&seller={seller_id}"

    data["fulfillment"] = "FBM"
    if is_amazon_fulfilled:
        url += f"&isAmazonFulfilled={is_amazon_fulfilled}"
        if is_amazon_fulfilled == 1:
            data["fulfillment"] = "FBA"

    data["seller_url"] = url

    return data


def get_offers(asin, raw_html):
    response = scrapy.Selector(text=raw_html)
    obj = response.xpath("//div[@id='aod-offer-list']/div[@id='aod-offer']").extract()
    sellers = []
    for seller in obj:
        sellers.append(get_offer(asin, seller))

    return [x for x in sellers if x.get("seller_name")]


def get_pinned_offer(asin, raw_html):
    response = scrapy.Selector(text=raw_html)
    pinned_seller = response.xpath("//div[@id='aod-pinned-offer']")
    if pinned_seller:
        return get_offer(asin, pinned_seller.get())


def get_all_offers(asin, raw_html):
    offers = []

    # Get pinned offer
    pinned_offer_raw = get_pinned_offer(asin, raw_html)
    if pinned_offer_raw.get("seller_name"):
        pinned_offer = dict()
        pinned_offer["merchant_name"] = pinned_offer_raw["seller_name"]
        pinned_offer["merchant_id"] = pinned_offer_raw["seller_id"]
        pinned_offer["condition"] = pinned_offer_raw["condition"]
        pinned_offer["price"] = pinned_offer_raw["price"]
        pinned_offer["fulfillment"] = pinned_offer_raw["fulfillment"]
        offers.append(pinned_offer)

    other_offers = get_offers(asin, raw_html)
    for offer in other_offers:
        data = {
            "merchant_name": offer["seller_name"],
            "merchant_id": offer["seller_id"],
            "condition": offer["condition"],
            "price": offer["price"],
            "fulfillment": offer["fulfillment"],
        }
        offers.append(data)

    return offers
