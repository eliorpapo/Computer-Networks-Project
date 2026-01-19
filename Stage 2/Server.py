import socket
import threading
import logging
from datetime import datetime

# הגדרת מערכת הלוגים
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("server_log.log"), # שמירה לקובץ
        logging.StreamHandler()                # הצגה בטרמינל
    ]
)

HOST = "172.20.10.2"
PORT = 55555

active_clients = {}

def broadcast_user_list():
    names = [info["name"] for info in active_clients.values()]
    list_msg = "USER_LIST:" + ",".join(names)
    for sock in active_clients:
        try:
            sock.sendall(list_msg.encode("utf-8"))
        except Exception as e:
            logging.error(f"Failed to send user list to a client: {e}")

def handle_client(conn, addr):
    logging.info(f"New connection attempt from {addr}")
    
    try:
        conn.sendall("NICKNAME_REQUEST".encode("utf-8"))
        nickname = conn.recv(1024).decode("utf-8")
        
        if not nickname:
            logging.warning(f"Connection from {addr} closed: No nickname provided.")
            conn.close()
            return

        active_clients[conn] = {"name": nickname, "addr": addr}
        logging.info(f"User '{nickname}' connected from {addr}. Total users: {len(active_clients)}")
        
        broadcast_user_list()

        while True:
            data = conn.recv(1024)
            if not data:
                break
            
            message = data.decode("utf-8")
            
            # לוג להודעות פרטיות
            if message.startswith("@"):
                try:
                    target_name, p_msg = message[1:].split(":", 1)
                    target_name = target_name.strip()
                    logging.info(f"PRIVATE MESSAGE: From '{nickname}' to '{target_name}': {p_msg}")
                    
                    found = False
                    for sock, info in active_clients.items():
                        if info["name"] == target_name:
                            sock.sendall(f"[Private from {nickname}]: {p_msg}".encode("utf-8"))
                            found = True
                            break
                    if not found:
                        logging.warning(f"User '{nickname}' tried to message non-existent user '{target_name}'")
                        conn.sendall(f"System: User {target_name} not found.".encode("utf-8"))
                except ValueError:
                    logging.error(f"Invalid private message format from {nickname}: {message}")
            else:
                # לוג להודעה ציבורית
                logging.info(f"PUBLIC MESSAGE: From '{nickname}': {message}")
                broadcast(f"{nickname}: {message}", conn)

    except ConnectionResetError:
        logging.warning(f"Connection reset by client: {addr}")
    except Exception as e:
        logging.error(f"Unexpected error with client {addr}: {e}")
    finally:
        if conn in active_clients:
            user_name = active_clients[conn]['name']
            logging.info(f"User '{user_name}' disconnected.")
            del active_clients[conn]
        
        broadcast_user_list()
        conn.close()

def broadcast(msg, sender_sock):
    for sock in active_clients:
        if sock != sender_sock:
            try:
                sock.sendall(msg.encode("utf-8"))
            except:
                pass

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((HOST, PORT))
        server.listen()
        logging.info(f"SERVER STARTED - Listening on {HOST}:{PORT}")
    except Exception as e:
        logging.critical(f"SERVER FAILED TO START: {e}")
        return

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()