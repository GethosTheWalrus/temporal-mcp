"""Sample Temporal workflows."""

from datetime import timedelta
from dataclasses import dataclass
from temporalio import workflow
from temporalio.common import RetryPolicy

from .activities import (
    greet_activity,
    process_data_activity,
    calculate_activity,
    GreetingInput,
)


@dataclass
class WorkflowInput:
    """Generic workflow input."""
    name: str
    data: dict = None


@workflow.defn(name="GreetingWorkflow")
class GreetingWorkflow:
    """A simple workflow that greets someone."""

    @workflow.run
    async def run(self, name: str) -> str:
        """
        Execute the greeting workflow.
        
        Args:
            name: Name to greet
            
        Returns:
            Greeting message
        """
        workflow.logger.info(f"Starting GreetingWorkflow for {name}")
        
        result = await workflow.execute_activity(
            greet_activity,
            GreetingInput(name=name, greeting="Hello"),
            start_to_close_timeout=timedelta(seconds=10),
        )
        
        workflow.logger.info(f"Completed GreetingWorkflow: {result}")
        return result


@workflow.defn(name="DataProcessingWorkflow")
class DataProcessingWorkflow:
    """A workflow that processes data through multiple activities."""

    def __init__(self) -> None:
        self._status = "initializing"
        self._processed_items = 0

    @workflow.run
    async def run(self, input: WorkflowInput) -> dict:
        """
        Execute the data processing workflow.
        
        Args:
            input: Workflow input with data to process
            
        Returns:
            Processing results
        """
        workflow.logger.info(
            f"Starting DataProcessingWorkflow for {input.name}"
        )
        self._status = "processing"
        
        # Process the data
        result = await workflow.execute_activity(
            process_data_activity,
            input.data or {"sample": "data"},
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
            ),
        )
        
        self._processed_items = result.get("count", 0)
        self._status = "completed"
        
        workflow.logger.info(f"Completed DataProcessingWorkflow: {result}")
        return result

    @workflow.query
    def get_status(self) -> str:
        """Query to get the current workflow status."""
        return self._status

    @workflow.query
    def get_processed_items(self) -> int:
        """Query to get the number of processed items."""
        return self._processed_items

    @workflow.signal
    async def update_data(self, new_data: dict) -> None:
        """Signal to update the data being processed."""
        workflow.logger.info(f"Received update_data signal: {new_data}")
        # In a real workflow, you might process this new data


@workflow.defn(name="CalculatorWorkflow")
class CalculatorWorkflow:
    """A workflow that performs calculations."""

    def __init__(self) -> None:
        self._last_result: float = 0.0
        self._operations_count = 0

    @workflow.run
    async def run(self, operations: list[dict]) -> list[float]:
        """
        Execute multiple calculations.
        
        Args:
            operations: List of operations to perform
                Each operation should have: operation, a, b
            
        Returns:
            List of calculation results
        """
        workflow.logger.info(
            f"Starting CalculatorWorkflow with {len(operations)} operations"
        )
        
        results = []
        for op in operations:
            result = await workflow.execute_activity(
                calculate_activity,
                args=[op["operation"], op["a"], op["b"]],
                start_to_close_timeout=timedelta(seconds=10),
            )
            results.append(result)
            self._last_result = result
            self._operations_count += 1
            
            # Small delay between operations
            await workflow.sleep(timedelta(milliseconds=100))
        
        workflow.logger.info(f"Completed CalculatorWorkflow: {results}")
        return results

    @workflow.query
    def get_last_result(self) -> float:
        """Query to get the last calculation result."""
        return self._last_result

    @workflow.query
    def get_operations_count(self) -> int:
        """Query to get the number of operations performed."""
        return self._operations_count


@workflow.defn(name="LongRunningWorkflow")
class LongRunningWorkflow:
    """A workflow that demonstrates long-running operations and signals."""

    def __init__(self) -> None:
        self._status = "running"
        self._should_stop = False
        self._iterations = 0

    @workflow.run
    async def run(self, max_iterations: int = 100) -> dict:
        """
        Execute a long-running workflow that can be stopped via signal.
        
        Args:
            max_iterations: Maximum number of iterations to run
            
        Returns:
            Workflow execution results
        """
        workflow.logger.info(
            f"Starting LongRunningWorkflow (max {max_iterations} iterations)"
        )
        
        while self._iterations < max_iterations and not self._should_stop:
            # Simulate some work
            await workflow.sleep(timedelta(seconds=1))
            self._iterations += 1
            
            workflow.logger.info(f"Iteration {self._iterations}")
        
        self._status = "stopped" if self._should_stop else "completed"
        
        result = {
            "status": self._status,
            "iterations": self._iterations,
            "max_iterations": max_iterations,
        }
        
        workflow.logger.info(f"Completed LongRunningWorkflow: {result}")
        return result

    @workflow.query
    def get_status(self) -> str:
        """Query to get the current workflow status."""
        return self._status

    @workflow.query
    def get_iterations(self) -> int:
        """Query to get the current iteration count."""
        return self._iterations

    @workflow.signal
    def stop(self) -> None:
        """Signal to stop the workflow."""
        workflow.logger.info("Received stop signal")
        self._should_stop = True
