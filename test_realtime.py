import time
from agents.shared import supabase
import sys

def handle_change(payload):
    print(f"Update received! {payload}")

if not supabase:
    print("No Supabase client available.")
    sys.exit(1)

print("Subscribing to 'drugs' table changes...")
channel = supabase.channel('test-channel')
channel.on(
    'postgres_changes',
    {'event': '*', 'schema': 'public', 'table': 'drugs'},
    handle_change
).subscribe()

print("Listening... (Press Ctrl+C to stop)")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped.")
