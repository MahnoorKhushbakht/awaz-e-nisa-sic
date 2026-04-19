import shutil
import os

cache_path = os.path.expanduser("~/.cache/whisper")
if os.path.exists(cache_path):
    shutil.rmtree(cache_path)