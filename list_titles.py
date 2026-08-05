import ctypes, time
user32 = ctypes.windll.user32
titles = []
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int)

def cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        t = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, t, 256)
        title = t.value.strip()
        if title:
            titles.append((hwnd, title))
    return 1

user32.EnumWindows(EnumWindowsProc(cb), 0)
for hwnd, title in titles:
    print(hwnd, repr(title))
