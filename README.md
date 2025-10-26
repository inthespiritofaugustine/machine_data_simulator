# Machine Data Simulator

A Python-based TCP streaming simulator that generates and broadcasts machine sensor data with a graphical user interface. Perfect for testing data ingestion pipelines, IoT applications, and real-time data processing systems.

## Features

- **TCP Streaming Server**: Streams data to multiple connected clients simultaneously
- **Multiple Data Generation Types**:
  - Random Integer
  - Random Float
  - Sine Wave (oscillating values)
  - Counter (incrementing values)
  - Boolean Toggle
  - Random Choice (from predefined options)
- **Multiple Protocol Support**: JSON and CSV output formats
- **Real-time Configuration**: Add/remove data items while streaming
- **GUI Interface**: Easy-to-use Tkinter-based interface
- **Configurable Update Intervals**: Control how frequently data is sent
- **Live Preview**: See the exact data being streamed to clients
- **Activity Logging**: Monitor server events and client connections

## Requirements

- Python 3.6+
- tkinter (usually included with Python)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd litmus
```

2. No additional dependencies are required! The simulator uses only Python standard library modules.

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

1. **Server Settings**:
   - **Host**: IP address to bind to (default: 127.0.0.1)
   - **Port**: TCP port to listen on (default: 5000)
   - **Update Interval**: Seconds between data broadcasts (default: 1.0)
   - **Protocol**: Choose between JSON or CSV format
   - **Machine ID**: Identifier for this simulator instance

2. **Adding Data Items**:
   - Enter a unique name for the data item
   - Select a generation type
   - Set min/max values (used by most generation types)
   - Click "Add Item"

3. **Starting/Stopping**:
   - Click "Start Streaming" to begin broadcasting data
   - Click "Stop Streaming" to halt transmission

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

## License

MIT License - Feel free to use this project for any purpose.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
