from PIL import Image
import numpy as np
from collections import defaultdict
import os

class HuffmanNode:
    def __init__(self, value=None, frequency=None):
        self.value = value
        self.frequency = frequency
        self.left = None
        self.right = None
        self.code = ''

class ImageHuffmanEncoder:
    def __init__(self):
        self.codes = {}
        self.reverse_codes = {}
        
    def read_image(self, path):
        """Read image and convert to grayscale numpy array."""
        try:
            # Open image and convert to grayscale
            image = Image.open(path)
            if image.mode != 'L':
                image = image.convert('L')
            
            # Convert to numpy array
            return np.array(image)
            
        except Exception as e:
            print(f"Error reading image: {e}")
            return None
    
    def calculate_frequencies(self, image_array):
        """Calculate frequency of each pixel value."""
        frequencies = defaultdict(int)
        height, width = image_array.shape
        
        for i in range(height):
            for j in range(width):
                pixel_value = image_array[i, j]
                frequencies[pixel_value] += 1
                
        return frequencies
    
    def build_huffman_tree(self, frequencies):
        """Build Huffman tree from frequency dictionary."""
        nodes = []
        
        # Create initial nodes
        for value, freq in frequencies.items():
            node = HuffmanNode(value=value, frequency=freq)
            nodes.append(node)
        
        while len(nodes) > 1:
            # Sort nodes by frequency
            nodes = sorted(nodes, key=lambda x: x.frequency)
            
            # Take two nodes with lowest frequencies
            left = nodes.pop(0)
            right = nodes.pop(0)
            
            # Create parent node
            parent = HuffmanNode(frequency=left.frequency + right.frequency)
            parent.left = left
            parent.right = right
            
            nodes.append(parent)
        
        return nodes[0] if nodes else None
    
    def generate_codes(self, root, code=""):
        """Generate Huffman codes by traversing the tree."""
        if root is None:
            return
        
        if root.value is not None:
            self.codes[root.value] = code
            self.reverse_codes[code] = root.value
            return
        
        self.generate_codes(root.left, code + "0")
        self.generate_codes(root.right, code + "1")
    
    def encode_image(self, image_path):
        """Main function to encode image."""
        # Read image
        print(f"\nReading image: {image_path}")
        image_array = self.read_image(image_path)
        if image_array is None:
            return
        
        # Calculate frequencies
        print("Calculating pixel frequencies...")
        frequencies = self.calculate_frequencies(image_array)
        
        # Build Huffman tree
        print("Building Huffman tree...")
        root = self.build_huffman_tree(frequencies)
        
        # Generate codes
        print("Generating Huffman codes...")
        self.generate_codes(root)
        
        # Print statistics
        self.print_statistics(image_array, frequencies)
        
        return self.codes, frequencies

    def print_statistics(self, image_array, frequencies):
        """Print encoding statistics."""
        print("\nHuffman Encoding Statistics:")
        print("-" * 50)
        
        # Image details
        print(f"Image dimensions: {image_array.shape[0]}x{image_array.shape[1]}")
        print(f"Total pixels: {image_array.size}")
        print(f"Unique pixel values: {len(frequencies)}")
        
        # Code details
        print("\nHuffman Codes (showing first 10 values):")
        print("Pixel Value | Frequency | Code")
        print("-" * 50)
        
        for i, (pixel_value, code) in enumerate(sorted(self.codes.items())):
            if i >= 20:  # Only show first 10 entries
                break
            freq = frequencies[pixel_value]
            print(f"{pixel_value:11d} | {freq:9d} | {code}")
        
        if len(self.codes) > 10:
            print("... (more entries not shown)")
        
        # Calculate compression
        original_size = image_array.size * 8  # 8 bits per pixel
        compressed_size = sum(len(self.codes[value]) * frequencies[value] 
                            for value in frequencies)
        
        print("\nCompression Analysis:")
        print(f"Original size: {original_size:,} bits")
        print(f"Compressed size: {compressed_size:,} bits")
        print(f"Compression ratio: {original_size/compressed_size:.2f}:1")
        
        # Calculate average code length
        total_pixels = sum(frequencies.values())
        avg_code_length = sum(len(code) * frequencies[pixel] / total_pixels 
                            for pixel, code in self.codes.items())
        print(f"Average code length: {avg_code_length:.2f} bits")

def main():
    # Specify your image path here - MODIFY THIS LINE WITH YOUR IMAGE PATH
    image_path = "/Users/sejaljadhav/Downloads/bdd/0a851459-0fb97708/0002.jpg"  # Replace with your actual image path
    
    # Verify if file exists
    if not os.path.exists(image_path):
        print(f"Error: File not found at {image_path}")
        return
    
    # Create encoder and process image
    encoder = ImageHuffmanEncoder()
    encoder.encode_image(image_path)

if __name__ == "__main__":
    main()