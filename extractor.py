# extractor.py

import fitz
import pandas as pd
import os
import glob
from datetime import datetime

from pdf_parser import (
    extract_page_text,
    process_page_images,
    extract_measurements,
    extract_annotations,
    extract_levels
)

def extract_pdf_data(pdf_path, output_dir):
    # Set up folders and filenames
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    folder_path = os.path.join(output_dir, pdf_name)
    os.makedirs(folder_path, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"extracted_data_{timestamp}.xlsx"
    full_excel_path = os.path.join(folder_path, excel_filename)
    
    images_folder = os.path.join(folder_path, "images")
    os.makedirs(images_folder, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    writer = pd.ExcelWriter(full_excel_path, engine="openpyxl")
    
    # Write PDF metadata if available
    metadata = doc.metadata
    if metadata:
        pd.DataFrame(list(metadata.items()), columns=["Property", "Value"]).to_excel(writer, sheet_name="Metadata", index=False)
    
    overall_summary = []
    annotations_records = []
    levels_records = []  # For lines containing 'FFL' or 'Level'
    
    # Process each page in the PDF
    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1
        
        # --- Text extraction and formatting ---
        # (calls the LLM API internally via our helper)
        page_text = extract_page_text(page, page_number, folder_path)
        
        # --- Image extraction and Vision API calls ---
        process_page_images(page, page_number, doc, folder_path, images_folder)
        
        # --- Measurement extraction ---
        measurements_records, totals = extract_measurements(page_text)
        totals["Page"] = page_number
        
        # --- Annotations extraction ---
        annots = extract_annotations(page, page_number)
        annotations_records.extend(annots)
        
        # --- Extraction of 'FFL' or 'Level' lines ---
        levels = extract_levels(page_text, page_number)
        levels_records.extend(levels)
        
        # Write measurements (and totals) to an Excel sheet
        page_df = pd.DataFrame(measurements_records) if measurements_records else pd.DataFrame(columns=["Measurement Value", "Unit", "Source"])
        totals_text = f"TOTALS: sq m = {totals['Total sq m']}, mm = {totals['Total mm']}, m = {totals['Total m']}, unknown = {totals['Total unknown']}"
        totals_df = pd.DataFrame([{"Measurement Value": totals_text, "Unit": "", "Source": ""}])
        page_df = pd.concat([page_df, totals_df], ignore_index=True)
        
        sheet_name = f"Page_{page_number}"
        page_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        overall_summary.append(totals)
    
    # Save overall measurements summary to CSV and Excel
    overall_df = pd.DataFrame(overall_summary)
    csv_filename = os.path.join(folder_path, f"overall_measurements_{timestamp}.csv")
    overall_df.to_csv(csv_filename, index=False)
    overall_df.to_excel(writer, sheet_name="Totals", index=False)
    
    if annotations_records:
        pd.DataFrame(annotations_records).to_excel(writer, sheet_name="Annotations", index=False)
    if levels_records:
        pd.DataFrame(levels_records).to_excel(writer, sheet_name="Levels", index=False)
    
    writer.close()
    print(f"Excel file saved at: {full_excel_path}")
    print(f"CSV summary saved at: {csv_filename}")
    print(f"Images saved in: {images_folder}")
    print(f"Text files saved in: {folder_path}")

if __name__ == "__main__":
    output_directory = "."
    pdf_files = glob.glob("*.pdf")
    if not pdf_files:
        print("No PDF files found in the root directory.")
    else:
        # Process the first PDF file found
        extract_pdf_data(pdf_files[0], output_directory)
