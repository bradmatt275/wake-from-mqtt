#!/usr/bin/env python3
"""
MQTT Wake-on-LAN Service

A Python service that listens to MQTT messages and sends Wake-on-LAN packets
to wake up devices on the network.
"""

import json
import logging
import os
import signal
import sys
import time
from typing import Dict, Any, Optional
from wakeonlan import send_magic_packet
import paho.mqtt.client as mqtt


class MQTTWOLService:
    """MQTT Wake-on-LAN service that listens for wake commands via MQTT."""
    
    def __init__(self):
        """Initialize the service with configuration from environment variables."""
        self.config = self._load_config_from_env()
        self.mqtt_client = None
        self.running = False
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _load_config_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        # Required environment variables
        broker = os.getenv('MQTT_BROKER')
        if not broker:
            print("ERROR: MQTT_BROKER environment variable is required")
            sys.exit(1)
            
        topic = os.getenv('MQTT_TOPIC', 'home/wake')
        
        config = {
            'mqtt': {
                'broker': broker,
                'port': int(os.getenv('MQTT_PORT', '1883')),
                'username': os.getenv('MQTT_USERNAME'),
                'password': os.getenv('MQTT_PASSWORD'),
                'use_tls': os.getenv('MQTT_USE_TLS', 'false').lower() == 'true',
                'topic': topic
            }
        }
        
        return config
        
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the MQTT client connects to the broker."""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            topic = self.config['mqtt']['topic']
            client.subscribe(topic)
            self.logger.info(f"Subscribed to topic: {topic}")
        else:
            self.logger.error(f"Failed to connect to MQTT broker, return code {rc}")
            
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the MQTT client disconnects from the broker."""
        if rc != 0:
            self.logger.warning("Unexpected disconnection from MQTT broker")
        else:
            self.logger.info("Disconnected from MQTT broker")
            
    def _on_message(self, client, userdata, msg):
        """Callback for when a message is received from MQTT."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            self.logger.info(f"Received message on topic '{topic}': {payload}")
            
            # Parse the message
            try:
                message_data = json.loads(payload)
            except json.JSONDecodeError:
                # If not JSON, treat as plain text - could be device name or MAC address
                payload_clean = payload.strip()
                if self._is_mac_address(payload_clean):
                    message_data = {"mac_address": payload_clean}
                else:
                    message_data = {"device": payload_clean}
            
            # Handle direct MAC address in message
            if 'mac_address' in message_data:
                mac_address = message_data['mac_address']
                ip_address = message_data.get('ip_address')  # Optional
                device_name = message_data.get('device', f"device-{mac_address[-5:]}")  # Use last 5 chars as name
                
                device_config = {
                    'name': device_name,
                    'mac_address': mac_address,
                    'ip_address': ip_address
                }
                
                self._wake_device(device_config)
                return
            
            # Handle device name lookup (no longer supported without config file)
            device_name = message_data.get('device', '')
            
            if device_name:
                self.logger.warning(f"Device name '{device_name}' specified, but no config file loaded. Please use MAC address instead.")
                self.logger.info("Send MAC address directly: 'AA:BB:CC:DD:EE:FF' or JSON: '{\"mac_address\": \"AA:BB:CC:DD:EE:FF\"}'")
                return
                
            self.logger.warning("No mac_address specified in message. Please send MAC address directly.")
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            
    def _wake_device(self, device_config: Dict[str, Any]):
        """Send Wake-on-LAN packet to the specified device."""
        try:
            mac_address = device_config['mac_address']
            device_name = device_config['name']
            ip_address = device_config.get('ip_address')
            
            self.logger.info(f"Sending WOL packet to device '{device_name}' ({mac_address})")
            
            if ip_address:
                send_magic_packet(mac_address, ip_address=ip_address)
                self.logger.info(f"WOL packet sent to {device_name} at {ip_address}")
            else:
                send_magic_packet(mac_address)
                self.logger.info(f"WOL packet sent to {device_name} (broadcast)")
                
        except Exception as e:
            self.logger.error(f"Failed to send WOL packet to {device_name}: {e}")
            

            
    def _is_mac_address(self, text: str) -> bool:
        """Check if the text looks like a MAC address."""
        import re
        # Match MAC address patterns like AA:BB:CC:DD:EE:FF or AA-BB-CC-DD-EE-FF
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(mac_pattern, text))
            
    def _setup_mqtt_client(self):
        """Setup and configure the MQTT client."""
        self.mqtt_client = mqtt.Client()
        
        # Set callbacks
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnect
        self.mqtt_client.on_message = self._on_message
        
        # Set authentication if provided
        username = self.config['mqtt'].get('username')
        password = self.config['mqtt'].get('password')
        if username and password:
            self.mqtt_client.username_pw_set(username, password)
            
        # Enable TLS if specified
        if self.config['mqtt'].get('use_tls', False):
            self.mqtt_client.tls_set()
            
    def run(self):
        """Start the MQTT WOL service."""
        self.logger.info("Starting MQTT Wake-on-LAN service")
        
        # Log configuration (without sensitive data)
        self.logger.info(f"MQTT Broker: {self.config['mqtt']['broker']}:{self.config['mqtt']['port']}")
        self.logger.info(f"MQTT Topic: {self.config['mqtt']['topic']}")
        self.logger.info("Send MAC addresses directly via MQTT (no config file needed)")
        
        # Setup MQTT client
        self._setup_mqtt_client()
        
        # Connect to MQTT broker
        try:
            broker = self.config['mqtt']['broker']
            port = self.config['mqtt']['port']
            self.mqtt_client.connect(broker, port, keepalive=60)
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            return
            
        # Start the MQTT loop in a separate thread
        self.mqtt_client.loop_start()
        self.running = True
        
        try:
            # Keep the main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            self.logger.info("Shutting down service")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()


def main():
    """Main entry point."""
    service = MQTTWOLService()
    service.run()


if __name__ == "__main__":
    main()