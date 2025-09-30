import shutil
import sys
from functools import lru_cache
import subprocess
import json
from pathlib import Path
from typing import List
import soundfile
import pycountry
import requests
import os
from tkinter import messagebox
from types import FunctionType
import ffmpeg
from src.Config import *
from huggingface_hub.hf_api import repo_exists as is_valid_model_id

def normalize_path(*path):
    """Gets a normalized path

    Args:
        path (str[]|Path): Path to join/normalize

    Returns:
        Path: The normalized path
    """
    if len(path) > 1:
        path = Path(*path)
    else:
        path = path[0] # allow out of bounds exception
    if type(path) == str:
        path = Path(path)
    if not isinstance(path, Path):
        raise ValueError(f"Path argument must be a str or Path")
    return path.expanduser().resolve()

def spawn_popup_activity(title, message, yes=None, no=None):
    result = messagebox.askyesno(title=title, message=message)
    if result and yes and type(yes) == FunctionType:
        return yes()
    elif not result and no and type(no) == FunctionType:
        return no()
    elif result and (yes is not None):
        return yes
    elif result and (no is not None):
        return no
    return result

def get_hf_search_query(**kwargs):
    """Get hf search query
    Expects kwargs to pass to the GET request.
    Ex:
    search="whisper",author="openai"
    etc.
    Returns:
        _type_: _description_
    """
    hf_token = get_hf_token()
    response = requests.get(
        "https://huggingface.co/api/models",
        params={
            **{k:kwargs[k] for k in kwargs if not k.lower().strip().startswith('expand')},
            "sort": kwargs.get('sort', "downloads"),
            "limit": kwargs.get('limit', "10"),
            "config": "True",
            "full": "False",
        },
        headers={
            "Authorization":f"Bearer {hf_token}"
        })
    if response.status_code == 401:
        spawn_popup_activity("Error!", f"Invalid huggingface token!\nTo use the search feature, you must have a file named\n\t'{HF_TOKEN_FILENAME}'\nthat contains your huggingface token!\nSee here for details:\n\nhttps://huggingface.co/docs/hub/en/security-tokens")
    return response.json()

def search_for_hf_model(query):
    """Searches huggingface to validate a model name
    Will check for the HF_TOKEN_FILENAME.
    If more than one match is found we will ask the user to select which one they wanted.
    Args:
        query (str): query string to be searched.
    
    Raises:
        Exception: If something went wrong.
    
    Returns:
        str | None: if a model is selected, we will return the model id, otherwise we will return None.
    """
    data = get_hf_search_query(search=query)
    # pre-filter for only whisper based models
    data = [x for x in data if x["config"]["model_type"] == "whisper"]
    if len(data) == 0:
        spawn_popup_activity(f"Search result", f"'{query}' yeilded {len(data)} results. Try again.")
        return None
    
    if not spawn_popup_activity(f"Search result", f"'{query}' yeilded {len(data)} results. Click Yes to view them or No to abort search selection. Click yes on the next window that matches the entry you want to use..."):
        return None
    
    while True:
        for idx, entry in enumerate(data,start=1):
            selected = spawn_popup_activity(f"Search result: #{idx}", f"'{query}' result #{idx}/{len(data)}:\n{entry['id']}\n\n{json.dumps(entry, indent=2)}\n\n Use selection?")
            if selected:
                return entry['id']
        if not spawn_popup_activity(f"Search result", f"End of results for '{query}'.\nYes to restart from the beginning or no to abort search:"):
            return None

def open_hf_search():
    hf_search_url = "https://huggingface.co/models?pipeline_tag=automatic-speech-recognition&library=transformers"
    try:
        import webbrowser
        webbrowser.open(hf_search_url)
    except:
        try:
            os.startfile(hf_search_url)
        except:
            print(f"Visit the following URL to find additional models from huggingface:\n{hf_search_url}")
    spawn_popup_activity("Search", f"Use the huggingface search to find the model ID or model name to use. Click yes or no to continue.\n\nURL: {hf_search_url}")

