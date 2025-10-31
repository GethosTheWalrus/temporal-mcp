#!/usr/bin/env python3
"""Populate Temporal with test data to verify all MCP tools."""

import asyncio
from datetime import timedelta
from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow, ScheduleSpec
from temporal_mcp.workflows import GreetingWorkflow, DataProcessingWorkflow, CalculatorWorkflow, LongRunningWorkflow
from temporal_mcp.activities import greet_activity, process_data_activity, calculate_activity


async def populate_test_data():
    """Create various workflows and schedules for testing."""
    
    print("🔌 Connecting to Temporal...")
    client = await Client.connect("localhost:7233")
    print("✅ Connected!\n")
    
    task_queue = "temporal-mcp-task-queue"
    
    # Add timestamp to make IDs unique
    import time
    timestamp = int(time.time())
    
    # 1. Start some completed workflows
    print("📝 Creating completed workflows...")
    
    # Simple greeting workflow
    handle1 = await client.start_workflow(
        GreetingWorkflow.run,
        "Alice",
        id=f"test-greeting-1-{timestamp}",
        task_queue=task_queue,
    )
    print(f"  ✅ Started: {handle1.id}")
    
    handle2 = await client.start_workflow(
        GreetingWorkflow.run,
        "Bob",
        id=f"test-greeting-2-{timestamp}",
        task_queue=task_queue,
    )
    print(f"  ✅ Started: {handle2.id}")
    
    # 2. Start a long-running workflow (will still be running)
    print("\n⏱️  Creating long-running workflow...")
    handle3 = await client.start_workflow(
        LongRunningWorkflow.run,
        3600,  # max iterations
        id=f"test-long-running-1-{timestamp}",
        task_queue=task_queue,
    )
    print(f"  ✅ Started: {handle3.id} (will run for ~1 hour)")
    
    # 3. Start a data processing workflow that supports queries and signals
    print("\n📊 Creating data processing workflow (supports queries/signals)...")
    from temporal_mcp.workflows import WorkflowInput
    handle4 = await client.start_workflow(
        DataProcessingWorkflow.run,
        WorkflowInput(name="test-data", data={"items": [1, 2, 3, 4, 5]}),
        id=f"test-data-processing-1-{timestamp}",
        task_queue=task_queue,
    )
    print(f"  ✅ Started: {handle4.id}")
    
    # Give it a moment to start processing
    await asyncio.sleep(0.5)
    
    # Send a signal to it (might complete too fast)
    try:
        print("  📡 Sending signal to update data...")
        await handle4.signal(DataProcessingWorkflow.update_data, {"new_items": [6, 7, 8]})
        print("  ✅ Signal sent!")
    except Exception as e:
        print(f"  ⚠️  Signal failed (workflow may have completed): {e}")
    
    # Query its status
    try:
        print("  🔍 Querying status...")
        status = await handle4.query(DataProcessingWorkflow.get_status)
        print(f"  📈 Status: {status}")
    except:
        print(f"  ⚠️  Query failed (workflow completed)")
    
    # 4. Start calculator workflows with different operations
    print("\n🧮 Creating calculator workflows...")
    calc_handle1 = await client.start_workflow(
        CalculatorWorkflow.run,
        [{"operation": "add", "a": 10, "b": 5}],
        id=f"test-calculator-add-{timestamp}",
        task_queue=task_queue,
    )
    print(f"  ✅ Started: {calc_handle1.id}")
    
    calc_handle2 = await client.start_workflow(
        CalculatorWorkflow.run,
        [{"operation": "multiply", "a": 7, "b": 8}],
        id=f"test-calculator-multiply-{timestamp}",
        task_queue=task_queue,
    )
    print(f"  ✅ Started: {calc_handle2.id}")
    
    # 5. Create a schedule
    print("\n📅 Creating a scheduled workflow...")
    try:
        await client.create_schedule(
            "test-schedule-daily-greeting",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    GreetingWorkflow.run,
                    {"name": "Scheduled User"},
                    id="scheduled-greeting",
                    task_queue=task_queue,
                ),
                spec=ScheduleSpec(
                    # Run every day at 9 AM
                    cron_expressions=["0 9 * * *"],
                ),
            ),
        )
        print("  ✅ Created schedule: test-schedule-daily-greeting")
    except Exception as e:
        print(f"  ⚠️  Schedule might already exist: {e}")
    
    # 6. Wait for some workflows to complete
    print("\n⏳ Waiting for quick workflows to complete...")
    await asyncio.sleep(3)
    
    try:
        result1 = await handle1.result()
        print(f"  ✅ {handle1.id} completed: {result1}")
    except:
        print(f"  ⏳ {handle1.id} still running...")
    
    try:
        result2 = await handle2.result()
        print(f"  ✅ {handle2.id} completed: {result2}")
    except:
        print(f"  ⏳ {handle2.id} still running...")
    
    try:
        calc_result1 = await calc_handle1.result()
        print(f"  ✅ {calc_handle1.id} completed: {calc_result1}")
    except:
        print(f"  ⏳ {calc_handle1.id} still running...")
    
    try:
        calc_result2 = await calc_handle2.result()
        print(f"  ✅ {calc_handle2.id} completed: {calc_result2}")
    except:
        print(f"  ⏳ {calc_handle2.id} still running...")
    
    # 7. Start one more workflow to cancel
    print("\n❌ Creating workflow to test cancellation...")
    cancel_handle = await client.start_workflow(
        LongRunningWorkflow.run,
        3600,
        id=f"test-to-cancel-{timestamp}",
        task_queue=task_queue,
    )
    print(f"  ✅ Started: {cancel_handle.id} (use this to test cancel/terminate)")
    
    print("\n" + "="*60)
    print("🎉 Test data population complete!")
    print("="*60)
    print("\n📋 Summary of created workflows:")
    print("  • test-greeting-1 (completed)")
    print("  • test-greeting-2 (completed)")
    print("  • test-calculator-add (completed)")
    print("  • test-calculator-multiply (completed)")
    print("  • test-data-processing-1 (running, supports queries/signals)")
    print("  • test-long-running-1 (running)")
    print("  • test-to-cancel (running, for testing cancel/terminate)")
    print("\n📅 Schedules:")
    print("  • test-schedule-daily-greeting")
    print("\n🧪 Now you can test these MCP tools:")
    print("  ✅ list_workflows - See all workflows")
    print("  ✅ describe_workflow - Check workflow details")
    print("  ✅ get_workflow_result - Get completed workflow results")
    print("  ✅ get_workflow_history - View workflow event history")
    print("  ✅ query_workflow - Query test-data-processing-1")
    print("  ✅ signal_workflow - Signal test-data-processing-1")
    print("  ✅ cancel_workflow - Cancel test-to-cancel")
    print("  ✅ terminate_workflow - Terminate test-to-cancel")
    print("  ✅ list_schedules - View schedules")
    print("  ✅ pause_schedule/unpause_schedule - Manage schedule")
    print("  ✅ batch_signal/batch_cancel/batch_terminate - Batch operations")
    print()


if __name__ == "__main__":
    asyncio.run(populate_test_data())
