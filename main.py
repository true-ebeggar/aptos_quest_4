import asyncio
import os
import random
import traceback

from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from seleniumwire import webdriver
from aptos_sdk.account import Account as acccount

from config import *
from contracts import *
from google_form import *
from galxy import GalaxyAccountManager
from data.database_actions import initialize_database
from transaction_staff import AptosTxnManager
from withdraw_okx import refuel_wrap


if os.path.exists('accounts.db'):
    pass
else:
    initialize_database('accounts.db')
    logger.warning("database created, if you need new db, delete or rename current one...")

Base = declarative_base()


class Account(Base):
    __tablename__ = 'accounts'
    account_number = Column(Integer, primary_key=True)
    address = Column(String)
    private_key = Column(String)
    stage_1 = Column(Integer)
    stage_2 = Column(Integer)
    stage_3 = Column(Integer)


engine = create_engine('sqlite:///accounts.db')
Base.metadata.create_all(engine)
DBSession = sessionmaker(bind=engine)


def sleep():
    s = random.randint(SLEEP_MIN, SLEEP_MAX)
    logger.warning(f"thread will sleep for {s}-sec")
    time.sleep(s)
def onchain_tasks(account):
    with DBSession() as session:
        if not account:
            logger.error(f"there is no account supply for this function...")
            return

        txn_manager = AptosTxnManager(account.private_key)
        if REFUEL:
            if not refuel_wrap(txn_manager, account):
                return

        try:
            random_token_key = random.choice(list(TOKEN_MAP.keys()))
            swap_amount = round(random.uniform(AMOUNT_TO_STAKE_MIN, AMOUNT_TO_STAKE_MAX), 8)
            balance = txn_manager.get_account_balance()
            swap_amount_wei = int(swap_amount * 10 ** 8)
            if balance - swap_amount_wei < 100000:
                logger.critical(f'acc does not have required amount. '
                                f'acc balance - {balance / 10 ** 8}, required - {swap_amount}')
                return

            txn_manager.swap_apt_to_token(random_token_key, swap_amount_wei)
            value = txn_manager._get_coin_value(TOKEN_MAP[random_token_key]['resource'])
            if int(value) > 0:
                txn_manager.lend_token(random_token_key, value)
            else:
                logger.error("tokens required for landing not funded")
                return

            swap_amount2 = round(random.uniform(AMOUNT_TO_STAKE_MIN, AMOUNT_TO_STAKE_MAX), 8)
            swap_amount_wei2 = int(swap_amount2 * 10 ** 8)
            if txn_manager.cell_wrap(swap_amount_wei2):
                logger.success(f'account №{account.account_number} [{account.address}] complete task')
                account = session.query(Account).filter_by(account_number=account.account_number).first()
                account.stage_1 = 1
                session.commit()
                sleep()

        except Exception as e:
            session.rollback()
            logger.critical(f"error while doing onchain tasks {account.address}: {e}")
            logger.critical(f"traceback: {traceback.format_exc()}")


def form_task(account):
    with DBSession() as session:
        if not account:
            logger.error(f"there is no account supply for this function...")
            return

        try:
            script_dir = os.path.dirname(os.path.realpath(__file__))
            extension_dir = os.path.join(script_dir, extension_subdir)
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--new-window')  # Open Chrome in a new window
            chrome_options.add_argument(f'--load-extension={extension_dir}')

            driver = webdriver.Chrome(options=chrome_options)
            driver.get(GOOGLE_FORM_URL)

            with open('data/emails.txt', 'r') as file:
                lines = file.readlines()
                if not lines:
                    logger.warning("there is no lines in file 'data/emails.txt'")
                    return
                email = lines[0].strip()
            with open('data/emails.txt', 'w') as file:
                file.writelines(lines[1:])

            logger.info(f'attempt to fill form for account №{account.account_number} [{account.address}]')
            if fill_the_form(driver, str(account.address), email):
                logger.success(f'email {email} assigned to account №{account.account_number} [{account.address}]')
                account = session.query(Account).filter_by(account_number=account.account_number).first()
                account.stage_2 = email
                session.commit()
                driver.close()
                sleep()

        except Exception as e:
            session.rollback()
            logger.critical(f"error while filling form for address {account.address}: {e}")
            logger.critical(f"traceback: {traceback.format_exc()}")


