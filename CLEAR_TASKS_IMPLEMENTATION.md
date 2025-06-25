# Clear All Scheduled Tasks Implementation

## Overview

This implementation provides a comprehensive solution to clear all scheduled tasks in the OPC-UA data ingestion microservice. The functionality covers three types of scheduled tasks:

1. **Scheduler Jobs** - APScheduler jobs managed by the SchedulerService
2. **Polling Tasks** - Periodic polling tasks managed by the PollingService
3. **Subscription Tasks** - OPC-UA subscription tasks managed by the SubscriptionService

## Two Types of Clearing

### 1. Temporary Clear (Deactivate)
- **Endpoint**: `POST /tasks/clear-all`
- **Action**: Deactivates tasks in the database (`is_active = False`)
- **Behavior**: Tasks can be reactivated when new polling requests come in
- **Use Case**: Temporary stopping of tasks

### 2. Permanent Clear (Delete)
- **Endpoint**: `POST /tasks/clear-all-permanent`
- **Action**: Permanently deletes task records from the database
- **Behavior**: Tasks cannot be reactivated - they must be recreated
- **Use Case**: Complete removal of tasks

## Implementation Details

### 1. SchedulerService Enhancement

**File**: `services/scheduler_services.py`

Added method: `clear_all_jobs()`

```python
def clear_all_jobs(self):
    """Clear all jobs from the scheduler
    
    Returns:
        dict: Information about the cleared jobs
    """
```

**Features**:
- Removes all jobs from the APScheduler
- Clears the internal jobs dictionary
- Returns detailed information about cleared jobs
- Handles errors gracefully

### 2. PollingService Enhancement

**File**: `services/polling_services.py`

Added methods:
- `clear_all_polling_tasks()` - Temporary clear (deactivate)
- `clear_all_polling_tasks_permanent()` - Permanent clear (delete)

```python
async def clear_all_polling_tasks(self):
    """Clear all polling tasks from memory and database (deactivate)"""

async def clear_all_polling_tasks_permanent(self):
    """Permanently clear all polling tasks from memory and database (delete records)"""
```

**Features**:
- Removes all polling tasks from the scheduler
- Deactivates/deletes polling tasks in the database
- Clears the internal polling_tasks dictionary
- Handles tasks that exist in scheduler but not in memory
- Returns detailed information about cleared tasks

### 3. SubscriptionService Enhancement

**File**: `services/subscription_services.py`

Added methods:
- `clear_all_subscriptions()` - Temporary clear (deactivate)
- `clear_all_subscriptions_permanent()` - Permanent clear (delete)

```python
async def clear_all_subscriptions(self):
    """Clear all subscription tasks from memory and database (deactivate)"""

async def clear_all_subscriptions_permanent(self):
    """Permanently clear all subscription tasks from memory and database (delete records)"""
```

**Features**:
- Unsubscribes from all OPC-UA nodes
- Deactivates/deletes subscription tasks in the database
- Clears the internal subscription_handles dictionary
- Updates metrics
- Returns detailed information about cleared subscriptions

### 4. MonitoringService Enhancement

**File**: `services/monitoring_services.py`

Added methods:
- `clear_all_scheduled_tasks()` - Temporary clear
- `clear_all_scheduled_tasks_permanent()` - Permanent clear

```python
async def clear_all_scheduled_tasks(self):
    """Clear all scheduled tasks from all services (deactivate)"""

async def clear_all_scheduled_tasks_permanent(self):
    """Permanently clear all scheduled tasks from all services (delete from database)"""
```

**Features**:
- Orchestrates clearing of all three types of tasks
- Provides comprehensive summary and details
- Handles errors from individual services
- Returns structured response with success status

### 5. Database Query Enhancements

**File**: `queries/polling_queries.py`

Added method: `delete_polling_task()`

**File**: `queries/subscription_queries.py`

Added method: `delete_subscription_task()`

### 6. API Endpoints

**File**: `api/endpoints.py`

Added routes:
- `POST /tasks/clear-all` - Temporary clear
- `POST /tasks/clear-all-permanent` - Permanent clear
- `GET /tasks/debug` - Debug endpoint

