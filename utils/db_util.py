from dotenv import load_dotenv
import http
import json
from http.client import HTTPConnection
import os
import asyncio
from typing import Dict, Any
from datetime import datetime

load_dotenv()

host = os.getenv('DB_HOST', "")
port = os.getenv('DB_PORT', 8361)
token = os.getenv("DB_TOKEN", "")

url = f"http://{host}:{port}/api/v1/sql"
headers = {
    "Content-Type": "application/binary",
    "Authorization": f"Basic {token}"
}

def __format_timestamp(timestamp_ms: str) -> str:
    """Convert millisecond timestamp to datetime string format"""
    # Convert string to integer
    ts_ms = int(timestamp_ms)
    # Convert milliseconds to datetime
    dt = datetime.fromtimestamp(ts_ms / 1000.0)
    # Format datetime with milliseconds
    return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # [:-3] to get only 3 decimal places

def generate_sql_values(records) -> Dict[str, str]:
    """Generate SQL values strings for each data type"""
    int_values = []
    float_values = []
    double_values = []
    boolean_values = []
    
    for record in records:
        metric = record['metric']
        datatype = metric['datatype']
        formatted_time = __format_timestamp(metric['timestamp'])
        base_values = f"('{formatted_time}', '{record['device_key']}', '{metric['name']}'"
        
        if datatype == 2:  # Integer type
            int_values.append(f"{base_values}, {metric['intValue']})")
        elif datatype == 9:  # Float type
            float_values.append(f"{base_values}, {metric['floatValue']})")
        elif datatype == 10:  # Double type
            double_values.append(f"{base_values}, {metric['doubleValue']})")
        elif datatype == 11:  # Boolean type
            boolean_values.append(f"{base_values}, {metric['booleanValue']})")
    
    sql_statements = {}
    
    if int_values:
        sql_statements['int'] = """
            INSERT INTO demo.int_tags (ts, device_key, tag_name, tag_value)
            VALUES """ + ",\n".join(int_values)
    
    if float_values:
        sql_statements['float'] = """
            INSERT INTO demo.float_tags (ts, device_key, tag_name, tag_value)
            VALUES """ + ",\n".join(float_values)
    
    if double_values:
        sql_statements['double'] = """
            INSERT INTO demo.double_tags (ts, device_key, tag_name, tag_value)
            VALUES """ + ",\n".join(double_values)
    
    if boolean_values:
        sql_statements['boolean'] = """
            INSERT INTO demo.boolean_tags (ts, device_key, tag_name, tag_value)
            VALUES """ + ",\n".join(boolean_values)

    return sql_statements

async def insert_db(records) -> None:
    """
    Insert records into appropriate tables based on datatype.
    
    Args:
        records: List of dictionaries containing device_key and metric information
        
    Example record format:
    {
        "device_key": "spBv1.0/factory_1/DDATA/assembly_1/test",
        "metric": {
            "name": "group2/voltage",
            "timestamp": "1743125955419",
            "datatype": 9,
            "floatValue": 3.5
        }
    }
    """
    
    try:
        # Generate SQL statements for each data type
        sql_statements = generate_sql_values(records)
        # Execute each SQL statement
        for data_type, sql in sql_statements.items():
            conn = http.client.HTTPConnection(host=host, port=port)
            # print(sql, end="\n")
            conn.request(method="POST", url=url, headers=headers, body=sql)
            # Get and print detailed response information
            conn.close()
            
        
        # print(f"\nGenerated SQL statements for: {', '.join(sql_statements.keys())} types")
        
    except Exception as e:
        # __print_response(conn)
        print(f"Error inserting records: {e}")

def schedule_insert_db(records):
    """Schedule the async insert_db function to run in the background"""
    loop = asyncio.get_event_loop()
    if not loop.is_running():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    asyncio.create_task(insert_db(records))

def __print_response(conn: HTTPConnection):
    with conn.getresponse() as response:
        response_body = response.read().decode('utf-8')
        print(f"Status: {response.status} {response.reason}")
        print("Headers:")
        for header, value in response.getheaders():
            print(f"  {header}: {value}")
        print("Body:")
        try:
            # Try to parse and pretty print JSON response
            response_json = json.loads(response_body)
            print(json.dumps(response_json, indent=2))
        except json.JSONDecodeError:
            # If not JSON, print raw response
            print(response_body)

def query(sql:str)->Any:
    conn = http.client.HTTPConnection(host=host, port=port)
    conn.request(method="POST", url=url, headers=headers, body=sql)
    with conn.getresponse() as response:
        data = response.read().decode('utf-8')
        obj = json.loads(data)
        return obj


def print_query_result(conn: HTTPConnection):
    with conn.getresponse() as response:
        data = response.read().decode('utf-8')
        obj = json.loads(data)
        columns = obj['result']['columns']
        rows = obj['result']['values']
        print(columns)
        for row in rows:
            print(row)

# if __name__ == "__main__":
#     result = query("select * from demo.float_tags; select * from demo.boolean_tags")
#     print(json.dumps(result, indent=2))

