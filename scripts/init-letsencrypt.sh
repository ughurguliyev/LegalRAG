#!/bin/bash

# Script to initialize Let's Encrypt SSL certificates for production deployment
# Usage: ./scripts/init-letsencrypt.sh [domain] [email]

set -e

# Configuration
DOMAIN=${1:-api.legalrag.ughur.me}
EMAIL=${2:-admin@legalrag.ughur.me}
RSA_KEY_SIZE=4096
DATA_PATH="./certbot"
STAGING=${STAGING:-0} # Set to 1 to use Let's Encrypt staging server

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Let's Encrypt SSL certificates for: ${DOMAIN}${NC}"

# Check if docker-compose is installed
if ! [ -x "$(command -v docker-compose)" ]; then
  echo -e "${RED}Error: docker-compose is not installed.${NC}" >&2
  exit 1
fi

# Create required directories
echo "Creating required directories..."
mkdir -p "$DATA_PATH/conf"
mkdir -p "$DATA_PATH/www"

# Download recommended TLS parameters
if [ ! -e "$DATA_PATH/conf/options-ssl-nginx.conf" ]; then
  echo "Downloading recommended TLS parameters..."
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$DATA_PATH/conf/options-ssl-nginx.conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$DATA_PATH/conf/ssl-dhparams.pem"
fi

# Create dummy certificate for nginx startup
echo "Creating dummy certificate for $DOMAIN..."
CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
mkdir -p "$DATA_PATH/conf/live/$DOMAIN"

# Check if certificate already exists
if [ -e "$DATA_PATH/conf/live/$DOMAIN/fullchain.pem" ]; then
  echo -e "${YELLOW}Certificate already exists for $DOMAIN. Delete it to create a new one.${NC}"
  read -p "Do you want to delete the existing certificate? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Keeping existing certificate."
    exit 0
  fi
  rm -rf "$DATA_PATH/conf/live/$DOMAIN"
  mkdir -p "$DATA_PATH/conf/live/$DOMAIN"
fi

# Generate dummy certificate
docker run --rm \
  -v "$PWD/$DATA_PATH/conf:/etc/letsencrypt" \
  --entrypoint openssl \
  certbot/certbot \
  req -x509 -nodes -newkey rsa:$RSA_KEY_SIZE -days 1 \
    -keyout "$CERT_PATH/privkey.pem" \
    -out "$CERT_PATH/fullchain.pem" \
    -subj "/CN=$DOMAIN"

# Start nginx with dummy certificate
echo "Starting nginx with dummy certificate..."
docker-compose -f docker-compose.prod.yml up -d nginx

# Delete dummy certificate
echo "Deleting dummy certificate..."
docker-compose -f docker-compose.prod.yml run --rm --entrypoint "\
  rm -rf /etc/letsencrypt/live/$DOMAIN && \
  rm -rf /etc/letsencrypt/archive/$DOMAIN && \
  rm -rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot

# Request Let's Encrypt certificate
echo "Requesting Let's Encrypt certificate for $DOMAIN..."

# Set staging argument if needed
STAGING_ARG=""
if [ $STAGING != "0" ]; then
  STAGING_ARG="--staging"
  echo -e "${YELLOW}Using Let's Encrypt staging server${NC}"
fi

# Request certificate
docker-compose -f docker-compose.prod.yml run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $STAGING_ARG \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d $DOMAIN" certbot

# Reload nginx
echo "Reloading nginx configuration..."
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload

echo -e "${GREEN}SSL certificate successfully obtained!${NC}"
echo
echo "To start the production stack, run:"
echo "  docker-compose -f docker-compose.prod.yml up -d"
echo
echo "To renew certificates (runs automatically every 12 hours):"
echo "  docker-compose -f docker-compose.prod.yml run --rm certbot renew" 