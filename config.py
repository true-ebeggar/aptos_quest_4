REFUEL = True
REFUEL_THRESHOLD = 0.5
API_KEY = "553f424f-b5d1-4054-bcdb-17689ceab4be"
API_SECRET = "BAF145E68CA0636D17FDFE6314BB6041"
PASSPHRASE = 'Zetca1337((('
MIN_AMOUNT_WITHDRAW, MAX_AMOUNT_WITHDRAW = 0.01, 0.1

SHUFFLE_ACCOUNTS = False
MAX_THREAD = 3

AMOUNT_TO_STAKE_MIN, AMOUNT_TO_STAKE_MAX = 0.01, 0.03
SLEEP_FOR_THREAD_MIN, SLEEP_FOR_THREAD_MAX = 60, 100

MAX_SLIPPAGE_PERCENT = 3
SLEEP_MIN, SLEEP_MAX = 500, 2000






# Token Mapping
TOKEN_MAP = {
    'usdc': {
        'resource': '0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC',
        'decimals': 6,
        'router': '0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::curves::Uncorrelated',
        'function': '0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::scripts_v2::swap'
    },
    'usdt': {
        'resource': '0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDT',
        'decimals': 6,
        'router': '0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::curves::Uncorrelated',
        'function': '0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::scripts_v2::swap'
    },
    'weth': {
        'resource': '0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::WETH',
        'decimals': 6,
        'router': "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::curves::Uncorrelated",
        'function': "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::scripts_v2::swap"
    },
}

# Network Node
NODE = "https://fullnode.mainnet.aptoslabs.com/v1"  # The URL of the blockchain node to connect to for transactions.

