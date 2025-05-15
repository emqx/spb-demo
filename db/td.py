from td_client import Client
import logging
from pandas import Timestamp
from dotenv import load_dotenv

load_dotenv()

class DB:
    def __init__(self):
        self.td = Client()
        self.create_db()
        self.use_database("demo")
        self.create_status_table()
        self.create_tags_table()
    
    def create_db(self):
        self.td.execute("CREATE DATABASE IF NOT EXISTS demo")
    
    def use_database(self, db_name: str):
        self.td.execute(f"USE {db_name}")
    
    def create_status_table(self):
        sql = """
        CREATE TABLE IF NOT EXISTS devices (
            `ts` TIMESTAMP,
            `device` BINARY(128),
            `status` BINARY(32))
        """
        self.td.execute(sql)
    
    def create_tags_table(self):
        sql = """
        CREATE TABLE IF NOT EXISTS tag_values (
            `ts` TIMESTAMP, `tag_name` BINARY(128), `value` BINARY(128), `device` BINARY(128))
        """
        self.td.execute(sql)
    
    def update_device_status(self, time: Timestamp, device: str, status: str):
        sql = f"INSERT INTO devices VALUES ('{time}', '{device}', '{status}')"
        logging.info(f"SQL: {sql}")
        result = self.td.execute(sql)
        logging.debug(f"Inserted {result} rows into devices table")
    
    def insert_tag(self, device: str, tag: str, value: str, time: Timestamp):
        timestamp = time.timestamp() * 1000
        timestamp = int(timestamp)
        sql = f"INSERT INTO tag_values VALUES ('{timestamp}', '{tag}', '{value}', '{device}')"
        result = self.td.execute(sql)
        logging.debug(f"Inserted {result} rows into tag_values table")
    
    def query_tag_range(self, device: str, tag: str, start: str, end: str) -> list[dict]:
        sql = f"SELECT * FROM tag_values WHERE device = '{device}' AND tag_name = '{tag}' AND ts > '{start}' AND ts < '{end}'"
        return self.td.execute(sql)
    
    def query_device_status(self, device: str) -> list[dict]:
        sql = f"SELECT * FROM devices WHERE device = '{device}'"
        return self.td.query(sql)
    
    def query_device_status_range(self, device: str, start: str, end: str) -> list[dict]:
        sql = f"SELECT * FROM devices WHERE device = '{device}' AND ts > '{start}' AND ts < '{end}'"
        return self.td.query(sql)
    
    def execute_sql(self, sql: str) -> list[dict]:
        result = self.td.execute(sql)
        return result.to_dict(orient="records")
    
    def query_sql(self, sql: str) -> list[dict]:
        result = self.td.query(sql)
        lresult = []
        index = 0;
        for row in result:
            lresult.append({result.fields[index].name(): row[0]})
            index += 1
        return lresult

if __name__ == "__main__":
    import os
    project_path = os.path.abspath(os.path.dirname(__file__))
    logging.basicConfig(level=logging.INFO, filename=os.path.join(project_path, "../logs/spb_server.log"), filemode="a", format="%(asctime)s - %(levelname)s - %(message)s")
    db = DB()
    db.create_db()
    db.query_sql("SELECT COUNT(*) AS rec_count FROM tag_values")