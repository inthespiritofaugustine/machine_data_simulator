#!/usr/bin/env python3
"""
Machine Data Simulator with UI
Simulates streaming machine data over TCP with configurable data items
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import socket
import threading
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Any
import math
import paho.mqtt.client as mqtt
import struct


class DataItem:
    """Represents a single data item with auto-generation capabilities"""
    
    GENERATION_TYPES = [
        "Random Integer",
        "Random Float",
        "Sine Wave",
        "Counter",
        "Boolean Toggle",
        "Random Choice"
    ]
    
    def __init__(self, name: str, generation_type: str, min_val: float = 0, 
                 max_val: float = 100, choices: List[str] = None):
        self.name = name
        self.generation_type = generation_type
        self.min_val = min_val
        self.max_val = max_val
        self.choices = choices or ["ON", "OFF"]
        self.counter = 0
        self.sine_offset = random.uniform(0, 2 * math.pi)
        
    def generate_value(self) -> Any:
        """Generate a value based on the generation type"""
        if self.generation_type == "Random Integer":
            return random.randint(int(self.min_val), int(self.max_val))
        
        elif self.generation_type == "Random Float":
            return round(random.uniform(self.min_val, self.max_val), 2)
        
        elif self.generation_type == "Sine Wave":
            # Create a sine wave that oscillates between min and max
            amplitude = (self.max_val - self.min_val) / 2
            offset = (self.max_val + self.min_val) / 2
            value = offset + amplitude * math.sin(self.counter * 0.1 + self.sine_offset)
            self.counter += 1
            return round(value, 2)
        
        elif self.generation_type == "Counter":
            value = int(self.min_val + self.counter)
            self.counter = (self.counter + 1) % int(self.max_val - self.min_val + 1)
            return value
        
        elif self.generation_type == "Boolean Toggle":
            value = self.counter % 2 == 0
            self.counter += 1
            return value
        
        elif self.generation_type == "Random Choice":
            return random.choice(self.choices)
        
        return None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "generation_type": self.generation_type,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "choices": self.choices
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DataItem':
        """Create DataItem from dictionary"""
        return cls(
            name=data["name"],
            generation_type=data["generation_type"],
            min_val=data.get("min_val", 0),
            max_val=data.get("max_val", 100),
            choices=data.get("choices", ["ON", "OFF"])
        )


class TCPStreamServer:
    """TCP server that streams data to connected clients"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5000, protocol: str = "json", simple_streaming: bool = False):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.simple_streaming = simple_streaming
        self.server_socket = None
        self.clients = []
        self.running = False
        self.server_thread = None
        self.lock = threading.Lock()
        self.csv_header_sent = {}
        
    def start(self):
        """Start the TCP server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)  # Allow periodic checking
            self.running = True
            
            self.server_thread = threading.Thread(target=self._accept_connections, daemon=True)
            self.server_thread.start()
            
            return True
        except Exception as e:
            raise Exception(f"Failed to start server: {e}")
    
    def _accept_connections(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                with self.lock:
                    self.clients.append((client_socket, address))
                print(f"Client connected from {address}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")
    
    def broadcast(self, data: Dict):
        """Broadcast data to all connected clients"""
        # Format message based on protocol and streaming mode
        if self.simple_streaming:
            message = self._format_simple(data)
        elif self.protocol == "csv":
            message = self._format_csv(data)
        else:  # json
            message = json.dumps(data) + "\n"
        
        # If no clients, just return the message for preview
        if not self.clients:
            return message
        
        encoded_message = message.encode('utf-8')
        
        with self.lock:
            disconnected = []
            for client_socket, address in self.clients:
                try:
                    # Send CSV header if this is a new client and protocol is CSV (not simple streaming)
                    if self.protocol == "csv" and not self.simple_streaming and address not in self.csv_header_sent:
                        header = self._get_csv_header(data)
                        client_socket.sendall(header.encode('utf-8'))
                        self.csv_header_sent[address] = True
                    
                    client_socket.sendall(encoded_message)
                except Exception as e:
                    print(f"Error sending to {address}: {e}")
                    disconnected.append((client_socket, address))
            
            # Remove disconnected clients
            for client in disconnected:
                self.clients.remove(client)
                if client[1] in self.csv_header_sent:
                    del self.csv_header_sent[client[1]]
                client[0].close()
        
        return message  # Return formatted message for preview
    
    def _get_csv_header(self, data: Dict) -> str:
        """Generate CSV header from data structure"""
        headers = ["timestamp", "machine_id"]
        if "data" in data:
            headers.extend(sorted(data["data"].keys()))
        return ",".join(headers) + "\n"
    
    def _format_csv(self, data: Dict) -> str:
        """Format data as CSV"""
        values = [
            data.get("timestamp", ""),
            data.get("machine_id", "")
        ]
        
        if "data" in data:
            # Sort keys to ensure consistent column order
            for key in sorted(data["data"].keys()):
                value = data["data"][key]
                # Handle boolean and string values
                if isinstance(value, bool):
                    values.append(str(value).lower())
                elif isinstance(value, str):
                    # Escape commas in strings
                    values.append(f'"{value}"' if ',' in value else value)
                else:
                    values.append(str(value))
        
        return ",".join(values) + "\n"

    def _format_simple(self, data: Dict) -> str:
        """Format data as simple comma-delimited values only"""
        values = []

        if "data" in data:
            # Sort keys to ensure consistent order
            for key in sorted(data["data"].keys()):
                value = data["data"][key]
                # Handle boolean and string values
                if isinstance(value, bool):
                    values.append(str(value).lower())
                else:
                    values.append(str(value))

        return ",".join(values) + "\n"

    def stop(self):
        """Stop the TCP server"""
        self.running = False
        
        # Close all client connections
        with self.lock:
            for client_socket, _ in self.clients:
                try:
                    client_socket.close()
                except:
                    pass
            self.clients.clear()
            self.csv_header_sent.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
    
    def get_client_count(self) -> int:
        """Get number of connected clients"""
        with self.lock:
            return len(self.clients)


class MQTTSubscriber:
    """MQTT client that subscribes to topics and receives messages"""

    def __init__(self, broker: str = "localhost", port: int = 1883, topic: str = "#"):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = None
        self.connected = False
        self.message_callback = None
        self.log_callback = None

    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.connected = True
            if self.log_callback:
                self.log_callback(f"MQTT: Connected to broker {self.broker}:{self.port}")
            # Subscribe to topic
            client.subscribe(self.topic)
            if self.log_callback:
                self.log_callback(f"MQTT: Subscribed to topic '{self.topic}'")
        else:
            self.connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized"
            }
            error_msg = error_messages.get(rc, f"Connection refused - unknown error ({rc})")
            if self.log_callback:
                self.log_callback(f"MQTT: {error_msg}")

    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.connected = False
        if self.log_callback:
            if rc != 0:
                self.log_callback(f"MQTT: Unexpected disconnection (code: {rc})")
            else:
                self.log_callback("MQTT: Disconnected from broker")

    def on_message(self, client, userdata, msg):
        """Callback when a message is received"""
        if self.message_callback:
            try:
                # Try to decode as JSON, otherwise use raw payload
                try:
                    payload = json.loads(msg.payload.decode('utf-8'))
                    formatted_payload = json.dumps(payload, indent=2)
                except:
                    formatted_payload = msg.payload.decode('utf-8', errors='replace')

                self.message_callback(msg.topic, formatted_payload)
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"MQTT: Error processing message: {e}")

    def start(self, message_callback=None, log_callback=None):
        """Start the MQTT client"""
        try:
            self.message_callback = message_callback
            self.log_callback = log_callback

            # Create MQTT client
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message

            # Connect to broker
            self.client.connect(self.broker, self.port, 60)

            # Start network loop in background thread
            self.client.loop_start()

            return True
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"MQTT: Failed to connect - {e}")
            return False

    def stop(self):
        """Stop the MQTT client"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

    def update_subscription(self, new_topic: str):
        """Update the subscribed topic"""
        if self.client and self.connected:
            # Unsubscribe from old topic
            self.client.unsubscribe(self.topic)
            # Subscribe to new topic
            self.topic = new_topic
            self.client.subscribe(self.topic)
            if self.log_callback:
                self.log_callback(f"MQTT: Subscription changed to '{self.topic}'")


