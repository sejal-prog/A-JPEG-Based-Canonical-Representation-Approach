from PIL import Image
import numpy as np
from collections import defaultdict
import os
import csv
import math

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
            print(f"Error reading image: {path} - {e}")
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
    
    def calculate_compression_percentage(self, image_array):
        """
        Calculate compression percentage using Huffman encoding
        
        Args:
        image_array (numpy.ndarray): Input image array
        
        Returns:
        dict: Compression details including percentage
        """
        # Original image size calculation
        original_bits_per_pixel = 8  # Assuming 8-bit grayscale
        original_total_bits = image_array.size * original_bits_per_pixel
        
        # Calculate frequencies
        frequencies = self.calculate_frequencies(image_array)
        self.frequencies = frequencies
        
        # Build Huffman tree
        root = self.build_huffman_tree(frequencies)
        
        # Generate Huffman codes
        self.generate_codes(root)
        
        # Calculate Huffman encoded bits
        huffman_bits = sum(len(self.codes[int(pixel)]) for pixel in image_array.flatten())
        
        # Calculate compression percentage
        compression_percentage = (1 - (huffman_bits / original_total_bits)) * 100
        
        return {
            'original_total_bits': original_total_bits,
            'huffman_encoded_bits': huffman_bits,
            'compression_percentage': round(compression_percentage, 2)
        }
    
    def encode_image(self, image_path):
        """Main function to encode image and calculate compression."""
        # Reset codes and frequencies for each image
        self.codes = {}
        self.reverse_codes = {}
        self.frequencies = {}
        
        # Read image
        image_array = self.read_image(image_path)
        if image_array is None:
            return None
        
        # Calculate compression details
        compression_details = self.calculate_compression_percentage(image_array)
        
        # Add filename to details
        compression_details['filename'] = os.path.basename(image_path)
        
        return compression_details

def process_folder_images(folder_path, output_csv=None):
    """
    Process all images in a given folder and collect their compression details.
    
    Args:
    folder_path (str): Path to the folder containing images
    output_csv (str, optional): Path to save CSV output
    
    Returns:
    list: List of dictionaries with compression details for each image
    """
    # Supported image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}
    
    # Initialize encoder and results list
    encoder = ImageHuffmanEncoder()
    results = []
    
    # Iterate through files in the folder
    for filename in os.listdir(folder_path):
        # Check if file is an image
        if os.path.splitext(filename)[1].lower() in image_extensions:
            image_path = os.path.join(folder_path, filename)
            
            # Process image
            compression_details = encoder.encode_image(image_path)
            
            if compression_details:
                results.append(compression_details)
                
                # Print details for each image
                print(f"\n--- Image: {filename} ---")
                print(f"Compression Percentage: {compression_details['compression_percentage']}%")
    
    # Optional: Save results to CSV
    if output_csv:
        save_results_to_csv(results, output_csv)
    
    return results

def save_results_to_csv(results, output_path):
    """
    Save compression details to a CSV file.
    
    Args:
    results (list): List of dictionaries with compression details
    output_path (str): Path to save CSV file
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Define CSV headers
    headers = [
        'filename', 
        'original_total_bits', 
        'huffman_encoded_bits', 
        'compression_percentage'
    ]
    
    # Write to CSV
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for result in results:
            # Extract only the specified headers
            csv_row = {
                'filename': result['filename'],
                'original_total_bits': result['original_total_bits'],
                'huffman_encoded_bits': result['huffman_encoded_bits'],
                'compression_percentage': result['compression_percentage']
            }
            writer.writerow(csv_row)

def main():
    # Specify the path to your image folder
    folder_path = "/Users/sejaljadhav/Documents/CV Projects/Folder1"
    
    # Optional: Specify CSV output path
    output_csv = "/Users/sejaljadhav/Documents/CV Projects/compression_analysis.csv"
    
    # Process images
    results = process_folder_images(folder_path, output_csv)

if __name__ == "__main__":
    main()