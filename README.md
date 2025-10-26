# Machine Data Simulator

A Python-based TCP streaming simulator that generates and broadcasts machine sensor data with a graphical user interface. Perfect for testing data ingestion pipelines, IoT applications, and real-time data processing systems.

## Features

- **TCP Streaming Server**: Streams data to multiple connected clients simultaneously
- **Embedded MQTT Broker**: Built-in MQTT broker receives messages from edge devices, creating a full data loop (Simulator → TCP → Edge Device → MQTT Broker → Simulator)
- **Multiple Data Generation Types**:
  - Random Integer
  - Random Float
  - Sine Wave (oscillating values)
  - Counter (incrementing values)
  - Boolean Toggle
  - Random Choice (from predefined options)
- **Multiple Protocol Support**: JSON, CSV, and Simple Streaming (values-only) output formats
- **Real-time Configuration**: Add/remove data items while streaming
- **GUI Interface**: Easy-to-use Tkinter-based interface
- **Configurable Update Intervals**: Control how frequently data is sent
- **Live Preview**: See the exact data being streamed to clients
- **Activity Logging**: Monitor server events and client connections
- **Loop Feedback Visualization**: View MQTT messages received from edge devices processing your TCP stream

## Requirements

- Python 3.6+
- tkinter (usually included with Python)
- paho-mqtt (optional - only needed if using external MQTT features)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd litmus
```

2. Install dependencies (optional):
```bash
pip install -r requirements.txt
```

**Note**: The embedded MQTT broker uses Python's standard library (socket, struct, threading), so paho-mqtt is only needed if you plan to extend the simulator with MQTT client features.

## Configuration Persistence

The simulator automatically saves your configuration to `simulator_config.json` when:
- You add or remove data items
- You close the application

On startup, the simulator automatically loads the last saved configuration, including:
- TCP server settings (host, port, interval, protocol, machine ID)
- MQTT broker settings (bind address, port, topic filter)
- All configured data items with their generation types and parameters

This saves time by restoring your previous setup automatically!

## Usage

### Starting the Simulator

Run the application:
```bash
python machine_data_simulator_v3.py
```

Or make it executable:
```bash
chmod +x machine_data_simulator_v3.py
./machine_data_simulator_v3.py
```

### Configuration

#### TCP Server Settings (Left Panel)
1. **Server Settings**:
   - **Host**: IP address to bind to (default: 127.0.0.1)
   - **Port**: TCP port to listen on (default: 5000)
   - **Update Interval**: Seconds between data broadcasts (default: 1.0)
   - **Protocol**: Choose between JSON or CSV format
   - **Simple Streaming**: Enable for values-only comma-delimited output
   - **Machine ID**: Identifier for this simulator instance

2. **Adding Data Items**:
   - Enter a unique name for the data item
   - Select a generation type
   - Set min/max values (used by most generation types)
   - Click "Add Item"

3. **Starting/Stopping TCP Stream**:
   - Click "Start Streaming" to begin broadcasting data
   - Click "Stop Streaming" to halt transmission

#### MQTT Broker Settings (Right Panel)
1. **MQTT Broker Configuration**:
   - **Bind Address**: IP address to bind the broker to (default: 0.0.0.0 for all interfaces)
   - **Port**: MQTT broker port (default: 1883)
   - **Topic Filter**: Filter which topics to display (default: # for all topics)
     - Use `#` to receive all topics
     - Use `sensor/#` to receive all topics under sensor/
     - Use `sensor/+/data` to receive sensor/*/data (+ matches one level)
     - Use specific topic like `device/temperature`

2. **Starting the MQTT Broker**:
   - Click "Start MQTT Broker" to begin accepting MQTT connections
   - The broker will receive and display PUBLISH messages from any client
   - Only messages matching the topic filter will be displayed
   - Received messages appear in the "MQTT Received Messages" window
   - Shows connected MQTT client count
   - Click "Stop MQTT Broker" to stop

#### Complete Loop Testing
To test the full data loop (Simulator → TCP → Litmus Edge → MQTT Broker → Simulator):
1. **Start the MQTT Broker** in the simulator (right panel) - this will receive messages
2. **Start TCP streaming** from the simulator (left panel) - this sends data
3. Configure your **Litmus Edge device** to:
   - Connect to the simulator's TCP stream (e.g., localhost:5000)
   - Parse/process the incoming data
   - Publish processed data to the simulator's MQTT broker (e.g., localhost:1883)
4. Watch the **complete loop**:
   - TCP data appears in "Output Preview"
   - Processed MQTT messages appear in "MQTT Received Messages"
   - See your data complete the full pipeline!

### Connecting Clients

Use any TCP client to connect and receive data. Examples:

**Using netcat:**
```bash
nc localhost 5000
```

**Using Python:**
```python
import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 5000))

while True:
    data = client.recv(1024).decode('utf-8')
    print(data)
```

**Using telnet:**
```bash
telnet localhost 5000
```

### Publishing to the MQTT Broker

The simulator's MQTT broker accepts connections on port 1883 (configurable). Any MQTT client can publish messages to it.

**Using mosquitto_pub:**
```bash
mosquitto_pub -h localhost -p 1883 -t "sensor/data" -m '{"temperature": 25.5, "humidity": 60}'
```

**Using Python with paho-mqtt:**
```python
import paho.mqtt.client as mqtt
import json

client = mqtt.Client()
client.connect("localhost", 1883, 60)

data = {"temperature": 25.5, "humidity": 60}
client.publish("sensor/data", json.dumps(data))
client.disconnect()
```

**Edge Device Configuration:**
Point your Litmus Edge device or any MQTT publisher to:
- **Broker**: `<simulator-ip>` (e.g., localhost or 192.168.1.100)
- **Port**: `1883` (or your configured port)
- **Topic**: Any topic (all topics are received and displayed)

## Data Formats

### JSON Format
```json
{
  "timestamp": "2025-10-26T05:00:00.123456",
  "machine_id": "SIMULATOR-001",
  "data": {
    "temperature": 72.5,
    "pressure": 101.3,
    "status": "ON"
  }
}
```

### CSV Format
```csv
timestamp,machine_id,pressure,status,temperature
2025-10-26T05:00:00.123456,SIMULATOR-001,101.3,ON,72.5
2025-10-26T05:00:01.234567,SIMULATOR-001,102.1,OFF,73.2
```

### Simple Streaming Format (Values Only)
```
101.3,ON,72.5
102.1,OFF,73.2
```

## Generation Types Explained

- **Random Integer**: Generates random whole numbers between min and max
- **Random Float**: Generates random decimal numbers between min and max
- **Sine Wave**: Creates smooth oscillating values following a sine curve
- **Counter**: Increments from min to max, then wraps back to min
- **Boolean Toggle**: Alternates between True and False
- **Random Choice**: Randomly selects from predefined options

## Use Cases

- Testing data ingestion pipelines
- Developing real-time dashboards
- IoT application development
- Machine learning data stream simulation
- Network protocol testing
- Educational demonstrations
- **Edge Computing Loop Testing**: Validate edge device data processing by simulating the complete loop from data generation through TCP streaming, edge processing, MQTT publishing, and feedback visualization

## License

MIT License - Feel free to use this project for any purpose.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
