"""
Subscription Queries

This module provides database queries related to subscription tasks.
"""

from database import async_session
from sqlalchemy import select, update, delete
from models.models import Tag, subscription_tasks
from datetime import datetime
from utils.log import setup_logger

logger = setup_logger(__name__)

async def save_subscription_task(node_id):
    """Save a subscription task to the database
    
    Args:
        node_id (str): The node ID
        
    Returns:
        int: The subscription task ID
    """
    try: 
        # Get tag_id
        tag_id = await get_or_create_tag_id(node_id)
        
        if not tag_id:
            logger.error(f"Could not get or create tag for node {node_id}")
            return None
        
        async with async_session() as session:
            # Check if task already exists
            result = await session.execute(
                select(subscription_tasks).where(
                    (subscription_tasks.tag_id == tag_id)
                )
            )
            existing_task = result.scalars().first()
            
            if existing_task:
                # Update existing task
                existing_task.is_active = True
                existing_task.last_updated = datetime.now()
                await session.commit()
                logger.info(f"Updated subscription task for node {node_id}")
                return existing_task.id
            else:
                # Create new task
                new_task = subscription_tasks(
                    tag_id=tag_id,
                    is_active=True,
                    created_at=datetime.now(),
                    last_updated=datetime.now()
                )
                session.add(new_task)
                await session.commit()
                await session.refresh(new_task)
                logger.info(f"Created subscription task for node {node_id}")
                return new_task.id
    except Exception as e:
        logger.error(f"Error saving subscription task for node {node_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def deactivate_subscription_task(node_id):
    """Deactivate a subscription task in the database
    
    Args:
        node_id (str): The node ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Use node_id directly as tag_name without parsing
        tag_name = node_id
        
        # Also try to get results using any extracted tag name (for backward compatibility)
        alternate_tag_names = []
        
        # Extract tag name from node_id if it has a specific format
        parts = node_id.split(';')
        if len(parts) > 1:
            try:
                extracted_tag = parts[1].split('=')[1]
                if extracted_tag != tag_name:
                    alternate_tag_names.append(extracted_tag)
            except (IndexError, ValueError):
                # If parsing fails, just continue with the original tag_name
                pass
                
        # Log what we're trying to deactivate
        logger.info(f"Attempting to deactivate subscription for node {node_id} (tag names: {[tag_name] + alternate_tag_names})")
            
        # Get tag_ids for all possible tag names
        tag_ids = []
        primary_tag_id = await get_or_create_tag_id(tag_name)
        if primary_tag_id:
            tag_ids.append(primary_tag_id)
            
        for alt_tag in alternate_tag_names:
            alt_tag_id = await get_or_create_tag_id(alt_tag)
            if alt_tag_id and alt_tag_id not in tag_ids:
                tag_ids.append(alt_tag_id)
                
        if not tag_ids:
            logger.warning(f"No tags found for node {node_id}")
            return False
            
        # Use all possible tag IDs to ensure we find and deactivate the task
        success = False
        async with async_session() as session:
            for tag_id in tag_ids:
                # Deactivate subscription for this tag
                query = (
                    update(subscription_tasks)
                    .where(subscription_tasks.tag_id == tag_id)
                    .values(is_active=False, last_updated=datetime.now())
                )
                
                result = await session.execute(query)
                await session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Deactivated {result.rowcount} subscription task(s) for tag_id {tag_id}")
                    success = True
            
        if success:
            return True
        else:
            logger.warning(f"No subscription tasks found for node {node_id} with any of the tag IDs: {tag_ids}")
            return False
    except Exception as e:
        logger.error(f"Error deactivating subscription task for node {node_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def get_active_subscription_tasks():
    """Get all active subscription tasks from the database
    
    Returns:
        list: List of active subscription tasks with tag information
    """
    try:
        async with async_session() as session:
            # Join subscription_tasks with Tag to get tag name
            query = select(subscription_tasks, Tag.name.label("tag_name")).join(
                Tag, subscription_tasks.tag_id == Tag.id
            ).where(subscription_tasks.is_active == True)
            
            result = await session.execute(query)
            tasks = result.all()
            
            # Convert to list of dictionaries
            task_list = []
            for task, tag_name in tasks:
                task_dict = {
                    "id": task.id,
                    "tag_id": task.tag_id,
                    "tag_name": tag_name,
                    "created_at": task.created_at,
                    "last_updated": task.last_updated
                }
                task_list.append(task_dict)
            
            return task_list
    except Exception as e:
        logger.error(f"Error getting active subscription tasks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

async def get_or_create_tag_id(node_id):
    """Get tag ID by name or create a new tag if it doesn't exist
    
    Args:
        node_id (str): The OPC-UA node ID used as tag name
        
    Returns:
        int: The tag ID
    """
    async with async_session() as session:
        # First check if the tag already exists in the database
        result = await session.execute(select(Tag).where(Tag.name == node_id))
        tag = result.scalars().first()
        
        if tag:
            return tag.id
        
        # Check if the node exists in the OPC UA server
        from services.opc_ua_services import get_opc_ua_client
        opc_client = get_opc_ua_client()
        node_exists = False
        
        try:
            if opc_client.connected:
                # Try to get the node from the server
                node = opc_client.client.get_node(node_id)
                # Try to read a property to verify the node exists
                await node.read_browse_name()
                node_exists = True
                logger.info(f"Verified node {node_id} exists in OPC UA server")
            else:
                logger.warning(f"OPC UA client not connected, cannot verify node {node_id}")
                # Proceed anyway since we can't verify
                node_exists = True
        except Exception as e:
            logger.warning(f"Node {node_id} not found in OPC UA server or error accessing it: {e}")
            # We'll still create the tag, but log the warning
        
        if node_exists:
            # Create new tag if it doesn't exist in the database
            new_tag = Tag(
                name=node_id,
                description=f"Auto-created tag for {node_id}",
                unit_of_measure="unknown"
            )
        
            session.add(new_tag)
            await session.commit()
            await session.refresh(new_tag)
        
            logger.info(f"Created new tag with ID {new_tag.id} for node {node_id}")
            return new_tag.id
        else:
            logger.warning(f"Node {node_id} does not exist in OPC UA server, cannot create tag")
            return None

async def delete_subscription_task(node_id):
    """Permanently delete a subscription task from the database
    
    Args:
        node_id (str): The node ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Use node_id directly as tag_name without parsing
        tag_name = node_id
        
        # Also try to get results using any extracted tag name (for backward compatibility)
        alternate_tag_names = []
        
        # Extract tag name from node_id if it has a specific format
        parts = node_id.split(';')
        if len(parts) > 1:
            try:
                extracted_tag = parts[1].split('=')[1]
                if extracted_tag != tag_name:
                    alternate_tag_names.append(extracted_tag)
            except (IndexError, ValueError):
                # If parsing fails, just continue with the original tag_name
                pass
                
        # Log what we're trying to delete
        logger.info(f"Attempting to delete subscription task for node {node_id} (tag names: {[tag_name] + alternate_tag_names})")
            
        # Get tag_ids for all possible tag names
        tag_ids = []
        primary_tag_id = await get_or_create_tag_id(tag_name)
        if primary_tag_id:
            tag_ids.append(primary_tag_id)
            
        for alt_tag in alternate_tag_names:
            alt_tag_id = await get_or_create_tag_id(alt_tag)
            if alt_tag_id and alt_tag_id not in tag_ids:
                tag_ids.append(alt_tag_id)
                
        if not tag_ids:
            logger.warning(f"No tags found for node {node_id}")
            return False
            
        # Use all possible tag IDs to ensure we find and delete the task
        success = False
        async with async_session() as session:
            for tag_id in tag_ids:
                # Delete subscription for this tag
                query = (
                    delete(subscription_tasks)
                    .where(subscription_tasks.tag_id == tag_id)
                )
                
                result = await session.execute(query)
                await session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Deleted {result.rowcount} subscription task(s) for tag_id {tag_id}")
                    success = True
            
        if success:
            return True
        else:
            logger.warning(f"No subscription tasks found for node {node_id} with any of the tag IDs: {tag_ids}")
            return False
    except Exception as e:
        logger.error(f"Error deleting subscription task for node {node_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False 