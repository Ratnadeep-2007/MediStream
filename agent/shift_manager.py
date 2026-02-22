import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def finalize_shift(shift_id: str):
    """
    Shift Summary Finalization Engine
    Aggregates shift data, creates a summary, and securely closes the shift.
    """
    # 1️⃣ Fetch Shift
    shift_response = supabase.table("shifts") \
        .select("id, is_active, risk_score") \
        .eq("id", shift_id) \
        .single() \
        .execute()

    if not shift_response.data:
        print(f"Shift {shift_id} not found.")
        return

    shift = shift_response.data
    
    # Enforce it's not already finalized
    if not shift.get("is_active"):
        print(f"Shift {shift_id} is already finalized.")
        return

    final_risk_score = shift.get("risk_score", 0)

    # 2️⃣ Fetch Tasks
    tasks_response = supabase.table("tasks") \
        .select("status") \
        .eq("shift_id", shift_id) \
        .execute()

    tasks = tasks_response.data or []
    
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t["status"] == "DONE")
    blocked_tasks = sum(1 for t in tasks if t["status"] == "BLOCKED")
    pending_tasks = total_tasks - completed_tasks - blocked_tasks

    # 3️⃣ Fetch Alerts (Include inactive for historical aggregate)
    alerts_response = supabase.table("alerts") \
        .select("id") \
        .eq("shift_id", shift_id) \
        .execute()

    alerts_count = len(alerts_response.data or [])

    # 4️⃣ Insert Summary
    supabase.table("shift_summaries").insert({
        "shift_id": shift_id,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "blocked_tasks": blocked_tasks,
        "pending_tasks": pending_tasks,
        "alerts_count": alerts_count,
        "final_risk_score": final_risk_score
    }).execute()

    # 5️⃣ The AI provides the Summary. (It does NOT close the shift)
    print(f"Shift {shift_id} summary generated successfully.")
