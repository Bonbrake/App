## 2026-08-22 - Path Traversal in Model Downloader Filenames
**Vulnerability:** Model downloader accepted arbitrary URLs and custom model filenames containing path traversal sequences (`../`, `..\`, `%2e%2e%2f`), allowing files to be written outside designated model directories.
**Learning:** `os.path.join` does not prevent path traversal when filename components contain relative directory elements or absolute path prefixes.
**Prevention:** Sanitize filenames with `os.path.basename` after normalizing slashes and URL-decoding, and enforce path confinement using `os.path.commonpath`.
