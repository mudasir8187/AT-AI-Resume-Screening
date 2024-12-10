import base64  # Import base64 for encoding
import streamlit as st
import mysql.connector

# Set page configuration
st.set_page_config(page_title="Show Resumes")

# Connect to the database
mydb = mysql.connector.connect(
    user='root',
    password='ali2468MYSQL*:',  # Update your password
    host='127.0.0.1',
    database='resumes',
    auth_plugin='mysql_native_password'
)

cur = mydb.cursor()

# Page header
st.header("Short listed Candidates")

# Fetch resumes based on category, including EXPERIENCE
query1 = """SELECT NAME, EMAIL, contact, experience, file_url FROM employee_details ORDER BY EXPERIENCE DESC"""
cur.execute(query1)
resumes = cur.fetchall()

# Initialize session state for PDF toggles
if "pdf_visibility" not in st.session_state:
    st.session_state.pdf_visibility = {}

# Display the headers
colms = st.columns((1, 2.1, 1.5, 1.5, 1.5))  # Adjusted column widths for better layout
fields = ["Name", "Email", "Contact No", "Experience", "Action"]
for col, field_name in zip(colms, fields):
    col.write(f"**{field_name}**")

# Display each resume
for idx, row in enumerate(resumes):
    col1, col2, col3, col4, col5 = st.columns((2, 3, 3, 2, 3))  # Adjusted column widths

    # Display the data in respective columns
    col1.write(row[0])  # Name
    col2.write(row[1])  # Email
    col3.write(row[2])  # Contact No
    col4.write(row[3])  # Experience

    # Initialize visibility state for this row if not already set
    if idx not in st.session_state.pdf_visibility:
        st.session_state.pdf_visibility[idx] = False

    # Button to toggle PDF visibility
    button_label = "Hide PDF" if st.session_state.pdf_visibility[idx] else "View PDF"
    if col5.button(button_label, key=f"toggle_pdf_{idx}"):
        # Toggle visibility state and update button label
        st.session_state.pdf_visibility[idx] = not st.session_state.pdf_visibility[idx]

    # Display the PDF if visibility is True
    if st.session_state.pdf_visibility[idx]:
        pdf_url = row[4]
        if pdf_url and pdf_url.startswith("file://"):
            file_path = pdf_url[7:]  # Remove 'file://' prefix
            try:
                with open(file_path, "rb") as f:
                    pdf_data = f.read()

                # Encode the PDF in base64
                pdf_base64 = base64.b64encode(pdf_data).decode("utf-8")
                pdf_display = f"data:application/pdf;base64,{pdf_base64}"

                # Display the PDF inline
                st.markdown(
                    f'<iframe src="{pdf_display}" width="100%" height="600px" frameborder="0"></iframe>',
                    unsafe_allow_html=True,
                )
            except FileNotFoundError:
                st.error("File not found!")
