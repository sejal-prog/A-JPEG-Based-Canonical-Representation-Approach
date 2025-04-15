# import numpy as np
# from PIL import Image
# import scipy.fftpack as fft
# from collections import defaultdict
# import os

# # Standard JPEG luminance quantization matrix (for Y channel)
# LUMINANCE_QUANTIZATION_MATRIX = np.array([
#     [16, 11, 10, 16, 24, 40, 51, 61],
#     [12, 12, 14, 19, 26, 58, 60, 55],
#     [14, 13, 16, 24, 40, 57, 69, 56],
#     [14, 17, 22, 29, 51, 87, 80, 62],
#     [18, 22, 37, 56, 68, 109, 103, 77],
#     [24, 35, 55, 64, 81, 104, 113, 92],
#     [49, 64, 78, 87, 103, 121, 120, 101],
#     [72, 92, 95, 98, 112, 100, 103, 99]
# ])

# # Standard JPEG chrominance quantization matrix (for Cb and Cr channels)
# CHROMINANCE_QUANTIZATION_MATRIX = np.array([
#     [17, 18, 24, 47, 99, 99, 99, 99],
#     [18, 21, 26, 66, 99, 99, 99, 99],
#     [24, 26, 56, 99, 99, 99, 99, 99],
#     [47, 66, 99, 99, 99, 99, 99, 99],
#     [99, 99, 99, 99, 99, 99, 99, 99],
#     [99, 99, 99, 99, 99, 99, 99, 99],
#     [99, 99, 99, 99, 99, 99, 99, 99],
#     [99, 99, 99, 99, 99, 99, 99, 99]
# ])

# class HuffmanNode:
#     def __init__(self, value=None, frequency=None):
#         self.value = value
#         self.frequency = frequency
#         self.left = None
#         self.right = None
#         self.code = ''

# class JPEGCompressor:
#     def __init__(self, quality=50, scan_method='zigzag'):
#         self.codes = {}
#         self.reverse_codes = {}
#         self.frequencies = {}
#         self.quality = quality
#         self.scan_method = scan_method  # 'zigzag' or 'horizontal'
#         # Adjust quantization matrices based on quality
#         self.luminance_quant_matrix = self.adjust_quantization_matrix(LUMINANCE_QUANTIZATION_MATRIX, quality)
#         self.chrominance_quant_matrix = self.adjust_quantization_matrix(CHROMINANCE_QUANTIZATION_MATRIX, quality)
    
#     def adjust_quantization_matrix(self, matrix, quality):
#         """Adjust quantization matrix based on quality factor (1-100)"""
#         if quality < 1:
#             quality = 1
#         if quality > 100:
#             quality = 100
            
#         if quality < 50:
#             # Standard JPEG scaling for quality < 50
#             scale_factor = 5000 / quality
#         else:
#             scale_factor = 200 - 2 * quality
            
#         # Apply scaling with proper rounding
#         adjusted_matrix = np.floor((matrix * scale_factor + 50) / 100)
#         adjusted_matrix[adjusted_matrix <= 0] = 1  # Ensure no zeros
        
#         # Cap maximum values to prevent extreme quantization
#         adjusted_matrix = np.minimum(adjusted_matrix, 255)
        
#         return adjusted_matrix

#     def read_image(self, path):
#         try:
#             image = Image.open(path)
#             image = image.convert('RGB')
#             # Pad image to be divisible by 8 for DCT blocks
#             width, height = image.size
#             new_width = width + (8 - width % 8) if width % 8 != 0 else width
#             new_height = height + (8 - height % 8) if height % 8 != 0 else height
            
#             if new_width != width or new_height != height:
#                 padded_image = Image.new('RGB', (new_width, new_height), (0, 0, 0))
#                 padded_image.paste(image, (0, 0))
#                 return np.array(padded_image), width, height
#             return np.array(image), width, height
#         except Exception as e:
#             print(f"Error reading image: {e}")
#             return None, None, None
    
#     def rgb_to_ycbcr(self, rgb_image):
#         # Standard RGB to YCbCr conversion
#         r = rgb_image[:, :, 0].astype(float)
#         g = rgb_image[:, :, 1].astype(float)
#         b = rgb_image[:, :, 2].astype(float)
        
#         y = 0.299 * r + 0.587 * g + 0.114 * b
#         cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
#         cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
        
#         return np.stack([y, cb, cr], axis=2)

#     def chroma_subsample(self, ycbcr_image, mode='420'):
#         """Perform chroma subsampling (4:2:0, 4:2:2, or 4:4:4)"""
#         height, width, _ = ycbcr_image.shape
#         y = ycbcr_image[:, :, 0]
#         cb = ycbcr_image[:, :, 1]
#         cr = ycbcr_image[:, :, 2]
        
#         if mode == '420':  # 4:2:0 - Quarter resolution for chroma
#             cb_ss = cb[::2, ::2]
#             cr_ss = cr[::2, ::2]
#             # Resize back to original for processing consistency
#             cb_up = np.repeat(np.repeat(cb_ss, 2, axis=0), 2, axis=1)
#             cr_up = np.repeat(np.repeat(cr_ss, 2, axis=0), 2, axis=1)
#             # Ensure same dimensions
#             cb_up = cb_up[:height, :width]
#             cr_up = cr_up[:height, :width]
#             return np.stack([y, cb_up, cr_up], axis=2)
#         elif mode == '422':  # 4:2:2 - Half horizontal resolution for chroma
#             cb_ss = cb[:, ::2]
#             cr_ss = cr[:, ::2]
#             cb_up = np.repeat(cb_ss, 2, axis=1)[:height, :width]
#             cr_up = np.repeat(cr_ss, 2, axis=1)[:height, :width]
#             return np.stack([y, cb_up, cr_up], axis=2)
#         else:  # 4:4:4 - No subsampling
#             return ycbcr_image

#     def calculate_dct(self, image_array):
#         height, width, channels = image_array.shape
#         dct_image = np.zeros_like(image_array, dtype=float)

#         # Center values at zero before DCT (subtract 128 except for Y which is already centered)
#         centered = image_array.copy().astype(float)
#         centered[:, :, 1:] -= 128.0  # Only center Cb and Cr

#         for channel in range(channels):
#             for i in range(0, height, 8):
#                 for j in range(0, width, 8):
#                     # Extract 8x8 block
#                     block = centered[i:i+8, j:j+8, channel]
                    
#                     # Handle incomplete blocks at edges
#                     if block.shape != (8, 8):
#                         temp_block = np.zeros((8, 8))
#                         temp_block[:block.shape[0], :block.shape[1]] = block
#                         block = temp_block
                        
#                     # Apply 2D DCT
#                     dct_block = fft.dct(fft.dct(block, norm='ortho', axis=0), norm='ortho', axis=1)
                    
