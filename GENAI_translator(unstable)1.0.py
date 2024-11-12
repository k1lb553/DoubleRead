import PyPDF2
import re
import google.generativeai as genai
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os

# Configuration
line_limit = 30000  # Number of lines to read from the PDF
genai_api_key = 'ASD'  # Replace with your Gemini API key

# Set up Google Generative AI
genai.configure(api_key=genai_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

def list_available_files():
    # Get all PDF and TXT files in the current directory
    files = [f for f in os.listdir('.') if f.lower().endswith(('.pdf', '.txt'))]
    print("\nAvailable files:")
    for idx, file in enumerate(files, 1):
        print(f"{idx}. {file}")
    return files

# Function to extract text based on file type
def extract_text_from_file(file_path):
    # Get file extension
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()

    text = ""
    try:
        if file_extension == '.pdf':
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages[:line_limit]:  # Limit to specified number of lines
                    text += page.extract_text() + "\n"
        elif file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8') as file:
                # Read only up to line_limit lines
                for i, line in enumerate(file):
                    if i >= line_limit:
                        break
                    text += line
        else:
            raise ValueError(f"Unsupported file type: {file_extension}. Please provide a .pdf or .txt file.")
        
        return text.strip()
    
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {file_path} was not found.")
    except Exception as e:
        raise Exception(f"Error reading file: {str(e)}")

# Function to clean and process text
def clean_text(text):
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    text = text.replace('\f', ';;;;')  # Replace page breaks with ";;;;"
    return text

# Function to translate and split text into sentences with custom rules
def translate_and_split_sentences(text, source_lang, target_lang):
    sentences = []
    translations = []
    prompt_prefix = (f"You are a translator. Your job is to translate the following text from {source_lang} to {target_lang}. "
                     "Be as literate as possible with the words, because your output will be used to learn vocabulary.")

    for sentence in re.split(r'(?<=[.!?]) +', text):
        if sentence and len(sentence) >= 6:
            prompt = f"{prompt_prefix}\n\nText: {sentence}"
            response = model.generate_content(prompt)
            translated_text = response.text  # Get the translation result
            sentences.append(sentence)
            translations.append(translated_text)
        elif sentences:
            sentences[-1] += " " + sentence
    return sentences, translations

# Custom canvas for page numbers
def add_page_number(canvas, doc):
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    # Get the width of the text
    text_width = canvas.stringWidth(text, 'Helvetica', 9)
    # Calculate center position
    x = (doc.pagesize[0] - text_width) / 2.0
    canvas.drawString(x, 20, text)
    canvas.restoreState()

# Function to generate PDF from the data
def generate_pdf(original_text, translated_text, output_pdf, original_first=True):
    # Create the PDF document
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    # Create styles
    styles = getSampleStyleSheet()
    
    # Create custom style for table cells
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,  # Line spacing
        spaceAfter=10,
        textColor=colors.black
    )

    # Prepare the data for the table
    data = []

    # Add sentences and translations to the table with row numbers based on order preference
    for i, (orig, trans) in enumerate(zip(original_text, translated_text), 1):
        if original_first:
            row = [str(i), Paragraph(orig, cell_style), Paragraph(trans, cell_style)]
        else:
            row = [str(i), Paragraph(trans, cell_style), Paragraph(orig, cell_style)]
        data.append(row)

    # Create the table
    table = Table(
        data,
        colWidths=[20, (doc.width-20)/2.0 - 10, (doc.width-20)/2.0 - 10],  # Column widths with number column
        repeatRows=0  # No header row
    )

    # Very light gray color
    very_light_gray = colors.Color(0.97, 0.97, 0.97)

    # Style the table
    table.setStyle(TableStyle([
        # Cell styling
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        
        # Row number column styling
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (0, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        
        # Borders
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        
        # Row styling (alternating very light gray)
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, very_light_gray]),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))

    # Build the PDF with page numbers
    doc.build([table], onFirstPage=add_page_number, onLaterPages=add_page_number)

def main():
    # List available files and get user selection
    files = list_available_files()
    while True:
        try:
            file_num = int(input("\nEnter the number of the file you want to process: "))
            if 1 <= file_num <= len(files):
                input_path = files[file_num - 1]
                break
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

    # Get language information
    source_lang = input("\nWhat is the original language of the text? ")
    target_lang = input("What language should it be translated to? ")

    # Get column order preference
    while True:
        order_pref = input(f"\nWhich text should be in the first column?\n1. {source_lang}\n2. {target_lang}\nEnter 1 or 2: ")
        if order_pref in ['1', '2']:
            original_first = (order_pref == '1')
            break
        print("Please enter either 1 or 2.")

    output_pdf = 'translated_output.pdf'  # Output PDF file

    try:
        # Extract text from either PDF or TXT file
        text = extract_text_from_file(input_path)
        
        # Process and generate output
        cleaned_text = clean_text(text)
        sentences, translations = translate_and_split_sentences(cleaned_text, source_lang, target_lang)
        generate_pdf(sentences, translations, output_pdf, original_first)
        
        print(f"\nPDF document has been created: {output_pdf}")
        print(f"Successfully processed {os.path.basename(input_path)}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
