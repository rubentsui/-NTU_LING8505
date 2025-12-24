import argparse
import os
import struct
import time
from src.agent import ContextAgent, SimpleAgent, ToolAgent
from src.tm import TranslationMemory
from langdetect import detect, DetectorFactory

# Ensure deterministic results for short texts
DetectorFactory.seed = 0

def clean_model_name(model_name):
    for char in model_name:
        if not char.isalnum() and char != "_":
            model_name = model_name.replace(char, "_")
    return model_name  

def run_translation_agent(input_text=None, input_file=None, source_lang="auto", target_lang=None, model=None, provider="nebius", agent_type="context", retrieval_method="semantic", full_doc_mode=False, n_results=3, k_glossary=10, sliding_window_size=3, debug=False, output_file=None):
    """
    Runs the translation agent as a library function.
    
    Args:
        input_text (str): The text to translate.
        input_file (str): Path to input file (used if input_text is None).
        source_lang (str): Source language code.
        target_lang (str): Target language code.
        model (str): Model name.
        provider (str): LLM provider.
        agent_type (str): 'context', 'tool', or 'simple'.
        retrieval_method (str): 'semantic' or 'bm25'.
        full_doc_mode (bool): Whether to process as one block.
        n_results (int): Number of TM results.
        k_glossary (int): Number of glossary terms.
        sliding_window_size (int): Size of context window.
        debug (bool): Enable debug logging.
        output_file (str): Path to output file (required if input_file is used).
        
    Returns:
        str: The translated text (if input_text is provided, otherwise returns None).
    """
    
    # Configure Provider
    api_key = None
    base_url = None
    
    if provider == "ollama":
        base_url = "http://localhost:11434/v1"
        api_key = "ollama"
        if not model: model = "llama3"
    elif provider == "gemini":
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        api_key = os.getenv("GEMINI_API_KEY")
        if not model: model = "gemini-1.5-flash"
    elif provider == "nebius":
        base_url = "https://api.tokenfactory.nebius.com/v1/"
        api_key = os.getenv("NEBIUS_API_KEY")
        if not model: model = "meta-llama/Llama-3.3-70B-Instruct"
    else:
        # OpenAI default
        if not model: model = "gpt-4o"

    # Language Handling
    if source_lang == "auto":
        if input_text:
            sample = input_text[:1000]
            try:
                detected = detect(sample)
                print(f"Detected language: {detected}")
                source_lang = detected if detected in ['zh', 'en'] else detected
            except:
                source_lang = "en"
        elif input_file and os.path.exists(input_file):
             try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    sample = f.read(1000)
                detected = detect(sample)
                print(f"Detected language: {detected}")
                source_lang = detected if detected in ['zh', 'en'] else detected
             except:
                source_lang = "en"
        else:
            source_lang = "en"

    if not target_lang:
        target_lang = 'en' if source_lang.startswith('zh') else 'zh'

    print(f"Language Configuration: Source='{source_lang}', Target='{target_lang}'")

    # Instantiate Agent
    agent_cls = ContextAgent
    if agent_type == 'simple':
        agent_cls = SimpleAgent
    elif agent_type == 'tool':
        agent_cls = ToolAgent
        
    agent = agent_cls(
        model=model,
        api_key=api_key,
        base_url=base_url,
        source_lang=source_lang,
        target_lang=target_lang,
        debug=debug,
        retrieval_method=retrieval_method,
        full_doc_mode=full_doc_mode,
        n_results=n_results,
        k_glossary=k_glossary,
        sliding_window_size=sliding_window_size
    )
    
    if input_text is not None:
        return agent.process_text(input_text)
    elif input_file:
        if not output_file:
            print("Error: output_file required when using input_file")
            return None
        agent.run(input_file, output_file)
        return None
    else:
        print("Error: Either input_text or input_file must be provided.")
        return None

