import ctypes
from ctypes import Structure, c_int, c_bool, c_char_p, c_void_p, c_float, POINTER, c_char, c_ubyte, c_ushort

lib = ctypes.CDLL('./guardian.so')

def convert_to_bpfsize(payload_size):
    reported_size = payload_size
    if payload_size >= (1024 * 1024):
        reported_size = 7000 + payload_size // (1024 * 1024)
    elif payload_size >= 1024:
        print(f"Old Payload_size: {payload_size}")
        reported_size = 3000 + payload_size // 1024
        print(f"Payload_size: {reported_size}")
    return reported_size


def setup_functions():
    """Configure all function signatures"""
    
    lib.my_outl.argtypes = [c_int, c_int]
    lib.my_outl.resty = None

    lib.my_ioperm.argtypes = [c_ushort]
    lib.my_ioperm.resty = None

