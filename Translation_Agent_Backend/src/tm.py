import chromadb
from chromadb.utils import embedding_functions
import uuid
import re
import math
import subprocess
import json
import sys
import os
import spacy
from src.stopwords import STOPWORDS
from functools import lru_cache
try:
    from rank_bm25 import BM25Okapi
except ImportError:
    print("Warning: rank_bm25 not found. BM25 retrieval will fail if requested.")
    BM25Okapi = None

# Load Spacy model once
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Warning: 'en_core_web_sm' not found. Term selection will fallback to basic tokenization.")
    nlp = None
import difflib

class TranslationMemory:
    def __init__(self, db_path="./tm_db", source_lang="en", target_lang="zh"):
        self.client = chromadb.PersistentClient(path=db_path)
        # Use a default embedding function (Sentence Transformers)
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        
        collection_name = f"tm_{source_lang}_{target_lang}"
        self.collection = self.client.get_or_create_collection(name=collection_name, embedding_function=self.ef)
        
        # Initialize Contextual Glossary
        # We share the same db_path for simplicity
        # Share the client to avoid locking/conflicts
        self.glossary = ContextualGlossary(db_path=db_path, collection_name=f"glossary_{source_lang}_{target_lang}", embedding_function=self.ef, client=self.client)

    def add_segment(self, source, target):
        """Adds a translation pair to the memory."""
        # Check if it already exists to avoid duplicates (optional, but good for TM)
        # For simplicity, we just add.
        self.collection.add(
            documents=[source],
            metadatas=[{"target": target, "source": source}],
            ids=[str(uuid.uuid4())]
        )

    def add_segments(self, sources, targets):
        """Adds multiple translation pairs to the memory."""
        ids = [str(uuid.uuid4()) for _ in range(len(sources))]
        metadatas = [{"target": t, "source": s} for s, t in zip(sources, targets)]
        self.collection.add(
            documents=sources,
            metadatas=metadatas,
            ids=ids
        )

    def search_exact(self, query):
        """Searches for an exact match in the source text."""
        # We can use the where clause to find the exact source
        results = self.collection.get(
            where={"source": query}
        )
        
        matches = []
        if results['ids']:
            for i in range(len(results['ids'])):
                matches.append({
                    "source": results['metadatas'][i]['source'],
                    "target": results['metadatas'][i]['target']
                })
        return matches

    def search_semantic(self, query, n_results=3):
        """Searches for semantically similar segments using in-process embedding."""
        try:
            n_results = int(n_results)
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            matches = []
            if results['ids']:
                # results is a dict of lists, we need to iterate
                for i in range(len(results['ids'][0])):
                    matches.append({
                        "source": results['documents'][0][i], # This is the source text stored as document
                        "target": results['metadatas'][0][i]['target'],
                        "distance": results['distances'][0][i]
                    })
            return matches
        except Exception as e:
            print(f"DEBUG: Error in vector search: {e}")
            return []

    def _ensure_bm25(self):
        """Lazily initializes the BM25 index."""
        if hasattr(self, 'bm25_index') and self.bm25_index:
            return

        if not BM25Okapi:
            raise ImportError("rank_bm25 is not installed.")

        # print("DEBUG: Building BM25 index (this may take a moment)...")
        # Fetch all documents
        # Note: ChromaDB .get() might be slow for massive datasets, but okay for typical TM sizes
        all_docs = self.collection.get()
        self.bm25_corpus_docs = all_docs['documents'] # List of source texts
        self.bm25_corpus_meta = all_docs['metadatas']
        
        tokenized_corpus = [doc.split() for doc in self.bm25_corpus_docs]
        self.bm25_index = BM25Okapi(tokenized_corpus)
        # print(f"DEBUG: BM25 index built with {len(self.bm25_corpus_docs)} documents.")

    def search_bm25(self, query, n_results=3):
        """Searches for similar segments using BM25 (keyword matching)."""
        try:
            self._ensure_bm25()
            n_results = int(n_results)
            
            tokenized_query = query.split()
            # Get top N scores
            # BM25Okapi doesn't give a direct "top n with scores" easily in one structure usually,
            # but get_top_n returns the docs. We want distinct matches with metadata.
            
            # Use get_scores to manually find top N indices
            scores = self.bm25_index.get_scores(tokenized_query)
            top_n_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n_results]
            
            matches = []
            for idx in top_n_indices:
                score = scores[idx]
                if score <= 0: continue # Ignore irrelevant
                
                matches.append({
                    "source": self.bm25_corpus_docs[idx],
                    "target": self.bm25_corpus_meta[idx]['target'],
                    "distance": -score # TM uses distance (lower is better), BM25 uses score (higher is better). 
                                       # We typically just return the result. 
                                       # If agent expects distance, negating it roughly sorts it correct way semantically?
                                       # Actually context agent just takes the list.
                })
            return matches
        except Exception as e:
            print(f"DEBUG: Error in BM25 search: {e}")
            return []

def remove_whitespace_between_chinese(text):
    """Removes whitespace between two Chinese characters."""
    if not text:
        return ""
    # Look for whitespace preceded by a Chinese char and followed by a Chinese char
    # Range \u4e00-\u9fff covers common CJK Unified Ideographs
    return re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', text)

