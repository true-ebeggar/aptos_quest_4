import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from config import GOOGLE_FORM_URL
from loguru import logger


extension_subdir = "CapSolver.Browser.Extension-chrome-v1.11.0"


def check_for_element_with_text(driver):
    end_time = time.time() + 30
    expected_text = "Your response has been recorded"
    while time.time() < end_time:
        try:
            element = driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[1]/div/div[3]')
            if element.text == expected_text:
                return True
        except NoSuchElementException:
            pass
        time.sleep(1)
    logger.error("expected text not found within 30-sec timeout")
    return False


def fill_the_form(driver, address: str, mail: str):
    driver.get(GOOGLE_FORM_URL)

    mail_input = "/html/body/div[1]/div[2]/form/div[2]/div/div[2]/div[1]/div/div[1]/div[2]/div[1]/div/div[1]/input"
    address_input = "/html/body/div[1]/div[2]/form/div[2]/div/div[2]/div[2]/div/div/div[2]/div/div[1]/div/div[1]/input"
    button_xpath = "/html/body/div[1]/div[2]/form/div[2]/div/div[3]/div[3]/div[1]/div"

    mail_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, mail_input)))
    address_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, address_input)))
    button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, button_xpath)))

    mail_input.send_keys(mail)
    address_input.send_keys(address)
    button.click()
    return check_for_element_with_text(driver)
