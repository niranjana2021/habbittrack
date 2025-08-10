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
    # Use colored badge icons for top three and highlight their background
    badges = [
        "\U0001F947",  # 🥇 gold medal
        "\U0001F948",  # 🥈 silver medal
        "\U0001F949"   # 🥉 bronze medal
    ]
   # colors = ["#eedc78", "#a1a0a0", "#cea47a"]  # gold, silver, bronze
    for rank, row in enumerate(rows, 1):
        badge = badges[rank-1] if rank <= 3 else ""
        entry = f"{badge} {rank}. {row['username']:<10} {row['rewards']} pts"
        lb_list.insert(tk.END, entry)
       # if rank <= 3:
           # lb_list.itemconfig(rank-1, {'bg': colors[rank-1], 'fg': '#000000'})

def animate_reward(frame, points):
    emoji = "🎉"
    label = tk.Label(frame, text=f"{emoji} +{points} pts! {emoji}", font=("Times New Roman", 20, "bold"), fg="#d84315", bg="#fffde7")
    label.place(relx=0.5, y=80, anchor="center")

    # Animation: fade in, bounce, fade out
    def fade_in(step=0):
        if step <= 10:
            alpha = int(25 * step)
            label.config(fg=f"#d84315", bg="#fffde7")
            label.after(30, fade_in, step+1)
        else:
            bounce(0)

    def bounce(step):
        if step < 15:
            y = 80 - abs(10 - step) * 3
            label.place_configure(y=y)
            label.after(30, bounce, step+1)
        else:
            fade_out(0)

    def fade_out(step):
        if step <= 10:
            alpha = 255 - int(25 * step)
            label.config(fg=f"#d84315", bg="#fffde7")
            label.after(30, fade_out, step+1)
        else:
            label.destroy()

    fade_in()

