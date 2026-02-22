from transformers import pipeline

priority_classifier = pipeline(
    "text-classification",
    model="priority_distilbert",
    tokenizer="priority_distilbert",
    return_all_scores=True
)

def predict_priority(text):
    outputs = priority_classifier(text)
    best = max(outputs, key=lambda x: x["score"])
    return {"priority": best["label"], "confidence": best["score"]}


# Test samples
tests = [
    "Emergency surgery required immediately",
    "Prepare discharge summary for ward 5",
    "Update attendance sheet",
    "Urgent ICU monitoring required"
]

for t in tests:
    print(f"\nInput: {t}")
    print("Prediction:", predict_priority(t))