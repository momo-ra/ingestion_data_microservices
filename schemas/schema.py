from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, TypeVar, Generic

T = TypeVar('T')

# General Class for Response
class ResponseModel(BaseModel, Generic[T]):
    """Base model for standardized API responses"""
    status: str = Field(..., description="Status of Response(success/fail)")
    data: Optional[T] = Field(None, description="Data should be return")
    message: Optional[str] = Field(None, description="Error message when fail happened")

class TagSchema(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., example="Tag Name")
    description: Optional[str] = Field(None, example="Tag Description")
    unit_of_measure: Optional[str] = Field(None, example="Tag Unit")
    
class TimeSeriesSchema(BaseModel):
    id: Optional[int] = None
    tag_id: int = Field(..., example="Tag ID")
    timestamp: datetime = Field(..., example="2023-03-10T12:00:00")
    value: str = Field(..., example="Tag Value")

class KafkaMessageSchema(BaseModel):
    tag_name: str = Field(..., example="Tag Name")
    tag_id: int = Field(..., example="Tag ID")
    value: str = Field(..., example="Tag Value")
    unit_of_measure: str = Field(..., example="Tag Unit")
    description: str = Field(..., example="Tag Description")
    timestamp: datetime = Field(..., example="2023-03-10T12:00:00")

#Request Schema
class NodeRequest(BaseModel):
    node_id: str
    
class PollingRequest(BaseModel):
    node_id: str
    interval_seconds: int = 60

class PollingResponse(BaseModel):
    success: bool
    message: str
    node_id: str
    interval_seconds: Optional[int] = None

class TimeRangeRequest(BaseModel):
    node_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: Optional[int] = 100

class ClearTasksResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    summary: dict
    details: dict

    
    