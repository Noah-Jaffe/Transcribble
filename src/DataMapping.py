from src.Utils import encode_int
from collections.abc import Hashable
import re
import json
from pathlib import Path
from typing import Any


class DataMapping(object):
    """Dict-like object that can reference key value pairs with dot notation as well as index notation."""
    
    __illegal_format__ = r"^__[^_]+.*?[^_]+__$"
    
    def __init__(self, data:dict={}):
        """Generate an object that can be used with dot notation to reference dynamic keys.
        AKA js like object.
        
        Args:
            data (dict, optional): data to set. Defaults to empty dict.
        """
        if data:
            if not isinstance(data, dict):
                raise TypeError(f"Data must be a dictlike object!")
            self.__update__(data)
    
    def __getattr__(self, key: Hashable):
        """Get item via <self>.<key>
        
        Args:
            key (Hashable): key to get
        
        Returns:
            Any: the value for the given key
        """
        return self.__dict__[key]
    
    def __setattr__(self, key:Hashable, value: Any):
        """Set an attribute that can be referenced via <self>.<key>
        
        Args:
            key (Hashable): key to be created or updated
            value (Any): value to set for the given key
        """
        if type(key) == str and re.match(DataMapping.__illegal_format__, key, re.MULTILINE | re.DOTALL):
            raise KeyError(f"Cannot set a key '{key}' as the key format of {DataMapping.__illegal_format__} is protected!")
        self.__dict__[key] = value
    
    def __delattr__(self, key:Hashable):
        """Deletes an key value pair via the given key

        Args:
            key (Hashable): key to delete, if it exists
        """
        if key in self.___illegal_key_names:
            raise KeyError(f"Cannot delete key '{key}' as it is protected!")
        del self[key]
    
    def __getitem__(self, key:Hashable):
        return self.__dict__[key]
    
    def __repr__(self):
        return repr({k: self.__dict__[k] for k in self.__dict__ if not re.match(DataMapping.__illegal_format__, k, re.MULTILINE | re.DOTALL)})
    
    def __str__(self):
        return str({k: self.__dict__[k] for k in self.__dict__ if not re.match(DataMapping.__illegal_format__, k, re.MULTILINE | re.DOTALL)})
    
    def __update__(self, obj:dict):
        """Update this object's key value pairs with the given dicts key value pairs.
        
        Args:
            obj (dict): dict to be merged into this one.
        """
        for key, value in obj.items():
            if type(key) == str:
                setattr(self, key, value)
            elif isinstance(key, Hashable):
                # note that regular hashable keys may not be able to be accessed via dot notation!
                self.__dict__[key] = value
    
    @staticmethod
    def __from_file__(file_path: str):
        """Load a DataMapping from a file (should be jsonlike)

        Args:
            file_path (str): file path for file to be loaded
        
        Raises:
            TypeError: if data in the given file cannot be parsed with json.
        
        Returns:
            DataMapping|None: The DataMapping for the read data, or None if file does not exist or an error occured
        """
        if Path(file_path).is_file():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return DataMapping(data)
            except Exception as e:
                print(e)
        return None
    
    def __to_file__(self, file_path: str, allow_overwrite: bool = True) -> Path:
        """Write this object to disk. 
        
        Args:
            file_path (str): path to be written to
            allow_overwrite (bool, optional): Allow overwrite exisint file, if False we will append a number to the file name to make it unique. Defaults to True.
        
        Raises:
            TypeError: if data in this object cannot be serialized with json.
        
        Returns:
            str: The file path we wrote to.
        """
        # MAGIC NUMBER [max file name length]: Windows (255), Mac (1023)
        MAX_FILE_NAME_LENGTH = 250
        fp = Path(file_path)
        if not fp.parent.exists():
            fp.parent.mkdir(exist_ok=True, parents=True)

        name, ext = fp.parts[-1].rsplit('.', 1)
        if not allow_overwrite and fp.exists():
            as_fn = lambda p, n, e, i: Path(p.parent, f"{n}{'.' + encode_int(i) if i else ''}{'.' + e if e else ''}")
            num = 0
            name, ext = fp.parts[-1].rsplit('.', 1)
            new_fp = as_fn(fp, name, ext, num)
            while len(new_fp.parts[-1]) < MAX_FILE_NAME_LENGTH and new_fp.exists():
                num += 1
                new_fp = as_fn(fp, name, ext, num)
            if len(new_fp.parts[-1]) >= MAX_FILE_NAME_LENGTH or new_fp.exists():
                raise FileExistsError(f"Please chose a different file name as the calculated file name of '{new_fp.as_posix()}' is either too long ({len(new_fp.as_posix())} >= {MAX_FILE_NAME_LENGTH} ?) or too many files exist with the same base name")
            fp = new_fp
        # find output file extention type
        try:
            with open(fp.as_posix(), 'w', encoding='utf-8') as f:
                json.dump(self.__dict__)
        except TypeError as e:
            raise TypeError(f"{self.__name__} contains data that is unserializable by json!")
        return fp
