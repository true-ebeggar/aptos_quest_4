import random
import re
import requests
from loguru import logger
def distribute_points(addresses, num_addresses):
    chosen_addresses = random.sample(addresses, num_addresses)

    points = [0] * num_addresses
    remaining_points = 100

    for i in range(num_addresses):
        if i == num_addresses - 1:
            points[i] = remaining_points
        else:
            min_points = round(remaining_points / num_addresses)
            max_points = remaining_points - (num_addresses - i - 1) * min_points
            p = random.randint(min_points, max_points)
            points[i] = p
            remaining_points -= p

    distribution = dict(zip(chosen_addresses, points))
    return distribution


def find_in_json(item, pattern):
    if isinstance(item, dict):
        for key, value in item.items():
            for result in find_in_json(value, pattern):
                yield result
    elif isinstance(item, list):
        for i in item:
            for result in find_in_json(i, pattern):
                yield result
    elif isinstance(item, str):
        if re.search(pattern, item):
            yield item


def find_token_address(hash):
    api_url = "https://api.mainnet.aptoslabs.com/v1/transactions/by_hash/" + hash
    response = requests.get(api_url)

    if response.status_code == 200:
        data = response.json()
        uri_pattern = r"https://api.cellana.finance/api/v1/ve-nft/uri/@([0-9a-fA-FxX]+)"

        for uri in find_in_json(data, uri_pattern):
            address_match = re.search(uri_pattern, uri)
            if address_match:
                address = address_match.group(1)
                return address
        logger.error("URI not found in the response.")
        return None
    else:
        logger.critical("Failed to fetch data from API. Status code:", response.status_code)
        return 0


def generate_payload(distribution, argument0):
    addresses = [{"inner": address} for address in distribution.keys()]
    points = [str(point) for point in distribution.values()]
    payload = {
        "function": "0x4bf51972879e3b95c4781a5cdcb9e1ee24ef483e7d22f2d903626f126df62bd1::vote_manager::vote",
        "type_arguments": [],
        "arguments": [
            argument0,
            addresses,
            points
        ],
        "type": "entry_function_payload"
    }

    return payload

