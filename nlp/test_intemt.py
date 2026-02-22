from transformers import pipeline

# Load local model
intent_classifier = pipeline(
    "text-classification",
    model="intent_distilbert",
    tokenizer="intent_distilbert",
    return_all_scores=True
)

CONFIDENCE_THRESHOLD = 0.75

def predict_intent(text):
    outputs = intent_classifier(text)
    best = max(outputs, key=lambda x: x["score"])

    if best["score"] < CONFIDENCE_THRESHOLD:
        return {"intent": "INVALID_COMMAND", "confidence": best["score"]}

    return {"intent": best["label"], "confidence": best["score"]}


# Test samples
tests = [
    "Prepare discharge summary for ward 5",
    "T-1023 completed",
    "T-2001 waiting for lab report",
    "Rapid response required",
    "Okay noted"
]

for t in tests:
    print(f"\nInput: {t}")
    print("Prediction:", predict_intent(t))
    