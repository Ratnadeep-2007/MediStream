import os
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

from transformers import pipeline

priority_classifier = pipeline(
    "text-classification",
    model="priority_distilbert",
    tokenizer="priority_distilbert",
    return_all_scores=True
)

def predict_priority(text):
    outputs = priority_classifier(text)
    # outputs is list of list of dicts
    scores = outputs[0] if isinstance(outputs[0], list) else outputs
    best = max(scores, key=lambda x: x["score"])
    return {"priority": best["label"], "confidence": round(best["score"], 4)}

tests = [
    "Emergency surgery required immediately",
    "Prepare discharge summary for ward 5",
    "Update attendance sheet",
    "Urgent ICU monitoring required"
]

results = []
for t in tests:
    pred = predict_priority(t)
    line = f"Input: {t}\nPrediction: {pred}\n"
    results.append(line)

output = "\n".join(results)
print(output)

with open("priority_results.txt", "w") as f:
    f.write(output)
print("Results also saved to priority_results.txt")
