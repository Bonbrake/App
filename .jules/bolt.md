## 2026-08-22 - Vectorized Pure-NumPy Sobel Gradient for PBR Maps
**Learning:** `scipy.ndimage.sobel` introduces external dependency requirements and extra call overhead for 2D image normal map generation. Standard 3x3 Sobel kernel convolution can be computed purely with NumPy `np.pad` and 2D slice subtraction (`dx` and `dy`), providing a fast and dependency-free gradient calculation.
**Action:** Replace `scipy.ndimage.sobel` calls with pure NumPy array slicing and padding when computing image gradients.
