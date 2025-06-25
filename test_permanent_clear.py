#!/usr/bin/env python3
"""
Test script to verify the permanent clear functionality
"""

import asyncio
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_permanent_clear():
    """Test the permanent clear functionality"""
    print("Testing permanent clear functionality...")
    
    try:
        from services.scheduler_services import SchedulerService
        
        # Get the scheduler service
        scheduler = SchedulerService.get_instance()
        
        # Check if jobs.sqlite exists and has jobs
        if os.path.exists('jobs.sqlite'):
            print("✅ jobs.sqlite file exists")
            
            # Check jobs in the file
            import sqlite3
            conn = sqlite3.connect('jobs.sqlite')
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM apscheduler_jobs")
            jobs = cursor.fetchall()
            conn.close()
            
            print(f"📋 Found {len(jobs)} jobs in APScheduler database:")
            for job in jobs:
                print(f"   - {job[0]}")
        else:
            print("❌ jobs.sqlite file does not exist")
        
        # Test the permanent clear
        print("\n🧹 Testing permanent clear...")
        result = scheduler.clear_all_jobs_permanent()
        
        print("Clear result:")
        print(f"Success: {result.get('success')}")
        print(f"Message: {result.get('message')}")
        print(f"Job count: {result.get('job_count', 0)}")
        print(f"Cleared jobs: {result.get('cleared_jobs', [])}")
        
        # Check if jobs.sqlite still exists
        if os.path.exists('jobs.sqlite'):
            print("\n📋 Checking jobs.sqlite after clear...")
            conn = sqlite3.connect('jobs.sqlite')
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM apscheduler_jobs")
            jobs = cursor.fetchall()
            conn.close()
            
            print(f"Found {len(jobs)} jobs after clear:")
            for job in jobs:
                print(f"   - {job[0]}")
        else:
            print("\n✅ jobs.sqlite file was removed successfully!")
        
        print("\nTest completed!")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_permanent_clear()) 