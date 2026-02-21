import logging
from fastapi import APIRouter, HTTPException, Request
from location_analyzer.api.schemas import PredictRequest, PredictResponse
from location_analyzer.pipeline.inference_pipeline import InferencePipeline

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/predict", response_model=PredictResponse)
async def predict_sales(request_body: PredictRequest, request: Request):
    """
    Endpoint to trigger the live scraping sequence and return an XGBoost prediction.
    """
    model_service = request.app.state.model_service
    if not model_service:
        raise HTTPException(status_code=500, detail="PredictionService is offline. ML artifacts could not be loaded on startup.")
        
    postcode = request_body.postcode.upper().strip()
    logger.info(f"Received Prediction Request for: {postcode}")
    
    try:
        # Step 1: Run the scrapers natively in the inference pipeline
        # Todo: Using run_in_threadpool if latency causes async blocking
        pipeline = InferencePipeline()
        features = pipeline.run(postcode)
        
        if not features:
            raise HTTPException(status_code=404, detail=f"Could not extract any data for postcode: {postcode}")
            
        # Optional: Add the requested branch_name
        if request_body.branch_name:
            features['Branch Name'] = request_body.branch_name
            
        # Step 2: Feed the unstructured Scraper data into the ML Model Feature Engineering pipeline
        # predict() expects a List of Dictionaries (oriented records)
        predictions = model_service.predict([features])
        predicted_sales = predictions[0]
        
        return PredictResponse(
            postcode=postcode,
            predicted_sales=round(predicted_sales, 2),
            features=features
        )
        
    except Exception as e:
        logger.error(f"Inference pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
