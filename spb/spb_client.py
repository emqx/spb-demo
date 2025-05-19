import os
import logging
import paho.mqtt.client as mqtt
from google.protobuf.json_format import MessageToJson
import json
import time
from pandas import Timestamp
import random
from dotenv import load_dotenv

from db.td import DB as TDDB

from spb_pb2 import Payload

class SparkPlugBClient:
    def __init__(self):
        self.db = TDDB()
        self.client = None
        self.broker = os.getenv("MQTT_BROKER")
        self.port = int(os.getenv("MQTT_PORT", 1883))

        self.device_tag_alias = {}
        self.device_tags = {}

        # tree
        # -- {group}
        # |  -- {node}
        # |     -- {device}
        # |       -- {metric}
        self.groups = {}
    
    def __parse_topic(self, topic: str) -> tuple[str, str, str]:
        parts = topic.split('/')
        if len(parts) < 5:
            raise ValueError("Invalid topic format")
        group = parts[1]
        node = parts[3]
        device = parts[4]
        return group, node, device
    
    # spBv1.0/{group}/msg_type/{node}/{device}
    def __on_connect(self, client, userdata, flags, rc):
        result = self.client.subscribe('spBv1.0/#', qos=1)
        logging.info(f"Subscribed spBv1.0/#, result: {result}")
    
    @staticmethod 
    def __timestamp_to_Timestamp(timestamp: int) -> Timestamp:
        offset = random.randint(1, 50)
        return Timestamp(timestamp + offset, unit='ms', tz='Asia/Shanghai')
    
    @staticmethod
    def __parse_spb_value(value_json) -> str:
        if 'intValue' in value_json:
            return str(value_json['intValue'])
        if 'longValue' in value_json:
            return str(value_json['longValue'])
        if 'floatValue' in value_json:
            return str(value_json['floatValue'])
        if 'doubleValue' in value_json:
            return str(value_json['doubleValue'])
        if 'stringValue' in value_json:
            return str(value_json['stringValue'])
        if 'booleanValue' in value_json:
            return str(value_json['booleanValue'])
        if 'bytesValue' in value_json:
            return str(value_json['bytesValue'])
        return 'unknown'

    def __on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        spb_msg = Payload()
        try:
            spb_msg.ParseFromString(msg.payload)
            spb_msg_json = MessageToJson(spb_msg)
            json_obj = json.loads(spb_msg_json)
            # logging.info(f"Message received: {msg.topic} {spb_msg_json}")
            topic_sp = msg.topic.split('/')
            device = topic_sp[-1]

            if 'NBIRTH' in msg.topic:
                logging.info("Node Birth message received")
            elif 'NDEATH' in msg.topic:
                logging.info("Node Death message received")
            elif 'DBIRTH' in msg.topic:
                logging.info("Device Birth message received")
                btime = self.__timestamp_to_Timestamp(int(json_obj['timestamp']))
                self.db.update_device_status(btime, device, 'online')
                metrics = json_obj['metrics']
                self.device_tag_alias[device] = {}
                self.device_tags[device] = {}

                (group, node, device) = self.__parse_topic(msg.topic)
                self.groups[group] = self.groups.get(group, {})
                self.groups[group][node] = self.groups[group].get(node, {})
                self.groups[group][node][device] = self.groups[group][node].get(device, {})

                for metric in metrics:
                    name = metric['name']

                    tag_time = self.__timestamp_to_Timestamp(int(metric['timestamp']))
                    datatype = metric['datatype']
                    value = self.__parse_spb_value(metric)

                    self.db.insert_tag(device, name, value, tag_time)
                    self.device_tags[device][name] = value
                    self.groups[group][node][device][name] = value
                    if 'alias' in metric:
                        alias = metric['alias']
                        self.device_tag_alias[device][alias] = name 
                    time.sleep(0.01)
                    logging.info(f"Device {device} tag {name} inserted")
                    
            elif 'DDEATH' in msg.topic:
                logging.info(f"Device Death message received")
                btime = self.__timestamp_to_Timestamp(int(json_obj['timestamp']))
                self.db.update_device_status(btime, device, 'offline')
            elif 'DDATA' in msg.topic:
                # logging.info("Device Data message received")
                metrics = json_obj['metrics']
                if device not in self.device_tags:
                    self.nbirth(topic_sp[1], topic_sp[-2])
                else:
                    for metric in metrics:
                        tag_time = self.__timestamp_to_Timestamp(int(metric['timestamp']))
                        datatype = metric['datatype']
                        value = self.__parse_spb_value(metric)

                        if 'name' in metric:
                            name = metric['name']
                            self.device_tags[device][name] = value
                            self.db.insert_tag(device, name, value, tag_time)
                        else:
                            alias = metric['alias']
                            name = self.device_tag_alias[device].get(alias, alias)
                            self.device_tags[device][name] = value
                            self.db.insert_tag(device, name, value, tag_time)
                        time.sleep(0.05)
            elif 'NDATA' in msg.topic:
                logging.info("Node Data message received")
            else:
                logging.info("Unknown message type received")
        except Exception as e:
            logging.error(f"Failed to parse message: {e}")
            logging.debug(f"Raw message: {msg.payload}")
    
    def query_spb_tree(self, device: str | None = None) -> str:
        tree = ""
        if device:
            if device in self.device_tags:
                tree += f"-- {device}\n"
                for tag, value in self.device_tags[device].items():
                    tree += f"|  -- {tag}, {value}\n"
            else:
                logging.warning(f"Device {device} not found")
                return "device not found" 
        else:
            for group, nodes in self.groups.items():
                tree += f"-- {group}\n"
                for node, devices in nodes.items():
                    tree += f"|  -- {node}\n"
                    for device, tags in devices.items():
                        tree += f"|    -- {device}\n"
                        for tag, value in tags.items():
                            tree += f"|      -- {tag}, {value}\n"
        return tree
    
    def query_device_current_tag_value(self, device: str, tag: str) -> str:
        if device in self.device_tags:
            if tag in self.device_tags[device]:
                return self.device_tags[device][tag]
            else:
                logging.warning(f"Tag {tag} not found for device {device}")
                return None
        else:
            logging.warning(f"Device {device} not found")
            return None
    
    def nbirth(self, group: str, node: str):
        payload = Payload()
        payload.timestamp = int(time.time() * 1000)
        payload.metrics.add(name='Node Control/Rebirth', datatype=11, boolean_value=True)
        msg = payload.SerializeToString()
        self.client.publish(f'spBv1.0/{group}/NCMD/{node}', msg, qos=0)
    
    def connect(self) -> bool:
        self.client = mqtt.Client()
        self.client.on_connect = self.__on_connect
        self.client.on_message = self.__on_message
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            logging.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            return True
        except Exception as e:
            logging.critical(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        if self.client:
            self.client.disconnect()
            self.client.loop_stop()
            logging.info("Disconnected from MQTT broker")
    