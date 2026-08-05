import ast
with open(r"C:\ComfyUI-Desktop\ComfyUI_App.py", "r") as f:
    ast.parse(f.read())
print("SYNTAX OK")
