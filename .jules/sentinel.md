## 2026-08-20 - Path Traversal in Model Downloader
**Vulnerability:** Model filename provided in model metadata was joined directly with target download directory without sanitization (`os.path.join(dest_dir, model_info["filename"])`), allowing directory traversal characters (e.g. `../../cron.d/malicious`) to write files outside the intended model directory.
**Learning:** External API model responses or user-supplied URLs cannot be trusted to contain safe filenames.
**Prevention:** Always sanitize untrusted path inputs using `os.path.basename()` before constructing file destination paths.
