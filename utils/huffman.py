import heapq
from collections import Counter
import pickle
import io

class HuffmanNode:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None
        
    def __lt__(self, other):
        return self.freq < other.freq

def build_huffman_tree(data):
    """Build a Huffman tree from data content"""
    # Count frequency of each byte
    frequency = Counter(data)
    priority_queue = [HuffmanNode(char, freq) for char, freq in frequency.items()]
    heapq.heapify(priority_queue)

    while len(priority_queue) > 1:
        
        left = heapq.heappop(priority_queue)
        right = heapq.heappop(priority_queue)
        
        internal = HuffmanNode(None, left.freq + right.freq)
        internal.left = left
        internal.right = right
        
        heapq.heappush(priority_queue, internal)
    
    return priority_queue[0] if priority_queue else None
def build_codes(node, code="", mapping=None):
    """Build the Huffman codes for each byte"""
    if mapping is None:
        mapping = {}
    
    if node is None:
        return mapping
    
    if node.char is not None:
        mapping[node.char] = code if code else "0"  # Special case for single character
        return mapping
        
    if node.left:
        build_codes(node.left, code + "0", mapping)
        
    if node.right:
        build_codes(node.right, code + "1", mapping)
        
    return mapping
def huffman_encode(data):
    """Encode data using Huffman coding"""
    if not data:
        return "", {}, {}
    
    root = build_huffman_tree(data)
    codes = build_codes(root)
    encoded_data = ""
    for byte in data:
        encoded_data += codes[byte]
    

    reverse_mapping = {code: byte for byte, code in codes.items()}
    
    return encoded_data, codes, reverse_mapping
def huffman_decode(encoded_data, reverse_mapping):
    """Decode Huffman-encoded data"""
    if not encoded_data:
        return bytearray()
        
    decoded_data = bytearray()
    current_code = ""
    
    for bit in encoded_data:
        current_code += bit
        if current_code in reverse_mapping:
            decoded_data.append(reverse_mapping[current_code])
            current_code = ""
            
    return decoded_data
def encode_file(input_path, output_path):
    """Encode a file using Huffman coding"""
    with open(input_path, 'rb') as file:
        data = file.read()
    
    encoded_text, codes, reverse_mapping = huffman_encode(data)
    
    padding = 8 - (len(encoded_text) % 8) if len(encoded_text) % 8 != 0 else 0
    padded_text = encoded_text + "0" * padding
    
    encoded_bytes = bytearray()
    for i in range(0, len(padded_text), 8):
        byte = padded_text[i:i+8]
        encoded_bytes.append(int(byte, 2))
    
    with open(output_path, 'wb') as file:
        metadata = {
            'padding': padding,
            'original_size': len(data),
            'reverse_mapping': reverse_mapping
        }
        pickle.dump(metadata, file)
        
        file.write(bytes(encoded_bytes))
    
    original_size = len(data)
    compressed_size = len(encoded_bytes) + len(pickle.dumps(metadata))
    compression_ratio = (original_size - compressed_size) / original_size * 100
    
    print(f"Original size: {original_size} bytes")
    print(f"Compressed size: {compressed_size} bytes")
    print(f"Compression ratio: {compression_ratio:.2f}%")
    
    return output_path
def decode_file(input_path, output_path):
    """Decode a Huffman-encoded file"""
    with open(input_path, 'rb') as file:
        metadata = pickle.load(file)
        padding = metadata['padding']
        reverse_mapping = metadata['reverse_mapping']
      
        encoded_bytes = file.read()
    
   
    binary_string = ""
    for byte in encoded_bytes:
        binary_string += format(byte, '08b')
    
    encoded_text = binary_string[:-padding] if padding > 0 else binary_string
    decoded_data = huffman_decode(encoded_text, reverse_mapping)
    with open(output_path, 'wb') as file:
        file.write(decoded_data)
    
    return output_path
def encode_data(data):
    """Encode data using Huffman coding (in-memory version)"""
    encoded_text, codes, reverse_mapping = huffman_encode(data)
    
    padding = 8 - (len(encoded_text) % 8) if len(encoded_text) % 8 != 0 else 0
    padded_text = encoded_text + "0" * padding
    encoded_bytes = bytearray()
    for i in range(0, len(padded_text), 8):
        byte = padded_text[i:i+8]
        encoded_bytes.append(int(byte, 2))
    
    memory_file = io.BytesIO()
    
    metadata = {
        'padding': padding,
        'original_size': len(data),
        'reverse_mapping': reverse_mapping
    }
    pickle.dump(metadata, memory_file)
    
    memory_file.write(bytes(encoded_bytes))
    
    original_size = len(data)
    compressed_size = len(encoded_bytes) + len(pickle.dumps(metadata))
    compression_ratio = (original_size - compressed_size) / original_size * 100
    
    print(f"Original size: {original_size} bytes")
    print(f"Compressed size: {compressed_size} bytes")
    print(f"Compression ratio: {compression_ratio:.2f}%")
    
    memory_file.seek(0)
    return memory_file.read(), compression_ratio
