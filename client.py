import sys
import socket
import json
import hashlib


from threading import Thread
from PyQt5 import QtCore
from PyQt5.QtWidgets import (
    QSplitter,
    QVBoxLayout,
    QDialog,
    QPushButton,
    QApplication,
    QTextEdit,
    QLineEdit,
    QMessageBox,
    QLabel,
    QCheckBox,
)

from chat_util import make_message


class Window(QDialog):
    """
    The chat client GUI also contains a method for sending messages to the server.
    """

    def __init__(self):
        super().__init__()

        self.dialog_login_window = QDialog()
        self.password_textbox = QLineEdit(self.dialog_login_window)
        self.login_textbox = QLineEdit(self.dialog_login_window)
        self.port_textbox = QLineEdit(self.dialog_login_window)
        self.host_textbox = QLineEdit(self.dialog_login_window)

        self.register_checkbox = QCheckBox("New User ?", self.dialog_login_window)

        self.server_username = QLabel(self)
        self.server_username.setText("SERVER USERNAME")
        self.server_username.move(10, 10)

        self.client_username = QLabel(self)
        self.client_username.setText("CLIENT USERNAME")
        self.client_username.move(10, 150)

        self.chatTextField = QLineEdit(self)
        self.chatTextField.resize(460, 100)
        self.chatTextField.move(50, 350)

        self.btnSend = QPushButton("Send", self)
        self.btnSend.resize(480, 30)
        self.btnSendFont = self.btnSend.font()
        self.btnSendFont.setPointSize(15)
        self.btnSend.setFont(self.btnSendFont)
        self.btnSend.move(10, 460)
        self.btnSend.setStyleSheet("background-color: #F7CE16")
        self.btnSend.clicked.connect(self.send)

        self.chatBody = QVBoxLayout(self)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)

        splitter_names = QSplitter(QtCore.Qt.Horizontal)
        splitter_names.addWidget(self.server_username)
        splitter_names.addWidget(self.client_username)
        splitter_names.setSizes([10, 10])

        splitter0 = QSplitter(QtCore.Qt.Vertical)
        splitter0.addWidget(splitter_names)
        splitter0.addWidget(self.chat)
        splitter0.setSizes([10, 10])

        splitter = QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(splitter0)
        splitter.addWidget(self.chatTextField)
        splitter.setSizes([350, 100])

        splitter2 = QSplitter(QtCore.Qt.Vertical)
        splitter2.addWidget(splitter)
        splitter2.addWidget(self.btnSend)
        splitter2.setSizes([200, 10])

        self.chatBody.addWidget(splitter2)

        self.setWindowTitle("Chat Client Application")
        self.resize(500, 500)

    def send(self) -> None:
        """
        Sends a message from the text input field (self.chatTextField)
        :return:
        """
        text = self.chatTextField.text()
        font = self.chat.font()
        font.setPointSize(13)
        self.chat.setFont(font)
        message = make_message(text, self.client_username.text(), RECIPIENT_LIST)
        message_json = json.loads(message)
        self.chat.append(
            f"{message_json.get('datetime')} {message_json.get('author')}: {message_json.get('text')}"
        )
        try:
            SERVER.send(message.encode())
        except (OSError, AttributeError) as e:
            self.rise_error(e)
        self.chatTextField.setText("")

    @staticmethod
    def rise_error(text: str) -> None:
        """
        Show an error window with the specified text.
        :param text:
        :return: None
        """
        print(f"ERROR: {str(text)}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Error")
        msg.setInformativeText(str(text))
        msg.setWindowTitle("Error")
        msg.exec_()

    def show_login(self) -> None:
        """
        Show the user authorization (registration) window
        :return: None
        """
        self.dialog_login_window.resize(250, 250)

        login_button = QPushButton("Login", self.dialog_login_window)
        login_button.move(10, 210)
        login_button.clicked.connect(self.login_actions)

        self.register_checkbox.move(170, 210)

        self.host_textbox.move(10, 10)
        self.host_textbox.resize(230, 30)
        self.host_textbox.setPlaceholderText("Host")
        self.host_textbox.setText("127.0.0.1")

        self.port_textbox.move(10, 60)
        self.port_textbox.resize(230, 30)
        self.port_textbox.setPlaceholderText("Port")
        self.port_textbox.setText("80")

        self.login_textbox.move(10, 110)
        self.login_textbox.resize(230, 30)
        self.login_textbox.setPlaceholderText("Login")
        self.login_textbox.setText("Arrow")

        self.password_textbox.move(10, 160)
        self.password_textbox.resize(230, 30)
        self.password_textbox.setPlaceholderText("Password")
        self.password_textbox.setEchoMode(QLineEdit.Password)
        self.password_textbox.setText("password")

        self.dialog_login_window.setWindowTitle("Login")
        self.dialog_login_window.setWindowModality(QtCore.Qt.ApplicationModal)
        self.dialog_login_window.exec_()

    def login_actions(self):
        """
        Called when the authorization button is pressed, closes the authorization window.
        :return: None
        """
        self.client_username.setText(self.login_textbox.text())
        self.dialog_login_window.close()


