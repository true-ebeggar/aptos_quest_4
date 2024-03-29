import json
import time

from aptos_sdk.account import Account
from aptos_sdk.client import RestClient
from aptos_sdk.client import ClientConfig
from pyuseragents import random as random_ua

from config import *
from contracts import *
from generate_payload import *

ClientConfig.max_gas_amount = 100_00
SLIPPAGE = (100 - 3) / 100


class AptosTxnManager:
    def __init__(self, key):
        self.account = Account.load_key(key)
        self.address = self.account.address()
        self.logger = logger
        self.rest_client = RestClient(NODE)

    def transfer(self, recipient, amount: int):
        payload = {
            "type": "entry_function_payload",
            "function": "0x1::aptos_account::transfer_coins",
            "type_arguments": ["0x1::aptos_coin::AptosCoin"],
            "arguments": [
                str(recipient),
                str(amount),
            ],
        }
        self._submit_and_log_transaction(payload)

    def _submit_and_log_transaction(self, payload):
        try:
            txn = self.rest_client.submit_transaction(self.account, payload)
            self.rest_client.wait_for_transaction(txn)
            self.logger.success(f'https://explorer.aptoslabs.com/txn/{txn}?network=mainnet')
            return 1
        except AssertionError as e:
            error_message = str(e)
            try:
                hash_value = error_message.split(" - ")[-1].strip()
                self.logger.error(f"assertionError: https://explorer.aptoslabs.com/txn/{hash_value}?network=mainnet")
                return 0
            except json.JSONDecodeError:
                self.logger.error(f"assertionError: {error_message}")
                return 0
        except Exception as e:
            self.logger.critical(f"an unexpected error occurred: {e}")
            return 0

    def _register_coin(self, to_register: str):
        payload = {
            "type": "entry_function_payload",
            "function": "0x1::managed_coin::register",
            "type_arguments": [
                to_register
            ],
            "arguments": []
        }
        self._submit_and_log_transaction(payload)

    def _check_registration(self, to_check: str):
        try:
            coin_type = f"0x1::coin::CoinStore<{to_check}>"
            url = f"https://fullnode.mainnet.aptoslabs.com/v1/accounts/{self.address}/resources?limit=9999"
            response = requests.get(url)
            # print(json.dumps(response.json(), indent=4))
            return any(item.get('type', '') == coin_type for item in response.json())
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            return False

    def _get_coin_value(self, coin_to_check: str):
        try:
            coin_store_type = f"0x1::coin::CoinStore<{coin_to_check}>"
            url = f"https://fullnode.mainnet.aptoslabs.com/v1/accounts/{self.address}/resources?limit=9999"
            response = requests.get(url)
            # print(json.dumps(response.json(), indent=4))

            for item in response.json():
                if item.get('type', '') == coin_store_type:
                    coin_data = item.get('data', {}).get('coin', {})
                    coin_value = coin_data.get('value')
                    return coin_value

            return None
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            return None

    def _get_cell_value(self):
        payload = {
            "function": "0x1::primary_fungible_store::balance",
            "type_arguments": ["0x1::fungible_asset::Metadata"],
            "arguments": [
                str(self.address),
                "0x2ebb2ccac5e027a87fa0e2e5f656a3a4238d6a48d93ec9b610d570fc0aa0df12"
            ]
        }
        try:
            response = requests.post('https://fullnode.mainnet.aptoslabs.com/v1/view', json=payload)
            if response.status_code == 200:
                response_data = response.json()
                if response_data:
                    return int(response_data[0])
            else:
                logger.error(f"failed to get cell value, status code: {response.status_code}")
                return None
        except Exception as e:
            logger.critical(f"error: {e}")
            return None

    def get_account_balance(self):
        max_retries = 3
        retries = 0

        while retries < max_retries:
            try:
                return int(self.rest_client.account_balance(account_address=self.address))
            except Exception as e:
                if "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>" in str(e):
                    self.logger.critical("Account does not exist")
                    return False
                else:
                    retries += 1
                    self.logger.error(f"Error occurred: {e} "
                                      f"\nRetry {retries}/{max_retries}")

        self.logger.critical(f"Maximum retries {max_retries} reached. Unable to get account balance.")
        return None

    def get_token_price(self, token_to_get):
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://liquidswap.com",
            "Referer": "https://liquidswap.com/",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "User-Agent": random_ua()
        }
        attempts = 0
        while attempts < 10:
            try:
                response = requests.get(
                    'https://control.pontem.network/api/integrations/fiat-prices?currencies=weth,apt,usdc,usdt',
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    # print(json.dumps(data, indent=4))
                    for token in data:
                        if token['coinType'].lower() == token_to_get.lower():
                            value = token['price']
                            if value is not None:
                                return round(float(value), 5)
                    return None
                else:
                    pass
            except Exception:
                pass
            finally:
                attempts += 1
                time.sleep(5)

        self.logger.error("Unable to fetch price after 10 retries. Giving up...")
        return None

    def swap_apt_to_token(self, token, amount_apt_wei: int):
        try:
            token_info = TOKEN_MAP[token]
            resource = token_info['resource']
            decimals = token_info['decimals']
            router = token_info['router']
            function = token_info['function']

            if self._check_registration(resource) is False:
                self.logger.warning(f"{token.upper()} is not registered, fixing it now...")
                self._register_coin(resource)

            apt_price = self.get_token_price('apt')
            aptos_float = amount_apt_wei / 10**8
            token_price = self.get_token_price(token)
            apt_amount_usd = apt_price * aptos_float
            token_amount_ideal = apt_amount_usd / token_price
            token_amount_slip = token_amount_ideal * SLIPPAGE
            token_amount_slip_wei = int(token_amount_slip * (10 ** decimals))

            payload = {
                "type": "entry_function_payload",
                "function": function,
                "type_arguments": [
                    "0x1::aptos_coin::AptosCoin",
                    str(resource),
                    router
                ],
                "arguments": [
                    str(amount_apt_wei),
                    str(token_amount_slip_wei)
                ],
            }

            self.logger.info(f"{self.address} swapping {aptos_float} APT to {token.upper()}")
            return self._submit_and_log_transaction(payload)

        except Exception as e:
            self.logger.error(f"error while swapping APT to {token.upper()}: {str(e)}")
            return 0

    def lend_token(self, token, amount_token_wei: int):
        token_info = TOKEN_MAP[token]
        resource = token_info['resource']
        decimals = token_info['decimals']

        payload = {
            "function": "0x17f1e926a81639e9557f4e4934df93452945ec30bc962e11351db59eb0d78c33::aries::lend",
            "type_arguments": [
                str(resource)
            ],
            "arguments": [
                str(amount_token_wei)
            ],
            "type": "entry_function_payload"
        }

        self.logger.info(f"going to lend {int(amount_token_wei) / 10**decimals} {token.upper()}")
        return self._submit_and_log_transaction(payload)

    def vote_cell(self, argument0):
        try:
            num_of_pools = random.randint(1, 5)
            self.logger.info(f"{self.address} going to distribute voting pover by {num_of_pools} pools")
            payload = generate_payload(distribute_points(pool_addresses, num_of_pools), argument0)
            # print(json.dumps(payload, indent=4))
            return self._submit_and_log_transaction(payload)
        except Exception as e:
            self.logger.error(f"error while making up payload: {str(e)}")
            return 0

    def _lock_cell(self):
        weeks = [2, 4, 24, 52, 104]
        week = random.choice(weeks)
        amount = self._get_cell_value()

        payload = {
            "function": "0x4bf51972879e3b95c4781a5cdcb9e1ee24ef483e7d22f2d903626f126df62bd1::voting_escrow::create_lock_entry",
            "type_arguments": [],
            "arguments": [
                str(amount),
                str(week)
            ],
            "type": "entry_function_payload"
        }
        self.logger.info(f"{self.address} locking {amount / 10**8} CELL for {week} weeks")
        try:
            txn = self.rest_client.submit_transaction(self.account, payload)
            self.rest_client.wait_for_transaction(txn)
            self.logger.success(f'https://explorer.aptoslabs.com/txn/{txn}?network=mainnet')
            return txn
        except AssertionError as e:
            error_message = str(e)
            try:
                hash_value = error_message.split(" - ")[-1].strip()
                self.logger.error(f"assertionError: https://explorer.aptoslabs.com/txn/{hash_value}?network=mainnet")
                return 0
            except json.JSONDecodeError:
                self.logger.error(f"assertionError: {error_message}")
                return 0
        except Exception as e:
            self.logger.critical(f"an unexpected error occurred: {e}")
            return 0

    def cell_wrap(self, amount_wei):
        if self._swap_to_cell(amount_wei):
            hash = self._lock_cell()
            argument0 = find_token_address(hash)
            if argument0 is not None:
                if self.vote_cell(argument0):
                    return 1
                else:
                    logger.error("error while voting")
                    return 0
            else:
                logger.error("error while finding cell argument")
                return 0
        else:
            logger.error("error while swapping apt to cell")
            return 0

    def _swap_to_cell(self, amount_apt_wei: int):
        payload = {
            "function": "0x4bf51972879e3b95c4781a5cdcb9e1ee24ef483e7d22f2d903626f126df62bd1::router::swap_route_entry_from_coin",
            "type_arguments": [
                "0x1::aptos_coin::AptosCoin"
            ],
            "arguments": [
                str(amount_apt_wei),
                str(int(amount_apt_wei * 15)),
                [
                    {
                        "inner": "0x2ebb2ccac5e027a87fa0e2e5f656a3a4238d6a48d93ec9b610d570fc0aa0df12"
                    }
                ],
                [
                    False
                ],
                str(self.address)
            ],
            "type": "entry_function_payload"
        }

        self.logger.info(f"{self.address} swapping {amount_apt_wei / 10 ** 8} APT to CELL")
        return self._submit_and_log_transaction(payload)

    def claim(self, verify_ids, signature, signature_expired_at):

        payload = {
            "function": "0xe7c7bb0e53fc6fb86aa7464645fbac96b96716463b4e2269c62945c135aa26fd::oat::claim",
            "type_arguments": [],
            "arguments": [
                "0x092d2f7ad00630e4dfffcca01bee12c84edf004720347fb1fd57016d2cc8d3f8",
                str(verify_ids),
                "0",
                "[CLAIM ONLY] Quest Four - Aptos Ecosystem Fundamentals",
                "1",
                str(signature_expired_at),
                str(signature)
            ],
            "type": "entry_function_payload"
        }

        return self._submit_and_log_transaction(payload)


if __name__ == "__main__":
    m = AptosTxnManager('')
