import numpy as np
from PIL import Image
import os
from collections import defaultdict
import heapq


class HuffmanNode:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None
    
    def __lt__(self, other):
        return self.freq < other.freq

def build_huffman_tree(data):
    frequency = defaultdict(int)
    for value in data.flatten():
        frequency[int(value)] = frequency[int(value)] + 1
    
    heap = []
    for char, freq in frequency.items():
        heapq.heappush(heap, HuffmanNode(char, freq))
    
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        
        internal = HuffmanNode(None, left.freq + right.freq)
        internal.left = left
        internal.right = right
        
        heapq.heappush(heap, internal)
    
    return heap[0]

def build_huffman_codes(root):
    codes = {}
    
    def generate_codes(node, code=""):
        if node is None:
            return
        
        if node.char is not None:
            codes[node.char] = code
            return
        
        generate_codes(node.left, code + "0")
        generate_codes(node.right, code + "1")
    
    generate_codes(root)
    return codes


def dct2d(block):
    M, N = block.shape
    dct_block = np.zeros((M, N))
    
    for u in range(M):
        for v in range(N):
            sum_val = 0
            cu = 1/np.sqrt(2) if u == 0 else 1
            cv = 1/np.sqrt(2) if v == 0 else 1
            
            for x in range(M):
                for y in range(N):
                    cos_term1 = np.cos((2*x + 1) * u * np.pi / (2*M))
                    cos_term2 = np.cos((2*y + 1) * v * np.pi / (2*N))
                    sum_val += block[x,y] * cos_term1 * cos_term2
            
            dct_block[u,v] = (2 / np.sqrt(M*N)) * cu * cv * sum_val
    
    return dct_block

def idct2d(block):
    M, N = block.shape
    idct_block = np.zeros((M, N))
    
    for x in range(M):
        for y in range(N):
            sum_val = 0
            
            for u in range(M):
                for v in range(N):
                    cu = 1/np.sqrt(2) if u == 0 else 1
                    cv = 1/np.sqrt(2) if v == 0 else 1
                    cos_term1 = np.cos((2*x + 1) * u * np.pi / (2*M))
                    cos_term2 = np.cos((2*y + 1) * v * np.pi / (2*N))
                    sum_val += cu * cv * block[u,v] * cos_term1 * cos_term2
            
            idct_block[x,y] = (2 / np.sqrt(M*N)) * sum_val
    
    return idct_block


def get_quantization_matrix(quality):
    """
    Quality factor = 1-100
    Higher quality = less compression, better image quality
    Lower quality = more compression, worse image quality
    """
    # Standard JPEG quantization matrix
    quantization_matrix = np.array([
        [16, 11, 10, 16, 24, 40, 51, 61],
        [12, 12, 14, 19, 26, 58, 60, 55],
        [14, 13, 16, 24, 40, 57, 69, 56],
        [14, 17, 22, 29, 51, 87, 80, 62],
        [18, 22, 37, 56, 68, 109, 103, 77],
        [24, 35, 55, 64, 81, 104, 113, 92],
        [49, 64, 78, 87, 103, 121, 120, 101],
        [72, 92, 95, 98, 112, 100, 103, 99]
    ])
    
    if quality < 1:
        quality = 1
    elif quality > 100:
        quality = 100
        
    if quality < 50:
        scaling = 5000 / quality
    else:
        scaling = 200 - 2 * quality
        
    if quality == 100:
        return np.ones_like(quantization_matrix)
        
    return np.ceil((scaling * quantization_matrix) / 100.0).astype(int)