def main():
    parser = argparse.ArgumentParser(description="Machine Translation Agent with TM")
    parser.add_argument("input_file", nargs='?', help="Path to the input English text file")
    parser.add_argument("--output", help="Path to the output Chinese text file", default=None)
    parser.add_argument("--add-to-tm", help="Add a segment to TM: 'Source|Target'", default=None)
    parser.add_argument("--import-tm", help="Path to Parquet file to import into TM", default=None)
    parser.add_argument("--import-glossary", help="Path to Parquet file to import into Contextual Glossary", default=None)
    parser.add_argument("--provider", help="LLM Provider: 'openai' or 'ollama' or 'nebius' or 'gemini'", default="nebius")
    parser.add_argument("--model", help="Model name", default=None)
    parser.add_argument("--source", help="Source language code (default: auto)", default="auto")
    parser.add_argument("--target", help="Target language code (default: inferred)", default=None)
    
    parser.add_argument("--agent-type", choices=['context', 'tool', 'simple'], default='context', help="Type of agent to use (default: context)")
    parser.add_argument("--retrieval", choices=['semantic', 'bm25'], default='semantic', help="Retrieval method for Context/Tool agents (default: semantic)")
    parser.add_argument("--full-doc", action="store_true", help="Enable full document mode (processes entire file at once)")
    parser.add_argument("--n-results", type=int, default=3, help="Number of TM results to retrieve (default: 3)")
    parser.add_argument("--k-glossary", type=int, default=10, help="Number of glossary candidates to consider (default: 10)")
    parser.add_argument("--sliding-window", type=int, default=3, help="Size of the sliding context window (default: 3)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    start_time = time.time()

    # Configure Provider
    api_key = None
    base_url = None
    model = args.model

    if args.provider == "ollama":
        base_url = "http://localhost:11434/v1"
        api_key = "ollama" # Ollama requires a non-empty key usually, or ignores it
        if not model:
            model = "llama3"
    elif args.provider == "gemini":
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        api_key = os.getenv("GEMINI_API_KEY")
        if not model:
            model = "gemini-1.5-flash"
    elif args.provider == "nebius":
        base_url = "https://api.tokenfactory.nebius.com/v1/"
        api_key = os.getenv("NEBIUS_API_KEY")
        if not model:
            model = "meta-llama/Llama-3.3-70B-Instruct"
    else:
        # OpenAI default
        if not model:
            model = "gpt-4o"

    # Language Detection and Inference
    source_lang = args.source
    target_lang = args.target

    # 1. Auto-detect source if needed and possible
    if source_lang == "auto" and args.input_file and os.path.exists(args.input_file):
        try:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                sample_text = f.read(1000) # Read first 1000 chars
            detected = detect(sample_text)
            print(f"Detected language: {detected}")
            if detected.startswith('zh'):
                source_lang = 'zh'
            elif detected == 'en':
                source_lang = 'en'
            else:
                # Fallback or keep as detected? Let's map common ones or just use code if supported.
                # For this specific app (EN/ZH), we'll try to map to 'en' or 'zh', else default 'en'.
                source_lang = detected # Use the detected code, might work if TM supports it or just for info.
                # But our logic mainly handles en/zh switching.
        except Exception as e:
            print(f"Warning: Auto-detection failed ({e}). Defaulting to 'en'.")
            source_lang = 'en'
    
    if source_lang == "auto":
        source_lang = "en" # Default fallback if no input file or detection skipped

    # 2. Infer target if not provided
    if target_lang is None:
        if source_lang.startswith('zh'):
            target_lang = 'en'
        else:
            target_lang = 'zh'

    print(f"Language Configuration: Source='{source_lang}', Target='{target_lang}'")

    if args.add_to_tm:
        if '|' not in args.add_to_tm:
            print("Error: Format for adding to TM is 'Source|Target'")
            return
        source, target = args.add_to_tm.split('|', 1)
        tm = TranslationMemory(source_lang=source_lang, target_lang=target_lang)
        tm.add_segment(source.strip(), target.strip())
        print(f"Added to TM ({source_lang}->{target_lang}): {source.strip()} -> {target.strip()}")
        return

    if args.import_tm:
        import pandas as pd
        if not os.path.exists(args.import_tm):
            print(f"Error: Parquet file '{args.import_tm}' not found.")
            return
        
        print(f"Reading {args.import_tm}...")
        try:
            df = pd.read_parquet(args.import_tm)
            if source_lang not in df.columns or target_lang not in df.columns:
                print(f"Error: Parquet file must contain '{source_lang}' and '{target_lang}' columns.")
                return
            
            # Filter out empty strings if any
            df = df.dropna(subset=[source_lang, target_lang])
            sources = df[source_lang].astype(str).tolist()
            targets = df[target_lang].astype(str).tolist()
            
            print(f"Importing {len(sources)} segments to TM ({source_lang}->{target_lang})...")
            tm = TranslationMemory(source_lang=source_lang, target_lang=target_lang)
            
            # Batch import to avoid memory issues if file is huge
            batch_size = 1000
            for i in range(0, len(sources), batch_size):
                batch_sources = sources[i:i+batch_size]
                batch_targets = targets[i:i+batch_size]
                tm.add_segments(batch_sources, batch_targets)
                print(f"Imported {min(i+batch_size, len(sources))}/{len(sources)}")
                
            print("Import completed successfully.")
        except Exception as e:
            print(f"Error importing Parquet: {e}")
        return

    if args.import_glossary:
        import pyarrow.parquet as pq
        if not os.path.exists(args.import_glossary):
            print(f"Error: Parquet file '{args.import_glossary}' not found.")
            return

        print(f"Reading {args.import_glossary} for glossary extraction...")
        try:
            pq_file = pq.ParquetFile(args.import_glossary)
            tm = TranslationMemory(source_lang=source_lang, target_lang=target_lang)
            glossary = tm.glossary
            
            print("Resetting glossary before import...")
            glossary.reset()
            
            total_rows = pq_file.metadata.num_rows
            print(f"Total rows to process: {total_rows}")
            print("Extracting terms and populating glossary (this may take a while)...")
            
            terms_batch = []
            trans_batch = []
            ctx_batch = []
            lang_batch = []
            
            count = 0
            
            # Iterate over batches
            for batch in pq_file.iter_batches(batch_size=2000):
                df = batch.to_pandas()
                
                for index, row in df.iterrows():
                    try:
                        en_text = row['en']
                        zh_text = row['zh']
                        align_data = row['word_alignments']
                        
                        if not isinstance(en_text, str) or not isinstance(zh_text, str):
                            continue
                         
                        en_tokens = en_text.strip().split()
                        zh_tokens = zh_text.strip().split()
                        
                        pairs = []
                        if isinstance(align_data, bytes):
                            l = len(align_data)
                            if l % 2 == 0:
                                shorts = struct.unpack('>' + 'H' * (l // 2), align_data)
                                for i in range(0, len(shorts), 2):
                                    if i+1 < len(shorts):
                                        pairs.append((shorts[i], shorts[i+1]))
                        else:
                            # String parsing fallback
                            aligns = str(align_data).strip().split()
                            for align in aligns:
                                try:
                                    src, tgt = map(int, align.split('-'))
                                    pairs.append((src, tgt))
                                except:
                                    continue
                        
                        for src_idx, tgt_idx in pairs:
                            if src_idx < len(en_tokens) and tgt_idx < len(zh_tokens):
                                term = en_tokens[src_idx]
                                translation = zh_tokens[tgt_idx]
                                
                                terms_batch.append(term)
                                trans_batch.append(translation)
                                ctx_batch.append(en_text)
                                lang_batch.append(source_lang)
                    except:
                        continue
                        
                    count += 1
                    
                    if len(terms_batch) >= 1000:
                        print(f"Committing batch of {len(terms_batch)} terms...")
                        glossary.add_batch(terms_batch, trans_batch, ctx_batch, lang_batch)
                        terms_batch = []
                        trans_batch = []
                        ctx_batch = []
                        lang_batch = []
                        print(f"Progress: ~{count} sentences processed.")

            # Final batch
            if terms_batch:
                 print(f"Committing final batch of {len(terms_batch)} terms...")
                 glossary.add_batch(terms_batch, trans_batch, ctx_batch, lang_batch)
            
            print("Glossary import completed successfully.")
            
        except Exception as e:
            print(f"Error importing glossary: {e}")
        return

    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        return

    output_file = args.output
    if not output_file:
        output_file = f"{args.provider}_{args.agent_type}_{clean_model_name(model)}.txt"

    print(f"Starting translation of {args.input_file} ({source_lang}->{target_lang})...")
    print(f"Using Provider: {args.provider}, Model: {model}, Agent Type: {args.agent_type}, Retrieval: {args.retrieval}")
    
    start_init = time.time()
    
    # Delegate to library function
    try:
        run_translation_agent(
            input_file=args.input_file,
            output_file=output_file,
            source_lang=args.source,
            target_lang=args.target,
            model=model, 
            provider=args.provider,
            agent_type=args.agent_type,
            retrieval_method=args.retrieval,
            full_doc_mode=args.full_doc,
            n_results=args.n_results,
            k_glossary=args.k_glossary,
            sliding_window_size=args.sliding_window,
            debug=args.debug
        )
        print(f"Translation completed. Output saved to {output_file}")
    except Exception as e:
        print(f"\nError during translation: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
    finally:
        total_duration = time.time() - start_time
        print(f"Total Execution Time: {total_duration:.2f}s")

if __name__ == "__main__":
    main()
