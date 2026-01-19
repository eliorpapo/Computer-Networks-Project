import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog

SERVER_IP = "172.20.10.2" 
SERVER_PORT = 55555

class ChatClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        # הגדרת צבעים גלובלית למניעת בעיית "לבן על לבן"
        self.bg_color = "white"
        self.text_color = "black"
        self.side_bg = "#f0f0f0" # אפור בהיר לצד

        self.nickname = simpledialog.askstring("Nickname", "Choose a name:") or "Guest"
        
        self.root.deiconify()
        self.root.title(f"Chat - {self.nickname}")
        self.root.geometry("700x500")
        self.root.configure(bg=self.bg_color)

        # פריים ראשי
        self.main_container = tk.Frame(self.root, bg=self.bg_color)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # --- צד שמאל: צ'אט ---
        self.left_frame = tk.Frame(self.main_container, bg=self.bg_color)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(self.left_frame, text="Chat Room", font=("Arial", 12, "bold"), 
                 bg=self.bg_color, fg=self.text_color).pack(anchor="w")
        
        # אזור הטקסט - הגדרת רקע וצבע טקסט מפורשת
        self.chat_area = scrolledtext.ScrolledText(self.left_frame, state='disabled', height=20, 
                                                  bg="white", fg="black", insertbackground="black")
        self.chat_area.pack(fill=tk.BOTH, expand=True, pady=5)

        self.status_label = tk.Label(self.left_frame, text="Sending to: Everyone", 
                                    bg=self.bg_color, fg="blue", font=("Arial", 10, "italic"))
        self.status_label.pack(anchor="w")

        # שדה הקלט - הגדרת רקע וצבע טקסט
        self.input_field = tk.Entry(self.left_frame, font=("Arial", 11), 
                                   bg="white", fg="black", insertbackground="black")
        self.input_field.pack(fill=tk.X, pady=5)
        self.input_field.bind("<Return>", lambda e: self.send_message())

        # --- צד ימין: רשימה ---
        self.right_frame = tk.Frame(self.main_container, width=180, bg=self.side_bg, bd=1, relief=tk.SUNKEN)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=10)
        self.right_frame.pack_propagate(False)

        tk.Label(self.right_frame, text="Online Users", bg=self.side_bg, fg=self.text_color, 
                 font=("Arial", 11, "bold")).pack(pady=5)
        
        self.users_listbox = tk.Listbox(self.right_frame, font=("Arial", 10), 
                                       bg="white", fg="black", selectbackground="#4CAF50")
        self.users_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.users_listbox.bind("<<ListboxSelect>>", self.on_user_select)

        self.reset_btn = tk.Button(self.right_frame, text="Back to Everyone", 
                                  command=self.reset_selection, bg="#e0e0e0", fg="black")
        self.reset_btn.pack(pady=5, padx=5, fill=tk.X)

        self.target_user = "Everyone"

        # חיבור
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((SERVER_IP, SERVER_PORT))
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except Exception as e:
            self.display_message(f"System: Error connecting - {e}")

        self.root.mainloop()

    # --- שאר הפונקציות נשארות זהות ---

    def reset_selection(self):
        self.target_user = "Everyone"
        self.status_label.config(text="Sending to: Everyone", fg="blue")
        self.users_listbox.selection_clear(0, tk.END)

    def on_user_select(self, event):
        selection = self.users_listbox.curselection()
        if selection:
            selected_name = self.users_listbox.get(selection[0])
            if selected_name == "Everyone":
                self.reset_selection()
            else:
                self.target_user = selected_name
                self.status_label.config(text=f"Sending Private to: {self.target_user}", fg="red")

    def send_message(self):
        msg = self.input_field.get().strip()
        if not msg: return
        if self.target_user == "Everyone":
            self.client_socket.sendall(msg.encode("utf-8"))
            self.display_message(f"You: {msg}")
        else:
            self.client_socket.sendall(f"@{self.target_user}:{msg}".encode("utf-8"))
            self.display_message(f"You (Private to {self.target_user}): {msg}")
        self.input_field.delete(0, tk.END)

    def receive_messages(self):
        while True:
            try:
                data = self.client_socket.recv(1024).decode("utf-8")
                if data == "NICKNAME_REQUEST":
                    self.client_socket.sendall(self.nickname.encode("utf-8"))
                elif data.startswith("USER_LIST:"):
                    raw_names = data.split(":")[1]
                    names = raw_names.split(",") if raw_names else []
                    self.update_listbox(names)
                else:
                    self.display_message(data)
            except:
                break

    def update_listbox(self, names):
        self.users_listbox.delete(0, tk.END)
        self.users_listbox.insert(tk.END, "Everyone")
        for name in names:
            if name != self.nickname:
                self.users_listbox.insert(tk.END, name)

    def display_message(self, message):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.config(state='disabled')
        self.chat_area.yview(tk.END)

if __name__ == "__main__":
    ChatClient()