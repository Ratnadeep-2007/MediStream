import os
from engine import MediStreamNLP

def run_tests():
    print("Loading MediStreamNLP Engine...")
    nlp = MediStreamNLP()
    
    test_cases = [

    # ---------------------------
    # VALID CREATE_TASK
    # ---------------------------
    "Create task for @Neha to check the patient in Room 101",
    "@Amit prepare discharge summary for ward 5",
    "Assign @Riya to monitor ICU patient 12",
    "@Karan update medication chart for bed 8",
    "Please ask @Meena to verify lab reports",

    # ---------------------------
    # VALID COMPLETE_TASK
    # ---------------------------
    "T-1023 is completed",
    "T-2001 completed",
    "Complete T-3099",
    "T-4500 done",
    "T-9999 has been completed",

    # ---------------------------
    # VALID BLOCK_TASK
    # ---------------------------
    "T-1102 waiting for lab report",
    "T-2100 blocked due to equipment failure",
    "T-3301 cannot proceed due to missing files",
    "T-7788 is waiting for doctor approval",
    "T-8899 delayed because oxygen supply is low",

    # ---------------------------
    # VALID ALERT
    # ---------------------------
    "Emergency in ICU",
    "Code blue in ward 5",
    "Cardiac arrest in ICU",
    "Rapid response required immediately",
    "Patient collapse in Room 202",

    # ---------------------------
    # INVALID CASES
    # ---------------------------
    "Just some random text",
    "Hello everyone",
    "Okay noted",
    "This is unrelated to any task",
    "CREATE_TASK but no mention",

    # ---------------------------
    # EDGE CASES
    # ---------------------------
    "t-1023 completed",                      # lowercase task code
    "@Neha T-1023 completed",                # mixed intent style
    "Complete task",                         # no code
    "@Neha please do this",                  # vague create
    "emergency",                             # single keyword alert
    "Code Blue",                             # case variation
    "T-1234",                                # code only
    "@Amit",                                 # mention only
    "T-5678 blocked",                        # short block
    "Prepare report for ward 3"              # no mention create
]
    
    print("\n--- Running Tests ---")
    for text in test_cases:
        print(f"\nMessage: {text}")
        result = nlp.process_message(text)
        print(f"Result: {result}")

if __name__ == "__main__":
    run_tests()
