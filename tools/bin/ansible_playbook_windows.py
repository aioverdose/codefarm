from __future__ import annotations

import locale
import os
import sys
import types

_original_get_blocking = getattr(os, "get_blocking", None)
if _original_get_blocking is not None:
    def _safe_get_blocking(fd: int) -> bool:
        try:
            return _original_get_blocking(fd)
        except OSError:
            return True
    os.get_blocking = _safe_get_blocking

_original_setlocale = locale.setlocale

def _safe_setlocale(category, value=None):
    try:
        return _original_setlocale(category, value)
    except locale.Error:
        return "C.UTF-8"

locale.setlocale = _safe_setlocale
locale.getlocale = lambda category=locale.LC_CTYPE: ("C", "UTF-8")
locale.getencoding = lambda: "UTF-8"
locale.getpreferredencoding = lambda do_setlocale=True: "UTF-8"

if "fcntl" not in sys.modules:
    fcntl = types.ModuleType("fcntl")
    fcntl.LOCK_EX = 2
    fcntl.LOCK_UN = 8
    fcntl.LOCK_NB = 4
    fcntl.F_GETFL = 3
    fcntl.F_SETFL = 4
    fcntl.ioctl = lambda *args, **kwargs: 0
    fcntl.fcntl = lambda *args, **kwargs: 0
    fcntl.flock = lambda *args, **kwargs: 0
    sys.modules["fcntl"] = fcntl

if "termios" not in sys.modules:
    termios = types.ModuleType("termios")
    termios.TIOCGWINSZ = 0x5413
    termios.TCSAFLUSH = 2
    termios.TCSADRAIN = 1
    termios.TCSANOW = 0
    termios.ICANON = 2
    termios.ECHO = 8
    termios.ISIG = 1
    termios.ICRNL = 256
    termios.IXON = 1024
    termios.OPOST = 1
    termios.CS8 = 48
    termios.tcgetattr = lambda *args, **kwargs: [0, 0, 0, 0, 0, 0, [b"", b""]]
    termios.tcsetattr = lambda *args, **kwargs: None
    sys.modules["termios"] = termios

from ansible.cli.playbook import main

if __name__ == "__main__":
    sys.exit(main())

