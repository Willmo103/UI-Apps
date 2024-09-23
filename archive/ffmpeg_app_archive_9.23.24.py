import logging
from logging.config import dictConfig
import os
import tkinter as tk
from tkinter import filedialog, messagebox, Menu
import subprocess
import json
import tkinter.font as tkFont
import sys

# Path to the FFmpeg binaries, which will be bundled inside the executable
if getattr(sys, 'frozen', False):  # Check if running as a PyInstaller bundle
    FFMPEG_DIR = os.path.join(sys._MEIPASS, "bin")
else:
    FFMPEG_DIR = "bin"

# Set up Global Variables
OUTPUT_PATH: str
LOGGER_NAME: str
LOG_FILE: str
FFMPEG_DIR = "bin"  # This is where we'll place the binaries
FFMPEG = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
FFPROBE = os.path.join(FFMPEG_DIR, "ffprobe.exe")
FFPLAY = os.path.join(FFMPEG_DIR, "ffplay.exe")



# Load configuration
try:
    with open("conf.json", "r") as j:
        data = json.load(j)
    OUTPUT_PATH = data["output_path"]
    dictConfig(data["logging_config"])
    LOGGER_NAME = data["logger_name"]
    LOG_FILE = os.path.join(os.path.dirname(__file__), data["log_file"])
except (FileNotFoundError, FileExistsError) as err:
    print(f"Error: {err}")
    exit(1)

# Set up logging
logger = logging.getLogger(LOGGER_NAME)

# Function to save updated configuration to conf.json
def save_config(output_path):
    try:
        # Update configuration with the new output path
        data["output_path"] = output_path
        data["mp4_dir"] = os.path.join(output_path, "mp4")
        data["gif_dir"] = os.path.join(output_path, "gif")
        with open("conf.json", "w") as j:
            json.dump(data, j, indent=4)
        logger.info(f"Configuration updated with new output path: {output_path}")
    except Exception as e:
        logger.error(f"Failed to update configuration: {str(e)}")


