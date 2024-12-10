import mysql.connector
import streamlit as st
import os
from pathlib import Path
import re
import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from docx import Document
import google.generativeai as genai
import mysql.connector

# Configure Google Generative AI
genai.configure(api_key="AIzaSyBubKQRTWfEMi7zWaXKRY_MkMaBj5r4gZ4")  # Replace with your actual API key
model = genai.GenerativeModel("gemini-1.5-flash")


# Streamlit layout: Logo and Title
col1, col2 = st.columns([4.5,1.5])  # Two columns with a 1:4 ratio

with col1:
     st.markdown(
        """
        <h1 style='text-align: left; font-size: 44px; margin: 0;'>
            Welcome to AT AI Resume Screening
        </h1>
        """,
        unsafe_allow_html=True,
    )
with col2:
       # Use st.image for the logo
    st.image("logos/at_logo")
   
# Directory to save uploaded files
UPLOAD_DIR = Path("uploaded_files")
UPLOAD_DIR.mkdir(exist_ok=True)

# Create the form for job details and file upload
with st.form("HR form"):
    position = st.text_input("Position", placeholder="Please enter the Job position") 
    exp = st.text_input("Minimum Experience (in years)", placeholder="Please enter the minimum experience required (in years)")
    location = st.text_input("Location", placeholder="Please enter the location") 
    skills = st.text_input("Skills", placeholder="Please enter the required skills")
    job_desc = st.text_area("Job Description", placeholder="Please enter the job description")
    
    # File upload inside the form
    uploaded_files = st.file_uploader(
        "Upload all files in the folder (PDF or Word files)",
        type=["pdf", "docx"],
        accept_multiple_files=True
    )

    # Submit button
    submitted = st.form_submit_button("Submit")


