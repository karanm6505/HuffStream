#!/usr/bin/env python3
"""
Utility script for encoding a file using Huffman coding.
Usage: python encode_file.py <input_file> <output_file>
"""

import sys
import os
from huffman import encode_file

def main():
    # Check command-line arguments
    if len(sys.argv) != 3:
        print("Usage: python encode_file.py <input_file> <output_file>")
        return 1
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        return 1
    
    print(f"Encoding file {input_file} using Huffman coding...")
    try:
        output_path = encode_file(input_file, output_file)
        print(f"File encoded successfully: {output_path}")
        return 0
    except Exception as e:
        print(f"Error encoding file: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
