

import os
import numpy as np
import pandas as pd
from PIL import Image
import scipy.fftpack as fft
from collections import defaultdict
import argparse
import time
import matplotlib.pyplot as plt
import json

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
    def __init__(self, quality=50):
        self.codes = {}
        self.reverse_codes = {}
        self.frequencies = {}
        self.quality = quality
        # Fixed to horizontal scan method
        self.scan_method = 'horizontal'
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
    
    def horizontal_scan(self, block):
        """Perform horizontal scanning on 8x8 block"""
        rows, cols = block.shape
        solution = []
        
        # Scan each row from left to right
        for i in range(rows):
            for j in range(cols):
                solution.append(block[i][j])
                
        return solution
    
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

    def calculate_frequencies(self, quantized_image):
        """Convert quantized image to RLE and calculate frequencies for Huffman coding"""
        height, width, channels = quantized_image.shape
        frequencies = defaultdict(int)
        rle_data = []

        for channel in range(channels):
            for i in range(0, height, 8):
                for j in range(0, width, 8):
                    block = quantized_image[i:min(i+8, height), j:min(j+8, width), channel]
                    
                    # Handle edge blocks
                    if block.shape != (8, 8):
                        temp_block = np.zeros((8, 8), dtype=int)
                        temp_block[:block.shape[0], :block.shape[1]] = block
                        block = temp_block
                    
                    # Scan using horizontal method
                    scanned = self.horizontal_scan(block)
                    
                    # Run-length encode
                    rle = self.run_length_encode(scanned)
                    rle_data.append((channel, i, j, rle))
                    
                    # Count frequencies for Huffman coding
                    for run, value in rle:
                        # Create a unique symbol for the (run, value) pair
                        symbol = (run, value)
                        frequencies[symbol] += 1

        return frequencies, rle_data

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

    def process_image(self, image_path, chroma_subsampling='420'):
        """Process a single image and return Huffman codes"""
        # Read image
        image_array, _, _ = self.read_image(image_path)
        if image_array is None:
            return None
        
        # Convert to YCbCr
        ycbcr_image = self.rgb_to_ycbcr(image_array)
        
        # Apply chroma subsampling
        subsampled_image = self.chroma_subsample(ycbcr_image, mode=chroma_subsampling)
        
        # Calculate DCT
        dct_image = self.calculate_dct(subsampled_image)
        
        # Quantize DCT coefficients
        quantized_image = self.quantize(dct_image)
        
        # Calculate frequencies and build Huffman tree
        frequencies, _ = self.calculate_frequencies(quantized_image)
        self.frequencies = frequencies
        
        # Reset codes for this image
        self.codes = {}
        self.reverse_codes = {}
        
        # Build Huffman tree and generate codes
        root = self.build_huffman_tree(frequencies)
        if root:
            self.generate_codes(root)
            
        return self.codes
    
def save_unified_huffman_dict(unified_dict, frequencies, output_file):
    """Save unified Huffman dictionary to a file and print top 10 codes by frequency"""
    # Create a combined dictionary with codes and frequencies
    result = {}
    for symbol_str, code in unified_dict.items():
        # Convert symbol_str back to tuple for frequency lookup
        run, value = map(int, symbol_str.split(','))
        symbol = (run, value)
        freq = frequencies.get(symbol, 0)
        result[symbol_str] = {
            "code": code, 
            "frequency": freq,
            "code_length": len(code)
        }
    
    # Save the complete dictionary to file
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    # Print top 10 codes by frequency
    print("\nTop 10 most frequent codes in unified dictionary:")
    sorted_codes = sorted(result.items(), key=lambda x: x[1]["frequency"], reverse=True)[:10]
    for i, (symbol, data) in enumerate(sorted_codes, 1):
        print(f"{i}. Symbol: {symbol} | Code: {data['code']} | Frequency: {data['frequency']}")
    
    return result