def get_available_langs() -> List[str]:
    """Returns:
        List[str]: language codes or names available for transcription.
    """
    common = ['', 'English', 'Spanish', 'Arabic', 'Egyptian Arabic', 'Bengali', 'Bhojpuri', 'Mandarin Chinese', 'German', 'French', 'Gujarati', 'Hausa', 'Hebrew', 'Hindi', 'Indonesian', 'Italian', 'Javanese', 'Japanese', 'Korean', 'Marathi', 'Iranian Persian', 'Portuguese', 'Russian', 'Tamil', 'Telugu', 'Turkish', 'Urdu', 'Vietnamese', 'Wu Chinese', 'Yue Chinese']
    return common

def validate_language(inp):
    if not inp:
        return inp
    try:
        l = pycountry.languages.lookup(inp)
        return l.alpha_3
    except LookupError as e:
        spawn_popup_activity("Language Error!", f"Unable to determine language: '{inp}'.\nValid language codes are:\nThe 2 letter code such as 'en', 'es', 'zh', etc.\nThe 3 letter code such as 'eng', 'spa', 'zho'\nThe full name such as 'english', 'spanish', 'chinese'.\nPress any button to continue.")
    return None

def get_any_file_type() -> List[str]:
    return ["*", ".*", "*.*"]

def get_audio_file_types() -> List[str]:
    """Supported audio file types that dont need to be converted

    Returns:
        list of file extentions
    """
    # if its not usable by the soundfile package then it will cause an error to be thrown
    return [t.lower() for t in soundfile.available_formats().keys()]

def get_video_file_types() -> List[str]:
    return [
        "webm", "mkv", "flv", "avi", "mov", "mp4", "m4v", "mpeg", 
        "mpg", "mpeg", "m2v", "m4v", "f4v", "f4p", "f4a", "f4b",
        "evo", "divx", "m4a"
    ]

