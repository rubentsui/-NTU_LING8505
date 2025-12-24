import sys
import json
from chromadb.utils import embedding_functions

def main():
    if len(sys.argv) < 2:
        return
    text = sys.argv[1]
    
    # Suppress warnings
    import warnings
    warnings.simplefilter('ignore')
    
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    emb = ef([text])[0]
    
    print(json.dumps(emb.tolist()))

if __name__ == "__main__":
    main()
