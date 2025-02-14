# pdf_parser.py

import os
import re
from api_calls import call_llm_format_text, call_vision_api_for_image

def extract_page_text(page, page_number, folder_path):
    """
    Extracts text from the PDF page, calls the LLM API to format it,
    and saves the formatted text to a .txt file.
    """
    page_text = page.get_text("text").strip()
    # --- LLM CALL: reformat page text ---
    formatted_text = call_llm_format_text(page_text, page_number)
    
    # Write the (formatted) page text to a file
    text_filename = os.path.join(folder_path, f"page_{page_number}.txt")
    with open(text_filename, "w", encoding="utf-8") as f:
        f.write(formatted_text)
    
    return formatted_text

def process_page_images(page, page_number, doc, folder_path, images_folder):
    """
    Processes each image found on the page:
    - Saves the image file.
    - Calls the Vision API for image analysis.
    """
    for img_index, img in enumerate(page.get_images(full=True), start=1):
        xref = img[0]
        base_image = doc.extract_image(xref)
        image_filename = os.path.join(images_folder, f"page_{page_number}_img_{img_index}.{base_image['ext']}")
        with open(image_filename, "wb") as img_file:
            img_file.write(base_image["image"])
        
        # --- CALL VISION API: process image ---
        call_vision_api_for_image(image_filename, page_number, img_index, images_folder)

def extract_measurements(page_text):
    """
    Extracts explicit measurements (in sq m, mm, and m) and standalone numbers from the page text.
    Returns a list of measurement records and a totals dictionary.
    """
    explicit_sq_m_matches = re.findall(r"([\d.,]+)\s*sq\s*m", page_text, flags=re.I)
    explicit_mm_matches = re.findall(r"([\d.,]+)\s*mm", page_text, flags=re.I)
    explicit_m_matches  = re.findall(r"([\d.,]+)\s*m(?!m)", page_text, flags=re.I)
    
    explicit_sq_m = [float(m.replace(",", "")) for m in explicit_sq_m_matches if m]
    explicit_mm = []
    for m in explicit_mm_matches:
        try:
            explicit_mm.append(float(m.replace(",", "")))
        except Exception:
            pass
    explicit_m = []
    for m in explicit_m_matches:
        try:
            explicit_m.append(float(m.replace(",", "")))
        except Exception:
            pass
    
    # Extract standalone numbers
    all_numbers = re.findall(r"\b\d+(?:[.,]\d+)?\b", page_text)
    standalone_numbers = []
    explicit_sq_m_str = [m.replace(",", "") for m in explicit_sq_m_matches]
    explicit_mm_str = [m.replace(",", "") for m in explicit_mm_matches]
    explicit_m_str  = [m.replace(",", "") for m in explicit_m_matches]
    for num in all_numbers:
        norm_num = num.replace(",", "")
        if norm_num in explicit_sq_m_str or norm_num in explicit_mm_str or norm_num in explicit_m_str:
            continue
        try:
            standalone_numbers.append(float(norm_num))
        except Exception:
            pass
    
    assumed_mm = []
    unknown_values = []
    for value in standalone_numbers:
        if value > 99999999999:
            assumed_mm.append(value)
        else:
            unknown_values.append(value)
    
    measurements_records = []
    for value in explicit_sq_m:
        measurements_records.append({"Measurement Value": value, "Unit": "sq m", "Source": "explicit"})
    for value in explicit_mm:
        measurements_records.append({"Measurement Value": value, "Unit": "mm", "Source": "explicit"})
    for value in explicit_m:
        measurements_records.append({"Measurement Value": value, "Unit": "m", "Source": "explicit"})
    for value in assumed_mm:
        measurements_records.append({"Measurement Value": value, "Unit": "mm (assumed)", "Source": "assumed"})
    for value in unknown_values:
        measurements_records.append({"Measurement Value": value, "Unit": "unknown (confirm)", "Source": "unknown"})
    
    total_sq_m   = sum(explicit_sq_m)
    total_mm     = sum(explicit_mm) + sum(assumed_mm)
    total_m      = sum(explicit_m)
    total_unknown = sum(unknown_values)
    
    totals = {
        "Total sq m": total_sq_m,
        "Total mm": total_mm,
        "Total m": total_m,
        "Total unknown": total_unknown
    }
    return measurements_records, totals

def extract_annotations(page, page_number):
    """
    Extracts annotation records from the PDF page.
    """
    annotations_records = []
    annots = page.annots()
    if annots:
        for annot in annots:
            annot_type = annot.type[1] if annot.type else None
            annotations_records.append({
                "Page": page_number,
                "Annotation Type": annot_type,
                "Content": annot.info.get("content", "")
            })
    return annotations_records

def extract_levels(page_text, page_number):
    """
    Extracts lines from the page text that contain 'FFL' or 'Level'.
    """
    levels_records = []
    for line in page_text.splitlines():
        if re.search(r"\b(FFL|Level)\b", line, flags=re.I):
            levels_records.append({"Page": page_number, "Line": line.strip()})
    return levels_records
