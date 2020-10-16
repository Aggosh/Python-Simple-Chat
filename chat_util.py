import datetime
import json

import psycopg2

from config_server import (
    DATABASE,
    DB_USER,
    DB_PASSWORD,
    DB_HOST,
    SERVER_NAME,
    SERVER_ACCOUNT_PASSWORD,
)


def make_message(
    text: str,
    author_name: str,
    recipient_names: list,
    m_datetime=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
) -> json:
    """
    Converts the collected data to JSON
    :param text:
    :param author_name:
    :param recipient_names:
    :param m_datetime: Optional, if not, the time and date is now
    :return: json message
    Return example:
    message = {
        "author": 'Arrow',
        "recipient": ['Aggosh', 'Anton'],
        "text": 'My text',
        "datetime": '2004-8-15 05:47:42',
    }
    """

    if author_name in recipient_names:
        recipient_names.remove(author_name)

    message = {
        "author": author_name,
        "recipient": recipient_names,
        "text": text,
        "datetime": m_datetime,
    }
    return json.dumps(message)


class User:
    """
    Stores user data and redirects requests to the database
    """

    def __init__(
        self,
        socket,
        db,
        username="UNKNOWN_USER",
        password="UNKNOWN_PASSWORD",
        address="UNKNOWN_ADDRESS",
    ):
        self.db = db
        self.username = username
        self.password = password
        self.socket = socket
        self.address = address

        self.logged_in = False

    def login(self) -> bool:
        if self.db.login(self.username, self.password):
            self.logged_in = True
            return True
        return False

    def register(self) -> bool:
        if self.db.register(self.username, self.password):
            self.logged_in = True
            return True
        return False

    def __str__(self) -> str:
        return self.username


class DataBase:
    @staticmethod
    def init() -> None:
        """
        Database initialization, creating tables: accounts, messages, accounts_messages
        and creating an account for messages from the server
        :return: None
        """
        with DataConn() as cursor:
            cursor.execute(
                "CREATE TABLE accounts ("
                "user_id serial PRIMARY KEY,"
                "username VARCHAR ( 50 ) UNIQUE NOT NULL,"
                "password VARCHAR ( 50 ) NOT NULL);"
            )

            cursor.execute(
                "CREATE TABLE messages ("
                "message_id serial PRIMARY KEY,"
                "author VARCHAR ( 50 ) NOT NULL,"
                "text VARCHAR ( 2048 ) NOT NULL,"
                "datetime timestamp NOT NULL,"
                "FOREIGN KEY (author) REFERENCES accounts(username) ON DELETE CASCADE);"
            )

            cursor.execute(
                "CREATE TABLE accounts_messages ("
                "message_id integer,"
                "recipient VARCHAR ( 50 ),"
                "FOREIGN KEY (recipient) REFERENCES accounts(username) ON DELETE CASCADE,"
                "FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE,"
                "PRIMARY KEY (message_id, recipient));"
            )

            cursor.execute(
                "INSERT INTO accounts (username, password) VALUES"
                f"('{SERVER_NAME}', '{SERVER_ACCOUNT_PASSWORD}');"
            )

    def register(self, username: str, password: str) -> bool:
        """
        Adds a record with new user data to the database. If there is no table, then the self.init () method is called
        :param username:
        :param password:
        :return: True if the record has been added, False if something went wrong,
        for example, such a user already exists.
        """
        with DataConn() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO accounts (username, password) VALUES"
                    f"('{username}', '{password}');"
                )
            except psycopg2.errors.UniqueViolation:
                print(f"User {username} already exist")
                return False

            except psycopg2.errors.UndefinedTable:
                self.init()
                return self.register(username, password)

        return True

    def login(self, username: str, password: str) -> bool:
        """
        Checks if the username and password are correct
        :param username:
        :param password:
        :return: False or True
        """
        with DataConn() as cursor:
            try:
                cursor.execute(
                    f"SELECT * FROM accounts WHERE username='{username}' AND password='{password}';"
                )
                records = cursor.fetchall()
            except psycopg2.errors.UndefinedTable:
                self.init()
                return self.login(username, password)

            if records:
                return True
            else:
                return False

    @staticmethod
    def new_message(author: str, recipients: list, text: str, m_datetime: str) -> None:
        """
        Saves the message to the database
        :param author:
        :param recipients:
        :param text:
        :param m_datetime:
        :return: None
        """
        if len(recipients) == 0:
            return

        with DataConn() as cursor:
            cursor.execute(
                "INSERT INTO messages (author, text, datetime) VALUES"
                f"('{author}', '{text}', '{m_datetime}') RETURNING message_id;"
            )
            records = cursor.fetchall()
            message_id = records[0][0]
            for recip in recipients:
                cursor.execute(
                    f"INSERT INTO accounts_messages (message_id, recipient) VALUES ({message_id}, '{recip}');"
                )

    @staticmethod
    def load_message(username, limit=10) -> list:
        """
        Loads messages written by the user or if the user was the recipient.
        Does not download messages that have no recipient.
        :param username:
        :param limit: default is 10
        :return:
        """
        with DataConn() as cursor:
            cursor.execute(
                f"SELECT messages.text, messages.author, messages.datetime FROM messages "
                f"JOIN accounts_messages on accounts_messages.message_id = messages.message_id "
                f"JOIN accounts on accounts.username = accounts_messages.recipient "
                f"WHERE messages.author = '{username}' OR accounts_messages.recipient = '{username}' LIMIT {limit};"
            )
            records = cursor.fetchall()
            print(records)

        return records


class DataConn:
    """
    Context manager for working with the database.
    """

    def __init__(self, name=DATABASE, user=DB_USER, password=DB_PASSWORD, host=DB_HOST):
        self.database = name
        self.user = user
        self.password = password
        self.host = host

    def __enter__(self):
        self.conn = psycopg2.connect(
            dbname=self.database, user=self.user, password=self.password, host=self.host
        )
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()
        if exc_val:
            raise Exception(exc_val)
