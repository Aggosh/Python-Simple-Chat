import socket
import threading
import json

from chat_util import make_message, User, DataBase
from config_server import (
    SERVER_NAME,
    MAX_CONNECTIONS,
    HOST,
    PORT,
)


def accept_client():
    """
    Handles new connections
    :return: None
    """
    while True:
        cli_sock, cli_add = ser_sock.accept()
        db = DataBase()
        user = User(cli_sock, db, address=cli_add)

        logged_users_count = 0
        for l_user in USER_LIST:
            if l_user.logged_in:
                logged_users_count += 1

        if logged_users_count < MAX_CONNECTIONS:
            USER_LIST.append(user)
            print(f" new connection from {user.address}")
            thread_client = threading.Thread(target=broadcast_user, args=[user])
            thread_client.start()
        else:
            message = make_message("/error server is busy", SERVER_NAME, [user.address])
            cli_sock.send(message.encode("utf-8"))


def broadcast_user(user):
    """
    Handles the message and connection with the user
    :param user:
    :return: None
    """
    while True:
        try:
            data = user.socket.recv(2048)
            if data:
                print(data.decode("utf-8"))
                decoded_data = json.loads(data.decode("utf-8"))

                data_text = decoded_data.get("text")

                if not user.logged_in:

                    if "/login" in data_text:
                        if not login_chat(data_text, user):
                            raise Exception("Invalid login")

                    elif "/register" in data_text:
                        if not register_chat(data_text, user):
                            raise Exception("Invalid registration")

                    else:
                        message = make_message(
                            f"/error you are not logged in", SERVER_NAME, [user.address]
                        )
                        user.socket.send(message.encode("utf-8"))
                        USER_LIST.remove(user)
                        break

                elif "/load" in data_text:
                    load_message_chat(decoded_data, user)

                else:
                    broadcast_to_users(user, data)

                    author = decoded_data.get("author")
                    recipient = decoded_data.get("recipient")
                    text = decoded_data.get("text")
                    datetime = decoded_data.get("datetime")

                    user.db.new_message(author, recipient, text, datetime)

        except Exception as x:
            print(x)
            USER_LIST.remove(user)
            message = make_message(
                f"{user.username} disconnected", SERVER_NAME, ["All users"]
            )
            broadcast_to_users(user, message.encode("utf-8"))
            online_to_all_users()
            break


def login_chat(data_text: str, user) -> bool:
    """
    Checking the correctness of information for authorization
    :param data_text:
    :param user:
    :return: True if the data is correct, False if not
    """
    user.username = data_text.split(" ")[1].split(":")[0]
    user.password = data_text.split(" ")[1].split(":")[1]

    for logged_users in USER_LIST:
        if user.username == logged_users.username and logged_users.logged_in:
            print(f"/error user {user.username} already logged")
            message = make_message(
                f"/error user {user.username} already logged",
                SERVER_NAME,
                [user.username],
            )
            user.socket.send(message.encode("utf-8"))
            return False

    if user.login():
        message = make_message(
            f"{user.username} was connected to chat", SERVER_NAME, [user.username]
        )
        broadcast_to_users(user, message.encode("utf-8"))

        welcome_message(user)

        return True

    else:
        message = make_message(
            f"/error invalid login {user.username}", SERVER_NAME, [user.username]
        )
        user.socket.send(message.encode("utf-8"))
        print(f"Invalid login {user.username}:{user.password}")
        return False


def register_chat(data_text: str, user) -> bool:
    """
    Creates a record with new user data, if they are not already there
    :param data_text:
    :param user:
    :return: True if the data is correct, False if not
    """
    user.username = data_text.split(" ")[1].split(":")[0]
    user.password = data_text.split(" ")[1].split(":")[1]

    if user.register():
        print(f"New user {user.username} was registered")

        message = make_message(
            f"New user {user.username} was registered", SERVER_NAME, [user.username]
        )
        broadcast_to_users(user, message.encode("utf-8"))

        welcome_message(user)

        return True
    else:
        message = make_message(
            f"/error user {user.username} already exist", SERVER_NAME, [user.username]
        )
        user.socket.send(message.encode("utf-8"))
        return False


def welcome_message(user) -> None:
    """
    Sends the user: server name, who is online now and a welcome message
    :param user:
    :return: None
    """
    message = make_message(f"/server_name {SERVER_NAME}", SERVER_NAME, [user.username])
    user.socket.send(message.encode("utf-8"))

    online_to_all_users(split_char=True)

    message = make_message(f"welcome to {SERVER_NAME}", SERVER_NAME, [user.username])
    user.socket.send(message.encode("utf-8"))


def load_message_chat(decoded_data: str, user) -> None:
    """
    Loads records of user messages
    :param decoded_data:
    :param user:
    :return: None
    """
    splitted_data = decoded_data.get("text").split(" ")
    if len(splitted_data) >= 2:
        limit = splitted_data[1]
    else:
        limit = 10
    for message in user.db.load_message(user.username, limit):
        new_message = make_message(
            message[0],
            message[1],
            [SERVER_NAME],
            m_datetime=message[2].strftime("%Y-%m-%d %H:%M:%S"),
        )
        user.socket.send((new_message + "__+\|SPLIT|/+__").encode("utf-8"))
        print(new_message)


def broadcast_to_users(b_user, msg: str) -> None:
    """
    Sends to all users (except the transmitted) message
    :param b_user:
    :param msg:
    :return: None
    """
    for user in USER_LIST:
        if user.socket != b_user.socket and user.logged_in:
            user.socket.send(msg)


def online_to_all_users(split_char=False) -> None:
    """
    Sends a message to all users about which users are currently in the chat
    If split_char = True there will be a separating character at the end of the message
    :param split_char:
    :return: None
    """
    online_users = []
    for l_user in USER_LIST:
        if l_user.logged_in:
            online_users.append(l_user.username)

    for user in USER_LIST:
        if user.logged_in:
            msg = make_message(
                f"/now_online " + " ".join(online_users), SERVER_NAME, ["All users"]
            )
            if split_char:
                user.socket.send((msg + "__+\|SPLIT|/+__").encode("utf-8"))
            else:
                user.socket.send(msg.encode("utf-8"))


if __name__ == "__main__":
    USER_LIST = []

    ser_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    ser_sock.bind((HOST, PORT))

    ser_sock.listen(1)
    print(f"Chat server started on {HOST}:{PORT}")

    thread_ac = threading.Thread(target=accept_client)
    thread_ac.start()
