from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import logging

from spb.spb_app import SparkPlugBApp

load_dotenv()

logging.basicConfig(level=logging.INFO, filename="./logs/spb_app.log", filemode="a", format="%(asctime)s - %(levelname)s - %(message)s")

mcp = FastMCP()
spb = SparkPlugBApp()

@mcp.tool()
async def get_device_by_alias(alias: str) -> str:
    """Get device name by alias.

    Args:
        alias: Device alias.
    """
    logging.info(f"Getting device by alias: {alias}")
    device = spb.query_device_by_alias(alias)
    if device:
        return device
    else:
        return "Device not found"

@mcp.tool()
async def get_device_all_status(device: str) -> str:
    """Get device status.

    Args:
        device: Device name.
    """
    logging.info(f"Getting device status for {device}")
    status = spb.query_device_status(device)
    result = ""
    for s in status:
        result += f"{s['status']} {s['time']}\n"
    return result

@mcp.tool()
async def get_device_status_range(device: str, start: str, end: str) -> str:
    """Get device status with time range.

    Args:
        device: Device name.
        start: Start time, format: YYYY-MM-DD HH:MM:SS, e.g. 2023-10-01 00:00:00.
        end: End time, format: YYYY-MM-DD HH:MM:SS, e.g. 2025-10-02 00:00:00.
    """
    logging.info(f"Getting device status range for {device} from {start} to {end}")
    status = spb.query_device_status_range(device, start, end)
    result = ""
    for s in status:
        result += f"{s['status']} {s['time']}\n"
    return result

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
    """
    logging.info(f"Getting device status by sql: {sql}")
    results  = spb.datalayer_execute_sql(sql)
    if not results:
        logging.info("No results found")
        return "No results found"

    status = []
    for result in results:
        status.append({
            "status": result['status'],
            "time": spb.timestamp_to_str(result['ts'])
        })
    return status

@mcp.tool()
async def get_device_current_tag_value(device: str, tag: str) -> str:
    """Get device current tag value.

    Args:
        device: Device name.
        tag: Tag name.
    """
    logging.info(f"Getting device current tag value for {device} {tag}")
    value = spb.query_device_current_tag_value(device, tag)
    return value

@mcp.tool()
async def get_device_tag_history(device: str, tag: str, start: str, end: str) -> str:
    """Get device tag history value from db.

    Args:
        device: Device name.
        tag: Tag name.
        start: Start time, format: YYYY-MM-DD HH:MM:SS+0800, should include timezone, e.g. 2023-10-01 00:00:00+0800.
        end: End time, format: YYYY-MM-DD HH:MM:SS+0800, should include timezone, e.g. 2025-10-02 00:00:00+0800.
    """
    logging.info(f"Getting device tag history for {device} {tag} from {start} to {end}")
    history = spb.query_device_tag_history(device, tag, start, end)
    result = ""
    for h in history:
        result += f"{h['time']} {h['value']}\n"
    return result

@mcp.tool()
async def get_device_tag_history_by_sql(sql) -> str:
	"""Query device tag history value from tags table.

	tags table schema:
		ts: timestamp, timezone is UTC+0
		tag: tag name
		device: device name
		value: tag value

	Args:
		sql: SQL query, format: SELECT * FROM tags [WHERE device = 'device_name'] [AND ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800'] [AND tag = 'tag_name']; 
			if query with time range, time format is YYYY-MM-DD HH:MM:SS+0800, should include timezone, e.g. 2023-10-01 00:00:00+0800;
			do not use like Now() or current_timestamp() in sql, because the time zone is different;
			e.g. query all tags history: SELECT * FROM tags;
			e.g. query all tags history with time range: SELECT * FROM tags WHERE ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800';
			e.g. query all tags history with tag name: SELECT * FROM tags WHERE tag = 'tag_name';
			e.g. query all tags history with time range and tag name: SELECT * FROM tags WHERE ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800' AND tag = 'tag_name';
			e.g. query specific device tag history with time range and tag name: SELECT * FROM tags WHERE device = 'device_name' AND ts > '2023-10-01 00:00:00+0800' AND ts < '2025-10-02 00:00:00+0800' AND tag = 'tag_name';
	"""
	logging.info(f"Getting device tag history by sql {sql}")
	results = spb.datalayer_execute_sql(sql)
	if not results:
		logging.info("No results found")
		return "No results found"

	history = []
	for result in results:
		history.append({
			"time": spb.timestamp_to_str(result['ts']),
			"value": result['value']
		})
	return history
    

logging.info("Starting SparkPlugB mcp server...")

if not spb.connect():
    exit(1)

mcp.run(transport="stdio")

# sleep, wait ctrl+c
spb.stop()
logging.info("Disconnected from MQTT broker.")
