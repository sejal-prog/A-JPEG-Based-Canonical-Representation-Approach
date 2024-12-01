from PIL import Image
import numpy as np
from collections import defaultdict
import os
import csv

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
            'min_code_length': min(code_lengths) if code_lengths else 0,
            'max_code_length': max(code_lengths) if code_lengths else 0,
            'average_code_length': sum(code_lengths) / total_unique_codes if total_unique_codes else 0,
            'code_length_distribution': {
                length: code_lengths.count(length) 
                for length in set(code_lengths)
            },
            'full_codebook': self.codes
        }
        
        return codebook_details
    
    def encode_image(self, image_path):
        """Main function to encode image."""
        # Reset codes and frequencies for each image
        self.codes = {}
        self.reverse_codes = {}
        self.frequencies = {}
        
        # Read image
        image_array = self.read_image(image_path)
        if image_array is None:
            return None
        
        # Calculate frequencies
        frequencies = self.calculate_frequencies(image_array)
        self.frequencies = frequencies
        
        # Build Huffman tree
        root = self.build_huffman_tree(frequencies)
        
        # Generate codes
        self.generate_codes(root)
        
        # Extract codebook details
        codebook_details = self.extract_codebook_details()
        
        return codebook_details

class CombinedHuffmanCodebook:
    def __init__(self):
        # Combined frequency dictionary across all images
        self.combined_frequencies = defaultdict(int)
        
        # Combined codebook
        self.combined_codebook = {}
        
    def merge_codebooks(self, codebook_results):
        """
        Merge Huffman codebooks from multiple images.
        
        Args:
        codebook_results (list): List of codebook details from images
        """
        # Aggregate frequencies from all images
        for result in codebook_results:
            # Create a temporary frequency dictionary from the full codebook
            for pixel_value, code in result.get('full_codebook', {}).items():
                # Count frequency based on code length (inverse proxy for frequency)
                self.combined_frequencies[pixel_value] += 1
        
        # Build a new Huffman tree from combined frequencies
        encoder = ImageHuffmanEncoder()
        root = encoder.build_huffman_tree(self.combined_frequencies)
        
        # Generate new codes based on combined frequencies
        encoder.codes = {}
        encoder.generate_codes(root)
        
        # Store the combined codebook
        self.combined_codebook = encoder.codes
        
        return self.get_codebook_summary()
    
    def get_codebook_summary(self):
        """
        Generate summary of the combined codebook.
        
        Returns:
        dict: Comprehensive summary of combined codebook
        """
        if not self.combined_codebook:
            return {}
        
        code_lengths = [len(code) for code in self.combined_codebook.values()]
        
        return {
            'total_unique_codes': len(self.combined_codebook),
            'min_code_length': min(code_lengths),
            'max_code_length': max(code_lengths),
            'average_code_length': sum(code_lengths) / len(code_lengths),
            'combined_codebook': self.combined_codebook
        }
    
    def save_combined_codebook(self, output_path):
        """
        Save combined codebook to a CSV file.
        
        Args:
        output_path (str): Path to save the CSV file
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Pixel Value', 'Huffman Code'])
            
            for pixel_value, code in self.combined_codebook.items():
                writer.writerow([pixel_value, code])

def process_folder_images(folder_path, output_csv=None):
    """
    Process all images in a given folder and collect their codebook details.
    
    Args:
    folder_path (str): Path to the folder containing images
    output_csv (str, optional): Path to save CSV output
    
    Returns:
    list: List of dictionaries with codebook details for each image
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
            codebook_details = encoder.encode_image(image_path)
            
            if codebook_details:
                # Add filename to details
                codebook_details['filename'] = filename
                results.append(codebook_details)
                
                # Print details for each image
                print(f"\n--- Image: {filename} ---")
                print(f"Total Unique Codes: {codebook_details['total_unique_codes']}")
                print(f"Total Non-Unique Codes: {codebook_details['total_non_unique_codes']}")
    
    # Optional: Save results to CSV
    if output_csv:
        save_results_to_csv(results, output_csv)
    
    return results

def save_results_to_csv(results, output_path):
    """
    Save codebook details to a CSV file.
    
    Args:
    results (list): List of dictionaries with codebook details
    output_path (str): Path to save CSV file
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Define CSV headers
    headers = [
        'filename', 
        'total_unique_codes', 
        'total_non_unique_codes', 
        'min_code_length', 
        'max_code_length', 
        'average_code_length'
    ]
    
    # Write to CSV
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for result in results:
            # Extract only the specified headers
            csv_row = {
                'filename': result['filename'],
                'total_unique_codes': result['total_unique_codes'],
                'total_non_unique_codes': result['total_non_unique_codes'],
                'min_code_length': result['min_code_length'],
                'max_code_length': result['max_code_length'],
                'average_code_length': round(result['average_code_length'], 2)
            }
            writer.writerow(csv_row)

def main():
    # Specify the path to your image folder
    folder_path = "/Users/sejaljadhav/Documents/CV Projects/Folder1"
    
    # Optional: Specify CSV output path
    output_csv = "/Users/sejaljadhav/Documents/CV Projects/codebook.csv"
    
    # Process images
    results = process_folder_images(folder_path, output_csv)
    
    # Create combined codebook
    combined_codebook = CombinedHuffmanCodebook()
    summary = combined_codebook.merge_codebooks(results)
    
    # Print summary
    print("\nCombined Codebook Summary:")
    for key, value in summary.items():
        if key != 'combined_codebook':
            print(f"{key}: {value}")
    
    # Optional: Save combined codebook
    combined_codebook.save_combined_codebook("/Users/sejaljadhav/Documents/CV Projects/combined_codebook.csv")

if __name__ == "__main__":
    main()