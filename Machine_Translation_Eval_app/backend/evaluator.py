import os
import pandas as pd
import torch
from typing import List, Dict
import sacrebleu
from comet import download_model, load_from_checkpoint
from bert_score import BERTScorer

# Monkey-patch transformers for TransQuest compatibility
import transformers.optimization
import torch.optim
if not hasattr(transformers.optimization, "AdamW"):
    transformers.optimization.AdamW = torch.optim.AdamW
if not hasattr(transformers.optimization, "Adafactor"):
    class Adafactor(torch.optim.Optimizer):
        def __init__(self, params, **kwargs):
            super().__init__(params, {})
        def step(self): pass
    transformers.optimization.Adafactor = Adafactor

# Patch ROBERTA_PRETRAINED_MODEL_ARCHIVE_LIST
try:
    import transformers.models.roberta.modeling_roberta
    if not hasattr(transformers.models.roberta.modeling_roberta, "ROBERTA_PRETRAINED_MODEL_ARCHIVE_LIST"):
        transformers.models.roberta.modeling_roberta.ROBERTA_PRETRAINED_MODEL_ARCHIVE_LIST = [
            "roberta-base", "roberta-large", "roberta-large-mnli", "distilroberta-base",
            "roberta-base-openai-detector", "roberta-large-openai-detector",
        ]
except ImportError: pass

# Patch SequenceSummary
try:
    import transformers.models.xlm.modeling_xlm
    if not hasattr(transformers.models.xlm.modeling_xlm, "SequenceSummary"):
        class SequenceSummary(torch.nn.Module):
            def __init__(self, config):
                super().__init__()
                self.summary = torch.nn.Identity()
            def forward(self, x): return x
        transformers.models.xlm.modeling_xlm.SequenceSummary = SequenceSummary
except ImportError: pass

# Patch XLM_ROBERTA_PRETRAINED_MODEL_ARCHIVE_LIST
try:
    import transformers.models.xlm_roberta.modeling_xlm_roberta
    if not hasattr(transformers.models.xlm_roberta.modeling_xlm_roberta, "XLM_ROBERTA_PRETRAINED_MODEL_ARCHIVE_LIST"):
        transformers.models.xlm_roberta.modeling_xlm_roberta.XLM_ROBERTA_PRETRAINED_MODEL_ARCHIVE_LIST = [
            "xlm-roberta-base", "xlm-roberta-large",
        ]
except ImportError: pass

from transquest.algo.sentence_level.monotransquest.run_model import MonoTransQuestModel
from config import get_models

