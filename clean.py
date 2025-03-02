import cv2
import numpy as np
from scipy.spatial import KDTree
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import json
from color_data import color_categories
currentpallet = []
global accent_color_selected
accent_color_selected = None

def color_distance(rgb1, rgb2):
    return np.linalg.norm(np.array(rgb1) - np.array(rgb2))

def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def upload_image():
    global image, img_label, upload_button
    file_path = filedialog.askopenfilename()
    if file_path:
        image = cv2.imread(file_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(image)
        img.thumbnail((300, 300))
        img_tk = ImageTk.PhotoImage(img)
        img_label.config(image=img_tk)
        img_label.image = img_tk
        toggle_controls(True)
        upload_button.config(text="Change Image")

def process_image():
    threshold = int(threshold_entry.get())
    min_percent = float(percent_entry.get())
    threshold_slider.set(threshold)
    percent_slider.set(min_percent)
    colors = count_colors(image, threshold, min_percent)
    
    
    palette_img = show_palette(colors)
    palette_label.config(image=palette_img)
    palette_label.image = palette_img

def count_colors(image, threshold, min_percent):
    
    pixels = image.reshape(-1, 3)
    unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
    total_pixels = len(pixels)
    global color_data
    color_data = []
    for color, count in zip(unique_colors, counts):
        percent = (count / total_pixels) * 100
        if percent >= min_percent:
            new_color = {"rgb": tuple(color), "percent": round(percent, 2), "count": count}
            add_or_merge_color(color_data, new_color, threshold)

    color_data.sort(key=lambda x: x["percent"], reverse=True)
    global currentpallet
    currentpallet = color_data
    return color_data

def add_or_merge_color(color_list, new_color, threshold):
    if not color_list:
        color_list.append(new_color)
        return

    tree = KDTree([color["rgb"] for color in color_list])
    dist, idx = tree.query(new_color["rgb"])

    if dist < threshold:
        color_list[idx]["percent"] += new_color["percent"]
        color_list[idx]["count"] += new_color["count"]
    else:
        color_list.append(new_color)

def show_palette(color_data):
    palette_height = 100
    palette_width = 300
    total_pixels = sum(color["count"] for color in color_data)
    color_blocks = [
        np.full((palette_height, int((color["count"] / total_pixels) * palette_width), 3), color["rgb"], dtype=np.uint8)
        for color in color_data if int((color["count"] / total_pixels) * palette_width) > 0
    ]
    toggle_controls2(True)
    palette = np.hstack(color_blocks) if color_blocks else np.zeros((palette_height, palette_width, 3), dtype=np.uint8)
    return ImageTk.PhotoImage(Image.fromarray(palette))

def find_accent_colors():
    if len(currentpallet) < 2:
        return []
    weighted_mid = np.average([c["rgb"] for c in currentpallet], axis=0, weights=[c["percent"] for c in currentpallet])
    sorted_colors = sorted(currentpallet, key=lambda x: color_distance(weighted_mid, x["rgb"]), reverse=True)
    return sorted_colors[:5]  

def show_accent_colors():
    accent_colors = find_accent_colors()
    if accent_colors:
        for widget in accent_frame.winfo_children():
            widget.destroy()
        for accent in accent_colors:
            accent_img = np.full((50, 50, 3), accent["rgb"], dtype=np.uint8)
            accent_img = ImageTk.PhotoImage(Image.fromarray(accent_img))
            btn = tk.Button(accent_frame, image=accent_img, command=lambda c=accent: select_accent_color(c))
            btn.image = accent_img
            btn.pack(side=tk.LEFT)

def select_accent_color(color):
    global accent_frame
    accent_selected = np.full((100, 100, 3), color["rgb"], dtype=np.uint8)
    global accent_color_selected
    accent_color_selected=accent_selected
    accent_selected = ImageTk.PhotoImage(Image.fromarray(accent_selected))
    accent_label.config(image=accent_selected)
    accent_label.image = accent_selected
    toggle_controls3(True)
    for widget in accent_frame.winfo_children():
        widget.destroy()

def show_colors():
    color_window = tk.Toplevel(root)
    color_window.title("Color Palette")
    color_window.geometry("400x400")
    color_frame = tk.Frame(color_window)
    color_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    for idx, color in enumerate(currentpallet):
        color_name = find_subcolor_name(color["rgb"])[1]  
        rgb_str = f"RGB: {color['rgb']}"
        color_block = tk.Label(color_frame, width=20, height=2, bg=rgb_to_hex(color["rgb"]))
        color_block.grid(row=idx, column=0, padx=5, pady=5)
        color_label = tk.Label(color_frame, text=f"{color_name} ({rgb_str})", anchor='w')
        color_label.grid(row=idx, column=1, padx=5, pady=5)      

def find_subcolor_name(input_rgb):
    min_distance = float('inf')
    best_main_color = None
    best_subcolor = None

    for main_color, subcolors in color_categories.items():
        for subcolor_name, subcolor_data in subcolors.items():
            distance = color_distance(input_rgb, subcolor_data["rgb"])  
            if distance < min_distance:
                min_distance = distance
                best_main_color = main_color
                best_subcolor = subcolor_name

    return best_main_color, best_subcolor

def update_threshold(val):
    threshold_entry.delete(0, tk.END)
    threshold_entry.insert(0, str(int(float(val))))

def update_percent(val):
    percent_entry.delete(0, tk.END)
    percent_entry.insert(0, str(float(val)))

def save_colors_to_json():
    folder_selected = filedialog.askdirectory()
    if not folder_selected:
        print("Збереження скасовано.")
        return

    color_ids = []

    if accent_color_selected is not None:
        main_color, subcolor_name = find_subcolor_name(accent_color_selected)
        subcolor_data = color_categories.get(main_color, {}).get(subcolor_name, {})
        color_id = subcolor_data.get("id", None)
        if color_id:
            color_ids.append(color_id)  

    for color in currentpallet:
        main_color, subcolor_name = find_subcolor_name(color["rgb"])
        subcolor_data = color_categories.get(main_color, {}).get(subcolor_name, {})
        color_id = subcolor_data.get("id", None)
        if color_id and color_id not in color_ids:  
            color_ids.append(color_id)

    file_path = f"{folder_selected}/colors.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(color_ids, f, ensure_ascii=False, indent=4)

    print(f"Кольори збережено у {file_path}")

def toggle_controls3(state):
    widgets = [save_button]
    for widget in widgets:
        widget.config(state=tk.NORMAL if state else tk.DISABLED)

def toggle_controls2(state):
    widgets = [accent_button, show_colors_button]
    for widget in widgets:
        widget.config(state=tk.NORMAL if state else tk.DISABLED)

def toggle_controls(state):
    widgets = [threshold_slider, percent_slider, threshold_entry, percent_entry, process_button]
    for widget in widgets:
        widget.config(state=tk.NORMAL if state else tk.DISABLED)

def create_ui():
    
    global threshold_slider, percent_slider, threshold_entry, percent_entry, root, img_label, palette_label, accent_label, accent_frame, image, upload_button, control_widgets, process_button, accent_button, show_colors_button, save_button
    image = None  
    root = tk.Tk()
    root.title("Color Extractor")
    root.geometry("700x500")
    frame_left = tk.Frame(root)
    frame_left.pack(side=tk.LEFT, padx=10, pady=10)
    img_label = tk.Label(frame_left)
    img_label.pack()
    frame_right = tk.Frame(root)
    frame_right.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)
    palette_label = tk.Label(frame_right)
    palette_label.pack()
    accent_label = tk.Label(frame_right)
    accent_label.pack()
    accent_frame = tk.Frame(frame_right)
    accent_frame.pack()
    frame_controls = tk.Frame(frame_right)
    frame_controls.pack()
    tk.Label(frame_controls, text="Merge Threshold").grid(row=0, column=0)
    threshold_slider = tk.Scale(frame_controls, from_=0, to=100, orient=tk.HORIZONTAL)
    threshold_slider.set(100)
    threshold_slider.grid(row=0, column=1)
    threshold_entry = tk.Entry(frame_controls, width=5)
    threshold_entry.grid(row=0, column=2)
    threshold_entry.insert(0, "50")
    tk.Label(frame_controls, text="Min Percentage").grid(row=1, column=0)
    percent_slider = tk.Scale(frame_controls, from_=0, to=10, resolution=0.1, orient=tk.HORIZONTAL)
    percent_slider.set(0.5)
    percent_slider.grid(row=1, column=1)
    percent_entry = tk.Entry(frame_controls, width=5)
    percent_entry.grid(row=1, column=2)
    percent_entry.insert(0, "1.0")
    frame_buttons = tk.Frame(frame_right)
    frame_buttons.pack()
    upload_button = tk.Button(frame_buttons, text="Upload Image", command=upload_image)
    upload_button.pack(side=tk.LEFT, padx=5, pady=5)
    process_button = tk.Button(frame_buttons, text="Process Image", command=process_image)
    process_button.pack(side=tk.RIGHT, padx=5, pady=5)
    accent_button = tk.Button(frame_buttons, text="Find Accent Colors", command=show_accent_colors)
    accent_button.pack(side=tk.RIGHT, padx=5, pady=5)
    show_colors_button = tk.Button(root, text="Show Colors", command=show_colors)
    show_colors_button.pack(pady=10)
    save_button = tk.Button(frame_buttons, text="Save", command=save_colors_to_json)
    save_button.pack(side=tk.LEFT, padx=5, pady=5)
    threshold_slider.bind("<Motion>", lambda event: update_threshold(threshold_slider.get()))
    percent_slider.bind("<Motion>", lambda event: update_percent(percent_slider.get()))
    threshold_entry.bind("<KeyRelease>", lambda event: threshold_slider.set(int(threshold_entry.get())))
    percent_entry.bind("<KeyRelease>", lambda event: percent_slider.set(float(percent_entry.get())))
    control_widgets = [threshold_slider, percent_slider, threshold_entry, percent_entry, process_button, save_button, accent_button, show_colors_button]
    toggle_controls(False)
    toggle_controls2(False)
    toggle_controls3(False)
    root.mainloop()

create_ui()
