#!/usr/bin/env python3
"""
Generate self-signed SSL certificates for HuffStream
"""

import os
import subprocess
import sys

def generate_self_signed_cert(cert_dir="config"):
    """Generate self-signed SSL certificate and key"""
    # Create directory if it doesn't exist
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)
    
    cert_file = os.path.join(cert_dir, "server.crt")
    key_file = os.path.join(cert_dir, "server.key")
    
    # Check if files already exist
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"Certificate files already exist at {cert_file} and {key_file}")
        overwrite = input("Do you want to overwrite them? (y/n): ").lower()
        if overwrite != 'y':
            print("Certificate generation canceled.")
            return
    
    print(f"Generating self-signed SSL certificate and key in {cert_dir}...")
    
    # Generate key and certificate with OpenSSL
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:4096", 
        "-keyout", key_file,
        "-out", cert_file,
        "-days", "365", 
        "-nodes",  # No password
        "-subj", "/CN=HuffStream/O=HuffStream/C=US"  # Subject info
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Successfully generated:")
        print(f"  Certificate: {cert_file}")
        print(f"  Key: {key_file}")
        
        # Make them readable by the application only
        os.chmod(key_file, 0o600)
        os.chmod(cert_file, 0o644)
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to generate certificates: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: OpenSSL not found. Please install OpenSSL and try again.")
        sys.exit(1)

if __name__ == "__main__":
    generate_self_signed_cert()
