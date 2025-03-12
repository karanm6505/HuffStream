import socket
import os
import sys
import subprocess

def receive_file(conn, save_dir):
    """Receive a file from the client."""
    # Receive filename and filesize
    file_info = conn.recv(1024).decode('utf-8')
    filename, filesize = file_info.split('|')
    filesize = int(filesize)
    
    # Create the destination path
    dest_path = os.path.join(save_dir, os.path.basename(filename))
    
    # Receive file data
    print(f"Receiving {filename} ({filesize} bytes)...")
    received = 0
    with open(dest_path, 'wb') as file:
        while received < filesize:
            data = conn.recv(4096)
            if not data:
                break
            file.write(data)
            received += len(data)
            progress = (received / filesize) * 100
            print(f"Progress: {progress:.2f}%", end="\r")
    
    print(f"\nFile {filename} received successfully")
    return dest_path

def decode_received_file(encoded_file_path):
    """Decode a received file using decode_file.py script."""
    try:
        # Create path for decoded file
        filename = os.path.basename(encoded_file_path)
        base_name, ext = os.path.splitext(filename)
        decoded_filename = base_name.replace('_encoded', '_decoded') + ext
        save_dir = os.path.dirname(encoded_file_path)
        decoded_path = os.path.join(save_dir, decoded_filename)
        
        # Get path to decode_file.py script
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        decode_script = os.path.join(project_root, 'utils', 'decode_file.py')
        
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

def start_server(host='0.0.0.0', port=9999):
    """Start a server listening for incoming file transfers."""
    # Create save directory if it doesn't exist
    save_dir = os.path.join(os.path.dirname(__file__), 'received_files')
    os.makedirs(save_dir, exist_ok=True)
    
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Set socket option to reuse address
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind to the port
    server_socket.bind((host, port))
    
    # Listen for incoming connections
    server_socket.listen(5)
    print(f"Server listening on {host}:{port}")

    try:
        while True:
            # Accept connection
            conn, addr = server_socket.accept()
            print(f"Connection from {addr}")
            
            try:
                # Receive and save file
                received_file_path = receive_file(conn, save_dir)
                print(f"Encoded file saved at {received_file_path}")
                
                # Decode the received file
                decoded_file_path = decode_received_file(received_file_path)
                
                if decoded_file_path:
                    conn.send("File received and decoded successfully".encode('utf-8'))
                    print(f"Decoded file saved at: {decoded_file_path}")
                else:
                    conn.send("File received but decoding failed".encode('utf-8'))
                
            except Exception as e:
                print(f"Error handling file transfer: {e}")
                conn.send(f"Error: {str(e)}".encode('utf-8'))
            finally:
                conn.close()
    
    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()
