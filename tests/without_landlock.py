"""CPU test helper: make Landlock syscalls unavailable in this child only.

This adds a kernel seccomp filter returning ENOSYS for all three Landlock calls.
It does not change the host, permit a blocked operation, or disable the selected
filesystem backend. Usage: python3 tests/without_landlock.py COMMAND [ARGS...]
"""

import ctypes
import errno
import os
import platform
import sys


class Instruction(ctypes.Structure):
    _fields_ = [
        ("code", ctypes.c_ushort),
        ("jt", ctypes.c_ubyte),
        ("jf", ctypes.c_ubyte),
        ("k", ctypes.c_uint),
    ]


class Program(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ushort), ("filter", ctypes.POINTER(Instruction))]


if __name__ == "__main__":
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise SystemExit("Test helper requires Linux x86-64")
    # Validate the syscall architecture, then reject create/add/restrict only.
    instructions = [
        (0x20, 0, 0, 4),
        (0x15, 1, 0, 0xC000003E),
        (0x06, 0, 0, 0x80000000),
        (0x20, 0, 0, 0),
    ]
    for number in (444, 445, 446):
        instructions += [(0x15, 0, 1, number), (0x06, 0, 0, 0x00050000 | errno.ENOSYS)]
    instructions += [(0x06, 0, 0, 0x7FFF0000)]
    filters = (Instruction * len(instructions))(
        *(Instruction(*i) for i in instructions)
    )
    program = Program(len(filters), filters)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        raise OSError(ctypes.get_errno(), "Cannot install missing-Landlock test filter")
    os.execvp(sys.argv[1], sys.argv[1:])
