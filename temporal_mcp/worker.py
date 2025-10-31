"""Temporal worker to execute workflows and activities."""

import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

from .workflows import (
    GreetingWorkflow,
    DataProcessingWorkflow,
    CalculatorWorkflow,
    LongRunningWorkflow,
)
from .activities import (
    greet_activity,
    process_data_activity,
    calculate_activity,
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_worker(
    temporal_host: str = "localhost:7233",
    task_queue: str = "temporal-mcp-task-queue",
):
    """
    Run a Temporal worker that processes workflows and activities.
    
    Args:
        temporal_host: The Temporal server host and port
        task_queue: The task queue to listen on
    """
    logger.info(f"Connecting to Temporal server at {temporal_host}")
    client = await Client.connect(temporal_host)
    
    logger.info(f"Starting worker on task queue: {task_queue}")
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[
            GreetingWorkflow,
            DataProcessingWorkflow,
            CalculatorWorkflow,
            LongRunningWorkflow,
        ],
        activities=[
            greet_activity,
            process_data_activity,
            calculate_activity,
        ],
    )
    
    logger.info("Worker started successfully")
    await worker.run()


async def main():
    """Main entry point for the worker."""
    import sys
    
    temporal_host = "localhost:7233"
    task_queue = "temporal-mcp-task-queue"
    
    # Allow override via command line arguments
    if len(sys.argv) > 1:
        temporal_host = sys.argv[1]
    if len(sys.argv) > 2:
        task_queue = sys.argv[2]
    
    logger.info("=" * 60)
    logger.info("Temporal MCP Worker")
    logger.info("=" * 60)
    logger.info(f"Temporal Host: {temporal_host}")
    logger.info(f"Task Queue: {task_queue}")
    logger.info("=" * 60)
    
    try:
        await run_worker(temporal_host, task_queue)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
