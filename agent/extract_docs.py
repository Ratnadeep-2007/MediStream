import os
import docx

RESOURCE_DIR = r"e:\Skills\Webstack\worksight1\MedStram\resources"

def extract_all():
    files = [f for f in os.listdir(RESOURCE_DIR) if f.endswith(".docx")]
    for filename in files:
        filepath = os.path.join(RESOURCE_DIR, filename)
        doc = docx.Document(filepath)
        text = "\n".join([p.text for p in doc.paragraphs])
        
        txt_filename = filename.replace(".docx", ".txt")
        txt_filepath = os.path.join(RESOURCE_DIR, txt_filename)
        with open(txt_filepath, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Extracted: {txt_filename}")

if __name__ == "__main__":
    extract_all()
