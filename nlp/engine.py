import os
import json
import google.generativeai as genai
from pydantic import BaseModel, Field
from typing import Optional, Literal
from config import GEMINI_API_KEY

# Configure Gemini globally
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class NLPEntities(BaseModel):
    assigned_to: Optional[str] = Field(None, description="Username of assignee from mention, without '@'")
    task_code: Optional[str] = Field(None, description="Task code identifier (e.g., 'T-1023')")
    title: Optional[str] = Field(None, description="Cleaned title of the task being created")
    block_reason: Optional[str] = Field(None, description="Reason for blocking the task")
    alert_message: Optional[str] = Field(None, description="Emergency description text")

class NLPResult(BaseModel):
    intent: Literal["CREATE_TASK", "COMPLETE_TASK", "BLOCK_TASK", "ALERT", "OTHER"]
    confidence: float
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    entities: NLPEntities

system_prompt = """You are an expert clinical operations parser. Your job is to parse conversational text from medical staff and extract structured operational signals.

Classify the text into one of these intents:
1. CREATE_TASK: Staff member assigns a task to a user (e.g., "@NurseNeha please check bed 4").
2. COMPLETE_TASK: Staff member reports a task code is finished (e.g., "T-102 is completed").
3. BLOCK_TASK: Staff member reports a task is blocked by an obstacle (e.g., "T-204 blocked because lab results are missing").
4. ALERT: Staff member reports an emergency (e.g., "Code blue in room 4" or "Need crash cart immediately").
5. OTHER: For messages that do not contain operational instructions (e.g., "Thanks!", "Got it").

Determine Priority:
- CRITICAL: Emergency alerts, cardiac arrest, patient coding.
- HIGH: Urgent tasks, immediate medications, significant blockers.
- MEDIUM: Standard checks, reports, routine care.
- LOW: Non-time-critical admin tasks, cleaning.

Extract Entities:
- assigned_to: The username mentioned after '@' (e.g. from '@NurseNeha' extract 'NurseNeha').
- task_code: The task number in the format 'T-XXXX' (e.g. 'T-1023').
- title: The content/title of the task to create.
- block_reason: The reason why a task is blocked (usually following 'because' or 'due to').
- alert_message: The emergency warning message.

Provide a confidence score between 0.0 and 1.0 representing your classification certainty.
"""

def process_message(text: str, user_id: str) -> dict:
    """
    Extracts structural signals from the message using Gemini.
    Returns the parsed intent, priority, entities, and confidence score.
    """
    if not text or len(text.strip()) < 3:
        return {"status": "invalid", "message": "Text too short"}

    # Base safe default to fallback to if the API fails
    safe_default = {
        "status": "success",
        "intent": "OTHER",
        "confidence": 0.0,
        "priority": "LOW",
        "entities": {}
    }

    if not GEMINI_API_KEY:
        print("NLP Engine Error: Missing GEMINI_API_KEY")
        return safe_default

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=system_prompt,
            generation_config={
                "temperature": 0.1,
            }
        )
        
        # We request structured output matching NLPResult
        response = model.generate_content(
            f"Parse the following message:\n\n{text}",
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=NLPResult,
                temperature=0.1,
            )
        )
        
        # Process the JSON string back to dictionary
        result_json = response.text
        result_dict = json.loads(result_json)
        
        return {
            "status": "success",
            "intent": result_dict.get("intent", "OTHER"),
            "confidence": result_dict.get("confidence", 0.0),
            "priority": result_dict.get("priority", "LOW"),
            "entities": result_dict.get("entities", {})
        }
    except Exception as e:
        print(f"NLP Engine Error: {str(e)}")
        return safe_default
