"""Use the console interpreter for JSON workers even under pythonw startup."""
from pathlib import Path
import sys

def worker_python():
    executable=Path(sys.executable)
    if executable.name.casefold()=='pythonw.exe':
        executable=executable.with_name('python.exe')
        if not executable.is_file():
            raise RuntimeError('The virtual environment console interpreter is missing.')
    return str(executable)
