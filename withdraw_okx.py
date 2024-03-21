from config import *
import ccxt
import time
import random
from loguru import logger

TOKEN = 'APT'
NETWORK = 'Aptos'

def refuel_wrap(txn_manager, account):
    balance_before = txn_manager.get_account_balance()
    readable_balance = balance_before / 10 ** 8
    logger.info(f"initial balance for account №{account.account_number} [{account.address}]: {readable_balance} APT")

    if readable_balance < REFUEL_THRESHOLD:
        amount = round(random.uniform(MIN_AMOUNT_WITHDRAW, MAX_AMOUNT_WITHDRAW), 4)
        logger.error(f'balance ({readable_balance}) < REFUEL_THRESHOLD ({REFUEL_THRESHOLD})')
        logger.warning(f"refueling account №{account.account_number} [{account.address}] with {amount} APT")

        if not okx_withdraw(str(account.address), amount):
            return False

        timeout, check_interval, start_time = 10 * 60, 30, time.time()
        while time.time() - start_time < timeout:
            current_balance = txn_manager.get_account_balance()
            if current_balance > balance_before:
                logger.info(f"account №{account.account_number} [{account.address}] refueled. "
                            f"new balance: {current_balance / 10 ** 8}")
                return True
            logger.info(f"waiting for funds to arrive for account №{account.account_number} [{account.address}]...")
            time.sleep(check_interval)
        else:
            logger.error(f"funds did not arrive within the 10-min period for "
                         f"№{account.account_number} [{account.address}].")
            return False
    else:
        logger.success(f'balance ({readable_balance}) > REFUEL_THRESHOLD ({REFUEL_THRESHOLD})')
        return True
def okx_withdraw(address, amount_to_withdraw):
    exchange = ccxt.okx({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'password': PASSPHRASE,
        'enableRateLimit': True,
    })

    max_retries = 20
    retry_delay = 2
    chain_name = f"{TOKEN}-{NETWORK}"

    for attempt in range(1, max_retries + 1):
        try:
            withdraw_params = {
                "toAddress": address,
                "chainName": chain_name,
                "dest": 4,
                "fee": 0.001,
                "pwd": '-',
                "amt": amount_to_withdraw,
                "network": NETWORK
            }

            exchange.withdraw(TOKEN, amount_to_withdraw, address, params=withdraw_params)
            logger.success(f'transferred {amount_to_withdraw} {TOKEN} to {address}')
            return True

        except Exception as error:
            logger.error(f'attempt {attempt}: Failed to transfer {amount_to_withdraw} {TOKEN}: {error}')

            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                logger.error(f"all attempts failed after {max_retries} retries.")
                return False