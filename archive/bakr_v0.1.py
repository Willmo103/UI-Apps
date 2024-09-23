import tkinter as tk
from tkinter import messagebox
import yaml
import threading
import time
import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Global variable to control the observer thread
running = False

class Config:
    def __init__(self, config_file):
        self.load_config(config_file)

    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            cfg = yaml.safe_load(f)
            self.watch_paths = cfg.get('watch_paths', [])
            self.backup_dir = cfg.get('backup_dir', 'backups')
            self.remote_host = cfg.get('remote_host', '')
            self.remote_user = cfg.get('remote_user', '')
            self.remote_path = cfg.get('remote_path', '')
            self.git_repo_path = cfg.get('git_repo_path', '')
            self.git_remote = cfg.get('git_remote', 'origin')
            self.git_branch = cfg.get('git_branch', 'main')
            self.zip_password = cfg.get('zip_password', '')

class BackupHandler(FileSystemEventHandler):
    def __init__(self, config):
        self.config = config

    def process(self, event):
        # Implement backup, transfer, and git commit/push
        for path in self.config.watch_paths:
            if os.path.exists(path):
                timestamp = time.strftime("%Y%m%d%H%M%S")
                zip_filename = f"backup_{timestamp}.7z"
                zip_filepath = os.path.join(self.config.backup_dir, zip_filename)

                # Create backup directory if it doesn't exist
                os.makedirs(self.config.backup_dir, exist_ok=True)

                # Zip and encrypt the files using 7zip
                zip_command = [
                    '7z', 'a', '-t7z', '-mhe=on', f"-p{self.config.zip_password}",
                    zip_filepath, path
                ]
                subprocess.run(zip_command)

                # Transfer the zipped file using scp
                scp_command = [
                    'scp', zip_filepath,
                    f"{self.config.remote_user}@{self.config.remote_host}:{self.config.remote_path}"
                ]
                subprocess.run(scp_command)

                # Commit and push to Git repository
                os.chdir(self.config.git_repo_path)
                subprocess.run(['git', 'add', '.'])
                commit_message = f"Automatic backup {timestamp}"
                subprocess.run(['git', 'commit', '-m', commit_message])
                subprocess.run(['git', 'push', self.config.git_remote, self.config.git_branch])

    def on_modified(self, event):
        self.process(event)

    def on_created(self, event):
        self.process(event)

def start_watching(config):
    global running
    running = True
    event_handler = BackupHandler(config)
    observer = Observer()
    for path in config.watch_paths:
        observer.schedule(event_handler, path=path, recursive=True)
    observer.start()
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def stop_watching():
    global running
    running = False

class BackupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Automatic Backup Application")
        self.geometry("300x150")
        self.config = None
        self.thread = None

        self.create_widgets()

    def create_widgets(self):
        self.start_button = tk.Button(self, text="Start Backup", command=self.start_backup)
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(self, text="Stop Backup", command=self.stop_backup, state='disabled')
        self.stop_button.pack(pady=10)

        self.load_button = tk.Button(self, text="Load Config", command=self.load_config)
        self.load_button.pack(pady=10)

    def load_config(self):
        config_file = 'config.yml'  # You can use a file dialog to select the file
        if os.path.exists(config_file):
            self.config = Config(config_file)
            messagebox.showinfo("Config Loaded", "Configuration loaded successfully.")
        else:
            messagebox.showerror("Error", "Config file not found.")

    def start_backup(self):
        if not self.config:
            messagebox.showwarning("No Config", "Please load the configuration file first.")
            return
        self.thread = threading.Thread(target=start_watching, args=(self.config,), daemon=True)
        self.thread.start()
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')

    def stop_backup(self):
        stop_watching()
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        messagebox.showinfo("Backup Stopped", "Backup process has been stopped.")

if __name__ == "__main__":
    app = BackupApp()
    app.mainloop()
