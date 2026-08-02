import os
import shutil
import threading
import requests
import tkinter as tk
from tkinter import ttk
from flask import Flask, request
from dotenv import load_dotenv, set_key
from datetime import datetime,timezone
import webbrowser
from flask_cors import CORS
from dateutil import parser
from tkinter import messagebox

CURRENT_VERSION = "1.4.0"

VERSION_URL = "https://raw.githubusercontent.com/ZeroCreates/Chaster-API-To-Resonite/main/CurrentVersion.txt"

def check_for_updates():
    try:
        r = requests.get(VERSION_URL, timeout=5)
        r.raise_for_status()

        latest_version = r.text.strip()

        print("Current:", CURRENT_VERSION)
        print("Latest:", latest_version)

        if latest_version != CURRENT_VERSION:
            messagebox.showinfo(
                "Update Available",
                "There is a new version for this app.\n\nGet it on the GitHub."
            )

    except Exception as e:
        print("Update check failed:", e)

# -------------------------
# CONFIG
# -------------------------

BACKEND = "https://chaster.zerocreates.org"  # CHANGE THIS

APPDATA_ROOT = os.getenv("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
APPDATA_DIR = os.path.join(APPDATA_ROOT, "ResoniteXChasterTimer")
ENV_FILE = os.path.join(APPDATA_DIR, ".env")

os.makedirs(APPDATA_DIR, exist_ok=True)

legacy_env_file = os.path.join(os.getcwd(), ".env")
if not os.path.exists(ENV_FILE):
    if os.path.exists(legacy_env_file):
        shutil.copy2(legacy_env_file, ENV_FILE)
    else:
        open(ENV_FILE, "w").close()

load_dotenv(dotenv_path=ENV_FILE)

USER_ID = os.getenv("USER_ID")
LOCK_ID = os.getenv("LOCK_ID")

locks = []

# -------------------------
# COLORS
# -------------------------

BG = "#0b0b0b"
PANEL = "#111111"
CYAN = "#00ffff"
GREEN = "#00ff9c"
TEXT = "#e0e0e0"

# -------------------------
# LOCAL SERVER
# -------------------------

app = Flask(__name__)
CORS(app)

@app.route("/set-user", methods=["POST"])
def set_user():

    global USER_ID

    data = request.json
    user = data.get("userId")

    if user:

        USER_ID = user

        user_entry.delete(0,"end")
        user_entry.insert(0,user)
        user_entry.config(state="disabled")

        set_key(ENV_FILE,"USER_ID",user)

        print("User ID received from login:",user)

    return {"status":"ok"}

@app.route("/add-time", methods=["POST"])
def api_add_time():

    try:

        add_time()  # call your existing function
        
        return "success"

    except Exception as e:

        return "Fail"

@app.route("/time", methods=["GET"])
def get_time():

    return timer_label.cget("text")

def run_server():
    app.run(port=5000)

threading.Thread(target=run_server,daemon=True).start()

# -------------------------
# API FUNCTIONS
# -------------------------

def get_lock_id(lock):
    return lock.get("_id") or lock.get("lock_id") or ""


def get_keyholder_name(lock):
    keyholder = lock.get("keyholder", "Unknown")

    if isinstance(keyholder, dict):
        return keyholder.get("username") or keyholder.get("name") or "Unknown"

    if isinstance(keyholder, str) and keyholder.strip():
        return keyholder

    return "Unknown"


def fetch_locks():

    global locks
    global LOCK_ID

    user = user_entry.get().strip()

    if not user:
        print("User ID missing")
        return

    try:

        r = requests.get(f"{BACKEND}/locks/{user}", timeout=5)

        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text)
        if r.status_code == 500:
            open(ENV_FILE, "w").close()
            user_entry.delete(0,"end")
            messagebox.showerror(
                "Server MSG",
                f"The server returned an msg.\n\nResponse:\n{r.text}"
            )
            return
        locks = r.json()

        options = []
        selected_index = None

        for i, lock in enumerate(locks):

            lock_id = get_lock_id(lock)
            kh = get_keyholder_name(lock)

            options.append(f"{lock_id} | KH: {kh}")

            # auto select saved lock
            if LOCK_ID and lock_id and lock_id == LOCK_ID:
                selected_index = i
                keyholder_label.config(text=f"KEYHOLDER: {kh}")

        lock_dropdown["values"] = options

        if selected_index is not None:

            lock_dropdown.current(selected_index)

            print("Auto-selected saved lock:", LOCK_ID)

        else:

            print("Saved lock not found")

    except Exception as e:

        print("Lock fetch error:", e)


def fetch_time():

    global LOCK_ID

    if not LOCK_ID:
        root.after(1000, fetch_time)
        return

    user = user_entry.get().strip()

    try:

        r = requests.get(f"{BACKEND}/lock/{user}/{LOCK_ID}", timeout=5)
        if r.status_code == 500:
            messagebox.showerror(
                "Server MSG",
                f"The server returned an msg.\n\nResponse:\n{r.text}"
            )
            return
        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text)
        data = r.json()

        end = data.get("endDate")

        if not end:
            timer_label.config(text="TIMER HIDDEN")
        else:

            
            end_time = parser.isoparse(end)

            remaining = end_time - datetime.now(timezone.utc)

            seconds = int(remaining.total_seconds())

            if seconds <= 0:
                timer_label.config(text="UNLOCKED")
            else:

                d = seconds // 86400
                h = (seconds % 86400) // 3600
                m = (seconds % 3600) // 60

                timer_label.config(text=f"{d}d {h}h {m}m")

    except Exception as e:

        print("Timer error:", e)

    root.after(1000, fetch_time)


