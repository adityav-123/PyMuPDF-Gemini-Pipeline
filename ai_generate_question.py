import json
import requests
import base64
import os
import random

DATA_PATH = os.path.join('final_output', 'questions_final.json')
USE_QUESTION_NUM = 1  

def read_question_file(filepath):
    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"ERROR: File '{filepath}' not found. Make sure extraction is complete.")
        return None
    except json.JSONDecodeError:
        print(f"ERROR: JSON decode failed for '{filepath}'.")
        return None

def pick_question(questions_data, number):
    if number == 'random':
        return random.choice(questions_data)
    
    for item in questions_data:
        if item.get("question_number") == number:
            return item

    print(f"ERROR: Could not locate question number {number}.")
    return None

def image_to_base64(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"Notice: Image not found at '{path}', skipping.")
        return None

def create_api_input(selected_q):
    question_prompt = f"""You're a skilled math educator for Grade 1 students.
Using the original question below, generate one new practice question:

Rules:
- Stick to the same concept.
- Change the numbers, visual elements, or scenario.
- Use four options: [A], [B], [C], [D].
- Finish the output with the correct option like: Ans: [X]

---
ORIGINAL QUESTION TEXT:
{selected_q['question_text']}
---
"""
    image_blocks = []

    for img_path in selected_q.get('question_images', []):
        base64_data = image_to_base64(img_path)
        if base64_data:
            image_blocks.append({
                "inline_data": {"mime_type": "image/png", "data": base64_data}
            })

    for opt_key, opt_value in selected_q.get('options', {}).items():
        if opt_value.get('type') == 'image':
            for opt_img in opt_value.get('content', []):
                base64_data = image_to_base64(opt_img)
                if base64_data:
                    image_blocks.append({
                        "inline_data": {"mime_type": "image/png", "data": base64_data}
                    })

    return {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": question_prompt},
                *image_blocks
            ]
        }]
    }

def query_gemini(api_data):
    API_KEY = "" #Didnt enter my API Key Cuz it was a common one between some of my projects 
    URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
    HEADERS = {'Content-Type': 'application/json'}

    print("Sending data to Gemini... Please wait.")
    
    try:
        res = requests.post(URL, headers=HEADERS, json=api_data)
        res.raise_for_status()
        result = res.json()

        if "candidates" in result and result["candidates"]:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return f"Success but empty response:\n{json.dumps(result, indent=2)}"

    except requests.exceptions.RequestException as err:
        return f"Request failed: {err}"

def run_question_creator():
    print("=== AI Practice Question Generator ===")

    all_questions = read_question_file(DATA_PATH)
    if not all_questions:
        return

    chosen_q = pick_question(all_questions, USE_QUESTION_NUM)
    if not chosen_q:
        return

    print(f"\nUsing base Question #{chosen_q['question_number']}:")
    print("--------------------------------------")
    print(chosen_q['question_text'])
    print("--------------------------------------\n")

    gemini_input = create_api_input(chosen_q)
    ai_output = query_gemini(gemini_input)

    print("\n✅ Generated Output:")
    print("======================================")
    print(ai_output)
    print("======================================")

if __name__ == "__main__":
    run_question_creator()
