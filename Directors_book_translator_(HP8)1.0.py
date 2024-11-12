import os
import time
import pdfplumber
import re
import pandas as pd
import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph

# Configuration
page_limit = 50  # Number of pages to read from the PDF
deepL_api_key = '8e9eef6f-7835-4fe6-a0e7-126780ef58b4:fx'  # Replace with your DeepL API key
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
    print("Extracting text from pdf... ")
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
        print("Successful text extraction from pdf! ")
        return text.strip()
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return ""

# Function to clean and process text
def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('\f', ';;;;')
    print("Successful text cleaning! ")
    return text

# Function to split text by speaker tags, including names with parentheses
def split_sentences(text):
    # Use a regex to split on patterns like 'JAMES:', 'HERMIONE:', or 'JAMES (with a grin):'
    sentences = re.split(r'(?=\b[A-Z]{3,}(?:\s*\([^)]*\))?:\s)', text)
    processed_sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    print("\nSuccessful text splitting! ")
    return processed_sentences


# Function to create a pandas DataFrame from text with an additional numbering column
def create_dataframe_from_text(text):
    sentences = split_sentences(text)
    df = pd.DataFrame({
        'No.': range(1, len(sentences) + 1),
        'Sentence': sentences,
        'Translation': [''] * len(sentences)
    })
    print("Successful dataframe creation! ")
    return df

# Function to translate sentences using DeepL with error handling
def translate_sentences(sentences):
    print("___INITIATING TRANSLATION___")
    translations = []
    for sentence in sentences:
        print('Translating "',sentence,'"')
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

        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 456:
                print("Error 456: Quota exceeded. Please check your DeepL plan or try again later.")
                translations.append("[Translation Error: Quota exceeded]")
                break  # Stop further translations since quota is exceeded
            else:
                print(f"HTTP error occurred: {http_err} (Status code: {response.status_code})")
                translations.append("[Translation Error]")

        except requests.exceptions.ConnectionError:
            print("Connection error. Retrying in 5 seconds...")
            time.sleep(5)
            continue  # Retry the current sentence

        except requests.exceptions.Timeout:
            print("Request timed out. Retrying in 5 seconds...")
            time.sleep(5)
            continue  # Retry the current sentence

        except Exception as err:
            print(f"An error occurred: {err}")
            translations.append("[Translation Error]")
    print("Successful translations! ")
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
    print("Successfully built PDF! ")

def calculate_character_count(text):
    return len(text)

# Prompt user for continuation based on character count and cost
def prompt_user_for_translation(character_count):
    cost_per_million_chars = 20.00
    characters_per_million = 1_000_000
    estimated_cost = (character_count / characters_per_million) * cost_per_million_chars
    print(f"\nTotal characters in source document: {character_count}")
    print(f"Estimated cost for translation: €{estimated_cost:.2f}")

    user_input = input("Would you like to continue with the translation? (yes/no): ")
    return user_input.lower() == 'yes'


# Main Execution Flow
text = extract_text_from_pdf(select_pdf_file())
cleaned_text = clean_text(text)
character_count = len(cleaned_text)

# Ask user if they want to continue with the translation process
if prompt_user_for_translation(character_count):
    df = create_dataframe_from_text(cleaned_text)

    # Translate sentences and populate the DataFrame
    df['Translation'] = translate_sentences(df['Sentence'])

    # Generate PDF from DataFrame
    generate_pdf(df, output_pdf)
    print("PDF document has been created:", output_pdf)
else:
    print("Translation process was canceled.")