#                     # Store in result image
#                     if i+8 <= height and j+8 <= width:
#                         dct_image[i:i+8, j:j+8, channel] = dct_block
#                     else:
#                         dct_image[i:min(i+8, height), j:min(j+8, width), channel] = dct_block[:min(i+8, height)-i, :min(j+8, width)-j]
    
#         return dct_image

#     def quantize(self, dct_image):
#         height, width, channels = dct_image.shape
#         quantized_image = np.zeros_like(dct_image, dtype=int)

#         for i in range(0, height, 8):
#             for j in range(0, width, 8):
#                 for channel in range(channels):
#                     block = dct_image[i:i+8, j:j+8, channel]
                    
#                     # Handle edge blocks
#                     if block.shape != (8, 8):
#                         temp_block = np.zeros((8, 8))
#                         temp_block[:block.shape[0], :block.shape[1]] = block
#                         block = temp_block
                    
#                     # Use appropriate quantization matrix
#                     if channel == 0:  # Y channel
#                         q_matrix = self.luminance_quant_matrix
#                     else:  # Cb, Cr channels
#                         q_matrix = self.chrominance_quant_matrix
                    
#                     # Quantize
#                     quantized_block = np.round(block / q_matrix)
                    
#                     # Store result
#                     if i+8 <= height and j+8 <= width:
#                         quantized_image[i:i+8, j:j+8, channel] = quantized_block
#                     else:
#                         quantized_image[i:min(i+8, height), j:min(j+8, width), channel] = quantized_block[:min(i+8, height)-i, :min(j+8, width)-j]

#         return quantized_image

#     def zigzag_scan(self, block):
#         """Perform zigzag scanning on 8x8 block"""
#         rows, cols = block.shape
#         solution = []
        
#         for i in range(rows + cols - 1):
#             if i % 2 == 0:  # Even - go up
#                 for j in range(min(i, rows-1), max(0, i-cols+1)-1, -1):
#                     solution.append(block[j][i-j])
#             else:  # Odd - go down
#                 for j in range(max(0, i-cols+1), min(i, rows-1)+1):
#                     solution.append(block[j][i-j])
                    
#         return solution
    
#     def horizontal_scan(self, block):
#         """Perform horizontal scanning on 8x8 block (auto-regressive approach)"""
#         rows, cols = block.shape
#         solution = []
        
#         # Scan each row from left to right
#         for i in range(rows):
#             for j in range(cols):
#                 solution.append(block[i][j])
                
#         return solution
    
#     def scan_block(self, block):
#         """Scan block using the selected method"""
#         if self.scan_method == 'zigzag':
#             return self.zigzag_scan(block)
#         elif self.scan_method == 'horizontal':
#             return self.horizontal_scan(block)
#         else:
#             raise ValueError(f"Unknown scan method: {self.scan_method}")

#     def run_length_encode(self, scanned):
#         """Run-length encode the scanned coefficients"""
#         # Count trailing zeros
#         i = len(scanned) - 1
#         while i >= 0 and scanned[i] == 0:
#             i -= 1
        
#         # Truncate trailing zeros
#         scanned = scanned[:i+1]
        
#         # Run-length encoding for remaining coefficients
#         result = []
#         run_length = 0
        
#         for value in scanned:
#             if value == 0:
#                 run_length += 1
#             else:
#                 result.append((run_length, value))
#                 run_length = 0
                
#         # Add EOB marker if needed
#         if run_length > 0 or len(result) == 0:
#             result.append((run_length, 0))  # EOB
            
#         return result

#     def calculate_frequencies(self, quantized_image):
#         """Convert quantized image to RLE and calculate frequencies for Huffman coding"""
#         height, width, channels = quantized_image.shape
#         frequencies = defaultdict(int)
#         rle_data = []
#         sample_blocks = []  # Store a few sample blocks for display

#         for channel in range(channels):
#             for i in range(0, height, 8):
#                 for j in range(0, width, 8):
#                     block = quantized_image[i:min(i+8, height), j:min(j+8, width), channel]
                    
#                     # Handle edge blocks
#                     if block.shape != (8, 8):
#                         temp_block = np.zeros((8, 8), dtype=int)
#                         temp_block[:block.shape[0], :block.shape[1]] = block
#                         block = temp_block
                    
#                     # Store sample blocks (first few)
#                     if len(sample_blocks) < 5 and channel == 0:
#                         sample_blocks.append((block.copy(), (i, j)))
                    
#                     # Scan using selected method
#                     scanned = self.scan_block(block)
                    
#                     # Run-length encode
#                     rle = self.run_length_encode(scanned)
#                     rle_data.append((channel, i, j, rle))
                    
#                     # Count frequencies for Huffman coding
#                     for run, value in rle:
#                         # Create a unique symbol for the (run, value) pair
#                         symbol = (run, value)
#                         frequencies[symbol] += 1

#         return frequencies, rle_data, sample_blocks

#     def build_huffman_tree(self, frequencies):
#         nodes = []
#         for value, freq in frequencies.items():
#             node = HuffmanNode(value=value, frequency=freq)
#             nodes.append(node)

#         while len(nodes) > 1:
#             nodes = sorted(nodes, key=lambda x: x.frequency)
#             left = nodes.pop(0)
#             right = nodes.pop(0)
#             parent = HuffmanNode(frequency=left.frequency + right.frequency)
#             parent.left = left
#             parent.right = right
#             nodes.append(parent)

#         return nodes[0] if nodes else None

#     def generate_codes(self, root, code=""):
#         if root is None:
#             return
#         if root.value is not None:
#             self.codes[root.value] = code
#             self.reverse_codes[code] = root.value
#             return
#         self.generate_codes(root.left, code + "0")
#         self.generate_codes(root.right, code + "1")
    
#     def estimate_compressed_size(self, rle_data):
#         """Estimate size in bytes after Huffman coding of RLE data"""
#         if not self.codes:
#             return 0
            
#         total_bits = 0
#         for _, _, _, block_rle in rle_data:
#             for symbol in block_rle:
#                 if symbol in self.codes:
#                     total_bits += len(self.codes[symbol])
                    
#         # Add overhead for Huffman table (approximation)
#         huffman_table_size = sum(len(str(k)) + len(v) for k, v in self.codes.items())
#         total_bits += huffman_table_size * 8
        
#         # Convert to bytes (8 bits per byte)
#         total_bytes = (total_bits + 7) // 8
#         return total_bytes
    
#     def print_scanned_patterns(self, sample_blocks):
#         """Print the original and scanned patterns for a few sample blocks"""
#         print(f"\n----- Sample Blocks ({self.scan_method} scanning) -----")
#         for idx, (block, position) in enumerate(sample_blocks[:2]):  # Print first two samples
#             print(f"\nSample Block {idx+1} at position {position} - Original:")
#             print(block)
            