class ClientThread(Thread):
    """
    The thread for the client to work with the server, contains methods for sending data to the server,
    processing messages from the server and changing the chat graphical interface.
    """

    def __init__(self, chat_window):
        """
        Injects chat_window into the class attributes and calls the show_login () method on it to display
        the authorization window.
        :param chat_window: chat GUI
        """
        Thread.__init__(self)
        self.window = chat_window

        self.window.show_login()
        self.client_name = "UNDEFINED_CLIENT_NAME"
        self.server_name = "UNDEFINED_SERVER_NAME"

    def run(self):
        host = window.host_textbox.text()
        try:
            port = int(window.port_textbox.text())
        except ValueError as e:
            self.window.rise_error(e)
            self.window.close()
            return False

        self.client_name = window.login_textbox.text()
        password = window.password_textbox.text()
        hash_password = hashlib.md5(password.encode()).hexdigest()

        BUFFER_SIZE = 1024
        global SERVER
        SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            SERVER.connect((host, port))
            print(f"register: {window.register_checkbox.isChecked()}")
            if window.register_checkbox.isChecked():
                message = make_message(
                    f"/register {self.client_name}:{hash_password}",
                    self.client_name,
                    RECIPIENT_LIST,
                )
                SERVER.send(message.encode())
            else:
                message = make_message(
                    f"/login {self.client_name}:{hash_password}",
                    self.client_name,
                    RECIPIENT_LIST,
                )
                SERVER.send(message.encode())
        except (
            OSError,
            AttributeError,
            ConnectionRefusedError,
            TypeError,
            ValueError,
            socket.gaierror,
        ) as e:
            self.window.rise_error(e)

        while True:
            try:
                data = SERVER.recv(BUFFER_SIZE)

                # for multiline messages
                if "__+\|SPLIT|/+__" in data.decode("utf-8"):
                    for message in data.decode("utf-8").split("__+\|SPLIT|/+__"):
                        print(f"splited to: {message}")
                        decoded_data = json.loads(message)
                        if not self.process_message(decoded_data):
                            break
                else:
                    decoded_data = json.loads(data.decode("utf-8"))
                    if not self.process_message(decoded_data):
                        break

            except ConnectionResetError as e:
                self.window.rise_error(e)
                break

            except json.decoder.JSONDecodeError:
                print(f'Decode json error: {data.decode("utf-8")}')
                continue

    def process_message(self, decoded_data: str) -> bool:
        """
        Handles messages from the server, including special messages (/server_name (sets the server name),
        /error (triggers an error alert), /now_online (records which users are currently online))
        :param decoded_data:
        :return:
        """
        data_text = decoded_data.get("text")
        if "/server_name" in data_text:
            self.server_name = data_text.split(" ")[1]
            window.server_username.setText(self.server_name)

        elif "/error" in data_text:
            self.window.rise_error(data_text)
            return False

        elif "/now_online" in data_text:
            global RECIPIENT_LIST
            RECIPIENT_LIST = []
            data_text.split(" ")
            for recipient in data_text.split(" ")[1:]:
                RECIPIENT_LIST.append(recipient)

        else:
            window.chat.append(
                f"{decoded_data.get('datetime')} {decoded_data.get('author')}: {data_text}"
            )
        return True


if __name__ == "__main__":
    SERVER = None
    RECIPIENT_LIST = []

    app = QApplication(sys.argv)

    window = Window()
    clientThread = ClientThread(window)
    clientThread.start()

    window.exec()
    sys.exit(app.exec_())
