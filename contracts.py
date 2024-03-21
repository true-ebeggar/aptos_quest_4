pool_addresses = [
    "0x85d3337c4ca94612f278c5164d2b21d0d83354648bf9555272b5f9d8f1f33b2a",
    "0x234f0be57d6acfb2f0f19c17053617311a8d03c9ce358bdf9cd5c460e4a02b7c",
    "0x1ef2be2a92393c09ac5bc5e5b934a831611ebab5c4f2419d1d35f0552abec5f6",
    "0xcd50c2dac7b902a653dc602faaa6ef7b81084fce365050593fea0f3bee96f6be",
    "0x1e9cf70ab184026fa1eafc3cc4a4bd0012418425049e60856ea249f72f94ba8a",
    "0x45a72801a76b89bb3786f693db1a23bcc2e80dbf69b53ad8405111cdc69595ba",
    "0xe3939aa0732d67dc0a4e2b5072a7975a0d279c8e93a2756f39ae4c0e5b9abcca",
    "0x5669f388059383ab806e0dfce92196304205059874fd845944137d96bbdfc8de",
    "0xf7d4a97f8a82b1454cd69f92b5a5bd5bcad609e44a6cf56377755adcfca5863a",
    "0x802960f795a5a6055c2662db55ec7dcb8610e12c0569fb8ed7953dc9a8e77876",
    "0xd18e396d497ceef12dbcc81c49e4308eca127492d820ae1628d9ed15ce73f538",
    "0xcfaadbe8c0cc5c7cdaa3aefd7c184830d12f2991d1ae70176337550b155a1780",
    "0xce0fd635bfa3a93ea4f33022a7a02e3d400841d9fe409381f8028df4b52b04aa",
    "0xde840ae644c74651a5000001de6fc12cc4194109a7501485cbc55960c614f139"
]

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