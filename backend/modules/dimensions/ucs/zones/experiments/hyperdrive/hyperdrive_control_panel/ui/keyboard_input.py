# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/ui/keyboard_input.py

"""
⌨ Hyperdrive Keyboard Input
----------------------------
* Provides non-blocking keyboard input during runtime.
* Supports manual stage transitions, pause/resume, and emergency stop.
"""

import sys
import termios
import tty
import select

def get_key(timeout=0.05):
    """Non-blocking keypress capture."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        rlist, _, _ = select.select([fd], [], [], timeout)
        if rlist:
            return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return None