class ContextualGlossary:
    def __init__(self, db_path="./tm_db", collection_name="contextual_glossary", embedding_function=None, client=None):
        if client:
            self.client = client
        else:
            self.client = chromadb.PersistentClient(path=db_path)
            
        self.collection_name = collection_name
        self.ef = embedding_function
        
        # If no EF provided, create one (consistency)
        if not self.ef:
             self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

        self.collection = self.client.get_or_create_collection(name=collection_name, embedding_function=self.ef)

    def reset(self):
        """Deletes and recreates the collection."""
        try:
            self.client.delete_collection(name=self.collection_name)
        except ValueError:
            pass # Collection might not exist
        self.collection = self.client.create_collection(name=self.collection_name, embedding_function=self.ef)

    def add_entry(self, term, translation, context, source_lang="en"):
        """Adds a glossary entry with context."""
        # Clean context if it's Chinese (though usually context is source/English for retrieval)
        # If source is Chinese, we clean it.
        # But typically we search using source sentence.
        
        # Determine if we need to clean. If source_lang starts with 'zh', clean context.
        if source_lang.startswith("zh"):
            context = remove_whitespace_between_chinese(context)

        self.collection.add(
            documents=[context],
            metadatas=[{"term": term, "translation": translation, "source_lang": source_lang}],
            ids=[str(uuid.uuid4())]
        )

    def add_batch(self, terms, translations, contexts, source_langs):
        """Adds a batch of entries."""
        # Pre-process contexts
        cleaned_contexts = []
        for ctx, lang in zip(contexts, source_langs):
            if lang.startswith("zh"):
                cleaned_contexts.append(remove_whitespace_between_chinese(ctx))
            else:
                cleaned_contexts.append(ctx)

        metadatas = [{"term": t, "translation": tr, "source_lang": l} for t, tr, l in zip(terms, translations, source_langs)]
        ids = [str(uuid.uuid4()) for _ in range(len(terms))]
        
        self.collection.add(
            documents=cleaned_contexts,
            metadatas=metadatas,
            ids=ids
        )

    @lru_cache(maxsize=1)
    def _get_total_docs(self):
        """Cached total document count."""
        try:
            return self.collection.count()
        except Exception:
            return 1000

    @lru_cache(maxsize=1024)
    def _get_doc_freq(self, term):
        """Cached document frequency for a term."""
        try:
            res = self.collection.get(where={"term": term}, include=[])
            return len(res['ids'])
        except Exception:
            return 0

    def search(self, context, n_results=1, k_terms=10):
        """
        Searches for relevant glossary terms using IDF ranking and Vector Search.
        """
        # 1. Identification: Extract terms using Spacy NER and Noun Chunks
        unique_terms = []
        seen = set()
        
        if nlp:
            doc = nlp(context)
            
            # A. Named Entities (High Priority)
            for ent in doc.ents:
                term = ent.text.strip()
                if term.lower() not in seen and len(term) > 1:
                    unique_terms.append(term)
                    seen.add(term.lower())
                    
            # B. Noun Chunks (Medium Priority)
            for chunk in doc.noun_chunks:
                term = chunk.text.strip()
                if term.lower() not in seen and len(term) > 2:
                    if term.lower() not in STOPWORDS:
                        unique_terms.append(term)
                        seen.add(term.lower())
                        
            # C. Individual Token Fallback (for coverage)
            for token in doc:
                if token.is_alpha and not token.is_stop and len(token.text) > 2:
                    if token.text.lower() not in seen:
                        unique_terms.append(token.text)
                        seen.add(token.text.lower())
        else:
            # Fallback to simple regex if spacy failed to load
            tokens = re.findall(r'\b\w+\b', context)
            for token in tokens:
                if token.lower() not in STOPWORDS and token not in seen and len(token) > 2:
                    unique_terms.append(token)
                    seen.add(token)
        
        print(f"DEBUG: Candidate Terms: {unique_terms}")
        
        # 2. Compute IDF for each term (Optimized with Cache)
        total_docs = self._get_total_docs()
        print(f"DEBUG: Total docs (Cached): {total_docs}")
            
        term_scores = []
        
        for term in unique_terms:
            try:
                df = self._get_doc_freq(term)
                
                if df > 0:
                    idf = math.log(total_docs / (df + 1))
                    term_scores.append((term, idf))
            except Exception as e:
                print(f"DEBUG: Error calculating IDF for '{term}': {e}")
                continue
                
        # Sort by IDF descending
        term_scores.sort(key=lambda x: x[1], reverse=True)
        target_terms = [t[0] for t in term_scores[:k_terms]]
        
        return self.lookup_terms(target_terms, context)

    def lookup_terms(self, terms, context=None):
        """
        Looks up definitions for a list of terms.
        If context is provided, uses semantic search to find the best matching definition.
        """
        glossary_items = {}
        
        for term in terms:
            try:
                if context:
                    # Query using the context (sentence) but filtered by the term
                    results = self.collection.query(
                        query_texts=[context],
                        n_results=1,
                        where={"term": term}
                    )
                    
                    if results['ids'] and results['ids'][0]:
                        meta = results['metadatas'][0][0]
                        glossary_items[term] = meta['translation'] # meta['term'] should be same as term
                else:
                    # Fallback: Just get the first/arbitrary entry if no context
                    # Or get all? Let's get one for simplicity as a dictionary return
                    results = self.collection.get(
                        where={"term": term},
                        limit=1
                    )
                    if results['ids']:
                        glossary_items[term] = results['metadatas'][0]['translation']

            except Exception as e:
                print(f"DEBUG: Error looking up '{term}': {e}")
                continue
                
        return glossary_items

