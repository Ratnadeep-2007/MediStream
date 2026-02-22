from agent_service import evaluate_shift_risk, PRIORITY_WEIGHTS, STATUS_WEIGHTS, RISK_THRESHOLD
import agent_service

# Mock Supabase
class MockQuery:
    def __init__(self, data):
        self._data = data
        self._eq_filters = {}
        
    def select(self, *args, **kwargs):
        return self
        
    def eq(self, key, value):
        self._eq_filters[key] = value
        return self
        
    def single(self):
        self._single = True
        return self
        
    def execute(self):
        # Apply filters
        result = self._data
        for k, v in self._eq_filters.items():
            result = [row for row in result if row.get(k) == v]
        
        # for single()
        if hasattr(self, '_single') and self._single:
            return type('Response', (), {'data': result[0] if result else None})()
            
        return type('Response', (), {'data': result})()
        
    def insert(self, data):
        self._data.append(data)
        return self
        
    def update(self, data):
        for row in self._data:
            match = True
            for k, v in self._eq_filters.items():
                if row.get(k) != v:
                    match = False
                    break
            if match:
                row.update(data)
        return self

class MockTable:
    def __init__(self, data):
        self.data = data
        
    def select(self, *args, **kwargs):
        return MockQuery(self.data).select(*args, **kwargs)
        
    def insert(self, data):
        return MockQuery(self.data).insert(data)
        
    def update(self, data):
        return MockQuery(self.data).update(data)

class MockSupabase:
    def __init__(self):
        self.db = {
            "shifts": [],
            "tasks": [],
            "alerts": [],
            "chat_messages": []
        }
        
    def table(self, name):
        return MockTable(self.db[name])

# Inject Mock
mock_db = MockSupabase()
agent_service.supabase = mock_db

# ---------------------------------------------------------
# TEST SETUP
# ---------------------------------------------------------

shift_id = "test-shift-1"

mock_db.db["shifts"].append({
    "id": shift_id,
    "name": "Test Shift",
    "is_active": True,
    "is_high_risk": False,
    "risk_score": 0
})

task_1_id = "t1"
task_2_id = "t2"
task_3_id = "t3"

mock_db.db["tasks"].extend([
    {"id": task_1_id, "shift_id": shift_id, "priority": "CRITICAL", "status": "TODO"},
    {"id": task_2_id, "shift_id": shift_id, "priority": "CRITICAL", "status": "TODO"},
    {"id": task_3_id, "shift_id": shift_id, "priority": "CRITICAL", "status": "TODO"}
])

print("\n--- TEST 1: 3 CRITICAL TODOs ---")
evaluate_shift_risk(shift_id)
shift = mock_db.db["shifts"][0]
print(f"Risk Score (Expected 15): {shift['risk_score']}")
print(f"Is High Risk (Expected False): {shift['is_high_risk']}")

print("\n--- TEST 2: Block 1 CRITICAL task (Force Escalation) ---")
mock_db.db["tasks"][2]["status"] = "BLOCKED"
evaluate_shift_risk(shift_id)
shift = mock_db.db["shifts"][0]
messages = mock_db.db["chat_messages"]

print(f"Risk Score (Expected 20): {shift['risk_score']}")
print(f"Is High Risk (Expected True): {shift['is_high_risk']}")
print(f"Total SYSTEM messages (Expected 1): {len(messages)}")
if messages:
    print(f"Last Message: {messages[-1]['message_text']}")


print("\n--- TEST 3: FSM Guard (No duplicate spam) ---")
# Update a task without changing risk (e.g. TODO -> IN_PROGRESS, weight stays 1)
mock_db.db["tasks"][0]["status"] = "IN_PROGRESS"
evaluate_shift_risk(shift_id)
shift = mock_db.db["shifts"][0]
messages = mock_db.db["chat_messages"]

print(f"Risk Score (Expected 20): {shift['risk_score']}")
print(f"Is High Risk (Expected True): {shift['is_high_risk']}")
print(f"Total SYSTEM messages STILL (Expected 1): {len(messages)}")


print("\n--- TEST 4: Normalization (Tasks DONE, Alerts deactivated) ---")

# First, test alert deactivation requirement explicitly:
mock_db.db["alerts"].append({
    "id": "a1", "shift_id": shift_id, "task_id": task_1_id, "weight": 5, "is_active": True
})

# Simulate the router code setting task status to DONE and automatically disabling alerts
def mock_router_mark_done(task_id):
    for t in mock_db.db["tasks"]:
        if t["id"] == task_id:
            t["status"] = "DONE"
    # THE REQUIRED ALERT DEACTIVATION
    mock_db.db["alerts"][0]["is_active"] = False
    
    evaluate_shift_risk(shift_id)

mock_router_mark_done(task_1_id)
mock_router_mark_done(task_2_id)
mock_router_mark_done(task_3_id)

shift = mock_db.db["shifts"][0]
messages = mock_db.db["chat_messages"]
alerts = mock_db.db["alerts"]

print(f"Risk Score (Expected 0): {shift['risk_score']}")
print(f"Is High Risk (Expected False): {shift['is_high_risk']}")
print(f"Total SYSTEM messages (Expected 2): {len(messages)}")
print(f"System Messages:")
for m in messages:
    print(f" - {m['message_text']}")
print(f"Alert 1 is_active (Expected False): {alerts[0]['is_active']}")
