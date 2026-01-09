# A JPEG Based Canonical Representation Approach

A Python toolkit for analyzing JPEG image compression, extracting DCT coefficients, and studying Huffman coding and quantization.

## Overview

This project provides tools to parse JPEG internals and analyze compression behavior. Useful for research in computer vision, image compression, and machine learning applications.

## Features

- Extract DCT coefficients from JPEG images
- Parse and manipulate Huffman coding tables
- Analyze quantization and compression quality
- Calculate compression loss metrics (MSE, PSNR, SSIM)
- Export codebooks and analysis results to CSV/JSON

## Project Structure

```
├── DCT_JPG.py              # DCT extraction and transformation
├── compression.py          # Compression and quantization
├── huffman_parser.py       # Parse Huffman tables
├── huffmancode.py          # Huffman encoding/decoding
├── quant.py                # Quantization operations
├── loss_calculation.py     # Loss metrics calculation
├── script.py               # Main execution script
└── *.csv, *.json           # Data files and codebooks
```

## Installation

```bash
git clone https://github.com/sejal-prog/A-JPEG-Based-Canonical-Representation-Approach.git
cd A-JPEG-Based-Canonical-Representation-Approach
pip install numpy pillow matplotlib
```

## Usage

Run the main script:
```bash
python script.py
```

Or use individual modules:
```python
from DCT_JPG import extract_dct_coefficients
from compression import quantize
from loss_calculation import calculate_psnr

# Extract DCT coefficients
coefficients = extract_dct_coefficients('image.jpg')

# Apply quantization
quantized = quantize(coefficients, quality_factor=75)

# Calculate quality metric
psnr = calculate_psnr(original, quantized)
```

## Requirements

- Python 3.7+
- numpy
- Pillow
- matplotlib

## Topics

Machine Learning • Computer Vision • Deep Learning • JPEG Compression • VQGAN-VAE

## Author

**Sejal** - [@sejal-prog](https://github.com/sejal-prog)

## License

MIT License
