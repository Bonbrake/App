# COMFYUI UNCENSORED — PHASE 3 FIX PLAN

## Audit Summary

### Verified Issues (from source + pixel analysis)

| # | Category | Issue | Severity | Root Cause |
|---|----------|-------|----------|------------|
| 1 | **Layout** | Tab content uses `CTkFrame` instead of `CTkScrollableFrame` — spacer at row 20 may not fill when content is less than 20 rows | Medium | Controls are pushed to top, large empty space below |
| 2 | **Layout** | Upscale tab dropdown missing styling (`fg_color`, `button_color`, `hover_color`) | Medium | Line 563: `ctk.CTkOptionMenu(sf, values=UPSCALE_MODELS, variable=m["model"])` — no color params |
| 3 | **Button** | Upscale Model dropdown has inconsistent styling | Medium | No `fg_color="#2a2a2e"` on upscale dropdown |
| 4 | **Button** | Scale entry in upscale has no border_color styling | Low | `ctk.CTkEntry(sf, textvariable=m["scale"])` — no border_width/border_color |
| 5 | **Button** | Sidebar "Gallery" nav goes to Upscale tab — misleading | Medium | No actual gallery exists |
| 6 | **Button** | Sidebar "Settings" nav goes to Image to Image tab — misleading | Medium | No actual settings panel exists |
| 7 | **Button** | "Open Output" button fails silently if dir doesn't exist | Low | `os.startfile(OUTPUT_DIR)` — no os.makedirs guard |
| 8 | **Button** | "View Log" button fails silently if file doesn't exist | Low | `os.startfile(LOG_FILE)` — no existence check |
| 9 | **Button** | "Save History" only saves current prompt — no metadata | Medium | Missing: model, params, output path, timestamp |
| 10 | **Layout** | Upscale tab: Scale entry not styled to match other entries | Low | Missing border_color / fg_color params |

### Verified OK (No Changes Needed)

| Component | Status |
|-----------|--------|
| Left edge white line | **FIXED** — 0% white pixels at x=0-15 |
| Sidebar settings | All visible (Steps through Output Format) |
| Tab switching | All 3 tabs switch correctly |
| Generate button | Works, calls `_start_generate` |
| Model dropdown | Works, calls `_on_model` |
| Preset dropdown | Works, calls `_on_preset` (handles txt2img + img2img) |
| Upload buttons | Both img2img and upscale have `command` set |
| Bottom bar buttons | All 4 have commands (evenly distributed) |
| Sidebar nav buttons | All 3 have commands |
| Tooltips | All controls have Enter/Leave bindings |
| Backend startup | Window visible immediately, backend deferred 300ms |
| Color tuples | All 32 tuples correct (light, dark) order |
| AcrylicBackground | No white line, debounced at 500ms |

---

## Fix Plan

### Tier 1: Critical UX Issues (Implement First)

#### Fix 1: Rename Sidebar Nav Buttons
```python
# Line 314: Change labels to be honest about what they do
nav = [("Generate", self._focus_generate), ("Upscale", self._focus_upscale),
       ("Image to Image", self._focus_img2img)]
```
- "Gallery" → "Upscale" (label now matches behavior)
- "Settings" → "Image to Image" (label now matches behavior)
- Rename handlers: `_focus_gallery` → `_focus_upscale`, `_focus_settings` → `_focus_img2img`

#### Fix 2: Add Error Handling to Bottom Buttons
```python
# Open Output: ensure directory exists
("Open Output", lambda: (os.makedirs(OUTPUT_DIR, exist_ok=True), os.startfile(OUTPUT_DIR)))

# View Log: check file exists
def _view_log(self):
    if os.path.exists(LOG_FILE):
        os.startfile(LOG_FILE)
    else:
        messagebox.showinfo("No log", "No log file found.")

# Save History: save full context
def _save_history(self):
    entry = {"ts": ..., "prompt": ..., "neg": ..., "model": ..., "tab": ..., "params": {...}}
```

#### Fix 3: Fix Upscale Dropdown Styling
```python
# Line 563: Add missing styling
ctk.CTkOptionMenu(sf, values=UPSCALE_MODELS, variable=m["model"],
                  fg_color="#2a2a2e", button_color="#2a2a2e", button_hover_color="#3a3a4e")
# Line 564: Add border to Scale entry
ctk.CTkEntry(sf, textvariable=m["scale"], border_width=1, border_color=("#d0d0d0", "#2a2a2e"))
```

### Tier 2: Layout Improvements (Implement After Tier 1)

#### Fix 4: Better Tab Content Layout
Instead of a fixed spacer row, use proper bottom-weight expansion:
```python
sf.grid_rowconfigure(0, weight=0)  # prompt
sf.grid_rowconfigure(1, weight=0)  # neg  
sf.grid_rowconfigure(2, weight=0)  # ...controls...
sf.grid_rowconfigure(999, weight=1)  # expand remaining space
```
This ensures controls stay at top and space grows evenly below.

#### Fix 5: Improve History Saving
Save full generation metadata:
- Model name
- All parameters (width, height, steps, cfg, seed, batch, sampler, scheduler)
- Prompt + negative prompt
- Output file path
- Timestamp
- Tab used (txt2img/img2img/upscale)

### Tier 3: Feature Enhancements (Optional)

#### Enhancement 1: Actual Gallery View
- Thumbnail grid of images from `OUTPUT_DIR`
- Click to re-open or re-upscale
- Delete/rename capability

#### Enhancement 2: Settings Panel
- VRAM limit slider
- Output directory picker
- Model archive management
- Theme toggle persistence

---

## Execution Order
```
1. [15 min] Fix nav button labels + handler names
2. [30 min] Add error handling to bottom bar buttons
3. [15 min] Fix upscale dropdown styling
4. [15 min] Improve tab content layout (proper row weights)
5. [30 min] Improve history saving with full metadata
6. [15 min] Rebuild EXE
7. [15 min] Verify all fixes
```

**Total: ~2 hours**

---

## Verification Criteria
- [ ] All 13 buttons have correct, descriptive labels
- [ ] All bottom bar buttons have error handling
- [ ] Upscale tab styling matches txt2img/img2img
- [ ] Tab content fills available space (no large empty middle)
- [ ] History saves full metadata, loads on startup
- [ ] No white lines or visual artifacts
- [ ] EXE builds and runs with 0 startup lag
- [ ] All tooltips visible on hover
```
