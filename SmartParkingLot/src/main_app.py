import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# --------- Database path (same folder) ----------
DB_PATH = os.path.join(os.path.dirname(__file__), "parking.db")

# --------- DB helper functions ----------
def get_connection():
    return sqlite3.connect(DB_PATH)

def ensure_tables_exist():
    """Create minimal tables if not exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS slots (
        slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_number TEXT UNIQUE NOT NULL,
        is_occupied INTEGER DEFAULT 0
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_name TEXT,
        vehicle_number TEXT UNIQUE,
        slot_id INTEGER,
        entry_time TEXT,
        exit_time TEXT,
        FOREIGN KEY(slot_id) REFERENCES slots(slot_id)
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER,
        amount REAL,
        payment_time TEXT,
        FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id)
    );""")
    conn.commit()
    conn.close()

# Ensure DB ready
ensure_tables_exist()

# --------- GUI root ----------
root = tk.Tk()
root.title("Smart Parking Lot Management System")
root.geometry("1000x700")
root.minsize(900, 600)
root.resizable(True, True)

# ---------- Gradient background ----------
canvas = tk.Canvas(root, width=1000, height=700, highlightthickness=0)
canvas.pack(fill="both", expand=True)
for i in range(700):
    r = int(240 - i * 0.05)
    g = int(250 - i * 0.04)
    b = int(255 - i * 0.02)
    color = f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"
    canvas.create_line(0, i, 1000, i, fill=color)

# ---------- Animated header ----------
header_text = canvas.create_text(500, 45, text="🚗 Smart Parking Lot Management System",
                                 font=("Segoe UI", 22, "bold"), fill="#0b486b")

_header_after_id = None
def animate_header():
    global _header_after_id
    try:
        if not (root.winfo_exists() and canvas.winfo_exists()):
            return
    except tk.TclError:
        return
    colors = ["#0b486b", "#987f10", "#6B292E", "#4c93e5", "#6a1b9a"]
    color = colors[int(datetime.now().timestamp() * 2) % len(colors)]
    try:
        canvas.itemconfig(header_text, fill=color)
    except tk.TclError:
        return
    _header_after_id = root.after(400, animate_header)

animate_header()

# ---------- Animated car (emoji version) ----------
car_text = canvas.create_text(-50, 90, text="🚗", font=("Segoe UI", 26))

def move_car(x=-50, direction=1):
    """Makes car move back and forth smoothly."""
    try:
        if not canvas.winfo_exists():
            return
    except tk.TclError:
        return

    canvas.coords(car_text, x, 90)
    if direction == 1:
        if x < 950:
            root.after(20, move_car, x + 4, direction)
        else:
            root.after(20, move_car, 950, -1)
    else:
        if x > 50:
            root.after(20, move_car, x - 4, direction)
        else:
            root.after(20, move_car, 50, 1)

move_car()

# ---------- On Close ----------
def on_app_close():
    try:
        if _header_after_id is not None:
            root.after_cancel(_header_after_id)
    except Exception:
        pass
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_app_close)

# ---------- Main content ----------
frame = tk.Frame(root, bg="#F4F9FD", bd=0)
frame.place(relx=0.05, rely=0.18, relwidth=0.9, relheight=0.8)

# ---------- Button style helpers ----------
def on_enter(e):
    e.widget.config(bg="#0b74d1", fg="white")
def on_leave(e):
    e.widget.config(bg="#83A7B9", fg="black")

btn_style = {"bg": "#96B1C4", "fg": "black", "relief": "ridge", "bd": 2,
             "font": ("Segoe UI", 10, "bold"), "width": 18, "height": 2, "cursor": "hand2"}

