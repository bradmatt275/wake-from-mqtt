#!/bin/bash

# Local development script
# This sets up a local environment for testing

echo "🚀 Setting up local development environment"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Set environment variables for local testing
export MQTT_BROKER="127.0.0.1"  # Change to your test broker IP
export MQTT_PORT="1883"
export MQTT_TOPIC="test/wake"
export MQTT_USE_TLS="false"
export LOG_LEVEL="DEBUG"

echo "🔧 Environment variables set:"
echo "  MQTT_BROKER: $MQTT_BROKER"
echo "  MQTT_PORT: $MQTT_PORT"
echo "  MQTT_TOPIC: $MQTT_TOPIC"
echo "  LOG_LEVEL: $LOG_LEVEL"

echo ""
echo "🎯 Ready to test! Run:"
echo "  python3 main.py"
echo ""
echo "📡 Test with MQTT messages:"
echo "  mosquitto_pub -h $MQTT_BROKER -t '$MQTT_TOPIC' -m 'AA:BB:CC:DD:EE:FF'"
echo "  mosquitto_pub -h $MQTT_BROKER -t '$MQTT_TOPIC' -m '{\"mac_address\": \"AA:BB:CC:DD:EE:FF\", \"device\": \"Test PC\"}'"