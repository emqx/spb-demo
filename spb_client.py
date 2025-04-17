from dotenv import load_dotenv
import os
import paho.mqtt.client as mqtt
from google.protobuf.json_format import MessageToJson
from spb.spb_pb2 import Payload  # Import the Payload message class
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from utils.db_util import insert_db
import threading
from queue import Queue
import time 

load_dotenv()

# MQTT Configuration
MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'spBv1.0/#')

topic_data = {}
data_to_insert = []
executor = ThreadPoolExecutor()
message_queue = Queue()

def process_messages():
    """Process messages from the queue in a separate thread with its own event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        if not message_queue.empty():
            records = message_queue.get()
            if records is None:  # Sentinel value to stop the thread
                break
            # Run the async insert in the event loop
            loop.run_until_complete(insert_db(records))
        else:
            # Sleep briefly to prevent busy-waiting
            loop.run_until_complete(asyncio.sleep(0.1))

# Start message processing thread
message_thread = threading.Thread(target=process_messages, daemon=True)
message_thread.start()

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        # print(f"Topic: {msg.topic}")
        #The handle the bug from NeuronEX - https://emqx.atlassian.net/browse/NEURON-3505?
        if "NDEATH".lower() in msg.topic.lower():
            current_timestamp_ms = int(time.time() * 1000)  # Get current time in milliseconds
            data_to_insert.append({"device_key": msg.topic, 
                                   "metric": {"name": "", "timestamp": current_timestamp_ms,  "datatype": 11,
                                              "booleanValue": True}})
            return
        # Create a new message object
        spb_message = Payload()
        # Parse the protobuf message
        spb_message.ParseFromString(msg.payload)
        # Convert to JSON for better readability
        json_message = MessageToJson(spb_message)
        
        # Parse the JSON message to access metrics
        message_dict = json.loads(json_message)
        # print(f"Message: {message_dict}")
        
        # Ensure topic doesn't end with multiple slashes
        base_topic = msg.topic.rstrip('/')
        
        # Process metrics if they exist in the message
        if 'metrics' in message_dict:
            for metric in message_dict['metrics']:
                if 'name' in metric:
                    # Combine topic and metric name
                    full_metric_path = f"{base_topic}/{metric['name']}"
                    topic_data[full_metric_path] = metric
                    data_to_insert.append({"device_key": base_topic, "metric": metric})
                    
                    # Check if we have enough records
                    if len(data_to_insert) >= 10:
                        # Create a copy of current data
                        records_to_insert = data_to_insert.copy()
                        # Clear the data_to_insert list
                        data_to_insert.clear()
                        # Add records to the queue for processing
                        message_queue.put(records_to_insert)
        else:
            # If no metrics, store the whole message under the topic
            topic_data[base_topic] = json_message
            
    except Exception as e:
        print(f"Error processing message: {e}")
        print(f"Raw message: {msg.payload}")

class SparkPlugClient:
    def __init__(self):
        self.mqtt_client = None
    
    def connect(self):
        # Initialize MQTT client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            # Start MQTT loop in a non-blocking way
            self.mqtt_client.loop_start()
            print("MQTT client started.")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
    
    def disconnect(self):
        if self.mqtt_client and self.mqtt_client.is_connected():
            # Signal the message processing thread to stop
            message_queue.put(None)
            message_thread.join(timeout=5)
            # Stop MQTT client
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("MQTT client disconnected.")

    def ddata_topic_trees(self)->str:
        """Returns all topic keys from the MQTT client's topic data"""
        return json.dumps(list(topic_data.keys()))
    
    def ddata_topic_values(self)->str:
        """Returns all latest value from the MQTT client's topic"""
        return json.dumps(topic_data)

def main():
    client = SparkPlugClient()
    try:
        print("Starting SparkPlug B client... Press Ctrl+C to exit")
        client.connect()
        # Keep the main thread running
        while True:
            pass
    except KeyboardInterrupt:
        print("\nShutting down SparkPlug B client...")
        client.disconnect()
        print("Shutdown complete")

if __name__ == "__main__":
    main()