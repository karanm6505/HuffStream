import socket
import ssl
import os
import threading
import time
import sys
from pathlib import Path

class SSLContext:
    """Manages SSL contexts for secure connections using OpenSSL directly"""
    
    @staticmethod
    def create_client_context():
        """Create an SSL context for the client using environment variables"""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        # Use environment variables for SSL configuration
        verify = os.environ.get("SSL_VERIFY", "false").lower() == "true"
        cert_path = os.environ.get("SSL_CERT_PATH")
        
        if verify:
            verification_mode = os.environ.get("SSL_VERIFICATION_MODE", "required")
            
            if verification_mode == "required":
                context.verify_mode = ssl.CERT_REQUIRED
                context.check_hostname = True
            elif verification_mode == "optional":
                context.verify_mode = ssl.CERT_OPTIONAL
                context.check_hostname = False
            else:
                context.verify_mode = ssl.CERT_NONE
                context.check_hostname = False
            
            # If certificate path is provided, load it
            if cert_path:
                try:
                    context.load_verify_locations(cafile=cert_path)
                    print(f"Using certificate at {cert_path} for verification")
                except (FileNotFoundError, ssl.SSLError) as e:
                    print(f"SSL Warning: {e}")
                    print("Cannot proceed with verification without valid certificate")
                    if context.verify_mode == ssl.CERT_REQUIRED:
                        raise
                    else:
                        # Fall back to no verification if not required
                        print("Falling back to no certificate verification")
                        context.check_hostname = False
                        context.verify_mode = ssl.CERT_NONE
        else:
            # No verification
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
        # Set secure protocol options
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # Disable older protocols
        
        return context
    
    @staticmethod
    def create_server_context():
        """Create an SSL context for the server using environment variables"""
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        
        cert_path = os.environ.get("SSL_CERT_PATH")
        key_path = os.environ.get("SSL_KEY_PATH")
        
        if not cert_path or not key_path:
            raise ValueError("SSL_CERT_PATH and SSL_KEY_PATH environment variables must be set")
        
        try:
            context.load_cert_chain(certfile=cert_path, keyfile=key_path)
            print(f"Using certificate at {cert_path} and key at {key_path}")
        except (FileNotFoundError, ssl.SSLError) as e:
            print(f"SSL Error: {e}")
            raise
        
        # Set secure protocol options
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # Disable older protocols
        
        return context
    
    @staticmethod
    def verify_ssl_connection(socket_conn):
        """Verify if a socket is using SSL and return connection details"""
        if not isinstance(socket_conn, ssl.SSLSocket):
            return {
                "secure": False,
                "message": "Connection is not using SSL/TLS"
            }
        
        # Get SSL/TLS version
        version = socket_conn.version()
        
        # Get cipher being used
        cipher = socket_conn.cipher()
        cipher_name = cipher[0] if cipher else "Unknown"
        cipher_bits = cipher[2] if cipher else "Unknown"
        
        # Check if certificate verification was done
        cert_verified = "verified" if socket_conn.context.verify_mode != ssl.CERT_NONE else "not verified"
        
        return {
            "secure": True,
            "version": version,
            "cipher": cipher_name,
            "bits": cipher_bits,
            "certificate": cert_verified
        }

