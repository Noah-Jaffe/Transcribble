import datetime
import json
import os
import subprocess
import time
import soundfile
from tkinter import messagebox, filedialog
import traceback
import tkinter as tk
from tkinter import ttk
from typing import List
import re

from src.DataMapping import DataMapping
from src.Config import *
from src.Tooltip import ToolTip
from src.Mascot import Mascot
from src.Utils import *


class MainGUI(tk.Tk):
    """Runtime config. Populated by cache"""
    data_config: DataMapping = DataMapping()
    # auto_retry_failures: tk.BooleanVar = None
    debug_mode: tk.BooleanVar = None
    open_when_done: tk.BooleanVar = None
    """Dynamic list of file entries to be updated during runtime. Populated by cache"""
    data_file_entries: List[tk.Frame] = []
    """List of models"""
    data_model_list: List[str] = []

    """Main header section"""
    header_frame: tk.Frame = None
    """Button to add new files"""
    header_button_add_files: tk.Button = None
    """Label for button to add new files"""
    header_label_file_management: tk.Label = None
    
    """Main center section"""
    center_frame: tk.Frame = None
    """Canvas for the center frame"""
    center_canvas: tk.Canvas = None
    """Center frame for the scrollable/dynamic file list"""
    center_canvas_window: tk.Frame = None
    """Scrollbar for the file entries"""
    center_scrollbar_file_entries: tk.Scrollbar = None
    """Frame for the file entries inside the scrollable canvas window. Populated by cache"""
    center_frame_file_entries: tk.Frame = None
    
    """Main footer section"""
    footer_frame: tk.Frame = None
    """Combo box for model selection. Populated by cache"""
    footer_combobox_model_selector: ttk.Combobox = None
    """Button to find additional models"""
    footer_button_find_additional_models: tk.Button = None
    """Button to start transcribe"""
    footer_button_start_transcribe: tk.Button = None
    """Checkbox to retry failures. Populated by cache"""
    footer_checkbox_auto_retry_failures: ttk.Checkbutton = None
    """Open transcribed files as they complete. Populated by cache"""
    footer_checkbox_open_when_done: ttk.Checkbutton = None
    """Checkbox for debug mode. Populated by cache"""
    footer_checkbox_debug_mode: ttk.Checkbutton = None
    
    def __init__(self):
        super().__init__()
        tk.Tk.report_callback_exception = self.show_error
        print("Finding models...")
        try:
            self.data_model_list = get_model_list()	# Utils.get_model_list()
        except:
            self.data_model_list = []
        print("Models found.")
        
        self.title("Transcribble")
        self.minsize(600, 300)
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.create_header()
        self.create_center()
        self.create_footer()
        
        self.load_data()
        
        self.bind("<Configure>", self.on_window_resize)
        
    
    def create_header(self):
        """Creates the header section contents and configures their layout.
            - title
            - select files button
            - @TODO: ADD FUTURE FEATURES HERE
        """
        # header root node
        self.header_frame = tk.Frame(self, bg=COLOR_THEME.MAIN_WINDOW)
        self.header_frame.grid(row=0, column=0, sticky="new")
        self.header_frame.grid_propagate(False)
        
        # file management - label
        self.header_label_file_management = tk.Label(self.header_frame, text="Files for transcription:", font=LABEL_FONT, bg=COLOR_THEME.MAIN_WINDOW, justify="right", anchor="ne")
        self.header_label_file_management.pack(side="left", padx=5, pady=5)
        ToolTip(self.header_label_file_management, text="Select the files to be transcribed!\nNote that we will handle file conversions!")
        
        # file management - add files
        self.header_button_add_files = tk.Button(self.header_frame, text="Select Files", command=self.select_new_files, background=COLOR_THEME.BUTTON)
        self.header_button_add_files.pack(side="right", padx=5, pady=5)
        ToolTip(self.header_button_add_files, text = "Select your file(s) to be transcribed. (Opens file selection window).")
        
        # debug - instant mascot
        # instantMascot = tk.Button(self.header_frame, text="mascot", command=lambda: Mascot(self, 'hi'), background=COLOR_THEME.BUTTON)
        # instantMascot.pack(side="left")
        
    def create_center(self):
        """Creates the center section contents and configures their layout.
            - file selection and management
            - @TODO: ADD FUTURE FEATURES HERE
        """
        # center node
        self.center_frame = tk.Frame(self, bg=COLOR_THEME.MAIN_WINDOW)
        self.center_frame.grid(row=1, column=0, sticky="nsew")
        
        # Scrollable canvas for dynamic list of files
        self.center_canvas = tk.Canvas(self.center_frame, borderwidth=0, background=COLOR_THEME.MAIN_WINDOW)
        self.center_frame_file_entries = tk.Frame(self.center_canvas, background=COLOR_THEME.MAIN_WINDOW)
        self.center_scrollbar_file_entries = tk.Scrollbar(self.center_frame, orient="vertical", command=self.center_canvas.yview, background=COLOR_THEME.BUTTON)
        self.center_canvas.configure(yscrollcommand=self.center_scrollbar_file_entries.set)
        self.center_scrollbar_file_entries.pack(side="right", fill="y")
        self.center_canvas.pack(side="left", fill="both", expand=True)
        
        self.center_canvas_window = self.center_canvas.create_window((0, 0), window=self.center_frame_file_entries, anchor="nw", tags="inner")
        
        self.center_canvas.bind("<Configure>", self.on_file_entry_resize)
        self.center_frame_file_entries.bind("<Configure>", self.on_file_entry_configure)
        self.center_frame_file_entries.grid_columnconfigure(0, weight=1)
        self.center_canvas.bind_all("<MouseWheel>", self.on_file_entry_mousewheel)

        # @TODO add cached files at some point? where? here or when we load cache?
        self.data_file_entries = self.data_file_entries or []
    
    def create_footer(self):
        """Creates the footer section contents and configures their layout.
            - model selection
            - start transcribe button
            - @TODO: ADD FUTURE FEATURES HERE
        """
        # footer frame root node
        self.footer_frame = tk.Frame(self, bg=COLOR_THEME.MAIN_WINDOW)
        self.footer_frame.grid(row=2, column=0, sticky="nsew")
        self.footer_frame.grid_propagate(False)
        
        # configure the height/widths of each module by weights, 1 = max fill, 0 = min fill.
        self.footer_frame.grid_rowconfigure(0, weight=1, minsize=30)    # model selection, max height allowed
        self.footer_frame.grid_rowconfigure(1, weight=1, minsize=30)    # options/config
        self.footer_frame.grid_rowconfigure(2, weight=1, minsize=30)    # start button, max height allowed
        self.footer_frame.grid_columnconfigure(0, weight=1) # max width allowed
        
        # model selection row
        model_selection_row = tk.Frame(self.footer_frame, background=COLOR_THEME.MAIN_WINDOW)
        model_selection_row.grid(row=0, column=0, sticky="ew")
        model_selection_row.grid_columnconfigure(0, weight=2)   # model select label
        model_selection_row.grid_columnconfigure(1, weight=6)   # model select dropdown
        model_selection_row.grid_columnconfigure(2, weight=2)   # model select search
        
        # model selection 
        self.footer_button_find_additional_models = tk.Button(model_selection_row, text="Find a different model", command=open_hf_search, font=BUTTON_FONT, bg=COLOR_THEME.BUTTON)	# Utils.open_hf_search, font=BUTTON_FONT, bg=COLOR_THEME.BUTTON)
        self.footer_button_find_additional_models.pack(side="right", padx=(5, 10))
        
        # @TODO figure out how to dynamically set the min width of the dropdown so the text does not get cut off
        self.footer_label_select_model = tk.Label(model_selection_row, text="Select AI Model:", font=LABEL_FONT, bg=COLOR_THEME.MAIN_WINDOW)
        self.footer_label_select_model.pack(side="left", padx=(10, 5))
        # @TODO populate footer_stringvar_model_selection_value from cache.modelCache
        self.footer_stringvar_model_selection_value = tk.StringVar()
        self.footer_combobox_model_selector = ttk.Combobox(model_selection_row, values=self.data_model_list, textvariable=self.footer_stringvar_model_selection_value)
        self.footer_combobox_model_selector.pack(fill="both", padx=(10, 10), pady=5)
        model_help_text = "\n".join([
            'Models can be set from any valid huggingface model.', 
            'Reccomended to use one of the following:', 
            'From batchalign:', 
            "    - 'talkbank/CHATWhisper-en'", 
            '', 
            'From OpenAI:', 
            '    * Choose the size that runs well on your computer.', 
            "    'openai/whisper-<TYPE>'", 
            '    Where you replace <TYPE> with the selected model. ', 
            "    For example, if you want the English only tiny type, then the value should be 'openai/whisper-tiny.en'.", 
            '    ╔════════╦══════════════╦══════════╦══════════╗', 
            '    ║        ║ English-only ║ Required ║ Relative ║', 
            '    ║  TYPE  ║     TYPE     ║   VRAM   ║  speed   ║', 
            '    ╠════════╬══════════════╬══════════╬══════════╣', 
            '    ║ tiny   ║   tiny.en    ║   ~1 GB  ║   ~10x   ║', 
            '    ║ base   ║   base.en    ║   ~1 GB  ║    ~7x   ║', 
            '    ║ small  ║   small.en   ║   ~2 GB  ║    ~4x   ║', 
            '    ║ medium ║   medium.en  ║   ~5 GB  ║    ~2x   ║', 
            '    ║ large  ║   N/A        ║  ~10 GB  ║     1x   ║', 
            '    ║ turbo  ║   N/A        ║   ~6 GB  ║    ~8x   ║', 
            '    ╚════════╩══════════════╩══════════╩══════════╝', 
            '', 
            'From other providers:', 
            '    Use the search button and find a model that you wish to use from huggingface.', 
            "    Enter the model ID to use as '<AUTHOR>/<NAME>' (the same pattern as the talkbank and openai models).", 
            '    Note that not all models will be valid, and you will only find out when it crashes when it attempts to transcribe.', 
            '    Use a model that is based off of the Openai whisper base!', 
            '', 
            'See the README.md file for more info!'
        ])
        ToolTip(self.footer_combobox_model_selector, text=model_help_text)
        ToolTip(self.footer_label_select_model, text=model_help_text)
        
        # Options/config row
        options_config_row = tk.Frame(self.footer_frame, background=COLOR_THEME.MAIN_WINDOW)
        options_config_row.grid(row=1, column=0, sticky="NEW", padx=10)
        
        # Auto-retry on failures
        # self.auto_retry_failures = tk.BooleanVar(value=False)
        # self.footer_checkbox_auto_retry_failures = ttk.Checkbutton(options_config_row, text="Auto-retry failures", variable=self.auto_retry_failures)
        # self.footer_checkbox_auto_retry_failures.pack(side="left", padx=5)
        # ToolTip(self.footer_checkbox_auto_retry_failures, text="Some errors caused by the AI have some known potential work-arounds. Selecting this will enable us to retry a transcription attempt if we know of a potential work-around for the issue encountered.")
        
        # Print debug/status lines (ENABLED BY DEFAULT)
        self.debug_mode = tk.BooleanVar(value=True)
        self.footer_checkbox_debug_mode = ttk.Checkbutton(options_config_row, text="Debug mode", variable=self.debug_mode)
        self.footer_checkbox_debug_mode.pack(side="left", padx=5)
        ToolTip(self.footer_checkbox_debug_mode, text="Sometimes knowing what went right or wrong can help with troubleshooting or validating the transcription. Selecting this will add '@DEBUG' lines to the bottom of the output transcript. Information in the @DEBUG lines may include:\n" + "\n".join([f"\t- {x}" for x in ["Help messages", "Status of each step of the pipeline", "Error messages", "Crash logs", "etc."]]))
        
        # Open when done as they complete (ENABLED BY DEFAULT)
        self.open_when_done = tk.BooleanVar(value=True)
        self.footer_checkbox_open_when_done = ttk.Checkbutton(options_config_row, text="Open transcripts", variable=self.open_when_done)
        self.footer_checkbox_open_when_done.pack(side="left", padx=5)
        ToolTip(self.footer_checkbox_open_when_done, text="Checking this will attempt to automatically open the transcribed files as they complete.")
        
        # Activity buttons row
        activity_button_row = tk.Frame(self.footer_frame, background=COLOR_THEME.MAIN_WINDOW)
        activity_button_row.grid(row=2, column=0, sticky="EWS", padx=10)
        
        
        # Start transcribe button
        self.footer_button_start_transcribe = tk.Button(activity_button_row, text="About", command=self.show_about, font=(BUTTON_FONT[0], int(BUTTON_FONT[1]*0.8), "italic"), bg=COLOR_THEME.BUTTON)
        self.footer_button_start_transcribe.pack(side="left", anchor="n")

        # Start transcribe button
        self.footer_button_start_transcribe = tk.Button(activity_button_row, text="Start Transcribe", command=self.start_transcribe, font=BUTTON_FONT, bg=COLOR_THEME.BUTTON)
        self.footer_button_start_transcribe.pack(side="right", anchor="n")
        ToolTip(self.footer_button_start_transcribe, text="Click here to start transcribing the files in the list!\nNote: If the transcription seems off, try running it again! Its possible the AI gets different results each time.")
    
    def serialize_file_entry(self, row):
        return {
            "filename": row.data.filepath.get(),
            "numSpeakers": row.data.numSpeakers.get(),
            "language": row.data.language.get()
        }
    
    def add_file_entry(self, filepath, num_speakers=0, language='', output_file=''):
        """Adds a file entry to the UI and the self.data_file_entries
        
        Args:
            filepath (str): filepath of file to be transcribed
        """
        row = tk.Frame(self.center_frame_file_entries, background=COLOR_THEME.MAIN_WINDOW)
        
        row.data = DataMapping()
        
        row.pack(fill="x", expand=True, padx=5, pady=3)
        
        # configure the column widths
        row.grid_columnconfigure(0, weight=1)   # file label
        row.grid_columnconfigure(1, weight=0)   # num speakers
        row.grid_columnconfigure(2, weight=0)   # language
        row.grid_columnconfigure(3, weight=0)   # delete button
        
        row.data.filepath = tk.StringVar(value=filepath)
        fp = Path(row.data.filepath.get())
        directory = fp.parent.as_posix()
        filename = fp.name
        # @TODO redo the file_label so that it is better
        file_label = tk.Label(row, text=f"{directory}\n{filename}", justify="right", anchor="e", font=MONO_FONT, background=COLOR_THEME.MAIN_WINDOW)
        file_label.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        if num_speakers:
            try:
                num_speakers = abs(int(num_speakers))
            except:
                num_speakers = 1
        row.data.numSpeakers = tk.IntVar(value=num_speakers)
        num_speakers_spinbox = tk.Spinbox(row, from_=1, to=99, width=6, textvariable=row.data.numSpeakers, background=COLOR_THEME.BUTTON)
        num_speakers_spinbox.grid(row=0, column=1, padx=4)
        ToolTip(num_speakers_spinbox, "Set the number of speakers to diarize for.\n1 will not run the diarization pipeline, but will transcribe all the same.")
        
        langs = get_available_langs()	# Utils.get_available_langs()
        if language:
            language = validate_language(language)	# Utils.validate_language(language)
        row.data.language = tk.StringVar(value=language or langs[0])
        language_combobox = ttk.Combobox(row, values=langs, textvariable=row.data.language)
        language_combobox.grid(row=0, column=2, padx=2)
        ToolTip(language_combobox, "Full language name, or 3 letter combo accepted.\nNote: this step might not be required, and is only required for a select few languages!")

        delete_text = "\U0001F5D1"
        delete_button = tk.Button(row, text=delete_text, width=6, command=lambda r=row: self.remove_file_entry(r), background=COLOR_THEME.BUTTON)
        delete_button.grid(row=0, column=3, padx=2)
        ToolTip(delete_button, "Remove this file from the list.")

        # # @TODO: open output file button?
        # open_output_file = tk.Button(row, text="view", width=6, command=lambda r=row: self.remove_file_entry(r), background=COLOR_THEME.BUTTON)
        # if output_file and Path(output_file).is_file():
        #     open_output_file.configure(state='normal')
        # else:
        #     open_output_file.configure(state='disabled')
        # ToolTip(open_output_file, "Open the transcribed file, if available!")
        
        self.data_file_entries.append(row)
        return row
    
    def remove_file_entry(self, row):
        """Removes a file entry from the UI and the self.data_file_entries
        
        Args:
            row (tk.Frame): row to be removed
        """
        self.data_file_entries.remove(row)
        row.destroy()
    
    def select_new_files(self):
        """Selects new files to be added to the file managament list."""
        supported_file_types = get_ffmpeg_supported_formats()	# Utils.get_ffmpeg_supported_formats()
        any_filetype = get_any_file_type()	# Utils.get_any_file_type()
        file_paths = filedialog.askopenfilenames(filetypes=[("Supported Media", " ".join([f"*.{x}" for x in supported_file_types])), ('All Files', " ".join(any_filetype))])
        for filepath in file_paths:
            self.add_file_entry(filepath=filepath)
        self.save_data()
    
    def on_window_resize(self, event):
        win_h = self.winfo_height()
        header_h = min(max(40, int(0.1 * win_h)), 100)
        center_h = min(max(200, int(0.7 * win_h)), int(0.7 * win_h))
        footer_h = max(min(max(80, int(0.2 * win_h)), int(0.2 * win_h)), sum(self.footer_frame.grid_rowconfigure(i)['minsize'] for i in range(self.footer_frame.grid_size()[1])))

        
        self.header_frame.config(height=header_h)
        self.footer_frame.config(height=footer_h)
    
    def on_file_entry_configure(self, event):
        self.center_canvas.configure(scrollregion=self.center_canvas.bbox("all"))
    
    def on_file_entry_resize(self, event):
        self.center_canvas.itemconfig("inner", width=event.width)
    
    def on_file_entry_mousewheel(self, event):
        """Enable scroll wheel where it should be enabled"""
        # Exception: When the mouse is over an open combobox popdown
        combobox_popdown = isinstance(event.widget, str) and re.match(r'.*?combobox.popdown.*?',event.widget,re.IGNORECASE)
        if combobox_popdown:
            return
        self.center_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def show_error(self, *args):
        """Display the error to the user as a popup window"""
        err = traceback.format_exception(*args)
        print("\n".join(err), flush=True)
        messagebox.showerror("Error!", '\n'.join([str(a) for a in args[1].args]) + "\n\n\n\nPlease see the console for the full error message!")
    
    def load_data(self):
        """Loads and imports data from the config cache file to save time."""
        cache = None
        if Path(CACHE_FILENAME).is_file():
            with open(CACHE_FILENAME, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        else:
            with open(CACHE_DEFAULT, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        if not cache:
            raise Exception(f"No cache file to load!\nWhere did the defualt cache file go?\nExpected to be located at '{CACHE_DEFAULT}'")
        for entry in cache.get('fileCache', []):
            if Path(entry.get('filename','.')).is_file():
                self.add_file_entry(entry.get('filename'), entry.get('numSpeakers'), entry.get('language'))
        # self.auto_retry_failures.set(value = True if cache.get('autoRetryFailuresMode') else False)
        self.debug_mode.set(value = True if cache.get('debugMode') else False)
        self.open_when_done.set(value = True if cache.get('openWhenDone') else False)
        if cache.get('selectedModel'):
            self.footer_stringvar_model_selection_value.set(str(cache.get('selectedModel')))
        if cache.get('modelCache') and type(cache.get('modelCache')) == list and len(cache.get('modelCache')) > 0:
            models = list(self.footer_combobox_model_selector['values'])
            for model in cache.get('modelCache', []):
                if model not in models:
                    models.append(model)
            # remove dupes
            self.data_model_list = models
            self.footer_combobox_model_selector['values'] = [n for n in self.data_model_list if is_valid_model_id(n)]	# Utils.is_valid_model_id(n)]
        reccomended = [cache.get('selectedModel','openai/whisper-small.en'),'openai/whisper-small.en', 'openai/whisper-medium.en', 'openai/whisper-small', 'openai/whisper-medium.en', self.data_model_list[0] if len(self.data_model_list) else None]
        for r in reccomended:
            try:
                idx = self.data_model_list.index(r)
                self.dropdown_model_selector.current(idx)
                break
            except:
                pass
        
    def save_data(self):
        """Exports current state to the config cache file."""
        jsonified = {
            "selectedModel": self.footer_stringvar_model_selection_value.get(),
            "modelCache": self.data_model_list or [],
            "fileCache": [self.serialize_file_entry(row) for row in self.data_file_entries] or [],
            "debugMode": self.debug_mode.get() or False,
            # "autoRetryFailuresMode": self.auto_retry_failures.get() or False,
            "openWhenDone": self.open_when_done.get() or False
            }
        if not CACHE_FILENAME.exists():
            CACHE_FILENAME.parent.mkdir(exist_ok=True, parents=True)
        with open(CACHE_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(jsonified, indent=2, fp=f)
    
    def start_transcribe(self):
        """Starts the transcribe process in the background
        
        Returns: 
            : @todo: pipe?
        """
        pass
        self.save_data()
        selected_model = self.footer_combobox_model_selector.get()
        if not is_valid_model_id(selected_model):	# Utils.is_valid_model_id(selected_model):
            if not spawn_popup_activity("Error!", f"An issue occured when we attempted to get the\n\n{self.dropdown_model_selector.get()}\n\nmodel. Please verify your huggingface token allows for read permissions of the given model.\n\nYes to continue with default model, no to abort!"):	# Utils.spawn_popup_activity("Error!", f"An issue occured when we attempted to get the\n\n{self.dropdown_model_selector.get()}\n\nmodel. Please verify your huggingface token allows for read permissions of the given model.\n\nYes to continue with default model, no to abort!"):
                return
        
        selected_model = self.footer_combobox_model_selector.get()
        if len(self.data_file_entries) == 0:
            raise Exception("Please select a file to transcribe first!")
        
        mascot = Mascot(self, "IM TRANSCRIIIIBINNNG!!\nTRANSCRIPTION STARTED, Reccomended that you close all background apps that might hog the system resources!")
        for item in self.data_file_entries:
            valid = validate_language(item.data.language.get())	# Utils.validate_language(item.data.language.get())
            if valid is None:
                spawn_popup_activity('WARNING!','Transcript process DID NOT START.\nPlease fix the errors and try again.')	# Utils.spawn_popup_activity('WARNING!','Transcript process DID NOT START.\nPlease fix the errors and try again.')
                return
        parsetime = 0
        twords = 0
        runtime = datetime.timedelta(0)
        for item in self.data_file_entries:
            # needs conversion?
            if not (item.data.filepath.get().split('.')[-1] in get_audio_file_types()):	# Utils.get_audio_file_types()):
                # looks like it probably needs conversion
                ntype = ".mp3"
                print(f"Converting {item.data.filepath.get()} to mp3 type so that it can be transcribed!")
                item.data.filepath.set(convert_file_to_type(item.data.filepath.get(), ntype))	# Utils.convert_file_to_type(item.data.filepath.get(), ntype)
                print(f"Convertion completed! Audio file can be found {item.data.filepath.get()}")
            
            pstart = datetime.datetime.now()
            d = soundfile.info(item.data.filepath.get()).duration
            print(f"Starting timer for ({d}) '{item.data.filepath.get()}'")
            proc = subprocess.Popen(
                args=[
                    sys.executable,
                    TRANSCRIBE_SUBPROC_FILENAME,
                    json.dumps({
                        'input_file': item.data.filepath.get(), 
                        'num_speakers': item.data.numSpeakers.get(), 
                        'lang': item.data.language.get(), 
                        'model_name':selected_model,
                        'open_after': self.open_when_done.get(),
                        'debug': self.debug_mode.get(),
                        # 'auto_retry': self.auto_retry_failures.get()
                        },
                        skipkeys=True, 
                        separators=(',', ':'))
                    ],
                    cwd=os.getcwd(),
                    start_new_session=True
                )
            self.title("Transcriber - PLEASE DONT KILL ME - I AM WORKING! I PROMISE!")
            while proc.poll() == None:
                try:
                    self.update_idletasks()
                    time.sleep(0.1)
                    #proc.wait(timeout=1)
                except:
                    pass
            ptime = datetime.datetime.now() - pstart
            runtime += ptime
            parsetime += d
            estwordcount = f"{item.data.filepath.get()}.cha"
            est_word_count = 0
            if os.path.isfile(estwordcount):
                with open(estwordcount, 'r', encoding='utf-8') as f:
                    est_word_count = sum([len([w for w in re.sub(r"^\*\w+:\s*(.*?)\s*\.\s*$", "\\1", l, count=0, flags=re.MULTILINE | re.IGNORECASE).replace(r'\s*[/]\s*',' ').split()]) for l in f.readlines() if re.match(r'^\*\w+:\s*(.*?)\s*\.\s*(?:\u0015.*?\u0015)?\s*$', l, re.MULTILINE|re.IGNORECASE)])
                    twords += est_word_count
            print(f"Took {ptime} to transcribe ~{est_word_count} words from ({soundfile.info(item.data.filepath.get()).duration}) '{item.data.filepath.get()}' using {selected_model}")
        try:
            pass
            mascot.destroy()
        except:
            pass
        self.title("Transcriber")
        # spawn_popup_activity("Transcriber", "Completed transcribing the files!")
        print("Completed transcribing the latest batch!")
        print(f"Took {runtime} to transcribe ~{twords} words from ({parsetime}) across {len(self.data_file_entries)} files!")
    
    def show_about(self):
        messagebox.showinfo('About Transcribble', 'https://github.com/Noah-Jaffe/Transcribble\n\nJaffe, N., & Lurie, S. (2025). *Jaffe-Lurie Transcribble* [Computer software]. GitHub. https://github.com/Noah-Jaffe/Transcribble\n\nPlease see the README.md file for more info!')
    
if __name__ == "__main__":
    from Utils import setup_local_user_cfgs
    setup_local_user_cfgs()
    app = MainGUI()
    app.mainloop()
