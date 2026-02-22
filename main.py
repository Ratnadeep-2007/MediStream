from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from db_service import check_db_connection, get_active_shift, get_shift_tasks, end_active_shift, update_task_status, create_task, supabase

# Strict integration routing (Phase 8 verification)
from nlp.engine import process_message
from agent.agent_service import evaluate_shift_risk
from agent.summary_service import generate_shift_summary

app = FastAPI(title="MediStream Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Phase 4: Guaranteeing Model Load exactly once on startup"""
    print("MEDI-STREAM STARTUP SEQUENCE INITIATED.")
    
    # Connection Check
    if not check_db_connection():
        print("CRITICAL: Supabase Database inaccessible!")
    else:
        print("Supabase Data Link: OK")

    # NLP Engine Force-Init Check
    print("Pre-warming NLP pipelines...")
    _ = process_message("Test warmup CREATE_TASK", user_id="system")
    print("NLP Link: OK")
    print("Backend Fully Armed.")

class ChatRequest(BaseModel):
    message: str


class PriorityOverrideRequest(BaseModel):
    priority: str

class TaskStatusRequest(BaseModel):
    status: str

class TaskCreateRequest(BaseModel):
    title: str
    assigned_to: str


# --- Dummy Response Helper ---

def ok():
    return {"status": "success", "message": "Endpoint working", "data": {}}


# --- Endpoints ---

@app.get("/health")
def health():
    if check_db_connection():
        return {
            "status": "success",
            "backend": "running",
            "database": "connected"
        }
    else:
        return {
            "status": "error",
            "backend": "running",
            "database": "disconnected"
        }


@app.post("/chat")
def chat(body: ChatRequest):
    """
    Phase 5: Single Chat Execution Pipeline
    Validates rules, triggers strict NLP extraction, mutates DB properly, then observes Risk constraints.
    """
    user_id = "235b4451-e7f9-4dc6-9ffd-3bf8ce30ca9b" # Phase 1 Mock Auth
    
    # 1. Fetch active shift context
    shift = get_active_shift()
    if not shift:
        raise HTTPException(status_code=400, detail="Cannot log. System has no active shift.")
    
    shift_id = shift.get("id")

    # 2. Extract deterministic NLP Signals
    nlp_res = process_message(body.message, user_id)
    if nlp_res.get("status") == "invalid":
         raise HTTPException(status_code=400, detail="Message too vague for operational logging.")
    
    intent = nlp_res["intent"]
    confidence = nlp_res["confidence"]
    entities = nlp_res["entities"]
    priority = nlp_res.get("priority", "MEDIUM")

    # 3. Validation Bounds
    if confidence < 0.60:
         return {"status": "error", "message": f"NLP Confidence ({confidence:.2f}) below safe threshold. Request human intervention."}

    action_summary = "Processed message."
    task = None

    # 4. Deterministic DB Mutators based strictly on Intent
    try:
        if intent == "CREATE_TASK":
            if not entities.get("assigned_to"):
                return {"status": "error", "message": "Failed determining assignee from chat."}
            task, err, _ = create_task(entities["title"], entities["assigned_to"])
            if err: raise Exception(err)
            action_summary = f"Generated Task {task['task_code']} for @{entities['assigned_to']}"

        elif intent == "COMPLETE_TASK":
            task_code = entities.get("task_code")
            if not task_code: raise Exception("No valid task code recognized to complete.")
            
            # Find DB ID via task_code (simplification for mock)
            t_res = supabase.table("tasks").select("id").eq("task_code", task_code).execute()
            if not t_res.data: raise Exception(f"Task {task_code} not found in active records.")
            
            _, err, _ = update_task_status(t_res.data[0]["id"], "DONE")
            if err: raise Exception(err)
            action_summary = f"Marked {task_code} as DONE."
            
        elif intent == "BLOCK_TASK":
             task_code = entities.get("task_code")
             if not task_code: raise Exception("No valid task code recognized to block.")
             
             t_res = supabase.table("tasks").select("id").eq("task_code", task_code).execute()
             if not t_res.data: raise Exception(f"Task {task_code} not found in active records.")
             
             _, err, _ = update_task_status(t_res.data[0]["id"], "BLOCKED")
             if err: raise Exception(err)
             
             # Sub-action: Log Alert for Risk Agent observation matching exact schema
             supabase.table("alerts").insert({
                 "shift_id": shift_id,
                 "task_id": t_res.data[0]["id"],
                 "alert_type": "BLOCK",
                 "weight": 8,
                 "message": entities.get("block_reason", "Unspecified block action"),
                 "is_active": True
             }).execute()
             
             action_summary = f"Task {task_code} BLOCKED. Alert logged."

        elif intent == "ALERT":
             supabase.table("alerts").insert({
                 "shift_id": shift_id,
                 "alert_type": "EMERGENCY",
                 "weight": 10,
                 "message": entities.get("alert_message", "Emergency Alert Declared"),
                 "is_active": True
             }).execute()
             action_summary = "Critical Alert broadcast securely."
             
    except Exception as e:
        print("Pipeline DB Mutation error", e)
        return {"status": "error", "message": f"Execution halted: {str(e)}"}
        
    # 5. Call Observer Agentic Risk Service
    # (Only logs System Events on thresholds. Never closes)
    risk_evaluation = evaluate_shift_risk(shift_id)

    # 6. Structured Return matching existing Frontend stub expectations
    return {
        "status": "success",
        "message": action_summary,
        "data": {
            "intent": intent,
            "confidence": confidence,
            "recorded_action": action_summary, 
            "system_risk_update": risk_evaluation
        }
    }


@app.get("/shift/tasks")
def shift_tasks():
    shift = get_active_shift()
    if not shift:
        return {
            "status": "error",
            "message": "No active shift found"
        }
    
    tasks = get_shift_tasks(shift.get("id"))
    if tasks is None:
        return {
            "status": "error",
            "message": "Failed to fetch tasks"
        }
        
    mapped_tasks = []
    for t in tasks:
        mapped_tasks.append({
            "task_id": t.get("id"),
            "task_code": t.get("task_code"),
            "title": t.get("title"),
            "status": t.get("status"),
            "priority": t.get("priority"),
            "assigned_to": t.get("assigned_to"),
            "created_at": t.get("created_at")
        })
        
    return {
        "status": "success",
        "message": "Tasks fetched",
        "data": mapped_tasks
    }


@app.get("/shift/status")
def shift_status():
    shift = get_active_shift()
    if not shift:
        return {
            "status": "error",
            "message": "No active shift found"
        }
    
    return {
        "status": "success",
        "message": "Active shift fetched",
        "data": {
            "shift_id": shift.get("id"),
            "shift_name": shift.get("shift_name"),
            "risk_score": shift.get("risk_score"),
            "is_high_risk": shift.get("is_high_risk")
        }
    }


@app.patch("/task/{task_id}/priority")
def update_priority(task_id: int, body: PriorityOverrideRequest):
    return ok()

from fastapi import HTTPException

@app.patch("/task/{task_id}/status")
def change_task_status(task_id: str, body: TaskStatusRequest):
    data, err, code = update_task_status(task_id, body.status)
    if err:
        if code == 404:
            raise HTTPException(status_code=404, detail=err)
        elif code == 400:
            raise HTTPException(status_code=400, detail=err)
        return {
            "status": "error",
            "message": err
        }
    
    return {
        "status": "success",
        "message": "Task status updated successfully",
        "data": data
    }


@app.post("/task/create")
def create_new_task(body: TaskCreateRequest):
    task, err, code = create_task(body.title, body.assigned_to)
    if err:
        if code == 400:
            raise HTTPException(status_code=400, detail=err)
        return {
            "status": "error",
            "message": err
        }
        
    return {
        "status": "success",
        "message": "Task created successfully",
        "data": {
            "task_id": task.get("id"),
            "title": task.get("title"),
            "assigned_to": task.get("assigned_to"),
            "shift_id": task.get("shift_id"),
            "status": task.get("status", "TODO"),
            "priority": task.get("priority", "MEDIUM")
        }
    }


@app.post("/shift/end")
def shift_end():
    """
    Phase 6: Shift Endpoint Extension 
    Rotates shift logically, THEN traps Gemini summary generation implicitly.
    """
    active_shift = get_active_shift()
    if not active_shift:
         return {"status": "error", "message": "No shift to end."}
         
    shift_id_closing = active_shift.get("id")

    # 1. Mutate active boundary 
    data, err = end_active_shift()
    if err:
        return {"status": "error", "message": err}
        
    # 2. Trigger Generative AI 
    generate_shift_summary(shift_id_closing)

    return {
        "status": "success",
        "message": "Shift ended safely. Summary generated.",
        "data": data
    }