# Validate input fields and file uploads upon form submission
if submitted:
    if not position or not exp or not location or not skills or not job_desc:
        st.error("All fields are required. Please fill in all the fields.")
    elif not uploaded_files:
        st.error("Please upload at least one resume.")
    else:
        st.success("Job details and CVs submitted successfully!")
        st.write(f"Number of CVs uploaded: {len(uploaded_files)}")

        ################################
        def extract_text_from_pdf(file):
            """Extract text from PDFs (both text-based and image-based) page by page."""
            text = ""
            pages_with_ocr = []

            try:
                with pdfplumber.open(file) as pdf:
                    for i, page in enumerate(pdf.pages, start=1):
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text += page_text + "\n"
                        else:
                            print(f"Page {i} had no extractable text with pdfplumber, switching to OCR.")
                            pages_with_ocr.append(i)

                if pages_with_ocr:
                    images = convert_from_path(file, dpi=300)
                    for i in pages_with_ocr:
                        print(f"Performing OCR on page {i}...")
                        text += extract_text_with_ocr(images[i - 1]) + "\n"

            except Exception as e:
                print(f"Error processing PDF: {e}")
                return text.strip()

            return text.strip()


        def extract_text_with_ocr(image):
            """Perform OCR on an image with enhanced settings."""
            custom_config = r'--oem 3 --psm 6'
            try:
                return pytesseract.image_to_string(image, config=custom_config)
            except Exception as e:
                print(f"Error during OCR: {e}")
                return ""


        def extract_text_from_docx(file):
            """Extract text from DOCX files."""
            text = ""
            try:
                doc = Document(file)
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
            except Exception as e:
                print(f"Error reading DOCX file: {e}")
            return text.strip()

        # Database connection function
        def get_db_connection():
            try:
                connection = mysql.connector.connect(
                user='root',
                password='ali2468MYSQL*:',
                host='127.0.0.1',
                database='resumes',
                auth_plugin='mysql_native_password',
                )
                return connection
            except Exception as e:
                st.error(f"Database connection failed: {e}")
                st.stop()
        
        def extract_data_from_uploaded_files(uploaded_files):
            """Extract text from uploaded files and process the content."""
            for uploaded_file in uploaded_files:
                file_name = uploaded_file.name
                file_extension = os.path.splitext(file_name)[1].lower()

                # Save file to the upload directory
                file_path = UPLOAD_DIR / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Generate a unique link for the file
                file_url = f"file://{file_path.absolute()}"
                
                
                # Extract text based on file type
                if file_extension == ".pdf":
                    text = extract_text_from_pdf(uploaded_file)
                elif file_extension == ".docx":
                    text = extract_text_from_docx(uploaded_file)
                else:
                    st.error(f"Unsupported file format: {file_extension}")
                    continue

                if text:
                    #print(text)
                    # Process the extracted text (e.g., send it to an AI model)
                    # Assuming `model.generate_content()` is a predefined function
                    skills_prompt = f"""
                                            This is the data of a CV:\n\n{text}\n\n
                                            1. Locate the "Skills" section in the CV and extract its content exactly as written. 
                                            2. If a specific "Skills" section is not explicitly provided, analyze CV text and identify the candidate's skill on which he has worked already.
                                            3. Strictly follow this : Don't give any text other than skills or ai genrative content, I only need skills by comma separated in a single line."""
                    
                    title_prompt = f"""This is the data of a CV:\n\n{text}\n\n
                                            1. Extract the most relevant job title explicitly mentioned in the CV. 
                                            2. If no job title is explicitly stated, analyze the "Skills" and "Experience" sections carefully to infer an appropriate job title based on the candidate's qualifications, expertise, and work history. 
                                            3. Ensure the job title is concise, relevant, and aligned with the information provided.
                                            4. Do not include any additional commentary or text other than the inferred or extracted job title.
                                    """
                    experience_prompt = f"""
                                            This is the data of a CV:\n\n{text}\n\n
                                            1. Analyze the "Experience" section of the CV carefully.
                                            2. For each company listed, extract the name of the company, the start date, and the end date (or indicate "present" if they are currently employed there).
                                            3. Calculate the duration worked at each company (in years and months).
                                            4. Sum up the durations to determine the total work experience across all companies, ensuring overlapping periods are accounted for.
                                            5. Present the following:
                                            - The total work experience in years and months.
                                            6. Show only the extracted and calculated information without any additional commentary or generative AI information.
                                            7. Strictly follow this : Don't give any company name or ai genrative content, I only need total experience as x year and x months and also not include text like Total Experince:.
                                            """
                    location_prompt = f""""
                                            This is the data of a CV:\n\n{text}\n\n
                                            1. Extract the one appropriate city location of candidate (not include Country name) from which he belongs to and provide it as exactly written in the CV text.
                                            2. If city is not found then find city in Experience and eduaction section. If not found in any case then write "No City"
                                            3. Strictly follow this : Don't give any text or ai genrative content.
                                            """
                    name_prompt = f"""
                                            This is the data of a CV:\n\n{text}\n\n
                                            1. Identify and extract the full name of the candidate from the CV.
                                            2. Ensure the name is taken only from sections like "Header," "Contact Information," or similar introductory parts.
                                            3. Avoid including names mentioned in references, project descriptions, or other sections.
                                            4. Present only the candidate's full name without any additional commentary or extra text.
                                            """
                    email_prompt = f"""
                                            This is the data of a CV:\n\n{text}\n\n
                                            1. Extract the email address of the candidate from the CV.
                                            2. Ensure the email address is taken only from the candidate's contact information or header section.
                                            3. Do not include any email addresses mentioned in other sections, such as references or third-party contacts.
                                            4. Provide only the candidate's email address without any additional commentary or extra text.
                                            """
                    contact_prompt = f"""
                                            This is the data of a CV:\n\n{text}\n\n
                                            1. Extract the mobile or primary contact number of the candidate from the CV.
                                            2. Ensure the number is taken only from the candidate's contact information or header section.
                                            3. Exclude any contact numbers mentioned in references, project descriptions, or other sections unrelated to the candidate.
                                            4. Provide only the candidate's contact number without any additional commentary or extra text.
                                            """
                    try:
                        title_response = model.generate_content(title_prompt)
                        experience_response = model.generate_content(experience_prompt)
                        skills_response = model.generate_content(skills_prompt)
                        location_response = model.generate_content(location_prompt)
                        name_response = model.generate_content(name_prompt)
                        email_response = model.generate_content(email_prompt)
                        contact_respose = model.generate_content(contact_prompt)
                    except Exception as e:
                        st.error(f"Error during AI processing: {e}")
                        return None
                
                    resume_title = title_response.text
                    #st.write(resume_title)
                    resume_experience = experience_response.text
                    #st.write(resume_experience)
                    resume_skills = skills_response.text
                    #st.write(resume_skills)
                    resume_location = location_response.text
                    #st.write(resume_location)
                    resume_name = name_response.text
                    #st.write(resume_name)
                    resume_email = email_response.text
                    #st.write(resume_email)
                    resume_contact = contact_respose.text
                    #st.write(resume_contact)
                    resume_url = file_url
                    #st.write(resume_url)
                    # Directory to save recommended resumes
                    RECOMMENDATION_DIR = Path("recommendation")
                    RECOMMENDATION_DIR.mkdir(exist_ok=True)

                    # Compare location and experience to filter resumes
                    try:
                        # Function to save resume details to the database
                        def save_to_database(name, email, contact, experience, resume_url):
                                connection = get_db_connection()
                                try:
                                        # Prepare the query to check for duplicates based on name and email
                                        check_query = """
                                        SELECT COUNT(*) FROM employee_details
                                        WHERE name = %s AND email = %s
                                        """
                                        
                                        # Create a cursor to execute the query
                                        cur = connection.cursor()

                                        # Execute the check query
                                        cur.execute(check_query, (name, email))
                                        record_count = cur.fetchone()[0]

                                        # If record exists, skip the insertion
                                        if record_count > 0:
                                                st.warning("This candidate's record already exists in the database. Thank you!")
                                        else:
                                        # Insert the new record
                                                insert_query = """
                                                        INSERT INTO employee_details (name, email, contact, experience, file_url) 
                                                        VALUES (%s, %s, %s, %s, %s)
                                                """
                                                cur.execute(insert_query, (name, email, contact, experience, str(resume_url)))
                                                connection.commit()
                                                st.success("Resume details saved to the database!")

                                except mysql.connector.Error as e:
                                        st.error(f"Error saving to database: {e}")
                                finally:
                                        # Close the cursor and connection
                                        cur.close()
                                        connection.close()


                        # resume_years = int(resume_experience.split()[0])/12
                        # Regex patterns
                        year_pattern = r"(\d+)\s*year"
                        month_pattern = r"(\d+)\s*month"
                        # Extract years and months
                        years = sum(int(y) for y in re.findall(year_pattern, resume_experience))
                        months = sum(int(m) for m in re.findall(month_pattern, resume_experience))

                        # Calculate total years (including converted months)
                        total_years = years + months / 12

                        # Output rounded result
                        resume_years = int(round(total_years, 2))
                        #print(resume_years)
                        # Convert user input for experience to an integer
                        required_experience = int(exp.strip())
                        # Check criteria for location and experience
                        if resume_location.strip().lower() == "no city":
                         # Only check experience if location is "No City"
                                if resume_years >= required_experience:
                                        recommended_file_path = RECOMMENDATION_DIR / uploaded_file.name
                                        with open(recommended_file_path, "wb") as f:
                                                f.write(uploaded_file.getbuffer())
                                        #st.success(f"Resume '{uploaded_file.name}' matches the experience criteria and has been saved to the 'recommendation' folder.")
                                        # Save details to the database
                                        save_to_database(resume_name, resume_email, resume_contact, resume_experience, recommended_file_path)
                                else:
                                        st.warning(f"Resume '{uploaded_file.name}' does not meet the experience criteria.")
                        else:
                                # Check both location and experience for other cases
                                if (
                                resume_location.strip().lower() == location.strip().lower() and
                                resume_years >= required_experience
                                ):
                                        recommended_file_path = RECOMMENDATION_DIR / uploaded_file.name
                                        with open(recommended_file_path, "wb") as f:
                                                f.write(uploaded_file.getbuffer())
                                        # Generate the full file URL
                                        full_file_url = f"file://{recommended_file_path.absolute()}"
                                        #st.success(f"Resume '{uploaded_file.name}' matches the criteria and has been saved to the 'recommendation' folder.")
            
                                        # Save details to the database
                                        save_to_database(resume_name, resume_email, resume_contact, resume_experience,full_file_url)
                                else:
                                        st.warning(f"Resume '{uploaded_file.name}' does not meet the criteria.")
                    except ValueError:
                        st.error(f"Could not parse experience from '{resume_experience}'. Ensure the format is correct.")

                
                                    
                    print("------------------------------")


        # Process the uploaded files
        extract_data_from_uploaded_files(uploaded_files)

