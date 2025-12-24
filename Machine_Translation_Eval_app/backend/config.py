import json
import os

MODELS_CONFIG_PATH = "models_config.json"

DEFAULT_MODELS = {
    "wmt22-cometkiwi-da": {
        "type": "comet",
        "model_name": "Unbabel/wmt22-cometkiwi-da",
        "category": "Quality Estimation",
        "description": "Reference-free quality estimation"
    },
    "monotransquest-da-multilingual": {
        "type": "transquest",
        "model_name": "TransQuest/monotransquest-da-multilingual",
        "category": "Quality Estimation",
        "description": "Multilingual quality estimation"
    },
    "wmt22-comet-da": {
        "type": "comet",
        "model_name": "Unbabel/wmt22-comet-da",
        "category": "Reference-based",
        "description": "Reference-based evaluation"
    },
    "sacrebleu": {
        "type": "sacrebleu",
        "model_name": "sacrebleu",
        "category": "Reference-based",
        "description": "Standard BLEU score"
    },
    "ter": {
        "type": "ter",
        "model_name": "ter",
        "category": "Reference-based",
        "description": "Translation Edit Rate"
    },
    "chrf": {
        "type": "chrf",
        "model_name": "chrf",
        "category": "Reference-based",
        "description": "Character F-score"
    },
    "bertscore": {
        "type": "bertscore",
        "model_name": "bert-base-multilingual-cased",
        "category": "Reference-based",
        "description": "BERTScore (Multilingual)"
    }
}

def get_models():
    if os.path.exists(MODELS_CONFIG_PATH):
        with open(MODELS_CONFIG_PATH, "r") as f:
            custom_models = json.load(f)
            return {**DEFAULT_MODELS, **custom_models}
    return DEFAULT_MODELS
