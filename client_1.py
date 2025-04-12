from utils import MCPClient
from utils import config
import os
import asyncio
from pprint import pprint
from contextlib import asynccontextmanager


mcp_client_config = config.MCPClientConfig(
    mcpServers={
        "demo_server": config.MCPServerConfig(
            command="/Users/rocky/Downloads/workspace/spb_demo/venv/bin/python",
            args=["/Users/rocky/Downloads/workspace/spb_demo/spb_app.py"],
        ),
        "mapping_server": config.MCPServerConfig(
            command="/Users/rocky/Downloads/workspace/spb_demo/venv/bin/python",
            args=["/Users/rocky/Downloads/workspace/spb_demo/biz_app.py"],
        )
        # add here other servers ...
    }
)
#  self.model = os.getenv("DS_MODEL_NAME")
#         print(self.model)
#         self.client = OpenAI(api_key = os.getenv("DS_API_KEY"), base_url = os.getenv("DS_API_BASE_URL"))

llm_client_config = config.LLMClientConfig(
    api_key=os.getenv("DS_API_KEY"),
    base_url=os.getenv("DS_API_BASE_URL"),
    
)

#llm_request_config = config.LLMRequestConfig(model=os.getenv("DS_MODEL_NAME"), stream=True)
llm_request_config = config.LLMRequestConfig(model=os.getenv("DS_MODEL_NAME"))
   
@asynccontextmanager
async def get_client():
    client = MCPClient(
        mcp_client_config,
        llm_client_config,
        llm_request_config,
    )
    try:
        yield client
    finally:
        await client.cleanup()

async def main():
    async with get_client() as client:
        await client.connect_to_server("demo_server")
        await client.connect_to_server("mapping_server")

        messages = [
            {
                "role": "system",
                "content": (
                    "Leverage the available tools to complete the task."
                ),
            },
            {"role": "user", "content":'"Query the offline status of  "Big boy" of last week.'},
        ]
        
        messages = await client.process_messages(messages)
        print("LEN MESSAGES", len(messages))
        pprint(messages)



if __name__ == "__main__":
    asyncio.run(main())