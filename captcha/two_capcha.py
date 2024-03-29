import uuid
import json
from datetime import datetime
from twocaptcha import TwoCaptcha

from aptos_quest_4.config import TWO_CAPTCHA_KEY
from loguru import logger

solver = TwoCaptcha(TWO_CAPTCHA_KEY)


def get_captcha_output():
    try:
        logger.info("Starting solve captcha")
        now_ms = int(datetime.now().timestamp() * 1000)
        result = solver.geetest_v4(captcha_id='244bcb8b9846215df5af4c624a750db4',
                                   url=f'https://gcaptcha4.geetest.com/load?captcha_id=244bcb8b9846215df5af4c624a750db4&'
                                       f'challenge={str(uuid.uuid4())}&client_type=web&lang=en-us&callback=geetest_{now_ms}',
                                   callback=f'geetest_{now_ms}')
        code_str = result.get('code')
        if code_str:
            code_dict = json.loads(code_str)
            lot_number = code_dict.get('lot_number')
            pass_token = code_dict.get('pass_token')
            gen_time = code_dict.get('gen_time')
            captcha_output = code_dict.get('captcha_output')
            logger.info("Got captcha data")
            return lot_number, pass_token, gen_time, captcha_output
        else:
            logger.error("No 'code' field in captcha result")
    except Exception as e:
        logger.critical(f"Error while solving captcha."
                        f"\nException: {e}")
