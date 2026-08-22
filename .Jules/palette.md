## 2026-08-22 - PySide6 HUD Control Accessibility & Hover Tooltips
**Learning:** PySide6 desktop HUD controls (`QComboBox`, `QPushButton`) without explicit `setToolTip`, `setAccessibleName`, and `setAccessibleDescription` leave screen reader users and mouse hover users without context for AI system actions like clearing VRAM or starting services.
**Action:** When adding or updating PySide6 interactive widgets in the HUD, always chain `setToolTip`, `setAccessibleName`, and `setAccessibleDescription` alongside visual styling.
