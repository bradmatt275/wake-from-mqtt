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
import yaml
from typing import Dict, Any, Optional
from wakeonlan import send_magic_packet
import paho.mqtt.client as mqtt


class MQTTWOLService:
    """MQTT Wake-on-LAN service that listens for wake commands via MQTT."""
    
    def __init__(self, config_file: str = "config.yaml"):
        """Initialize the service with configuration."""
        self.config = self._load_config(config_file)
        self.mqtt_client = None
        self.running = False
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML file with environment variable overrides."""
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.error(f"Configuration file {config_file} not found")
            sys.exit(1)
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing configuration file: {e}")
            sys.exit(1)
            
        # Override with environment variables
        config['mqtt']['broker'] = os.getenv('MQTT_BROKER', config['mqtt']['broker'])
        config['mqtt']['port'] = int(os.getenv('MQTT_PORT', config['mqtt']['port']))
        config['mqtt']['username'] = os.getenv('MQTT_USERNAME', config['mqtt'].get('username'))
        config['mqtt']['password'] = os.getenv('MQTT_PASSWORD', config['mqtt'].get('password'))
        config['mqtt']['topic'] = os.getenv('MQTT_TOPIC', config['mqtt']['topic'])
        
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
            
            # Handle device name lookup (original behavior)
            device_name = message_data.get('device', '').lower()
            
            if not device_name:
                self.logger.warning("No device or mac_address specified in message")
                return
                
            # Find device in configuration
            device_config = None
            for device in self.config.get('devices', []):
                if device['name'].lower() == device_name:
                    device_config = device
                    break
                    
            if not device_config:
                self.logger.warning(f"Device '{device_name}' not found in configuration")
                self._list_available_devices()
                return
                
            # Send Wake-on-LAN packet
            self._wake_device(device_config)
            
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
            
    def _list_available_devices(self):
        """Log the list of available devices."""
        devices = self.config.get('devices', [])
        if devices:
            device_names = [device['name'] for device in devices]
            self.logger.info(f"Available devices: {', '.join(device_names)}")
        else:
            self.logger.info("No devices configured")
            
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
        self._list_available_devices()
        
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
    config_file = os.getenv('CONFIG_FILE', 'config.yaml')
    service = MQTTWOLService(config_file)
    service.run()


if __name__ == "__main__":
    main()