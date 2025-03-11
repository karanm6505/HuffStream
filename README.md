# File Compression and Transfer System

A client-server application for transferring files with Huffman encoding-based compression. This system demonstrates data compression techniques in network communications.

## Project Overview

This application implements a client-server architecture for file transfer with the following features:

- **Huffman Encoding**: Compresses files using Huffman coding algorithm
- **Network Transfer**: Sends compressed files over TCP/IP
- **Decompression**: Reconstructs original files from Huffman-encoded data
- **Compression Statistics**: Displays file size reduction metrics

## System Architecture

The project is organized into three main components:

1. **Client**: Encodes and sends files to the server
2. **Server**: Receives encoded files, decodes them, and saves both versions
3. **Utilities**: Contains the Huffman encoding/decoding implementation

### Directory Structure

```
HuffStream/
├── client/
│   ├── client.py                # Client application
│   └── sending_files/           # Files to be sent
│   
├── server/
│   ├── server.py                # Server application
│   └── received_files/          # Files received from client
└── utils/
    ├── huffman.py               # Huffman coding implementation
    ├── encode_file.py           # Command-line encoding tool
    └── decode_file.py           # Command-line decoding tool
```

## How It Works

### Huffman Encoding

Huffman coding is a lossless data compression algorithm that:

1. Analyzes the frequency of characters/bytes in the source data
2. Builds a binary tree where more common symbols get shorter codes
3. Uses variable-length codes to represent each symbol, with shorter codes for more frequent symbols
4. Creates a compressed representation of the original data

### Workflow

1. The client reads a file and compresses it using Huffman encoding
2. The compressed file is sent over the network to the server
3. The server receives and saves the compressed file
4. The server decodes the file to recover the original data
5. Both encoded and decoded versions are stored on the server

## Usage Instructions

### Server Setup

1. Navigate to the server directory:
   ```
   cd server
   ```

2. Run the server:
   ```
   python server.py
   ```
   
   The server will start listening on port 9999 by default.

### Client Usage

1. Navigate to the client directory:
   ```
   cd client
   ```

2. Place the file you want to send in the `sending_files` directory.

3. Edit `client.py` to set:
   - `SERVER_IP`: IP address of the server
   - `FILE_PATH`: Path to the file you want to send

4. Run the client:
   ```
   python client.py
   ```

### Stand-alone Encoding/Decoding

The system also provides utilities for encoding and decoding files without using the network:

1. To encode a file:
   ```
   python utils/encode_file.py <input_file> <output_file>
   ```

2. To decode a file:
   ```
   python utils/decode_file.py <encoded_file> <output_file>
   ```

## Performance Analysis

The Huffman compression algorithm provides varying compression ratios depending on the data:

- **Text files**: Typically achieve 40-60% compression
- **Images**: Already compressed formats (JPEG, PNG) see minimal benefit
- **Documents**: Can see significant compression (40-70%)

The system outputs compression statistics when encoding files, showing:
- Original file size
- Compressed file size
- Compression ratio

## Requirements

- Python 3.6+
- Standard Python libraries (no external dependencies)

## Implementation Details

### Huffman Encoding Process

1. **Build Frequency Table**: Count occurrences of each byte in the input
2. **Create Priority Queue**: Initialize with leaf nodes for each byte
3. **Build Huffman Tree**: Repeatedly merge two lowest-frequency nodes
4. **Generate Code Table**: Traverse tree to assign codes to each byte
5. **Encode Data**: Replace each byte with its variable-length code
6. **Handle Padding**: Add padding to make total bits a multiple of 8
7. **Store Metadata**: Save mapping information for decoding

### Network Protocol

The application uses a simple protocol for file transfer:

1. **Header**: `<filename>|<filesize>` sent as a string
2. **Body**: Raw binary data of the file
3. **Acknowledgment**: Confirmation message from the receiver

## License

This project is open source and available under the MIT License.
