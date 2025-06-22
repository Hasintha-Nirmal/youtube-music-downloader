import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import yt_dlp
import pygame
from PIL import Image, ImageTk
import io
import urllib.request
import time
import queue
import webbrowser
from datetime import datetime

class YouTubeMusicDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Music Downloader")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
        
        # Initialize pygame mixer for music playback
        pygame.mixer.init()
        self.currently_playing = None
        self.paused = False
        
        # Set default download directory
        self.output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        
        # Authentication settings
        self.auth_method = tk.StringVar(value="none")
        self.browser_var = tk.StringVar(value="chrome")
        
        # Download queue and worker thread
        self.download_queue = queue.Queue()
        self.queue_active = False
        self.current_download = None
        self.download_method = tk.StringVar(value="single")
        self.max_concurrent_downloads = tk.IntVar(value=2)
        self.active_downloads = 0
        self.download_threads = []
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # App title
        title_label = ttk.Label(main_frame, text="YouTube Music Downloader", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.search_tab = ttk.Frame(self.notebook)
        self.download_tab = ttk.Frame(self.notebook)
        self.queue_tab = ttk.Frame(self.notebook)  # New queue tab
        self.player_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.info_tab = ttk.Frame(self.notebook)  # New info tab
        
        self.notebook.add(self.search_tab, text="Search")
        self.notebook.add(self.download_tab, text="Download")
        self.notebook.add(self.queue_tab, text="Queue")  # Add queue tab
        self.notebook.add(self.player_tab, text="Player")
        self.notebook.add(self.settings_tab, text="Settings")
        self.notebook.add(self.info_tab, text="Info")  # Add info tab
        
        # Setup search tab
        self.setup_search_tab()
        
        # Setup download tab
        self.setup_download_tab()
        
        # Setup queue tab
        self.setup_queue_tab()
        
        # Setup player tab
        self.setup_player_tab()
        
        # Setup settings tab
        self.setup_settings_tab()
        
        # Setup info tab
        self.setup_info_tab()
        
        # Store search results
        self.search_results = []
        self.downloaded_songs = []
        self.update_song_list()
        
        # Start queue processor
        self.start_queue_processor()
    
    def setup_search_tab(self):
        # Search Entry
        search_frame = ttk.Frame(self.search_tab)
        search_frame.pack(fill=tk.X, pady=(10, 10))
        
        search_label = ttk.Label(search_frame, text="Search for song:")
        search_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_entry = ttk.Entry(search_frame, width=50)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<Return>", lambda event: self.search_song())
        
        search_button = ttk.Button(search_frame, text="Search", command=self.search_song)
        search_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # Search Results
        results_frame = ttk.LabelFrame(self.search_tab, text="Search Results")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create treeview for search results
        self.results_tree = ttk.Treeview(results_frame, columns=("title", "duration", "channel"), show="headings")
        self.results_tree.heading("title", text="Title")
        self.results_tree.heading("duration", text="Duration")
        self.results_tree.heading("channel", text="Channel")
        
        self.results_tree.column("title", width=300)
        self.results_tree.column("duration", width=100)
        self.results_tree.column("channel", width=200)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to select
        self.results_tree.bind("<Double-1>", self.select_search_result)
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.search_tab)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        download_selected_button = ttk.Button(buttons_frame, text="Download Selected", command=self.download_selected)
        download_selected_button.pack(side=tk.LEFT, padx=5)
        
        add_to_queue_button = ttk.Button(buttons_frame, text="Add to Queue", command=self.add_selected_to_queue)
        add_to_queue_button.pack(side=tk.LEFT, padx=5)
        
        clear_button = ttk.Button(buttons_frame, text="Clear", command=self.clear_search)
        clear_button.pack(side=tk.LEFT, padx=5)
        
        # Status
        self.search_status_label = ttk.Label(self.search_tab, text="")
        self.search_status_label.pack(pady=(10, 0))
    
    def setup_download_tab(self):
        # URL Entry
        url_frame = ttk.Frame(self.download_tab)
        url_frame.pack(fill=tk.X, pady=(10, 10))
        
        url_label = ttk.Label(url_frame, text="Enter YouTube URL:")
        url_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.url_entry = ttk.Entry(url_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        paste_button = ttk.Button(url_frame, text="Paste", command=self.paste_url)
        paste_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # Output Directory
        dir_frame = ttk.Frame(self.download_tab)
        dir_frame.pack(fill=tk.X, pady=10)
        
        dir_label = ttk.Label(dir_frame, text="Save to:")
        dir_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.dir_entry = ttk.Entry(dir_frame, width=50)
        self.dir_entry.insert(0, self.output_dir)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_button = ttk.Button(dir_frame, text="Browse", command=self.browse_directory)
        browse_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # Format Options
        format_frame = ttk.LabelFrame(self.download_tab, text="Download Options")
        format_frame.pack(fill=tk.X, pady=10)
        
        # Audio Format
        self.format_var = tk.StringVar(value="mp3")
        
        format_label = ttk.Label(format_frame, text="Audio Format:")
        format_label.grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        
        mp3_radio = ttk.Radiobutton(format_frame, text="MP3", variable=self.format_var, value="mp3")
        mp3_radio.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        m4a_radio = ttk.Radiobutton(format_frame, text="M4A", variable=self.format_var, value="m4a")
        m4a_radio.grid(row=0, column=2, padx=10, pady=10, sticky=tk.W)
        
        # Audio Quality
        quality_label = ttk.Label(format_frame, text="Audio Quality:")
        quality_label.grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        
        self.quality_var = tk.StringVar(value="192")
        quality_combo = ttk.Combobox(format_frame, textvariable=self.quality_var, width=10)
        quality_combo['values'] = ("128", "192", "256", "320")
        quality_combo.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)
        quality_combo.current(1)  # Default to 192kbps
        
        # Download Method
        method_label = ttk.Label(format_frame, text="Download Method:")
        method_label.grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        
        single_radio = ttk.Radiobutton(format_frame, text="Direct Download", 
                                      variable=self.download_method, value="single")
        single_radio.grid(row=2, column=1, padx=10, pady=10, sticky=tk.W)
        
        queue_radio = ttk.Radiobutton(format_frame, text="Add to Queue", 
                                     variable=self.download_method, value="queue")
        queue_radio.grid(row=2, column=2, padx=10, pady=10, sticky=tk.W)
        
        # Progress Bar
        progress_frame = ttk.Frame(self.download_tab)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode="determinate")
        self.progress_bar.pack(fill=tk.X)
        
        # Download Button
        button_frame = ttk.Frame(self.download_tab)
        button_frame.pack(pady=20)
        
        self.download_button = ttk.Button(button_frame, text="Download", command=self.start_download, width=20)
        self.download_button.pack()
        
        # Status
        self.status_label = ttk.Label(self.download_tab, text="")
        self.status_label.pack(pady=(10, 0))
    
    def setup_queue_tab(self):
        """Setup the queue tab for managing download queue"""
        # Queue settings frame
        settings_frame = ttk.LabelFrame(self.queue_tab, text="Queue Settings")
        settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Concurrent downloads
        ttk.Label(settings_frame, text="Max Concurrent Downloads:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        
        concurrent_spinner = ttk.Spinbox(settings_frame, from_=1, to=5, textvariable=self.max_concurrent_downloads, width=5)
        concurrent_spinner.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        # Queue controls
        controls_frame = ttk.Frame(self.queue_tab)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)
        
        start_queue_button = ttk.Button(controls_frame, text="Start Queue", command=self.start_queue)
        start_queue_button.pack(side=tk.LEFT, padx=5)
        
        pause_queue_button = ttk.Button(controls_frame, text="Pause Queue", command=self.pause_queue)
        pause_queue_button.pack(side=tk.LEFT, padx=5)
        
        clear_queue_button = ttk.Button(controls_frame, text="Clear Queue", command=self.clear_queue)
        clear_queue_button.pack(side=tk.LEFT, padx=5)
        
        # Queue list
        queue_frame = ttk.LabelFrame(self.queue_tab, text="Download Queue")
        queue_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create treeview for queue
        self.queue_tree = ttk.Treeview(queue_frame, 
                                     columns=("title", "status", "progress"), 
                                     show="headings")
        self.queue_tree.heading("title", text="Title")
        self.queue_tree.heading("status", text="Status")
        self.queue_tree.heading("progress", text="Progress")
        
        self.queue_tree.column("title", width=400)
        self.queue_tree.column("status", width=100)
        self.queue_tree.column("progress", width=100)
        
        scrollbar = ttk.Scrollbar(queue_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=scrollbar.set)
        
        self.queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right-click menu for queue items
        self.queue_menu = tk.Menu(self.queue_tree, tearoff=0)
        self.queue_menu.add_command(label="Remove", command=self.remove_from_queue)
        self.queue_menu.add_command(label="Move Up", command=lambda: self.move_in_queue("up"))
        self.queue_menu.add_command(label="Move Down", command=lambda: self.move_in_queue("down"))
        
        self.queue_tree.bind("<Button-3>", self.show_queue_menu)
        
        # Queue status
        self.queue_status_label = ttk.Label(self.queue_tab, text="Queue is empty")
        self.queue_status_label.pack(pady=10)
    
    def start_queue_processor(self):
        """Start the queue processor thread"""
        self.queue_active = True
        threading.Thread(target=self.process_queue, daemon=True).start()
    
    def process_queue(self):
        """Process the download queue"""
        while True:
            if self.queue_active and self.active_downloads < self.max_concurrent_downloads.get():
                try:
                    # Get the next item from the queue (non-blocking)
                    item = self.download_queue.get_nowait()
                    
                    # Update status
                    self.root.after(0, lambda i=item: self.update_queue_item_status(i["id"], "Downloading"))
                    
                    # Start download in a new thread
                    self.active_downloads += 1
                    download_thread = threading.Thread(
                        target=self.download_queued_item, 
                        args=(item,),
                        daemon=True
                    )
                    download_thread.start()
                    self.download_threads.append(download_thread)
                    
                except queue.Empty:
                    # Queue is empty, nothing to do
                    pass
            
            # Clean up completed threads
            self.download_threads = [t for t in self.download_threads if t.is_alive()]
            
            # Update queue status
            self.root.after(0, self.update_queue_status)
            
            # Sleep to prevent high CPU usage
            time.sleep(0.5)
    
    def download_queued_item(self, item):
        """Download a queued item"""
        try:
            # Configure yt-dlp options
            audio_format = item["format"]
            audio_quality = item["quality"]
            output_dir = item["output_dir"]
            url = item["url"]
            item_id = item["id"]
            
            # Create output directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': audio_format,
                    'preferredquality': audio_quality,
                }],
                'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
                'progress_hooks': [lambda d: self.update_queue_progress_hook(d, item_id)],
                'quiet': True,
                'no_warnings': True
            }
            
            # Add authentication if selected
            if self.auth_method.get() == "browser_cookies":
                browser = self.browser_var.get()
                ydl_opts['cookiesfrombrowser'] = (browser, None, None, None)
            
            # Download the audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                base_filename = os.path.splitext(filename)[0] + f".{audio_format}"
            
            # Update queue item status
            self.root.after(0, lambda: self.update_queue_item_status(item_id, "Completed"))
            
            # Update song list if needed
            if output_dir == self.output_dir:
                self.root.after(0, self.update_song_list)
            
        except Exception as e:
            # Update queue item status with error
            self.root.after(0, lambda: self.update_queue_item_status(item_id, f"Error: {str(e)[:30]}..."))
        
        finally:
            # Decrement active downloads counter
            self.active_downloads -= 1
            self.download_queue.task_done()
    
    def update_queue_progress_hook(self, d, item_id):
        """Update progress for a queued download"""
        if d['status'] == 'downloading':
            # Calculate download progress
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            
            if total > 0:
                percent = (downloaded / total) * 100
                self.root.after(0, lambda: self.update_queue_item_progress(item_id, f"{percent:.1f}%"))
        
        elif d['status'] == 'finished':
            self.root.after(0, lambda: self.update_queue_item_progress(item_id, "Converting..."))
    
    def update_queue_item_status(self, item_id, status):
        """Update the status of a queue item"""
        for item in self.queue_tree.get_children():
            if item == item_id:
                self.queue_tree.set(item, "status", status)
                break
    
    def update_queue_item_progress(self, item_id, progress):
        """Update the progress of a queue item"""
        for item in self.queue_tree.get_children():
            if item == item_id:
                self.queue_tree.set(item, "progress", progress)
                break
    
    def update_queue_status(self):
        """Update the queue status label"""
        queue_size = self.download_queue.qsize()
        active = self.active_downloads
        status = "active" if self.queue_active else "paused"
        
        self.queue_status_label.config(
            text=f"Queue Status: {status.capitalize()} | Items in queue: {queue_size} | Active downloads: {active}"
        )
    
    def start_queue(self):
        """Start/resume the download queue"""
        self.queue_active = True
        self.update_queue_status()
    
    def pause_queue(self):
        """Pause the download queue"""
        self.queue_active = False
        self.update_queue_status()
    
    def clear_queue(self):
        """Clear all items from the download queue"""
        # Clear the queue
        while not self.download_queue.empty():
            try:
                self.download_queue.get_nowait()
                self.download_queue.task_done()
            except queue.Empty:
                break
        
        # Clear the treeview
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        
        self.update_queue_status()
    
    def show_queue_menu(self, event):
        """Show context menu for queue items"""
        item = self.queue_tree.identify_row(event.y)
        if item:
            self.queue_tree.selection_set(item)
            self.queue_menu.post(event.x_root, event.y_root)
    
    def remove_from_queue(self):
        """Remove selected item from queue"""
        selected = self.queue_tree.selection()
        if selected:
            # Note: This only removes from the UI, not from the actual queue
            # For a complete implementation, you would need to track queue items
            self.queue_tree.delete(selected[0])
    
    def move_in_queue(self, direction):
        """Move selected item up or down in the queue"""
        selected = self.queue_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        index = self.queue_tree.index(item)
        
        if direction == "up" and index > 0:
            self.queue_tree.move(item, "", index - 1)
        elif direction == "down":
            self.queue_tree.move(item, "", index + 1)
    
    def add_to_queue(self, url, title):
        """Add a URL to the download queue"""
        # Create a unique ID for this queue item
        item_id = f"item_{int(time.time())}_{len(self.queue_tree.get_children())}"
        
        # Add to queue data structure
        queue_item = {
            "id": item_id,
            "url": url,
            "title": title,
            "format": self.format_var.get(),
            "quality": self.quality_var.get(),
            "output_dir": self.dir_entry.get(),
            "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.download_queue.put(queue_item)
        
        # Add to queue UI
        self.queue_tree.insert("", tk.END, iid=item_id, values=(title, "Queued", "Waiting..."))
        
        # Update queue status
        self.update_queue_status()
        
        # Switch to queue tab
        self.notebook.select(self.queue_tab)
        
        return item_id
    
    def start_download(self):
        """Start the download process based on selected method"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a YouTube URL")
            return
        
        # Get video info first
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown')
                duration = self._format_duration(info.get('duration', 0))
                
                # Confirm download
                if not messagebox.askyesno("Confirm Download", 
                                          f"Do you want to download:\n{title}\nDuration: {duration}?"):
                    return
                
                # Check download method
                if self.download_method.get() == "queue":
                    # Add to queue
                    self.add_to_queue(url, title)
                    messagebox.showinfo("Queue", f"Added to download queue:\n{title}")
                else:
                    # Direct download
                    self.download_button.config(state=tk.DISABLED)
                    self.progress_label.config(text="Preparing download...")
                    self.status_label.config(text="")
                    
                    # Start download in a separate thread
                    threading.Thread(target=self.download_audio, args=(url,), daemon=True).start()
                
        except Exception as e:
            # If we can't get info, just confirm with the URL
            if self.download_method.get() == "queue":
                if messagebox.askyesno("Confirm Download", f"Unable to get video info. Add this URL to queue?\n{url}"):
                    self.add_to_queue(url, f"Unknown ({url[-11:] if len(url) > 11 else url})")
            else:
                if messagebox.askyesno("Confirm Download", f"Unable to get video info. Download this URL?\n{url}"):
                    self.download_button.config(state=tk.DISABLED)
                    self.progress_label.config(text="Preparing download...")
                    self.status_label.config(text="")
                    threading.Thread(target=self.download_audio, args=(url,), daemon=True).start()
    
    def download_selected(self):
        """Download the selected search result"""
        selected_item = self.results_tree.focus()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a song to download")
            return
        
        index = int(selected_item)
        if 0 <= index < len(self.search_results):
            video_id = self.search_results[index].get('id', '')
            url = f"https://www.youtube.com/watch?v={video_id}"
            title = self.search_results[index].get('title', 'Unknown')
            
            # Confirm download
            if messagebox.askyesno("Confirm Download", f"Do you want to download:\n{title}?"):
                # Check download method
                if self.download_method.get() == "queue":
                    # Add to queue
                    self.add_to_queue(url, title)
                    messagebox.showinfo("Queue", f"Added to download queue:\n{title}")
                else:
                    # Switch to download tab and start download
                    self.notebook.select(self.download_tab)
                    self.url_entry.delete(0, tk.END)
                    self.url_entry.insert(0, url)
                    self.start_download()

    def play_preview(self):
        """Play a preview of the selected song"""
        selected_item = self.results_tree.focus()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a song to preview")
            return
        
        index = int(selected_item)
        if 0 <= index < len(self.search_results):
            video_id = self.search_results[index].get('id', '')
            title = self.search_results[index].get('title', 'Unknown')
            
            self.search_status_label.config(text=f"Loading preview for: {title}")
            
            # Start preview in a separate thread
            threading.Thread(target=self._load_preview, args=(video_id, title), daemon=True).start()
    
    def _load_preview(self, video_id, title):
        """Load and play a preview of the song"""
        try:
            # Configure yt-dlp options for preview
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
                'outtmpl': os.path.join(self.output_dir, 'preview.%(ext)s'),
                'max_filesize': 3 * 1024 * 1024,  # Limit to 3MB for preview
                'playlistend': 1,
            }
            
            # Download a short preview
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
            
            # Play the preview
            preview_path = os.path.join(self.output_dir, 'preview.mp3')
            if os.path.exists(preview_path):
                self.root.after(0, lambda: self._play_file(preview_path, f"Preview: {title}"))
                self.root.after(0, lambda: self.search_status_label.config(text=f"Playing preview: {title}"))
            else:
                self.root.after(0, lambda: self.search_status_label.config(text="Failed to load preview"))
                
        except Exception as e:
            self.root.after(0, lambda: self.search_status_label.config(text=f"Error: {str(e)}"))
    
    def update_progress_hook(self, d):
        """Update progress bar based on download progress"""
        if d['status'] == 'downloading':
            # Calculate download progress
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            
            if total > 0:
                percent = (downloaded / total) * 100
                self.progress_bar["value"] = percent
                self.progress_label.config(text=f"Downloading: {percent:.1f}%")
                
                # Update speed and ETA if available
                speed = d.get('speed', 0)
                if speed:
                    speed_str = f"{speed/1024/1024:.2f} MB/s"
                    eta = d.get('eta', 0)
                    if eta:
                        self.status_label.config(text=f"Speed: {speed_str} | ETA: {eta} seconds")
                    else:
                        self.status_label.config(text=f"Speed: {speed_str}")
            
            self.root.update_idletasks()
        
        elif d['status'] == 'finished':
            self.progress_label.config(text="Download complete. Converting...")
            self.root.update_idletasks()
    
    def setup_settings_tab(self):
        """Setup the settings tab for authentication options"""
        # Authentication frame
        auth_frame = ttk.LabelFrame(self.settings_tab, text="YouTube Authentication")
        auth_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Authentication method
        ttk.Label(auth_frame, text="Authentication Method:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        
        # No authentication option
        ttk.Radiobutton(auth_frame, text="No Authentication", variable=self.auth_method, 
                       value="none").grid(row=0, column=1, sticky=tk.W, padx=10, pady=10)
        
        # Browser cookies option
        ttk.Radiobutton(auth_frame, text="Browser Cookies", variable=self.auth_method, 
                       value="browser_cookies").grid(row=1, column=1, sticky=tk.W, padx=10, pady=10)
        
        # Browser selection
        ttk.Label(auth_frame, text="Browser:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=10)
        browser_combo = ttk.Combobox(auth_frame, textvariable=self.browser_var, width=15)
        browser_combo['values'] = ("chrome", "firefox", "edge", "safari", "opera", "brave")
        browser_combo.grid(row=2, column=1, sticky=tk.W, padx=10, pady=10)
        browser_combo.current(0)  # Default to Chrome
        
        # Help text
        help_text = """Authentication Help:
        
1. Browser Cookies: Uses cookies from your browser to authenticate with YouTube.
   - Select your browser from the dropdown
   - Make sure you're logged into YouTube in that browser
   - Close the browser before downloading (recommended)

2. If you're still getting 403 errors:
   - Try updating yt-dlp using the button below
   - Try a different browser
   - Make sure you're logged into YouTube"""
        
        help_label = ttk.Label(self.settings_tab, text=help_text, justify=tk.LEFT, wraplength=700)
        help_label.pack(fill=tk.X, padx=10, pady=10)
        
        # Update yt-dlp button
        update_button = ttk.Button(self.settings_tab, text="Update yt-dlp", command=self.update_ytdlp)
        update_button.pack(pady=10)
        
        # Status label
        self.settings_status_label = ttk.Label(self.settings_tab, text="")
        self.settings_status_label.pack(pady=10)
    
    def update_ytdlp(self):
        """Update yt-dlp to the latest version"""
        self.settings_status_label.config(text="Updating yt-dlp...")
        self.root.update_idletasks()
        
        def _update():
            try:
                import subprocess
                result = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"], 
                                       capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.root.after(0, lambda: self.settings_status_label.config(
                        text="yt-dlp updated successfully! Please restart the application."))
                else:
                    self.root.after(0, lambda: self.settings_status_label.config(
                        text=f"Error updating yt-dlp: {result.stderr}"))
            except Exception as e:
                self.root.after(0, lambda: self.settings_status_label.config(
                    text=f"Error updating yt-dlp: {str(e)}"))
        
        threading.Thread(target=_update, daemon=True).start()
    
    def download_audio(self, url):
        """Download audio from YouTube URL"""
        try:
            # Get output directory from entry field (in case it was edited manually)
            self.output_dir = self.dir_entry.get()
            
            # Create output directory if it doesn't exist
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
            
            # Configure yt-dlp options
            audio_format = self.format_var.get()
            audio_quality = self.quality_var.get()
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': audio_format,
                    'preferredquality': audio_quality,
                }],
                'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
                'progress_hooks': [self.update_progress_hook],
                'quiet': True,
                'no_warnings': True
            }
            
            # Add authentication if selected
            if self.auth_method.get() == "browser_cookies":
                browser = self.browser_var.get()
                ydl_opts['cookiesfrombrowser'] = (browser, None, None, None)
                self.status_label.config(text=f"Using cookies from {browser}")
            
            # Download the audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                base_filename = os.path.splitext(filename)[0] + f".{audio_format}"
            
            # Show success message
            self.progress_label.config(text="Download Complete!")
            self.status_label.config(text=f"Saved to: {base_filename}")
            messagebox.showinfo("Success", f"Downloaded: {info.get('title')}")
            
            # Update song list
            self.update_song_list()
            
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            self.progress_label.config(text="Error!")
            self.status_label.config(text=str(e))
            
            # Check for 403 error
            if "403" in error_msg or "forbidden" in error_msg.lower():
                messagebox.showerror("Authentication Error", 
                                   "403 Forbidden Error: YouTube requires authentication.\n\n"
                                   "Please go to the Settings tab and enable browser cookies authentication.")
                # Switch to settings tab
                self.notebook.select(self.settings_tab)
            else:
                messagebox.showerror("Error", str(e))
        
        except Exception as e:
            self.progress_label.config(text="Error!")
            self.status_label.config(text=str(e))
            messagebox.showerror("Error", str(e))
        
        finally:
            # Reset UI
            self.progress_bar["value"] = 0
            self.download_button.config(state=tk.NORMAL)
    
    def start_download(self):
        """Start the download process in a separate thread"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a YouTube URL")
            return
        
        # Confirm download
        try:
            # Get video info first
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown')
                duration = self._format_duration(info.get('duration', 0))
                
                if not messagebox.askyesno("Confirm Download", 
                                          f"Do you want to download:\n{title}\nDuration: {duration}?"):
                    return
        except Exception as e:
            # If we can't get info, just confirm with the URL
            if not messagebox.askyesno("Confirm Download", f"Do you want to download this URL?\n{url}"):
                return
        
        # Disable download button during download
        self.download_button.config(state=tk.DISABLED)
        self.progress_label.config(text="Preparing download...")
        self.status_label.config(text="")
        
        # Start download in a separate thread to keep UI responsive
        threading.Thread(target=self.download_audio, args=(url,), daemon=True).start()
    
    def update_song_list(self):
        """Update the list of downloaded songs"""
        # Clear the treeview
        for item in self.song_tree.get_children():
            self.song_tree.delete(item)
        
        self.downloaded_songs = []
        
        try:
            # Get output directory from entry field
            output_dir = self.dir_entry.get()
            
            if os.path.exists(output_dir):
                # Find all audio files
                audio_extensions = (".mp3", ".m4a")
                for file in os.listdir(output_dir):
                    if file.lower().endswith(audio_extensions) and file != "preview.mp3":
                        file_path = os.path.join(output_dir, file)
                        self.downloaded_songs.append(file_path)
                        title = os.path.splitext(file)[0]
                        self.song_tree.insert("", tk.END, values=(title, file_path))
        except Exception as e:
            messagebox.showerror("Error", f"Error updating song list: {str(e)}")
    
    # These methods have been replaced by the new implementations above
    
    def play_music(self):
        """Play or resume the current song"""
        if self.currently_playing:
            if self.paused:
                pygame.mixer.music.unpause()
                self.paused = False
            else:
                # If not paused and not playing, restart
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.load(self.currently_playing)
                    pygame.mixer.music.play()
        else:
            # If no song is selected, play the first one in the list
            if self.downloaded_songs and len(self.downloaded_songs) > 0:
                song_path = self.downloaded_songs[0]
                song_name = os.path.splitext(os.path.basename(song_path))[0]
                self._play_file(song_path, song_name)
    
    def pause_music(self):
        """Pause the currently playing song"""
        if pygame.mixer.music.get_busy() and not self.paused:
            pygame.mixer.music.pause()
            self.paused = True
    
    def stop_music(self):
        """Stop the currently playing song"""
        pygame.mixer.music.stop()
        self.paused = False
    
    def set_volume(self, value):
        """Set the volume of the music player"""
        volume = float(value)
        pygame.mixer.music.set_volume(volume)

    def search_song(self):
        """Search for songs on YouTube based on the search query"""
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter a search query")
            return
        
        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        self.search_results = []
        self.search_status_label.config(text="Searching...")
        
        # Start search in a separate thread to keep UI responsive
        threading.Thread(target=self._perform_search, args=(query,), daemon=True).start()
    
    def _perform_search(self, query):
        """Perform the actual search using yt-dlp"""
        try:
            # Configure yt-dlp options for search
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'skip_download': True,
                'format': 'bestaudio/best',
            }
            
            # Add authentication if selected
            if self.auth_method.get() == "browser_cookies":
                browser = self.browser_var.get()
                ydl_opts['cookiesfrombrowser'] = (browser, None, None, None)
            
            # Search YouTube
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Use ytsearch to find videos
                search_results = ydl.extract_info(f"ytsearch10:{query}", download=False)
                
                if search_results and 'entries' in search_results:
                    # Process results
                    for i, entry in enumerate(search_results['entries']):
                        if entry:
                            # Store result data
                            self.search_results.append({
                                'id': entry.get('id', ''),
                                'title': entry.get('title', 'Unknown'),
                                'duration': entry.get('duration', 0),
                                'channel': entry.get('channel', 'Unknown'),
                                'url': entry.get('url', '')
                            })
                            
                            # Format duration
                            duration_str = self._format_duration(entry.get('duration', 0))
                            
                            # Add to treeview
                            self.root.after(0, lambda i=i, entry=entry, duration_str=duration_str: 
                                self.results_tree.insert("", tk.END, iid=str(i), values=(
                                    entry.get('title', 'Unknown'),
                                    duration_str,
                                    entry.get('channel', 'Unknown')
                                ))
                            )
                    
                    # Update status
                    self.root.after(0, lambda: self.search_status_label.config(
                        text=f"Found {len(self.search_results)} results for: {query}"))
                else:
                    # No results
                    self.root.after(0, lambda: self.search_status_label.config(
                        text=f"No results found for: {query}"))
            
        except Exception as e:
            # Handle errors
            self.root.after(0, lambda: self.search_status_label.config(
                text=f"Error: {str(e)}"))

    def select_search_result(self, event):
        """Handle double-click on search result"""
        selected_item = self.results_tree.focus()
        if selected_item:
            # Switch to download tab
            self.notebook.select(self.download_tab)
            
            # Get the selected item's data
            index = int(selected_item)
            if 0 <= index < len(self.search_results):
                video_id = self.search_results[index].get('id', '')
                url = f"https://www.youtube.com/watch?v={video_id}"
                
                # Set the URL in the download tab
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, url)
    
    def paste_url(self):
        """Paste clipboard content into URL entry"""
        try:
            clipboard_content = self.root.clipboard_get()
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, clipboard_content)
        except Exception as e:
            messagebox.showerror("Paste Error", f"Could not paste from clipboard: {str(e)}")
            
    def browse_directory(self):
        """Open directory browser dialog and set the selected directory"""
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
            
    def setup_player_tab(self):
        """Setup the player tab with controls and song list"""
        # Song list frame
        list_frame = ttk.LabelFrame(self.player_tab, text="Downloaded Songs")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create treeview for song list
        self.song_tree = ttk.Treeview(list_frame, columns=("title", "path"), show="headings")
        self.song_tree.heading("title", text="Title")
        self.song_tree.heading("path", text="Path")
        
        self.song_tree.column("title", width=300)
        self.song_tree.column("path", width=400)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.song_tree.yview)
        self.song_tree.configure(yscrollcommand=scrollbar.set)
        
        self.song_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to play
        self.song_tree.bind("<Double-1>", self.play_selected_song)
        
        # Player controls frame
        controls_frame = ttk.Frame(self.player_tab)
        controls_frame.pack(fill=tk.X, pady=10)
        
        # Play button
        self.play_button = ttk.Button(controls_frame, text="Play", command=self.play_music)
        self.play_button.pack(side=tk.LEFT, padx=5)
        
        # Pause button
        self.pause_button = ttk.Button(controls_frame, text="Pause/Resume", command=self.pause_resume_music)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        # Stop button
        self.stop_button = ttk.Button(controls_frame, text="Stop", command=self.stop_music)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Volume control
        volume_frame = ttk.Frame(controls_frame)
        volume_frame.pack(side=tk.RIGHT, padx=10)
        
        volume_label = ttk.Label(volume_frame, text="Volume:")
        volume_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.volume_scale = ttk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=100, 
                                      command=self.set_volume)
        self.volume_scale.set(70)  # Default volume
        self.volume_scale.pack(side=tk.LEFT)
        
        # Now playing label
        self.now_playing_label = ttk.Label(self.player_tab, text="Not playing", font=("Helvetica", 10))
        self.now_playing_label.pack(pady=(0, 10))
    
    def play_selected_song(self, event):
        """Play the selected song from the song list"""
        selected_item = self.song_tree.focus()
        if selected_item:
            item_data = self.song_tree.item(selected_item)
            file_path = item_data['values'][1]
            self._play_file(file_path)
    
    def play_music(self):
        """Play the currently selected song"""
        selected_item = self.song_tree.focus()
        if selected_item:
            self.play_selected_song(None)
    
    def pause_resume_music(self):
        """Pause or resume the currently playing music"""
        if self.currently_playing:
            if self.paused:
                pygame.mixer.music.unpause()
                self.paused = False
            else:
                pygame.mixer.music.pause()
                self.paused = True
    
    def stop_music(self):
        """Stop the currently playing music"""
        if self.currently_playing:
            pygame.mixer.music.stop()
            self.currently_playing = None
            self.paused = False
            self.now_playing_label.config(text="Not playing")
    
    def set_volume(self, value):
        """Set the volume of the music player"""
        volume = float(value) / 100
        pygame.mixer.music.set_volume(volume)
    
    def _play_file(self, file_path):
        """Play an audio file"""
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            self.currently_playing = file_path
            self.paused = False
            
            # Update now playing label
            filename = os.path.basename(file_path)
            self.now_playing_label.config(text=f"Now playing: {filename}")
        except Exception as e:
            messagebox.showerror("Playback Error", f"Could not play file: {str(e)}")
    
    def _format_duration(self, seconds):
        """Format duration in seconds to MM:SS format"""
        if not seconds:
            return "Unknown"
        
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
            
    def clear_search(self):
        """Clear the search results and search entry"""
        # Clear the search entry
        self.search_entry.delete(0, tk.END)
        
        # Clear the search results treeview
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
            
        # Clear the search results list
        self.search_results = []
        
        # Update status label
        self.search_status_label.config(text="Search cleared")
        
    def add_selected_to_queue(self):
        """Add the selected search result to the download queue"""
        selected_item = self.results_tree.focus()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a song to add to queue")
            return
        
        index = int(selected_item)
        if 0 <= index < len(self.search_results):
            video_id = self.search_results[index].get('id', '')
            url = f"https://www.youtube.com/watch?v={video_id}"
            title = self.search_results[index].get('title', 'Unknown')
            
            # Add to queue
            self.add_to_queue(url, title)
            
            # Show confirmation and switch to queue tab
            self.search_status_label.config(text=f"Added to queue: {title}")
            self.notebook.select(self.queue_tab)
            
    def setup_info_tab(self):
        """Setup the info tab with author details and GitHub link"""
        # Main frame
        info_frame = ttk.Frame(self.info_tab, padding="20 20 20 20")
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        # App title and version
        title_label = ttk.Label(info_frame, text="YouTube Music Downloader", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 5))
        
        version_label = ttk.Label(info_frame, text="Version 1.0.0", font=("Helvetica", 10))
        version_label.pack(pady=(0, 20))
        
        # Author information
        author_frame = ttk.LabelFrame(info_frame, text="Author Information")
        author_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Replace with your actual name
        author_label = ttk.Label(author_frame, text="Developer: Hasintha-Nirmal", font=("Helvetica", 11))
        author_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Replace with your actual GitHub username
        github_text = "GitHub: https://github.com/Hasintha-Nirmal/youtube-music-downloader"
        github_label = ttk.Label(author_frame, text=github_text, font=("Helvetica", 11), foreground="blue", cursor="hand2")
        github_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Make GitHub link clickable
        github_label.bind("<Button-1>", lambda e: self.open_github_link())
        
        # Description
        desc_frame = ttk.LabelFrame(info_frame, text="About")
        desc_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        description = """YouTube Music Downloader is a desktop application that allows you to search, download, and play music from YouTube. 

Features:
• Search for songs on YouTube
• Download audio in MP3 or M4A format
• Queue multiple downloads
• Built-in audio player
• Authentication support for age-restricted content

This application is built with Python and Tkinter, using yt-dlp for downloading content.

License: MIT
© 2023 Hasintha-Nirmal. All rights reserved."""

        
        desc_label = ttk.Label(desc_frame, text=description, justify=tk.LEFT, wraplength=700)
        desc_label.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    def open_github_link(self):
        """Open the GitHub repository link in the default web browser"""
        # Replace with your actual GitHub repository URL
        github_url = "https://github.com/Hasintha-Nirmal/youtube-music-downloader"
        webbrowser.open(github_url)

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeMusicDownloader(root)
    root.mainloop()