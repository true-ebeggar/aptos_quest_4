import os
import random
import time
import traceback

from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from loguru import logger

from config import *
from contracts import *
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

def onchain_tasks(account_number):
    with DBSession() as session:
        account = session.query(Account).filter_by(account_number=account_number).first()
        if not account:
            logger.error(f"Account_number: {account_number} not found. Exiting process.")
            return
        txn_manager = AptosTxnManager(account.private_key)
        if REFUEL:
            if not refuel_wrap(txn_manager, account):
                return

        if account.stage_1 != 0:
            logger.warning(f'it look like address {account.address} already done onchain tasks')
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
                account.stage_1 = 1
                session.commit()
                s = random.randint(SLEEP_MIN, SLEEP_MAX)
                logger.warning(f"thread will sleep for {s}-sec")


        except Exception as e:
            logger.critical(f"Error while swapping: {str(e)}")
            logger.critical(f"Error occurred in account {account_number} with token {random_token_key}")
            logger.critical(f"Traceback: {traceback.format_exc()}")

def treading(task):
    with DBSession() as session:
        accounts = session.query(Account).all()
        if SHUFFLE_ACCOUNTS:
            random.shuffle(accounts)

    with ThreadPoolExecutor(max_workers=MAX_THREAD) as executor:
        futures = []
        for account in accounts:
            future = executor.submit(task, account.account_number)
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

    choice = input("\nEnter your choice: ")

    if choice == "1":
        treading(onchain_tasks)
    else:
        print("Invalid choice. Please try again.")