class Evaluator:
    def __init__(self):
        self.loaded_models = {}
        self.model_configs = get_models()

    def load_model(self, model_key: str, progress_callback=None):
        if model_key in self.loaded_models:
            return self.loaded_models[model_key]

        config = self.model_configs.get(model_key)
        if not config:
            raise ValueError(f"Unknown model: {model_key}")

        msg = f"Loading model: {model_key} ({config['type']})"
        print(msg)
        if progress_callback:
            progress_callback(msg)
        
        if config['type'] == 'comet':
            if progress_callback:
                progress_callback(f"Downloading/Loading Comet model: {config['model_name']}...")
            model_path = download_model(config['model_name'])
            model = load_from_checkpoint(model_path)
            model.eval()
            if torch.cuda.is_available():
                model = model.cuda()
            self.loaded_models[model_key] = model
            
        elif config['type'] == 'transquest':
            if progress_callback:
                progress_callback(f"Downloading/Loading TransQuest model: {config['model_name']}...")
            model = MonoTransQuestModel("xlmroberta", config['model_name'], use_cuda=torch.cuda.is_available())
            self.loaded_models[model_key] = model

        elif config['type'] in ['sacrebleu', 'ter', 'chrf']:
            # SacreBLEU metrics don't need heavy model loading
            self.loaded_models[model_key] = config['type']
            
        elif config['type'] == 'bertscore':
            if progress_callback:
                progress_callback(f"Loading BERTScore model: {config['model_name']}...")
            # Initialize BERTScorer
            # We use use_fast_tokenizer=True by default for speed
            scorer = BERTScorer(model_type=config['model_name'], device='cuda' if torch.cuda.is_available() else 'cpu')
            self.loaded_models[model_key] = scorer
            
        return self.loaded_models[model_key]

    def evaluate(self, df: pd.DataFrame, src_col: str, tgt_cols: List[str], models: List[str], ref_col: str = None, progress_callback=None) -> pd.DataFrame:
        if progress_callback:
            progress_callback("Starting evaluation...")
        else:
            print("Starting evaluation...")
            
        results_df = df.copy()
        
        # Prepare data for evaluation
        # Comet expects: [{"src": "...", "mt": "...", "ref": "..."}] (ref is optional for QE but CometKiwi is QE)
        # TransQuest expects: [[src, mt], ...]
        
        for model_key in models:
            model = self.load_model(model_key, progress_callback)
            config = self.model_configs[model_key]
            
            for tgt_col in tgt_cols:
                msg = f"Evaluating {tgt_col} with {model_key}..."
                print(msg)
                if progress_callback:
                    progress_callback(msg)
                    
                scores = []
                
                if config['type'] == 'comet':
                    data = []
                    for _, row in df.iterrows():
                        item = {"src": str(row[src_col]), "mt": str(row[tgt_col])}
                        if ref_col and ref_col in df.columns:
                            item["ref"] = str(row[ref_col])
                        data.append(item)
                    
                    model_output = model.predict(data, batch_size=8, gpus=1 if torch.cuda.is_available() else 0)
                    scores = model_output.scores
                    
                elif config['type'] == 'transquest':
                    data = []
                    for _, row in df.iterrows():
                        data.append([str(row[src_col]), str(row[tgt_col])])
                        
                    # TransQuest predict returns (predictions, raw_outputs)
                    predictions, _ = model.predict(data)
                    scores = predictions

                elif config['type'] == 'sacrebleu':
                    if not ref_col or ref_col not in df.columns:
                        raise ValueError(f"Reference column is required for SacreBLEU but not provided or found.")
                    
                    refs = df[ref_col].astype(str).tolist()
                    sys = df[tgt_col].astype(str).tolist()
                    
                    # Check for Chinese characters to decide on tokenizer
                    # Simple check: if any character in the first few sentences is Chinese
                    import re
                    def contains_chinese(text):
                        return bool(re.search(r'[\u4e00-\u9fff]', text))
                    
                    # Check a sample of the reference text
                    sample_text = "".join(refs[:5])
                    use_zh = contains_chinese(sample_text)
                    
                    tokenizer = 'zh' if use_zh else '13a'
                    msg = f"Using tokenizer: {tokenizer} (Chinese detected: {use_zh})"
                    print(msg)
                    if progress_callback:
                        progress_callback(msg)
                    
                    scores = []
                    for s, r in zip(sys, refs):
                        # references expects a list of reference strings for that sentence
                        score = sacrebleu.sentence_bleu(s, [r], tokenize=tokenizer).score
                        scores.append(score)

                elif config['type'] == 'ter':
                    if not ref_col or ref_col not in df.columns:
                        raise ValueError(f"Reference column is required for TER but not provided or found.")
                    
                    refs = df[ref_col].astype(str).tolist()
                    sys = df[tgt_col].astype(str).tolist()
                    
                    # Check for Chinese characters
                    import re
                    def contains_chinese(text):
                        return bool(re.search(r'[\u4e00-\u9fff]', text))
                    
                    sample_text = "".join(refs[:5])
                    use_zh = contains_chinese(sample_text)
                    
                    if use_zh:
                        print("Chinese detected: applying tokenization for TER...")
                        try:
                            from sacrebleu.tokenizers.tokenizer_zh import TokenizerZh
                            tokenizer = TokenizerZh()
                            # Tokenize both system output and references
                            sys = [tokenizer(s) for s in sys]
                            refs = [tokenizer(r) for r in refs]
                        except ImportError:
                            print("Warning: Could not import TokenizerZh, TER scores may be inaccurate for Chinese.")
                    
                    scores = []
                    for s, r in zip(sys, refs):
                        # TER score is an error rate (lower is better), but typically displayed as 0-100
                        score = sacrebleu.sentence_ter(s, [r]).score
                        scores.append(score)

                elif config['type'] == 'chrf':
                    if not ref_col or ref_col not in df.columns:
                        raise ValueError(f"Reference column is required for chrF but not provided or found.")
                    
                    refs = df[ref_col].astype(str).tolist()
                    sys = df[tgt_col].astype(str).tolist()
                    
                    scores = []
                    for s, r in zip(sys, refs):
                        score = sacrebleu.sentence_chrf(s, [r]).score
                        scores.append(score)

                elif config['type'] == 'bertscore':
                    if not ref_col or ref_col not in df.columns:
                        raise ValueError(f"Reference column is required for BERTScore but not provided or found.")
                    
                    refs = df[ref_col].astype(str).tolist()
                    sys = df[tgt_col].astype(str).tolist()
                    
                    msg = "Calculating BERTScore..."
                    print(msg)
                    if progress_callback:
                        progress_callback(msg)
                    
                    # BERTScore can process in batches
                    P, R, F1 = model.score(sys, refs)
                    
                    # We typically use F1 score
                    scores = F1.tolist()
                
                # Add scores to dataframe
                col_name = f"{model_key}_{tgt_col}"
                results_df[col_name] = scores
                
        return results_df

evaluator = Evaluator()
