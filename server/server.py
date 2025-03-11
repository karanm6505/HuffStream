import socket
import os
import sys

# Add the parent directory to sys.path to import the utils module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.huffman import encode_data, decode_file

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

def send_encoded_data(conn, original_file_path):
    """Encode a file using Huffman coding and send it to the client without saving."""
    try:
        # Read the original file
        with open(original_file_path, 'rb') as f:
            file_data = f.read()
        
        # Get the filename for the encoded version
        filename = os.path.basename(original_file_path)
        base_name, ext = os.path.splitext(filename)
        encoded_filename = f"{base_name}_encoded{ext}"
        
        # Encode the data in memory
        print(f"Encoding {filename} using Huffman coding...")
        encoded_data, compression_ratio = encode_data(file_data)
        filesize = len(encoded_data)
        
        # Send filename and filesize
        file_info = f"{encoded_filename}|{filesize}"
        conn.send(file_info.encode('utf-8'))
        
        # Send the encoded data
        print(f"Sending encoded data ({filesize} bytes) to client...")
        conn.sendall(encoded_data)
        
        print(f"Encoded data sent successfully (compression ratio: {compression_ratio:.2f}%)")
        return True
    except Exception as e:
        print(f"Error encoding and sending data: {e}")
        return False

def receive_encoded_file(conn, save_dir):
    """Receive an encoded file from the client."""
    try:
        # Receive filename and filesize
        file_info = conn.recv(1024).decode('utf-8')
        filename, filesize = file_info.split('|')
        filesize = int(filesize)
        
        # Create the destination path
        encoded_path = os.path.join(save_dir, filename)
        
        # Receive encoded file data
        print(f"Receiving encoded file {filename} ({filesize} bytes)...")
        received = 0
        with open(encoded_path, 'wb') as file:
            while received < filesize:
                data = conn.recv(4096)
                if not data:
                    break
                file.write(data)
                received += len(data)
                progress = (received / filesize) * 100
                print(f"Progress: {progress:.2f}%", end="\r")
        
        print(f"\nEncoded file {filename} received successfully")
        
        # Create path for decoded file
        base_name, ext = os.path.splitext(filename)
        decoded_filename = base_name.replace('_encoded', '_decoded') + ext
        decoded_path = os.path.join(save_dir, decoded_filename)
        
        # Decode the file
        print(f"Decoding file...")
        decoded_path = decode_file(encoded_path, decoded_path)
        
        print(f"File decoded successfully: {decoded_path}")
        
        return encoded_path, decoded_path
    except Exception as e:
        print(f"Error receiving/decoding file: {e}")
        return None, None

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
                print(f"File saved at {received_file_path}")
                
                # Encode and send back the file (in memory)
                if send_encoded_data(conn, received_file_path):
                    print("Transaction completed successfully")
                else:
                    conn.send("Error encoding the file".encode('utf-8'))
                    
                # Receive and process encoded file
                encoded_path, decoded_path = receive_encoded_file(conn, save_dir)
                
                if encoded_path and decoded_path:
                    conn.send("File received and decoded successfully".encode('utf-8'))
                    print(f"Encoded file saved at: {encoded_path}")
                    print(f"Decoded file saved at: {decoded_path}")
                else:
                    conn.send("Error processing file".encode('utf-8'))
                    
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
