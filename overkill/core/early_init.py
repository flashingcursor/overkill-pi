"""Early initialization for TTY font setting"""

import os
import sys


def set_tty_font_early():
    """Set TTY font before any imports that might produce output"""
    try:
        # Check if on physical console
        tty = os.ttyname(0)
        if tty.startswith("/dev/tty") and not tty.startswith("/dev/pts"):
            # Apply large font for TV viewing
            os.system("setfont /usr/share/consolefonts/Lat15-TerminusBold28x14.psf.gz 2>/dev/null || " +
                     "setfont /usr/share/consolefonts/Lat15-TerminusBold20x10.psf.gz 2>/dev/null || " +
                     "setfont /usr/share/consolefonts/Lat15-Fixed16.psf.gz 2>/dev/null")
    except:
        pass