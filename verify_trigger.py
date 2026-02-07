import asyncio
from supabase import create_async_client, create_client
from agents.shared import SUPABASE_URL, SUPABASE_SERVICE_KEY
import sys
import time

# Sync client for triggering the update
sync_supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

async def test_trigger():
    print(f"--- Starting Realtime Verification ---")
    
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        print("Credentials missing")
        return

    # 1. Setup Listener
    async_client = await create_async_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("Async client created.")

    event_received = asyncio.Event()

    def handle_change(payload):
        print(f"!!! SUCCESS: Event received: {payload}")
        event_received.set()

    try:
        channel = async_client.channel('test-channel')
        await channel.on_postgres_changes(
            event='*', 
            schema='public', 
            table='drugs', 
            callback=handle_change
        ).subscribe()
        print("Subscribed to 'drugs' updates. Waiting for event...")

        # Give it a second to establish connection
        await asyncio.sleep(2)

        # 2. Trigger Update
        print("Triggering update via sync client...")
        # Get a drug to update (Levofloxacin or first one)
        res = sync_supabase.table('drugs').select('id, stock_quantity, name').limit(1).execute()
        if not res.data:
            print("No drugs found to update.")
            return
        
        drug = res.data[0]
        new_qty = drug['stock_quantity']  # Keep same quantity, just touch it
        # Or toggle +1/-1 to ensure change
        
        print(f"Touching drug: {drug['name']} (ID: {drug['id']})")
        sync_supabase.table('drugs').update({'stock_quantity': new_qty}).eq('id', drug['id']).execute()
        print("Update sent.")

        # 3. Wait for Event
        try:
            await asyncio.wait_for(event_received.wait(), timeout=10)
            print("\n✅ VERIFICATION PASSED: Realtime updates are working.\n")
        except asyncio.TimeoutError:
            print("\n❌ VERIFICATION FAILED: Timed out waiting for event.")
            print("Possible causes:")
            print("1. 'Realtime' is NOT ENABLED for the 'drugs' table in Supabase Dashboard.")
            print("2. Network restrictions blocking WebSocket.")
            print("3. RLS policies preventing the Service Key from subscribing (unlikely but possible).")

    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        await async_client.close()

if __name__ == "__main__":
    asyncio.run(test_trigger())
