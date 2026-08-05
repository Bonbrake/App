import os
exe = r"C:\ComfyUI-Desktop\dist\ComfyUI_Uncensored.exe"
shortcut = r"C:\Users\jakeb\Desktop\ComfyUI.lnk"
print("EXE exists:", os.path.exists(exe))
print("EXE size:", os.path.getsize(exe) if os.path.exists(exe) else "N/A")
print("Shortcut exists:", os.path.exists(shortcut))
print("Shortcut size:", os.path.getsize(shortcut) if os.path.exists(shortcut) else "N/A")