def show_main_window():
    global current_user
    root = tk.Tk()
    root.title("🏆 Gamified Habit Tracker")
    root.geometry("850x600")
    root.config(bg="#fdf6e3")

    user_data = get_user(current_user)
    habit_data = get_habits(current_user)

    tk.Label(root, text=f"👋 Welcome, {current_user.title()}!", font=("Times New Roman", 20, "bold"), bg="#fdf6e3", fg="#000000").grid(row=0, column=0, columnspan=3, pady=15)
    reward_label = tk.Label(root, text=f"⭐ Reward Points: {user_data['rewards']}", font=("Times New Roman", 14, "bold"), bg="#fdf6e3", fg="#000000")
    reward_label.grid(row=1, column=0, columnspan=3)

    habit_frame = tk.LabelFrame(root, text="📜 Your Habits", font=("Times New Roman", 13), bg="#fdf6e3", fg="#000000", padx=10, pady=10)
    habit_frame.grid(row=2, column=0, padx=15, pady=10, sticky="nsew")

    habit_list = tk.Listbox(habit_frame, height=8, font=("Times New Roman", 11), width=25)
    habit_list.pack(fill="both", expand=True)

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

            points = 5

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE habits SET last_done=%s WHERE username=%s AND habit_name=%s",
                           (today, current_user, habit))
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
                points_to_deduct = 5
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

    btn_frame = tk.Frame(habit_frame, bg="#fdf6e3")
    btn_frame.pack(pady=5, fill="x")
    ttk.Button(btn_frame, text="Add Habit", command=add_habit, width=10).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Mark Done", command=mark_done, width=10).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Delete Habit", command=delete_habit, width=10).pack(side="left", padx=5)

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

        timer_label = tk.Label(timer_win, text="00:00", font=("Times New Roman", 28), bg="#e0f2f1", fg="#000000")
        timer_label.pack(pady=15)
        update_label()

        btns = tk.Frame(timer_win, bg="#e0f2f1")
        btns.pack(pady=5)
        style = ttk.Style(timer_win)
        style.configure("TButton", font=("Times New Roman", 11), padding=6, relief="flat", background="#ffffff", foreground="#000000")
        ttk.Button(btns, text="Start", command=start, style="TButton", width=10).pack(side="left", padx=7)
        ttk.Button(btns, text="Stop", command=stop, style="TButton", width=10).pack(side="left", padx=7)
        ttk.Button(btns, text="Reset", command=reset, style="TButton", width=10).pack(side="left", padx=7)


    lb_frame = tk.LabelFrame(root, text="🏅 Leaderboard", font=("Times New Roman", 13), bg="#fdf6e3", fg="#000000")
    lb_frame.grid(row=2, column=1, padx=15, pady=10, sticky="nsew")
    lb_list = tk.Listbox(lb_frame, font=("Times New Roman", 12), width=20)
    lb_list.pack(fill="both", expand=True)
    refresh_leaderboard(lb_list)

    chart_frame = tk.LabelFrame(root, text="📊 Habit Progress", font=("Times New Roman", 13), bg="#fdf6e3", fg="#000000", padx=10, pady=10)
    chart_frame.grid(row=2, column=2, padx=15, pady=10, sticky="nsew")
    canvas = tk.Canvas(chart_frame, height=300, width=280, bg="#fdf6e3", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    def update_chart():
        canvas.delete("all")
        bar_height = 18
        spacing = 32
        x0 = 90
        for i, (habit, info) in enumerate(habit_data.items()):
            total_time = info.get("total_time", 0)  # total_time in minutes
            hours = total_time // 60
            mins = total_time % 60
            y = i * spacing + 10
            # Show tick if last_done is today
            tick = " ✔️" if info.get('last_done') == datetime.date.today() else ""
            canvas.create_text(5, y, anchor="nw", text=f"📌 {habit}{tick}", font=("Times New Roman", 11))
            bar_length = min(total_time, 220)
            canvas.create_rectangle(x0, y - 2, x0 + bar_length, y + bar_height - 2, fill="#000000")
            time_str = f"{hours}h {mins}m"
            canvas.create_text(x0 + bar_length + 5, y, anchor="nw", text=f"{time_str}", font=("Times New Roman", 11), fill="#000000")

    update_chart()

    # Timer bar at the bottom
    timer_frame = tk.LabelFrame(root, text="⏰ Timer", font=("Times New Roman", 13), bg="#fdf6e3", fg="#000000")
    timer_frame.grid(row=3, column=0, columnspan=3, padx=15, pady=10, sticky="ew")
    timer_icon = tk.Label(timer_frame, text="⏱️", font=("Times New Roman", 32), bg="#fdf6e3", fg="#000000")
    timer_icon.pack(side="left", padx=10)
    timer_display_var = tk.StringVar(value="00:00")
    timer_display = tk.Label(timer_frame, textvariable=timer_display_var, font=("Times New Roman", 28), bg="#fdf6e3", fg="#000000")
    timer_display.pack(side="left", padx=10)

    timer_running = [False]
    timer_seconds = [0]

    def update_main_timer():
        mins, secs = divmod(timer_seconds[0], 60)
        timer_display_var.set(f"{mins:02d}:{secs:02d}")

    def main_timer_tick():
        if timer_running[0]:
            timer_seconds[0] += 1
            update_main_timer()
            root.after(1000, main_timer_tick)

    def main_timer_start():
        if not timer_running[0]:
            timer_running[0] = True
            main_timer_tick()

    def main_timer_stop():
        timer_running[0] = False

    def main_timer_reset():
        timer_running[0] = False
        timer_seconds[0] = 0
        update_main_timer()

    btns = tk.Frame(timer_frame, bg="#fdf6e3")
    btns.pack(side="left", padx=10)
    style = ttk.Style(timer_frame)
    style.configure("TButton", font=("Times New Roman", 11), padding=6, relief="flat", background="#ffffff", foreground="#000000")
    ttk.Button(btns, text="Start", command=main_timer_start, style="TButton", width=10).pack(side="left", padx=7)
    ttk.Button(btns, text="Stop", command=main_timer_stop, style="TButton", width=10).pack(side="left", padx=7)
    ttk.Button(btns, text="Reset", command=main_timer_reset, style="TButton", width=10).pack(side="left", padx=7)

    def main_timer_finish():
        selected = habit_list.curselection()
        if not selected:
            messagebox.showinfo("Select Habit", "Please select a habit to add the timer progress.")
            return
        habit = habit_list.get(selected)
        elapsed_minutes = timer_seconds[0] // 60
        if elapsed_minutes > 0:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE habits SET total_time = total_time + %s WHERE username=%s AND habit_name=%s", (elapsed_minutes, current_user, habit))
            conn.commit()
            cursor.close()
            conn.close()
            nonlocal habit_data
            habit_data = get_habits(current_user)
            update_chart()
            refresh_habit_list()
            messagebox.showinfo("Timer Finished", f"Added {elapsed_minutes} minutes to '{habit}'.")
            main_timer_reset()
        else:
            messagebox.showinfo("No Time", "Timer must run for at least 1 minute to add progress.")

    ttk.Button(btns, text="Finish", command=main_timer_finish, style="TButton", width=10).pack(side="left", padx=7)
    update_main_timer()

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
    login.config(bg="#fdf6e3")

    username_entry = tk.Entry(login, font=("Times New Roman", 12), width=15)
    username_entry.grid(row=1, column=1, pady=5, padx=10)
    password_entry = tk.Entry(login, font=("Times New Roman", 12), width=15, show="*")
    password_entry.grid(row=2, column=1, pady=5, padx=10)
    tk.Label(login, text="Login", font=("Times New Roman", 16, "bold"), bg="#fdf6e3", fg="#000000").grid(row=0, column=0, columnspan=2, pady=10)
    tk.Label(login, text="Username:", bg="#fdf6e3", font=("Times New Roman", 12), fg="#000000").grid(row=1, column=0, sticky="e", padx=10)
    tk.Label(login, text="Password:", bg="#fdf6e3", font=("Times New Roman", 12), fg="#000000").grid(row=2, column=0, sticky="e", padx=10)

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
    signup.config(bg="#fdf6e3")

    username_entry = tk.Entry(signup, font=("Times New Roman", 12), width=18)
    username_entry.grid(row=1, column=1, pady=5)
    password_entry = tk.Entry(signup, font=("Times New Roman", 12), width=18, show="*")
    password_entry.grid(row=2, column=1, pady=5)
    confirm_entry = tk.Entry(signup, font=("Times New Roman", 12), width=18, show="*")
    confirm_entry.grid(row=3, column=1, pady=5)
    tk.Label(signup, text="Create Account", font=("Times New Roman", 16, "bold"), bg="#fdf6e3", fg="#000000").grid(row=0, column=0, columnspan=2, pady=10)
    tk.Label(signup, text="Username:", bg="#fdf6e3", font=("Times New Roman", 12), fg="#000000").grid(row=1, column=0, sticky="e", padx=10)
    tk.Label(signup, text="Password:", bg="#fdf6e3", font=("Times New Roman", 12), fg="#000000").grid(row=2, column=0, sticky="e", padx=10)
    tk.Label(signup, text="Confirm:", bg="#fdf6e3", font=("Times New Roman", 12), fg="#000000").grid(row=3, column=0, sticky="e", padx=10)

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
    welcome.config(bg="#fdf6e3")

    tk.Label(welcome, text="Habit Tracker", font=("Times New Roman", 18, "bold"), bg="#fdf6e3", fg="#000000").pack(pady=15)
    ttk.Button(welcome, text="Login", command=lambda: [welcome.destroy(), show_login_window()]).pack(pady=10)
    ttk.Button(welcome, text="Sign Up", command=lambda: [welcome.destroy(), show_signup_window()]).pack()

    welcome.mainloop()

if __name__ == "__main__":
    show_welcome_window()
