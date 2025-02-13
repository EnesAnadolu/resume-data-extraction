import streamlit as st
import fitz
import os
import json
from typing import List, Dict
from openai import OpenAI
from io import BytesIO

class ResumeParser:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        
    def extract_text_from_file(self, file) -> str:
        try:
            # Read the file into bytes
            file_bytes = file.read()
            
            # Open document with PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="docx" if file.name.endswith((".docx", ".doc")) else "pdf")
            
            # Extract text from all pages
            text = ""
            for page in doc:
                text += page.get_text()
            
            # Close the document
            doc.close()
            return text
        except Exception as e:
            st.error(f"Error extracting text from file: {str(e)}")
            return ""

    def extract_text(self, file) -> str:
        if file.name.lower().endswith(('.pdf', '.docx', '.doc')):
            return self.extract_text_from_file(file)
        else:
            st.error("Unsupported file format. Please upload PDF or DOCX files only.")
            return ""

    def extract_information(self, text: str) -> Dict:
        prompt = f"""Extract the following structured information from the resume text. Ensure consistency in format and field names. If data is not exist in resume, leave it empty. Return the data in JSON format:
        - name: Full name of the candidate (string)
        - education: List of educational qualifications (list of dictionaries)
          Each dictionary contains:
            - institution: Name of the institution (string)
            - location: Location of the institution (string)
            - degree: Degree earned (string)
            - date: Completion date (string)
        - nationality: Candidate's nationality (string)
        - dob: Date of birth (string)
        - languages: List of languages known (list of strings)
        - location: Current location/residence (string)
        - experience: List of work experiences (list of dictionaries)
          Each dictionary contains:
            - company_name: Name of the company (string)
            - position: Job title (string)
            - duration: Employment period (string)
            - job_description: All of job responsibilities (string)
        - certificates: List of valid certificates (list of strings)
        - visas: List of valid work visas (list of strings)
        - summary: AI-generated summary of the candidate's profile (2-3 sentences, string)
        
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

def display_formatted_resume(info: Dict, filename: str):
    """
    Display resume information in a formatted, readable manner using Streamlit components.
    """
    # Clear previous content
    st.empty()
    
    # Display file name as title
    st.title(f"Resume Analysis: {filename}")
    
    # Display basic information
    st.subheader("📌 Basic Information")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Name:** {info.get('name', 'N/A')}")
        st.write(f"**Location:** {info.get('location', 'N/A')}")
    with col2:
        st.write(f"**Nationality:** {info.get('nationality', 'N/A')}")
        st.write(f"**Date of Birth:** {info.get('dob', 'N/A')}")

    # Display summary
    if info.get('summary'):
        st.subheader("📝 Professional Summary")
        st.write(info['summary'])

    # Display work experience
    if info.get('experience'):
        st.subheader("💼 Work Experience")
        for exp in info['experience']:
            with st.expander(f"{exp.get('position', 'Role')} at {exp.get('company_name', 'Company')}"):
                st.write(f"**Duration:** {exp.get('duration', 'N/A')}")
                st.write(f"**Job Description:**")
                job_desc = exp.get('job_description', '').split('\n')
                for desc in job_desc:
                    if desc.strip():
                        st.write(f"- {desc.strip()}")

    # Display education
    if info.get('education'):
        st.subheader("🎓 Education")
        for edu in info['education']:
            st.write(f"**{edu.get('degree', 'Degree')}**")
            st.write(f"- Institution: {edu.get('institution', 'N/A')}")
            st.write(f"- Location: {edu.get('location', 'N/A')}")
            st.write(f"- Completion Date: {edu.get('date', 'N/A')}")

    # Display languages
    if info.get('languages'):
        st.subheader("🗣 Languages")
        st.write(", ".join(info['languages']))

    # Display certificates
    if info.get('certificates'):
        st.subheader("📜 Certificates")
        for cert in info['certificates']:
            st.write(f"- {cert}")

    # Display visas
    if info.get('visas'):
        st.subheader("🛂 Work Visas")
        for visa in info['visas']:
            st.write(f"- {visa}")

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
    
    # Initialize session state
    if 'processed_files' not in st.session_state:
        st.session_state['processed_files'] = set()
    
    # Sidebar
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
    
    # Main content area
    if 'extracted_data' in st.session_state and st.session_state['extracted_data']:
        resumes = list(st.session_state['extracted_data'].keys())
        
        # Create selectbox for resume selection
        selected_resume = st.selectbox(
            "Select Resume",
            resumes,
            key='resume_selector'  # Add a unique key
        )
        
        # Display the selected resume
        if selected_resume:
            extracted_info = st.session_state['extracted_data'][selected_resume]
            display_formatted_resume(extracted_info, selected_resume)
    else:
        st.write("Upload resumes in the sidebar to begin analysis.")

if __name__ == "__main__":
    main()