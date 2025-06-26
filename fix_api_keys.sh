#!/bin/bash

# This script updates the API keys in the server's environment files.
# It is intended to be run on the EC2 instance.

# --- Configuration ---
# Replace with your actual API keys
GOOGLE_API_KEY_VALUE="YOUR_GOOGLE_API_KEY_HERE"
OPENAI_API_KEY_VALUE="YOUR_OPENAI_API_KEY_HERE"

# --- Script ---
echo "🚀 Updating API keys on the server..."

# Update .env file
echo "🔑 Updating .env file..."
cat > /opt/DIY-MOD/Backend/.env << EOF
GOOGLE_API_KEY=${GOOGLE_API_KEY_VALUE}
OPENAI_API_KEY=${OPENAI_API_KEY_VALUE}
EOF

# Update .bashrc for persistence across sessions
echo "🔧 Adding keys to .bashrc for future sessions..."
# Remove old keys first to avoid duplicates
sed -i '/DIY_MOD_API_KEYS/d' ~/.bashrc
sed -i '/GOOGLE_API_KEY/d' ~/.bashrc
sed -i '/OPENAI_API_KEY/d' ~/.bashrc

# Add new keys
echo '' >> ~/.bashrc
echo '# --- DIY_MOD_API_KEYS ---' >> ~/.bashrc
echo "export GOOGLE_API_KEY='${GOOGLE_API_KEY_VALUE}'" >> ~/.bashrc
echo "export OPENAI_API_KEY='${OPENAI_API_KEY_VALUE}'" >> ~/.bashrc
echo '# --- END DIY_MOD_API_KEYS ---' >> ~/.bashrc

echo "✅ API keys have been updated."
echo "✅ Please restart the server for the changes to take effect." 