#             # Show scanned version
#             scanned = self.scan_block(block)
#             print(f"\nScanned ({self.scan_method}):")
            
#             # Print 8 elements per row
#             for i in range(0, len(scanned), 8):
#                 print(scanned[i:i+8])
                
#             # Show RLE
#             rle = self.run_length_encode(scanned)
#             print(f"\nRun-Length Encoded:")
#             print(rle)
    
#     def compress_image(self, image_path, chroma_subsampling='420'):
#         """Compress image using JPEG-like algorithm"""
#         print(f"\nReading image: {image_path}")
#         image_array, orig_width, orig_height = self.read_image(image_path)
#         if image_array is None:
#             return None
        
#         print("Converting image to YCbCr...")
#         ycbcr_image = self.rgb_to_ycbcr(image_array)
        
#         print(f"Applying chroma subsampling ({chroma_subsampling})...")
#         subsampled_image = self.chroma_subsample(ycbcr_image, mode=chroma_subsampling)
        
#         print("Applying DCT...")
#         dct_image = self.calculate_dct(subsampled_image)
        
#         print("Quantizing the DCT coefficients...")
#         quantized_image = self.quantize(dct_image)
        
#         print(f"Performing {self.scan_method} scanning and run-length encoding...")
#         frequencies, rle_data, sample_blocks = self.calculate_frequencies(quantized_image)
#         self.frequencies = frequencies
        
#         # Print sample blocks and their scanned patterns
#         self.print_scanned_patterns(sample_blocks)
        
#         print("Building Huffman tree...")
#         root = self.build_huffman_tree(frequencies)
#         if root:
#             print("Generating Huffman codes...")
#             self.generate_codes(root)
        
#         compression_info = {
#             'original_size': orig_width * orig_height * 3,  # RGB image size in bytes
#             'rle_data': rle_data,
#             'quantized': quantized_image,
#             'sample_blocks': sample_blocks
#         }
            
#         return compression_info

# def print_huffman_codes(encoder, num_codes=10):
#     print("\n----- Huffman Codes -----")
#     codes_list = list(encoder.codes.items())
#     if len(codes_list) > 0:
#         # Sort by frequency (most frequent first)
#         for i, (symbol, code) in enumerate(sorted(codes_list, key=lambda x: len(x[1]))[:num_codes]):
#             print(f"Symbol {symbol}: {code}")

# def compare_compression_methods(image_path, quality=50):
#     """Compare zigzag and horizontal scanning methods"""
#     print("\n==== COMPARING COMPRESSION METHODS ====")
    
#     # Zigzag scanning
#     print("\n*** ZIGZAG SCANNING METHOD ***")
#     zigzag_compressor = JPEGCompressor(quality=quality, scan_method='zigzag')
#     zigzag_info = zigzag_compressor.compress_image(image_path)
    
#     if zigzag_info:
#         zigzag_size = zigzag_compressor.estimate_compressed_size(zigzag_info['rle_data'])
#         print(f"\nZigzag scanning estimated compressed size: {zigzag_size} bytes")
#         print_huffman_codes(zigzag_compressor)
    
#     # Horizontal scanning
#     print("\n*** HORIZONTAL SCANNING METHOD ***")
#     horizontal_compressor = JPEGCompressor(quality=quality, scan_method='horizontal')
#     horizontal_info = horizontal_compressor.compress_image(image_path)
    
#     if horizontal_info:
#         horizontal_size = horizontal_compressor.estimate_compressed_size(horizontal_info['rle_data'])
#         print(f"\nHorizontal scanning estimated compressed size: {horizontal_size} bytes")
#         print_huffman_codes(horizontal_compressor)
    
#     # Compare results
#     if zigzag_info and horizontal_info:
#         original_size = zigzag_info['original_size']
#         print("\n==== COMPARISON SUMMARY ====")
#         print(f"Original size: {original_size} bytes")
#         print(f"Zigzag compression: {zigzag_size} bytes (ratio: {original_size/zigzag_size:.2f}x)")
#         print(f"Horizontal compression: {horizontal_size} bytes (ratio: {original_size/horizontal_size:.2f}x)")
#         print(f"Difference: {abs(zigzag_size - horizontal_size)} bytes, " +
#               f"{'Zigzag is better' if zigzag_size < horizontal_size else 'Horizontal is better'} " +
#               f"by {abs(zigzag_size - horizontal_size)/max(zigzag_size, horizontal_size)*100:.2f}%")

# def main():
#     image_path = "/home/sejal/Documents/CV Project/Canonical-Image-Compression/Folder1/0000.jpg"  # Update this path to your image
#     quality = 50  # Compression quality
    
#     if not os.path.exists(image_path):
#         print(f"Error: File not found at {image_path}")
#         return
    
#     # Compare zigzag and horizontal scanning methods
#     compare_compression_methods(image_path, quality)

# if __name__ == "__main__":
#     main()

import numpy as np
from PIL import Image
import scipy.fftpack as fft
from collections import defaultdict
import os
import matplotlib.pyplot as plt

# Standard JPEG luminance quantization matrix (for Y channel)
LUMINANCE_QUANTIZATION_MATRIX = np.array([
    [16, 11, 10, 16, 24, 40, 51, 61],
    [12, 12, 14, 19, 26, 58, 60, 55],
    [14, 13, 16, 24, 40, 57, 69, 56],
    [14, 17, 22, 29, 51, 87, 80, 62],
    [18, 22, 37, 56, 68, 109, 103, 77],
    [24, 35, 55, 64, 81, 104, 113, 92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103, 99]
])

# Standard JPEG chrominance quantization matrix (for Cb and Cr channels)
CHROMINANCE_QUANTIZATION_MATRIX = np.array([
    [17, 18, 24, 47, 99, 99, 99, 99],
    [18, 21, 26, 66, 99, 99, 99, 99],
    [24, 26, 56, 99, 99, 99, 99, 99],
    [47, 66, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99]
])

class HuffmanNode:
    def __init__(self, value=None, frequency=None):
        self.value = value
        self.frequency = frequency
        self.left = None
        self.right = None
        self.code = ''