class SimpleMQTTBroker:
    """Simple MQTT broker that receives and displays PUBLISH messages"""

    def __init__(self, host: str = "0.0.0.0", port: int = 1883, topic_filter: str = "#"):
        self.host = host
        self.port = port
        self.topic_filter = topic_filter
        self.server_socket = None
        self.clients = []
        self.running = False
        self.server_thread = None
        self.lock = threading.Lock()
        self.message_callback = None
        self.log_callback = None

    def start(self, message_callback=None, log_callback=None):
        """Start the MQTT broker"""
        try:
            self.message_callback = message_callback
            self.log_callback = log_callback

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)
            self.running = True

            self.server_thread = threading.Thread(target=self._accept_connections, daemon=True)
            self.server_thread.start()

            if self.log_callback:
                self.log_callback(f"MQTT Broker: Started on {self.host}:{self.port}")

            return True
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"MQTT Broker: Failed to start - {e}")
            return False

    def _accept_connections(self):
        """Accept incoming MQTT client connections"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                client_socket.settimeout(60.0)  # 60 second timeout for recv operations

                if self.log_callback:
                    self.log_callback(f"MQTT Broker: Client connected from {address}")

                # Start a thread to handle this client
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()

                with self.lock:
                    self.clients.append((client_socket, address))

            except socket.timeout:
                continue
            except Exception as e:
                if self.running and self.log_callback:
                    self.log_callback(f"MQTT Broker: Error accepting connection: {e}")

    def _decode_remaining_length(self, client_socket):
        """Decode MQTT variable length field (up to 4 bytes)"""
        multiplier = 1
        value = 0
        byte_count = 0

        while True:
            data = client_socket.recv(1)
            if not data:
                return None

            byte = data[0]
            value += (byte & 127) * multiplier
            multiplier *= 128
            byte_count += 1

            if (byte & 128) == 0:
                break

            if byte_count >= 4:
                raise ValueError("Remaining length exceeds 4 bytes")

        return value

    def _handle_client(self, client_socket, address):
        """Handle MQTT messages from a connected client"""
        try:
            while self.running:
                # Read MQTT fixed header first byte
                header_byte = client_socket.recv(1)
                if not header_byte or len(header_byte) < 1:
                    break

                msg_type = (header_byte[0] >> 4) & 0x0F

                # Decode variable-length remaining length field
                remaining_length = self._decode_remaining_length(client_socket)
                if remaining_length is None:
                    break

                # Read remaining message if any
                if remaining_length > 0:
                    payload = b''
                    bytes_to_read = remaining_length
                    while bytes_to_read > 0:
                        chunk = client_socket.recv(min(bytes_to_read, 4096))
                        if not chunk:
                            break
                        payload += chunk
                        bytes_to_read -= len(chunk)
                else:
                    payload = b''

                # Handle different MQTT message types
                if msg_type == 1:  # CONNECT
                    self._handle_connect(client_socket, payload)
                elif msg_type == 3:  # PUBLISH
                    self._handle_publish(client_socket, payload, header_byte[0])
                elif msg_type == 12:  # PINGREQ
                    self._handle_pingreq(client_socket)
                elif msg_type == 14:  # DISCONNECT
                    break

        except Exception as e:
            if self.log_callback:
                self.log_callback(f"MQTT Broker: Client {address} error: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            with self.lock:
                if (client_socket, address) in self.clients:
                    self.clients.remove((client_socket, address))
            if self.log_callback:
                self.log_callback(f"MQTT Broker: Client {address} disconnected")

    def _handle_connect(self, client_socket, payload):
        """Handle MQTT CONNECT message"""
        try:
            # Send CONNACK (Connection Acknowledgment)
            # Fixed header: 0x20 (CONNACK), 0x02 (remaining length)
            # Variable header: 0x00 (session present), 0x00 (connection accepted)
            connack = bytes([0x20, 0x02, 0x00, 0x00])
            client_socket.send(connack)
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"MQTT Broker: Error sending CONNACK: {e}")

    def _topic_matches_filter(self, topic: str, topic_filter: str) -> bool:
        """Check if topic matches the MQTT topic filter (supports wildcards)"""
        if topic_filter == "#":
            return True

        topic_parts = topic.split('/')
        filter_parts = topic_filter.split('/')

        for i, filter_part in enumerate(filter_parts):
            if filter_part == "#":
                return True  # Multi-level wildcard matches everything after

            if i >= len(topic_parts):
                return False

            if filter_part == "+":
                continue  # Single-level wildcard matches one level

            if filter_part != topic_parts[i]:
                return False

        return len(topic_parts) == len(filter_parts)

    def _handle_publish(self, client_socket, payload, flags):
        """Handle MQTT PUBLISH message"""
        try:
            qos = (flags >> 1) & 0x03

            # Parse topic
            topic_len = struct.unpack('>H', payload[0:2])[0]
            topic = payload[2:2+topic_len].decode('utf-8')

            # Check if topic matches filter
            if not self._topic_matches_filter(topic, self.topic_filter):
                return  # Ignore messages that don't match filter

            # Get message (skip packet identifier if QoS > 0)
            if qos > 0:
                message_start = 2 + topic_len + 2
            else:
                message_start = 2 + topic_len

            message_bytes = payload[message_start:]

            # Try to decode as JSON, otherwise as string
            try:
                message = json.loads(message_bytes.decode('utf-8'))
                formatted_message = json.dumps(message, indent=2)
            except:
                formatted_message = message_bytes.decode('utf-8', errors='replace')

            # Call the message callback
            if self.message_callback:
                self.message_callback(topic, formatted_message)

        except Exception as e:
            if self.log_callback:
                self.log_callback(f"MQTT Broker: Error handling PUBLISH: {e}")

    def _handle_pingreq(self, client_socket):
        """Handle MQTT PINGREQ message"""
        try:
            # Send PINGRESP
            pingresp = bytes([0xD0, 0x00])
            client_socket.send(pingresp)
        except:
            pass

    def stop(self):
        """Stop the MQTT broker"""
        self.running = False

        # Close all client connections
        with self.lock:
            for client_socket, _ in self.clients:
                try:
                    client_socket.close()
                except:
                    pass
            self.clients.clear()

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        if self.log_callback:
            self.log_callback("MQTT Broker: Stopped")

    def get_client_count(self) -> int:
        """Get number of connected MQTT clients"""
        with self.lock:
            return len(self.clients)


class MachineDataSimulatorApp:
    """Main application with UI"""

    def __init__(self, root):
        self.root = root
        self.root.title("Machine Data Simulator")
        self.root.geometry("1920x1080")

        self.data_items: List[DataItem] = []
        self.tcp_server = None
        self.mqtt_broker = None
        self.streaming = False
        self.mqtt_running = False
        self.stream_thread = None
        self.update_interval = 1.0  # seconds
        self.last_message = ""  # Store last message for preview
        self.simple_streaming = False  # Simple streaming mode flag
        self.config_file = "simulator_config.json"

        self.setup_ui()
        # Load configuration after UI is set up so variables exist
        self.root.after(100, self.load_configuration)
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # Left column - TCP Server Configuration and Data Items
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)

        # Right column - MQTT Configuration
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

        # Server Configuration Section (left)
        self.setup_server_config(left_frame)

        # Data Items Section (left)
        self.setup_data_items_section(left_frame)

        # MQTT Configuration Section (right)
        self.setup_mqtt_config(right_frame)

        # MQTT Messages Section (right)
        self.setup_mqtt_messages(right_frame)

        # Output Preview Section (spans both columns)
        self.setup_output_preview(main_frame)

        # Log Section (spans both columns)
        self.setup_log_section(main_frame)
        
    def setup_server_config(self, parent):
        """Setup server configuration section"""
        config_frame = ttk.LabelFrame(parent, text="Server Configuration", padding="10")
        config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Row 0 - Connection settings
        # Host
        ttk.Label(config_frame, text="Host:").grid(row=0, column=0, sticky=tk.W)
        self.host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(config_frame, textvariable=self.host_var, width=15).grid(row=0, column=1, padx=5)
        
        # Port
        ttk.Label(config_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.port_var = tk.StringVar(value="5000")
        ttk.Entry(config_frame, textvariable=self.port_var, width=10).grid(row=0, column=3, padx=5)
        
        # Update Interval
        ttk.Label(config_frame, text="Update Interval (s):").grid(row=0, column=4, sticky=tk.W, padx=(20, 0))
        self.interval_var = tk.StringVar(value="1.0")
        ttk.Entry(config_frame, textvariable=self.interval_var, width=10).grid(row=0, column=5, padx=5)
        
        # Protocol Selection
        ttk.Label(config_frame, text="Protocol:").grid(row=0, column=6, sticky=tk.W, padx=(20, 0))
        self.protocol_var = tk.StringVar(value="json")
        protocol_combo = ttk.Combobox(config_frame, textvariable=self.protocol_var,
                                       values=["json", "csv"], width=8, state="readonly")
        protocol_combo.grid(row=0, column=7, padx=5)
        protocol_combo.bind('<<ComboboxSelected>>', self.on_protocol_change)

        # Row 1 - Machine ID and Simple Streaming
        ttk.Label(config_frame, text="Machine ID:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.machine_id_var = tk.StringVar(value="SIMULATOR-001")
        ttk.Entry(config_frame, textvariable=self.machine_id_var, width=20).grid(row=1, column=1, columnspan=2, padx=5, pady=(10, 0), sticky=tk.W)

        # Simple Streaming Checkbox
        self.simple_streaming_var = tk.BooleanVar(value=False)
        simple_check = ttk.Checkbutton(config_frame, text="Simple Streaming",
                                        variable=self.simple_streaming_var,
                                        command=self.on_simple_streaming_toggle)
        simple_check.grid(row=1, column=3, columnspan=2, padx=(20, 0), pady=(10, 0), sticky=tk.W)

        # Start/Stop Button
        self.start_button = ttk.Button(config_frame, text="Start Streaming", command=self.toggle_streaming)
        self.start_button.grid(row=1, column=5, columnspan=2, padx=(20, 0), pady=(10, 0), sticky=tk.W)

        # Status Label
        self.status_var = tk.StringVar(value="Status: Stopped")
        ttk.Label(config_frame, textvariable=self.status_var, foreground="red").grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

        # Clients Label
        self.clients_var = tk.StringVar(value="Connected Clients: 0")
        ttk.Label(config_frame, textvariable=self.clients_var).grid(row=2, column=3, columnspan=5, sticky=tk.W, pady=(5, 0))
    
    def on_protocol_change(self, event=None):
        """Handle protocol change"""
        if self.streaming:
            self.log(f"Protocol changed to: {self.protocol_var.get().upper()}")
            if self.tcp_server:
                self.tcp_server.protocol = self.protocol_var.get()
                self.tcp_server.csv_header_sent.clear()  # Reset header tracking for CSV

    def on_simple_streaming_toggle(self):
        """Handle simple streaming mode toggle"""
        if self.streaming:
            simple_mode = self.simple_streaming_var.get()
            self.log(f"Simple Streaming: {'Enabled' if simple_mode else 'Disabled'}")
            if self.tcp_server:
                self.tcp_server.simple_streaming = simple_mode
        
    def setup_data_items_section(self, parent):
        """Setup data items configuration section"""
        items_frame = ttk.LabelFrame(parent, text="Data Items", padding="10")
        items_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        items_frame.columnconfigure(0, weight=1)
        items_frame.rowconfigure(1, weight=1)
        
        # Add item controls
        add_frame = ttk.Frame(items_frame)
        add_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(add_frame, text="Name:").grid(row=0, column=0, sticky=tk.W)
        self.item_name_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.item_name_var, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(add_frame, text="Type:").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.item_type_var = tk.StringVar()
        type_combo = ttk.Combobox(add_frame, textvariable=self.item_type_var, 
                                   values=DataItem.GENERATION_TYPES, width=15, state="readonly")
        type_combo.grid(row=0, column=3, padx=5)
        type_combo.current(0)
        
        ttk.Label(add_frame, text="Min:").grid(row=0, column=4, sticky=tk.W, padx=(10, 0))
        self.item_min_var = tk.StringVar(value="0")
        ttk.Entry(add_frame, textvariable=self.item_min_var, width=8).grid(row=0, column=5, padx=5)
        
        ttk.Label(add_frame, text="Max:").grid(row=0, column=6, sticky=tk.W)
        self.item_max_var = tk.StringVar(value="100")
        ttk.Entry(add_frame, textvariable=self.item_max_var, width=8).grid(row=0, column=7, padx=5)
        
        ttk.Button(add_frame, text="Add Item", command=self.add_data_item).grid(row=0, column=8, padx=(10, 0))
        
        # Items list
        list_frame = ttk.Frame(items_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Treeview for data items
        columns = ("name", "type", "min", "max", "current_value")
        self.items_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        
        self.items_tree.heading("name", text="Name")
        self.items_tree.heading("type", text="Generation Type")
        self.items_tree.heading("min", text="Min")
        self.items_tree.heading("max", text="Max")
        self.items_tree.heading("current_value", text="Current Value")
        
        self.items_tree.column("name", width=120)
        self.items_tree.column("type", width=150)
        self.items_tree.column("min", width=80)
        self.items_tree.column("max", width=80)
        self.items_tree.column("current_value", width=120)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=scrollbar.set)
        
        self.items_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Remove button
        ttk.Button(items_frame, text="Remove Selected", command=self.remove_data_item).grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
    
    def setup_output_preview(self, parent):
        """Setup output preview section"""
        preview_frame = ttk.LabelFrame(parent, text="Output Preview (Last Streamed Message)", padding="10")
        preview_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=8, state='disabled',
                                                       wrap=tk.WORD, font=('Courier', 9))
        self.preview_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
    def setup_log_section(self, parent):
        """Setup log display section"""
        log_frame = ttk.LabelFrame(parent, text="Activity Log", padding="10")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state='disabled', wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Button frame for log controls
        log_button_frame = ttk.Frame(log_frame)
        log_button_frame.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        ttk.Button(log_button_frame, text="Clear Log", command=self.clear_log).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Button(log_button_frame, text="Save Configuration", command=lambda: self.save_configuration(show_message=True)).grid(row=0, column=1, sticky=tk.W)

    def setup_mqtt_config(self, parent):
        """Setup MQTT broker configuration section"""
        mqtt_frame = ttk.LabelFrame(parent, text="MQTT Broker (Receive Messages)", padding="10")
        mqtt_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Row 0 - Broker bind settings
        ttk.Label(mqtt_frame, text="Bind Address:").grid(row=0, column=0, sticky=tk.W)
        self.mqtt_host_var = tk.StringVar(value="0.0.0.0")
        ttk.Entry(mqtt_frame, textvariable=self.mqtt_host_var, width=20).grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(mqtt_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.mqtt_port_var = tk.StringVar(value="1883")
        ttk.Entry(mqtt_frame, textvariable=self.mqtt_port_var, width=10).grid(row=0, column=3, padx=5, pady=2)

        # Row 1 - Topic filter
        ttk.Label(mqtt_frame, text="Topic Filter:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.mqtt_topic_filter_var = tk.StringVar(value="#")
        topic_entry = ttk.Entry(mqtt_frame, textvariable=self.mqtt_topic_filter_var, width=30)
        topic_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=(5, 0), sticky=(tk.W, tk.E))

        # Row 2 - Start/Stop button and status
        self.mqtt_button = ttk.Button(mqtt_frame, text="Start MQTT Broker", command=self.toggle_mqtt)
        self.mqtt_button.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky=tk.W)

        # Status
        self.mqtt_status_var = tk.StringVar(value="MQTT Broker: Stopped")
        ttk.Label(mqtt_frame, textvariable=self.mqtt_status_var, foreground="red").grid(row=2, column=2, columnspan=2, pady=(10, 0), sticky=tk.W, padx=(10, 0))

        # Connected clients count
        self.mqtt_clients_var = tk.StringVar(value="MQTT Clients: 0")
        ttk.Label(mqtt_frame, textvariable=self.mqtt_clients_var).grid(row=3, column=0, columnspan=4, pady=(5, 0), sticky=tk.W)

    def setup_mqtt_messages(self, parent):
        """Setup MQTT messages display section"""
        messages_frame = ttk.LabelFrame(parent, text="MQTT Received Messages (Loop Feedback)", padding="10")
        messages_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        messages_frame.columnconfigure(0, weight=1)
        messages_frame.rowconfigure(0, weight=1)

        self.mqtt_messages_text = scrolledtext.ScrolledText(messages_frame, height=20, state='disabled',
                                                             wrap=tk.WORD, font=('Courier', 9))
        self.mqtt_messages_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        ttk.Button(messages_frame, text="Clear Messages", command=self.clear_mqtt_messages).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

    def log(self, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
        
    def clear_log(self):
        """Clear the log"""
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')

    def clear_mqtt_messages(self):
        """Clear the MQTT messages display"""
        self.mqtt_messages_text.configure(state='normal')
        self.mqtt_messages_text.delete(1.0, tk.END)
        self.mqtt_messages_text.configure(state='disabled')

    def on_mqtt_message_received(self, topic: str, payload: str):
        """Callback when MQTT message is received"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.mqtt_messages_text.configure(state='normal')
        self.mqtt_messages_text.insert(tk.END, f"[{timestamp}] Topic: {topic}\n")
        self.mqtt_messages_text.insert(tk.END, f"{payload}\n")
        self.mqtt_messages_text.insert(tk.END, "-" * 80 + "\n")
        self.mqtt_messages_text.see(tk.END)
        self.mqtt_messages_text.configure(state='disabled')

    def toggle_mqtt(self):
        """Toggle MQTT broker"""
        if not self.mqtt_running:
            self.start_mqtt_broker()
        else:
            self.stop_mqtt_broker()

    def start_mqtt_broker(self):
        """Start the MQTT broker"""
        try:
            host = self.mqtt_host_var.get()
            port = int(self.mqtt_port_var.get())
            topic_filter = self.mqtt_topic_filter_var.get()

            self.mqtt_broker = SimpleMQTTBroker(host, port, topic_filter)
            success = self.mqtt_broker.start(
                message_callback=lambda t, p: self.root.after(0, self.on_mqtt_message_received, t, p),
                log_callback=lambda msg: self.root.after(0, self.log, msg)
            )

            if success:
                self.mqtt_running = True
                self.mqtt_button.configure(text="Stop MQTT Broker")
                self.mqtt_status_var.set("MQTT Broker: Running")
                # Change status label color
                for widget in self.mqtt_button.master.winfo_children():
                    if isinstance(widget, ttk.Label) and "MQTT Broker:" in str(widget.cget("text") if hasattr(widget, "cget") else ""):
                        try:
                            widget.configure(foreground="green")
                        except:
                            pass

                # Start MQTT client count updater
                self.update_mqtt_client_count()

        except ValueError:
            messagebox.showerror("Error", "Port must be a valid number")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start MQTT broker: {e}")

    def stop_mqtt_broker(self):
        """Stop the MQTT broker"""
        if self.mqtt_broker:
            self.mqtt_broker.stop()
            self.mqtt_broker = None

        self.mqtt_running = False
        self.mqtt_button.configure(text="Start MQTT Broker")
        self.mqtt_status_var.set("MQTT Broker: Stopped")
        self.mqtt_clients_var.set("MQTT Clients: 0")
        # Change status label color back to red
        for widget in self.mqtt_button.master.winfo_children():
            if isinstance(widget, ttk.Label) and "MQTT Broker:" in str(widget.cget("text") if hasattr(widget, "cget") else ""):
                try:
                    widget.configure(foreground="red")
                except:
                    pass

    def update_mqtt_client_count(self):
        """Update MQTT connected clients count"""
        if self.mqtt_running and self.mqtt_broker:
            count = self.mqtt_broker.get_client_count()
            self.mqtt_clients_var.set(f"MQTT Clients: {count}")
            self.root.after(1000, self.update_mqtt_client_count)

    def update_preview(self, message: str):
        """Update the output preview with the latest message"""
        self.preview_text.configure(state='normal')
        self.preview_text.delete(1.0, tk.END)
        
        # For CSV, show header + message for clarity
        if self.tcp_server and self.tcp_server.protocol == "csv":
            # Generate and show header
            if hasattr(self, 'last_csv_header'):
                self.preview_text.insert(1.0, self.last_csv_header + "\n" + message)
            else:
                self.preview_text.insert(1.0, message)
        else:
            self.preview_text.insert(1.0, message)
        
        self.preview_text.configure(state='disabled')
        
    def add_data_item(self):
        """Add a new data item"""
        name = self.item_name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter a name for the data item")
            return
        
        # Check for duplicate names
        if any(item.name == name for item in self.data_items):
            messagebox.showerror("Error", f"Data item '{name}' already exists")
            return
        
        try:
            gen_type = self.item_type_var.get()
            min_val = float(self.item_min_var.get())
            max_val = float(self.item_max_var.get())
            
            if min_val >= max_val:
                messagebox.showerror("Error", "Min value must be less than Max value")
                return
            
            item = DataItem(name, gen_type, min_val, max_val)
            self.data_items.append(item)
            
            # Add to treeview
            self.items_tree.insert("", tk.END, values=(name, gen_type, min_val, max_val, "-"))

            self.log(f"Added data item: {name} ({gen_type})")

            # Save configuration
            self.save_configuration()

            # Clear input fields
            self.item_name_var.set("")
            
        except ValueError:
            messagebox.showerror("Error", "Min and Max values must be numbers")
            
    def remove_data_item(self):
        """Remove selected data item"""
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a data item to remove")
            return
        
        for item_id in selection:
            values = self.items_tree.item(item_id, "values")
            name = values[0]
            
            # Remove from data items list
            self.data_items = [item for item in self.data_items if item.name != name]
            
            # Remove from treeview
            self.items_tree.delete(item_id)

            self.log(f"Removed data item: {name}")

        # Save configuration after removing items
        if selection:
            self.save_configuration()
            
    def toggle_streaming(self):
        """Toggle streaming on/off"""
        if not self.streaming:
            self.start_streaming()
        else:
            self.stop_streaming()
            
    def start_streaming(self):
        """Start the TCP server and streaming"""
        if not self.data_items:
            messagebox.showerror("Error", "Please add at least one data item before starting")
            return
        
        try:
            host = self.host_var.get()
            port = int(self.port_var.get())
            protocol = self.protocol_var.get()
            simple_streaming = self.simple_streaming_var.get()
            self.update_interval = float(self.interval_var.get())

            if self.update_interval <= 0:
                raise ValueError("Update interval must be positive")

            # Create and start TCP server
            self.tcp_server = TCPStreamServer(host, port, protocol, simple_streaming)
            self.tcp_server.start()
            
            # Start streaming thread
            self.streaming = True
            self.stream_thread = threading.Thread(target=self.stream_data, daemon=True)
            self.stream_thread.start()
            
            # Update UI
            self.start_button.configure(text="Stop Streaming")
            self.status_var.set("Status: Running")
            self.log(f"Started streaming on {host}:{port} using {protocol.upper()} protocol")
            
            # Start client count updater
            self.update_client_count()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid configuration: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")
            
    def stop_streaming(self):
        """Stop streaming and TCP server"""
        self.streaming = False
        
        if self.tcp_server:
            self.tcp_server.stop()
            self.tcp_server = None
        
        # Update UI
        self.start_button.configure(text="Start Streaming")
        self.status_var.set("Status: Stopped")
        self.clients_var.set("Connected Clients: 0")
        self.log("Stopped streaming")
        
    def stream_data(self):
        """Stream data continuously"""
        while self.streaming:
            # Generate data payload
            timestamp = datetime.now().isoformat()
            data = {
                "timestamp": timestamp,
                "machine_id": self.machine_id_var.get(),
                "data": {}
            }
            
            # Generate values for all data items
            for item in self.data_items:
                value = item.generate_value()
                data["data"][item.name] = value
                
                # Update treeview (in main thread)
                self.root.after(0, self.update_item_value, item.name, value)
            
            # Broadcast to clients and get formatted message
            if self.tcp_server:
                # Store CSV header for preview if using CSV protocol
                if self.tcp_server.protocol == "csv":
                    self.last_csv_header = self.tcp_server._get_csv_header(data).rstrip('\n')
                
                message = self.tcp_server.broadcast(data)
                # Update preview in main thread
                if message:
                    self.root.after(0, self.update_preview, message.rstrip('\n'))
            
            time.sleep(self.update_interval)
            
    def update_item_value(self, name: str, value: Any):
        """Update current value in treeview"""
        for item_id in self.items_tree.get_children():
            values = list(self.items_tree.item(item_id, "values"))
            if values[0] == name:
                values[4] = str(value)
                self.items_tree.item(item_id, values=values)
                break
                
    def update_client_count(self):
        """Update connected clients count"""
        if self.streaming and self.tcp_server:
            count = self.tcp_server.get_client_count()
            self.clients_var.set(f"Connected Clients: {count}")
            self.root.after(1000, self.update_client_count)
            
    def save_configuration(self, show_message=False):
        """Save current configuration to file"""
        try:
            config = {
                "tcp_server": {
                    "host": self.host_var.get(),
                    "port": self.port_var.get(),
                    "update_interval": self.interval_var.get(),
                    "protocol": self.protocol_var.get(),
                    "simple_streaming": self.simple_streaming_var.get(),
                    "machine_id": self.machine_id_var.get()
                },
                "mqtt_broker": {
                    "host": self.mqtt_host_var.get(),
                    "port": self.mqtt_port_var.get(),
                    "topic_filter": self.mqtt_topic_filter_var.get()
                },
                "data_items": [item.to_dict() for item in self.data_items]
            }

            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

            if show_message:
                self.log("Configuration saved successfully")

        except Exception as e:
            self.log(f"Failed to save configuration: {e}")

    def load_configuration(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            # Load TCP server settings
            if "tcp_server" in config:
                tcp = config["tcp_server"]
                self.host_var.set(tcp.get("host", "127.0.0.1"))
                self.port_var.set(tcp.get("port", "5000"))
                self.interval_var.set(tcp.get("update_interval", "1.0"))
                self.protocol_var.set(tcp.get("protocol", "json"))
                self.simple_streaming_var.set(tcp.get("simple_streaming", False))
                self.machine_id_var.set(tcp.get("machine_id", "SIMULATOR-001"))

            # Load MQTT broker settings
            if "mqtt_broker" in config:
                mqtt = config["mqtt_broker"]
                self.mqtt_host_var.set(mqtt.get("host", "0.0.0.0"))
                self.mqtt_port_var.set(mqtt.get("port", "1883"))
                self.mqtt_topic_filter_var.set(mqtt.get("topic_filter", "#"))

            # Load data items
            if "data_items" in config:
                for item_data in config["data_items"]:
                    try:
                        item = DataItem.from_dict(item_data)
                        self.data_items.append(item)
                        # Add to treeview
                        self.items_tree.insert("", tk.END, values=(
                            item.name,
                            item.generation_type,
                            item.min_val,
                            item.max_val,
                            "-"
                        ))
                    except Exception as e:
                        self.log(f"Failed to load data item: {e}")

            self.log("Configuration loaded successfully")

        except FileNotFoundError:
            self.log("No saved configuration found, using defaults")
        except Exception as e:
            self.log(f"Failed to load configuration: {e}")

    def on_closing(self):
        """Handle window closing"""
        self.save_configuration()
        if self.streaming:
            self.stop_streaming()
        if self.mqtt_running:
            self.stop_mqtt_broker()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MachineDataSimulatorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
