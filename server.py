import socket
import threading
import psycopg2
import pickle
import os
from dotenv import load_dotenv

load_dotenv()

HEADER = 64
FORMAT = "utf-8"
DISCONNECT_COMMAND = "!QUIT"
WHISPER_COMMAND = "!WHISPER"
SERVER = os.environ["server"]
PORT = 8080
ADDR = (SERVER, PORT)

dbconn = psycopg2.connect(database="chat_application", host="localhost", user="chat_user", password="chat321!", port="5432")

class Server:
    def __init__(self) -> None:
        self.cursor = dbconn.cursor()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(ADDR)
        self.clients = []
        max_length = len(b' ' * HEADER)
        command = "CREATE TABLE IF NOT EXISTS chat_users (name VARCHAR(255) UNIQUE NOT NULL);"
        self.cursor.execute(command)
        command = f"CREATE TABLE IF NOT EXISTS history (msg VARCHAR({max_length}) NOT NULL, name VARCHAR(255) NOT NULL);"
        self.cursor.execute(command)
        dbconn.commit()

    def send_join_message(self, name: str) -> None:
        self.send_message(f"{name} has joined the chat")

    def send_message(self, msg: str, name: str = "SERVER") -> None:
        message = [(msg, name)]
        message = pickle.dumps(message)
        msg_length = len(message)
        msg_length = str(msg_length).encode(FORMAT)
        msg_length += b" " * (HEADER - len(msg_length))
        for client in self.clients:
            client[0].sendall(msg_length)
            client[0].sendall(message)
        if name != "SERVER":
            command = f"INSERT INTO history(msg, name) VALUES ('{msg}', '{name}')"
            self.cursor.execute(command)

    def send_personal_message(self, msg: str, name: str) -> None:
        msg = msg.split(" ")
        sender = name
        receiver = msg[1]
        body = ' '.join(msg[2:])
        message = [(body, sender)]
        message = pickle.dumps(message)
        msg_length = len(message)
        msg_length = str(msg_length).encode(FORMAT)
        header = msg_length + b";whisper=true"
        header += b" " * (HEADER - len(header))
        for client in self.clients:
            if receiver == client[2]:
                conn = client[0]
                conn.sendall(header)
                conn.sendall(message)

    def handle_message(self, conn: socket.socket, name: str, addr: tuple) -> None:
        connected = True
        while connected:
            msg_length = conn.recv(HEADER).decode(FORMAT)
            msg_length = int(msg_length)
            msg = conn.recv(msg_length).decode(FORMAT)
            if msg == DISCONNECT_COMMAND:
                connected = False
            elif msg.find(WHISPER_COMMAND) != -1:
                self.send_personal_message(msg, name)
            else:
                self.send_message(msg, name)
        self.send_message(f"{name} has left the chat")
        conn.close()
        self.clients.remove((conn, addr, name))

    def send_history(self, conn: socket.socket) -> None:
        max_length = len(b" " * HEADER)
        command = f"SELECT msg, name FROM history LIMIT {max_length};"
        self.cursor.execute(command)
        history = self.cursor.fetchall()
        history = pickle.dumps(history)
        length = len(history)
        length = str(length).encode(FORMAT)
        length += b" " * (HEADER - len(length))
        conn.send(length)
        conn.send(history)

    def handle_client(self, conn: socket.socket, addr: tuple) -> None:
        headers = conn.recv(HEADER).decode(FORMAT)
        headers = headers.split(";")
        name, sign_up = headers
        self.clients.append((conn, addr, name))
        if sign_up == "yes":
            self.cursor.execute(f"INSERT INTO chat_users(name) VALUES ('{name}');")
            dbconn.commit()
            self.send_history(conn)
            self.send_join_message(name)
            self.handle_message(conn, name, addr)
        else:
            self.cursor.execute(f"SELECT name FROM chat_users WHERE name = '{name}';")
            result = self.cursor.fetchone()[0]
            if result:
                dbconn.commit()
                self.send_history(conn)
                self.send_join_message(name)
                self.handle_message(conn, name, addr)
    
    def start(self) -> None:
        self.server.listen()
        print(f"[LISTENING] the server is listening on {SERVER}")
        try:
            while True:
                conn, addr = self.server.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.start()
                print(f"[ACTIVE CONNECTIONS] {threading.active_count()-1}")
        except KeyboardInterrupt:
            self.server.close()
            dbconn.close()
            print("[SERVER CLOSED]")
            exit(0)

server = Server()
server.start()