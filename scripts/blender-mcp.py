# /// script
# dependencies = ["mcp"]
# ///
"""Send a checked-in Python script through the Blender MCP server."""
import asyncio
import os
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server = StdioServerParameters(command='uvx', args=['blender-mcp'],
        env={**os.environ, 'BLENDER_HOST': '127.0.0.1', 'DISABLE_TELEMETRY': 'true'})
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if len(sys.argv) == 1:
                result = await session.call_tool('get_scene_info', {'user_prompt': 'Inspect the rowing character authoring scene'})
            else:
                path = str(Path(sys.argv[1]).resolve())
                code = f"exec(compile(open({path!r}).read(), {path!r}, 'exec'), {{'__file__': {path!r}, '__name__': '__main__'}})"
                result = await session.call_tool('execute_blender_code', {'code': code, 'user_prompt': 'Build and validate the rowing characters from the project script'})
            for content in result.content:
                if hasattr(content, 'text'):
                    print(content.text)

asyncio.run(main())