class JPEGCompressor:
    def __init__(self, quality=50, scan_method='zigzag'):
        self.codes = {}
        self.reverse_codes = {}
        self.frequencies = {}
        self.quality = quality
        self.scan_method = scan_method  # 'zigzag' or 'horizontal'
        # Adjust quantization matrices based on quality
        self.luminance_quant_matrix = self.adjust_quantization_matrix(LUMINANCE_QUANTIZATION_MATRIX, quality)
        self.chrominance_quant_matrix = self.adjust_quantization_matrix(CHROMINANCE_QUANTIZATION_MATRIX, quality)
    
    def adjust_quantization_matrix(self, matrix, quality):
        """Adjust quantization matrix based on quality factor (1-100)"""
        if quality < 1:
            quality = 1
        if quality > 100:
            quality = 100
            
        if quality < 50:
            # Standard JPEG scaling for quality < 50
            scale_factor = 5000 / quality
        else:
            scale_factor = 200 - 2 * quality
            
        # Apply scaling with proper rounding
        adjusted_matrix = np.floor((matrix * scale_factor + 50) / 100)
        adjusted_matrix[adjusted_matrix <= 0] = 1  # Ensure no zeros
        
        # Cap maximum values to prevent extreme quantization
        adjusted_matrix = np.minimum(adjusted_matrix, 255)
        
        return adjusted_matrix

    def read_image(self, path):
        try:
            image = Image.open(path)
            image = image.convert('RGB')
            # Pad image to be divisible by 8 for DCT blocks
            width, height = image.size
            new_width = width + (8 - width % 8) if width % 8 != 0 else width
            new_height = height + (8 - height % 8) if height % 8 != 0 else height
            
            if new_width != width or new_height != height:
                padded_image = Image.new('RGB', (new_width, new_height), (0, 0, 0))
                padded_image.paste(image, (0, 0))
                return np.array(padded_image), width, height
            return np.array(image), width, height
        except Exception as e:
            print(f"Error reading image: {e}")
            return None, None, None
    
    def rgb_to_ycbcr(self, rgb_image):
        # Standard RGB to YCbCr conversion
        r = rgb_image[:, :, 0].astype(float)
        g = rgb_image[:, :, 1].astype(float)
        b = rgb_image[:, :, 2].astype(float)
        
        y = 0.299 * r + 0.587 * g + 0.114 * b
        cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
        cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
        
        return np.stack([y, cb, cr], axis=2)
    
    def ycbcr_to_rgb(self, ycbcr_image):
        # Convert YCbCr back to RGB using standard formula
        y = ycbcr_image[:, :, 0].astype(float)
        cb = ycbcr_image[:, :, 1].astype(float)
        cr = ycbcr_image[:, :, 2].astype(float)
        
        r = y + 1.402 * (cr - 128)
        g = y - 0.344136 * (cb - 128) - 0.714136 * (cr - 128)
        b = y + 1.772 * (cb - 128)
        
        # Clip values to valid range
        r = np.clip(r, 0, 255).astype(np.uint8)
        g = np.clip(g, 0, 255).astype(np.uint8)
        b = np.clip(b, 0, 255).astype(np.uint8)
        
        return np.stack([r, g, b], axis=2)

    def chroma_subsample(self, ycbcr_image, mode='420'):
        """Perform chroma subsampling (4:2:0, 4:2:2, or 4:4:4)"""
        height, width, _ = ycbcr_image.shape
        y = ycbcr_image[:, :, 0]
        cb = ycbcr_image[:, :, 1]
        cr = ycbcr_image[:, :, 2]
        
        if mode == '420':  # 4:2:0 - Quarter resolution for chroma
            cb_ss = cb[::2, ::2]
            cr_ss = cr[::2, ::2]
            # Resize back to original for processing consistency
            cb_up = np.repeat(np.repeat(cb_ss, 2, axis=0), 2, axis=1)
            cr_up = np.repeat(np.repeat(cr_ss, 2, axis=0), 2, axis=1)
            # Ensure same dimensions
            cb_up = cb_up[:height, :width]
            cr_up = cr_up[:height, :width]
            return np.stack([y, cb_up, cr_up], axis=2)
        elif mode == '422':  # 4:2:2 - Half horizontal resolution for chroma
            cb_ss = cb[:, ::2]
            cr_ss = cr[:, ::2]
            cb_up = np.repeat(cb_ss, 2, axis=1)[:height, :width]
            cr_up = np.repeat(cr_ss, 2, axis=1)[:height, :width]
            return np.stack([y, cb_up, cr_up], axis=2)
        else:  # 4:4:4 - No subsampling
            return ycbcr_image

    def calculate_dct(self, image_array):
        height, width, channels = image_array.shape
        dct_image = np.zeros_like(image_array, dtype=float)

        # Center values at zero before DCT (subtract 128 except for Y which is already centered)
        centered = image_array.copy().astype(float)
        centered[:, :, 1:] -= 128.0  # Only center Cb and Cr

        for channel in range(channels):
            for i in range(0, height, 8):
                for j in range(0, width, 8):
                    # Extract 8x8 block
                    block = centered[i:i+8, j:j+8, channel]
                    
                    # Handle incomplete blocks at edges
                    if block.shape != (8, 8):
                        temp_block = np.zeros((8, 8))
                        temp_block[:block.shape[0], :block.shape[1]] = block
                        block = temp_block
                        
                    # Apply 2D DCT
                    dct_block = fft.dct(fft.dct(block, norm='ortho', axis=0), norm='ortho', axis=1)
                    
                    # Store in result image
                    if i+8 <= height and j+8 <= width:
                        dct_image[i:i+8, j:j+8, channel] = dct_block
                    else:
                        dct_image[i:min(i+8, height), j:min(j+8, width), channel] = dct_block[:min(i+8, height)-i, :min(j+8, width)-j]
    
        return dct_image

    def quantize(self, dct_image):
        height, width, channels = dct_image.shape
        quantized_image = np.zeros_like(dct_image, dtype=int)

        for i in range(0, height, 8):
            for j in range(0, width, 8):
                for channel in range(channels):
                    block = dct_image[i:i+8, j:j+8, channel]
                    
                    # Handle edge blocks
                    if block.shape != (8, 8):
                        temp_block = np.zeros((8, 8))
                        temp_block[:block.shape[0], :block.shape[1]] = block
                        block = temp_block
                    
                    # Use appropriate quantization matrix
                    if channel == 0:  # Y channel
                        q_matrix = self.luminance_quant_matrix
                    else:  # Cb, Cr channels
                        q_matrix = self.chrominance_quant_matrix
                    
                    # Quantize
                    quantized_block = np.round(block / q_matrix)
                    
                    # Store result
                    if i+8 <= height and j+8 <= width:
                        quantized_image[i:i+8, j:j+8, channel] = quantized_block
                    else:
                        quantized_image[i:min(i+8, height), j:min(j+8, width), channel] = quantized_block[:min(i+8, height)-i, :min(j+8, width)-j]

        return quantized_image
    
    def dequantize(self, quantized_image):
        """Reverse the quantization process"""
        height, width, channels = quantized_image.shape
        dequantized_image = np.zeros_like(quantized_image, dtype=float)

        for i in range(0, height, 8):
            for j in range(0, width, 8):
                for channel in range(channels):
                    block = quantized_image[i:i+8, j:j+8, channel]
                    
                    # Handle edge blocks
                    if block.shape != (8, 8):
                        temp_block = np.zeros((8, 8))
                        temp_block[:block.shape[0], :block.shape[1]] = block
                        block = temp_block
                    
                    # Use appropriate quantization matrix
                    if channel == 0:  # Y channel
                        q_matrix = self.luminance_quant_matrix
                    else:  # Cb, Cr channels
                        q_matrix = self.chrominance_quant_matrix
                    
                    # Dequantize
                    dequantized_block = block * q_matrix
                    
                    # Store result
                    if i+8 <= height and j+8 <= width:
                        dequantized_image[i:i+8, j:j+8, channel] = dequantized_block
                    else:
                        dequantized_image[i:min(i+8, height), j:min(j+8, width), channel] = dequantized_block[:min(i+8, height)-i, :min(j+8, width)-j]

        return dequantized_image
    
    def inverse_dct(self, dequantized_image):
        """Apply inverse DCT to recover the spatial domain image"""
        height, width, channels = dequantized_image.shape
        idct_image = np.zeros_like(dequantized_image)

        for channel in range(channels):
            for i in range(0, height, 8):
                for j in range(0, width, 8):
                    # Extract 8x8 block
                    block = dequantized_image[i:i+8, j:j+8, channel]
                    
                    # Handle incomplete blocks at edges
                    if block.shape != (8, 8):
                        temp_block = np.zeros((8, 8))
                        temp_block[:block.shape[0], :block.shape[1]] = block
                        block = temp_block
                        
                    # Apply 2D inverse DCT
                    idct_block = fft.idct(fft.idct(block, norm='ortho', axis=0), norm='ortho', axis=1)
                    
                    # Store in result image
                    if i+8 <= height and j+8 <= width:
                        idct_image[i:i+8, j:j+8, channel] = idct_block
                    else:
                        idct_image[i:min(i+8, height), j:min(j+8, width), channel] = idct_block[:min(i+8, height)-i, :min(j+8, width)-j]
    
        # Undo centering (add 128 back to Cb and Cr)
        idct_image[:, :, 1:] += 128.0
        
        return idct_image

    def zigzag_scan(self, block):
        """Perform zigzag scanning on 8x8 block"""
        rows, cols = block.shape
        solution = []
        
        for i in range(rows + cols - 1):
            if i % 2 == 0:  # Even - go up
                for j in range(min(i, rows-1), max(0, i-cols+1)-1, -1):
                    solution.append(block[j][i-j])
            else:  # Odd - go down
                for j in range(max(0, i-cols+1), min(i, rows-1)+1):
                    solution.append(block[j][i-j])
                    
        return solution
    
    def inverse_zigzag(self, zigzag):
        """Convert zigzag array back to 8x8 block"""
        block = np.zeros((8, 8), dtype=int)
        rows, cols = 8, 8
        index = 0
        
        for i in range(rows + cols - 1):
            if i % 2 == 0:  # Even - go up
                for j in range(min(i, rows-1), max(0, i-cols+1)-1, -1):
                    if index < len(zigzag):
                        block[j][i-j] = zigzag[index]
                        index += 1
            else:  # Odd - go down
                for j in range(max(0, i-cols+1), min(i, rows-1)+1):
                    if index < len(zigzag):
                        block[j][i-j] = zigzag[index]
                        index += 1
        
        return block
    
    def horizontal_scan(self, block):
        """Perform horizontal scanning on 8x8 block"""
        rows, cols = block.shape
        solution = []
        
        # Scan each row from left to right
        for i in range(rows):
            for j in range(cols):
                solution.append(block[i][j])
                
        return solution
    
    def inverse_horizontal_scan(self, scanned):
        """Convert horizontal scanned array back to 8x8 block"""
        block = np.zeros((8, 8), dtype=int)
        index = 0
        
        for i in range(8):
            for j in range(8):
                if index < len(scanned):
                    block[i][j] = scanned[index]
                    index += 1
        
        return block
    
    def scan_block(self, block):
        """Scan block using the selected method"""
        if self.scan_method == 'zigzag':
            return self.zigzag_scan(block)
        elif self.scan_method == 'horizontal':
            return self.horizontal_scan(block)
        else:
            raise ValueError(f"Unknown scan method: {self.scan_method}")
    
    def inverse_scan(self, scanned):
        """Inverse scan based on the selected method"""
        if self.scan_method == 'zigzag':
            return self.inverse_zigzag(scanned)
        elif self.scan_method == 'horizontal':
            return self.inverse_horizontal_scan(scanned)
        else:
            raise ValueError(f"Unknown scan method: {self.scan_method}")

    def run_length_encode(self, scanned):
        """Run-length encode the scanned coefficients"""
        # Count trailing zeros
        i = len(scanned) - 1
        while i >= 0 and scanned[i] == 0:
            i -= 1
        
        # Truncate trailing zeros
        scanned = scanned[:i+1]
        
        # Run-length encoding for remaining coefficients
        result = []
        run_length = 0
        
        for value in scanned:
            if value == 0:
                run_length += 1
            else:
                result.append((run_length, value))
                run_length = 0
                
        # Add EOB marker if needed
        if run_length > 0 or len(result) == 0:
            result.append((run_length, 0))  # EOB
            
        return result
    
    def run_length_decode(self, rle):
        """Decode run-length encoded data back to scanned array"""
        scanned = []
        for run, value in rle:
            scanned.extend([0] * run)
            if value != 0:  # Skip EOB marker
                scanned.append(value)
        
        # Pad with zeros to make a complete 64-element array
        scanned.extend([0] * (64 - len(scanned)))
        return scanned

    def calculate_frequencies(self, quantized_image):
        """Convert quantized image to RLE and calculate frequencies for Huffman coding"""
        height, width, channels = quantized_image.shape
        frequencies = defaultdict(int)
        rle_data = []
        sample_blocks = []  # Store a few sample blocks for display

        for channel in range(channels):
            for i in range(0, height, 8):
                for j in range(0, width, 8):
                    block = quantized_image[i:min(i+8, height), j:min(j+8, width), channel]
                    
                    # Handle edge blocks
                    if block.shape != (8, 8):
                        temp_block = np.zeros((8, 8), dtype=int)
                        temp_block[:block.shape[0], :block.shape[1]] = block
                        block = temp_block
                    
                    # Store sample blocks (first few)
                    if len(sample_blocks) < 5 and channel == 0:
                        sample_blocks.append((block.copy(), (i, j)))
                    
                    # Scan using selected method
                    scanned = self.scan_block(block)
                    
                    # Run-length encode
                    rle = self.run_length_encode(scanned)
                    rle_data.append((channel, i, j, rle))
                    
                    # Count frequencies for Huffman coding
                    for run, value in rle:
                        # Create a unique symbol for the (run, value) pair
                        symbol = (run, value)
                        frequencies[symbol] += 1

        return frequencies, rle_data, sample_blocks

    def build_huffman_tree(self, frequencies):
        nodes = []
        for value, freq in frequencies.items():
            node = HuffmanNode(value=value, frequency=freq)
            nodes.append(node)

        while len(nodes) > 1:
            nodes = sorted(nodes, key=lambda x: x.frequency)
            left = nodes.pop(0)
            right = nodes.pop(0)
            parent = HuffmanNode(frequency=left.frequency + right.frequency)
            parent.left = left
            parent.right = right
            nodes.append(parent)

        return nodes[0] if nodes else None

    def generate_codes(self, root, code=""):
        if root is None:
            return
        if root.value is not None:
            self.codes[root.value] = code
            self.reverse_codes[code] = root.value
            return
        self.generate_codes(root.left, code + "0")
        self.generate_codes(root.right, code + "1")
    
    def estimate_compressed_size(self, rle_data):
        """Estimate size in bytes after Huffman coding of RLE data"""
        if not self.codes:
            return 0
            
        total_bits = 0
        for _, _, _, block_rle in rle_data:
            for symbol in block_rle:
                if symbol in self.codes:
                    total_bits += len(self.codes[symbol])
                    
        # Add overhead for Huffman table (approximation)
        huffman_table_size = sum(len(str(k)) + len(v) for k, v in self.codes.items())
        total_bits += huffman_table_size * 8
        
        # Convert to bytes (8 bits per byte)
        total_bytes = (total_bits + 7) // 8
        return total_bytes
    
    def print_scanned_patterns(self, sample_blocks):
        """Print the original and scanned patterns for a few sample blocks"""
        print(f"\n----- Sample Blocks ({self.scan_method} scanning) -----")
        for idx, (block, position) in enumerate(sample_blocks[:2]):  # Print first two samples
            print(f"\nSample Block {idx+1} at position {position} - Original:")
            print(block)
            
            # Show scanned version
            scanned = self.scan_block(block)
            print(f"\nScanned ({self.scan_method}):")
            
            # Print 8 elements per row
            for i in range(0, len(scanned), 8):
                print(scanned[i:i+8])
                
            # Show RLE
            rle = self.run_length_encode(scanned)
            print(f"\nRun-Length Encoded:")
            print(rle)
    
    def decompress_image(self, rle_data, shape, orig_width=None, orig_height=None):
        """Reconstruct image from RLE encoded data"""
        height, width, channels = shape
        reconstructed_quantized = np.zeros(shape, dtype=int)

        # Decode RLE data back to quantized DCT coefficients
        for channel, i, j, rle in rle_data:
            # Run-length decode
            scanned = self.run_length_decode(rle)
            
            # Inverse scan
            block = self.inverse_scan(scanned)
            
            # Store in reconstructed quantized image
            if i+8 <= height and j+8 <= width:
                reconstructed_quantized[i:i+8, j:j+8, channel] = block
            else:
                reconstructed_quantized[i:min(i+8, height), j:min(j+8, width), channel] = block[:min(i+8, height)-i, :min(j+8, width)-j]
        
        # Dequantize
        dequantized_image = self.dequantize(reconstructed_quantized)
        
        # Inverse DCT
        idct_image = self.inverse_dct(dequantized_image)
        
        # Convert back to RGB
        reconstructed_ycbcr = idct_image
        reconstructed_rgb = self.ycbcr_to_rgb(reconstructed_ycbcr)
        
        # Crop to original dimensions if needed
        if orig_width and orig_height:
            reconstructed_rgb = reconstructed_rgb[:orig_height, :orig_width]
            
        return reconstructed_rgb
    
    def compress_image(self, image_path, chroma_subsampling='420'):
        """Compress image using JPEG-like algorithm"""
        print(f"\nReading image: {image_path}")
        image_array, orig_width, orig_height = self.read_image(image_path)
        if image_array is None:
            return None
        
        print("Converting image to YCbCr...")
        ycbcr_image = self.rgb_to_ycbcr(image_array)
        
        print(f"Applying chroma subsampling ({chroma_subsampling})...")
        subsampled_image = self.chroma_subsample(ycbcr_image, mode=chroma_subsampling)
        
        print("Applying DCT...")
        dct_image = self.calculate_dct(subsampled_image)
        
        print("Quantizing the DCT coefficients...")
        quantized_image = self.quantize(dct_image)
        
        print(f"Performing {self.scan_method} scanning and run-length encoding...")
        frequencies, rle_data, sample_blocks = self.calculate_frequencies(quantized_image)
        self.frequencies = frequencies
        
        # Print sample blocks and their scanned patterns
        self.print_scanned_patterns(sample_blocks)
        
        print("Building Huffman tree...")
        root = self.build_huffman_tree(frequencies)
        if root:
            print("Generating Huffman codes...")
            self.generate_codes(root)
        
        print("Reconstructing image from compressed data...")
        # Reconstruct the image to visualize the compression effects
        reconstructed_rgb = self.decompress_image(rle_data, subsampled_image.shape, orig_width, orig_height)
        
        compression_info = {
            'original_size': orig_width * orig_height * 3,  # RGB image size in bytes
            'original_image': image_array[:orig_height, :orig_width],
            'reconstructed_image': reconstructed_rgb,
            'rle_data': rle_data,
            'quantized': quantized_image,
            'sample_blocks': sample_blocks,
            'shape': subsampled_image.shape,
            'orig_width': orig_width,
            'orig_height': orig_height
        }
            
        return compression_info

