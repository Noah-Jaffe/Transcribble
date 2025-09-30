import sys
from tkinter.font import BOLD, NORMAL
from pathlib import Path

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

# Style
## Colors
class COLOR_THEME:
    """ Color theme to apply to the GUI. """
    IN_PROGRESS = "#FFFFE0"   # lightyellow
    LOADED = "#00FFFF"        # aqua
    MAIN_WINDOW = "#ADD8E6"   # lightblue
    FAILED = "#E04545"        # lightred
    COMPLETED = "#008000"     # green
    BUTTON = "#FFC0CB"        # pink

## Fonts
DEFAULT_FONT = "Helvetica" if sys.platform == "darwin" else "Arial"
MONO_FONT = "Menlo" if sys.platform == "darwin" else "Consolas"

LABEL_FONT = (DEFAULT_FONT, 12, BOLD)
BUTTON_FONT = (DEFAULT_FONT, 12, NORMAL)

FILE_NAME_FONT = (MONO_FONT, 10, NORMAL)
TOOLTIP_FONT = (MONO_FONT, 8, NORMAL)

# Files and directories
## Local directories and filenames
LOC_OF_THIS_FILE_RELATIVE_TO_PROJECT_ROOT = "../"
THIS_DIR = normalize_path(__file__, LOC_OF_THIS_FILE_RELATIVE_TO_PROJECT_ROOT).parent
TOOLS_DIR_REL = "tools"
CONFIG_FILES_DIRECTORY_REL = "cfg" 
MODELS_FN = "models.json"
CACHE_FN = "cache.json"
MASCOT_FN = "mascot.png"
HF_TOKEN_FN = ".hftoken"
TRANSCRIBE_SUBPROC_FN = "transcribe_proc.py"

## Default cfg files
MODELS_CFG_DEFAULT = normalize_path(THIS_DIR, CONFIG_FILES_DIRECTORY_REL, MODELS_FN)
CACHE_DEFAULT = normalize_path(THIS_DIR, CONFIG_FILES_DIRECTORY_REL, CACHE_FN)

## Functional config values
HF_TOKEN_FILENAME = normalize_path(THIS_DIR, HF_TOKEN_FN)
MASCOT_FILENAME = normalize_path(CONFIG_FILES_DIRECTORY_REL, MASCOT_FN)
TRANSCRIBE_SUBPROC_FILENAME = normalize_path(THIS_DIR, TRANSCRIBE_SUBPROC_FN)
FFMPEG_EXE_DIR = normalize_path(TOOLS_DIR_REL)

## Per user config file locations
PER_USER_ROOT = normalize_path(Path.home())
PER_USER_CONFIG_FILES_DIRECTORY_REL = f".{CONFIG_FILES_DIRECTORY_REL}"
MODELS_CFG_FILENAME = normalize_path(PER_USER_ROOT, PER_USER_CONFIG_FILES_DIRECTORY_REL, MODELS_FN)
CACHE_FILENAME = normalize_path(PER_USER_ROOT, PER_USER_CONFIG_FILES_DIRECTORY_REL, CACHE_FN)


