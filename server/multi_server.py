#!/usr/bin/env python3
"""
Enhanced server for HuffStream supporting multiple clients, SSL, and dual channels
"""

import os
import sys
import subprocess
import threading
import json
import time
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.network_manager import ConnectionManager

class HuffStreamServer:
    """Multi-threaded server for receiving Huffman encoded files"""
    
    def __init__(self):
        # Find project root
        self.project_root = Path(__file__).parent.parent
        config_path = self.project_root / "config" / "server_config.json"
        
        # Initialize connection manager
        self.connection_manager = ConnectionManager(config_path, is_server=True)
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Create directories for received files
        self.save_dir = os.path.join(
            os.path.dirname(__file__), 
            self.config['servers'][0].get('save_directory', 'received_files')
        )
        os.makedirs(self.save_dir, exist_ok=True)
        
        # Active transfers tracking
        self.transfers = {}
        self.transfers_lock = threading.Lock()
        
    def start(self):
        """Start the server"""
        try:
            self.connection_manager.start_server(
                self.handle_data_connection, 
                self.handle_control_connection
            )
            
            # Keep main thread alive
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down server...")
        finally:
            self.connection_manager.stop()
    
    def handle_control_connection(self, client_socket, client_address, channel_type):
        """Handle client control connections"""
        print(f"Control connection established with {client_address[0]}:{client_address[1]}")
        
        try:
            while True:
                # Receive control message
                data = self.connection_manager.receive_message(client_socket)
                if not data:
                    print(f"Control connection closed by {client_address[0]}:{client_address[1]}")
                    break
                    
                # Parse control message
                try:
                    control_msg = json.loads(data.decode('utf-8'))
                    command = control_msg.get('command')
                    
                    # Process command
                    if command == 'prepare':
                        # Client is preparing to send a file
                        transfer_id = control_msg.get('transfer_id')
                        filename = control_msg.get('filename')
                        filesize = control_msg.get('filesize')
                        
                        # Register new transfer
                        with self.transfers_lock:
                            self.transfers[transfer_id] = {
                                'filename': filename,
                                'filesize': filesize,
                                'status': 'prepared',
                                'dest_path': os.path.join(self.save_dir, os.path.basename(filename))
                            }
                        
                        # Send acknowledgment
                        response = {
                            'status': 'ready',
                            'transfer_id': transfer_id
                        }
                        self.connection_manager.send_message(client_socket, json.dumps(response))
                        print(f"Ready to receive file {filename} ({filesize} bytes)")
                        
                    elif command == 'status':
                        # Client is asking about transfer status
                        transfer_id = control_msg.get('transfer_id')
                        status = 'unknown'
                        
                        with self.transfers_lock:
                            if transfer_id in self.transfers:
                                status = self.transfers[transfer_id]['status']
                        
                        # Send status
                        response = {
                            'status': status,
                            'transfer_id': transfer_id
                        }
                        self.connection_manager.send_message(client_socket, json.dumps(response))
                        
                    elif command == 'cancel':
                        # Client wants to cancel transfer
                        transfer_id = control_msg.get('transfer_id')
                        
                        with self.transfers_lock:
                            if transfer_id in self.transfers:
                                self.transfers[transfer_id]['status'] = 'cancelled'
                        
                        # Send acknowledgment
                        response = {
                            'status': 'cancelled',
                            'transfer_id': transfer_id
                        }
                        self.connection_manager.send_message(client_socket, json.dumps(response))
                        
                except json.JSONDecodeError:
                    print(f"Received invalid control message from {client_address[0]}")
                    
        except Exception as e:
            print(f"Error handling control connection: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass  # Ignore errors during socket closure
    
    def handle_data_connection(self, client_socket, client_address, channel_type):
        """Handle client data connections"""
        print(f"Data connection established with {client_address[0]}:{client_address[1]}")
        
        try:
            # Receive transfer ID
            data = self.connection_manager.receive_message(client_socket)
            if not data:
                print(f"Data connection closed by {client_address[0]}:{client_address[1]}")
                return
            
            # Parse transfer metadata
            try:
                metadata = json.loads(data.decode('utf-8'))
                transfer_id = metadata.get('transfer_id')
                
                # Check if this is a registered transfer
                with self.transfers_lock:
                    if transfer_id not in self.transfers:
                        print(f"Unknown transfer ID from {client_address[0]}")
                        return
                    
                    transfer = self.transfers[transfer_id]
                    dest_path = transfer['dest_path']
                    filesize = transfer['filesize']
                    
                    # Update status
                    transfer['status'] = 'receiving'
                
                # Send ready signal
                self.connection_manager.send_message(client_socket, "READY")
                
                # Receive file data
                print(f"Receiving file for transfer {transfer_id}...")
                received = 0
                last_progress = 0
                
                with open(dest_path, 'wb') as file:
                    while received < filesize:
                        data = self.connection_manager.receive_message(client_socket)
                        if not data:
                            break
                            
                        file.write(data)
                        received += len(data)
                        
                        # Update progress occasionally
                        progress = int((received / filesize) * 100)
                        if progress >= last_progress + 10:
                            print(f"Progress: {progress}%")
                            last_progress = progress
                
                if received == filesize:
                    print(f"File received successfully: {dest_path}")
                    
                    # Update status
                    with self.transfers_lock:
                        self.transfers[transfer_id]['status'] = 'received'
                    
                    # Decode the file
                    decoded_file_path = self.decode_received_file(dest_path)
                    
                    with self.transfers_lock:
                        if decoded_file_path:
                            self.transfers[transfer_id]['status'] = 'decoded'
                            self.transfers[transfer_id]['decoded_path'] = decoded_file_path
                        else:
                            self.transfers[transfer_id]['status'] = 'decode_failed'
                    
                    # Send completion message
                    self.connection_manager.send_message(client_socket, "COMPLETE")
                else:
                    print(f"Incomplete file received: {received}/{filesize} bytes")
                    
                    # Update status
                    with self.transfers_lock:
                        self.transfers[transfer_id]['status'] = 'incomplete'
                    
                    # Send error message
                    self.connection_manager.send_message(client_socket, "INCOMPLETE")
                
            except json.JSONDecodeError:
                print(f"Received invalid transfer metadata from {client_address[0]}")
            
        except Exception as e:
            print(f"Error handling data connection: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass  # Ignore errors during socket closure
    
    def decode_received_file(self, encoded_file_path):
        """Decode a received file using decode_file.py script"""
        try:
            # Create path for decoded file
            filename = os.path.basename(encoded_file_path)
            base_name, ext = os.path.splitext(filename)
            decoded_filename = base_name.replace('_encoded', '_decoded') + ext
            save_dir = os.path.dirname(encoded_file_path)
            decoded_path = os.path.join(save_dir, decoded_filename)
            
            # Get path to decode_file.py script
            decode_script = os.path.join(self.project_root, 'utils', 'decode_file.py')
            
            # Run the decoding script
            print(f"Decoding file using Huffman coding...")
            print(f"Running: python3 {decode_script} {encoded_file_path} {decoded_path}")
            
            result = subprocess.run(
                [sys.executable, decode_script, encoded_file_path, decoded_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"File decoded successfully: {decoded_path}")
                return decoded_path
            else:
                print(f"Error decoding file: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error during decoding: {e}")
            return None

if __name__ == "__main__":
    server = HuffStreamServer()
    server.start()