# ---------- Core functions ----------
def refresh_main_table():
    for r in main_table.get_children():
        main_table.delete(r)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT v.vehicle_id, v.vehicle_number, s.slot_number, v.entry_time, 
                          COALESCE(v.exit_time, '-') as exit_time
                   FROM vehicles v LEFT JOIN slots s ON v.slot_id = s.slot_id
                   ORDER BY v.vehicle_id DESC LIMIT 50""")
    for row in cur.fetchall():
        main_table.insert("", "end", values=row)
    conn.close()
    update_status_label()

def update_status_label():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM slots")
    total = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM slots WHERE is_occupied=0")
    free = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM vehicles WHERE exit_time IS NULL")
    parked = cur.fetchone()[0] or 0
    conn.close()
    status_label.config(text=f"Total Slots: {total}   Available: {free}   Currently Parked: {parked}")

def add_vehicle_window():
    def submit():
        owner = win_owner.get().strip()
        vnum = win_number.get().strip()
        if not vnum:
            messagebox.showwarning("Input", "Please enter a vehicle number.")
            return
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT slot_id, slot_number FROM slots WHERE is_occupied=0 LIMIT 1")
        row = cur.fetchone()
        if not row:
            conn.close()
            messagebox.showerror("Full", "No available slots.")
            return
        slot_id, slot_no = row
        entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cur.execute("INSERT INTO vehicles (owner_name, vehicle_number, slot_id, entry_time) VALUES (?,?,?,?)",
                        (owner, vnum, slot_id, entry_time))
            cur.execute("UPDATE slots SET is_occupied=1 WHERE slot_id=?", (slot_id,))
            conn.commit()
            messagebox.showinfo("Parked", f"Vehicle parked in {slot_no}")
            win.destroy()
            refresh_main_table()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Vehicle number already exists.")
        finally:
            conn.close()

    win = tk.Toplevel(root)
    win.title("Park Vehicle")
    win.geometry("400x230")
    win.config(bg="#E8F7FF")
    tk.Label(win, text="Owner Name:", bg="#DDE6EB").pack(pady=8)
    win_owner = tk.Entry(win, width=32); win_owner.pack()
    tk.Label(win, text="Vehicle Number:", bg="#DDE6EB").pack(pady=8)
    win_number = tk.Entry(win, width=32); win_number.pack()
    b = tk.Button(win, text="Park Vehicle", command=submit, **btn_style)
    b.pack(pady=14)
    b.bind("<Enter>", on_enter); b.bind("<Leave>", on_leave)

def exit_vehicle_window():
    def submit_exit():
        vnum = win_number.get().strip()
        if not vnum:
            messagebox.showwarning("Input", "Please enter vehicle number.")
            return
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""SELECT v.vehicle_id, v.entry_time, v.slot_id, s.slot_number
                       FROM vehicles v JOIN slots s ON v.slot_id = s.slot_id
                       WHERE v.vehicle_number=? AND v.exit_time IS NULL""", (vnum,))
        rec = cur.fetchone()
        if not rec:
            conn.close()
            messagebox.showerror("Not found", "No active parked vehicle with this number.")
            return
        vehicle_id, entry_time_str, slot_id, slot_no = rec
        entry_dt = datetime.strptime(entry_time_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        minutes = int((now - entry_dt).total_seconds() / 60)
        minutes = max(1, minutes)
        rate_per_min = 1.0
        amount = round(minutes * rate_per_min, 2)
        cur.execute("UPDATE vehicles SET exit_time=? WHERE vehicle_id=?", (now.strftime("%Y-%m-%d %H:%M:%S"), vehicle_id))
        cur.execute("UPDATE slots SET is_occupied=0 WHERE slot_id=?", (slot_id,))
        cur.execute("INSERT INTO payments (vehicle_id, amount, payment_time) VALUES (?, ?, ?)",
                    (vehicle_id, amount, now.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        messagebox.showinfo("Payment", f"Vehicle: {vnum}\nSlot: {slot_no}\nDuration: {minutes} min\nAmount: ₹{amount}")
        win.destroy()
        refresh_main_table()

    win = tk.Toplevel(root)
    win.title("Exit Vehicle")
    win.geometry("380x220")
    win.config(bg="#F9F6F0")
    tk.Label(win, text="Vehicle Number:", bg="#FFF6E5").pack(pady=10)
    win_number = tk.Entry(win, width=30); win_number.pack()
    b = tk.Button(win, text="Process Exit & Pay", command=submit_exit, **btn_style)
    b.pack(pady=16)
    b.bind("<Enter>", on_enter); b.bind("<Leave>", on_leave)

def view_parked_window():
    win = tk.Toplevel(root)
    win.title("Currently Parked Vehicles")
    win.geometry("760x420")
    tree = ttk.Treeview(win, columns=("Owner","Vehicle","Slot","Entry"), show="headings")
    for col in ("Owner","Vehicle","Slot","Entry"):
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=180)
    tree.pack(expand=True, fill="both", padx=8, pady=8)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT v.owner_name, v.vehicle_number, s.slot_number, v.entry_time
                   FROM vehicles v JOIN slots s ON v.slot_id=s.slot_id
                   WHERE v.exit_time IS NULL ORDER BY v.entry_time DESC""")
    for row in cur.fetchall():
        tree.insert("", "end", values=row)
    conn.close()

def payments_window():
    win = tk.Toplevel(root)
    win.title("Payments / Revenue")
    win.geometry("760x420")
    tree = ttk.Treeview(win, columns=("Vehicle","Amount","Time"), show="headings")
    for col in ("Vehicle","Amount","Time"):
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=180)
    tree.pack(expand=True, fill="both", padx=8, pady=8)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT v.vehicle_number, p.amount, p.payment_time
                   FROM payments p JOIN vehicles v ON p.vehicle_id=v.vehicle_id
                   ORDER BY p.payment_time DESC""")
    for row in cur.fetchall():
        tree.insert("", "end", values=row)
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments")
    total = cur.fetchone()[0] or 0
    conn.close()
    tk.Label(win, text=f"Total Revenue: ₹{round(total,2)}", font=("Segoe UI", 12, "bold")).pack(pady=6)

def slot_status_window():
    win = tk.Toplevel(root)
    win.title("Slot Status")
    win.geometry("900x600")
    win.configure(bg="#EAF6F6")
    table = ttk.Treeview(win, columns=("Slot","Status"), show="headings")
    for c in ("Slot","Status"):
        table.heading(c, text=c)
        table.column(c, anchor="center", width=200)
    table.pack(expand=True, fill="both", padx=12, pady=12)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT slot_number, is_occupied 
                   FROM slots 
                   ORDER BY CAST(SUBSTR(slot_number, INSTR(slot_number, '-') + 1) AS INTEGER)""")
    rows = cur.fetchall()
    conn.close()
    for s, occ in rows:
        status = "Occupied" if occ else "Available"
        table.insert("", "end", values=(s, status))
    total = len(rows)
    occupied = sum(1 for _, occ in rows if occ)
    available = total - occupied
    tk.Label(win, text=f"Total Slots: {total} | Occupied: {occupied} | Available: {available}",
             font=("Segoe UI", 11, "bold"), bg="#F1F6F6").pack(pady=8)
    
    # ---------- Add Slots Window ----------
def add_slots_window():
    win = tk.Toplevel(root)
    win.title("➕ Add Parking Slots")
    win.geometry("400x220")
    win.configure(bg="#EAF6F6")
    win.resizable(False, False)

    tk.Label(win, text="🚘 Add or Update Total Slots",
             font=("Segoe UI", 14, "bold"), bg="#EAF6F6", fg="#0b486b").pack(pady=10)
    tk.Label(win, text="Enter total number of slots:", bg="#EAF6F6",
             font=("Segoe UI", 11)).pack(pady=5)
    entry = tk.Entry(win, width=15, font=("Segoe UI", 11), justify="center")
    entry.pack(pady=5)

    def update_slots():
        try:
            total = int(entry.get().strip())
            if total <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid", "Enter a valid positive number.")
            return

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS slots (
                        slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        slot_number TEXT UNIQUE NOT NULL,
                        is_occupied INTEGER DEFAULT 0
                       );""")
        for i in range(1, total + 1):
            slot_name = f"Slot-{i}"
            cur.execute("INSERT OR IGNORE INTO slots (slot_number, is_occupied) VALUES (?, 0)", (slot_name,))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM slots")
        count = cur.fetchone()[0]
        conn.close()

        messagebox.showinfo(" Success", f"Slots updated!\nTotal slots: {count}")
        win.destroy()
        refresh_main_table()

    b = tk.Button(win, text="Update Slots", command=update_slots, bg="#0b74d1", fg="white",
                  font=("Segoe UI", 10, "bold"), width=15, height=1)
    b.pack(pady=15)


