from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from spb_client import SparkPlugClient
import json
from utils.db_util import query

load_dotenv()

mcp = FastMCP("sparkplug_app")
client = SparkPlugClient()
client.connect()  # Connect the client when starting the application

@mcp.tool()
async def get_latest_device_tree() -> str:
    '''
    The tool is used for returning the current latest online device tree. The device tree data is saved in the memory, if no device is connected, then the tree is empty.
    The tools is not for querying the history data.
    Returns the device tree that with list of value similar to 'spBv1.0/{group_id}/DBIRTH/{edge_node_id}/{device_id}/{tag_id}'.
    '''
    return client.ddata_topic_trees()


@mcp.tool()
async def get_latest_devices_values() -> str:
    '''
    The tool is used for returning the current latest online device tree and relevant values. The data is saved in the memory, if no device is connected, then it is empty.
    The tools is not for querying the history data.
    Returns the device tree that with list of value similar to 'spBv1.0/{group_id}/DBIRTH/{edge_node_id}/{device_id}/{tag_id}'.
    '''
    return client.ddata_topic_values()

@mcp.tool()
async def get_node_death(sql:str) -> str:
    '''
    The tool is used for fetching the node death status from 'demo.booleantag' table with specified SQL statement. The SQL sample is as following,
    SELECT * FROM demo.boolean_tags WHERE device_key="spBv1.0/{group_id}/NDEATH/{edge_node_id}"
    As in above SQL sample, user must supply the {group_id}, {edge_node_id} and {device_id} before querying the data.
    
    There are 4 columns in the table 'demo.booleantag',
    - ts(timestamp): The timestamp value for node death event (known as "NDEATH")
    - device_key(string): The MQTT topic name that can identify the node. The node name is similar as following: spBv1.0/{group_id}/NDEATH/{edge_node_id}
      - {group_id}: The Group ID element of the topic namespace provides for a logical grouping of Sparkplug EdgeNodes into the MQTT Server and back out to the consuming Sparkplug Host Applications.
      - {edge_node_id}: The edge_node_id element of the Sparkplug topic namespace uniquely identifies the Sparkplug EdgeNode within the infrastructure.
    - tag_name(string): The metric name for NDEATH
    - tag_value(boolean): The metric value for NDEATH

    Returns the result of the SQL query as a string. The SQL query is expected to fetch the node death status from the 'demo.booleantag' table. 
    '''
    return query(sql)

@mcp.tool()
async def get_node_birth(sql:str) -> str:
    '''
    The tool is used for fetching the node birth status from 'demo.booleantag' table with specified SQL statement. The SQL sample is as following,
    SELECT * FROM demo.boolean_tags WHERE device_key="spBv1.0/{group_id}/NBIRTH/{edge_node_id}"
    As in above SQL sample, user must supply the {group_id}, {edge_node_id} and {device_id} before querying the data.
    
    There are 4 columns in the table 'demo.booleantag',
    - ts(timestamp): The timestamp value for node birth event (known as "NBIRTH")
    - device_key(string): The MQTT topic name that can identify the node. The node name is similar as following: spBv1.0/{group_id}/NBIRTH/{edge_node_id}
      - {group_id}: The Group ID element of the topic namespace provides for a logical grouping of Sparkplug EdgeNodes into the MQTT Server and back out to the consuming Sparkplug Host Applications.
      - {edge_node_id}: The edge_node_id element of the Sparkplug topic namespace uniquely identifies the Sparkplug EdgeNode within the infrastructure.
    - tag_name(string): The metric name for NBIRTH
    - tag_value(boolean): The metric value for NBIRTH

    Returns the result of the SQL query as a string. The SQL query is expected to fetch the node birth status from the 'demo.booleantag' table. 
    '''
    return query(sql)

