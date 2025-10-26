# Machine Data Simulator

A Python-based TCP streaming simulator that generates and broadcasts machine sensor data with a graphical user interface. Perfect for testing data ingestion pipelines, IoT applications, and real-time data processing systems.

## Features

- **TCP Streaming Server**: Streams data to multiple connected clients simultaneously
- **MQTT Subscriber**: Connect to MQTT broker to receive feedback messages, creating a full data loop (Simulator → TCP → Edge Device → MQTT → Simulator)
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
- paho-mqtt (for MQTT subscriber functionality)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd litmus
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install paho-mqtt
```

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

#### MQTT Subscriber Settings (Right Panel)
1. **MQTT Configuration**:
   - **Broker**: MQTT broker address (default: localhost)
   - **Port**: MQTT broker port (default: 1883)
   - **Topic**: Topic to subscribe to (default: # for all topics)

2. **Connecting to MQTT**:
   - Click "Connect to MQTT" to start receiving messages
   - Received messages appear in the "MQTT Received Messages" window
   - Click "Disconnect from MQTT" to stop

#### Complete Loop Testing
To test the full data loop (Simulator → TCP → Litmus Edge → MQTT → Simulator):
1. Start TCP streaming from the simulator
2. Configure your Litmus Edge device to connect to the TCP stream
3. Set up Litmus Edge to publish processed data to MQTT
4. Connect the simulator's MQTT subscriber to the same broker
5. Watch the loop feedback in the MQTT messages window!

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
