import os
import logging
import time
import signal

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from spb.spb_app import SparkPlugBApp

load_dotenv()

project_path = os.path.abspath(os.path.dirname(__file__))
logging.basicConfig(level=logging.INFO, filename=os.path.join(project_path, "logs/spb_server.log"), filemode="a", format="%(asctime)s - %(levelname)s - %(message)s")

mcp = FastMCP()
spb = SparkPlugBApp()

@mcp.tool()
async def get_spb_tree(device: str | None = None) -> str:
    """Get SparkPlugB tree.

    Args:
        device: Device name. Option, If None, get spb tree for all devices.

    Returns:
        Tree format string, e.g.:
        -- neuron
        |  -- node
        |    -- modbus
        |      -- diagnose/tag1, 0
        |      -- diagnose/tag2, 0
        |      -- diagnose/error_code, 0
    """
    tree = spb.query_spb_tree(device)
    logging.info(f"Tree: \n{tree}")
    return tree

@mcp.tool()
async def get_current_time() -> str:
    """Get current timezone local time.

    Returns:
        Current time, include timezone, format: YYYY-MM-DD HH:MM:SS+Z, e.g. 2023-10-01 00:00:00+0000.
    """
    logging.info("Getting current time")
    return time.strftime("%Y-%m-%d %H:%M:%S.000%z", time.localtime())

@mcp.tool()
async def get_device_tag_value_count_by_sql(sql) -> int:
    """
    To get the returned number of records with specified conditions. 

    tag_values table schema:
		ts: timestamp, timezone is UTC+0
		tag_name: tag name  (string type)
		device: device name  (string type)
		tag_value: tag value (string type)

    If query with time range, time format is YYYY-MM-DD HH:MM:SS+0800, should include timezone, e.g. 2023-10-01 00:00:00+0800; Do not use like Now() or current_timestamp() in sql, because the time zone is different; 
    
    Please use `COUNT(*) AS rec_count` for determining the count of retured records. 
    """

    logging.info(f"Getting get_device_tag_value_count_by_sql by sql {sql}")
    results = spb.db_execute_sql(sql)
    if not results:
        logging.info("No results found")
        return 0
    else:
        return results[0]['rec_count']

@mcp.tool()
async def get_device_tag_value_aggregate_time_window_by_sql(sql) -> str:
    ''' 
    Important: If the return number is larger than 300, then use `date_bin` function, and choose right aggregated time unit to return the records that close to 300. 

    tag_values table schema:
		ts: timestamp, timezone is UTC+0
		tag_name: tag name  (string type)
		device: device name  (string type)
		tag_value: tag value (string type)

    If query with time range, time format is YYYY-MM-DD HH:MM:SS+0800, should include timezone, e.g. 2023-10-01 00:00:00+0800; Do not use like Now() or current_timestamp() in sql, because the time zone is different;          
    
    Use `date_bin(INTERVAL, expression[, origin-timestamp])` to leverage time windows to decrease the number of returned records. The date_bin function truncates the expression based on the input interval time unit. 
    It allows specifying an origin-timestamp as the starting point, which defaults to the UNIX epoch (1970-01-01 00:00:00 UTC) if not provided. 
    For example: date_bin('interval 1 hour', ts) aligns timestamps into 1-hour bins starting from the origin. 
    INTERVAL is string such as, '2 hour', the available time units: 'nanosecond', 'microsecond', 'millisecond', 'second', 'minute, 'hour', 'day', 'week', 'month', 'year'
    For exmaple, with below SQL, it queries the tag_values table and calculates average tag_value as returned tag_value in 1 hour, so reduced the number of record to 1 for every 1 hour.
    `SELECT date_bin('3 minute', ts) AS timepoint, tag_value FROM tag_values WHERE where_expression GROUP BY timepoint, tag_value ORDER BY timepoint;`
    `SELECT date_bin('1 hour', ts) AS timepoint, avg(CAST(tag_value AS FLOAT)) AS value FROM tag_values WHERE where_expression GROUP BY timepoint ORDER BY timepoint;`
    '''
    
    logging.info(f"Getting get_device_tag_value_aggregate_time_window_by_sql by sql {sql}")
    results = spb.db_execute_sql(sql)
    if not results:
        logging.info("No results found")
        return "No results found"

    history = []
    for result in results:
        timestamp = result.get('timepoint')
        history.append({
			"time": spb.timestamp_to_str(timestamp),
			"tag_value": result['tag_value']
		})
    return history

