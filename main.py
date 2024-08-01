import os
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import streamlit as st
from pathlib import Path
import pandas as pd
import streamlit.components.v1 as components
from dotenv import load_dotenv
load_dotenv()
# Set up Streamlit configuration
st.set_page_config(page_title="My Experiment", layout="wide")
#importtant 
# Include custom JavaScript to disable Enter key
custom_js = """
<script type="text/javascript">
    window.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            if (e.target.nodeName === 'INPUT' && e.target.type === 'text') {
                e.preventDefault();
            }
        }
    });
</script>
"""
components.html(custom_js, height=0, width=0)

# Google Sheets API setup
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1PUURytVhS25vs75lFS1duA7EtayJZXkh-d_Y_Rwdkrs"

def get_google_sheet_service():
    credentials = None
    # Check for existing token file
    if os.path.exists("token.json"):
        credentials = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            # Create new credentials from environment variables
            client_config = {
                "installed": {
                    "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                    "project_id": "humansurveyproject",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": os.getenv('GOOGLE_TOKEN_URI'),
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                    "redirect_uris": ["http://localhost"]
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            credentials = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(credentials.to_json())
    try:
        service = build("sheets", "v4", credentials=credentials)
        return service
    except HttpError as error:
        st.error(f"An error occurred: {error}")
        return None
service = get_google_sheet_service()

# Function to get the list of video files
def get_videos(video_folder):
    video_extensions = [".mp4"]
    return [str(video) for video in Path(video_folder).rglob("*") if video.suffix in video_extensions]

# Function to display the instructions
def display_instructions():
    st.markdown(
        """
        ## Welcome to the experiment.
        **Please read the following instructions carefully:**

        1. Press the button to begin the experiment.
        2. Watch the video presented.
        3. Select the most appropriate option from the list provided below the video.
        4. The video will only play once, so please ensure you watch it attentively.
        5. There are 36 videos, and you must choose an option for each video.
        6. Click on the play button to play the video. Each video is 3sec long.
        7. For optimal visualization, we recommend using a laptop, MacBook, or iPad.
        8. The experiment may take 5-10 minutes, so please proceed patiently.
        """
    )

# Remove whitespace from the top of the page and sidebar
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 5rem;
            padding-right: 5rem;
        }
    </style>
    """, unsafe_allow_html=True)

# Callback function for starting the experiment
def start_experiment():
    if st.session_state.consent_given:
        st.session_state.current_video = 1
        st.session_state.video_done = False
        st.session_state.responses = {}
        st.session_state.start_time = time.time()
    else:
        st.error("Please accept the terms and conditions before starting the experiment.")

# Callback function for submitting an answer
def submit_answer(selected_option):
    st.session_state.responses[st.session_state.current_video] = selected_option
    st.session_state.current_video += 1
    st.session_state.video_done = False

# Callback function for submitting the final form
def submit_final_form(name, age, spectacles):
    st.session_state.participant_info = {
        "Name": name,
        "Age": age,
        "Wears Spectacles": spectacles
    }

    # Calculate total time taken
    total_time = time.time() - st.session_state.start_time

    # Prepare data to update the Google Sheet
    participant_info = [name, age, spectacles]
    responses = [st.session_state.responses.get(i, "") for i in range(1, 37)]
    row_data = participant_info + responses + [total_time]

    # Append data to Google Sheet
    body = {'values': [row_data]}
    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Sheet1!A1",
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

    st.session_state.experiment_completed = True

# Main function to run the experiment
def main():
    video_folder = "videos"  # Folder containing the videos
    videos = get_videos(video_folder)
    choices = ['ball', 'human', 'Swing/Pendulum', 'mammal', 'reptile', 'tool']
    num_videos = len(videos)

    # Initialize session state variables
    if "current_video" not in st.session_state:
        st.session_state.current_video = 0
    if "video_done" not in st.session_state:
        st.session_state.video_done = False
    if "responses" not in st.session_state:
        st.session_state.responses = {}
    if "participant_info" not in st.session_state:
        st.session_state.participant_info = {}
    if "experiment_completed" not in st.session_state:
        st.session_state.experiment_completed = False
    if "consent_given" not in st.session_state:
        st.session_state.consent_given = False

    if st.session_state.current_video == 0:
        display_instructions()
        # Add consent checkbox
        consent_checkbox = st.checkbox("**I understand that my data is being collected.**", key="consent")
        if consent_checkbox:
            st.session_state.consent_given = True
        else:
            st.session_state.consent_given = False
        
        # Add Start Experiment button
        st.button("Start Experiment", on_click=start_experiment, disabled=not st.session_state.consent_given)
    elif st.session_state.current_video <= num_videos:
        video_path = videos[st.session_state.current_video - 1]

        # Check if the video file exists
        if not Path(video_path).exists():
            st.error(f"Video file not found: {video_path}")
            return

        st.markdown(f"### Video {st.session_state.current_video}")

        # Create two columns for layout
        col1, col2 = st.columns(2)
        
        with col1:
            # Display the video on the left column
            st.video(video_path)

        with col2:
            # Display the choices and submit button on the right column
            choice = st.radio("Select the most appropriate option:", choices)
            st.button("Next", on_click=lambda: submit_answer(choice))

    elif st.session_state.current_video > num_videos and not st.session_state.participant_info:
        st.markdown("### Please fill out the following form:")
        st.markdown("Please fill all the entries before clicking on submit button.")
        st.markdown(
            """
            <style>
                .participant-form {
                    background-color: #FFFFE0; /* Light yellow background */
                    padding: 20px;
                    border-radius: 10px;
                }
            </style>
            """, unsafe_allow_html=True)

        with st.form(key='participant_form'):
            name = st.text_input("Participant's Name", value="")
            age = st.number_input("Age of the Participant", min_value=0, max_value=120, step=1)
            spectacles = st.radio("Do you wear spectacles?", ('Yes', 'No'))
            submit_button = st.form_submit_button("Submit")
            if submit_button:
                submit_final_form(name, age, spectacles)

    if st.session_state.experiment_completed:
        # Define the column names for the CSV
        column_names = ["Name", "Age", "Wears Spectacles"] + [f"Video {i} Response" for i in range(1, 37)] + ["Total Time"]

        # Create responses DataFrame
        responses_df = pd.DataFrame([list(st.session_state.participant_info.values()) + 
                                    [st.session_state.responses.get(i, "") for i in range(1, 37)] + 
                                    [time.time() - st.session_state.start_time]], 
                                    columns=column_names)
        
        # Save responses to CSV
        csv = responses_df.to_csv(index=False).encode('utf-8')

        # Provide download link for CSV
        st.download_button(
            label="Download responses as CSV",
            data=csv,
            file_name='responses.csv',
            mime='text/csv',
        )

if __name__ == "__main__":
    main()


