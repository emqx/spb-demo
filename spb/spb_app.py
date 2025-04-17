import os
import logging
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from google.protobuf.json_format import MessageToJson
import json
from datetime import datetime
import time
from pandas import Timestamp
from pytz import timezone, utc
import random

from spb_pb2 import Payload

class SparkPlugBClient:
    def __init__(self):
        #self.db = DB()
        self.client = None
        self.broker = os.getenv("MQTT_BROKER", "broker.emqx.io")
        self.port = int(os.getenv("MQTT_PORT", 1883))
        self.device_tag_alias = {}
        self.device_tags = {}
    
    def __on_connect(self, client, userdata, flags, rc):
        result = self.client.subscribe('spBv1.0/#', qos=1)
        logging.info(f"Subscribed spBv1.0/#, result: {result}")
    
    @staticmethod 
    def __timestamp_to_Timestamp(timestamp: int) -> Timestamp:
        offset = random.randint(1, 50)
        return Timestamp(timestamp + offset, unit='ms', tz='Asia/Shanghai')
    
    @staticmethod
    def __parse_spb_value(datatype: int, value_json) -> str:
        match datatype:
            case 6:
                return str(value_json['intValue'])
    
    @staticmethod
    def timestamp_to_str(timestamp: Timestamp, tz: str = 'Asia/Shanghai') -> str:
        return timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    def query_device_status(self, device: str) -> list[dict]:
        results = self.db.query_device_status(device)
        status = []
        for result in results:
            status.append({
                "status": result['status'],
                "time": self.timestamp_to_str(result['ts'])
            })
        return status

    def __on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        spb_msg = Payload()
        try:
            spb_msg.ParseFromString(msg.payload)
            spb_msg_json = MessageToJson(spb_msg)
            json_obj = json.loads(spb_msg_json)
            logging.info(f"Message received: {msg.topic} {spb_msg_json}")
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
                for metric in metrics:
                    name = metric['name']
                    alias = metric['alias']
                    tag_time = self.__timestamp_to_Timestamp(int(metric['timestamp']))
                    datatype = metric['datatype']
                    value = self.__parse_spb_value(datatype, metric)
                    self.db.insert_tag(device, name, value, tag_time)
                    self.device_tag_alias[device][alias] = name 
                    self.device_tags[device][name] = value
                    time.sleep(0.01)
                    logging.info(f"Device {device} tag {name} with alias {alias} inserted")
                    
            elif 'DDEATH' in msg.topic:
                logging.info(f"Device Death message received")
                btime = self.__timestamp_to_Timestamp(int(json_obj['timestamp']))
                self.db.update_device_status(btime, device, 'offline')
            elif 'DDATA' in msg.topic:
                logging.info("Device Data message received")
                metrics = json_obj['metrics']
                for metric in metrics:
                    alias = metric['alias']
                    tag_time = self.__timestamp_to_Timestamp(int(metric['timestamp']))
                    datatype = metric['datatype']
                    value = self.__parse_spb_value(datatype, metric)
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
    
    def query_device_tag_history(self, device: str, tag: str, start: str, end: str) -> list[dict]:
        results = self.db.query_tag_range(device, tag, start, end)
        history = []
        for result in results:
            history.append({
                "time": self.timestamp_to_str(result['ts']),
                "value": result['value']
            })
        return history
    
    def query_device_status_range(self, device: str, start: str, end: str) -> list[dict]:
        results = self.db.query_device_status_with_range(device, start, end)
        status = []
        for result in results:
            status.append({
                "status": result['status'],
                "time": self.timestamp_to_str(result['ts'])
            })
        return status
    
    def query_device_by_alias(self, alias: str) -> str | None:
        return self.db.get_device_by_alias(alias)
    
    def execute_sql(self, sql: str) -> list[dict]:
        result = self.db.execute_sql(sql)
        return result
    
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