def compress_image(image_path, quality=50):
 
    img = Image.open(image_path)
    original_size = os.path.getsize(image_path)
    print(f"Original file size: {original_size} bytes")

    quantization_matrix = get_quantization_matrix(quality)
    print(f"Compressing with quality factor: {quality}")
    
    img_array = np.array(img)
    height, width, channels = img_array.shape
    block_size = 8
    
    compressed_channels = []
    huffman_trees = []
    
    for channel in range(channels):
        channel_array = img_array[:, :, channel]
        dct_array = np.zeros_like(channel_array, dtype=float)
        
        # DCT 
        for i in range(0, height, block_size):
            for j in range(0, width, block_size):
                block = channel_array[i:i+block_size, j:j+block_size].astype(float)
                block -= 128
                dct_block = dct2d(block)
                dct_array[i:i+block_size, j:j+block_size] = dct_block
        
        quantized_array = np.zeros_like(dct_array)
        for i in range(0, height, block_size):
            for j in range(0, width, block_size):
                block = dct_array[i:i+block_size, j:j+block_size]
                quantized_array[i:i+block_size, j:j+block_size] = np.round(block / quantization_matrix)
        
       
        huffman_tree = build_huffman_tree(quantized_array)
        huffman_codes = build_huffman_codes(huffman_tree)
        
        encoded_data = ""
        for value in quantized_array.flatten():
            encoded_data += huffman_codes[int(value)]
        
        compressed_channels.append(encoded_data)
        huffman_trees.append(huffman_tree)
    
    total_compressed_size = sum(len(channel) // 8 + (1 if len(channel) % 8 else 0) 
                              for channel in compressed_channels)
    print(f"Size after compression: {total_compressed_size} bytes")
    
    return compressed_channels, huffman_trees, (height, width, channels), total_compressed_size, quality

def decompress_image(compressed_channels, huffman_trees, shape, quality):
   
    height, width, channels = shape
    reconstructed_array = np.zeros(shape, dtype=np.uint8)
    block_size = 8
    

    quantization_matrix = get_quantization_matrix(quality)
    
    for channel in range(channels):
        current = huffman_trees[channel]
        decoded_values = []
        
        for bit in compressed_channels[channel]:
            if bit == '0':
                current = current.left
            else:
                current = current.right
                
            if current.char is not None:
                decoded_values.append(current.char)
                current = huffman_trees[channel]
        
        quantized_array = np.array(decoded_values).reshape((height, width))
        
        # Dequantize and IDCT
        dequantized_array = np.zeros_like(quantized_array, dtype=float)
        for i in range(0, height, block_size):
            for j in range(0, width, block_size):
                block = quantized_array[i:i+block_size, j:j+block_size]
                dequantized_array[i:i+block_size, j:j+block_size] = block * quantization_matrix
        
        reconstructed_channel = np.zeros_like(dequantized_array)
        for i in range(0, height, block_size):
            for j in range(0, width, block_size):
                block = dequantized_array[i:i+block_size, j:j+block_size]
                idct_block = idct2d(block)
                idct_block += 128
                reconstructed_channel[i:i+block_size, j:j+block_size] = idct_block
        
        reconstructed_array[:, :, channel] = np.clip(reconstructed_channel, 0, 255)
    
    reconstructed_image = Image.fromarray(reconstructed_array)
    return reconstructed_image

def main():
    image_path = "/Users/sejaljadhav/Documents/CV/Canonical-Image-Compression/Folder1/0000.jpg"

    
    compressed_channels, huffman_trees, shape, compressed_size, quality = compress_image(image_path, quality=25)
    reconstructed_image = decompress_image(compressed_channels, huffman_trees, shape, quality)
    
    output_path = f"reconstructed_q{quality}.jpg"
    reconstructed_image.save(output_path)
    
    original_size = os.path.getsize(image_path)
    reconstructed_size = os.path.getsize(output_path)
    print(f"\nFinal size comparison:")
    print(f"Original size: {original_size} bytes")
    print(f"Reconstructed size: {reconstructed_size} bytes")
    print(f"Difference: {abs(original_size - reconstructed_size)} bytes")
    print(f"Compression ratio: {original_size / compressed_size:.2f}x")

if __name__ == "__main__":
    main()