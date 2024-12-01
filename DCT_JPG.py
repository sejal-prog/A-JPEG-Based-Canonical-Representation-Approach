from PIL import Image
import numpy as np
from collections import defaultdict
import os
import scipy.fftpack as fft

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
        self.frequencies = {}
        
    def read_image(self, path):
        """Read image and convert to grayscale numpy array."""
        try:
            image = Image.open(path)
            if image.mode != 'L':
                image = image.convert('L')
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
    
    def calculate_dct(self, image_array):
        """Calculate the Discrete Cosine Transform (DCT) of the image."""
        dct_values = fft.dct(fft.dct(image_array.T, axis=0).T, axis=1)
        return dct_values
    
    def extract_codebook_details(self):
        """
        Detailed extraction of codebook information
        
        Returns:
        dict: Comprehensive codebook statistics
        """
        # Total number of unique codes
        total_unique_codes = len(self.codes)
        
        # Total number of non-unique codes (total pixel occurrences)
        total_non_unique_codes = sum(self.frequencies.values())
        
        # Code length analysis
        code_lengths = [len(code) for code in self.codes.values()]
        
        codebook_details = {
            'total_unique_codes': total_unique_codes,
            'total_non_unique_codes': total_non_unique_codes,
            'min_code_length': min(code_lengths),
            'max_code_length': max(code_lengths),
            'average_code_length': sum(code_lengths) / total_unique_codes,
            'code_length_distribution': {
                length: code_lengths.count(length) 
                for length in set(code_lengths)
            },
            'full_codebook': self.codes
        }
        
        return codebook_details
    
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
        self.frequencies = frequencies
        
        # Build Huffman tree
        print("Building Huffman tree...")
        root = self.build_huffman_tree(frequencies)
        
        # Generate codes
        print("Generating Huffman codes...")
        self.generate_codes(root)
        
        # Extract codebook details
        codebook_details = self.extract_codebook_details()
        
        return image_array, frequencies, codebook_details

def print_codebook_details(codebook_details):
    """Pretty print codebook details"""
    print("\n--- Codebook Details ---")
    print(f"Total Unique Codes: {codebook_details['total_unique_codes']}")
    print(f"Total Non-Unique Codes: {codebook_details['total_non_unique_codes']}")
    print(f"Minimum Code Length: {codebook_details['min_code_length']} bits")
    print(f"Maximum Code Length: {codebook_details['max_code_length']} bits")
    print(f"Average Code Length: {codebook_details['average_code_length']:.2f} bits")
    
    print("\nCode Length Distribution:")
    for length, count in sorted(codebook_details['code_length_distribution'].items()):
        print(f"  {length} bits: {count} codes")
    
    # Optional: Print first few codebook entries
    print("\nFirst 10 Codebook Entries:")
    for pixel, code in list(codebook_details['full_codebook'].items())[:10]:
        print(f"Pixel {pixel}: {code}")

def main():
    # Specify the path to your image
    image_path = "/Users/sejaljadhav/Downloads/bdd/0a851459-0fb97708/0003.jpg"
    
    if not os.path.exists(image_path):
        print(f"Error: File not found at {image_path}")
        return
    
    # Initialize encoder and process image
    encoder = ImageHuffmanEncoder()
    image_array, frequencies, codebook_details = encoder.encode_image(image_path)
    
    # Print codebook details
    print_codebook_details(codebook_details)

if __name__ == "__main__":
    main()