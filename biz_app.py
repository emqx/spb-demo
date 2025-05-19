from dotenv import load_dotenv
import signal


from mcp.server.fastmcp import FastMCP
from db.mariadb import Client
import logging
import os
from db.rag import RAG

load_dotenv()

project_path = os.path.abspath(os.path.dirname(__file__))
logging.basicConfig(level=logging.INFO, filename=os.path.join(project_path, "logs/biz_server.log"), filemode="a", format="%(asctime)s - %(levelname)s - %(message)s")

mcp = FastMCP()
client = Client()

def get_rag() -> RAG:
    rag = RAG()
    try:
        rag.load_index_from_hybrid_chunks()
    except Exception as e:
        rag.create_index_from_hybrid_chunks("./data/3HAC066553-010_20250426183500.md")
    return rag
rag = get_rag()

@mcp.tool()
async def get_ot_key(alias:str) -> list[str]:
    '''
    Human normally refer to assets with alias, or human readable descriptions instead of long, random identifiers mixed with characters and numbers. This tool is to use the alias specified by user to return the actual key that usually reported by devices.
    Since the alias information could be not accurate, it possibly return with multiple keys.
    For example, user specify "Orange factory", the function returns "fact_0x00001", which is the unique identifier within organization.

    Return: The key values list that match to the specified alias or descriptive text, system use the key to match the real data reported from devices.
    '''
    return client.get_ot_id_by_alias(alias)

@mcp.tool()
def search_error_info_by_code(query: str) -> str:
    """
    Search for error information in the document vector database using a query string.

    This function uses a RAG (Retrieval-Augmented Generation) system to search through
    indexed documents and retrieve relevant error information based on the provided query.

    Args:
        query (str): The search query string, typically an error code or error-related text.
        E,g: 10040, 10091 etc.

    Returns:
        str: The search response containing relevant error information found in the documents.

    Example:
        >>> result = search_error_info_by_code("10042")
        >>> print(result)
        "10042 Axis synchronized Description
        A fine calibration or update of revolution counter(s) was made...."
    """
    logging.info(f"Searching documents with query: {query}")
    response = rag.query(query)
    logging.info(f"Search result: {response}")
    return str(response)

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
    import uvicorn
    
    def signal_handler(sig, frame):
        logging.info("Shutting down...")
        logging.warning("biz app mcp server stopped")
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    logging.info("Starting biz app mcp server...")

    starlette_app = create_starlette_app(mcp._mcp_server, debug=True)
    uvicorn.run(starlette_app, host="0.0.0.0", port=8082)
