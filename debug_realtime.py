import asyncio
from supabase import create_async_client
from agents.shared import SUPABASE_URL, SUPABASE_SERVICE_KEY
import sys

async def debug_channel():
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        print("Credentials missing")
        return

    print("Creating client...", flush=True)
    client = await create_async_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    print("Creating channel...", flush=True)
    channel = client.channel('test-channel')
    
    print(f"Channel type: {type(channel)}", flush=True)
    print("Channel attributes:", flush=True)
    for attr in dir(channel):
        if not attr.startswith('_'):
            print(f"  - {attr}", flush=True)
            
    # Try to close if possible, or just exit
    # await client.close() 

if __name__ == "__main__":
    asyncio.run(debug_channel())
