import os
from db_service import supabase
import google.generativeai as genai

# Configure Gemini once globally
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
generation_config = {
  "temperature": 0.2, # Low temperature for factual reporting
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 1024,
  "response_mime_type": "text/plain",
}

def generate_shift_summary(shift_id: str) -> None:
    """
    Phase 6: Shift End Integration (Gemini Component)
    Fetches shift metrics, asks Gemini to summarize strictly based on numbers,
    and saves it to the DB. Does NOT crash if Gemini fails.
    """
    try:
        # Fetch Shift Data
        shift_response = supabase.table("shifts").select("*").eq("id", shift_id).execute()
        shift = shift_response.data[0] if shift_response.data else None
        
        if not shift:
            print("Summary Error: Shift not found")
            return

        # Fetch Tasks
        tasks_response = supabase.table("tasks").select("status").eq("shift_id", shift_id).execute()
        tasks = tasks_response.data or []
        
        # Calculate Metrics
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.get("status") == "DONE")
        blocked_tasks = sum(1 for t in tasks if t.get("status") == "BLOCKED")
        pending_tasks = total_tasks - completed_tasks - blocked_tasks

        # Fetch Active Alerts
        alerts_response = supabase.table("alerts").select("id").eq("shift_id", shift_id).eq("is_active", True).execute()
        alerts_count = len(alerts_response.data or [])

        risk_score = shift.get("risk_score", 0)

        prompt = f"""You are a hospital operations analyst.
        
Shift Summary Data:
Total Tasks: {total_tasks}
Completed Tasks: {completed_tasks}
Blocked Tasks: {blocked_tasks}
Pending Tasks: {pending_tasks}
Active Alerts: {alerts_count}
Final Risk Score: {risk_score}/10

Write a concise 3-sentence professional shift performance summary.
Do not invent data.
Do not speculate.
Only describe based on numbers provided."""

        ai_summary = ""
        # Wrap Gemini call in error handler so it doesn't crash the server shift end
        try:
            if not GEMINI_API_KEY:
                raise ValueError("Missing Gemini API Key in backend environment.")
                
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                generation_config=generation_config,
            )
            chat_session = model.start_chat(history=[])
            response = chat_session.send_message(prompt)
            ai_summary = response.text.strip()
            print(f"Shift {shift_id} Gemini summary successfully generated.")
        except Exception as e:
            print(f"Gemini API failure: {str(e)}")
            ai_summary = "AI summary unavailable due to generation error."

        # Insert final summary into database
        supabase.table("shift_summaries").insert({
            "shift_id": shift_id,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "blocked_tasks": blocked_tasks,
            "alerts_raised": alerts_count,
            "final_risk_score": risk_score,
            "ai_summary": ai_summary
        }).execute()
        
    except Exception as e:
        print(f"Summary Service DB Error: {str(e)}")
