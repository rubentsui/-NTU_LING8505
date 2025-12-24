from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import shutil
from typing import List, Dict, Any

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "data"
DEFAULT_FILE = os.path.join(DATA_DIR, "evaluated_results.xlsx")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def process_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Process the DataFrame to extract metrics and organize data for the frontend.
    Supports multiple metrics: BLEU, BLEURT, COMET (w/ reference) and COMET-KIWI, TransQuest (w/o reference)
    Enhanced to handle various column naming patterns including missing parentheses and prefix patterns.
    """
    # Replace NaN with None (null in JSON)
    df = df.where(pd.notnull(df), None)
    
    columns = df.columns.tolist()
    
    # Define metric mappings (more specific patterns first to avoid false matches)
    metric_patterns = {
        'BLEU': ['sacrebleu', 'BLEU'],
        'BLEURT': ['BLEURT'],
        'BERTScore': ['BERTScore', 'BERT', 'bert_score'],
        'COMET-KIWI': ['wmt22-cometkiwi-da', 'COMET-KIWI', 'COMETKIWI'],  # Must come before COMET
        'COMET': ['wmt22-comet-da', 'COMET'],
        'TransQuest': ['monotransquest-da-multilingual', 'TransQuest', 'TQ']
    }
    
    reference_metrics = ['BLEU', 'BLEURT', 'COMET', 'BERTScore']
    qe_metrics = ['COMET-KIWI', 'TransQuest']
    
    # Get all metric keywords for filtering
    all_metric_keywords = []
    for patterns in metric_patterns.values():
        all_metric_keywords.extend([p.lower() for p in patterns])
    
    # Step 1: Find translation text columns (exclude metric columns)
    potential_text_cols = []
    for col in columns:
        if col.startswith('zh('):
            # Check if this column contains any metric keyword
            col_lower = col.lower()
            is_metric = any(keyword in col_lower for keyword in all_metric_keywords)
            if not is_metric:
                potential_text_cols.append(col)
    
    # Step 2: Normalize column names (add missing parentheses)
    normalized_text_cols = {}
    for col in potential_text_cols:
        if ')' not in col:
            normalized = col + ')'
        else:
            normalized = col
        normalized_text_cols[col] = normalized
    
    # Step 3: Detect available metrics and build column mapping
    available_metrics = set()
    metric_type_map = {}
    model_metric_map = {}  # {model_name: {metric_name: column_name}}
    
    for text_col in potential_text_cols:
        model_name = normalized_text_cols[text_col].replace('zh(', '').replace(')', '')
        model_metric_map[model_name] = {}
        
        # For each metric, try to find the corresponding column
        # Process in order so more specific patterns match first
        # Track which columns have been matched to avoid duplicate matching
        matched_cols = set()
        
        for metric, patterns in metric_patterns.items():
            matched = False
            for pattern in patterns:
                if matched:
                    break
                # Try to find columns that match this model + metric combination
                for col in columns:
                    # Skip if this column was already matched to another metric for this model
                    if col in matched_cols:
                        continue
                        
                    col_lower = col.lower()
                    pattern_lower = pattern.lower()
                    text_col_in_col = text_col.lower() in col_lower or text_col in col
                    pattern_in_col = pattern_lower in col_lower
                    
                    if text_col_in_col and pattern_in_col:
                        # Found a match!
                        model_metric_map[model_name][metric] = col
                        available_metrics.add(metric)
                        matched_cols.add(col)  # Mark this column as matched
                        if metric in reference_metrics:
                            metric_type_map[metric] = 'reference'
                        else:
                            metric_type_map[metric] = 'qe'
                        matched = True
                        break
    
    # Step 3.5: Identify reference column
    # Check for explicit reference columns first
    reference_col = None
    if 'zh_reference' in columns:
        reference_col = 'zh_reference'
    elif 'reference' in columns:
        reference_col = 'reference'
    else:
        # Check for columns containing 'reference'
        ref_cols = [c for c in columns if 'reference' in c.lower()]
        if ref_cols:
            reference_col = ref_cols[0]
    
    # Heuristic: If no explicit reference found, and we have exactly one model without metrics,
    # treat it as the reference.
    # DISABLED: This heuristic can incorrectly treat models without metrics as references
    # Users should explicitly mark reference columns with 'reference' in the name
    # if not reference_col:
    #     models_with_metrics = []
    #     models_without_metrics = []
    #     for text_col in potential_text_cols:
    #         model_name = normalized_text_cols[text_col].replace('zh(', '').replace(')', '')
    #         if model_metric_map.get(model_name):
    #             models_with_metrics.append(text_col)
    #         else:
    #             models_without_metrics.append(text_col)
    #     
    #     if len(models_without_metrics) == 1 and len(models_with_metrics) > 0:
    #         reference_col = models_without_metrics[0]
    #         # Remove from potential_text_cols so it's not treated as a model
    #         potential_text_cols.remove(reference_col)
    #         # Remove from model_metric_map
    #         model_name = normalized_text_cols[reference_col].replace('zh(', '').replace(')', '')
    #         if model_name in model_metric_map:
    #             del model_metric_map[model_name]

    has_reference = reference_col is not None
    
    # Step 4: Build structured data
    structured_data = []
    for idx, row in df.iterrows():
        item = {
            "id": idx,
            "source": row.get('en', ''),
            "reference": row.get(reference_col) if reference_col else None,
            "models": {}
        }
        
        for text_col in potential_text_cols:
            model_name = normalized_text_cols[text_col].replace('zh(', '').replace(')', '')
            
            model_data = {
                "translation": row.get(text_col),
                "scores": {}
            }
            
            # Add scores from the mapping we built
            if model_name in model_metric_map:
                for metric, col_name in model_metric_map[model_name].items():
                    model_data["scores"][metric] = row.get(col_name)
            
            item["models"][model_name] = model_data
        
        structured_data.append(item)
    
    # Step 5: Calculate stats
    stats = {}
    for text_col in potential_text_cols:
        model_name = normalized_text_cols[text_col].replace('zh(', '').replace(')', '')
        stats[model_name] = {}
        
        if model_name in model_metric_map:
            for metric, col_name in model_metric_map[model_name].items():
                stats[model_name][metric] = df[col_name].mean()

    return {
        "data": structured_data,
        "stats": stats,
        "models": [c.replace("zh(", "").replace(")", "") for c in potential_text_cols],
        "available_metrics": list(available_metrics),
        "metric_types": metric_type_map,
        "has_reference": has_reference,
        "mode": "reference" if has_reference or any(m in available_metrics for m in reference_metrics) else "qe"
    }

@app.get("/")
def read_root():
    return {"message": "Translation Dashboard API is running"}

@app.get("/api/data")
def get_data():
    if not os.path.exists(DEFAULT_FILE):
        return {"error": "Default file not found"}
    
    try:
        df = pd.read_excel(DEFAULT_FILE)
        return process_dataframe(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/preview")
async def upload_file_preview(file: UploadFile = File(...)):
    """Upload file and return column information for user selection"""
    file_location = os.path.join(DATA_DIR, f"temp_{file.filename}")
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    try:
        df = pd.read_excel(file_location)
        columns = df.columns.tolist()
        
        # Provide sample data for each column (first 3 rows)
        sample_data = {}
        for col in columns:
            sample_data[col] = df[col].head(3).tolist()
        
        return {
            "filename": file.filename,
            "temp_path": file_location,
            "columns": columns,
            "sample_data": sample_data,
            "row_count": len(df)
        }
    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=400, detail=f"Invalid Excel file: {str(e)}")

@app.post("/api/upload/process")
async def process_uploaded_file(config: Dict[str, Any]):
    """Process uploaded file with user-selected column configuration"""
    temp_path = config.get("temp_path")
    
    if not temp_path or not os.path.exists(temp_path):
        raise HTTPException(status_code=400, detail="Temporary file not found")
    
    try:
        df = pd.read_excel(temp_path)
        
        # Extract configuration
        source_col = config.get("source_column")
        reference_col = config.get("reference_column")
        model_columns = config.get("model_columns", [])  # List of {name, text_col, metric_cols}
        
        # Build structured data based on user configuration
        structured_data = []
        for idx, row in df.iterrows():
            item = {
                "id": idx,
                "source": row.get(source_col, '') if source_col else '',
                "reference": row.get(reference_col) if reference_col else None,
                "models": {}
            }
            
            for model_config in model_columns:
                model_name = model_config.get("name")
                text_col = model_config.get("text_column")
                metric_cols = model_config.get("metric_columns", {})
                
                model_data = {
                    "translation": row.get(text_col),
                    "scores": {}
                }
                
                # Add scores
                for metric_name, col_name in metric_cols.items():
                    model_data["scores"][metric_name] = row.get(col_name)
                
                item["models"][model_name] = model_data
            
            structured_data.append(item)
        
        # Calculate stats
        stats = {}
        for model_config in model_columns:
            model_name = model_config.get("name")
            metric_cols = model_config.get("metric_columns", {})
            stats[model_name] = {}
            
            for metric_name, col_name in metric_cols.items():
                if col_name in df.columns:
                    stats[model_name][metric_name] = df[col_name].mean()
        
        # Determine available metrics and their types
        available_metrics = set()
        metric_types = {}
        reference_metric_names = ['BLEU', 'BLEURT', 'COMET']
        
        for model_config in model_columns:
            metric_cols = model_config.get("metric_columns", {})
            for metric_name in metric_cols.keys():
                available_metrics.add(metric_name)
                if metric_name in reference_metric_names:
                    metric_types[metric_name] = 'reference'
                else:
                    metric_types[metric_name] = 'qe'
        
        # Save to default location
        final_path = os.path.join(DATA_DIR, "evaluated_results.xlsx")
        shutil.copy(temp_path, final_path)
        
        # Clean up temp file
        os.remove(temp_path)
        
        return {
            "data": structured_data,
            "stats": stats,
            "models": [m.get("name") for m in model_columns],
            "available_metrics": list(available_metrics),
            "metric_types": metric_types,
            "has_reference": reference_col is not None,
            "mode": "reference" if reference_col or any(m in available_metrics for m in reference_metric_names) else "qe"
        }
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=400, detail=f"Processing error: {str(e)}")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Legacy upload endpoint - uses automatic column detection"""
    file_location = os.path.join(DATA_DIR, file.filename)
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    try:
        df = pd.read_excel(file_location)
        return process_dataframe(df)
    except Exception as e:
        os.remove(file_location) # Clean up bad file
        raise HTTPException(status_code=400, detail=f"Invalid Excel file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
