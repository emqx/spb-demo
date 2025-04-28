from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP
from db.mariadb import Client
import os
import logging


load_dotenv()

mcp = FastMCP("biz_app")
client = Client()

@mcp.tool()
async def get_ot_key(alias:str) -> list[str]:
    '''
    Human normally refer to assets with alias, or human readable descriptions instead of long, random identifiers mixed with characters and numbers. This tool is to use the alias specified by user to return the actual key that usually reported by devices.
    Since the alias information could be not accurate, it possibly return with multiple keys.
    For example, user specify "Orange factory", the function returns "fact_0x00001", which is the unique identifier within organization.

    Return: The key values list that match to the specified alias or descriptive text, system use the key to match the real data reported from devices.
    '''
    return client.get_ot_id_by_alias(alias)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')