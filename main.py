"""
PharmaSentinel Main Entry Point

Runs the pipeline orchestrator in a continuous loop with configurable interval.
This is the production entry point for the PharmaSentinel system.

Usage:
    python main.py                    # Run continuously with default 60-minute interval
    python main.py --once             # Run once and exit
    python main.py --interval 30      # Run with custom interval (minutes)
"""

import os
import sys
import time
import argparse
from datetime import datetime
from agents.pipeline import run_pipeline, run_quick_pipeline
from agents.shared import validate_environment

def main():
    """Main entry point for PharmaSentinel."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='PharmaSentinel Pipeline Runner')
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run pipeline once and exit (default: run continuously)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=int(os.getenv('PIPELINE_INTERVAL_MINUTES', 60)),
        help='Interval between pipeline runs in minutes (default: 60)'
    )
    args = parser.parse_args()

    print("\n" + "="*80)
    print("PHARMASENTINEL - Hospital Pharmacy Supply Chain Intelligence")
    print("="*80 + "\n")

    # Validate environment
    print("Validating environment configuration...")
    env_valid = validate_environment()

    if not env_valid:
        print("\n⚠️  WARNING: Some environment variables are missing or using placeholders.")
        print("The system will continue but some features may not work correctly.")
        print("Please update your .env file with actual values.\n")

        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting. Please configure environment variables and try again.")
            sys.exit(1)
    else:
        print("✓ Environment validated\n")

    # Run mode
    if args.once:
        print(f"Mode: Single execution")
        print(f"Starting pipeline at {datetime.now().isoformat()}\n")

        try:
            result = run_pipeline()
            print(f"\n✓ Pipeline completed successfully")
            print(f"Status: {result.get('status')}")
            print(f"Run ID: {result.get('run_id')}")
            print(f"Duration: {result.get('total_duration_seconds', 0):.2f}s")

            if result.get('errors'):
                print(f"\n⚠️  Errors encountered:")
                for error in result['errors']:
                    print(f"  - {error}")
                sys.exit(1)
            else:
                sys.exit(0)

        except Exception as e:
            print(f"\n✗ Pipeline failed: {e}")
            sys.exit(1)

    else:
        # Continuous mode - Async Realtime Listener
        import asyncio
        from supabase import create_async_client
        from agents.shared import SUPABASE_URL, SUPABASE_SERVICE_KEY

        if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
            print("Error: Supabase credentials missing.")
            sys.exit(1)

        async def listen_for_changes():
            print(f"Mode: Continuous execution (Realtime Trigger)")
            
            # Initialize Async Client
            async_supabase = await create_async_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            print(f"Listening for changes on 'drugs' table...")
            
            # Smart Loop Prevention
            last_run_time = 0
            min_interval = 2  # Seconds - debounce quick clicks
            # Counter to skip agent self-updates from full pipeline (agent_0 updates 10 drugs)
            skip_count = 0

            def handle_db_change(payload):
                nonlocal last_run_time, skip_count
                current_time = time.time()

                
                # Inspect Payload Structure (Debug)
                try:
                    # supabase-py Realtime returns: {'data': {...}, 'ids': [...]}
                    # The actual event info is in payload['data']
                    data = payload.get('data', {}) if isinstance(payload, dict) else payload
                    
                    table_name = data.get('table')
                    # 'type' can be a string or an enum like RealtimePostgresChangesListenEvent.Update
                    event_type_raw = data.get('type')
                    if hasattr(event_type_raw, 'value'):
                        event_type = event_type_raw.value  # Get string from enum
                    else:
                        event_type = str(event_type_raw) if event_type_raw else None
                    
                    new_record = data.get('record', {})
                    old_record = data.get('old_record', {})

                    print(f"\n[Realtime] Event: {event_type} on table '{table_name}'", flush=True)
                    
                except Exception as e:
                    print(f"[Realtime Error] Failed to parse payload: {e}", flush=True)
                    return

                # Only process valid database events
                if event_type not in ('UPDATE', 'INSERT', 'DELETE'):
                    print(f"  -> Ignoring non-database event: {event_type}")
                    return
                
                if table_name != 'drugs':
                    print(f"  -> Ignoring event on table: {table_name}")
                    return

                # Skip counter: After FULL pipeline runs, agent_0 updates 10 drugs
                # Quick pipeline doesn't update DB, so no skip needed after quick runs
                if skip_count > 0:
                    skip_count -= 1
                    print(f"  -> Skipping agent self-update ({skip_count} remaining to skip)")
                    return

                # Check Debounce (too fast user clicks)
                if current_time - last_run_time < min_interval:
                    print(f"  -> Skipping (debounced)")
                    return

                print(f"[Realtime] Triggering QUICK pipeline (Agent 0 Quick Mode + Overseer)...", flush=True)
                last_run_time = time.time()
                
                # Run quick pipeline in separate thread (Overseer only)
                import concurrent.futures
                try:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_quick_pipeline)
                        result = future.result()
                    # Quick pipeline doesn't update DB, so no skip_count needed
                    print(f"✓ Quick pipeline completed. Status: {result.get('status')}", flush=True)
                except Exception as e:
                    print(f"✗ Quick pipeline failed: {e}")


            try:
                # client.channel is synchronous
                channel = async_supabase.channel('drug-updates')
                
                # channel.on returns the channel (synchronous builder)
                # AsyncRealtimeChannel uses on_postgres_changes instead of .on()
                await channel.on_postgres_changes(
                    event='*',
                    schema='public',
                    table='drugs',
                    callback=handle_db_change
                ).subscribe()

                print("✓ Subscribed to Realtime events on 'drugs' table.")
                
                # Initial Run on Startup (as requested)
                print("\n[Startup] Running initial pipeline analysis...")
                import concurrent.futures
                try:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_pipeline)
                        result = future.result()
                    # After FULL pipeline, agent_0 updates 10 drugs -> skip those events
                    skip_count = 10
                    print(f"✓ Initial pipeline run completed. Status: {result.get('status')}")
                    print(f"  (Will skip next {skip_count} updates to prevent self-loop)")
                except Exception as e:
                    print(f"✗ Initial pipeline run failed: {e}")
                    skip_count = 10  # Still set on failure

                print("\n  - Waiting for updates... (Press Ctrl+C to stop)")


                # Keep alive
                while True:
                    await asyncio.sleep(1)

            except Exception as e:
                print(f"Realtime error: {e}")
                # Don't try to close the client as it doesn't have a close method exposed here


        try:
            asyncio.run(listen_for_changes())
        except KeyboardInterrupt:
            print("\nShutting down...")
            sys.exit(0)

if __name__ == '__main__':
    # Imports are handled inside main functions or at top
    pass
    main()
