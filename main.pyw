
#parche para win 7
import hashlib

_original_md5 = hashlib.md5

def _md5_compat(*args, **kwargs):
    # Eliminamos el argumento problemático si existe
    kwargs.pop("usedforsecurity", None)
    return _original_md5(*args, **kwargs)

hashlib.md5 = _md5_compat

from interfaz import InterfazEstricta
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    InterfazEstricta(root)
    root.mainloop()