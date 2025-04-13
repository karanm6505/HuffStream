import socket
import ssl
import json
import os
import threading
import time
import sys
from pathlib import Path

class SSLContext:
    """Manages SSL contexts for secure connections"""
    
    @staticmethod
    def create_server_context(cert_file, key_file):
        """Create an SSL context for the server"""
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        try:
            context.load_cert_chain(certfile=cert_file, keyfile=key_file)
            context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # Disable older protocols
            return context
        except (FileNotFoundError, ssl.SSLError) as e:
            print(f"SSL Error: {e}")
            print(f"Make sure certificate files exist: {cert_file}, {key_file}")
            print("Run scripts/generate_certificates.py to create them")
            return None
    
    @staticmethod
    def create_client_context(cert_file=None, verify=False):
        """Create an SSL context for the client"""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        if not verify:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        if cert_file:
            try:
                context.load_verify_locations(cafile=cert_file)
            except (FileNotFoundError, ssl.SSLError) as e:
                print(f"SSL Warning: {e}")
                print(f"Will continue without certificate verification")
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
        return context

class ConnectionManager:
    """Manages network connections for both server and client"""
    
    def __init__(self, config_path, is_server=True):
        self.is_server = is_server
        self.running = False
        self.connections = []
        self.threads = []
        self.ssl_contexts = {}
        
        # Load configuration
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)
            
        # Resolve paths relative to project root
        self.project_root = Path(__file__).parent.parent
            
    def start_server(self, connection_handler, control_handler):
        """Start server listening on all configured ports"""
        if not self.is_server:
            raise RuntimeError("This instance is configured as a client")
            
        self.running = True
        self.server_sockets = []
        
        for server_config in self.config['servers']:
            # Setup SSL if enabled
            ssl_context = None
            if server_config.get('ssl', {}).get('enabled', False):
                cert_file = self.project_root / server_config['ssl'].get('cert_file')
                key_file = self.project_root / server_config['ssl'].get('key_file')
                ssl_context = SSLContext.create_server_context(cert_file, key_file)
                if not ssl_context:
                    print(f"Warning: SSL setup failed for {server_config['host']}:{server_config['data_port']}")
                    # Continue without SSL
            
            # Create data channel socket
            self._start_listening_socket(
                server_config['host'], 
                server_config['data_port'], 
                connection_handler,
                ssl_context,
                'data'
            )
            
            # Create control channel socket
            self._start_listening_socket(
                server_config['host'], 
                server_config['control_port'], 
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
            server_socket.listen(self.config.get('max_connections', 5))
            
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
    
    def connect_to_server(self, server_index=0):
        """Connect to a server as a client"""
        if self.is_server:
            raise RuntimeError("This instance is configured as a server")
        
        if server_index >= len(self.config['servers']):
            raise ValueError(f"Server index {server_index} out of range")
            
        server_config = self.config['servers'][server_index]
        retry_attempts = self.config.get('retry_attempts', 1)
        retry_delay = self.config.get('retry_delay', 5)
        
        # Setup SSL if enabled
        ssl_context = None
        if server_config.get('ssl', {}).get('enabled', False):
            cert_file = None
            if 'cert_file' in server_config['ssl']:
                cert_file = self.project_root / server_config['ssl']['cert_file']
            verify = server_config['ssl'].get('verify', False)
            ssl_context = SSLContext.create_client_context(cert_file, verify)
        
        # Connect data channel
        data_socket = self._connect_socket(
            server_config['host'],
            server_config['data_port'],
            ssl_context,
            retry_attempts,
            retry_delay,
            'data'
        )
        
        # Connect control channel
        control_socket = self._connect_socket(
            server_config['host'],
            server_config['control_port'],
            ssl_context,
            retry_attempts,
            retry_delay,
            'control'
        )
        
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
                        client_socket = ssl_context.wrap_socket(
                            client_socket,
                            server_hostname=host if ssl_context.check_hostname else None
                        )
                        print(f"SSL {channel_type} connection established")
                    except ssl.SSLError as e:
                        print(f"SSL error: {e}")
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
            buffer_size = self.config.get('buffer_size', 4096)
            
        try:
            data = sock.recv(buffer_size)
            if not data:  # Connection closed by remote host
                return None
            return data
        except (socket.error, ssl.SSLError) as e:
            print(f"Error receiving message: {e}")
            return None
