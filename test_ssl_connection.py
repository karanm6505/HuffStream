#!/usr/bin/env python3
"""
Test script to verify SSL connection between client and server
"""

import os
import sys
from utils.network_manager import ConnectionManager, SSLContext
import socket
import ssl
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure SSL is enabled
os.environ['SSL_ENABLED'] = 'true'

def test_ssl_connection():
    """Test SSL connection to the server"""
    print("Testing SSL connection to server...")
    
    # Display SSL configuration
    print("\nSSL Configuration:")
    print(f"SSL_ENABLED: {os.environ.get('SSL_ENABLED', 'false')}")
    print(f"SSL_VERIFY: {os.environ.get('SSL_VERIFY', 'false')}")
    print(f"SSL_CERT_PATH: {os.environ.get('SSL_CERT_PATH', 'Not set')}")
    print(f"CLIENT_SERVER_HOST: {os.environ.get('CLIENT_SERVER_HOST', '127.0.0.1')}")
    print(f"CLIENT_DATA_PORT: {os.environ.get('CLIENT_DATA_PORT', '9999')}")
    
    # Create client connection manager
    client = ConnectionManager(is_server=False)
    
    try:
        # Try to connect to server
        data_socket, control_socket = client.connect_to_server()
        
        # Check if sockets are SSL sockets
        print("\nVerifying SSL implementation:")
        is_data_ssl = isinstance(data_socket, ssl.SSLSocket)
        is_control_ssl = isinstance(control_socket, ssl.SSLSocket)
        
        if is_data_ssl and is_control_ssl:
            print("✅ Both data and control connections are using SSL")
            
            # Get SSL version and cipher
            data_version = data_socket.version()
            data_cipher = data_socket.cipher()
            
            print(f"\nSSL Details:")
            print(f"Protocol Version: {data_version}")
            print(f"Cipher Suite: {data_cipher[0] if data_cipher else 'Unknown'}")
            print(f"Cipher Bits: {data_cipher[2] if data_cipher else 'Unknown'}")
            
            # Send test message
            test_message = "PING"
            print(f"\nSending test message: {test_message}")
            client.send_message(data_socket, test_message)
            
            # Receive response
            response = client.receive_message(data_socket)
            if response:
                print(f"Received response: {response.decode('utf-8', errors='ignore')}")
            else:
                print("No response received")
            
            print("\n✅ SSL connection test completed successfully!")
        else:
            print("\n❌ Error: SSL is not being used for the connection!")
            print(f"Data socket using SSL: {is_data_ssl}")
            print(f"Control socket using SSL: {is_control_ssl}")
            
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        try:
            client.stop()
        except:
            pass

if __name__ == "__main__":
    test_ssl_connection()
    print("\nDone.")