def process_folder(input_folder, output_json, quality=50, chroma_subsampling='420'):
    """Process all images in a folder and save Huffman codes to JSON"""
    # Create compressor
    compressor = JPEGCompressor(quality=quality)
    
    # Initialize global frequency counter
    global_frequencies = defaultdict(int)
    
    # Supported image formats
    image_extensions = ['.jpg', '.jpeg']
    # Find all image files in folder
    image_files = []
    for file in os.listdir(input_folder):
        file_lower = file.lower()
        if any(file_lower.endswith(ext) for ext in image_extensions):
            image_files.append(os.path.join(input_folder, file))
    
    # Dictionary to store per-image Huffman codes
    image_huffman_dict = {}
    # Dictionary for unified codes across all images
    unified_huffman_dict = {}
    
    for img_path in image_files:
        print(f"Processing {os.path.basename(img_path)}...")
        
        # Get Huffman codes for this image
        huffman_codes = compressor.process_image(img_path, chroma_subsampling)
        
        if huffman_codes:
            image_name = os.path.basename(img_path)
            
            # Convert tuple keys to string representation for JSON serialization
            image_codes = {}
            for symbol, code in huffman_codes.items():
                run, value = symbol
                # Create a string key from the tuple
                symbol_str = f"{run},{value}"
                image_codes[symbol_str] = code
                
                # Add to unified dictionary
                if symbol_str in unified_huffman_dict:
                    # If symbol already exists, use the shorter code
                    if len(code) < len(unified_huffman_dict[symbol_str]):
                        unified_huffman_dict[symbol_str] = code
                else:
                    unified_huffman_dict[symbol_str] = code
            
            # Store in per-image dictionary
            image_huffman_dict[image_name] = image_codes
    for symbol, freq in compressor.frequencies.items():
            global_frequencies[symbol] += freq
    
    # Create result dictionary with both per-image and unified dictionaries
    result = {
        "per_image_huffman_codes": image_huffman_dict,
        "unified_huffman_codes": unified_huffman_dict
    }
    unified_output = os.path.splitext(output_json)[0] + '_unified.json'
    unified_dict_with_stats = save_unified_huffman_dict(unified_huffman_dict, 
                                                       compressor.frequencies, 
                                                       unified_output)
    print(f"Unified Huffman dictionary saved to {unified_output}")
    
    with open(output_json, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Huffman codes saved to {output_json}")

    total_images = len(image_huffman_dict)
    total_unified_symbols = len(unified_huffman_dict)
    unique_codes = set(unified_huffman_dict.values())
    total_unique_codes = len(unique_codes)
    
    print(f"\nProcessed {total_images} images")
    print(f"Total unique symbols in unified dictionary: {total_unified_symbols}")
    print(f"Total unique code patterns: {total_unique_codes}")
    
    
    
    return image_huffman_dict, unified_huffman_dict


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract Huffman codes from images')
    parser.add_argument('--input', type=str, required=True, help='Input folder containing images')
    parser.add_argument('--output', type=str, default='huffman_codes.json', help='Output JSON file')
    parser.add_argument('--quality', type=int, default=50, help='JPEG quality (1-100)')
    parser.add_argument('--chroma', type=str, default='420', choices=['420', '422', '444'], 
                        help='Chroma subsampling mode')
    parser.add_argument('--visualize', action='store_true', help='Visualize compression stages')
    parser.add_argument('--output_folder', type=str, default='output', help='Output folder for visualizations')
    
    args = parser.parse_args()
    
    # Create output directory if needed
    if args.visualize:
        os.makedirs(args.output_folder, exist_ok=True)
    
    # Process the folder
    start_time = time.time()
    image_huffman_dict, unified_huffman_dict = process_folder(
        args.input, args.output, args.quality, args.chroma
    )
    
    # Print statistics
    total_images = len(image_huffman_dict)
    total_unified_symbols = len(unified_huffman_dict)
    
    print(f"\nProcessed {total_images} images")
    print(f"Total unique symbols in unified dictionary: {total_unified_symbols}")
    
    # Calculate average code lengths per image
    avg_lengths = {}
    for img_name, codes in image_huffman_dict.items():
        avg_length = sum(len(code) for code in codes.values()) / len(codes) if codes else 0
        avg_lengths[img_name] = avg_length
        print(f"Image {img_name}: {len(codes)} symbols, avg code length: {avg_length:.2f} bits")
    
    # Calculate average code length for unified dictionary
    if unified_huffman_dict:
        unified_avg = sum(len(code) for code in unified_huffman_dict.values()) / len(unified_huffman_dict)
        print(f"Unified dictionary avg code length: {unified_avg:.2f} bits")
    
    print(f"Processing time: {time.time() - start_time:.2f} seconds")
    print(f"Results saved to {args.output}")
    
    # Visualize if requested
    if args.visualize and image_huffman_dict:
        # Plot average code lengths
        plt.figure(figsize=(12, 6))
        plt.bar(avg_lengths.keys(), avg_lengths.values())
        plt.title('Average Huffman Code Length by Image')
        plt.ylabel('Average Code Length (bits)')
        plt.xlabel('Image')
        plt.xticks(rotation=90)
        plt.tight_layout()
        viz_path = os.path.join(args.output_folder, 'huffman_code_lengths.png')
        plt.savefig(viz_path)
        print(f"Visualization saved to {viz_path}")
    
    print("\nDone!")