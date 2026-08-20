# Palette's Journal - UX & Accessibility Learnings

## 2026-08-20 - Icon-Only Button Accessibility in CustomTkinter
**Learning:** Icon-only and compact micro-action buttons (e.g. `📁`, `🗑`, `🎲`) in desktop Tkinter/CustomTkinter apps lack screen reader labels and visual text context for novice users. Binding a custom `ToolTip` instance to these widgets provides essential desktop visual cues and aria/tooltip guidance on hover.
**Action:** Always attach `ToolTip(button, ("Title", "Description"))` when creating icon-only or compact glyph buttons.
