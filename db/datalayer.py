from datalayer_client import Client
import logging
from pandas import Timestamp

# datalayers

# tags table
# CREATE TABLE tag_values (
#  ts TIMESTAMP(9) NOT NULL DEFAULT CURRENT_TIMESTAMP,
#  tag_name STRING,
#  device STRING,
#  value STRING,
#  timestamp KEY (ts))
#  PARTITION BY HASH(device) PARTITIONS 8
#  ENGINE=TimeSeries
#  with (ttl='10d');

# deivce status table (online, offline)
# CREATE TABLE devices (
#  ts TIMESTAMP(9) NOT NULL DEFAULT CURRENT_TIMESTAMP,
#  device STRING,
#  status STRING,
#  timestamp KEY (ts))
#  PARTITION BY HASH(device) PARTITIONS 8
#  ENGINE=TimeSeries
#  with (ttl='10d');

class DB:
    def __init__(self):
        self.datalayers = Client()
        self.datalayers.use_database("demo")
        self.create_device_status_table()
        self.create_tags_table()

    def create_device_status_table(self):
        sql = """
         CREATE TABLE IF NOT EXISTS devices (
          ts TIMESTAMP(9) NOT NULL DEFAULT CURRENT_TIMESTAMP,
          device STRING,
          status STRING,
          timestamp KEY (ts))
          PARTITION BY HASH(device) PARTITIONS 8
          ENGINE=TimeSeries
          with (ttl='10d');
        """
        self.datalayers.execute(sql)
    
    def create_tags_table(self):
        sql = """
         CREATE TABLE IF NOT EXISTS tag_values (
          ts TIMESTAMP(9) NOT NULL DEFAULT CURRENT_TIMESTAMP,
          tag_name STRING,
          device STRING,
          value STRING,
          timestamp KEY (ts))
          PARTITION BY HASH(device) PARTITIONS 8
          ENGINE=TimeSeries
          with (ttl='10d');
        """
        self.datalayers.execute(sql)
    
    def insert_tags(self, tags:list[tuple]):
        sql = "INSERT INTO tag_values (ts, tag_name, device, value) VALUES "
        for tag in tags:
            sql += f"('{tag[0]}', '{tag[1]}', '{tag[2]}', '{tag[3]}'), "
        sql = sql[:-2] + ";"
        logging.info(f"SQL: {sql}")
        result = self.datalayers.execute(sql)
        logging.info(f"Inserted {result} rows into tags table")
    
    def insert_tag(self, device: str, tag: str, value: str, time: Timestamp):
        result = self.datalayers.execute(f"INSERT INTO tag_values (ts, tag_name, device, value) VALUES ('{time}', '{tag}', '{device}', '{value}')")
        logging.debug(f"Inserted {result} rows into tags table")
    
    def query_tags(self, device: str) -> list[dict]:
        result = self.datalayers.execute(f"SELECT * FROM tag_values WHERE device = '{device}'")
        return result.to_dict(orient="records")
    
    def query_tag(self, device: str, tag: str) -> list[dict]:
        result = self.datalayers.execute(f"SELECT * FROM tag_values WHERE device = '{device}' AND tag_name = '{tag}'")
        return result.to_dict(orient="records")
    
    def query_tag_range(self, device: str, tag: str, start: str, end: str) -> list[dict]:
        sql = f"SELECT * FROM tag_values WHERE device = '{device}' AND tag_name = '{tag}' AND ts > '{start}' AND ts < '{end}'"
        logging.info(f"SQL: {sql}")
        result = self.datalayers.execute(sql)
        return result.to_dict(orient="records")
    
    def update_device_status(self, time: Timestamp, device: str, status: str):
        result = self.datalayers.execute(f"INSERT INTO devices (ts, device, status) VALUES ('{time}', '{device}', '{status}')")
        logging.debug(f"Inserted {result} rows into devices table")
    
    def query_device_status_with_range(self, device: str, start: str, end: str) -> list[dict]:
        result = self.datalayers.execute(f"SELECT * FROM devices WHERE device = '{device}' AND ts > '{start}' AND ts < '{end}'")
        return result.to_dict(orient="records")

    def query_device_status(self, device: str) -> list[dict]:
        result = self.datalayers.execute(f"SELECT * FROM devices WHERE device = '{device}'")
        return result.to_dict(orient="records")
    
    def execute_sql(self, sql: str) -> list[dict]:
        result = self.datalayers.execute(sql)
        return result.to_dict(orient="records")