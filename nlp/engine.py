import os
import re
from transformers import pipeline

class MediStreamNLP:
    """
    Phase 3: NLP Engine Integration (Singleton)
    Loads HuggingFace DistilBERT pipelines strictly ONCE at startup to avoid re-loading on every API call.
    Strictly pure signal extraction. Does not mutate DB.
    """
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MediStreamNLP, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        print("Initializing Global NLP Singletons...")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        intent_model_path = os.path.join(base_dir, "intent_distilbert")
        priority_model_path = os.path.join(base_dir, "priority_distilbert")
        
        self.intent_pipeline = pipeline("text-classification", model=intent_model_path, tokenizer=intent_model_path)
        self.priority_pipeline = pipeline("text-classification", model=priority_model_path, tokenizer=priority_model_path)
        
        self._initialized = True
        print("NLP Engine Ready.")

    def extract_mentions(self, text: str) -> str:
        mentions = re.findall(r'@\w+', text)
        return mentions[0].replace('@', '') if mentions else None

    def extract_task_code(self, text: str) -> str:
        match = re.search(r'T-\d+', text, re.IGNORECASE)
        return match.group(0).upper() if match else None

    def _clean_text(self, text: str) -> str:
        return re.sub(r'@[a-zA-Z0-9_]+', '', text).strip()

    def process_message(self, text: str, user_id: str) -> dict:
        """
        Extracts structural signals and guarantees output contract structure.
        Phase 3: NO GENAI. NO DB CALLS.
        """
        if not text or len(text.strip()) < 3:
            return {"status": "invalid", "message": "Text too short"}

        cleaned = self._clean_text(text)
        
        # Identify Intent via Local BERT
        intent_res = self.intent_pipeline(cleaned)[0]
        intent = intent_res['label']
        confidence = intent_res['score']
        
        priority = None
        entities = {}
        
        if intent == "CREATE_TASK":
            prio_res = self.priority_pipeline(cleaned)[0]
            priority = prio_res['label']
            entities["assigned_to"] = self.extract_mentions(text)
            entities["title"] = cleaned
            
        elif intent in ["COMPLETE_TASK", "BLOCK_TASK"]:
            entities["task_code"] = self.extract_task_code(text)
            if intent == "BLOCK_TASK":
                block_parts = re.split(r'due to|because', cleaned, flags=re.IGNORECASE)
                entities["block_reason"] = block_parts[1].strip() if len(block_parts) > 1 else "Unspecified operational blocker"
                
        elif intent == "ALERT":
            prio_res = self.priority_pipeline(cleaned)[0]
            priority = prio_res['label']
            entities["alert_message"] = cleaned

        return {
            "status": "success",
            "intent": intent,
            "confidence": confidence,
            "priority": priority,
            "entities": entities
        }

# Instantiate Singleton immediately so import is heavy, not router logic
nlp_engine_instance = MediStreamNLP()

def process_message(text: str, user_id: str) -> dict:
    """Wrapper exposing the standardized contract required by main.py"""
    return nlp_engine_instance.process_message(text, user_id)
