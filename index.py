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
import pystray
from PIL import Image, ImageDraw
from flask_cors import CORS
from dateutil import parser

CURRENT_VERSION = "1.5.2"

VERSION_URL = "https://raw.githubusercontent.com/ZeroCreates/Chaster-API-To-Resonite/main/CurrentVersion.txt"

def check_for_updates():
    try:
        r = requests.get(VERSION_URL, timeout=5)
        r.raise_for_status()

        latest_version = r.text.strip()

        print("Current:", CURRENT_VERSION)
        print("Latest:", latest_version)

        if latest_version != CURRENT_VERSION:
            notify("Update available. Get the latest version on GitHub.", GREEN)

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
frozen_remaining_seconds = None
tray_icon = None

# -------------------------
# COLORS
# -------------------------

BG = "#0b0b0b"
PANEL = "#111111"
CYAN = "#00ffff"
GREEN = "#00ff9c"
TEXT = "#e0e0e0"
ERROR = "#ff5555"

notification_after_id = None


def notify(message, color=CYAN, duration=4000):
    global notification_after_id

    def display():
        global notification_after_id

        if notification_after_id:
            root.after_cancel(notification_after_id)

        notification_label.config(text=message, fg=color)
        notification_after_id = root.after(
            duration,
            lambda: notification_label.config(text=""),
        )

    root.after(0, display)

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

        def apply_user():
            user_entry.delete(0, "end")
            user_entry.insert(0, user)
            user_entry.config(state="disabled")

        root.after(0, apply_user)

        set_key(ENV_FILE,"USER_ID",user)

        print("User ID received from login:",user)

    return {"status":"ok"}


def save_user_id(event=None):

    global USER_ID

    user = user_entry.get().strip()
    if not user or str(user_entry.cget("state")) == "disabled":
        return

    USER_ID = user
    set_key(ENV_FILE, "USER_ID", USER_ID)
    user_entry.delete(0, "end")
    user_entry.insert(0, USER_ID)
    user_entry.config(state="disabled")


def save_time_value(event=None):

    if str(time_entry.cget("state")) == "disabled":
        return

    time_value = time_entry.get().strip()
    if not time_value:
        return

    seconds = validate_time_value(time_value)
    if seconds is None:
        return

    set_key(ENV_FILE, "TIME", str(seconds))
    time_entry.delete(0, "end")
    time_entry.insert(0, str(seconds))
    time_entry.config(state="disabled")

@app.route("/add-time", methods=["POST"])
def api_add_time():

    try:

        root.after(0, add_time)
        return {"status": "queued"}, 202

    except Exception as e:

        print("API add time error:", e)
        return {"status": "error"}, 500

@app.route("/time", methods=["GET"])
def get_time():

    return timer_label.cget("text")

@app.route("/status", methods=["GET"])
def get_status():

    status = {
        "userId": USER_ID or "",
        "lockId": LOCK_ID or "",
        "timer": timer_label.cget("text"),
        "keyholder": keyholder_label.cget("text") if "keyholder_label" in globals() else "KEYHOLDER: UNKNOWN",
        "lockSaved": bool(LOCK_ID)
    }

    return status

def run_server():
    app.run(port=5000)

threading.Thread(target=run_server,daemon=True).start()


# -------------------------
# SYSTEM TRAY
# -------------------------

