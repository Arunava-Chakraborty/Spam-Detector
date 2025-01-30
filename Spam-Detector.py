import streamlit as st
import imaplib
import email
from email.header import decode_header
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os
import pickle

# Function to connect to Gmail using OAuth2
@st.cache_data
def connect_gmail_oauth():
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']
    creds = None

    # The file token.pickle stores the user's access and refresh tokens, and is created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Failed to connect to Gmail API: {e}")
        return None

# Fetch emails from Gmail
def fetch_emails_gmail(service):
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
    messages = results.get('messages', [])
    if not messages:
        st.write('No messages found.')
    return messages

# Check if an email is spam based on keywords
def is_spam_gmail(service, message_id, spam_keywords):
    message = service.users().messages().get(userId='me', id=message_id).execute()
    payload = message['payload']
    headers = payload['headers']

    # Get the subject
    for header in headers:
        if header['name'] == 'Subject':
            subject = header['value']
            break

    if any(spam_word in subject.lower() for spam_word in spam_keywords):
        return subject
    return None

# Delete spam emails
def delete_spam_emails_gmail(service, spam_keywords):
    messages = fetch_emails_gmail(service)
    spam_count = 0
    spam_list = []

    for message in messages:
        subject = is_spam_gmail(service, message['id'], spam_keywords)
        if subject:
            service.users().messages().modify(userId='me', id=message['id'], body={'removeLabelIds': ['INBOX'], 'addLabelIds': ['TRASH']}).execute()
            spam_list.append(subject)
            spam_count += 1

    return spam_list, spam_count

# Streamlit UI
st.title("📧 Spam Email Cleaner")
st.write("Detect and delete spam emails from your inbox using OAuth2 authentication.")

# User input for credentials
oauth_login = st.button("Login with Google")

if oauth_login:
    service = connect_gmail_oauth()
    if service:
        spam_keywords = ["lottery", "winner", "prize", "free money", "claim now", "click here", "urgent", "congratulations", "you won"]

        if st.button("Scan for Spam Emails"):
            spam_list, spam_count = delete_spam_emails_gmail(service, spam_keywords)
            st.success(f"Deleted {spam_count} spam emails.")
            if spam_list:
                st.write("### Deleted Spam Emails:")
                for subject in spam_list:
                    st.write(f"- {subject}")
            else:
                st.write("No spam emails found.")
else:
    st.error("Please log in to your Gmail account to proceed.")