def print_huffman_codes(encoder, num_codes=10):
    print("\n----- Huffman Codes -----")
    codes_list = list(encoder.codes.items())
    if len(codes_list) > 0:
        # Sort by frequency (most frequent first)
        for i, (symbol, code) in enumerate(sorted(codes_list, key=lambda x: len(x[1]))[:num_codes]):
            print(f"Symbol {symbol}: {code}")

def save_reconstructed_image(image_array, output_path):
    """Save reconstructed image to file"""
    # Ensure values are in valid range
    img_array = np.clip(image_array, 0, 255).astype(np.uint8)
    img = Image.fromarray(img_array)
    img.save(output_path)
    print(f"Saved image to {output_path}")

def compare_with_original(original, reconstructed, quality, scan_method, output_dir="output"):
    """Display original and reconstructed images side by side"""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Calculate PSNR (Peak Signal-to-Noise Ratio)
    mse = np.mean((original - reconstructed) ** 2)
    if mse == 0:
        psnr = float('inf')
    else:
        max_pixel = 255.0
        psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    
    # Plot images side by side
    plt.figure(figsize=(12, 6))
    
    plt.subplot(1, 2, 1)
    plt.title("Original Image")
    plt.imshow(original)
    plt.axis('off')
    
    plt.subplot(1, 2, 2)
    plt.title(f"Reconstructed (Q={quality}, {scan_method})\nPSNR: {psnr:.2f} dB")
    plt.imshow(reconstructed)
    plt.axis('off')
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/comparison_q{quality}_{scan_method}.png")
    plt.close()
    
    # Save the reconstructed image
    save_reconstructed_image(reconstructed, f"{output_dir}/reconstructed_q{quality}_{scan_method}.jpg")
    
    return psnr

