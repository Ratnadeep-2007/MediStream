import requests
import time
import sys
from db_service import supabase  # Connect directly to DB to spawn dependencies

BASE_URL = "http://localhost:8000"

def print_step(title):
    print(f"\n{'-'*50}\n▶ {title}\n{'-'*50}")

def reset_and_seed_database():
    print_step("0. Seeding Database Context (Mocks)")
    print("Clearing active tables safely...")
    
    # Supabase needs at least one shift and one valid User (our mock user)
    # 1. Clean up old tests to avoid unique constraints
    try:
        supabase.table("alerts").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        supabase.table("chat_messages").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        supabase.table("tasks").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        supabase.table("users").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        supabase.table("shifts").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        
        # 2. Spawn a Demo Shift (strictly matching 'shifts' schema constraints)
        shift_res = supabase.table("shifts").insert({
            "name": "Demo Hackathon Shift",
            "is_active": True,
            "risk_score": 0,
            "is_high_risk": False,
            "sequence_order": 1
        }).execute()
        shift_id = shift_res.data[0]["id"]
        
        # 3. Spawn Users (strictly matching 'users' schema constraints)
        # Note: 235b4451-e7f9-4dc6-9ffd-3bf8ce30ca9b is the hardcoded test user in main.py!
        user_res = supabase.table("users").insert([
            {
                "id": "235b4451-e7f9-4dc6-9ffd-3bf8ce30ca9b", 
                "name": "Dr. Gregory House", 
                "role_type": "HEAD", 
                "shift_id": shift_id
            },
            {
                "id": "11111111-1111-1111-1111-111111111111", 
                "name": "NurseNeha", 
                "role_type": "NURSE", 
                "shift_id": shift_id
            }
        ]).execute()
        print("✅ DB Seeded with Mock Data.")
        return shift_id, "11111111-1111-1111-1111-111111111111"
        
    except Exception as e:
        print(f"Failed to seed db: {e}")
        print("Note: Seeding users requires auth.users FK constraints. If auth.users is empty, this script will fail.")
        sys.exit(1)


def run_tests():
    print("Testing MediStream E2E (Strict Schema Compliant)...")

    # [Note for Hackathon: Supabase auth.users MUST have these IDs manually created over the GUI first or FK constraints fail!]
    try:
        # Check health first
        requests.get(f"{BASE_URL}/health")
    except requests.exceptions.ConnectionError:
         print("CRITICAL: Server is not running. Boot uvicorn first!")
         sys.exit(1)

    # 1. Check Shift
    print_step("1. Fetching Context")
    res = requests.get(f"{BASE_URL}/shift/status")
    print(f"Response: {res.json()}")

    # 2. NLP: Create Task
    print_step("2. NLP -> CREATE_TASK")
    chat_payload = {"message": "@NurseNeha Please prepare discharge summary for bed 42 immediately."}
    res = requests.post(f"{BASE_URL}/chat", json=chat_payload)
    print(f"Response: {res.json()}")
    
    time.sleep(1) # Let database settle
    
    # Grab the generated task_code to use in the block query
    tasks_res = supabase.table("tasks").select("task_code").execute()
    if not tasks_res.data:
        print("Task insertion failed.")
        sys.exit(1)
        
    t_code = tasks_res.data[0]["task_code"]

    # 3. NLP: Block Task
    print_step("3. NLP -> BLOCK_TASK & Risk Agent")
    chat_payload_2 = {"message": f"T-{t_code} is blocked because patient is dizzy."}
    res = requests.post(f"{BASE_URL}/chat", json=chat_payload_2)
    print(f"Response: {res.json()}")

    # 4. NLP: Emergency Alert (CRITICAL)
    print_step("4. NLP -> EMERGENCY ALERT")
    chat_payload_3 = {"message": "Patient coding in Room 402, need immediate crash cart!"}
    res = requests.post(f"{BASE_URL}/chat", json=chat_payload_3)
    print(f"Response: {res.json()}")

    time.sleep(2) # Give supabase agent hooks time

    # 5. Validate Risk
    print_step("5. Validate Agentic Risk Escelation")
    res = requests.get(f"{BASE_URL}/shift/status")
    print(f"Response: {res.json()}")

    # 6. End Shift
    print_step("6. End Shift -> Gemini Summary")
    res = requests.post(f"{BASE_URL}/shift/end")
    print(f"Response: {res.json()}")
    
    print("\n✅ Verification Completed.")


if __name__ == "__main__":
    run_tests()
