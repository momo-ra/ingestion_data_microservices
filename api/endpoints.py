from fastapi import APIRouter, HTTPException, Path
from services.opc_ua_services import get_opc_ua_client
from services.polling_services import get_polling_service
from services.subscription_services import get_subscription_service
from utils.log import setup_logger
from utils.metrics import get_metrics
from queries.polling_queries import get_active_polling_tasks
from queries.timeseries_queries import get_latest_node_data, get_node_data_history, get_node_data_statistics
from services.monitoring_services import MonitoringService
from datetime import datetime, timedelta
import time
from queries.subscription_queries import get_active_subscription_tasks
from schemas.schema import NodeRequest, PollingRequest, TimeRangeRequest, PollingResponse, ClearTasksResponse

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/")
async def root():
    return {"message": "OPC-UA API is running"}

@router.post("/node/value")
async def get_node_value(request: NodeRequest):
    """Get the current value of a specific OPC-UA node"""
    try:
        client = get_opc_ua_client()
        node_data = await client.get_value_of_specific_node(request.node_id)
        
        if node_data:
            return node_data
        else:
            raise HTTPException(status_code=404, detail=f"Failed to get value for node {request.node_id}")
    except Exception as e:
        logger.error(f"Error getting node value: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/node/subscribe")
async def subscribe_to_node(request: NodeRequest):
    """Subscribe to data changes for a specific OPC-UA node"""
    try:
        subscription_service = get_subscription_service()
        handle = await subscription_service.create_subscription(request.node_id)
        
        if handle:
            return {"success": True, "message": f"Subscribed to node {request.node_id}", "handle": str(handle)}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to subscribe to node {request.node_id}")
    except Exception as e:
        logger.error(f"Error subscribing to node: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/node/unsubscribe")