@mcp.tool()
async def get_device_birth(sql:str) -> str:
    '''
    The tool is used for fetching the device birth status from 'demo.booleantag' table with specified SQL statement. The SQL sample is as following,
    SELECT * FROM demo.boolean_tags WHERE device_key="spBv1.0/{group_id}/DBIRTH/{edge_node_id}/{device_id}"
    As in above SQL sample, user must supply the {group_id}, {edge_node_id} and {device_id} before querying the data.
    
    There are 4 columns in the table 'demo.booleantag',
    - ts(timestamp): The timestamp value for device birth event (known as "DBIRTH")
    - device_key(string): The MQTT topic name that can identify the node. The node name is similar as following: spBv1.0/{group_id}/NBIRTH/{edge_node_id}
      - {group_id}: The Group ID element of the topic namespace provides for a logical grouping of Sparkplug EdgeNodes into the MQTT Server and back out to the consuming Sparkplug Host Applications.
      - {edge_node_id}: The edge_node_id element of the Sparkplug topic namespace uniquely identifies the Sparkplug EdgeNode within the infrastructure.
      - {device_id}: The device_id element of the Sparkplug topic namespace identifies a device attached (physically or logically) to the Sparkplug Edge Node. Note that the device_id is an optional element within the topic namespace as some messages will be either originating or destined to the edge_node_id and the device_id would not be required.
    - tag_name(string): The metric name for DBIRTH
    - tag_value(boolean): The metric value for DBIRTH

    Returns the result of the SQL query as a string. The SQL query is expected to fetch the device birth status from the 'demo.booleantag' table. 
    '''
    return query(sql)

@mcp.tool()
async def get_device_history_data(sqls:list[str]) -> str:
    '''
    The device history data is saved into below 3 different tables. So if user wants to query data for a specific device or tag, you need try to execute query
    against all of the tables.
    - 'demo.int_tags'
    - 'demo.float_tags' 
    - 'demo.double_tags'
    The tool is used for fetching the device data from 'demo.int_tags', 'demo.float_tags' and 'demo.double_tags' tables with specified SQL statement. The SQL sample is as following,
    SELECT * FROM demo.int_tags WHERE device_key="spBv1.0/{group_id}/DDATA/{edge_node_id}/{device_id}" AND tag_name="{tag_name}"
    SELECT * FROM demo.float_tags WHERE device_key="spBv1.0/{group_id}/DDATA/{edge_node_id}/{device_id}" AND tag_name="{tag_name}"
    SELECT * FROM demo.double_tags WHERE device_key="spBv1.0/{group_id}/DDATA/{edge_node_id}/{device_id}" AND tag_name="{tag_name}"
    As in above SQL samples, user must supply the right {group_id}, {edge_node_id}, {device_id} and {tag_name} before querying the data.
    - If you don't know the above variables, you need either let user to specify one or use fuzzy query for the SQL (e.g use LIKE statement).
    The SQL conditions (in WHERE clause) for the 3 tables should be the same.
    
    There are 4 columns in 'demo.int_tags', 'demo.float_tags' and 'demo.double_tags' tables,
    - ts(timestamp): The timestamp value for tag value report event (known as "DDATA")
    - device_key(string): The MQTT topic name that can identify the node. The node name is similar as following: spBv1.0/{group_id}/NBIRTH/{edge_node_id}
      - {group_id}: The Group ID element of the topic namespace provides for a logical grouping of Sparkplug EdgeNodes into the MQTT Server and back out to the consuming Sparkplug Host Applications.
      - {edge_node_id}: The edge_node_id element of the Sparkplug topic namespace uniquely identifies the Sparkplug EdgeNode within the infrastructure.
      - {device_id}: The device_id element of the Sparkplug topic namespace identifies a device attached (physically or logically) to the Sparkplug Edge Node. Note that the device_id is an optional element within the topic namespace as some messages will be either originating or destined to the edge_node_id and the device_id would not be required.
    - tag_name(string): The metric name
    - tag_value(boolean): The metric value

    Returns the result of the SQL query as a string. The SQL query is expected to fetch the device birth status from 'demo.int_tags', 'demo.float_tags' and 'demo.double_tags' tables. 
    '''
    results = []
    for sql in sqls:
        result = query(sql)
        results.append(result)
    return json.dumps({"results": results})

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')