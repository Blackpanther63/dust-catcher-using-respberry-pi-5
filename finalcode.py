import serial
import time
import json
import tkinter as tk
import lgpio

# Assign GPIO pins for buttons and relay
BUTTONS = {
    "Menu": 17,
    "Back": 18,
    "Up": 27,
    "Down": 22,
    "OK": 23
}
RELAY_PIN = 25

# Initialize lgpio
h = lgpio.gpiochip_open(0)

# Set up each button as an INPUT with a pull-up resistor
for pin in BUTTONS.values():
    lgpio.gpio_claim_input(h, pin, lgpio.SET_PULL_UP)

# Set up the relay pin as an OUTPUT
lgpio.gpio_claim_output(h, RELAY_PIN)

# Ensure the relay starts OFF
lgpio.gpio_write(h, RELAY_PIN, 1)

# Initialize Serial Connection
ser = serial.Serial(port='/dev/ttyAMA0', baudrate=9600, timeout=2)

# File to store thresholds
THRESHOLD_FILE = "thresholds.json"

# Load saved thresholds
def load_thresholds():
    try:
        with open(THRESHOLD_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"PM2.5": 50, "PM10": 100}

# Save thresholds to file
def save_thresholds():
    with open(THRESHOLD_FILE, "w") as file:
        json.dump(confirmed_thresholds, file)

# Load thresholds from file
confirmed_thresholds = load_thresholds()
thresholds = confirmed_thresholds.copy()

menu_options = ["PM2.5", "PM10"]
menu_index = 0
current_selection = None
current_screen = "home"

# Variable to store the selected mode
selected_mode = "Both"  # Default mode
temp_selected_mode = selected_mode  # Temporary mode variable

# Function to read PM data from the sensor
def read_pm_data():
    try:
        ser.reset_input_buffer()
        data = ser.read(32)
        if len(data) < 32:
            return None
        if data[0] == 0x42 and data[1] == 0x4D:
            pm2_5 = ((data[6] << 8) | data[7]) / 10.0
            pm10 = ((data[8] << 8) | data[9]) / 10.0
            return pm2_5, pm10
    except Exception as e:
        print("Serial Error:", e)
        return None

# Function to update PM values on the home screen
def update_pm_values():
    global selected_mode
    pm_data = read_pm_data()
    if pm_data:
        pm2_5, pm10 = pm_data
        pm2_5_label.config(text=f"PM2.5: {pm2_5} µg/m³")
        pm10_label.config(text=f"PM10: {pm10} µg/m³")

        # Control the fan based on the selected mode
        if selected_mode == "PM2.5":
            if pm2_5 > confirmed_thresholds["PM2.5"]:
                lgpio.gpio_write(h, RELAY_PIN, 0)  # Turn ON the fan
                fan_status_label.config(text="Fan: ON")
            else:
                lgpio.gpio_write(h, RELAY_PIN, 1)  # Turn OFF the fan
                fan_status_label.config(text="Fan: OFF")
        elif selected_mode == "PM10":
            if pm10 > confirmed_thresholds["PM10"]:
                lgpio.gpio_write(h, RELAY_PIN, 0)  # Turn ON the fan
                fan_status_label.config(text="Fan: ON")
            else:
                lgpio.gpio_write(h, RELAY_PIN, 1)  # Turn OFF the fan
                fan_status_label.config(text="Fan: OFF")
        elif selected_mode == "Both":
            if pm2_5 > confirmed_thresholds["PM2.5"] or pm10 > confirmed_thresholds["PM10"]:
                lgpio.gpio_write(h, RELAY_PIN, 0)  # Turn ON the fan
                fan_status_label.config(text="Fan: ON")
            else:
                lgpio.gpio_write(h, RELAY_PIN, 1)  # Turn OFF the fan
                fan_status_label.config(text="Fan: OFF")

    root.after(1000, update_pm_values)  # Update every 1 second

# Function to switch frames
def show_frame(frame, screen_name):
    global current_screen
    current_screen = screen_name

    home_frame.pack_forget()
    menu_frame.pack_forget()
    threshold_frame.pack_forget()
    success_frame.pack_forget()
    mode_frame.pack_forget()  # Hide the mode frame when switching to other frames

    frame.pack()

# Function to open the "Set Threshold" menu
def open_menu():
    global menu_index
    menu_index = 0
    menu_label.config(text=f"> {menu_options[menu_index]}")
    show_frame(menu_frame, "menu")

# Function to navigate the menu using Up/Down buttons
def navigate_menu(direction):
    global menu_index
    if current_screen == "menu":
        if direction == "up":
            menu_index = (menu_index - 1) % len(menu_options)
        elif direction == "down":
            menu_index = (menu_index + 1) % len(menu_options)
        menu_label.config(text=f"> {menu_options[menu_index]}")

# Function to confirm selection and open threshold-setting interface
def confirm_selection():
    global current_selection
    if current_screen == "menu":
        current_selection = menu_options[menu_index]
        threshold_label.config(text=f"{current_selection} Threshold: {thresholds[current_selection]}")
        show_frame(threshold_frame, "threshold")

# Function to increase/decrease threshold value
def adjust_threshold(direction):
    if current_screen == "threshold":
        if direction == "up":
            thresholds[current_selection] += 1
        elif direction == "down":
            thresholds[current_selection] -= 1
        threshold_label.config(text=f"{current_selection} Threshold: {thresholds[current_selection]}")