def create_tray_image():
    image = Image.new("RGB", (64, 64), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((6, 6, 58, 58), outline=CYAN, width=3)
    draw.line((16, 32, 48, 32), fill=GREEN, width=4)
    draw.line((32, 16, 32, 48), fill=GREEN, width=4)
    return image


def show_window(icon=None, item=None):
    root.after(0, _show_window)


def _show_window():
    root.deiconify()
    root.state("normal")
    root.lift()
    root.focus_force()


def hide_window():
    root.withdraw()


def exit_app(icon=None, item=None):
    if icon is not None:
        icon.stop()
    root.after(0, root.destroy)


def start_tray():
    global tray_icon

    tray_icon = pystray.Icon(
        "resonite_x_chaster_timer",
        create_tray_image(),
        "Resonite X Chaster Timer",
        menu=pystray.Menu(
            pystray.MenuItem("Show", show_window, default=True),
            pystray.MenuItem("Exit", exit_app),
        ),
    )
    tray_icon.run()

# -------------------------
# API FUNCTIONS
# -------------------------

def get_lock_id(lock):
    return lock.get("_id") or lock.get("lock_id") or ""

def get_lock_name(lock):
    return lock.get("name") or lock.get("lock_name") or "Unknown Lock"

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
            notify(f"Server error while fetching locks: {r.text}", ERROR)
            return
        locks = r.json()

        options = []
        selected_index = None

        for i, lock in enumerate(locks):

            lock_id = get_lock_id(lock)
            kh = get_keyholder_name(lock)
            name = get_lock_name(lock)

            options.append(f"{name} | KH: {kh}")

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
    global frozen_remaining_seconds

    if not LOCK_ID:
        root.after(1000, fetch_time)
        return

    user = user_entry.get().strip()

    try:

        r = requests.get(f"{BACKEND}/lock/{user}/{LOCK_ID}", timeout=5)
        if r.status_code == 500:
            notify(f"Server error while fetching timer: {r.text}", ERROR)
            return
        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text)
        data = r.json()

        end = data.get("endDate")
        is_frozen = data.get("isFrozen", False)

        if not end:
            frozen_remaining_seconds = None
            timer_label.config(text="TIMER HIDDEN")
        else:

            end_time = parser.isoparse(end)

            if is_frozen:
                if frozen_remaining_seconds is None:
                    remaining = end_time - datetime.now(timezone.utc)
                    frozen_remaining_seconds = int(remaining.total_seconds())
                seconds = frozen_remaining_seconds
            else:
                frozen_remaining_seconds = None
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


def validate_time_value(time_value):
    if not time_value:
        notify("Enter an amount of time in seconds.", ERROR)
        return None

    if not time_value.isdigit():
        notify("Time must be a positive whole number of seconds.", ERROR)
        return None

    seconds = int(time_value)
    if seconds <= 0:
        notify("Time must be greater than zero.", ERROR)
        return None

    return seconds


def add_time():

    global LOCK_ID

    user = user_entry.get().strip()
    time_value = time_entry.get().strip()

    if not user:
        notify("Please enter or log in with your User ID first.", ERROR)
        return

    if not LOCK_ID:
        notify("Please save a lock before adding time.", ERROR)
        return

    seconds = validate_time_value(time_value)
    if seconds is None:
        return

    try:

        r = requests.post(f"{BACKEND}/addtime/{user}/{LOCK_ID}/{seconds}", timeout=5)
        if r.status_code == 500:
            notify(f"Server error while adding time: {r.text}", ERROR)
            return
        print("Add time response:", r.text)
        set_key(ENV_FILE, "TIME", str(seconds))
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
        notify(f"{timestring}has been added to your time.", GREEN)
        fetch_time()
    except Exception as e:

        print("Add time error:", e)

# -------------------------
# LOCK SELECTION
# -------------------------

def save_lock():

    global LOCK_ID
    global frozen_remaining_seconds

    idx = lock_dropdown.current()

    if idx < 0:
        return

    lock = locks[idx]
    lock_id = get_lock_id(lock)

    if not lock_id:
        return

    LOCK_ID = lock_id
    frozen_remaining_seconds = None

    keyholder_name = get_keyholder_name(lock)
    keyholder_label.config(text=f"KEYHOLDER: {keyholder_name}")

    set_key(ENV_FILE, "LOCK_ID", LOCK_ID)
    update_add_button_state()


