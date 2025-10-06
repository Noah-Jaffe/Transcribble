import os
from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ffmpeg

def get_audio_length(filepath):
    """Return length of audio in seconds"""
    try:
        probe = ffmpeg.probe(filepath)
        duration = float(probe['format']['duration'])
        return int(duration)
    except:
        pass
    return None

def split_audio(filepath, num_parts, overlap=2):
    """Split audio file into parts with given overlap."""
    length = get_audio_length(filepath)
    if not length or num_parts < 2 or num_parts > length:
        return False

    part_duration = length / num_parts
    fp = Path(filepath)
    basename, ext = os.path.splitext(os.path.basename(filepath))
    output_dir = os.path.dirname(filepath)

    for i in range(num_parts):
        start_time = i * part_duration
        if i > 0:
            start_time = max(0, start_time - overlap)
        duration = part_duration
        if i < num_parts - 1:
            duration += overlap
        if start_time + duration > length:
            duration = length - start_time

        output_file = os.path.join(output_dir, f"{basename}.{i+1}{ext}")
        subprocess.run([
            "ffmpeg", "-y", "-i", filepath,
            "-ss", str(start_time), "-t", str(duration),
            "-c", "copy", output_file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True

def process_files():
    """Process all files with given table inputs."""
    for row in rows:
        filepath, parts_entry, overlap_entry = row
        try:
            num_parts = int(parts_entry.get())
            overlap = int(overlap_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Input", f"Invalid numbers for {os.path.basename(filepath)}")
            return

        if not split_audio(filepath, num_parts, overlap):
            messagebox.showerror("Error", f"Failed to split {os.path.basename(filepath)}")
            return

    messagebox.showinfo("Done", "All files split successfully.")

def select_files():
    """Open file dialog and build table."""
    global rows
    rows.clear()

    files = filedialog.askopenfilenames(
        title="Select Audio Files",
        filetypes=[("Audio Files", "*.mp3 *.wav *.m4a *.flac *.aac *.ogg")]
    )
    if not files:
        return

    for widget in table_frame.winfo_children():
        widget.destroy()

    ttk.Label(table_frame, text="File Name", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5)
    ttk.Label(table_frame, text="Length (s)", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=1, padx=5)
    ttk.Label(table_frame, text="Parts", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=2, padx=5)
    ttk.Label(table_frame, text="Overlap (s)", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=3, padx=5)

    for i, filepath in enumerate(files, start=1):
        length = get_audio_length(filepath)
        if not length:
            length = "?"
        ttk.Label(table_frame, text=os.path.basename(filepath)).grid(row=i, column=0, sticky="w", padx=5)
        ttk.Label(table_frame, text=str(length)).grid(row=i, column=1, padx=5)

        parts_entry = ttk.Entry(table_frame, width=5)
        parts_entry.insert(0, "2")
        parts_entry.grid(row=i, column=2, padx=5)

        overlap_entry = ttk.Entry(table_frame, width=5)
        overlap_entry.insert(0, "2")
        overlap_entry.grid(row=i, column=3, padx=5)

        rows.append((filepath, parts_entry, overlap_entry))

# --- Main GUI ---
root = tk.Tk()
root.title("Audio Splitter with Overlap")

rows = []

ttk.Button(root, text="Select Files", command=select_files).pack(pady=5)

canvas = tk.Canvas(root)
scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollable_frame = ttk.Frame(canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

table_frame = ttk.Frame(scrollable_frame)
table_frame.pack(fill="x", expand=True)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

ttk.Button(root, text="Split Files", command=process_files).pack(pady=5)

root.mainloop()
