import logging
import os
import webbrowser
import tkinter as tk
from tkinter import messagebox
from tkinter.ttk import Progressbar
from concurrent.futures import ThreadPoolExecutor
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pytube import YouTube
from utils import download_and_combine_video

logging.basicConfig(
    filename="app.log",
    filemode="w",
    format="%(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)

class YouTubeDownloader(ttk.Window):
    def __init__(self):
        self.current_theme = "darkly"
        super().__init__(themename=self.current_theme)
        self.youtube = None
        self.quality_options = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.downloading = False

        self.setup_ui()

    def setup_ui(self):
        self.title("YouTube Video Downloader")
        self.geometry("600x400")
        self.resizable(False, False)

        self.container = ttk.Frame(self)
        self.container.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        self.title_label = ttk.Label(self.container, text="YouTube Video Downloader", font=('Helvetica', 24, 'bold'))
        self.title_label.pack(pady=10)

        self.url_frame = ttk.Frame(self.container)
        self.url_frame.pack(pady=10, fill=tk.X)

        self.url_label = ttk.Label(self.url_frame, text="YouTube Link:", width=15)
        self.url_label.pack(side=tk.LEFT, padx=5)

        self.url_entry = ttk.Entry(self.url_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5)

        self.quality_frame = ttk.Frame(self.container)
        self.quality_frame.pack(pady=10, fill=tk.X)

        self.quality_label = ttk.Label(self.quality_frame, text="Select the Quality:", width=15)
        self.quality_label.pack(side=tk.LEFT, padx=5)

        self.quality_combobox = ttk.Combobox(self.quality_frame, state="readonly", width=20)
        self.quality_combobox.pack(side=tk.LEFT, padx=5)
        self.quality_combobox['values'] = ['1080p', '720p', '480p', '360p', '240p']
        self.quality_combobox.current(0)

        self.audio_frame = ttk.Frame(self.container)
        self.audio_frame.pack(pady=10, fill=tk.X)

        self.download_audio_var = tk.BooleanVar(value=True)
        self.download_audio_check = ttk.Checkbutton(
            self.audio_frame, text="With Audio", variable=self.download_audio_var, bootstyle="primary", command=self.toggle_audio_options)
        self.download_audio_check.pack(side=tk.LEFT, padx=5)

        self.audio_separate_var = tk.BooleanVar(value=False)
        self.audio_separate_check = ttk.Checkbutton(
            self.audio_frame, text="Video with Separate Audio", variable=self.audio_separate_var, bootstyle="secondary")
        self.audio_separate_check.pack(side=tk.LEFT, padx=5)

        self.button_frame = ttk.Frame(self.container)
        self.button_frame.pack(pady=10, fill=tk.X)

        self.download_video_button = ttk.Button(
            self.button_frame, text="Download Video", command=self.download_video, bootstyle="success")
        self.download_video_button.pack(side=tk.LEFT, padx=10, pady=5)

        self.open_dir_button = ttk.Button(
            self.button_frame, text="Open Folder", command=self.open_download_directory, bootstyle="info")
        self.open_dir_button.pack(side=tk.LEFT, padx=10, pady=5)

        self.theme_button = ttk.Button(
            self.button_frame, text="Switch Background", command=self.switch_theme, bootstyle="secondary")
        self.theme_button.pack(side=tk.LEFT, padx=10, pady=5)

        self.progressbar = Progressbar(self.container, mode="determinate", length=400)
        self.progressbar.pack(pady=20)

    def switch_theme(self):
        self.current_theme = "darkly" if self.current_theme == "litera" else "litera"
        style = ttk.Style()
        style.theme_use(self.current_theme)
        self.log_status(f"Switched to {'Dark' if self.current_theme == 'darkly' else 'Light'} Mode")

    def log_status(self, message):
        print(message)  # For simplicity, just print the status. Implement as needed.
        logging.debug(message)

    def open_download_directory(self):
        download_directory = os.getcwd()
        webbrowser.open(download_directory)
        self.log_status(f"Opened Folder: {download_directory}")

    def toggle_audio_options(self):
        if self.download_audio_var.get():
            self.audio_separate_check.config(state=tk.NORMAL)
        else:
            self.audio_separate_check.config(state=tk.DISABLED)
            self.audio_separate_var.set(False)

    def download_video(self):
        if self.downloading:
            messagebox.showwarning("Warning", "A download is already in progress.")
            return

        url = self.url_entry.get()
        selected_quality = self.quality_combobox.get()
        if not url:
            messagebox.showwarning("Warning", "Please enter a YouTube Link.")
            return

        self.downloading = True
        self.log_status(f"Starting download in {selected_quality} quality...")
        try:
            self.progressbar["value"] = 0
            download_audio = self.download_audio_var.get()
            separate_audio = self.audio_separate_var.get()
            self.executor.submit(self.start_download, url, selected_quality, download_audio, separate_audio)
        except Exception as e:
            logging.error(f"Error starting download: {e}")
            self.progressbar.stop()
            self.downloading = False
            self.status_label.config(text="Error starting download", bootstyle="danger")
            messagebox.showerror("Error", f"An error occurred while starting the download: {e}")

    def start_download(self, url, selected_quality, download_audio, separate_audio):
        try:
            self.youtube = YouTube(url, on_progress_callback=self.show_progress)
            streams = self.youtube.streams.filter(file_extension="mp4").order_by("resolution").desc()
            self.quality_options = {f"{stream.resolution} {stream.abr or ''}".strip(): stream for stream in streams if stream.resolution or stream.abr}
            if selected_quality not in self.quality_options:
                raise ValueError("Selected quality not available")

            download_and_combine_video(
                self.youtube, self.quality_options, selected_quality, download_audio, separate_audio,
                self.log_status, self.progressbar, self.success_callback, self.error_callback
            )
        except Exception as e:
            logging.error(f"Error during download: {e}")
            self.error_callback(str(e))

    def success_callback(self, final_file):
        self.downloading = False
        self.log_status("Download completed successfully.")
        messagebox.showinfo("Success", f"Video downloaded successfully as {final_file}")
        self.clear_url()

    def error_callback(self, error_message):
        self.downloading = False
        self.log_status(f"An error occurred: {error_message}")
        messagebox.showerror("Error", f"An error occurred while downloading the video: {error_message}")

    def show_progress(self, stream, chunk, remaining):
        try:
            total_size = stream.filesize
            bytes_downloaded = total_size - remaining
            percentage_of_completion = (bytes_downloaded / total_size) * 100
            self.progressbar["value"] = percentage_of_completion
            self.update_idletasks()
            self.log_status(f"Downloaded {percentage_of_completion:.2f}%")
        except Exception as e:
            logging.error(f"Error showing progress: {e}")
            self.log_status("Error showing progress")

if __name__ == "__main__":
    app = YouTubeDownloader()
    app.mainloop()
