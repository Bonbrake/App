import unittest
import os
import model_downloader

class TestModelDownloaderSecurity(unittest.TestCase):

    def test_invalid_url_scheme_raises_value_error(self):
        invalid_urls = [
            "file:///etc/passwd",
            "file:///C:/Windows/win.ini",
            "ftp://example.com/model.safetensors",
            "gopher://127.0.0.1:8188",
            "data:text/plain;base64,SGVsbG8=",
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError) as ctx:
                    model_downloader.download_custom_url(url)
                self.assertIn("Invalid URL scheme", str(ctx.exception))

    def test_custom_name_path_traversal_sanitization(self):
        traversal_names = [
            ("../../malicious.exe", "malicious.exe.safetensors"),
            ("..\\..\\malicious.py", "malicious.py.safetensors"),
            ("../../../etc/shadow", "shadow.safetensors"),
            ("..", "custom_model.safetensors"),
            (".", "custom_model.safetensors"),
        ]
        for input_name, expected_filename in traversal_names:
            with self.subTest(input_name=input_name):
                t = model_downloader.download_custom_url("https://example.com/model.safetensors", custom_name=input_name)
                t.cancel()
                if t._thread and t._thread.is_alive():
                    t._thread.join(timeout=1.0)
                self.assertEqual(t.model_info["filename"], expected_filename)
                self.assertEqual(os.path.dirname(t.dest_path), t.dest_dir)

if __name__ == "__main__":
    unittest.main()
