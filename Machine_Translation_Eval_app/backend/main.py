from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import shutil
import pandas as pd
from typing import List, Dict, Optional
from config import get_models
from utils import get_hardware_info, estimate_time
from pydantic import BaseModel
from evaluator import evaluator
import asyncio
from huggingface_hub import login

app = FastAPI(title="MT Evaluation App")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

manager = ConnectionManager()

class TimeEstimateRequest(BaseModel):
    rows: int
    models: List[str]

class EvaluateRequest(BaseModel):
    filename: str
    src_col: str
    tgt_cols: List[str]
    models: List[str]
    ref_col: Optional[str] = None # Optional reference column
    client_id: Optional[str] = None # Optional for backward compatibility, but needed for progress

@app.get("/")
def read_root():
    return {"message": "MT Evaluation Backend is running"}

class TokenVerificationRequest(BaseModel):
    token: str

@app.post("/verify_token")
def verify_token(request: TokenVerificationRequest):
    try:
        login(token=request.token)
        return {"status": "success", "message": "Token verified and login successful"}
    except Exception as e:
        logging.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=400, detail=f"Token verification failed: {str(e)}")


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# Configure logging
import logging
logging.basicConfig(filename='backend_debug.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    logging.info(f"Received upload request for file: {file.filename}")
    if not file.filename.endswith('.xlsx'):
        logging.error("Invalid file type")
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an .xlsx file.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    logging.info(f"Saving file to {file_path}")
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logging.info("File saved successfully")
    except Exception as e:
        logging.error(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")
    
    # Validate and parse columns
    try:
        logging.info("Reading excel file for columns")
        # Check encoding by reading headers. Excel files usually handle encoding well, 
        # but we'll ensure we can read it.
        df = pd.read_excel(file_path, nrows=0) 
        columns = df.columns.tolist()
        logging.info(f"Columns found: {columns}")
        
        # Basic check for empty columns or weird characters could go here
        
        logging.info("Reading excel file for total rows")
        total_rows = pd.read_excel(file_path).shape[0]
        logging.info(f"Total rows: {total_rows}")
        
        response = {"filename": file.filename, "columns": columns, "total_rows": total_rows}
        logging.info(f"Sending response: {response}")
        return response
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

@app.get("/models")
def list_models():
    return get_models()

@app.post("/estimate_time")
def get_time_estimate(request: TimeEstimateRequest):
    hardware = get_hardware_info()
    seconds = estimate_time(request.rows, len(request.models), hardware)
    return {"estimated_seconds": seconds, "hardware": hardware}

@app.post("/evaluate")
async def evaluate(request: EvaluateRequest):
    file_path = os.path.join(UPLOAD_DIR, request.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Define progress callback
    def progress_callback(message: str):
        if request.client_id:
            asyncio.run(manager.send_message(message, request.client_id))

    try:
        df = pd.read_excel(file_path)
        
        # Run evaluation in a threadpool to avoid blocking the event loop
        # We need to wrap the call to handle the async callback if possible, 
        # but asyncio.run inside a thread is tricky. 
        # Actually, since we are in async def evaluate, we can run synchronous code in threadpool.
        # But the callback needs to be async to send websocket message?
        # No, manager.send_message is async.
        # So we need a sync wrapper for the callback that schedules the async task?
        # Or just use run_in_executor.
        
        # Simplified approach:
        # The evaluator is synchronous. The callback is synchronous.
        # Inside the callback, we need to send a message to the websocket.
        # Since we are in a separate thread (if using run_in_executor), we can't easily access the main event loop.
        
        # Alternative: Make evaluate async? No, evaluator uses heavy CPU/GPU, should be blocking or in thread.
        # Let's use a queue or just run it directly if we don't mind blocking for a bit between updates?
        # No, blocking the loop is bad.
        
        # Better: Use a sync callback that puts messages into a queue, and a background task that sends them?
        # Or just use `asyncio.run_coroutine_threadsafe` if we have the loop.
        
        loop = asyncio.get_event_loop()
        
        def sync_progress_callback(message: str):
            if request.client_id:
                asyncio.run_coroutine_threadsafe(manager.send_message(message, request.client_id), loop)

        # Run evaluator in threadpool
        results_df = await asyncio.to_thread(
            evaluator.evaluate, 
            df, 
            request.src_col, 
            request.tgt_cols, 
            request.models, 
            request.ref_col,
            sync_progress_callback
        )
        
        # Filter results to keep only selected columns and scores
        # Order: Source, Reference (if exists), Targets, Scores
        cols_to_keep = [request.src_col]
        
        if request.ref_col:
            cols_to_keep.append(request.ref_col)
            
        cols_to_keep.extend(request.tgt_cols)
            
        # Add score columns (columns that are in results_df but not in original df)
        original_cols = df.columns.tolist()
        new_cols = [c for c in results_df.columns if c not in original_cols]
        cols_to_keep.extend(new_cols)
        
        # Create filtered dataframe
        final_df = results_df[cols_to_keep]
        
        # Save results
        output_filename = f"results_{request.filename}"
        output_path = os.path.join(UPLOAD_DIR, output_filename)
        final_df.to_excel(output_path, index=False)
        
        return results_df.to_dict(orient="records")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

from fastapi.responses import FileResponse

@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=filename)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
