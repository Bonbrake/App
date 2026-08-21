## 2026-08-21 - Custom Model Download URL Validation and Path Traversal Protection
**Vulnerability:** `download_custom_url` in `model_downloader.py` accepted unvalidated URL schemes (allowing `file://` local file reads) and un-sanitized custom filenames (allowing directory traversal via `../` or `..\`).
**Learning:** Arbitrary direct URL downloads in desktop applications must explicitly enforce network-only schemes (`http`/`https`) and strip directory paths from filenames before passing them to file system operations.
**Prevention:** Always validate URL schemes with `urllib.parse.urlparse` and sanitize filenames with `os.path.basename(filename.replace("\\", "/"))` when accepting user-supplied URLs and filenames.
