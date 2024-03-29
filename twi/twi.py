import asyncio
import json

import twitter
from loguru import logger
from aptos_quest_4.config import SMART_PROXY_URL

class TwitterAction:
    def __init__(self, twi_token):
        try:
            self.account = twitter.Account(auth_token=twi_token, proxy=SMART_PROXY_URL)
            self.client = twitter.Client(self.account)
        except Exception as e:
            logger.critical('error while creating manager instance, probably due to bad token'
                            f'\nError: {e}')

    async def twitter_action(self):
        follow = await self.client.follow("1736572729585770496")
        follow2 = await self.client.follow("1748571796310478848")
        if follow is True and follow2 is True:
            return True
        else:
            return False

    async def make_post_for_binding(self, gid: str):
        tweet_text = f'Verifying my Twitter account for my #GalxeID gid:{gid} @Galxe \n\n galxe.com/galxeid'
        tweet = await self.client.tweet(tweet_text)
        logger.info(f'made post and got post id: {tweet}')
        return tweet

    async def get_username(self):
        data = await self.client.request_user()
        return data.raw_data['legacy']['screen_name']

    async def main(self):
        pass


if __name__ == "__main__":
    pass
    # asyncio.run(main())