class ConnectionManager:
    """Manages network connections for both server and client"""
    
    def __init__(self, is_server=True):
        self.is_server = is_server
        self.running = False
        self.connections = []
        self.threads = []
        self.ssl_contexts = {}
            
        # Resolve paths relative to project root
        self.project_root = Path(__file__).parent.parent
            
    def start_server(self, connection_handler, control_handler):
        """Start server listening on all configured ports"""
        if not self.is_server:
            raise RuntimeError("This instance is configured as a client")
            
        self.running = True
        self.server_sockets = []
        
        # Get server configuration from environment variables
        host = os.environ.get('SERVER_HOST', '0.0.0.0')
        data_port = int(os.environ.get('SERVER_DATA_PORT', '9999'))
        control_port = int(os.environ.get('SERVER_CONTROL_PORT', '9998'))
        ssl_enabled = os.environ.get('SSL_ENABLED', 'false').lower() == 'true'
        
        # Setup SSL if enabled
        ssl_context = None
        if ssl_enabled:
            ssl_context = SSLContext.create_server_context()
            if not ssl_context:
                print(f"Warning: SSL setup failed for {host}:{data_port}")
                # Continue without SSL
        
        # Create data channel socket
        self._start_listening_socket(
            host, 
            data_port, 
            connection_handler,
            ssl_context,
            'data'
        )
        
        # Create control channel socket
        self._start_listening_socket(
            host, 
            control_port, 
            control_handler,
            ssl_context,
            'control'
        )
            
        print(f"Server started with {len(self.threads)} listening threads")
        print("Press Ctrl+C to stop the server")
    
    def _start_listening_socket(self, host, port, handler_func, ssl_context, channel_type):
        """Start a socket listening on the specified host and port"""
        try:
            # Create socket
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind and listen
            server_socket.bind((host, port))
            max_connections = int(os.environ.get('MAX_CONNECTIONS', '5'))
            server_socket.listen(max_connections)
            
            self.server_sockets.append(server_socket)
            print(f"Listening for {channel_type} connections on {host}:{port}")
            
            # Start listener thread
            thread = threading.Thread(
                target=self._accept_connections,
                args=(server_socket, handler_func, ssl_context, channel_type),
                daemon=True
            )
            thread.start()
            self.threads.append(thread)
            
        except socket.error as e:
            print(f"Socket error on {host}:{port}: {e}")
    
    def _accept_connections(self, server_socket, handler_func, ssl_context, channel_type):
        """Accept incoming connections and start handler threads"""
        while self.running:
            try:
                client_socket, client_address = server_socket.accept()
                print(f"New {channel_type} connection from {client_address[0]}:{client_address[1]}")
                
                # Wrap with SSL if configured
                if ssl_context:
                    try:
                        client_socket = ssl_context.wrap_socket(
                            client_socket, 
                            server_side=True
                        )
                    except ssl.SSLError as e:
                        print(f"SSL error with {client_address}: {e}")
                        client_socket.close()
                        continue
                
                # Start handler thread
                client_thread = threading.Thread(
                    target=handler_func,
                    args=(client_socket, client_address, channel_type),
                    daemon=True
                )
                client_thread.start()
                
                with threading.Lock():
                    self.connections.append((client_socket, client_thread))
                
            except socket.error as e:
                if self.running:  # Only show error if we're supposed to be running
                    print(f"Error accepting connection: {e}")
            except Exception as e:
                print(f"Unexpected error in connection acceptance: {e}")
    
    def connect_to_server(self):
        """Connect to a server as a client"""
        if self.is_server:
            raise RuntimeError("This instance is configured as a server")
            
        # Get client configuration from environment variables
        host = os.environ.get('CLIENT_SERVER_HOST', '127.0.0.1')
        data_port = int(os.environ.get('CLIENT_DATA_PORT', '9999'))
        control_port = int(os.environ.get('CLIENT_CONTROL_PORT', '9998'))
        retry_attempts = int(os.environ.get('RETRY_ATTEMPTS', '3'))
        retry_delay = int(os.environ.get('RETRY_DELAY', '5'))
        ssl_enabled = os.environ.get('SSL_ENABLED', 'false').lower() == 'true'
        
        # Setup SSL if enabled
        ssl_context = None
        if ssl_enabled:
            ssl_context = SSLContext.create_client_context()
        
        # Connect data channel
        data_socket = self._connect_socket(
            host,
            data_port,
            ssl_context,
            retry_attempts,
            retry_delay,
            'data'
        )
        
        # Connect control channel
        control_socket = self._connect_socket(
            host,
            control_port,
            ssl_context,
            retry_attempts,
            retry_delay,
            'control'
        )
        
        # Verify if connection is secure
        if ssl_enabled:
            data_security = SSLContext.verify_ssl_connection(data_socket)
            control_security = SSLContext.verify_ssl_connection(control_socket)
            
            if data_security["secure"] and control_security["secure"]:
                print("\n✅ Secure connection established successfully!")
                print(f"Protocol: {data_security['version']}")
                print(f"Cipher: {data_security['cipher']} ({data_security['bits']} bits)")
                print(f"Certificate: {data_security['certificate']}")
            else:
                print("\n⚠️  Warning: Connection is not secure!")
                print("SSL was requested but could not be established.")
                print("Check your SSL configuration and certificate paths.")
        else:
            print("\n⚠️  Warning: Connection is not encrypted!")
            print("SSL is disabled. Enable SSL for secure communication.")
        
        return data_socket, control_socket
        
    def _connect_socket(self, host, port, ssl_context, retry_attempts, retry_delay, channel_type):
        """Establish a connection to the server with retries"""
        for attempt in range(retry_attempts):
            try:
                # Create socket
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
                print(f"Connecting to {host}:{port} ({channel_type} channel)...")
                client_socket.connect((host, port))
                
                # Wrap with SSL if configured
                if ssl_context:
                    try:
                        # This is where certificate verification happens
                        client_socket = ssl_context.wrap_socket(
                            client_socket,
                            server_hostname=host if ssl_context.check_hostname else None
                        )
                        
                        # Explicitly verify and show certificate details
                        if ssl_context.verify_mode != ssl.CERT_NONE:
                            cert = client_socket.getpeercert()
                            if cert:
                                print("Server certificate verified:")
                                if 'subject' in cert:
                                    for item in cert['subject']:
                                        for key, value in item:
                                            if key == 'commonName':
                                                print(f"  - Common Name: {value}")
                                print(f"  - Issuer: {cert.get('issuer', 'Unknown')}")
                                print(f"  - Valid until: {cert.get('notAfter', 'Unknown')}")
                            else:
                                print("Warning: No certificate information available")
                        else:
                            print("Warning: SSL certificate verification is disabled")
                            
                        print(f"SSL {channel_type} connection established")
                    except ssl.SSLError as e:
                        print(f"SSL certificate verification failed: {e}")
                        client_socket.close()
                        if attempt == retry_attempts - 1:
                            raise
                        continue
                    except ssl.CertificateError as e:
                        print(f"Certificate verification error: {e}")
                        client_socket.close()
                        if attempt == retry_attempts - 1:
                            raise
                        continue
                
                print(f"{channel_type.capitalize()} channel connected")
                return client_socket
                
            except (socket.error, ssl.SSLError) as e:
                if attempt < retry_attempts - 1:
                    print(f"Connection attempt {attempt + 1} failed: {e}")
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print(f"Failed to connect after {retry_attempts} attempts: {e}")
                    raise
        
        return None  # Should not reach here due to raising exception
    
    def stop(self):
        """Stop all connections and threads"""
        print("Stopping connection manager...")
        self.running = False
        
        # Close all client connections
        for client_socket, _ in self.connections:
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
                client_socket.close()
            except:
                pass  # Ignore errors during shutdown
        
        # Close all server sockets if we're a server
        if self.is_server:
            for server_socket in self.server_sockets:
                try:
                    server_socket.close()
                except:
                    pass
        
        print("All connections closed")
    
    def send_message(self, sock, message):
        """Send a message through the socket"""
        try:
            if isinstance(message, str):
                message = message.encode('utf-8')
            sock.sendall(message)
            return True
        except (socket.error, ssl.SSLError) as e:
            print(f"Error sending message: {e}")
            return False
    
    def receive_message(self, sock, buffer_size=None):
        """Receive a message from the socket"""
        if buffer_size is None:
            buffer_size = int(os.environ.get('BUFFER_SIZE', '4096'))
            
        try:
            data = sock.recv(buffer_size)
            if not data:  # Connection closed by remote host
                return None
            return data
        except (socket.error, ssl.SSLError) as e:
            print(f"Error receiving message: {e}")
            return None
