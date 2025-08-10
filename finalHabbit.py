import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime
import random
import mysql.connector

# DB connection
def get_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="Idly@a2b",
        database="habbittracker"
    )

current_user = None
challenges = ["🥤 Drink 2L Water", "📖 Read 10 Pages", "❌ No Junk Food", "🏃 Exercise 30 mins"]

def get_user(username):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def get_habits(username):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM habits WHERE username=%s", (username,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {
        row['habit_name']: {
            'last_done': row['last_done'],
            'streak': row['streak'],
            'total_time': row.get('total_time', 0)  # total_time now in minutes
        } for row in rows
    }

def refresh_leaderboard(lb_list):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, rewards FROM users ORDER BY rewards DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    lb_list.delete(0, tk.END)
    for rank, row in enumerate(rows, 1):
        lb_list.insert(tk.END, f"{rank}. {row['username']:<10} {row['rewards']} pts")
        #if rank == 1:
           # lb_list.itemconfig(tk.END, {'bg': '#ffeb3b'}) # highlight the topper

def animate_reward(frame, points):
    emoji = "🎉"
    label = tk.Label(frame, text=f"{emoji} +{points} pts! {emoji}", font=("Forte", 18, "bold"), fg="#00796b", bg="#e0f2f1")
    label.place(relx=0.5, y=50, anchor="center")

    def animate(step=0):
        if step < 30:
            label.place_configure(y=50 - step*2, relx=0.5 + step*0.005)
            label.after(30, animate, step+1)
        else:
            label.destroy()

    animate()