@mcp.tool()
async def get_device_tag_value_distinct_by_sql(sql) -> int:
    """
    To get the returned distinct records with specified conditions. 
    
    tag_values table schema:
		ts: timestamp, timezone is UTC+0
		tag_name: tag name  (string type)
		device: device name  (string type)
		tag_value: tag value (string type)
    
    If query with time range, time format is YYYY-MM-DD HH:MM:SS+0800, should include timezone, e.g. 2023-10-01 00:00:00+0800; Do not use like Now() or current_timestamp() in sql, because the time zone is different;
          
    Please use `SELECT DISTINCT tag_value FROM tag_values WHERE where_expr` for getting the distinct tag_value with specified conditions. 
    """
    logging.info(f"Getting get_device_tag_value_distinct_by_sql by sql {sql}")

    pass

@mcp.tool()
async def get_device_tag_history_raw_values_by_sql(sql) -> str:
	"""Query device raw tag history value from tag_values table without aggregating by window.
     
	tag_values table schema:
		ts: timestamp, timezone is UTC+0
		tag_name: tag name  (string type)
		device: device name  (string type)
		tag_value: tag value (string type)

	Args:
		sql: SQL query, format: SELECT * FROM tag_values [WHERE device = 'device_name'] [AND ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800'] [AND tag_name = 'tag_name']; 
			if query with time range, time format is YYYY-MM-DD HH:MM:SS+0800, should include timezone, e.g. 2023-10-01 00:00:00+0800;
			do not use like Now() or current_timestamp() in sql, because the time zone is different;
			e.g. query all tags history: SELECT * FROM tag_values;
			e.g. query all tags history with time range: SELECT * FROM tag_values WHERE ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800';
			e.g. query all tags history with tag name: SELECT * FROM tag_values WHERE tag_name = 'tag_name';
			e.g. query all tags history with time range and tag name: SELECT * FROM tag_values WHERE ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800' AND tag_name = 'tag_name';
			e.g. query specific device tag history with time range and tag name: SELECT * FROM tag_values WHERE device = 'device_name' AND ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800' AND tag_name = 'tag_name';

	"""
	logging.info(f"Getting get_device_tag_history_raw_values_by_sql by sql {sql}")
	results = spb.db_execute_sql(sql)
	if not results:
		logging.info("No results found")
		return "No results found"

	history = []
	for result in results:
		# Check for timepoint first (from date_bin queries), fall back to ts if not found
		timestamp = result.get('ts')
		history.append({
			"time": spb.timestamp_to_str(timestamp),
			"tag_value": result['tag_value']
		})
	return history

@mcp.tool()
async def get_device_latest_tag_value(device: str, tag: str) -> str:
    """Get device latest tag value.

    Args:
        device: Device name.
        tag: Tag name.
    """
    logging.info(f"Getting get_device_latest_tag_value for {device} {tag}")
    value = spb.query_device_current_tag_value(device, tag)
    return value


@mcp.tool()
async def get_device_status_count_by_sql(sql) -> int:
    """
    Query device status number from devices table with specified condition. This fucntion is used for determining if need to use the time windows to decrease the returned records. 
    
    Please refer to the description of `get_device_status_by_sql` function for the sample SQLs.
    Please use `COUNT(*) AS rec_count` for determining the count of retured records. 
    """

    logging.info(f"Getting device status record number by sql {sql}")
    results = spb.db_execute_sql(sql)
    if not results:
        logging.info("No results found")
        return 0
    else:
        return results[0]['rec_count']

