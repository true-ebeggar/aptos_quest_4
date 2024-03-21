import sqlite3
from aptos_sdk.account import Account

def initialize_database(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'")
    if not cursor.fetchone():
        cursor.execute('''CREATE TABLE accounts
                          (account_number INTEGER PRIMARY KEY,
                           address TEXT,
                           private_key TEXT,
                           stage_1 INTEGER DEFAULT 0,
                           stage_2 INTEGER DEFAULT 0,
                           stage_3 INTEGER DEFAULT 0)''')

    with open("aptos_quest_4\\data\\private_keys.txt", 'r') as pk_file:
        private_keys = pk_file.readlines()

    for i, private_key in enumerate(private_keys, start=1):
        acc = Account.load_key(private_key)
        cursor.execute("INSERT INTO accounts (account_number, address, private_key) VALUES (?, ?, ?)",
                       (i, str(acc.address()), private_key.strip()))

    conn.commit()
    conn.close()
