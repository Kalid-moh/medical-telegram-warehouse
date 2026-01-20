from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date

# Endpoint 1: Top Products
class ProductMention(BaseModel):
    term: str
    mention_count: int
    
    model_config = ConfigDict(from_attributes=True)

# Endpoint 2: Channel Activity
class ChannelActivity(BaseModel):
    day: date
    post_count: int
    daily_views: int
    
    model_config = ConfigDict(from_attributes=True)

# Endpoint 3: Message Search
class MessageSearch(BaseModel):
    message_id: int
    date: date
    message_text: Optional[str] = None
    view_count: int
    
    model_config = ConfigDict(from_attributes=True)

# Endpoint 4: Visual Stats
class VisualStat(BaseModel):
    channel_name: str
    total_images: int
    primary_category: Optional[str] = "Unknown"
    avg_confidence: float
    
    model_config = ConfigDict(from_attributes=True)