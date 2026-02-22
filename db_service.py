from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def check_db_connection():
    try:
        response = supabase.table("shifts").select("id").limit(1).execute()
        return True
    except Exception as e:
        print("DB ERROR:", e)
        return False


def get_active_shift():
    try:
        response = supabase.table("shifts").select("*").eq("is_active", True).limit(1).execute()
        shifts = response.data
        if not shifts:
            return None
        return shifts[0]
    except Exception as e:
        print("DB ERROR:", e)
        return None


def get_shift_tasks(shift_id: str):
    try:
        response = supabase.table("tasks").select("*").eq("shift_id", shift_id).execute()
        tasks = response.data
        if not tasks:
            return []
        
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        
        def sort_key(task):
            prio = priority_order.get(task.get("priority", "LOW"), 4)
            created = task.get("created_at", "")
            return (prio, created)
            
        tasks.sort(key=sort_key)
        return tasks
    except Exception as e:
        print("DB ERROR:", e)
        return None


def end_active_shift():
    try:
        active_shift = get_active_shift()
        if not active_shift:
            return None, "No active shift found"

        response = supabase.table("shifts").select("*").order("sequence_order").execute()
        all_shifts = response.data
        if not all_shifts:
            return None, "No shifts available"

        current_id = active_shift.get("id")
        current_index = next((i for i, s in enumerate(all_shifts) if s.get("id") == current_id), -1)

        if current_index == -1:
            return None, "Active shift not found in ordered list"

        next_index = current_index + 1 if current_index + 1 < len(all_shifts) else 0
        next_shift = all_shifts[next_index]

        old_name = active_shift["name"]
        new_name = next_shift["name"]

        # Update database
        supabase.table("shifts").update({"is_active": False}).eq("id", current_id).execute()
        supabase.table("shifts").update({"is_active": True}).eq("id", next_shift.get("id")).execute()


        # Insert system message
        message = {
            "shift_id": next_shift.get("id"),
            "sender_id": None,
            "message_text": f"Shift changed from {old_name} to {new_name}",
            "message_type": "SYSTEM"
        }
        supabase.table("chat_messages").insert(message).execute()

        return {"previous_shift": old_name, "current_shift": new_name}, None
    except Exception as e:
        print("DB ERROR:", e)
        return None, "Internal server error"

from datetime import datetime, timezone

def update_task_status(task_id: str, new_status: str):
    try:
        response = supabase.table("tasks").select("*").eq("id", task_id).execute()
        tasks = response.data
        if not tasks:
            return None, "Task not found", 404
        
        task = tasks[0]
        current_status = task.get("status")
        
        if current_status == "DONE":
            return None, "Cannot modify a completed task", 400
            
        update_data = {"status": new_status}
        if new_status == "DONE":
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
        else:
            update_data["completed_at"] = None
            
        supabase.table("tasks").update(update_data).eq("id", task_id).execute()
        
        return {"task_id": task_id, "previous_status": current_status, "current_status": new_status}, None, 200
        
    except Exception as e:
        print("DB ERROR:", e)
def create_task(title: str, assigned_to: str):
    try:
        active_shift = supabase.table("shifts") \
            .select("id") \
            .eq("is_active", True) \
            .limit(1) \
            .execute()

        if not active_shift.data:
            return None, "No active shift", 400

        active_shift_id = active_shift.data[0]["id"]

        creator_id = "235b4451-e7f9-4dc6-9ffd-3bf8ce30ca9b"

        insert_response = supabase.table("tasks").insert({
            "title": title,
            "shift_id": active_shift_id,
            "created_by": creator_id,
            "assigned_to": assigned_to,
            "status": "TODO",
            "priority": "MEDIUM"
        }).execute()

        inserted_data = insert_response.data
        if not inserted_data:
            return None, "Failed to insert task", 500
            
        return inserted_data[0], None, 201
        
    except Exception as e:
        print("CREATE TASK ERROR:", str(e))
        return None, str(e), 500
