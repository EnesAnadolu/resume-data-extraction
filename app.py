import streamlit as st
import fitz
import os
import json
from typing import List, Dict
from openai import OpenAI
from docx import Document
from io import BytesIO

class ResumeParser:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        
    def extract_text_from_pdf(self, pdf_file) -> str:
        try:
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            text = "".join([page.get_text() for page in doc])
            return text
        except Exception as e:
            st.error(f"Error extracting text from PDF: {str(e)}")
            return ""

    def extract_text_from_docx(self, docx_file) -> str:
        try:
            document = Document(BytesIO(docx_file.read()))
            return "\n".join([para.text for para in document.paragraphs])
        except Exception as e:
            st.error(f"Error extracting text from DOCX: {str(e)}")
            return ""

    def extract_text(self, file) -> str:
        if file.name.endswith(".pdf"):
            return self.extract_text_from_pdf(file)
        elif file.name.endswith(".docx") or file.name.endswith(".doc"):
            return self.extract_text_from_docx(file)
        else:
            st.error("Unsupported file format")
            return ""

    def extract_information(self, text: str) -> Dict:
        prompt = f"""Extract the following information from the resume text. Return the data in JSON format:
        - name: Full name of the candidate
        - education: List of qualifications and education
        - nationality: Candidate's nationality
        - dob: Date of birth
        - languages: List of languages known
        - location: Current location/residence
        - experience: List of work experiences with company name, position, and duration
        - certificates: List of valid certificates
        - visas: List of valid work visas
        - summary: AI generated summary of the candidate's profile (2-3 sentences)
        
        Resume text:
        {text}
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            st.error(f"Error extracting information: {str(e)}")
            return {}

def process_uploaded_files(files, parser):
    if 'extracted_data' not in st.session_state:
        st.session_state['extracted_data'] = {}
    
    new_files = [f for f in files if f.name not in st.session_state['extracted_data']]
    
    for file in new_files:
        with st.spinner(f"Processing {file.name}..."):
            text = parser.extract_text(file)
            if text:
                info = parser.extract_information(text)
                if info:
                    st.session_state['extracted_data'][file.name] = info

def main():
    st.set_page_config(layout="wide")
    
    if 'processed_files' not in st.session_state:
        st.session_state['processed_files'] = set()
    
    with st.sidebar:
        st.title("Resume Upload")
        api_key = st.text_input("Enter OpenAI API Key:", type="password")
        if not api_key:
            st.warning("Please enter your OpenAI API key to continue.")
            return
            
        uploaded_files = st.file_uploader("Upload Resumes (PDF, DOC, DOCX)", type=['pdf', 'doc', 'docx'], accept_multiple_files=True)
        
        if uploaded_files:
            parser = ResumeParser(api_key)
            process_uploaded_files(uploaded_files, parser)
    
    if 'extracted_data' in st.session_state and st.session_state['extracted_data']:
        resumes = list(st.session_state['extracted_data'].keys())
        
        if 'selected_resume' not in st.session_state:
            st.session_state['selected_resume'] = resumes[0]
            
        selected_resume = st.selectbox("Select Resume", resumes, index=resumes.index(st.session_state['selected_resume']))
        st.session_state['selected_resume'] = selected_resume
        st.header(f"Resume Analysis: {selected_resume}")
        st.write(st.session_state['extracted_data'][selected_resume])
    else:
        st.write("Upload resumes in the sidebar to begin analysis.")

if __name__ == "__main__":
    main()
