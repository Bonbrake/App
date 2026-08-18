using System;
using System.IO;
using System.Diagnostics;
using System.Windows.Forms;

namespace ComfyUIX
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            try
            {
                string appDir = AppDomain.CurrentDomain.BaseDirectory;
                string scriptPath = Path.Combine(appDir, "ComfyUI_App.py");

                if (!File.Exists(scriptPath))
                {
                    string alt = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "ComfyUIX", "ComfyUI_App.py");
                    if (File.Exists(alt))
                    {
                        scriptPath = alt;
                        appDir = Path.GetDirectoryName(alt);
                    }
                }

                if (!File.Exists(scriptPath))
                {
                    MessageBox.Show("Could not find ComfyUI_App.py in:\n" + appDir, "ComfyUIX Launcher Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }

                // Locate pythonw.exe or python.exe
                string[] pyCandidates = new string[]
                {
                    Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Python\Python311\pythonw.exe"),
                    Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Python\Python311\python.exe"),
                    Path.Combine(appDir, @"python_embeded\pythonw.exe"),
                    Path.Combine(appDir, @"python_embeded\python.exe"),
                    @"C:\Python311\pythonw.exe",
                    @"C:\Python311\python.exe"
                };

                string pythonExe = null;
                foreach (string c in pyCandidates)
                {
                    if (File.Exists(c))
                    {
                        pythonExe = c;
                        break;
                    }
                }

                if (pythonExe == null)
                {
                    string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
                    foreach (string dir in pathEnv.Split(';'))
                    {
                        string trimmed = dir.Trim();
                        if (string.IsNullOrEmpty(trimmed)) continue;
                        string pw = Path.Combine(trimmed, "pythonw.exe");
                        string p = Path.Combine(trimmed, "python.exe");
                        if (File.Exists(pw)) { pythonExe = pw; break; }
                        if (File.Exists(p)) { pythonExe = p; break; }
                    }
                }

                if (pythonExe == null)
                {
                    MessageBox.Show("Python 3.11 was not detected on this system.\nPlease ensure Python 3.11 is installed.", "ComfyUIX Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }

                // Build argument string
                string formattedArgs = "\"" + scriptPath + "\"";
                if (args != null && args.Length > 0)
                {
                    foreach (string a in args)
                    {
                        formattedArgs += " \"" + a.Replace("\"", "\\\"") + "\"";
                    }
                }

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = pythonExe;
                psi.Arguments = formattedArgs;
                psi.WorkingDirectory = appDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;

                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Launch failed:\n" + ex.Message, "ComfyUIX Launcher Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
