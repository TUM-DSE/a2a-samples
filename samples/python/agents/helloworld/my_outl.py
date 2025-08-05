import ctypes
from ctypes import Structure, c_int, c_bool, c_char_p, c_void_p, c_float, POINTER, c_char, c_ubyte, c_ushort

lib = ctypes.CDLL('./guardian.so')

def setup_functions():
    """Configure all function signatures"""
    
    lib.my_outl.argtypes = [c_int, c_int]
    lib.my_outl.resty = None

    lib.my_ioperm.argtypes = [c_ushort]
    lib.my_ioperm.resty = None

