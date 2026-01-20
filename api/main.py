from fastapi import FastAPI, Depends, Request, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import logging
import time
import os

# Import local modules
from . import schemas, database
from .database import get_db

# --- DIRECTORY SETUP ---
if not os.path.exists("logs"):
    os.makedirs("logs")

# --- STRUCTURED LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/api_access.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MedicalAPI")

# --- API METADATA FOR DOCUMENTATION ---
tags_metadata = [
    {"name": "General", "description": "Root and health check operations."},
    {"name": "Reports", "description": "Analytical data regarding products and visual detections."},
    {"name": "Channels", "description": "Performance and activity metrics for specific Telegram channels."},
    {"name": "Search", "description": "Keyword-based message retrieval."},
]

app = FastAPI(
    title="Pharmaceutical Sales & Visual Analytics API",
    description="""
    An analytical API designed to monitor medical product mentions and image detection results from Telegram channels.
    
    ## Features
    * **Analytics**: Get top products and visual detection stats.
    * **Monitoring**: Track channel posting activity over time.
    * **Search**: Look up specific drugs or medical terms in historical messages.
    """,
    version="1.0.0",
    openapi_tags=tags_metadata
)

# --- LOGGING MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    log_message = f"Method: {request.method} Path: {request.url.path} Status: {response.status_code} Duration: {process_time:.2f}s"
    logger.info(log_message)
    return response

# --- ENDPOINTS ---

@app.get("/", tags=["General"], summary="Welcome Root")
def read_root():
    """Returns a simple welcome message to verify the API is running."""
    return {"message": "Welcome to the Medical Analytical API. Access /docs for full documentation."}


@app.get(
    "/api/reports/top-products", 
    response_model=List[schemas.ProductMention], 
    tags=["Reports"],
    summary="Get Top Trending Products"
)
def get_top_products(
    limit: int = Query(10, gt=0, le=100, description="The number of top products to retrieve."), 
    db: Session = Depends(get_db)
):
    """
    Returns the most frequently mentioned terms/products across all channels.
    Groups results by message text and sorts by count.
    """
    logger.info(f"Generating Top Products report (limit={limit})")
    sql = text("""
        SELECT message_text AS term, COUNT(*) AS mention_count
        FROM "raw".fct_messages
        WHERE message_text IS NOT NULL
        GROUP BY message_text
        ORDER BY mention_count DESC
        LIMIT :limit
    """)
    result = db.execute(sql, {"limit": limit}).mappings().all()
    if not result:
        raise HTTPException(status_code=404, detail="No product data found.")
    return result


@app.get(
    "/api/channels/{channel_name}/activity", 
    response_model=List[schemas.ChannelActivity], 
    tags=["Channels"],
    summary="Channel Activity Trends"
)
def get_channel_activity(
    channel_name: str = Path(..., description="The name of the channel to analyze."),
    db: Session = Depends(get_db)
):
    """
    Returns daily posting activity and view trends for a specific channel.
    Converts integer date keys into standard date formats.
    """
    logger.info(f"Retrieving activity for channel: {channel_name}")
    sql = text("""
        SELECT 
            TO_DATE(m.date_key::TEXT, 'YYYYMMDD') AS day, 
            COUNT(m.message_id) AS post_count,
            COALESCE(SUM(m.view_count), 0) AS daily_views
        FROM "raw".fct_messages m
        JOIN "raw".dim_channels c ON m.channel_key = c.channel_key
        WHERE c.channel_name = :channel_name
        GROUP BY day
        ORDER BY day DESC
    """)
    result = db.execute(sql, {"channel_name": channel_name}).mappings().all()
    if not result:
        raise HTTPException(status_code=404, detail=f"No activity found for channel: {channel_name}")
    return result


@app.get(
    "/api/search/messages", 
    response_model=List[schemas.MessageSearch], 
    tags=["Search"],
    summary="Keyword Search"
)
def search_messages(
    query: str = Query(..., min_length=3, description="The keyword or drug name to search for."),
    limit: int = Query(20, ge=1, le=100, description="Max results to return."),
    db: Session = Depends(get_db)
):
    """
    Searches for messages containing a specific keyword (case-insensitive).
    """
    logger.info(f"Searching messages for keyword: {query}")
    sql = text("""
        SELECT 
            message_id,
            TO_DATE(date_key::TEXT, 'YYYYMMDD') AS date,
            message_text,
            COALESCE(view_count, 0) AS view_count
        FROM "raw".fct_messages
        WHERE message_text ILIKE :search_term
        ORDER BY date_key DESC
        LIMIT :limit
    """)
    return db.execute(sql, {"search_term": f"%{query}%", "limit": limit}).mappings().all()


@app.get(
    "/api/reports/visual-content", 
    response_model=List[schemas.VisualStat], 
    tags=["Reports"],
    summary="YOLO Detection Statistics"
)
def get_visual_stats(db: Session = Depends(get_db)):
    """
    Returns statistics about image usage and YOLOv8 detection categories across channels.
    Includes the most frequent object detected and average confidence scores.
    """
    logger.info("Generating Visual Content Statistics report")
    sql = text("""
        SELECT 
            c.channel_name,
            COUNT(i.message_id) AS total_images,
            MODE() WITHIN GROUP (ORDER BY i.detected_class) AS primary_category,
            ROUND(AVG(i.confidence_score)::numeric, 2) AS avg_confidence
        FROM "raw".fct_image_detections i
        JOIN "raw".dim_channels c ON i.channel_key = c.channel_key
        GROUP BY c.channel_name
        ORDER BY total_images DESC
    """)
    try:
        return db.execute(sql).mappings().all()
    except Exception as e:
        logger.error(f"Error retrieving visual stats: {e}")
        raise HTTPException(status_code=500, detail="Visual detection data is currently unavailable.")