def compare_compression_methods(image_path, quality, chroma_subsampling='420', output_dir="output"):
    """Compare zigzag and horizontal scanning methods with reconstruction"""
    print("\n==== COMPARING COMPRESSION METHODS WITH RECONSTRUCTION ====")
    results = {}
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Zigzag scanning
    print("\n*** ZIGZAG SCANNING METHOD ***")
    zigzag_compressor = JPEGCompressor(quality=quality, scan_method='zigzag')
    zigzag_info = zigzag_compressor.compress_image(image_path, chroma_subsampling)
    
    if zigzag_info:
        zigzag_size = zigzag_compressor.estimate_compressed_size(zigzag_info['rle_data'])
        print(f"\nZigzag scanning estimated compressed size: {zigzag_size} bytes")
        print_huffman_codes(zigzag_compressor)
        
        # Compare with original
        psnr_zigzag = compare_with_original(
            zigzag_info['original_image'], 
            zigzag_info['reconstructed_image'],
            quality, 
            'zigzag',
            output_dir
        )
        results['zigzag'] = {
            'size': zigzag_size,
            'psnr': psnr_zigzag
        }
    
    # Horizontal scanning
    print("\n*** HORIZONTAL SCANNING METHOD ***")
    horizontal_compressor = JPEGCompressor(quality=quality, scan_method='horizontal')
    horizontal_info = horizontal_compressor.compress_image(image_path, chroma_subsampling)
    
    if horizontal_info:
        horizontal_size = horizontal_compressor.estimate_compressed_size(horizontal_info['rle_data'])
        print(f"\nHorizontal scanning estimated compressed size: {horizontal_size} bytes")
        print_huffman_codes(horizontal_compressor)
        
        # Compare with original
        psnr_horizontal = compare_with_original(
            horizontal_info['original_image'], 
            horizontal_info['reconstructed_image'],
            quality, 
            'horizontal',
            output_dir
        )
        results['horizontal'] = {
            'size': horizontal_size,
            'psnr': psnr_horizontal
        }
    
    # Compare methods
    if 'zigzag' in results and 'horizontal' in results:
        zigzag_result = results['zigzag']
        horizontal_result = results['horizontal']
        
        # Create comparison plot
        plt.figure(figsize=(10, 6))
        methods = ['Zigzag', 'Horizontal']
        sizes = [zigzag_result['size'], horizontal_result['size']]
        psnrs = [zigzag_result['psnr'], horizontal_result['psnr']]
        
        # Plot size comparison
        plt.subplot(1, 2, 1)
        plt.bar(methods, sizes, color=['blue', 'orange'])
        plt.title('Compressed Size (bytes)')
        plt.ylabel('Bytes')
        
        # Plot PSNR comparison
        plt.subplot(1, 2, 2)
        plt.bar(methods, psnrs, color=['blue', 'orange'])
        plt.title('Image Quality (PSNR)')
        plt.ylabel('PSNR (dB)')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/method_comparison_q{quality}.png")
        plt.close()
        
        print("\n----- Compression Method Comparison -----")
        print(f"Zigzag scanning:    Size: {zigzag_result['size']} bytes, PSNR: {zigzag_result['psnr']:.2f} dB")
        print(f"Horizontal scanning: Size: {horizontal_result['size']} bytes, PSNR: {horizontal_result['psnr']:.2f} dB")
        
        # Determine which method is better
        if zigzag_result['size'] < horizontal_result['size']:
            size_winner = "Zigzag"
        elif zigzag_result['size'] > horizontal_result['size']:
            size_winner = "Horizontal"
        else:
            size_winner = "Tie"
            
        if zigzag_result['psnr'] > horizontal_result['psnr']:
            quality_winner = "Zigzag"
        elif zigzag_result['psnr'] < horizontal_result['psnr']:
            quality_winner = "Horizontal"
        else:
            quality_winner = "Tie"
            
        print(f"\nBetter compression: {size_winner}")
        print(f"Better quality: {quality_winner}")
    
    return results

