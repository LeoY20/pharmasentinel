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
from agents.pipeline import run_pipeline
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
        # Continuous mode
        interval_seconds = args.interval * 60
        print(f"Mode: Continuous execution")
        print(f"Interval: {args.interval} minutes ({interval_seconds} seconds)")
        print(f"Press Ctrl+C to stop\n")

        run_count = 0

        try:
            while True:
                run_count += 1
                print(f"\n{'='*80}")
                print(f"EXECUTION #{run_count}")
                print(f"Started: {datetime.now().isoformat()}")
                print(f"{'='*80}\n")

                try:
                    result = run_pipeline()
                    print(f"\n✓ Execution #{run_count} completed")
                    print(f"Status: {result.get('status')}")
                    print(f"Duration: {result.get('total_duration_seconds', 0):.2f}s")

                    if result.get('errors'):
                        print(f"⚠️  Errors: {len(result['errors'])}")
                        for error in result['errors']:
                            print(f"  - {error}")

                except Exception as e:
                    print(f"\n✗ Execution #{run_count} failed: {e}")
                    print("Continuing to next scheduled run...")

                # Calculate next run time
                next_run = datetime.now().timestamp() + interval_seconds
                next_run_dt = datetime.fromtimestamp(next_run)

                print(f"\nNext run scheduled for: {next_run_dt.isoformat()}")
                print(f"Sleeping for {args.interval} minutes...")

                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print(f"\n\nReceived interrupt signal. Shutting down gracefully...")
            print(f"Total executions: {run_count}")
            print(f"Goodbye!\n")
            sys.exit(0)

if __name__ == '__main__':
    main()
