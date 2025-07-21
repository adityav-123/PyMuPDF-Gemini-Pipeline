import fitz  # PyMuPDF
import os
import json
import re

def extract_elements_from_pdf(pdf_doc, output_path):
    extracted_items = []
    IMAGE_SKIP_THRESHOLD = 0.3

    for page_index in range(len(pdf_doc)):
        current_page = pdf_doc.load_page(page_index)
        page_size = current_page.rect.width * current_page.rect.height
        content_blocks = current_page.get_text("dict")["blocks"]

        for block in content_blocks:
            if block['type'] == 0:
                for line in block["lines"]:
                    line_content = "".join(span["text"] for span in line["spans"]).strip()
                    if line_content:
                        extracted_items.append({
                            "type": "text",
                            "page": page_index,
                            "bbox": line["bbox"],
                            "content": line_content
                        })

        images_on_page = current_page.get_images(full=True)
        for idx, img_info in enumerate(images_on_page):
            try:
                image_bbox = current_page.get_image_bbox(img_info)
                image_area = image_bbox.width * image_bbox.height
                if image_area / page_size > IMAGE_SKIP_THRESHOLD:
                    continue

                xref_id = img_info[0]
                image_data = pdf_doc.extract_image(xref_id)
                img_bytes = image_data["image"]
                img_ext = image_data["ext"]
                img_filename = f"page{page_index + 1}_img{idx + 1}.{img_ext}"
                img_output_path = os.path.join(output_path, img_filename)

                with open(img_output_path, "wb") as img_out_file:
                    img_out_file.write(img_bytes)

                extracted_items.append({
                    "type": "image",
                    "page": page_index,
                    "bbox": image_bbox,
                    "content": img_output_path
                })

            except Exception as err:
                print(f"Warning: Could not process image {idx} on page {page_index + 1}. Error: {err}")

    extracted_items.sort(key=lambda el: (el["page"], el["bbox"][1]))
    return extracted_items


def build_question_objects(extracted_items):
    question_list = []
    current_q = None

    for item in extracted_items:
        text = item["content"]
        number_match = re.match(r"^\s*(\d+)\.", text)

        if number_match:
            if current_q:
                current_q["question_text"] = "\n".join(current_q["question_text"]).strip()
                question_list.append(current_q)

            q_num = int(number_match.group(1))
            current_q = {
                "question_number": q_num,
                "question_text": [text],
                "images": [],
                "options": {},
                "answer": ""
            }
        elif current_q:
            if item["type"] == "image":
                current_q["images"].append(text)
            elif item["type"] == "text":
                answer_match = re.search(r"Ans\s*\.?\s*\[([A-D])\]", text)
                header_check = re.search(r'SECTION|ACHIEVER', text, re.IGNORECASE)

                if answer_match:
                    current_q["answer"] = answer_match.group(1)
                elif header_check:
                    pass
                elif not re.match(r"^\d+$", text) and not re.match(r"^\[[A-D]\]$", text):
                    current_q["question_text"].append(text)

    if current_q:
        current_q["question_text"] = "\n".join(current_q["question_text"]).strip()
        question_list.append(current_q)

    return question_list


def run_parser():
    input_pdf_path = "sample.pdf"
    export_dir = "final_output"
    output_json_path = os.path.join(export_dir, "questions_final.json")

    os.makedirs(export_dir, exist_ok=True)

    try:
        pdf_doc = fitz.open(input_pdf_path)
    except Exception as load_err:
        print(f"FATAL: Could not open PDF file at '{input_pdf_path}'. Error: {load_err}")
        return

    print("Step 1: Pulling all text and image elements...")
    elements = extract_elements_from_pdf(pdf_doc, export_dir)
    pdf_doc.close()
    print(f"Extracted {len(elements)} elements from the document.")

    print("Step 2: Creating structured questions from elements...")
    questions = build_question_objects(elements)

    if questions:
        print("\n--- PARSING COMPLETE ---")

        with open(output_json_path, 'w') as json_file:
            json.dump(questions, json_file, indent=4)

        print(f"\nSuccessfully extracted {len(questions)} questions.")
        print(f"Images saved in '{export_dir}'")
        print(f"Structured data written to: {output_json_path}")

        print("\n--- FIRST QUESTION PREVIEW ---")
        print(json.dumps(questions[0], indent=4))
        print("\n--- LAST QUESTION PREVIEW ---")
        print(json.dumps(questions[-1], indent=4))


if __name__ == "__main__":
    run_parser()
