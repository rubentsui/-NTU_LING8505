from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from main import run_translation_agent

app = FastAPI(title="Translation Agent API")

class TranslationRequest(BaseModel):
    input_text: str
    source_lang: str = "auto"
    target_lang: Optional[str] = None
    model: Optional[str] = "meta-llama/Llama-3.3-70B-Instruct"
    provider: str = "nebius"
    agent_type: str = "context"
    retrieval_method: str = "semantic"
    full_doc_mode: bool = False
    n_results: int = 3
    k_glossary: int = 10
    sliding_window_size: int = 3
    debug: bool = False

@app.post("/translate")
async def translate(request: TranslationRequest):
    try:
        # Delegate to the library function
        result = run_translation_agent(
            input_text=request.input_text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            model=request.model,
            provider=request.provider,
            agent_type=request.agent_type,
            retrieval_method=request.retrieval_method,
            full_doc_mode=request.full_doc_mode,
            n_results=request.n_results,
            k_glossary=request.k_glossary,
            sliding_window_size=request.sliding_window_size,
            debug=request.debug
        )
        return {"translation": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
