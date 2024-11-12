import os
import pdfplumber
import re
import pandas as pd
import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph

# Configuration
page_limit = 223  # Number of pages to read from the PDF
deepL_api_key = 'KEY'  # Replace with your DeepL API key
output_pdf = 'OutputPDFs/output.pdf'  # Output PDF file
pdf_dir = 'SourcePDFs'  # Directory containing PDF files
margin = 30
cell_padding = 4

# Function to list available PDF files and ask user to select one
def select_pdf_file():
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("No PDF files found in the 'pdfBooks' directory.")
        return None

    print("Available PDF files:")
    for idx, pdf_file in enumerate(pdf_files, start=1):
        print(f"{idx}. {pdf_file}")

    try:
        choice = int(input("Select the PDF file by number: ")) - 1
        if 0 <= choice < len(pdf_files):
            return os.path.join(pdf_dir, pdf_files[choice])
        else:
            print("Invalid choice. Please try again.")
            return None
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None

# Function to extract text from a PDF file with page limit and add page markers
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                if page_num >= page_limit:
                    break
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                    text += f"IIII: ~~~~~  {page_num + 1}  ~~~~~"
        return text.strip()
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return ""

# Function to clean and process text
def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('\f', ';;;;')
    return text

# Function to split text by speaker tags, including names with parentheses
def split_sentences(text):
    # Use a regex to split on patterns like 'JAMES:', 'HERMIONE:', or 'JAMES (with a grin):'
    sentences = re.split(r'(?=\b[A-Z]{3,}(?:\s*\([^)]*\))?:\s)', text)
    processed_sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    return processed_sentences


# Function to create a pandas DataFrame from text with an additional numbering column
def create_dataframe_from_text(text):
    sentences = split_sentences(text)
    df = pd.DataFrame({
        'No.': range(1, len(sentences) + 1),
        'Sentence': sentences,
        'Translation': [''] * len(sentences)
    })
    return df

# Function to translate sentences using DeepL with error handling
def translate_sentences(sentences):
    translations = []
    for sentence in sentences:
        try:
            response = requests.post(
                'https://api-free.deepl.com/v2/translate',
                data={
                    'auth_key': deepL_api_key,
                    'text': sentence,
                    'source_lang': 'EN',  # Source language
                    'target_lang': 'DA'   # Target language
                }
            )
            response.raise_for_status()  # Check for HTTP errors
            result = response.json()
            translated_text = result['translations'][0]['text']
            translations.append(translated_text)
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            translations.append("[Translation Error]")
        except (KeyError, IndexError) as e:
            print(f"API response error: {e}")
            translations.append("[Invalid API Response]")
    return translations

# Function to generate a printable PDF from the DataFrame
def generate_pdf(df, output_pdf):
    pdf = SimpleDocTemplate(output_pdf, pagesize=A4, rightMargin=margin, leftMargin=margin, topMargin=margin, bottomMargin=margin)
    styles = getSampleStyleSheet()
    elements = []

    # Define table data and style
    table_data = [['No.', 'Translation', 'Sentence']]
    for _, row in df.iterrows():
        number = row['No.']
        sentence = Paragraph(row['Sentence'], styles['Normal'])
        translation = Paragraph(row['Translation'], styles['Normal'])
        table_data.append([number, translation, sentence])

    table = Table(table_data, colWidths=[30, 250, 250])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), cell_padding),
        ('RIGHTPADDING', (0, 0), (-1, -1), cell_padding),
        ('TOPPADDING', (0, 0), (-1, -1), cell_padding),
        ('BOTTOMPADDING', (0, 0), (-1, -1), cell_padding)
    ]))

    elements.append(table)
    pdf.build(elements)

# Main script execution
if __name__ == "__main__":
    pdf_path = select_pdf_file()
    if pdf_path:
        text = extract_text_from_pdf(pdf_path)
        cleaned_text = clean_text(text)
        df = create_dataframe_from_text(cleaned_text)

        # Translate sentences and populate the DataFrame
        df['Translation'] = translate_sentences(df['Sentence'])

        # Generate PDF from DataFrame
        generate_pdf(df, output_pdf)
        print("PDF document has been created:", output_pdf)
