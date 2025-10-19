# MQTT Wake-on-LAN Service

[![Build and Push Docker Image](https://github.com/bradmatt275/wake-from-mqtt/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/bradmatt275/wake-from-mqtt/actions/workflows/docker-publish.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/ghcr.io/bradmatt275/wake-from-mqtt)](https://github.com/bradmatt275/wake-from-mqtt/pkgs/container/wake-from-mqtt)

A lightweight Python service that listens to MQTT messages and sends Wake-on-LAN (WOL) packets to wake up devices on your network. Perfect for Home Assistant integration and cross-VLAN Wake-on-LAN scenarios.

## Features

- 🔌 MQTT client for receiving wake commands
- 💤 Wake-on-LAN packet transmission
- 🐳 Docker containerized for easy deployment
- 🔧 YAML configuration with environment variable overrides
- 📝 Comprehensive logging
- 🔒 Security-focused (runs as non-root user)
- 🎯 Support for targeted IP or broadcast WOL packets

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone or download this project**

2. **Set up your MQTT broker connection**
   
   Create a `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env with your MQTT broker details (MQTT_BROKER is required)
   ```

4. **Start the service**
   ```bash
   docker-compose up -d
   ```

5. **Test it**
   
   Send an MQTT message to wake a device:
   ```bash
   # Using mosquitto_pub (if you have MQTT clients installed)
   mosquitto_pub -h your-mqtt-broker -t "home/wake" -m "my-pc"
   
   # Or send JSON for more control
   mosquitto_pub -h your-mqtt-broker -t "home/wake" -m '{"device": "my-pc"}'
   ```

## Configuration

All configuration is done via environment variables - no config files needed!

### Environment Variables

You can override any configuration using environment variables:

- `MQTT_BROKER` - MQTT broker hostname/IP (**required**)
- `MQTT_PORT` - MQTT broker port (default: 1883)
- `MQTT_USERNAME` - MQTT username (optional)
- `MQTT_PASSWORD` - MQTT password (optional)
- `MQTT_TOPIC` - MQTT topic to listen on (default: "home/wake")
- `MQTT_USE_TLS` - Enable TLS/SSL (default: false)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

## MQTT Message Format

The service accepts multiple message formats:

### 1. Direct MAC Address (Recommended)
```
AA:BB:CC:DD:EE:FF
```

### 2. JSON Format with Direct MAC Address
```json
{
  "mac_address": "AA:BB:CC:DD:EE:FF"
}
```

### 3. JSON Format with MAC Address and Target IP
```json
{
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "ip_address": "192.168.1.50",
  "device": "My Gaming PC"
}
```

**How it works:**
- **Direct MAC address**: Sends WOL packet directly to that MAC address
- **JSON with MAC**: Allows you to specify MAC address, optional target IP, and optional device name for logging

## Home Assistant Integration

Add this to your Home Assistant configuration:

### configuration.yaml
```yaml
mqtt:
  button:
    - name: "Wake Desktop PC"
      command_topic: "home/wake"
      payload_press: "desktop"
      icon: "mdi:power"
      
    - name: "Wake Gaming PC"
      command_topic: "home/wake" 
      payload_press: "gaming-pc"
      icon: "mdi:gamepad-variant"
```

### Using Scripts
```yaml
script:
  wake_desktop:
    alias: "Wake Desktop PC"
    sequence:
      - service: mqtt.publish
        data:
          topic: "home/wake"
          payload: "desktop"
          
  wake_gaming_pc_direct:
    alias: "Wake Gaming PC (Direct MAC)"
    sequence:
      - service: mqtt.publish
        data:
          topic: "home/wake"
          payload: "AA:BB:CC:DD:EE:FF"  # Direct MAC address
          
  wake_server_with_ip:
    alias: "Wake Server with Target IP"
    sequence:
      - service: mqtt.publish
        data:
          topic: "home/wake"
          payload: >
            {
              "mac_address": "11:22:33:44:55:66",
              "ip_address": "192.168.1.100",
              "device": "Home Server"
            }
```

### Using Automations
```yaml
automation:
  - alias: "Wake PC when arriving home"
    trigger:
      - platform: state
        entity_id: person.your_name
        to: "home"
    action:
      - service: mqtt.publish
        data:
          topic: "home/wake"
          payload: "desktop"
```

## Development Setup

### Prerequisites
- Python 3.8+
- Docker (for containerized deployment)
- MQTT broker (for testing - can use local Mosquitto or online broker)

### Local Development & Testing

#### Option 1: Python Direct (Recommended for development)

1. **Setup local environment**
   ```bash
   ./test-local.sh
   ```

2. **Run the service**
   ```bash
   python3 main.py
   ```

3. **Test with MQTT messages** (in another terminal)
   ```bash
   # Test with device name
   mosquitto_pub -h 127.0.0.1 -t "test/wake" -m "test-device"
   
   # Test with MAC address
   mosquitto_pub -h 127.0.0.1 -t "test/wake" -m "AA:BB:CC:DD:EE:FF"
   
   # Test with JSON
   mosquitto_pub -h 127.0.0.1 -t "test/wake" -m '{"mac_address": "AA:BB:CC:DD:EE:FF", "device": "My Test PC"}'
   ```

#### Option 2: Local Docker Testing

1. **Build and test locally**
   ```bash
   # Build and run with test configuration
   docker-compose -f docker-compose.yml -f docker-compose.test.yml up --build
   ```

2. **Test with MQTT**
   ```bash
   mosquitto_pub -h localhost -t "test/wake" -m "AA:BB:CC:DD:EE:FF"
   ```

#### Option 3: Quick MQTT Broker for Testing

If you don't have an MQTT broker, run one locally:
```bash
# Run local Mosquitto broker
docker run -it -p 1883:1883 eclipse-mosquitto:latest

# In another terminal, test the service
python3 main.py

# In a third terminal, send test messages
mosquitto_pub -h localhost -t "test/wake" -m "test-device"
```

### Testing Notes

- **Fake MAC addresses**: Use fake MACs like `AA:BB:CC:DD:EE:FF` for testing - the service will attempt to send WOL packets but they won't wake anything
- **Debug logging**: Set `LOG_LEVEL=DEBUG` to see detailed packet information
- **Test topics**: Use `test/wake` topic to avoid triggering production devices
- **Network**: WOL packets are sent but won't work unless target device is on same network

### Building Docker Image

```bash
# Build the image
docker build -t mqtt-wol-service .

# Run with custom config
docker run -d \
  --name mqtt-wol \
  --network host \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -e MQTT_BROKER=192.168.1.100 \
  mqtt-wol-service
```

## Network Requirements

### Wake-on-LAN Setup

1. **Enable WOL on target devices**
   - Enable "Wake-on-LAN" in BIOS/UEFI
   - Enable WOL in network adapter settings
   - Some devices may need "Magic Packet" specifically enabled

- **Network considerations**
  - The service must be on the same network segment as target devices
  - For cross-VLAN scenarios, ensure WOL packets can traverse VLANs (or deploy the container on the target VLAN)
  - Use `network_mode: host` in Docker for best compatibility, or configure custom networks with proper routing

### Finding MAC Addresses

**Windows:**
```cmd
ipconfig /all
```

**Linux/macOS:**
```bash
ip link show  # Linux
ifconfig      # macOS
```

**From router/DHCP:**
Most router admin interfaces show connected devices with MAC addresses.

## Troubleshooting

### Common Issues

1. **WOL packets not working**
   - Verify MAC address is correct
   - Check if target device has WOL enabled in BIOS and OS
   - Ensure Docker container uses `network_mode: host`
   - Try both broadcast (ip_address: null) and targeted WOL

2. **MQTT connection issues**
   - Verify broker IP and port in configuration
   - Check authentication credentials if required
   - Ensure broker is accessible from container network

3. **Device not found errors**
   - Check device name spelling in MQTT message
   - Verify device is configured in config.yaml
   - Check logs for available device list

### Viewing Logs

```bash
# Docker Compose
docker-compose logs -f

# Docker run
docker logs mqtt-wol-service -f

# Local development
LOG_LEVEL=DEBUG python main.py
```

### Testing WOL Manually

```bash
# Install wakeonlan tool
pip install wakeonlan

# Test WOL packet
wakeonlan AA:BB:CC:DD:EE:FF
```

## Security Considerations

- The container runs as a non-root user for security
- Consider using MQTT over TLS for production deployments
- Store sensitive credentials in environment variables, not config files
- Review firewall rules if WOL packets aren't reaching targets

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## Support

For issues and questions:
1. Check the [troubleshooting section](#troubleshooting) above
2. Review the logs for error messages
3. Verify your network and device configuration
4. Open an [issue](https://github.com/bradmatt275/wake-from-mqtt/issues) with detailed information about your setup

## Acknowledgments

- Built with [paho-mqtt](https://pypi.org/project/paho-mqtt/) for MQTT communication
- Uses [wakeonlan](https://pypi.org/project/wakeonlan/) for sending magic packets
- Inspired by the need for cross-VLAN Wake-on-LAN in home networks