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

class ImageJPEGCompressor:
    def __init__(self, quality=50):
        self.codes = {}
        self.reverse_codes = {}
        self.frequencies = {}
        self.quality = quality
        self.original_shape = None
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
            # For low quality, use a more conservative scale to avoid black images
            scale_factor = 50 / quality
        else:
            scale_factor = 2 - quality / 50
            
        # Apply scaling with proper rounding to avoid too aggressive quantization
        adjusted_matrix = np.floor((matrix * scale_factor + 0.5))
        adjusted_matrix[adjusted_matrix <= 0] = 1  # Ensure no zeros
        
        # Cap maximum values to prevent extreme quantization
        adjusted_matrix = np.minimum(adjusted_matrix, 255)
        
        return adjusted_matrix

    def read_image(self, path):
        try:
            image = Image.open(path)
            image = image.convert('RGB')
            self.original_shape = image.size  # Store original dimensions
            
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

    def run_length_encode(self, zigzag):
        """Run-length encode the zigzag coefficients"""
        # Count trailing zeros
        i = len(zigzag) - 1
        while i >= 0 and zigzag[i] == 0:
            i -= 1
        
        # Truncate trailing zeros
        zigzag = zigzag[:i+1]
        
        # Run-length encoding for remaining coefficients
        result = []
        run_length = 0
        
        for value in zigzag:
            if value == 0:
                run_length += 1
            else:
                result.append((run_length, value))
                run_length = 0
                
        # Add EOB marker if needed
        if run_length > 0:
            result.append((run_length, 0))  # EOB
            
        return result
    
    def run_length_decode(self, rle):
        """Decode run-length encoded data back to zigzag array"""
        zigzag = []
        for run, value in rle:
            zigzag.extend([0] * run)
            if value != 0:  # Skip EOB marker
                zigzag.append(value)
        
        # Pad with zeros to make a complete 64-element zigzag
        zigzag.extend([0] * (64 - len(zigzag)))
        return zigzag

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
                    
                    # Zigzag scan
                    zigzag = self.zigzag_scan(block)
                    
                    # Run-length encode
                    rle = self.run_length_encode(zigzag)
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
    
    def decompress_image(self, rle_data, shape):
        """Reconstruct image from RLE encoded DCT coefficients"""
        height, width, channels = shape
        reconstructed_quantized = np.zeros(shape, dtype=int)

        # Decode RLE data back to quantized DCT coefficients
        for channel, i, j, rle in rle_data:
            # Run-length decode
            zigzag = self.run_length_decode(rle)
            
            # Inverse zigzag scan
            block = self.inverse_zigzag(zigzag)
            
            # Store in reconstructed quantized image
            if i+8 <= height and j+8 <= width:
                reconstructed_quantized[i:i+8, j:j+8, channel] = block
            else:
                reconstructed_quantized[i:min(i+8, height), j:min(j+8, width), channel] = block[:min(i+8, height)-i, :min(j+8, width)-j]
                
        # Dequantize
        dequantized_image = self.dequantize(reconstructed_quantized)
        
        # Inverse DCT
        idct_image = self.inverse_dct(dequantized_image)
        
        return idct_image
    
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
        
        print("Performing zigzag scanning and run-length encoding...")
        frequencies, rle_data = self.calculate_frequencies(quantized_image)
        self.frequencies = frequencies
        
        print("Building Huffman tree...")
        root = self.build_huffman_tree(frequencies)
        if root:
            print("Generating Huffman codes...")
            self.generate_codes(root)
        
        print("Reconstructing image from compressed data...")
        # Reconstruct the image to visualize the compression effects
        reconstructed_ycbcr = self.decompress_image(rle_data, subsampled_image.shape)
        reconstructed_rgb = self.ycbcr_to_rgb(reconstructed_ycbcr)
        
        # Crop to original dimensions if needed
        if orig_width and orig_height:
            reconstructed_rgb = reconstructed_rgb[:orig_height, :orig_width]
            
        compression_info = {
            'original': image_array,
            'ycbcr': ycbcr_image,
            'dct': dct_image,
            'quantized': quantized_image,
            'reconstructed_ycbcr': reconstructed_ycbcr,
            'reconstructed_rgb': reconstructed_rgb,
            'rle_data': rle_data
        }
            
        return compression_info

def print_huffman_codes(encoder, num_codes=10):
    print("\n--- Top Huffman Codes ---")
    codes_list = list(encoder.codes.items())
    if len(codes_list) > 0:
        # Sort by frequency (most frequent first)
        for i, (symbol, code) in enumerate(sorted(codes_list, key=lambda x: len(x[1]))[:num_codes]):
            print(f"Symbol {symbol}: {code}")

def save_compressed_image(compressed_image, output_path):
    """Save reconstructed image to file"""
    # Ensure values are in valid range
    img_array = np.clip(compressed_image, 0, 255).astype(np.uint8)
    img = Image.fromarray(img_array)
    img.save(output_path)
    print(f"Saved compressed image to {output_path}")

def visualize_compression(compression_info, quality, chroma_subsampling, output_dir="compressed_output"):
    """Visualize original and compressed images"""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save reconstructed image
    output_path = os.path.join(output_dir, f"compressed_q{quality}_{chroma_subsampling}.jpg")
    save_compressed_image(compression_info['reconstructed_rgb'], output_path)
    
    # Display images
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    
    axes[0].imshow(compression_info['original'])
    axes[0].set_title("Original Image")
    axes[0].axis('off')
    
    axes[1].imshow(compression_info['reconstructed_rgb'])
    axes[1].set_title(f"Compressed (Quality: {quality}, Subsampling: {chroma_subsampling})")
    axes[1].axis('off')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"comparison_q{quality}_{chroma_subsampling}.png"))
    plt.show()

def main():
    image_path = "/home/sejal/Documents/CV Project/Canonical-Image-Compression/Folder1/0000.jpg"  # Update this path to your image
    output_dir = "compressed_output"
    
    # Test with different quality settings
    quality_levels = [90, 50, 30, 10, 5]
    chroma_subsampling = '420'  # 4:2:0 subsampling
    
    if not os.path.exists(image_path):
        print(f"Error: File not found at {image_path}")
        return
    
    original_size = os.path.getsize(image_path)
    print(f"Original Image Size: {original_size} bytes ({original_size/1024:.1f} KB)")
    
    # Test each quality level
    for quality in quality_levels:
        print(f"\n--- Testing Quality Level: {quality} ---")
        compressor = ImageJPEGCompressor(quality=quality)
        compression_info = compressor.compress_image(image_path, chroma_subsampling=chroma_subsampling)
        
        if compression_info is None:
            print("Compression failed!")
            continue
        
        # Calculate compression ratio
        compressed_size = compressor.estimate_compressed_size(compression_info['rle_data'])
        jpeg_overhead = 1000  # Approx. size for headers, tables, metadata
        total_jpeg_size = compressed_size + jpeg_overhead
        compression_ratio = original_size / total_jpeg_size
        
        print(f"Quality: {quality}")
        print(f"Estimated compressed size: ~{total_jpeg_size} bytes ({total_jpeg_size/1024:.1f} KB)")
        print(f"Compression Ratio: {compression_ratio:.2f}x")
        
        # Visualize the compression
        visualize_compression(compression_info, quality, chroma_subsampling, output_dir)
        
        # Show Huffman codes
        print_huffman_codes(compressor, 10)

if __name__ == "__main__":
    main()