#!/usr/bin/env python3
"""
Enhanced client for HuffStream supporting SSL and dual channels
"""

import os
import sys
import time
import json
import uuid
import threading
import argparse
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.network_manager import ConnectionManager
from utils.huffman import encode_data

class HuffStreamClient:
    """Client for sending files with Huffman encoding over secure channels"""
    
    def __init__(self):
        # Find project root
        self.project_root = Path(__file__).parent.parent
        config_path = self.project_root / "config" / "client_config.json"
        
        # Initialize connection manager
        self.connection_manager = ConnectionManager(config_path, is_server=False)
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Default server index
        self.current_server = 0
    
    def send_file(self, file_path, server_index=None):
        """Send a file to the server using Huffman encoding"""
        if server_index is not None:
            self.current_server = server_index
        
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found")
            return False
        
        try:
            # Connect to server
            data_socket, control_socket = self.connection_manager.connect_to_server(self.current_server)
            
            # Read the file
            with open(file_path, 'rb') as f:
                file_data = f.read()
                
            # Generate unique transfer ID
            transfer_id = str(uuid.uuid4())
            
            # Encode the data in memory
            print(f"Encoding file using Huffman coding...")
            encoded_data, compression_ratio = encode_data(file_data)
            
            # Get the filename for the encoded version
            filename = os.path.basename(file_path)
            base_name, ext = os.path.splitext(filename)
            encoded_filename = f"{base_name}_encoded{ext}"
            
            filesize = len(encoded_data)
            
            # Send prepare message over control channel
            prepare_msg = {
                'command': 'prepare',
                'transfer_id': transfer_id,
                'filename': encoded_filename,
                'filesize': filesize
            }
            self.connection_manager.send_message(control_socket, json.dumps(prepare_msg))
            
            # Wait for ready response
            response_data = self.connection_manager.receive_message(control_socket)
            if not response_data:
                print("Failed to receive response from server")
                return False
            
            response = json.loads(response_data.decode('utf-8'))
            if response.get('status') != 'ready':
                print(f"Server not ready to receive file: {response}")
                return False
            
            # Send data over data channel
            print(f"Sending file {encoded_filename} ({filesize} bytes, compression: {compression_ratio:.2f}%)...")
            
            # First send metadata with transfer ID
            metadata = {
                'transfer_id': transfer_id
            }
            self.connection_manager.send_message(data_socket, json.dumps(metadata))
            
            # Wait for server ready signal
            ready_signal = self.connection_manager.receive_message(data_socket)
            if not ready_signal or ready_signal.decode('utf-8') != "READY":
                print("Server not ready for data transfer")
                return False
            
            # Send data in chunks
            chunk_size = self.config.get('buffer_size', 4096)
            total_sent = 0
            last_progress = 0
            
            for i in range(0, len(encoded_data), chunk_size):
                chunk = encoded_data[i:i+chunk_size]
                if not self.connection_manager.send_message(data_socket, chunk):
                    print("Failed to send data chunk")
                    return False
                
                total_sent += len(chunk)
                progress = int((total_sent / filesize) * 100)
                if progress >= last_progress + 10:
                    print(f"Progress: {progress}%")
                    last_progress = progress
            
            print("Data transfer complete")
            
            # Wait for completion confirmation
            completion = self.connection_manager.receive_message(data_socket)
            if completion and completion.decode('utf-8') == "COMPLETE":
                print("File successfully sent and processed by server")
                return True
            else:
                print("File transfer incomplete or failed")
                return False
                
        except Exception as e:
            print(f"Error sending file: {e}")
            return False
        finally:
            # Close sockets
            try:
                if 'data_socket' in locals():
                    data_socket.close()
                if 'control_socket' in locals():
                    control_socket.close()
            except:
                pass
    
    def check_transfer_status(self, transfer_id, server_index=None):
        """Check status of a transfer on the server"""
        if server_index is not None:
            self.current_server = server_index
        
        try:
            # Connect to server (control channel only needed)
            _, control_socket = self.connection_manager.connect_to_server(self.current_server)
            
            # Send status request
            status_msg = {
                'command': 'status',
                'transfer_id': transfer_id
            }
            self.connection_manager.send_message(control_socket, json.dumps(status_msg))
            
            # Wait for response
            response_data = self.connection_manager.receive_message(control_socket)
            if not response_data:
                print("Failed to receive response from server")
                return None
            
            response = json.loads(response_data.decode('utf-8'))
            return response.get('status')
                
        except Exception as e:
            print(f"Error checking transfer status: {e}")
            return None
        finally:
            # Close socket
            try:
                if 'control_socket' in locals():
                    control_socket.close()
            except:
                pass

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="HuffStream Client")
    parser.add_argument("file", help="Path to the file to send")
    parser.add_argument("--server", type=int, default=0, help="Server index to use")
    args = parser.parse_args()
    
    # Create client instance
    client = HuffStreamClient()
    
    # Send file
    print(f"Sending file: {args.file}")
    client.send_file(args.file, args.server)

if __name__ == "__main__":
    main()