def show_main_window():
    global current_user
    root = tk.Tk()
    root.title("🏆 Gamified Habit Tracker")
    root.geometry("850x600")
    root.config(bg="#e0f2f1")

    user_data = get_user(current_user)
    habit_data = get_habits(current_user)

    tk.Label(root, text=f"👋 Welcome, {current_user.title()}!", font=("Forte", 20, "bold"), bg="#e0f2f1", fg="#004d40").grid(row=0, column=0, columnspan=3, pady=15)
    reward_label = tk.Label(root, text=f"⭐ Reward Points: {user_data['rewards']}", font=("Forte", 14, "bold"), bg="#e0f2f1", fg="#00796b")
    reward_label.grid(row=1, column=0, columnspan=3)

    habit_frame = tk.LabelFrame(root, text="📜 Your Habits", font=("Forte", 13), bg="#ffffff", padx=10, pady=10)
    habit_frame.grid(row=2, column=0, padx=15, pady=10, sticky="nsew")

    habit_list = tk.Listbox(habit_frame, height=8, font=("Forte", 11), width=25)
    habit_list.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    btn_frame = tk.Frame(habit_frame, bg="#ffffff")
    btn_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0,5))
    btn_frame.grid_columnconfigure(0, weight=1)
    btn_frame.grid_columnconfigure(1, weight=1)
    btn_frame.grid_columnconfigure(2, weight=1)
    btn_frame.grid_columnconfigure(3, weight=1)

    def refresh_habit_list():
        nonlocal habit_data
        habit_data = get_habits(current_user)
        habit_list.delete(0, tk.END)
        for habit in habit_data:
            habit_list.insert(tk.END, habit)

    refresh_habit_list()

    def add_habit():
        habit = simpledialog.askstring("New Habit", "Enter a new habit:")
        if habit:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM habits WHERE username=%s AND habit_name=%s", (current_user, habit))
            if cursor.fetchone():
                messagebox.showwarning("Duplicate", "This habit already exists.")
                return
            cursor.execute("INSERT INTO habits (username, habit_name) VALUES (%s, %s)", (current_user, habit))
            conn.commit()
            cursor.close()
            conn.close()
            refresh_habit_list()
            update_chart()

    def mark_done():
        nonlocal habit_data
        selected = habit_list.curselection()
        if selected:
            habit = habit_list.get(selected)
            today = datetime.date.today()
            info = habit_data[habit]
            last_done = info['last_done']

            if last_done == today:
                messagebox.showinfo("Already Done", f"You already completed '{habit}' today!")
                return

            try:
                hours = float(simpledialog.askstring("Time Spent", f"How many hours did you spend on '{habit}' today? (24-hour format)"))
                if hours < 0 or hours > 24:
                    raise ValueError("Invalid hours")
            except:
                messagebox.showerror("Error", "Please enter a valid number of hours (0-24).")
                return

            streak = info['streak'] + 1 if last_done == today - datetime.timedelta(days=1) else 1
            points = streak * 5

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE habits SET last_done=%s, streak=%s, total_time = total_time + %s WHERE username=%s AND habit_name=%s",
                           (today, streak, hours, current_user, habit))
            cursor.execute("UPDATE users SET rewards = rewards + %s WHERE username=%s", (points, current_user))
            conn.commit()
            cursor.close()
            conn.close()

            habit_data = get_habits(current_user)
            animate_reward(root, points)
            reward_label.config(text=f"⭐ Reward Points: {get_user(current_user)['rewards']}")
            refresh_leaderboard(lb_list)
            update_chart()
            refresh_habit_list()

    def delete_habit():
        selected = habit_list.curselection()
        if selected:
            habit = habit_list.get(selected)
            confirm = messagebox.askyesno("Delete Habit", f"Are you sure you want to delete '{habit}'?")
            if confirm:
                streak = habit_data[habit]['streak']
                points_to_deduct = streak * 5
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM habits WHERE username=%s AND habit_name=%s", (current_user, habit))
                cursor.execute("UPDATE users SET rewards = GREATEST(rewards - %s, 0) WHERE username=%s",
                               (points_to_deduct, current_user))
                conn.commit()
                cursor.close()
                conn.close()

                reward_label.config(text=f"⭐ Reward Points: {get_user(current_user)['rewards']}")
                refresh_habit_list()
                update_chart()
                refresh_leaderboard(lb_list)

    def start_timer():
        selected = habit_list.curselection()
        if not selected:
            messagebox.showinfo("Select Habit", "Please select a habit to start the timer.")
            return
        habit = habit_list.get(selected)
        timer_win = tk.Toplevel(root)
        timer_win.title(f"Timer for {habit}")
        timer_win.geometry("300x180")
        timer_win.config(bg="#e0f2f1")

        time_var = tk.IntVar(value=0)
        running = [False]

        def update_label():
            mins, secs = divmod(time_var.get(), 60)
            timer_label.config(text=f"{mins:02d}:{secs:02d}")

        def tick():
            if running[0]:
                time_var.set(time_var.get() + 1)
                update_label()
                timer_win.after(1000, tick)

        def start():
            running[0] = True
            tick()

        def stop():
            running[0] = False
            # Add elapsed time to habit progress (in minutes)
            elapsed_seconds = time_var.get()
            elapsed_minutes = elapsed_seconds // 60
            if elapsed_minutes > 0:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE habits SET total_time = total_time + %s WHERE username=%s AND habit_name=%s", (elapsed_minutes, current_user, habit))
                conn.commit()
                cursor.close()
                conn.close()
                # Refresh chart and habit list
                nonlocal habit_data
                habit_data = get_habits(current_user)
                update_chart()
                refresh_habit_list()

        def reset():
            running[0] = False
            time_var.set(0)
            update_label()

        timer_label = tk.Label(timer_win, text="00:00", font=("Forte", 28), bg="#e0f2f1", fg="#00796b")
        timer_label.pack(pady=15)
        update_label()

        btns = tk.Frame(timer_win, bg="#e0f2f1")
        btns.pack(pady=5)
        ttk.Button(btns, text="Start", command=start, width=8).pack(side="left", padx=5)
        ttk.Button(btns, text="Stop", command=stop, width=8).pack(side="left", padx=5)
        ttk.Button(btns, text="Reset", command=reset, width=8).pack(side="left", padx=5)

    ttk.Button(btn_frame, text="Add Habit", command=add_habit, width=10).grid(row=0, column=0, padx=5, pady=2)
    ttk.Button(btn_frame, text="Mark Done", command=mark_done, width=10).grid(row=0, column=1, padx=5, pady=2)
    ttk.Button(btn_frame, text="Delete Habit", command=delete_habit, width=10).grid(row=0, column=2, padx=5, pady=2)
    ttk.Button(btn_frame, text="Start Timer", command=start_timer, width=10).grid(row=0, column=3, padx=5, pady=2)

    lb_frame = tk.LabelFrame(root, text="🏅 Leaderboard", font=("Forte", 13), bg="#e0f2f1")
    lb_frame.grid(row=2, column=1, padx=15, pady=10, sticky="nsew")
    lb_list = tk.Listbox(lb_frame, font=("Forte", 12), width=20)
    lb_list.pack(fill="both", expand=True)
    refresh_leaderboard(lb_list)

    chart_frame = tk.LabelFrame(root, text="📊 Habit Progress", font=("Forte", 13), bg="#ffffff", padx=10, pady=10)
    chart_frame.grid(row=2, column=2, padx=15, pady=10, sticky="nsew")
    canvas = tk.Canvas(chart_frame, height=300, width=280, bg="#ffffff", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    def update_chart():
        canvas.delete("all")
        bar_height = 18
        spacing = 32
        x0 = 90
        for i, (habit, info) in enumerate(habit_data.items()):
            streak = info["streak"]
            total_time = info.get("total_time", 0)  # total_time in minutes
            hours = total_time // 60
            mins = total_time % 60
            y = i * spacing + 10
            canvas.create_text(5, y, anchor="nw", text=f"📌 {habit}", font=("Forte", 11))
            bar_length = min(streak * 20, 220)
            canvas.create_rectangle(x0, y - 2, x0 + bar_length, y + bar_height - 2, fill="#00796b")
            time_str = f"{hours}h {mins}m"
            canvas.create_text(x0 + bar_length + 5, y, anchor="nw", text=f"{streak}🔥 | {time_str}", font=("Forte", 11), fill="#004d40")

    update_chart()

    ch_frame = tk.LabelFrame(root, text="🔥 Daily Challenge", font=("Forte", 13), bg="#e0f2f1")
    ch_frame.grid(row=3, column=0, columnspan=3, padx=15, pady=10, sticky="ew")
    ch_text = tk.StringVar()
    ch_text.set(random.choice(challenges))
    tk.Label(ch_frame, textvariable=ch_text, font=("Forte", 13, "italic"), bg="#e0f2f1", fg="#d32f2f").pack()
    ttk.Button(ch_frame, text="New Challenge", command=lambda: ch_text.set(random.choice(challenges))).pack(pady=5)

    root.grid_columnconfigure(0, weight=2)
    root.grid_columnconfigure(1, weight=1)
    root.grid_columnconfigure(2, weight=1)
    root.grid_rowconfigure(2, weight=1)

    root.mainloop()

def show_login_window():
    global current_user
    login = tk.Tk()
    login.title("Login | Habit Tracker")
    login.geometry("300x200")
    login.config(bg="#e0f2f1")

    tk.Label(login, text="Login", font=("Forte", 16, "bold"), bg="#e0f2f1", fg="#00796b").grid(row=0, column=0, columnspan=2, pady=10)
    tk.Label(login, text="Username:", bg="#e0f2f1", font=("Forte", 12)).grid(row=1, column=0, sticky="e", padx=10)
    username_entry = tk.Entry(login, font=("Forte", 12), width=15)
    username_entry.grid(row=1, column=1, pady=5, padx=10)
    tk.Label(login, text="Password:", bg="#e0f2f1", font=("Forte", 12)).grid(row=2, column=0, sticky="e", padx=10)
    password_entry = tk.Entry(login, font=("Forte", 12), width=15, show="*")
    password_entry.grid(row=2, column=1, pady=5, padx=10)

    def login_user():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        user = get_user(username)
        if user and user['password'] == password:
            global current_user
            current_user = username
            login.destroy()
            show_main_window()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    ttk.Button(login, text="Login", command=login_user).grid(row=3, column=0, columnspan=2, pady=15)
    login.mainloop()

def show_signup_window():
    signup = tk.Tk()
    signup.title("Sign Up | Habit Tracker")
    signup.geometry("320x220")
    signup.config(bg="#e0f2f1")

    tk.Label(signup, text="Create Account", font=("Forte", 16, "bold"), bg="#e0f2f1", fg="#00796b").grid(row=0, column=0, columnspan=2, pady=10)
    tk.Label(signup, text="Username:", bg="#e0f2f1", font=("Forte", 12)).grid(row=1, column=0, sticky="e", padx=10)
    username_entry = tk.Entry(signup, font=("Forte", 12), width=18)
    username_entry.grid(row=1, column=1, pady=5)
    tk.Label(signup, text="Password:", bg="#e0f2f1", font=("Forte", 12)).grid(row=2, column=0, sticky="e", padx=10)
    password_entry = tk.Entry(signup, font=("Forte", 12), width=18, show="*")
    password_entry.grid(row=2, column=1, pady=5)
    tk.Label(signup, text="Confirm:", bg="#e0f2f1", font=("Forte", 12)).grid(row=3, column=0, sticky="e", padx=10)
    confirm_entry = tk.Entry(signup, font=("Forte", 12), width=18, show="*")
    confirm_entry.grid(row=3, column=1, pady=5)

    def register_user():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        confirm = confirm_entry.get().strip()

        if not username or not password or not confirm:
            messagebox.showerror("Error", "All fields are required.")
            return
        if password != confirm:
            messagebox.showerror("Mismatch", "Passwords do not match.")
            return
        if get_user(username):
            messagebox.showwarning("User  Exists", "Username already taken.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, rewards) VALUES (%s, %s, 0)", (username, password))
        conn.commit()
        cursor.close()
        conn.close()
        messagebox.showinfo("Success", "Account created successfully!")
        signup.destroy()
        show_login_window()

    ttk.Button(signup, text="Sign Up", command=register_user).grid(row=4, column=0, columnspan=2, pady=15)
    signup.mainloop()

def show_welcome_window():
    welcome = tk.Tk()
    welcome.title("Welcome | Habit Tracker")
    welcome.geometry("300x200")
    welcome.config(bg="#e0f2f1")

    tk.Label(welcome, text="Habit Tracker", font=("Forte", 18, "bold"), bg="#e0f2f1", fg="#00796b").pack(pady=15)
    ttk.Button(welcome, text="Login", command=lambda: [welcome.destroy(), show_login_window()]).pack(pady=10)
    ttk.Button(welcome, text="Sign Up", command=lambda: [welcome.destroy(), show_signup_window()]).pack()

    welcome.mainloop()

if __name__ == "__main__":
    show_welcome_window()
