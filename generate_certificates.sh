#!/bin/bash

# Define variables
SSL_DIR="/Users/karanm/HuffStream/ssl"
CERT_FILE="$SSL_DIR/server.crt"
KEY_FILE="$SSL_DIR/server.key"
DAYS_VALID=365
COMMON_NAME="localhost"

mkdir -p "$SSL_DIR"

echo "Generating SSL certificate and key..."
echo "Certificate will be valid for $DAYS_VALID days"
echo "Common Name: $COMMON_NAME"

openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout "$KEY_FILE" \
  -out "$CERT_FILE" \
  -days "$DAYS_VALID" \
  -subj "/CN=$COMMON_NAME" \
  -addext "subjectAltName=DNS:$COMMON_NAME,IP:127.0.0.1,IP:$SERVER_IP"

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
  echo "Certificate and key generated successfully!"
  echo "Certificate path: $CERT_FILE"
  echo "Key path: $KEY_FILE"
  
  echo -e "\nCertificate information:"
  openssl x509 -in "$CERT_FILE" -text -noout | grep -E 'Subject:|Issuer:|Not Before:|Not After:|DNS:|IP Address:'
  
  chmod 600 "$KEY_FILE"
  chmod 644 "$CERT_FILE"
  echo -e "\nPermissions set: Private key (600), Certificate (644)"
else
  echo "Error: Failed to generate certificate or key"
  exit 1
fi
