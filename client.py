import socket
import pickle
import threading
import queue
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

class Client:
    def __init__(self) -> None:
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(ADDR)
        self.client.settimeout(3)

    def read_kbd_input(self, inputQueue: queue.Queue):
        while (True):
            print(">> ", end="", flush=True)
            input_str = input()
            inputQueue.put(input_str)
    
    def get_message(self):
        try:
            msg_length = self.client.recv(HEADER).decode(FORMAT)
            try:
                msg_length = int(msg_length)
                msg = self.client.recv(msg_length)
                msg = pickle.loads(msg)
                if not msg: return
                for i in msg:
                    message = i[0]
                    name = i[1]
                    print(f"\n[{name}] {message}")
                    print(">> ", end="", flush=True)
            except:
                msg_length = msg_length.split(";")[0]
                msg_length = int(msg_length)
                msg = self.client.recv(msg_length)
                msg = pickle.loads(msg)
                if not msg: return
                for i in msg:
                    message = i[0]
                    name = i[1]
                    print(f"\n[{name} WHISPERED] {message}")
                    print(">> ", end="", flush=True)
        except:
            return

    def start(self):
        name = input("What is your name: ")
        sign_up = input("Are you signing up for the first time (yes/no): ")
        header = f"{name};{sign_up}".encode(FORMAT)
        self.client.send(header)
        self.get_message()
        self.get_message()
        inputQueue = queue.Queue()
        inputThread = threading.Thread(target=self.read_kbd_input, args=(inputQueue,), daemon=True)
        inputThread.start()
        while True:
            if inputQueue.qsize() > 0:
                msg = inputQueue.get()
                if msg == "": continue
                if msg == "!HELP":
                    print("\n!QUIT quits chat")
                    print("!WHISPER <name> <msg> whispers message to one person")
                    print(">> ", end="", flush=True)
                else:
                    msg = msg.encode(FORMAT)
                    msg_length = len(msg)
                    msg_length = str(msg_length).encode(FORMAT)
                    msg_length += b" " * (HEADER - len(msg_length))
                    self.client.send(msg_length)
                    self.client.send(msg)
                    if msg.decode(FORMAT) == "!QUIT":
                        break
            self.get_message()
        print("\n[QUIT] you have successfully exited the server")

client = Client()
client.start()