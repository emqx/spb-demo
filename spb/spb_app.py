from pandas import Timestamp

from db.datalayer import DB
from db.mariadb import Client
from spb_client import SparkPlugBClient


class SparkPlugBApp:
    def __init__(self):
        self.datalayer = DB()
        self.mariadb = Client()
        self.client = SparkPlugBClient()

    @staticmethod
    def timestamp_to_str(timestamp: Timestamp, tz: str = 'Asia/Shanghai') -> str:
        return timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    def query_device_status(self, device: str) -> list[dict]:
        results = self.datalayer.query_device_status(device)
        status = []
        for result in results:
            status.append({
                "status": result['status'],
                "time": self.timestamp_to_str(result['ts'])
            })
        return status

    def query_device_current_tag_value(self, device: str, tag: str) -> str:
        return self.client.query_device_current_tag_value(device, tag)
    
    def query_device_tag_history(self, device: str, tag: str, start: str, end: str) -> list[dict]:
        results = self.datalayer.query_tag_range(device, tag, start, end)
        history = []
        for result in results:
            history.append({
                "time": self.timestamp_to_str(result['ts']),
                "value": result['value']
            })
        return history
    
    def query_device_status_range(self, device: str, start: str, end: str) -> list[dict]:
        results = self.datalayer.query_device_status_with_range(device, start, end)
        status = []
        for result in results:
            status.append({
                "status": result['status'],
                "time": self.timestamp_to_str(result['ts'])
            })
        return status
    
    def query_device_by_alias(self, alias: str) -> str | None:
        return self.mariadb.query_device_by_alias(alias)
    
    def datalayer_execute_sql(self, sql: str) -> list[dict]:
        result = self.datalayer.execute_sql(sql)
        return result
    
    def stop(self):
        self.client.disconnect()
    
    def connect(self) -> bool:
        return self.client.connect()
    