"""Sample Temporal activities."""

from dataclasses import dataclass
from temporalio import activity


@dataclass
class GreetingInput:
    """Input for greeting activity."""
    name: str
    greeting: str = "Hello"


@activity.defn(name="greet_activity")
async def greet_activity(input: GreetingInput) -> str:
    """
    A simple activity that returns a greeting message.
    
    Args:
        input: The greeting input parameters
        
    Returns:
        A formatted greeting string
    """
    activity.logger.info(f"Greeting {input.name}")
    return f"{input.greeting}, {input.name}!"


@activity.defn(name="process_data_activity")
async def process_data_activity(data: dict) -> dict:
    """
    A sample activity that processes data.
    
    Args:
        data: Dictionary with data to process
        
    Returns:
        Processed data dictionary
    """
    activity.logger.info(f"Processing data: {data}")
    
    # Simulate some processing
    result = {
        "original": data,
        "processed": True,
        "count": len(data),
    }
    
    return result


@activity.defn(name="calculate_activity")
async def calculate_activity(operation: str, a: float, b: float) -> float:
    """
    A sample activity that performs calculations.
    
    Args:
        operation: The operation to perform (add, subtract, multiply, divide)
        a: First operand
        b: Second operand
        
    Returns:
        Result of the calculation
    """
    activity.logger.info(f"Calculating: {a} {operation} {b}")
    
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")