def add_time():

    global LOCK_ID

    user = user_entry.get().strip()
    time_value = time_entry.get().strip()
    if not user or not LOCK_ID:
        return

    try:

        r = requests.post(f"{BACKEND}/addtime/{user}/{LOCK_ID}/{time_value}", timeout=5)
        if r.status_code == 500:
            messagebox.showerror(
                "Server MSG",
                f"The server returned an msg.\n\nResponse:\n{r.text}"
            )
            return
        print("Add time response:",r.text)
        set_key(ENV_FILE,"TIME",time_value)
        seconds = int(time_value)
        d = seconds // 86400
        h = (seconds % 86400) // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        timestring = ""
        if d != 0:
            timestring = timestring + f"{d}d "
        if h != 0:
            timestring = timestring + f"{h}h "
        if m != 0:
            timestring = timestring + f"{m}m "
        if s != 0:
            timestring = timestring + f"{s}s "
        messagebox.showinfo(
                "Time Added",
                f"{timestring} has been added to your time"
            )
    except Exception as e:

        print("Add time error:",e)

# -------------------------
# LOCK SELECTION
# -------------------------

def save_lock():

    global LOCK_ID

    idx = lock_dropdown.current()

    if idx < 0:
        return

    lock = locks[idx]
    lock_id = get_lock_id(lock)

    if not lock_id:
        return

    LOCK_ID = lock_id

    keyholder_name = get_keyholder_name(lock)
    keyholder_label.config(text=f"KEYHOLDER: {keyholder_name}")

    set_key(ENV_FILE, "LOCK_ID", LOCK_ID)

# -------------------------
# GUI
# -------------------------

def open_login_page():
    login_url = f"{BACKEND}/login"
    webbrowser.open(login_url)


def main():
    global root
    global user_entry
    global lock_dropdown
    global keyholder_label
    global time_entry
    global timer_label

    root = tk.Tk()
    root.title("Resonite X Chaster Timer")
    root.geometry("520x520")
    root.configure(bg=BG)

    title = tk.Label(
        root,
        text="RESONITE X CHASTER TIMER",
        bg=BG,
        fg=CYAN,
        font=("Consolas", 18, "bold")
    )

    title.pack(pady=10)

    # USER ID

    user_label = tk.Label(root, text="USER ID", bg=BG, fg=TEXT)
    user_label.pack()

    user_entry = tk.Entry(root, width=50, bg=PANEL, fg=GREEN, insertbackground=GREEN)
    user_entry.pack(pady=5)

    if USER_ID:
        user_entry.insert(0, USER_ID)
        user_entry.config(state="disabled")

    # LOCK SELECT

    lock_dropdown = ttk.Combobox(root, width=55)
    lock_dropdown.pack(pady=10)

    keyholder_label = tk.Label(
        root,
        text="KEYHOLDER: UNKNOWN",
        bg=BG,
        fg=CYAN
    )

    keyholder_label.pack()

    # BUTTONS

    button_frame = tk.Frame(root, bg=BG)
    button_frame.pack(pady=10)

    fetch_button = tk.Button(
        button_frame,
        text="FETCH LOCKS",
        command=fetch_locks,
        bg=PANEL,
        fg=CYAN
    )

    fetch_button.grid(row=0, column=0, padx=10)

    save_button = tk.Button(
        button_frame,
        text="SAVE LOCK",
        command=save_lock,
        bg=PANEL,
        fg=GREEN
    )

    save_button.grid(row=0, column=1, padx=10)

    time_label = tk.Label(root, text="ADD TIME (seconds)", bg=BG, fg=CYAN)
    time_label.pack()

    time_entry = tk.Entry(root, bg=PANEL, fg=CYAN, insertbackground=CYAN)
    time_entry.pack(pady=5)
    add_button = tk.Button(
        root,
        text="ADD TIME",
        command=add_time,
        bg=PANEL,
        fg=CYAN
    )

    add_button.pack(pady=10)

    # TIMER DISPLAY

    timer_label = tk.Label(
        root,
        text="NOT CONFIGURED",
        bg=BG,
        fg=GREEN,
        font=("Consolas", 30, "bold")
    )

    login_button = tk.Button(
        root,
        text="LOGIN WITH CHASTER",
        command=open_login_page,
        bg=PANEL,
        fg=CYAN
    )
    login_button.pack(pady=10)

    timer_label.pack(pady=40)

    TIME = os.getenv("TIME")
    if TIME:
        time_entry.insert(0, TIME)
        time_entry.config(state="disabled")

    # START TIMER LOOP
    check_for_updates()
    fetch_time()

    if USER_ID:
        fetch_locks()

    root.mainloop()


if __name__ == "__main__":
    main()