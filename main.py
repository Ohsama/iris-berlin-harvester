#!/usr/bin/env python3
"""
IRIS-SIG-17: Berlin Bebauungspläne Portal Harvester
CLI Entry point.
"""

import argparse
import json
import logging
import sys

from app.config.settings import Settings
from app.config.paths import ProjectPaths
from app.runners.harvest_runner import HarvestRunner


def configure_logging(level_name: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level_name.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="IRIS-SIG-17: Berlin Bebauungspläne Portal Harvester (Signal Ingestion)"
    )
    parser.add_argument(
        "--mode",
        choices=["offline", "live"],
        default="offline",
        help="Harvest mode: 'offline' (verified fixtures) or 'live' (direct network)",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip database ingestion and export JSON/GeoJSON files only",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Custom SQLAlchemy database URL (e.g., sqlite:///dev_staging.db)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity level",
    )

    args = parser.parse_args()
    configure_logging(args.log_level)

    settings = Settings()
    settings.use_offline_fixtures = (args.mode == "offline")
    if args.db_url:
        settings.postgres_host = args.db_url  # Used if custom DB URL is provided

    paths = ProjectPaths()
    runner = HarvestRunner(settings=settings, paths=paths)

    print("=" * 70)
    print("IRIS-SIG-17: Berlin Bebauungsplaene Portal Harvester")
    print(f"Mode: {args.mode.upper()} | Save to DB: {not args.no_db}")
    print("=" * 70)

    try:
        results = runner.run(save_to_db=not args.no_db)
        print("\n" + "=" * 70)
        print("EXECUTION SUMMARY:")
        print(json.dumps(results, indent=2))
        print("=" * 70)
        print(f"Sample signals exported to: {paths.output}")
        sys.exit(0)
    except Exception as exc:
        logging.exception("Harvester execution failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