### 7. Response Schema

**File**: `schemas/schema.py`

Added schema: `ClearTasksResponse`

```python
class ClearTasksResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    summary: dict
    details: dict
```

## API Usage

### Temporary Clear (Deactivate)
```bash
curl -X POST http://localhost:8007/tasks/clear-all
```

### Permanent Clear (Delete) - USE WITH CAUTION
```bash
curl -X POST http://localhost:8007/tasks/clear-all-permanent
```

### Debug Current Tasks
```bash
curl http://localhost:8007/tasks/debug
```

### Response Format
```json
{
    "success": true,
    "message": "Cleared 5 total scheduled tasks",
    "timestamp": "2024-01-01T12:00:00",
    "summary": {
        "total_tasks": 5,
        "scheduler_jobs": 2,
        "polling_tasks": 2,
        "subscription_tasks": 1
    },
    "details": {
        "scheduler": {
            "success": true,
            "message": "Successfully cleared 2 scheduled jobs",
            "cleared_jobs": ["job1", "job2"],
            "job_count": 2
        },
        "polling": {
            "success": true,
            "message": "Successfully cleared 2 polling tasks",
            "cleared_tasks": ["node1", "node2"],
            "task_count": 2
        },
        "subscriptions": {
            "success": true,
            "message": "Successfully cleared 1 subscription tasks",
            "cleared_subscriptions": ["node3"],
            "subscription_count": 1
        }
    }
}
```

## Key Features

### 1. Memory-Scheduler Synchronization
The implementation handles cases where tasks exist in the scheduler but not in memory (common after application restarts):

```python
# Check scheduler for polling jobs that might not be in memory
scheduler_jobs = self.scheduler.get_all_jobs()
polling_job_ids = []

for job_id, job_info in scheduler_jobs.items():
    if job_id.startswith("poll_"):
        polling_job_ids.append(job_id)

# Extract node IDs from job IDs
if polling_job_ids and not node_ids:
    for job_id in polling_job_ids:
        if job_id.startswith("poll_"):
            node_id = job_id[5:]  # Remove "poll_" prefix
            node_ids.append(node_id)
```

### 2. Comprehensive Error Handling
- Individual service errors are handled and reported
- Database operations are wrapped in try-catch blocks
- Network errors (OPC-UA) are handled gracefully
- API errors return appropriate HTTP status codes

### 3. Detailed Logging
- All operations are logged with appropriate levels
- Success/failure messages include task counts
- Error logs include stack traces for debugging

### 4. Database Consistency
- Both temporary (deactivate) and permanent (delete) options
- Handles multiple tag name formats for backward compatibility
- Ensures database state matches memory state

## Error Handling

The implementation includes comprehensive error handling:

1. **Individual Service Errors**: Each service method handles its own errors and returns success/failure status
2. **Database Errors**: Database operations are wrapped in try-catch blocks
3. **Network Errors**: OPC-UA operations handle connection issues
4. **API Errors**: HTTP exceptions are raised with appropriate status codes

## Logging

All operations are logged with appropriate log levels:
- `INFO`: Successful operations
- `WARNING`: Non-critical issues
- `ERROR`: Critical errors with stack traces

## Security Considerations

- **Temporary Clear**: Safe for normal operations
- **Permanent Clear**: Destructive operation - use with caution
- No authentication/authorization implemented (should be added based on requirements)
- Consider adding confirmation mechanisms for permanent clear

## Future Enhancements

1. **Selective Clearing**: Add options to clear specific types of tasks
2. **Confirmation**: Add confirmation step before permanent clear
3. **Authentication**: Add proper authentication/authorization
4. **Audit Trail**: Log who cleared tasks and when
5. **Dry Run**: Add option to preview what would be cleared
6. **Recovery**: Add ability to restore cleared tasks from backup
7. **Scheduled Clearing**: Add ability to schedule task clearing

## Dependencies

The implementation uses existing dependencies:
- FastAPI for the API endpoints
- Pydantic for response validation
- APScheduler for job management
- SQLAlchemy for database operations
- AsyncIO for asynchronous operations 