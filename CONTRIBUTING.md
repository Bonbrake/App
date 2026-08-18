# Contributing to ComfyUIX Matrix Edition

Thank you for your interest in contributing to **ComfyUIX**! We welcome code contributions, feature requests, workflow graphs, and documentation improvements.

---

## 🛠️ Development Setup

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/Bonbrake/ComfyUIX.git
   cd ComfyUIX
   ```

2. **Create a virtual environment (Recommended)**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Launch the Development GUI**:
   ```powershell
   python ComfyUI_App.py
   ```

---

## 🧪 Testing & Quality Assurance

Before submitting any Pull Request, you MUST run both automated test suites to ensure 100% regression-free code:

```powershell
# 1. Run the Primary Functional QA Suite (53 Tests)
python qa_suite.py

# 2. Run the Multi-Angle Deep Stress Suite (160+ Assertions)
python multi_angle_debug.py
```

### Key Contribution Guidelines
- **Zero Feature Removal**: Never remove existing dials, sliders, or workflow capabilities without clear architectural deprecation plans.
- **Responsive Geometry**: Verify that all UI elements render cleanly without clipping on small windows (880×580) and 4K displays with 125%–175% DPI scaling.
- **Process Safety**: Use Windows Job Objects for any child process spawns to prevent orphan backend processes.
- **AST Integrity**: Avoid duplicate method names or shadowed class definitions.

---

## 🚀 Building Standalone Executables

To build the standalone Windows `.exe` using PyInstaller:
```powershell
pip install pyinstaller
pyinstaller ComfyUI_Uncensored.spec --noconfirm --clean
```
The compiled output will be generated in `dist/ComfyUIX.exe`.
