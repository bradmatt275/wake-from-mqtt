# Wake from MQTT Project Instructions

This project creates a Python-based MQTT client that listens for wake-on-LAN commands and sends WOL packets to specified devices.

## Project Structure
- Python application using paho-mqtt for MQTT communication
- wakeonlan library for sending WOL packets
- Docker containerization for easy deployment
- YAML configuration for flexibility
- Logging for debugging and monitoring

## Key Components
- main.py: Core MQTT client and WOL functionality
- config.yaml: Configuration file for MQTT broker and target devices
- requirements.txt: Python dependencies
- Dockerfile: Container configuration
- docker-compose.yml: Easy deployment setup

## Development Notes
- Use environment variables for sensitive configuration
- Implement proper error handling and logging
- Follow Python best practices for code structure
- Ensure Docker container runs with minimal privileges