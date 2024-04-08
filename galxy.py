# Standard library imports
import asyncio
import json
from datetime import datetime, timedelta
from time import time

# Third-party imports
import nltk
import requests
from nltk.corpus import words
from pyuseragents import random as random_user_agent
from aptos_sdk.account import Account as acccount

# Local imports
from config import SMART_PROXY_URL
from captcha.two_capcha import get_captcha_output
from loguru import logger
from twi.twi import TwitterAction
# NLTK setup
nltk.download('words', quiet=True)


class GalaxyAccountManager:
    def __init__(self, account_evm=None, account_apt=None):
        if account_apt is not None:
            self.account_apt = account_apt
        if account_evm is not None:
            self.account_evm = account_evm
        self.galaxy_query = 'https://graphigo.prd.galaxy.eco/query'
        self.word_list = words.words()
        self.proxies = {
                'http': SMART_PROXY_URL,
                'https': SMART_PROXY_URL
        }
        self.token = None

    def unlink_twitter(self):
        headers = self.galaxy_headers(content_length=300)

        payload = {
            "operationName": "DeleteSocialAccount",
            "variables": {
                "input": {
                    "address": F"APTOS:{self.account_apt.address()}",
                    "type": "TWITTER"
                }
            },
            "query": """
            mutation DeleteSocialAccount($input: DeleteSocialAccountInput!) {
              deleteSocialAccount(input: $input) {
                code
                message
                __typename
              }
            }
            """
        }
        try:
            response = requests.post(self.galaxy_query, headers=headers, json=payload, proxies=self.proxies)
            response_json = response.json()
            # print(json.dumps(response.json(), indent=4))

            if response.status_code == 200 and response_json == {"data": {"deleteSocialAccount": None}}:
                print(json.dumps(response_json, indent=4))
                logger.info('Twitter unlinked successfully')
                return True
            else:
                logger.error(f"{self.account_evm.address} Unlink failed."
                                  f"\nResponse code: {response.status_code}."
                                  f"\nResponse content {response.content}")
                return None

        except Exception as e:
            logger.critical(f"Unlink failed."
                            f"\nException: {e}")
            return None

    def sign_in_apt(self):
        try:
            now = datetime.utcnow()
            next_day = now + timedelta(days=7)
            iso_time_next_day = next_day.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            current_time = int(time())
            rounded_time = int(current_time - (current_time % 3600))

            message = (f"Galxe.com wants you to sign in with your Aptos account: "
                       f"{self.account_apt.address()}; "
                       f"<Public key: {self.account_apt.public_key()}>, "
                       f"<Version: 1>, "
                       f"<Chain ID: 1>, "
                       f"<Nonce: {rounded_time}>, "
                       f"<Expiration Time: {iso_time_next_day}>")

            full_message = f'APTOS\nmessage: {message}\nnonce: {rounded_time}'

            signature = self.account_apt.sign(full_message.encode('utf-8'))

            data = {
                "operationName": "SignIn",
                "variables": {
                    "input": {
                        "address": str(self.account_apt.address()),
                        "message": message,
                        "signature": str(signature.signature.hex())
                    }
                },
                "query": """
            mutation SignIn($input: Auth) {
              signin(input: $input)
            }
            """
            }

            response = requests.post(self.galaxy_query, json=data, proxies=self.proxies)
            # print(json.dumps(response.json(), indent=4))

            if response.status_code == 200 and 'signin' in response.text:
                signin = response.json()['data']['signin']
                logger.info('Got the signIn token')
                self.token = signin
                return signin
            else:
                logger.error(f"{self.account_apt.address()} Login failed."
                             f"\nResponse code: {response.status_code}."
                             f"\nResponse content {response.content}")
                return None

        except Exception as e:
            logger.critical(f"Login failed."
                            f"\nException: {e}")
            return None

    async def link_twitter(self, token: str):
        data = self.get_user_info(self.account_apt.address())
        gid = data['data']['addressInfo']['id']
        twi = data['data']['addressInfo']['hasTwitter']
        if twi:
            logger.warning(f"another twitter ({data['data']['addressInfo']['twitterUserName']}) is bind to account,"
                           f"unbinding and continue")
            self.unlink_twitter()

        try:
            action = TwitterAction(token)
            await action.twitter_action()
            post_id = await action.make_post_for_binding(gid)
            if post_id is None:
                logger.error("post_id is None, dropping process")
                return False
            name = await action.get_username()
        except Exception as e:
            logger.error('error during twitter action, check token'
                         f'\nerror: {e}')
            return False

        payload = {
            "operationName": "VerifyTwitterAccount",
            "variables": {
                "input": {
                    "address": f"APTOS:{str(self.account_apt.address())}",
                    "tweetURL": f"https://twitter.com/{name}/status/{post_id}"
                }
            },
            "query": """
                mutation VerifyTwitterAccount($input: VerifyTwitterAccountInput!) {
                  verifyTwitterAccount(input: $input) {
                    address
                    twitterUserID
                    twitterUserName
                    __typename
                  }
                }
            """
        }
        try:
            headers = self.galaxy_headers(content_length=418)
            response = requests.post(self.galaxy_query, headers=headers, json=payload, proxies=self.proxies)
            # print(json.dumps(response.json(), indent=4))

            if response.json()['data']['verifyTwitterAccount']['twitterUserName'] == name:
                logger.success(f"twitter is bind to {self.account_apt.address()}")
                return True
            else:
                return False
        except Exception as e:
            logger.critical(f"Exception during twitter binding"
                            f"\nException: {e}")
            return False

    def get_user_info(self, user_address: str):
        headers = self.galaxy_headers()
        payload = {
            "operationName": "BasicUserInfo",
            "variables": {"address": f"APTOS:{user_address}"},
            "query": """query BasicUserInfo($address: String!) {
                                    addressInfo(address: $address) {
                                        id
                                        username
                                        address
                                        aptosAddress
                                        hasEvmAddress
                                        hasAptosAddress
                                        hasTwitter
                                        twitterUserID
                                        twitterUserName
                                    }
                                }"""
        }
        try:
            response = requests.post(self.galaxy_query, headers=headers, json=payload, proxies=self.proxies)
            # print(json.dumps(response.json(), indent=4))

            if response.status_code == 200:
                logger.info("user info retrieved")
                return response.json()
            else:
                logger.error(f"Failed to retrieve user info for address: {user_address}.\nResponse: {response.text}")
                return None
        except Exception as e:
            logger.critical(f"Exception during user info retrieval for address: {user_address}.\nException: {e}")
            return None

    def prepare_twitter(self, credId: str):
        headers = self.galaxy_headers(content_length=1056)
        lot_number, pass_token, gen_time, captcha_output = get_captcha_output()
        payload = {
            "operationName": "AddTypedCredentialItems",
            "variables": {
                "input": {
                    "credId": credId,
                    "campaignId": "GCm4Ct4fp8",
                    "operation": "APPEND",
                    "items": [
                        f"APTOS:{str(self.account_apt.address())}"
                    ],
                    "captcha": {
                        "lotNumber": lot_number,
                        "captchaOutput": captcha_output,
                        "passToken": pass_token,
                        "genTime": gen_time
                    }
                }
            },
            "query": "mutation AddTypedCredentialItems($input: MutateTypedCredItemInput!) {\n  typedCredentialItems(input: $input) {\n    id\n    __typename\n  }\n}\n"
        }
        try:
            response = requests.post(self.galaxy_query, headers=headers, json=payload, proxies=self.proxies)
            print(json.dumps(response.json(), indent=4))
        except Exception as e:
            logger.critical(f"\nException: {e}")

    def confirm_twitter(self, credId: str):
        headers = self.galaxy_headers(content_length=1671)
        lot_number, pass_token, gen_time, captcha_output = get_captcha_output()
        payload = {
            "operationName": "SyncCredentialValue",
            "variables": {
                "input": {
                    "syncOptions": {
                        "credId": credId,
                        "address": f"APTOS:{self.account_apt.address()}",
                        "twitter": {
                            "campaignID": "GCm4Ct4fp8",
                            "captcha": {
                                "lotNumber": lot_number,
                                "captchaOutput": captcha_output,
                                "passToken": pass_token,
                                "genTime": gen_time
                            }
                        }
                    }
                }
            },
            "query": "mutation SyncCredentialValue($input: SyncCredentialValueInput!) {\n  syncCredentialValue(input: $input) {\n    value {\n      address\n      spaceUsers {\n        follow\n        points\n        participations\n        __typename\n      }\n      campaignReferral {\n        count\n        __typename\n      }\n      gitcoinPassport {\n        score\n        lastScoreTimestamp\n        __typename\n      }\n      walletBalance {\n        balance\n        __typename\n      }\n      multiDimension {\n        value\n        __typename\n      }\n      allow\n      survey {\n        answers\n        __typename\n      }\n      quiz {\n        allow\n        correct\n        __typename\n      }\n      __typename\n    }\n    message\n    __typename\n  }\n}\n"
        }
        try:
            response = requests.post(self.galaxy_query, headers=headers, json=payload, proxies=self.proxies)
            print(json.dumps(response.json(), indent=4))
            if response.status_code == 200:
                return response.json()['data']['syncCredentialValue']['value']['allow']
            else:
                logger.error(f"wrong status code {response.status_code}.\nResponse: {response.json()}")
                return False
        except Exception as e:
            logger.critical(f"\nException: {e}")
            return False

    def check_approve(self):
        headers = self.galaxy_headers()
        payload = {
            "operationName": "CampaignDetailAll",
            "variables": {
                "address": f"APTOS:{self.account_apt.address()}",
                "id": 'GCm4Ct4fp8',
                'withAddress': True
            },
            "query": "query CampaignDetailAll($id: ID!, $address: String!, $withAddress: Boolean!) {\n  campaign(id: $id) {\n    ...CampaignForSiblingSlide\n    coHostSpaces {\n      ...SpaceDetail\n      isAdmin(address: $address) @include(if: $withAddress)\n      isFollowing @include(if: $withAddress)\n      followersCount\n      categories\n      __typename\n    }\n    bannerUrl\n    ...CampaignDetailFrag\n    userParticipants(address: $address, first: 1) @include(if: $withAddress) {\n      list {\n        status\n        premintTo\n        __typename\n      }\n      __typename\n    }\n    space {\n      ...SpaceDetail\n      isAdmin(address: $address) @include(if: $withAddress)\n      isFollowing @include(if: $withAddress)\n      followersCount\n      categories\n      __typename\n    }\n    isBookmarked(address: $address) @include(if: $withAddress)\n    inWatchList\n    claimedLoyaltyPoints(address: $address) @include(if: $withAddress)\n    parentCampaign {\n      id\n      isSequencial\n      thumbnail\n      __typename\n    }\n    isSequencial\n    numNFTMinted\n    childrenCampaigns {\n      ...ChildrenCampaignsForCampaignDetailAll\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment CampaignDetailFrag on Campaign {\n  id\n  ...CampaignMedia\n  ...CampaignForgePage\n  ...CampaignForCampaignParticipantsBox\n  name\n  numberID\n  type\n  inWatchList\n  cap\n  info\n  useCred\n  smartbalancePreCheck(mintCount: 1)\n  smartbalanceDeposited\n  formula\n  status\n  seoImage\n  creator\n  tags\n  thumbnail\n  gasType\n  isPrivate\n  createdAt\n  requirementInfo\n  description\n  enableWhitelist\n  chain\n  startTime\n  endTime\n  requireEmail\n  requireUsername\n  blacklistCountryCodes\n  whitelistRegions\n  rewardType\n  distributionType\n  rewardName\n  claimEndTime\n  loyaltyPoints\n  tokenRewardContract {\n    id\n    address\n    chain\n    __typename\n  }\n  tokenReward {\n    userTokenAmount\n    tokenAddress\n    depositedTokenAmount\n    tokenRewardId\n    tokenDecimal\n    tokenLogo\n    tokenSymbol\n    __typename\n  }\n  nftHolderSnapshot {\n    holderSnapshotBlock\n    __typename\n  }\n  spaceStation {\n    id\n    address\n    chain\n    __typename\n  }\n  ...WhitelistInfoFrag\n  ...WhitelistSubgraphFrag\n  gamification {\n    ...GamificationDetailFrag\n    __typename\n  }\n  creds {\n    id\n    name\n    type\n    credType\n    credSource\n    referenceLink\n    description\n    lastUpdate\n    lastSync\n    syncStatus\n    credContractNFTHolder {\n      timestamp\n      __typename\n    }\n    chain\n    eligible(address: $address, campaignId: $id)\n    subgraph {\n      endpoint\n      query\n      expression\n      __typename\n    }\n    dimensionConfig\n    value {\n      gitcoinPassport {\n        score\n        lastScoreTimestamp\n        __typename\n      }\n      __typename\n    }\n    commonInfo {\n      participateEndTime\n      modificationInfo\n      __typename\n    }\n    __typename\n  }\n  credentialGroups(address: $address) {\n    ...CredentialGroupForAddress\n    __typename\n  }\n  rewardInfo {\n    discordRole {\n      guildId\n      guildName\n      roleId\n      roleName\n      inviteLink\n      __typename\n    }\n    premint {\n      startTime\n      endTime\n      chain\n      price\n      totalSupply\n      contractAddress\n      banner\n      __typename\n    }\n    loyaltyPoints {\n      points\n      __typename\n    }\n    loyaltyPointsMysteryBox {\n      points\n      weight\n      __typename\n    }\n    __typename\n  }\n  participants {\n    participantsCount\n    bountyWinnersCount\n    __typename\n  }\n  taskConfig(address: $address) {\n    participateCondition {\n      conditions {\n        ...ExpressionEntity\n        __typename\n      }\n      conditionalFormula\n      eligible\n      __typename\n    }\n    rewardConfigs {\n      id\n      conditions {\n        ...ExpressionEntity\n        __typename\n      }\n      conditionalFormula\n      description\n      rewards {\n        ...ExpressionReward\n        __typename\n      }\n      eligible\n      rewardAttrVals {\n        attrName\n        attrTitle\n        attrVal\n        __typename\n      }\n      __typename\n    }\n    referralConfig {\n      id\n      conditions {\n        ...ExpressionEntity\n        __typename\n      }\n      conditionalFormula\n      description\n      rewards {\n        ...ExpressionReward\n        __typename\n      }\n      eligible\n      rewardAttrVals {\n        attrName\n        attrTitle\n        attrVal\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  referralCode(address: $address)\n  recurringType\n  latestRecurringTime\n  nftTemplates {\n    id\n    image\n    treasureBack\n    __typename\n  }\n  __typename\n}\n\nfragment CampaignMedia on Campaign {\n  thumbnail\n  rewardName\n  type\n  gamification {\n    id\n    type\n    __typename\n  }\n  __typename\n}\n\nfragment CredentialGroupForAddress on CredentialGroup {\n  id\n  description\n  credentials {\n    ...CredForAddressWithoutMetadata\n    __typename\n  }\n  conditionRelation\n  conditions {\n    expression\n    eligible\n    ...CredentialGroupConditionForVerifyButton\n    __typename\n  }\n  rewards {\n    expression\n    eligible\n    rewardCount\n    rewardType\n    __typename\n  }\n  rewardAttrVals {\n    attrName\n    attrTitle\n    attrVal\n    __typename\n  }\n  claimedLoyaltyPoints\n  __typename\n}\n\nfragment CredForAddressWithoutMetadata on Cred {\n  id\n  name\n  type\n  credType\n  credSource\n  referenceLink\n  description\n  lastUpdate\n  lastSync\n  syncStatus\n  credContractNFTHolder {\n    timestamp\n    __typename\n  }\n  chain\n  eligible(address: $address)\n  subgraph {\n    endpoint\n    query\n    expression\n    __typename\n  }\n  dimensionConfig\n  value {\n    gitcoinPassport {\n      score\n      lastScoreTimestamp\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment CredentialGroupConditionForVerifyButton on CredentialGroupCondition {\n  expression\n  eligibleAddress\n  __typename\n}\n\nfragment WhitelistInfoFrag on Campaign {\n  id\n  whitelistInfo(address: $address) {\n    address\n    maxCount\n    usedCount\n    claimedLoyaltyPoints\n    currentPeriodClaimedLoyaltyPoints\n    currentPeriodMaxLoyaltyPoints\n    __typename\n  }\n  __typename\n}\n\nfragment WhitelistSubgraphFrag on Campaign {\n  id\n  whitelistSubgraph {\n    query\n    endpoint\n    expression\n    variable\n    __typename\n  }\n  __typename\n}\n\nfragment GamificationDetailFrag on Gamification {\n  id\n  type\n  nfts {\n    nft {\n      id\n      animationURL\n      category\n      powah\n      image\n      name\n      treasureBack\n      nftCore {\n        ...NftCoreInfoFrag\n        __typename\n      }\n      traits {\n        name\n        value\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  airdrop {\n    name\n    contractAddress\n    token {\n      address\n      icon\n      symbol\n      __typename\n    }\n    merkleTreeUrl\n    addressInfo(address: $address) {\n      index\n      amount {\n        amount\n        ether\n        __typename\n      }\n      proofs\n      __typename\n    }\n    __typename\n  }\n  forgeConfig {\n    minNFTCount\n    maxNFTCount\n    requiredNFTs {\n      nft {\n        category\n        powah\n        image\n        name\n        nftCore {\n          capable\n          contractAddress\n          __typename\n        }\n        __typename\n      }\n      count\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment NftCoreInfoFrag on NFTCore {\n  id\n  capable\n  chain\n  contractAddress\n  name\n  symbol\n  dao {\n    id\n    name\n    logo\n    alias\n    __typename\n  }\n  __typename\n}\n\nfragment ExpressionEntity on ExprEntity {\n  cred {\n    id\n    name\n    type\n    credType\n    credSource\n    dimensionConfig\n    referenceLink\n    description\n    lastUpdate\n    lastSync\n    chain\n    eligible(address: $address)\n    metadata {\n      visitLink {\n        link\n        __typename\n      }\n      twitter {\n        isAuthentic\n        __typename\n      }\n      worldcoin {\n        dimensions {\n          values {\n            value\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    commonInfo {\n      participateEndTime\n      modificationInfo\n      __typename\n    }\n    __typename\n  }\n  attrs {\n    attrName\n    operatorSymbol\n    targetValue\n    __typename\n  }\n  attrFormula\n  eligible\n  eligibleAddress\n  __typename\n}\n\nfragment ExpressionReward on ExprReward {\n  arithmetics {\n    ...ExpressionEntity\n    __typename\n  }\n  arithmeticFormula\n  rewardType\n  rewardCount\n  rewardVal\n  __typename\n}\n\nfragment CampaignForgePage on Campaign {\n  id\n  numberID\n  chain\n  spaceStation {\n    address\n    __typename\n  }\n  gamification {\n    forgeConfig {\n      maxNFTCount\n      minNFTCount\n      requiredNFTs {\n        nft {\n          category\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment CampaignForCampaignParticipantsBox on Campaign {\n  ...CampaignForParticipantsDialog\n  id\n  chain\n  space {\n    id\n    isAdmin(address: $address)\n    __typename\n  }\n  participants {\n    participants(first: 10, after: \"-1\", download: false) {\n      list {\n        address {\n          id\n          avatar\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    participantsCount\n    bountyWinners(first: 10, after: \"-1\", download: false) {\n      list {\n        createdTime\n        address {\n          id\n          avatar\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    bountyWinnersCount\n    __typename\n  }\n  __typename\n}\n\nfragment CampaignForParticipantsDialog on Campaign {\n  id\n  name\n  type\n  rewardType\n  chain\n  nftHolderSnapshot {\n    holderSnapshotBlock\n    __typename\n  }\n  space {\n    isAdmin(address: $address)\n    __typename\n  }\n  rewardInfo {\n    discordRole {\n      guildName\n      roleName\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment SpaceDetail on Space {\n  id\n  name\n  info\n  thumbnail\n  alias\n  status\n  links\n  isVerified\n  discordGuildID\n  followersCount\n  nftCores(input: {first: 1}) {\n    list {\n      id\n      marketLink\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment ChildrenCampaignsForCampaignDetailAll on Campaign {\n  space {\n    ...SpaceDetail\n    isAdmin(address: $address) @include(if: $withAddress)\n    isFollowing @include(if: $withAddress)\n    followersCount\n    categories\n    __typename\n  }\n  ...CampaignDetailFrag\n  claimedLoyaltyPoints(address: $address) @include(if: $withAddress)\n  userParticipants(address: $address, first: 1) @include(if: $withAddress) {\n    list {\n      status\n      __typename\n    }\n    __typename\n  }\n  parentCampaign {\n    id\n    isSequencial\n    __typename\n  }\n  __typename\n}\n\nfragment CampaignForSiblingSlide on Campaign {\n  id\n  space {\n    id\n    alias\n    __typename\n  }\n  parentCampaign {\n    id\n    thumbnail\n    isSequencial\n    childrenCampaigns {\n      id\n      ...CampaignForGetImage\n      ...CampaignForCheckFinish\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment CampaignForCheckFinish on Campaign {\n  claimedLoyaltyPoints(address: $address)\n  whitelistInfo(address: $address) {\n    usedCount\n    __typename\n  }\n  __typename\n}\n\nfragment CampaignForGetImage on Campaign {\n  ...GetImageCommon\n  nftTemplates {\n    image\n    __typename\n  }\n  __typename\n}\n\nfragment GetImageCommon on Campaign {\n  ...CampaignForTokenObject\n  id\n  type\n  thumbnail\n  __typename\n}\n\nfragment CampaignForTokenObject on Campaign {\n  tokenReward {\n    tokenAddress\n    tokenSymbol\n    tokenDecimal\n    tokenLogo\n    __typename\n  }\n  tokenRewardContract {\n    id\n    chain\n    __typename\n  }\n  __typename\n}\n"
        }
        try:
            response = requests.post(self.galaxy_query, headers=headers, json=payload, proxies=self.proxies)
            # print(json.dumps(response.json(), indent=4))
            if response.status_code == 200:
                credentials_list = response.json()['data']['campaign']['credentialGroups'][0]['credentials']
                eligible_value = None
                for cred in credentials_list:
                    if cred['id'] == '397897604815392768':
                        eligible_value = cred['eligible']
                        break
                if eligible_value == 1:
                    logger.success(f"it look like wallet {self.account_apt.address()}"
                                   f" is approved, connection twitter and claim")
                    return True
            else:
                logger.error(f"wrong status code {response.status_code}.\nResponse: {response.json()}")
                return False
        except Exception as e:
            logger.critical(f"\nException: {e}")
            return False

    def get_txn_data(self):
        lot_number, pass_token, gen_time, captcha_output = get_captcha_output()
        try:
            payload = {
                "operationName": "PrepareParticipate",
                "variables": {
                    "input": {
                        "signature": "",
                        "campaignID": "GCm4Ct4fp8",
                        "address": f"APTOS:{self.account_apt.address()}",
                        "mintCount": 1,
                        "chain": "APTOS",
                        "captcha": {
                            "lotNumber": str(lot_number),
                            "captchaOutput": str(captcha_output),
                            "passToken": str(pass_token),
                            "genTime": str(gen_time)
                        }
                    }
                },
                "query": "mutation PrepareParticipate($input: PrepareParticipateInput!) {\n  prepareParticipate(input: $input) {\n    allow\n    disallowReason\n    signature\n    nonce\n    mintFuncInfo {\n      funcName\n      nftCoreAddress\n      verifyIDs\n      powahs\n      cap\n      __typename\n    }\n    extLinkResp {\n      success\n      data\n      error\n      __typename\n    }\n    metaTxResp {\n      metaSig2\n      autoTaskUrl\n      metaSpaceAddr\n      forwarderAddr\n      metaTxHash\n      reqQueueing\n      __typename\n    }\n    solanaTxResp {\n      mint\n      updateAuthority\n      explorerUrl\n      signedTx\n      verifyID\n      __typename\n    }\n    aptosTxResp {\n      signatureExpiredAt\n      tokenName\n      __typename\n    }\n    tokenRewardCampaignTxResp {\n      signatureExpiredAt\n      verifyID\n      __typename\n    }\n    loyaltyPointsTxResp {\n      TotalClaimedPoints\n      __typename\n    }\n    flowTxResp {\n      Name\n      Description\n      Thumbnail\n      __typename\n    }\n    __typename\n  }\n}\n"
            }

            response = requests.post(self.galaxy_query, headers=self.galaxy_headers(content_length=1939),
                                     json=payload, proxies=self.proxies)

            if response.status_code == 200:
                response_data = response.json()
                print(json.dumps(response_data, indent=4))
                if 'data' in response_data and 'prepareParticipate' in response_data['data']:
                    if response_data['data']['prepareParticipate']['allow']:
                        verify_ids = response_data['data']['prepareParticipate']['mintFuncInfo'].get('verifyIDs')
                        signature = response_data['data']['prepareParticipate'].get('signature')
                        signature_expired_at = response_data['data']['prepareParticipate']['aptosTxResp'].get(
                            'signatureExpiredAt')
                        if verify_ids:
                            verify_id = verify_ids[0]
                            logger.info("Transaction data gathered successfully.")
                            return verify_id, signature, signature_expired_at
                    else:
                        disallow_reason = response_data['data']['prepareParticipate'].get('disallowReason', '')
                        if "Exceed limit, available claim count is 0" in disallow_reason:
                            logger.info(
                                f"OAT is already claimed or address is not eligible (in both cases responses the same)")
                            return None
                        else:
                            logger.error(f"Transaction preparation failed due to: {disallow_reason}")
                            return None
                else:
                    logger.error("Transaction preparation failed. Invalid response format.")
                    return None
            else:
                logger.error(f"{self.account_apt.address()} Request failed."
                             f"\nResponse code: {response.status_code}."
                             f"\nResponse content: {response.text}")
                return None
        except Exception as e:
            logger.critical(f"Exception occurred."
                            f"\nException: {e}")
        return None

    def galaxy_headers(self, content_length=None):
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
            "Accept-Language": "en-GB,en;q=0.9",
            "Authorization": self.token,
            "Content-Type": "application/json",
            "Origin": "https://galxe.com",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "User-Agent": str(random_user_agent())
        }
        if content_length is not None:
            headers['Content-Length'] = str(content_length)
        return headers


if __name__ == "__main__":
    pass