@lru_cache(maxsize=1)
def get_ffmpeg_supported_formats():
    result = subprocess.run(
        ['ffmpeg', '-formats'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True  # decode to string instead of bytes
    )

    ret = set()
    for line in result.stdout.split('\n'):
        if not line:
            continue
        sections = [x for x in line.split(' ') if x]
        if len(sections) < 2:
            continue
        filetypes = sections[1].lower().split(',')
        ret |= set(filetypes)
    if len(ret) < 10:
        # something went wrong
        print("Ensure that ffmpeg is installed correctly!")
    return sorted(ret)

def convert_file_to_type(inp_file: str, totype: str):
    """Converts given file to the file type using ffmpeg.

    Args:
        inp_file (str): the input file path
        totype (str): the output file type extention

    Returns:
        str: the output file path
    """
    name, ext = os.path.splitext(inp_file)
    out_name = f"{name}{'' if str(totype).startswith('.') else '.'}{totype}"
    if os.path.exists(out_name):
        # assume it has already converted the file
        print(f"Using cached version of {inp_file}!")
        return out_name
    try:
        out, err = (ffmpeg
            .input(inp_file)
            .output(out_name)#, format='s16le', acodec='pcm_s16le', ac=1, ar='16k')
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        print(e.stderr, file=sys.stderr)
        print(f"Failed to convert '{inp_file}' to '{totype}'! Please attempt to convert it to '{totype}' manually and retrying!")
    return out_name

def decode_int(encoded: str, base_chars: str='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') -> int:
    """Converts a string representing an int in the given base_chars of characters to an integer.

    Args:
        encoded (str): string to be converted from the base_chars
        base_chars (str, optional): The string with the chars to be converted, in order, duplicates NOT allowed. Defaults to '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'.

    Returns:
        int: number decoded with the base_chars
    """
    assert len(encoded) > 0, 'encoded value must have content!'
    assert len(base_chars) > 0, 'base_chars must contain at least one character'
    assert len(set(base_chars)) == len(base_chars), 'base_chars cannot contain duplicates'
    assert len(set(encoded) - set(base_chars)) == 0, 'encoded value must be comprised of values inside the base_chars!'
    
    base = len(base_chars)
    decoded_value = 0
    power = 0
    
    # Create a mapping from character to its integer value
    char_to_value = {char: i for i, char in enumerate(base_chars)}
    
    # Iterate through the encoded string from right to left (least significant to most significant)
    for char in reversed(encoded):
        digit_value = char_to_value[char]
        decoded_value += digit_value * (base ** power)
        power += 1
    
    return decoded_value

def encode_int(number: int, base_chars: str='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') -> str:
    """Converts an integer to a base of the characters in the given string.

    Args:
        number (int): number to be converted to the base_chars
        base_chars (str, optional): The string with the chars available to be converted, in order, duplicates NOT allowed. Defaults to '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'.

    Returns:
        str: number encoded with the base_chars
    """
    assert isinstance(number, int), 'number must be a number'
    assert number >= 0, 'number must be greater than or equal to zero'
    assert len(base_chars) > 0, 'base_chars must contain at least one character'
    assert len(set(base_chars)) == len(base_chars), 'base_chars cannot contain duplicates'
    if number < len(base_chars):
        return base_chars[number]
    encoded = ''
    while number != 0:
        number, i = divmod(number, len(base_chars))
        encoded = base_chars[i] + encoded
    return encoded

def setup_local_user_cfgs():
    """ Make per user config files and directories. """
    if not MODELS_CFG_FILENAME.exists():
        MODELS_CFG_FILENAME.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(MODELS_CFG_DEFAULT, MODELS_CFG_FILENAME)
    if not CACHE_FILENAME.exists():
        CACHE_FILENAME.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(CACHE_DEFAULT, CACHE_FILENAME)

def get_hf_token():
    """Gets hf token.

    Raises:
        Exception: FileNotFoundError if we cant find the file located at HF_TOKEN_FILENAME

    Returns:
        _type_: _description_
    """
    try:
        stats = os.stat(HF_TOKEN_FILENAME)
        if stats.st_size == 0:
            raise Exception("Empty file!")
    except:
        with open(HF_TOKEN_FILENAME, 'w') as f:
            f.write("hf_YOUR_TOKEN_HERE\nSee here for details:\n\nhttps://huggingface.co/docs/hub/en/security-tokens\nWhen done, the only thing in this file should be your hftoken, remove these lines of text.")
        return FileNotFoundError(f"To use the search feature, you must have a file named\n\t'{HF_TOKEN_FILENAME}'\nthat contains your huggingface token!\nSee here for details:\n\nhttps://huggingface.co/docs/hub/en/security-tokens\n\nRetry operation after you have set your token.")
        
    with open(HF_TOKEN_FILENAME, 'r', encoding='utf-8') as f:
        hf_token = f.read().strip()
    return hf_token

def get_model_list():
    """
    Gets an updated list of models
    Returns:
        List[str]: List of available model names
    """
    models = {}
    models_to_search = []
    if os.path.isfile(MODELS_CFG_FILENAME):
        with open(MODELS_CFG_FILENAME, 'r', encoding='utf-8') as f:
            models_to_search = json.load(f)
    for q in models_to_search:
        results = get_hf_search_query(**q)
        for r in results:
            if r.get('pipeline_tag') == 'automatic-speech-recognition':
                models[r['id']] = r
    models = sorted(models, key = lambda k: models[k].get('downloads', models[k].get('likes', 0)), reverse=True)
    return models

def validate_requirements():
    """Ensure we have 3rd party software accessable.

    Returns:
        bool: True if there are errors, otherwise, False.
    """
    has_errors = False
    # locate ffmpeg path
    FFMPEG_PATH = shutil.which('ffmpeg') or (shutil.which('ffmpeg', path=FFMPEG_EXE_DIR) if sys.platform.startswith("win") else None)
    # locate git path
    GIT_PATH = shutil.which('git')

    if not FFMPEG_PATH:
        print("> TRANSCRIBER WARNING!\n>> FFMPEG not found!\n>>> We will not be able to convert files automatically!\n>>> Reccomendations to fix:\n>>>>   - Install ffmpeg and add the installed ...ffmpeg/bin directory to your system PATH variables.\n>>>>   OR\n>>>>   - Manaually convert the input files to one of '.mp3', '.mp4', or '.wav' so that the AI will be able to accept the file!\n\n")
        has_errors = True
    # validate for git
    if not GIT_PATH:
        print("> TRANSCRIBER WARNING\n>> GIT not found!\n>>> We will not be able to generate the @debug logs properly!")
        has_errors = True
    if has_errors:
        print("> TRANSCRIBER WARNING: Please see the latest README.md (https://github.com/Noah-Jaffe/Transcriber/blob/main/README.md) and follow the full requirements and install guide to fix these issues!")
    return has_errors