# Function to confirm threshold value and save it
def confirm_threshold():
    if current_screen == "threshold":
        confirmed_thresholds[current_selection] = thresholds[current_selection]
        save_thresholds()
        success_label.config(text=f"{current_selection} Threshold Set Successfully!")
        show_frame(success_frame, "success")
        root.after(3000, lambda: show_frame(home_frame, "home"))

# Function to handle Back button logic
def handle_back():
    if current_screen == "threshold":
        show_frame(menu_frame, "menu")
    elif current_screen == "menu":
        show_frame(home_frame, "home")

# Function to open the Mode settings frame
def open_mode_window():
    show_frame(mode_frame, "mode")

# Function to select the mode
def select_mode(mode):
    global temp_selected_mode
    temp_selected_mode = mode
    mode_label.config(text=f"Mode: {temp_selected_mode}")

# Function to confirm the mode selection and show a message
def confirm_mode():
    global selected_mode, temp_selected_mode
    selected_mode = temp_selected_mode  # Update the actual selected mode
    # Show the confirmation message
    mode_confirmation_label.config(text=f"Fan working with {selected_mode}")
    mode_confirmation_label.pack(pady=20)

    # Redirect to home screen after 3 seconds
    root.after(3000, lambda: [mode_confirmation_label.pack_forget(), show_frame(home_frame, "home")])

# Initialize GUI
root = tk.Tk()
root.title("Dust Sensor Monitor")
root.geometry("500x400")

# Home Screen Frame
home_frame = tk.Frame(root)
home_frame.pack()

pm2_5_label = tk.Label(home_frame, text="PM2.5: N/A", font=('Arial', 30))
pm2_5_label.pack(pady=10)

pm10_label = tk.Label(home_frame, text="PM10: N/A", font=('Arial', 30))
pm10_label.pack(pady=10)

fan_status_label = tk.Label(home_frame, text="Fan: OFF", font=('Arial', 20))
fan_status_label.pack(pady=10)

menu_button = tk.Button(home_frame, text="Menu", font=('Arial', 30), command=open_menu)
menu_button.pack(pady=10)

# Mode Button
mode_button = tk.Button(home_frame, text="Mode", font=('Arial', 30), command=open_mode_window)
mode_button.pack(pady=10)

# Menu Frame
menu_frame = tk.Frame(root)

menu_label = tk.Label(menu_frame, text=f"> {menu_options[menu_index]}", font=('Arial', 30))
menu_label.pack(pady=10)

ok_button = tk.Button(menu_frame, text="OK", font=('Arial', 30), command=confirm_selection)
ok_button.pack(pady=10)

# Threshold Frame
threshold_frame = tk.Frame(root)
threshold_label = tk.Label(threshold_frame, text="", font=('Arial', 30))
threshold_label.pack(pady=10)

confirm_threshold_button = tk.Button(threshold_frame, text="Confirm", font=('Arial', 30), command=confirm_threshold)
confirm_threshold_button.pack(pady=10)

# Success Frame
success_frame = tk.Frame(root)
success_label = tk.Label(success_frame, text="", font=('Arial', 30))
success_label.pack(pady=50)

# Mode Frame
mode_frame = tk.Frame(root)
mode_label = tk.Label(mode_frame, text=f"Mode: {temp_selected_mode}", font=('Arial', 30))
mode_label.pack(pady=20)

# Add buttons for mode selection
pm2_5_mode_button = tk.Button(mode_frame, text="PM2.5", font=('Arial', 20), command=lambda: select_mode("PM2.5"))
pm2_5_mode_button.pack(pady=10)

pm10_mode_button = tk.Button(mode_frame, text="PM10", font=('Arial', 20), command=lambda: select_mode("PM10"))
pm10_mode_button.pack(pady=10)

both_mode_button = tk.Button(mode_frame, text="Both", font=('Arial', 20), command=lambda: select_mode("Both"))
both_mode_button.pack(pady=10)

# Add OK button to confirm mode selection
mode_ok_button = tk.Button(mode_frame, text="OK", font=('Arial', 20), command=confirm_mode)
mode_ok_button.pack(pady=10)

# Add a label to show the confirmation message
mode_confirmation_label = tk.Label(mode_frame, text="", font=('Arial', 20))

back_button = tk.Button(mode_frame, text="Back", font=('Arial', 20), command=lambda: show_frame(home_frame, "home"))
back_button.pack(pady=10)

# Function to poll button states
def poll_buttons():
    if lgpio.gpio_read(h, BUTTONS["Menu"]) == 0:
        open_menu()
        time.sleep(0.2)

    if lgpio.gpio_read(h, BUTTONS["Back"]) == 0:
        handle_back()
        time.sleep(0.2)

    if lgpio.gpio_read(h, BUTTONS["Up"]) == 0:
        if current_screen == "menu":
            navigate_menu("up")
        elif current_screen == "threshold":
            adjust_threshold("up")
        time.sleep(0.2)

    if lgpio.gpio_read(h, BUTTONS["Down"]) == 0:
        if current_screen == "menu":
            navigate_menu("down")
        elif current_screen == "threshold":
            adjust_threshold("down")
        time.sleep(0.2)

    if lgpio.gpio_read(h, BUTTONS["OK"]) == 0:
        if current_screen == "menu":
            confirm_selection()
        elif current_screen == "threshold":
            confirm_threshold()
        time.sleep(0.2)

    root.after(100, poll_buttons)

# Start updating PM values and polling for button presses
update_pm_values()
poll_buttons()

root.mainloop()

lgpio.gpiochip_close(h)