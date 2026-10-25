"""Small fixed-frame X11/XTest client for a private, authenticated display only."""
import ctypes as C, ctypes.util, struct, zlib
W, H = (800, 600)

class XImage(C.Structure):
    _fields_ = [('width', C.c_int), ('height', C.c_int), ('xoffset', C.c_int), ('format', C.c_int), ('data', C.c_void_p), ('byte_order', C.c_int), ('bitmap_unit', C.c_int), ('bitmap_bit_order', C.c_int), ('bitmap_pad', C.c_int), ('depth', C.c_int), ('bytes_per_line', C.c_int), ('bits_per_pixel', C.c_int), ('red_mask', C.c_ulong), ('green_mask', C.c_ulong), ('blue_mask', C.c_ulong)]

class Display:

    def __init__(self):
        self.x = C.CDLL('libX11.so.6')
        self.t = C.CDLL('libXtst.so.6')
        defs = {'XOpenDisplay': ([C.c_char_p], C.c_void_p), 'XDefaultRootWindow': ([C.c_void_p], C.c_ulong), 'XGetImage': ([C.c_void_p, C.c_ulong, C.c_int, C.c_int, C.c_uint, C.c_uint, C.c_ulong, C.c_int], C.POINTER(XImage)), 'XDestroyImage': ([C.POINTER(XImage)], C.c_int), 'XFlush': ([C.c_void_p], C.c_int), 'XSync': ([C.c_void_p, C.c_int], C.c_int), 'XStringToKeysym': ([C.c_char_p], C.c_ulong), 'XKeysymToKeycode': ([C.c_void_p, C.c_ulong], C.c_ubyte), 'XSetInputFocus': ([C.c_void_p, C.c_ulong, C.c_int, C.c_ulong], C.c_int), 'XRaiseWindow': ([C.c_void_p, C.c_ulong], C.c_int), 'XQueryTree': ([C.c_void_p, C.c_ulong, C.POINTER(C.c_ulong), C.POINTER(C.c_ulong), C.POINTER(C.POINTER(C.c_ulong)), C.POINTER(C.c_uint)], C.c_int), 'XFetchName': ([C.c_void_p, C.c_ulong, C.POINTER(C.c_char_p)], C.c_int), 'XFree': ([C.c_void_p], C.c_int), 'XCloseDisplay': ([C.c_void_p], C.c_int)}
        for n, (args, rest) in defs.items():
            f = getattr(self.x, n)
            f.argtypes = args
            f.restype = rest
        self.t.XTestFakeKeyEvent.argtypes = [C.c_void_p, C.c_uint, C.c_int, C.c_ulong]
        self.t.XTestFakeKeyEvent.restype = C.c_int
        self.d = self.x.XOpenDisplay(None)
        if not self.d:
            raise ValueError('Cannot connect to private display')
        self.root = self.x.XDefaultRootWindow(self.d)

    def frame(self):
        p = self.x.XGetImage(self.d, self.root, 0, 0, W, H, 18446744073709551615, 2)
        if not p:
            raise ValueError('Invalid compatibility-helper state')
        try:
            i = p.contents
            if not (i.width, i.height, i.bits_per_pixel, i.bytes_per_line, i.byte_order) == (W, H, 32, W * 4, 0):
                raise ValueError('Invalid compatibility-helper state')
            if not (i.red_mask, i.green_mask, i.blue_mask) == (16711680, 65280, 255):
                raise ValueError('Invalid compatibility-helper state')
            raw = C.string_at(i.data, W * H * 4)
            rgb = bytearray(W * H * 3)
            rgb[0::3] = raw[2::4]
            rgb[1::3] = raw[1::4]
            rgb[2::3] = raw[0::4]
            return bytes(rgb)
        finally:
            self.x.XDestroyImage(p)

    def focus(self, needle='DOSBox-X'):
        root, parent = (C.c_ulong(), C.c_ulong())
        children = C.POINTER(C.c_ulong)()
        count = C.c_uint()
        if not self.x.XQueryTree(self.d, self.root, C.byref(root), C.byref(parent), C.byref(children), C.byref(count)):
            raise ValueError('Invalid compatibility-helper state')
        found = None
        try:
            if not count.value < 1000:
                raise ValueError('Invalid compatibility-helper state')
            for i in range(count.value):
                name = C.c_char_p()
                win = children[i]
                if self.x.XFetchName(self.d, win, C.byref(name)) and name.value:
                    try:
                        if needle in name.value.decode(errors='replace'):
                            found = win
                    finally:
                        self.x.XFree(C.cast(name, C.c_void_p))
        finally:
            if children:
                self.x.XFree(children)
        if not found:
            raise ValueError('Expected private window absent')
        self.x.XRaiseWindow(self.d, found)
        self.x.XSetInputFocus(self.d, found, 2, 0)
        self.x.XSync(self.d, False)

    def key(self, name, down):
        allowed = {'Left', 'Right', 'Up', 'Down', 'Return', 'Escape', 'space', 'Control_L', 'Alt_L', 'Shift_L', 'Pause', 'Tab', 'BackSpace', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10'}
        if not (name in allowed or (len(name) == 1 and name in 'abcdefghijklmnopqrstuvwxyz0123456789')):
            raise ValueError('Invalid compatibility-helper state')
        code = self.x.XKeysymToKeycode(self.d, self.x.XStringToKeysym(name.encode()))
        if not code:
            raise ValueError('Invalid compatibility-helper state')
        if not self.t.XTestFakeKeyEvent(self.d, code, bool(down), 0):
            raise ValueError('Invalid compatibility-helper state')
        self.x.XFlush(self.d)

    def close(self):
        self.x.XCloseDisplay(self.d)

def png(rgb):
    if not len(rgb) == W * H * 3:
        raise ValueError('Invalid compatibility-helper state')

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 4294967295)
    scan = b''.join((b'\x00' + rgb[y * W * 3:(y + 1) * W * 3] for y in range(H)))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(scan)) + chunk(b'IEND', b'')