def visualize_quantization_effect(image_path, qualities=(10, 50, 90), scan_method='zigzag', output_dir="output"):
    """Visualize the effect of different quality factors on image compression"""
    print("\n==== VISUALIZING QUANTIZATION EFFECT ====")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    original_image = None
    
    # Process with different quality factors
    for quality in qualities:
        print(f"\n*** Processing with Quality = {quality} ***")
        compressor = JPEGCompressor(quality=quality, scan_method=scan_method)
        compression_info = compressor.compress_image(image_path)
        
        if compression_info:
            # Store original image (only once)
            if original_image is None:
                original_image = compression_info['original_image']
                
            compressed_size = compressor.estimate_compressed_size(compression_info['rle_data'])
            reconstructed = compression_info['reconstructed_image']
            
            # Calculate PSNR
            mse = np.mean((original_image - reconstructed) ** 2)
            if mse == 0:
                psnr = float('inf')
            else:
                max_pixel = 255.0
                psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
                
            # Save reconstructed image
            output_path = f"{output_dir}/quality_{quality}_{scan_method}.jpg"
            save_reconstructed_image(reconstructed, output_path)
            
            # Store results
            results.append({
                'quality': quality,
                'size': compressed_size,
                'psnr': psnr,
                'image': reconstructed
            })
    
    # Create comparison figure
    if results and original_image is not None:
        # Plot all images side by side
        n_images = len(results) + 1  # +1 for original
        plt.figure(figsize=(4*n_images, 8))
        
        # Original image
        plt.subplot(2, n_images, 1)
        plt.title("Original Image")
        plt.imshow(original_image)
        plt.axis('off')
        
        # Reconstructed images
        for i, result in enumerate(results):
            plt.subplot(2, n_images, i+2)
            plt.title(f"Quality = {result['quality']}\nPSNR: {result['psnr']:.2f} dB\nSize: {result['size']} bytes")
            plt.imshow(result['image'])
            plt.axis('off')
            
        # Plot quality vs size and PSNR
        qualities = [r['quality'] for r in results]
        sizes = [r['size'] for r in results]
        psnrs = [r['psnr'] for r in results]
        
        # Size plot
        plt.subplot(2, 2, 3)
        plt.plot(qualities, sizes, 'o-', color='blue')
        plt.title('Quality vs Compressed Size')
        plt.xlabel('Quality Factor')
        plt.ylabel('Size (bytes)')
        
        # PSNR plot
        plt.subplot(2, 2, 4)
        plt.plot(qualities, psnrs, 'o-', color='green')
        plt.title('Quality vs Image Quality (PSNR)')
        plt.xlabel('Quality Factor')
        plt.ylabel('PSNR (dB)')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/quality_comparison_{scan_method}.png")
        plt.close()
        
        print("\n----- Quality Comparison -----")
        for result in results:
            print(f"Quality {result['quality']}: Size: {result['size']} bytes, PSNR: {result['psnr']:.2f} dB")

