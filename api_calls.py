# api_calls.py

import requests
import base64

def call_llm_format_text(page_text, page_number):
    """
    Calls the LLM API to reformat the provided page text.
    Returns the formatted text, or the original text in case of failure.
    """
    preface = 'Data : \n'
    system_message = (
        "You are a text formatting assistant. Your task is to reformat the provided page text into clearly defined sections. "
        "Please ensure your response contains the entire content, formatted perfectly with no extra commentary."
    )
    user_message = preface + page_text
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]
    try:
        response = requests.post("http://192.168.1.1:5050/generate_llama",
                                 json={
                                     "messages": messages,
                                     "max_new_tokens": 4000,
                                     "temperature": 1,
                                     "top_p": 0.9
                                 })
        if response.ok:
            result = response.json()
            formatted_text = result.get('assistant', {}).get('content', page_text)
            return formatted_text
        else:
            print(f"LLM call failed for page {page_number}: HTTP {response.status_code}")
            return page_text
    except Exception as e:
        print(f"Error during LLM call for page {page_number}: {e}")
        return page_text

def call_vision_api_for_image(image_filename, page_number, img_index, images_folder):
    """
    Calls the Vision API for image analysis and saves the analysis result to a text file.
    """
    try:
        with open(image_filename, "rb") as img_file:
            img_bytes = img_file.read()
        encoded_image = base64.b64encode(img_bytes).decode("utf-8")
        
        vision_response = requests.post(
            "http://192.168.1.1:1234/process_pdf_imagery",
            data=encoded_image
        )
        if vision_response.ok:
            vision_result = vision_response.json()
            analysis_filename = f"{images_folder}/page_{page_number}_img_{img_index}_analysis.txt"
            with open(analysis_filename, "w", encoding="utf-8") as analysis_file:
                analysis_file.write("Unconditional Caption:\n")
                analysis_file.write(vision_result.get("unconditional_caption", ""))
                analysis_file.write("\n\nPDF Domain Classification:\n")
                for label, score in vision_result.get("pdf_classification", {}).items():
                    analysis_file.write(f"{label}: {score:.4f}\n")
                analysis_file.write("\nVILT Domain Q&A Results:\n")
                for label, score in vision_result.get("vilt_results", []):
                    analysis_file.write(f"{label}: {score:.4f}\n")
        else:
            print(f"Vision API call failed for image {page_number}_{img_index}: HTTP {vision_response.status_code}")
    except Exception as e:
        print(f"Error calling Vision API for image {page_number}_{img_index}: {e}")
