
import sys, os, traceback
with open(r'c:\Users\jakeb\AppData\Local\Programs\ComfyUIX\debug_launch.log', 'w') as f:
    f.write('Wrapper started with python: ' + sys.executable + '\n')
    f.write('CWD: ' + os.getcwd() + '\n')
    try:
        f.write('Importing ComfyUI_App...\n')
        f.flush()
        import ComfyUI_App
        f.write('Imported successfully! Calling main()...\n')
        f.flush()
        ComfyUI_App.main()
        f.write('main() finished!\n')
    except Exception as e:
        f.write('FATAL EXCEPTION:\n' + traceback.format_exc())