# ---------- Buttons ----------
buttons = [
    ("Park Vehicle", add_vehicle_window),
    ("Exit Vehicle", exit_vehicle_window),
    ("View Parked Vehicles", view_parked_window),
    ("Payments / Summary", payments_window),
    ("Slot Status", slot_status_window),
    ("➕ Add Slots", lambda: add_slots_window())
]

btn_frame = tk.Frame(frame, bg="#fffdfc")
btn_frame.pack(pady=12, fill="x")

for i, (txt, cmd) in enumerate(buttons):
    b = tk.Button(btn_frame, text=txt, command=cmd, **btn_style)
    b.grid(row=0, column=i, padx=8, ipadx=4, sticky="ew")
    b.bind("<Enter>", on_enter)
    b.bind("<Leave>", on_leave)
    btn_frame.grid_columnconfigure(i, weight=1)

# ---------- Status label ----------
status_label = tk.Label(frame, text="Total Slots: -    Available: -    Parked: -",
                        bg="#b5aedf", font=("Segoe UI", 11, "bold"))
status_label.pack(pady=6)

# ---------- Main table ----------
columns = ("ID", "Vehicle", "Slot", "Entry", "Exit")
main_table = ttk.Treeview(frame, columns=columns, show="headings", height=12)
for c in columns:
    main_table.heading(c, text=c)
    main_table.column(c, anchor="center", width=160)
main_table.pack(expand=True, fill="both", padx=12, pady=8)

# Initialize and run
refresh_main_table()
root.mainloop()