def get_video_info():
    input_file = input_file_var.get()
    if not input_file:
        return
    try:
        ffprobe_cmd = [
            FFPROBE,  # Use the dynamically resolved FFPROBE path
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "csv=s=x:p=0",
            input_file,
        ]
        result = subprocess.run(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        width, height, duration = result.stdout.decode("utf-8").strip().split("x")
        duration = float(duration)
        video_duration_label.config(text=f"Video Duration: {int(duration)} seconds")
        start_slider.config(to=int(duration))
        end_slider.config(to=int(duration))
        logger.info(f"Video: {input_file}, Dimensions: {width}x{height}, Duration: {int(duration)} seconds")
        rename_var.set(os.path.basename(input_file).replace(".mp4", "_processed"))
        return int(width), int(height), duration
    except Exception as e:
        messagebox.showerror("Error", f"Failed to retrieve video info: {str(e)}")
        logger.error(f"Failed to retrieve video info: {str(e)}")
        return 0, 0, 0


# Function to execute ffmpeg trimming command
def process_video():
    input_file = input_file_var.get()
    output_folder = output_folder_var.get()
    output_filename = rename_var.get()
    start_trim = start_slider.get() if trim_enabled_var.get() else 0
    end_trim = end_slider.get() if trim_enabled_var.get() else 0
    output_format = format_var.get()

    # Get video dimensions for GIF creation
    width, height, video_duration = get_video_info()

    logger.info(
        f"Processing video: {input_file} to {output_folder} as {output_filename}.{output_format}"
    )

    if not input_file or not output_folder or not output_filename:
        messagebox.showerror(
            "Error", "Please select both input file, output folder, and provide a name."
        )
        logger.error(
            "Please select both input file, output folder, and provide a name."
        )
        return

    # Ensure output folders exist
    mp4_folder = os.path.join(output_folder, "mp4")
    gif_folder = os.path.join(output_folder, "gif")
    os.makedirs(mp4_folder, exist_ok=True)
    os.makedirs(gif_folder, exist_ok=True)

    # Construct ffmpeg command array
    cmd_array = [FFMPEG, "-i", input_file]  # Use the dynamically resolved FFMPEG path

    if trim_enabled_var.get():
        cmd_array.extend(
            ["-ss", str(start_trim), "-to", str(video_duration - end_trim)]
        )

    # MP4 conversion logic
    if output_format == "MP4":
        cmd_array.extend(["-c:v", "libx264", "-c:a", "aac", "-strict", "experimental"])
        output_path = os.path.join(mp4_folder, f"{output_filename}.mp4")

    # GIF conversion logic
    if output_format == "GIF":
        cmd_array.extend([f"-vf", f"fps=10,scale={width}:{height}:flags=lanczos"])
        output_path = os.path.join(gif_folder, f"{output_filename}.gif")

    # Look for the output file and prompt user to overwrite
    if os.path.exists(output_path):
        logger.info("Creating unique filename for duplicate file")
        output_path = output_path.replace(
            f".{output_format.lower()}", f"_1.{output_format.lower()}"
        )

    try:
        cmd_array.append(output_path)
        logger.info(f"Executing command: {' '.join(cmd_array)}")
        subprocess.run(cmd_array, check=True)
        logger.info(f"Saved file to: {output_path}")
        messagebox.showinfo("Success", f"Saved file to: {output_path}")
    except Exception as e:
        logger.error(f"Failed to save {output_format}: {str(e)}")
        messagebox.showerror("Error", f"Failed to save {output_format}: {str(e)}")


# Function to open file dialog for selecting input file
def select_input_file():
    file_path = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4")])
    if file_path:
        input_file_var.set(file_path)
        get_video_info()


# Function to open file dialog for selecting output folder
def select_output_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        output_folder_var.set(folder_path)
        # Update configuration with the new output path
        save_config(folder_path)


# Function to toggle trimming options
def toggle_trimming():
    if trim_enabled_var.get():
        start_slider.config(state="normal")
        end_slider.config(state="normal")
    else:
        start_slider.config(state="disabled")
        end_slider.config(state="disabled")


# Function to open file dialog for selecting output folder
def select_output_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        output_folder_var.set(folder_path)
        # Update configuration with the new output path
        save_config(folder_path)
        output_directory_label.config(text=f"Output Directory: '{folder_path}'")
        logger.info(f"Output directory set to: {folder_path}")


# Create the main window
root = tk.Tk()
root.title("FFmpeg Video Processor")

# Set padding and spacing
padding = {"padx": 10, "pady": 10}

# Custom font
title_font = tkFont.Font(family="Helvetica", size=12, weight="bold")
label_font = tkFont.Font(family="Helvetica", size=10)
button_font = tkFont.Font(family="Helvetica", size=10, weight="bold")

# Output Folder Dropdown (Hidden by default)
output_folder_var = tk.StringVar()
output_folder_var.set(OUTPUT_PATH)  # Use default from config file
output_label = tk.Label(root, text="Output Folder (Hidden):")
output_dropdown = tk.Entry(root, textvariable=output_folder_var, width=50)
output_button = tk.Button(root, text="Browse", command=select_output_folder)

# Input File Dropdown
input_file_var = tk.StringVar()
input_label = tk.Label(root, text="Input Video:", font=label_font)
input_label.grid(row=0, column=0, **padding, sticky="e")
input_dropdown = tk.Entry(
    root, textvariable=input_file_var, width=50, bd=2, relief="groove"
)
input_dropdown.grid(row=0, column=1, **padding)
input_button = tk.Button(
    root,
    text="Browse",
    command=select_input_file,
    font=button_font,
    bd=2,
    relief="raised",
)
input_button.grid(row=0, column=2, **padding)

# Video Duration Label
video_duration_label = tk.Label(root, text="Video Duration: Unknown", font=label_font)
video_duration_label.grid(row=1, column=1, **padding)

# Rename field
rename_label = tk.Label(root, text="Rename Output File:", font=label_font)
rename_label.grid(row=2, column=0, **padding, sticky="e")
rename_var = tk.StringVar()
rename_entry = tk.Entry(root, textvariable=rename_var, width=50, bd=2, relief="groove")
rename_entry.grid(row=2, column=1, **padding)

# Sliders for trimming start and end
start_slider_label = tk.Label(root, text="Trim Seconds from Start:", font=label_font)
start_slider_label.grid(row=3, column=0, **padding, sticky="e")
start_slider = tk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL, length=300, bd=2)
start_slider.grid(row=3, column=1, **padding)

end_slider_label = tk.Label(root, text="Trim Seconds from End:", font=label_font)
end_slider_label.grid(row=4, column=0, **padding, sticky="e")
end_slider = tk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL, length=300, bd=2)
end_slider.grid(row=4, column=1, **padding)

# Trimming checkbox
trim_enabled_var = tk.IntVar(value=0)
trim_radio = tk.Checkbutton(
    root, text="Enable Trimming", variable=trim_enabled_var, font=label_font
)
trim_radio.grid(row=5, column=1, **padding)

# Format Selection (MP4 or GIF)
format_var = tk.StringVar(value="GIF")
format_label = tk.Label(root, text="Output Format:", font=label_font)
format_label.grid(row=6, column=0, **padding, sticky="e")
format_dropdown = tk.OptionMenu(root, format_var, "MP4", "GIF")
format_dropdown.config(width=8, bd=2, relief="groove")
format_dropdown.grid(row=6, column=1, **padding)

# Process Button
process_button = tk.Button(
    root,
    text="Process Video",
    command=process_video,
    font=button_font,
    width=20,
    bd=2,
    relief="raised",
)
process_button.grid(row=7, column=1, **padding)

# Output Directory Display
output_directory_label = tk.Label(
    root, text=f"Output Directory: '{OUTPUT_PATH}'", font=label_font
)
output_directory_label.grid(row=8, column=0, columnspan=3, **padding)

# Menu for selecting output folder
menu_bar = Menu(root)
file_menu = Menu(menu_bar, tearoff=0)
file_menu.add_command(label="Select Output Folder", command=select_output_folder)
menu_bar.add_cascade(label="Options", menu=file_menu)
root.config(menu=menu_bar)

# Run the main loop
root.mainloop()