def analyze_quantization_matrices(quality_levels=(10, 50, 90)):
    """Visualize the quantization matrices at different quality levels"""
    print("\n==== ANALYZING QUANTIZATION MATRICES ====")
    
    fig, axs = plt.subplots(len(quality_levels), 2, figsize=(12, 4*len(quality_levels)))
    
    for i, quality in enumerate(quality_levels):
        compressor = JPEGCompressor(quality=quality)
        
        # Luminance matrix
        im1 = axs[i, 0].imshow(compressor.luminance_quant_matrix, cmap='viridis')
        axs[i, 0].set_title(f'Luminance Q-Matrix (Quality={quality})')
        plt.colorbar(im1, ax=axs[i, 0])
        
        # Chrominance matrix
        im2 = axs[i, 1].imshow(compressor.chrominance_quant_matrix, cmap='viridis')
        axs[i, 1].set_title(f'Chrominance Q-Matrix (Quality={quality})')
        plt.colorbar(im2, ax=axs[i, 1])
        
        # Print max value
        max_luma = np.max(compressor.luminance_quant_matrix)
        max_chroma = np.max(compressor.chrominance_quant_matrix)
        print(f"Quality {quality}: Max Luminance Q value = {max_luma}, Max Chrominance Q value = {max_chroma}")
    
    plt.tight_layout()
    plt.savefig("output/quantization_matrices.png")
    plt.close()

def visualize_dct_blocks(image_path, quality=50, output_dir="output"):
    """Visualize the DCT coefficients of sample blocks"""
    print("\n==== VISUALIZING DCT COEFFICIENTS ====")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize compressor
    compressor = JPEGCompressor(quality=quality)
    
    # Read and process image
    image_array, _, _ = compressor.read_image(image_path)
    if image_array is None:
        return
    
    ycbcr_image = compressor.rgb_to_ycbcr(image_array)
    dct_image = compressor.calculate_dct(ycbcr_image)
    quantized_image = compressor.quantize(dct_image)
    
    # Extract sample blocks (Y channel)
    height, width, _ = ycbcr_image.shape
    sample_positions = [(100, 100), (200, 200)]  # Adjust based on image size
    
    for pos_idx, (y, x) in enumerate(sample_positions):
        if y < height-8 and x < width-8:
            # Get 8x8 block from different processing stages
            original_block = ycbcr_image[y:y+8, x:x+8, 0]  # Y channel
            dct_block = dct_image[y:y+8, x:x+8, 0]
            quantized_block = quantized_image[y:y+8, x:x+8, 0]
            
            # Plot the blocks
            plt.figure(figsize=(15, 5))
            
            # Original block
            plt.subplot(1, 3, 1)
            plt.imshow(original_block, cmap='gray')
            plt.title(f"Original Block at ({y},{x})")
            plt.colorbar()
            
            # DCT coefficients
            plt.subplot(1, 3, 2)
            im = plt.imshow(dct_block, cmap='seismic', vmin=-100, vmax=100)
            plt.title("DCT Coefficients")
            plt.colorbar(im)
            
            # Quantized DCT coefficients
            plt.subplot(1, 3, 3)
            im = plt.imshow(quantized_block, cmap='seismic', vmin=-10, vmax=10)
            plt.title(f"Quantized DCT (Q={quality})")
            plt.colorbar(im)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/dct_block_{pos_idx}.png")
            plt.close()
            
            # Log coefficient statistics
            nonzero_count = np.count_nonzero(quantized_block)
            total_elements = 64  # 8x8 block
            zero_percentage = (1 - nonzero_count/total_elements) * 100
            
            print(f"\nBlock at position ({y},{x}):")
            print(f"  Non-zero coefficients after quantization: {nonzero_count}/{total_elements} ({zero_percentage:.1f}% are zeros)")
            
            # Show scanned sequence
            if compressor.scan_method == 'zigzag':
                scanned = compressor.zigzag_scan(quantized_block)
            else:
                scanned = compressor.horizontal_scan(quantized_block)
                
            print(f"  {compressor.scan_method.capitalize()} scanned sequence:")
            print("  " + str(scanned))
            
            # Show RLE result
            rle = compressor.run_length_encode(scanned)
            print(f"  Run-Length Encoded: {rle}")
            print(f"  Compression in this block: {len(rle)} symbols instead of 64")

def main():
    """Main program entry point"""
    # Set default parameters
    image_path = "/home/sejal/Documents/CV Project/Canonical-Image-Compression/Folder1/0000.jpg"  # Change this to your image path
    quality = 50  # Default quality
    scan_method = 'horizontal'  # Default scanning method
    chroma_subsampling = '420'  # Default chroma subsampling
    output_dir = "output"
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='JPEG-like Image Compression')
    parser.add_argument('--image', type=str, help='Path to input image')
    parser.add_argument('--quality', type=int, help='Compression quality (1-100)')
    parser.add_argument('--scan', type=str, choices=['zigzag', 'horizontal'], help='Scanning method')
    parser.add_argument('--chroma', type=str, choices=['420', '422', '444'], help='Chroma subsampling')
    parser.add_argument('--output', type=str, help='Output directory')
    
    args = parser.parse_args()
    
    if args.image:
        image_path = args.image
    if args.quality:
        quality = args.quality
    if args.scan:
        scan_method = args.scan
    if args.chroma:
        chroma_subsampling = args.chroma
    if args.output:
        output_dir = args.output
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Processing image: {image_path}")
    print(f"Quality: {quality}")
    print(f"Scan method: {scan_method}")
    print(f"Chroma subsampling: {chroma_subsampling}")
    print(f"Output directory: {output_dir}")
    
    # Run compression analysis
    compare_compression_methods(image_path, quality, chroma_subsampling, output_dir)
    
    # Visualize quantization effect with different quality levels
    visualize_quantization_effect(image_path, qualities=(10, 50, 90), scan_method=scan_method, output_dir=output_dir)
    
    # Analyze quantization matrices
    analyze_quantization_matrices(quality_levels=(10, 50, 90))
    
    # Visualize DCT blocks
    visualize_dct_blocks(image_path, quality=quality, output_dir=output_dir)
    
    print("\nCompression analysis complete. Results saved to:", output_dir)

if __name__ == "__main__":
    main()