@mcp.tool()
async def get_device_status_by_sql(sql: str) -> str:
    """Query device status info from devices table.

    devices table schema:
        ts: timestamp, timezone is UTC+0
        device: device name
        status: device status, options: online, offline

    Args:
        sql: SQL query, format: SELECT * FROM devices [WHERE device = 'device_name'] [AND ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800'] [AND status = 'online']; 
            if query with time range, time format is YYYY-MM-DD HH:MM:SS+0800, should include timezone, e.g. 2023-10-01 00:00:00+0800;
            do not use like Now() or current_timestamp() in sql, because the time zone is different;
            e.g. query all devices status: SELECT * FROM devices;
            e.g. query all devices status with time range: SELECT * FROM devices WHERE ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800';
            e.g. query all devices status with status: SELECT * FROM devices WHERE status = 'online';
            e.g. query all devices status with time range and status: SELECT * FROM devices WHERE ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800' AND status = 'online';
            e.g. query specific device status: SELECT * FROM devices WHERE device = 'device_name';
            e.g. query specific device status with time range: SELECT * FROM devices WHERE device = 'device_name' AND ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800';
            e.g. query specific device status with status: SELECT * FROM devices WHERE device = 'device_name' AND status = 'online';
            e.g. query specific device status with time range and status: SELECT * FROM devices WHERE device = 'device_name' AND ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800' AND status = 'online';
            e.g. query modbus device status: SELECT * FROM devices WHERE device = 'modbus';
            e.g. query specific device latest status: SELECT * FROM devices WHERE device = 'device_name' ORDER BY ts DESC LIMIT 1;

            Use `date_bin(INTERVAL, expression[, origin-timestamp])` to leverage time windows to decrease the number of returned records. The date_bin function truncates the expression based on the input interval time unit. 
            It allows specifying an origin-timestamp as the starting point, which defaults to the UNIX epoch (1970-01-01 00:00:00 UTC) if not provided. 
            For example: date_bin('interval 1 hour', ts) aligns timestamps into 1-hour bins starting from the origin. 
            INTERVAL is string similar to '2 hour', the available time units: 'nanosecond', 'microsecond', 'millisecond', 'second', 'minute, 'hour', 'day', 'week', 'month', 'year'
            For exmaple, with below SQL, it queries the device table and calculates the aggregated value.
            To get aggregated online status: `SELECT date_bin('1 hour', ts) AS timepoint, count(*) AS status FROM devices WHERE status="online" GROUP BY timepoint ORDER BY timepoint;`
            To get aggregated offline status: `SELECT date_bin('1 hour', ts) AS timepoint, count(*) AS status FROM devices WHERE status="offline" GROUP BY timepoint ORDER BY timepoint;`
    """
    logging.info(f"Getting device status by sql: {sql}")
    results  = spb.db_execute_sql(sql)
    if not results:
        logging.info("No results found")
        return "No results found"

    status = []
    for result in results:
        timestamp = result.get('timepoint', result.get('ts'))
        status.append({
            "status": result['status'],
            "time": spb.timestamp_to_str(timestamp)
        })
    return status
    
from mcp.server import Server
from starlette.requests import Request
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.routing import Mount, Route

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

if __name__ == "__main__":
    import time
    import uvicorn
    
    def signal_handler(sig, frame):
        logging.info("Shutting down...")
        spb.stop()
        logging.warning("SparkPlugB mcp server stopped")
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    logging.info("Starting SparkPlugB mcp server...")

    if not spb.connect():
        exit(1)
    
    starlette_app = create_starlette_app(mcp._mcp_server, debug=True)
    uvicorn.run(starlette_app, host="0.0.0.0", port=8081)

    #try:
        #while True:
            #time.sleep(1)
            #tree = spb.query_spb_tree()
            #logging.info(tree)
    #except:
        #signal_handler(None, None)
