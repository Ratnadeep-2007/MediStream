import os
import json
from db_service import supabase

PRIORITY_WEIGHTS = {"LOW": 1, "MEDIUM": 3, "HIGH": 6, "CRITICAL": 10}
STATUS_WEIGHTS = {"TODO": 1, "IN_PROGRESS": 0, "BLOCKED": 15, "DONE": 0}

RISK_THRESHOLD = 8

def evaluate_shift_risk(shift_id: str) -> dict:
    """
    Evaluates risk and ONLY logs escalation exactly as demanded by Phase 7 and 12(C).
    DOES NOT CLOSE THE SHIFT OR MUTATE TASKS.
    Returns: {"risk": int, "escalated": bool}
    """
    try:
        # Fetch actual tasks
        tasks_response = supabase.table("tasks").select("*").eq("shift_id", shift_id).execute()
        tasks = tasks_response.data
        if not tasks:
            return {"risk": 0, "escalated": False}

        # Fetch active alerts
        alerts_response = supabase.table("alerts").select("*").eq("shift_id", shift_id).eq("is_active", True).execute()
        alerts = alerts_response.data
        
        # Calculate Risk deterministically
        task_risk = sum(
            PRIORITY_WEIGHTS.get(t.get("priority", "LOW"), 1) + STATUS_WEIGHTS.get(t.get("status", "TODO"), 0)
            for t in tasks
        )
        alert_risk = sum(10 for _ in alerts)
        
        base_risk = task_risk + alert_risk
        risk_score = min(10, base_risk // 10)

        escalated = False

        if risk_score >= RISK_THRESHOLD:
            # Phase 7 & Phase 12(C): Only Log Escelation! Do NOT close the shift!
            print(f"Shift {shift_id} crossed threshold (Risk {risk_score}). System event logged.")
            supabase.table("chat_messages").insert({
                "shift_id": shift_id,
                "sender_id": None,
                "message_text": f"Warning! Operational Risk threshold breached! Score: {risk_score}/10.",
                "message_type": "SYSTEM" 
            }).execute()
            escalated = True

        # Update the live score exactly once
        supabase.table("shifts").update({
            "risk_score": risk_score,
            "is_high_risk": escalated
        }).eq("id", shift_id).execute()

        return {
            "risk": risk_score,
            "escalated": escalated
        }

    except Exception as e:
        print(f"RISK AGENT ERROR: {str(e)}")
        return {"risk": 0, "escalated": False}