def update_add_button_state():
    if add_button is None:
        return

    if LOCK_ID:
        add_button.config(state="normal")
    else:
        add_button.config(state="disabled")


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
    global add_button
    global notification_label

    root = tk.Tk()
    root.title("Resonite X Chaster Timer")
    root.geometry("560x600")
    root.minsize(560, 600)
    root.configure(bg=BG)
    root.protocol("WM_DELETE_WINDOW", hide_window)

    threading.Thread(target=start_tray, daemon=True).start()

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        "Cyber.TCombobox",
        fieldbackground=PANEL,
        background=PANEL,
        foreground=GREEN,
        bordercolor=CYAN,
        lightcolor=CYAN,
        darkcolor=CYAN,
        arrowcolor=CYAN,
        padding=6,
    )
    style.map(
        "Cyber.TCombobox",
        fieldbackground=[("readonly", PANEL)],
        foreground=[("readonly", GREEN)],
        selectbackground=[("readonly", CYAN)],
        selectforeground=[("readonly", BG)],
    )

    shell = tk.Frame(root, bg=PANEL, highlightbackground=CYAN, highlightthickness=1)
    shell.pack(fill="both", expand=True, padx=18, pady=18)

    title = tk.Label(
        shell,
        text="RESONITE X CHASTER TIMER",
        bg=PANEL,
        fg=CYAN,
        font=("Consolas", 18, "bold"),
        pady=8,
    )

    title.pack(pady=(14, 4))

    # USER ID

    user_label = tk.Label(shell, text="[ USER ID ]", bg=PANEL, fg=TEXT, font=("Consolas", 10, "bold"))
    user_label.pack(anchor="w", padx=28, pady=(10, 2))

    user_entry = tk.Entry(
        shell,
        width=50,
        bg=BG,
        fg=GREEN,
        insertbackground=GREEN,
        relief="flat",
        highlightbackground=CYAN,
        highlightcolor=GREEN,
        highlightthickness=1,
        font=("Consolas", 10),
    )
    user_entry.pack(padx=28, pady=(0, 10), fill="x")
    user_entry.bind("<Return>", save_user_id)
    user_entry.bind("<FocusOut>", save_user_id)

    if USER_ID:
        user_entry.insert(0, USER_ID)
        user_entry.config(state="disabled")

    # LOCK SELECT

    lock_dropdown = ttk.Combobox(shell, width=55, style="Cyber.TCombobox", state="readonly")
    lock_dropdown.pack(padx=28, pady=(0, 10), fill="x")

    keyholder_label = tk.Label(
        shell,
        text="KEYHOLDER: UNKNOWN",
        bg=PANEL,
        fg=CYAN,
        font=("Consolas", 10, "bold"),
    )

    keyholder_label.pack(anchor="w", padx=28, pady=(0, 12))

    # BUTTONS

    button_frame = tk.Frame(shell, bg=PANEL)
    button_frame.pack(pady=4)

    fetch_button = tk.Button(
        button_frame,
        text="FETCH LOCKS",
        command=fetch_locks,
        bg=BG,
        fg=CYAN,
        activebackground=CYAN,
        activeforeground=BG,
        relief="flat",
        padx=14,
        pady=6,
        font=("Consolas", 9, "bold"),
        cursor="hand2",
    )

    fetch_button.grid(row=0, column=0, padx=10)

    save_button = tk.Button(
        button_frame,
        text="SAVE LOCK",
        command=save_lock,
        bg=BG,
        fg=GREEN,
        activebackground=GREEN,
        activeforeground=BG,
        relief="flat",
        padx=14,
        pady=6,
        font=("Consolas", 9, "bold"),
        cursor="hand2",
    )

    save_button.grid(row=0, column=1, padx=10)

    time_label = tk.Label(shell, text="[ ADD TIME (SECONDS) ]", bg=PANEL, fg=CYAN, font=("Consolas", 10, "bold"))
    time_label.pack(anchor="w", padx=28, pady=(14, 2))

    time_entry = tk.Entry(shell, bg=BG, fg=CYAN, insertbackground=CYAN, relief="flat", highlightbackground=CYAN, highlightcolor=GREEN, highlightthickness=1, font=("Consolas", 10))
    time_entry.pack(padx=28, pady=(0, 8), fill="x")
    time_entry.bind("<Return>", save_time_value)
    time_entry.bind("<FocusOut>", save_time_value)
    add_button = tk.Button(
        root,
        text="ADD TIME",
        command=add_time,
        bg=BG,
        fg=CYAN,
        activebackground=CYAN,
        activeforeground=BG,
        relief="flat",
        padx=20,
        pady=6,
        font=("Consolas", 9, "bold"),
        cursor="hand2",
    )

    add_button.pack(pady=4)

    refresh_button = tk.Button(
        root,
        text="REFRESH TIMER",
        command=fetch_time,
        bg=BG,
        fg=CYAN,
        activebackground=CYAN,
        activeforeground=BG,
        relief="flat",
        padx=16,
        pady=5,
        font=("Consolas", 9, "bold"),
        cursor="hand2",
    )

    refresh_button.pack(pady=4)

    # TIMER DISPLAY

    timer_label = tk.Label(
        shell,
        text="NOT CONFIGURED",
        bg=PANEL,
        fg=GREEN,
        font=("Consolas", 30, "bold"),
    )

    notification_label = tk.Label(
        shell,
        text="",
        bg=PANEL,
        fg=CYAN,
        font=("Consolas", 10, "bold"),
    )

    login_button = tk.Button(
        shell,
        text="LOGIN WITH CHASTER",
        command=open_login_page,
        bg=BG,
        fg=CYAN,
        activebackground=CYAN,
        activeforeground=BG,
        relief="flat",
        padx=18,
        pady=6,
        font=("Consolas", 9, "bold"),
        cursor="hand2",
    )
    login_button.pack(pady=(6, 0))

    timer_label.pack(pady=(22, 12))
    notification_label.pack(pady=(0, 8))

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