async def unsubscribe_from_node(request: NodeRequest):
    """Unsubscribe from data changes for a specific OPC-UA node"""
    try:
        subscription_service = get_subscription_service()
        success = await subscription_service.remove_subscription(request.node_id)
        
        if success:
            return {"success": True, "message": f"Unsubscribed from node {request.node_id}"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to unsubscribe from node {request.node_id}")
    except Exception as e:
        logger.error(f"Error unsubscribing from node: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/node/poll/start")
async def start_polling_node(request: PollingRequest):
    """Start polling a specific OPC-UA node at regular intervals"""
    try:
        polling_service = get_polling_service()
        success = await polling_service.add_polling_node(request.node_id, request.interval_seconds)
        
        if success:
            return PollingResponse(
                success=True,
                message=f"Started polling node {request.node_id} every {request.interval_seconds} seconds",
                node_id=request.node_id,
                interval_seconds=request.interval_seconds
            )
        else:
            raise HTTPException(status_code=500, detail=f"Failed to start polling node {request.node_id}")
    except Exception as e:
        logger.error(f"Error starting polling: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/node/poll/stop")
async def stop_polling_node(request: NodeRequest):
    """Stop polling a specific OPC-UA node"""
    try:
        polling_service = get_polling_service()
        success = await polling_service.remove_polling_node(request.node_id)
        
        if success:
            return PollingResponse(
                success=True,
                message=f"Stopped polling node {request.node_id}",
                node_id=request.node_id
            )
        else:
            raise HTTPException(status_code=404, detail=f"Polling task for node {request.node_id} not found")
    except Exception as e:
        logger.error(f"Error stopping polling: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/node/poll/active")
async def get_active_polling_nodes():
    """Get all active polling nodes"""
    try:
        tasks = await get_active_polling_tasks()
        return {"active_polling_tasks": tasks}
    except Exception as e:
        logger.error(f"Error getting active polling nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/node/subscribe/active")
async def get_active_subscriptions():
    """Get all active subscriptions"""
    try:
        tasks = await get_active_subscription_tasks()
        return {"active_subscriptions": tasks}
    except Exception as e:
        logger.error(f"Error getting active subscriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/node/subscribe/count")
async def get_subscription_count():
    """Get the count of active subscriptions in memory and database"""
    try:
        # Get count from service instance
        subscription_service = get_subscription_service()
        memory_count = len(subscription_service.subscription_handles)
        
        # Get count from database
        db_tasks = await get_active_subscription_tasks()
        db_count = len(db_tasks)
        
        return {
            "memory_count": memory_count,
            "database_count": db_count,
            "subscription_handles": list(subscription_service.subscription_handles.keys())
        }
    except Exception as e:
        logger.error(f"Error getting subscription count: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
    


@router.post("/data/latest")
async def get_latest_data(request: NodeRequest):
    """Get the latest data for a specific node"""
    try:
        data = await get_latest_node_data(request.node_id)
        if data:
            return data
        else:
            raise HTTPException(status_code=404, detail=f"No data found for node {request.node_id}")
    except Exception as e:
        logger.error(f"Error getting latest data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/data/history")
async def get_data_history(request: TimeRangeRequest):
    """Get historical data for a specific node"""
    try:
        data = await get_node_data_history(
            request.node_id,
            start_time=request.start_time,
            end_time=request.end_time,
            limit=request.limit or 100
        )
        return {"node_id": request.node_id, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Error getting data history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/data/statistics")
async def get_data_statistics(request: TimeRangeRequest):
    """Get statistics for a specific node's data"""
    try:
        stats = await get_node_data_statistics(
            request.node_id,
            start_time=request.start_time,
            end_time=request.end_time
        )
        return stats
    except Exception as e:
        logger.error(f"Error getting data statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/recent/{hours}")
async def get_recent_data(hours: int = Path(..., ge=1, le=24)):
    """Get recent data for all active polling nodes"""
    try:
        # Get all active polling tasks
        tasks = await get_active_polling_tasks()
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Get data for each node
        results = []
        for task in tasks:
            try:
                # Convert tag_name to node_id
                node_id = f"ns=2;s={task['tag_name']}"
                
                # Get data history
                data = await get_node_data_history(
                    node_id,
                    start_time=start_time,
                    end_time=end_time,
                    limit=100
                )
                
                # Get statistics
                stats = await get_node_data_statistics(
                    node_id,
                    start_time=start_time,
                    end_time=end_time
                )
                
                results.append({
                    "node_id": node_id,
                    "tag_name": task["tag_name"],
                    "interval_seconds": task["interval_seconds"],
                    "data_count": len(data),
                    "statistics": stats,
                    "latest_data": data[0] if data else None
                })
            except Exception as node_error:
                logger.error(f"Error getting data for node {task['tag_name']}: {node_error}")
                results.append({
                    "node_id": f"ns=2;s={task['tag_name']}",
                    "tag_name": task["tag_name"],
                    "error": str(node_error)
                })
        
        return {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            },
            "nodes": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error getting recent data: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/metrics")
async def metrics():
    """Get all metrics in JSON format"""
    return get_metrics()

@router.get("/metrics/prometheus")
async def prometheus_metrics():
    """Get metrics in Prometheus format"""
    from fastapi.responses import PlainTextResponse
    metrics_data = get_metrics()
    
    # Convert to Prometheus format
    lines = []
    for metric in metrics_data["metrics"]:
        # Add metric metadata
        lines.append(f"# HELP {metric['name']} {metric['description']}")
        lines.append(f"# TYPE {metric['name']} {metric['type']}")
        
        # Add metric values based on type
        if metric['type'] == 'counter' or metric['type'] == 'gauge':
            for value_entry in metric.get('values', []):
                if 'labels' in value_entry:
                    label_str = ','.join([f'{k}="{v}"' for k, v in value_entry['labels'].items()])
                    lines.append(f"{metric['name']}{{{label_str}}} {value_entry['value']}")
                else:
                    lines.append(f"{metric['name']} {value_entry['value']}")
                    
        elif metric['type'] == 'histogram':
            for value_entry in metric.get('values', []):
                # Extract labels
                if 'labels' in value_entry:
                    label_str = ','.join([f'{k}="{v}"' for k, v in value_entry['labels'].items()])
                    label_part = f"{{{label_str}}}"
                else:
                    label_part = ""
                
                # Add sum and count
                lines.append(f"{metric['name']}_sum{label_part} {value_entry['sum']}")
                lines.append(f"{metric['name']}_count{label_part} {value_entry['count']}")
                
                # Add buckets
                for bucket in value_entry['buckets']:
                    # Add le label to existing labels
                    if 'labels' in value_entry:
                        bucket_label_str = ','.join([f'{k}="{v}"' for k, v in value_entry['labels'].items()])
                        bucket_label_str += f',le="{bucket["le"]}"'
                    else:
                        bucket_label_str = f'le="{bucket["le"]}"'
                    
                    lines.append(f"{metric['name']}_bucket{{{bucket_label_str}}} {bucket['count']}")
    
    return PlainTextResponse("\n".join(lines))

@router.post("/connection/check")
async def check_connection():
    """Check the connection to the OPC-UA server"""
    try:
        client = get_opc_ua_client()
        if client.connected:
            return {"connected": True, "message": "Connected to OPC-UA server"}
        else:
            # Try to connect
            success = await client.connect()
            if success:
                return {"connected": True, "message": "Successfully connected to OPC-UA server"}
            else:
                return {"connected": False, "message": "Failed to connect to OPC-UA server"}
    except Exception as e:
        logger.error(f"Error checking connection: {e}")
        return {"connected": False, "message": f"Error checking connection: {str(e)}"}

@router.get("/health")
async def get_health():
    """Get the health status of the system"""
    try:
        monitoring_service = MonitoringService.get_instance()
        health_status = monitoring_service.get_health_status()
        return health_status
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        return {
            "status": "error",
            "message": f"Error getting health status: {str(e)}"
        }

@router.get("/health/detailed")
async def get_detailed_health():
    """Get detailed health status of all components"""
    try:
        monitoring_service = MonitoringService.get_instance()
        health_status = await monitoring_service.get_detailed_health()
        return health_status
    except Exception as e:
        logger.error(f"Error getting detailed health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/clear-all", response_model=ClearTasksResponse)
async def clear_all_scheduled_tasks():
    """Clear all scheduled tasks (scheduler jobs, polling tasks, and subscriptions)"""
    try:
        monitoring_service = MonitoringService.get_instance()
        result = await monitoring_service.clear_all_scheduled_tasks()
        
        if result.get("success", False):
            return ClearTasksResponse(**result)
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to clear scheduled tasks"))
    except Exception as e:
        logger.error(f"Error clearing all scheduled tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/clear-all-permanent", response_model=ClearTasksResponse)
async def clear_all_scheduled_tasks_permanent():
    """Permanently clear all scheduled tasks (delete from database) - USE WITH CAUTION"""
    try:
        monitoring_service = MonitoringService.get_instance()
        result = await monitoring_service.clear_all_scheduled_tasks_permanent()
        
        if result.get("success", False):
            return ClearTasksResponse(**result)
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to permanently clear scheduled tasks"))
    except Exception as e:
        logger.error(f"Error permanently clearing all scheduled tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/debug")
async def debug_tasks():
    """Debug endpoint to check what tasks are currently running"""
    try:
        from services.scheduler_services import SchedulerService
        from services.polling_services import get_polling_service
        from services.subscription_services import get_subscription_service
        
        scheduler = SchedulerService.get_instance()
        polling_service = get_polling_service()
        subscription_service = get_subscription_service()
        
        # Get scheduler jobs
        scheduler_jobs = scheduler.get_all_jobs()
        
        # Get polling tasks from memory
        polling_tasks = polling_service.polling_tasks
        
        # Get subscription handles
        subscription_handles = subscription_service.subscription_handles
        
        # Get active tasks from database
        db_polling_tasks = await get_active_polling_tasks()
        db_subscription_tasks = await get_active_subscription_tasks()
        
        return {
            "scheduler_jobs": {
                "count": len(scheduler_jobs),
                "jobs": list(scheduler_jobs.keys())
            },
            "polling_tasks_memory": {
                "count": len(polling_tasks),
                "tasks": list(polling_tasks.keys())
            },
            "subscription_handles_memory": {
                "count": len(subscription_handles),
                "handles": list(subscription_handles.keys())
            },
            "db_polling_tasks": {
                "count": len(db_polling_tasks),
                "tasks": [task["tag_name"] for task in db_polling_tasks]
            },
            "db_subscription_tasks": {
                "count": len(db_subscription_tasks),
                "tasks": [task["tag_name"] for task in db_subscription_tasks]
            }
        }
    except Exception as e:
        logger.error(f"Error in debug tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