def twitter_and_claim(account):
    with DBSession() as session:
        if not account:
            logger.error(f"there is no account supply for this function...")
            return
        account_apt = acccount.load_key(account.private_key)
        manager = GalaxyAccountManager(account_apt=account_apt)
        txn_manager = AptosTxnManager(account.private_key)
        if manager.check_approve():
            try:
                with open('data/twitter_tokens.txt', 'r') as file:
                    lines = file.readlines()
                    if not lines:
                        logger.warning("there is no lines in file 'data/emails.txt'")
                        return
                    token = lines[0].strip()
                with open('data/twitter_tokens.txt', 'w') as file:
                    file.writelines(lines[1:])

                logger.info(f'attempt to bind twitter for account №{account.account_number} [{account.address}]')
                manager.sign_in_apt()
                if asyncio.run(manager.link_twitter(token)):
                    logger.info(f'twitter token is prepared and bind to '
                                f'account №{account.account_number} [{account.address}]')
                    manager.prepare_twitter("388797856569397248")
                    manager.prepare_twitter('375866499102953472')
                    manager.confirm_twitter('388797856569397248')
                    manager.confirm_twitter('375866499102953472')
                    verify_id, signature, signature_expired_at = manager.get_txn_data()
                    if txn_manager.claim(verify_id, signature, signature_expired_at):
                        logger.success(f"OAT claimed, twitter token assigned to account "
                                       f"№{account.account_number} [{account.address}]")
                        account = session.query(Account).filter_by(account_number=account.account_number).first()
                        account.stage_2 = token
                        session.commit()
                        sleep()
            except Exception as e:
                session.rollback()
                logger.critical(f"error while doing twitter tasks and claim for address {account.address}: {e}")
                logger.critical(f"traceback: {traceback.format_exc()}")
        else:
            logger.info(f'account №{account.account_number} [{account.address}] is not approved, impossible to claim')
            return


def treading(task):
    with DBSession() as session:
        accounts = session.query(Account).all()
        if SHUFFLE_ACCOUNTS:
            random.shuffle(accounts)

    with ThreadPoolExecutor(max_workers=MAX_THREAD) as executor:
        futures = []
        for account in accounts:
            if account.stage_1 != 0 and task == onchain_tasks:
                logger.warning(f'it look like address {account.address} already done onchain tasks')
                continue
            if account.stage_2 != 0 and task == form_task:
                logger.warning(f'it look like address {account.address} already filled form')
                continue
            if account.stage_3 != 0 and task == twitter_and_claim:
                logger.warning(f'it look like address {account.address} already claim OAT')
                continue
            if account.stage_3 != 0 and task == form_task:
                logger.warning(f'it look like address {account.address} already claim OAT, no need to fill form')
                continue
            future = executor.submit(task, account)
            futures.append(future)

            s = random.randint(SLEEP_FOR_THREAD_MIN, SLEEP_FOR_THREAD_MAX)
            logger.info(f'waiting for {s}-sec before starting the next thread.')
            time.sleep(s)

            if len(futures) >= MAX_THREAD:
                done, _ = wait(futures, return_when=FIRST_COMPLETED)
                futures = [f for f in futures if f not in done]

    for future in as_completed(futures):
        future.result()


if __name__ == "__main__":

    print("\nMake your choice:")
    print("1. Onchain tasks")
    print('2. Form filler (selenium)')
    print('3. Claim')

    choice = input("\nEnter your choice: ")

    if choice == "1":
        treading(onchain_tasks)
    elif choice == '2':
        print("if form filled - email will be deleted from emails.txt and assigned to it address inside db")
        treading(form_task)
    elif choice == '3':
        print("if claimed - twitter token will be deleted from twitter_tokens.txt and assigned to it address inside db")
        treading(twitter_and_claim)
    else:
        print("Invalid choice. Please try again.")
