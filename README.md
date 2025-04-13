# HuffStream

A client-server application for transferring files with Huffman encoding-based compression. This system demonstrates data compression techniques in network communications.

## New Features

- **Multiple Clients/Servers**: Support for any number of clients and servers
- **Dual Channels**: Separate channels for data and control transmissions
- **SSL/TLS Security**: Encrypted communications between client and server
- **Graceful Termination**: Proper cleanup to prevent socket binding errors
- **Configuration-based**: No need to rewrite or recompile code for new servers

## Installation

1. Clone the repository:
```bash
git clone https://github.com/karanm6505/HuffStream.git
cd HuffStream
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up the configuration files:
```bash
python scripts/setup_config.py
```

4. Generate SSL certificates:
```bash
python scripts/generate_certificates.py
```

## Configuration

The application uses JSON configuration files located in the `config` directory. Template files are provided and copied to actual configuration files during setup.

### Server Configuration

Edit `config/server_config.json`:

```json
{
  "servers": [
    {
      "host": "0.0.0.0",
      "data_port": 9999,
      "control_port": 9998,
      "save_directory": "received_files",
      "ssl": {
        "enabled": true,
        "cert_file": "config/server.crt",
        "key_file": "config/server.key"
      }
    }
  ],
  "max_connections": 10,
  "buffer_size": 4096
}
```

### Client Configuration

Edit `config/client_config.json`:

```json
{
  "servers": [
    {
      "host": "127.0.0.1",
      "data_port": 9999,
      "control_port": 9998,
      "ssl": {
        "enabled": true,
        "cert_file": "config/server.crt",
        "verify": false
      }
    }
  ],
  "buffer_size": 4096,
  "retry_attempts": 3,
  "retry_delay": 5
}
```

## Usage

### Enhanced Server

```bash
python server/multi_server.py
```

### Enhanced Client

```bash
python client/multi_client.py /path/to/file.txt
```

To specify a different server from the configuration:

```bash
python client/multi_client.py /path/to/file.txt --server 1
```

## Features

- File compression using Huffman coding
- Client-server architecture for file transfer
- SSL/TLS encrypted communications
- Separate channels for data and control messages
- Environment-based configuration
- Support for multiple simultaneous connections

## Project Overview

This application implements a client-server architecture for file transfer with the following features:

- **Huffman Encoding**: Compresses files using Huffman coding algorithm
- **Network Transfer**: Sends compressed files over TCP/IP
- **Decompression**: Reconstructs original files from Huffman-encoded data
- **Compression Statistics**: Displays file size reduction metrics
- **SSL Security**: Encrypts communications between client and server
- **Multi-client Support**: Handles multiple client connections simultaneously

## System Architecture

The project is organized into these main components:

1. **Network Manager**: Handles socket connections, SSL, and threading
2. **Client**: Encodes and sends files to the server
3. **Server**: Receives encoded files, decodes them, and saves both versions
4. **Utilities**: Contains the Huffman encoding/decoding implementation

### Directory Structure

```
HuffStream/
├── client/
│   ├── client.py                # Client application
│   ├── multi_client.py          # Enhanced client application
│   └── sending_files/           # Files to be sent
│   
├── server/
│   ├── server.py                # Server application
│   ├── multi_server.py          # Enhanced server application
│   └── received_files/          # Files received from client
│   
├── config/
│   ├── client_config.json       # Client configuration file
│   ├── server_config.json       # Server configuration file
│   ├── server.crt               # SSL certificate
│   ├── server.key               # SSL key
│   
├── scripts/
│   ├── generate_certificates.py # Script to generate SSL certificates
│   └── setup_config.py          # Script to set up configuration files
│   
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

2. Run the enhanced server:
   ```
   python multi_server.py
   ```
   
   The server will start listening on the configured ports.

### Client Usage

1. Navigate to the client directory:
   ```
   cd client
   ```

2. Place the file you want to send in the `sending_files` directory.

3. Run the enhanced client:
   ```
   python multi_client.py /path/to/file.txt
   ```

4. To specify a different server from the configuration:
   ```
   python multi_client.py /path/to/file.txt --server 1
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
