from __future__ import print_function
import pickle
import socket
import os
import json
import requests
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
from datetime import datetime
import logging
import time
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run_flow
from oauth2client.file import Storage
import sys

socket.setdefaulttimeout(600) 
logging.basicConfig(filename='log.log',
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)

logging.info("Running")                            


SCOPES = ['https://www.googleapis.com/auth/drive']


def authenticate_drive():

    creds = None

    if os.path.exists('drive_token.pickle'):
        with open('drive_token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'drive_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('drive_token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    drive_service = build('drive', 'v3', credentials=creds)

    return drive_service


def upload_files(files, folder_id, drive_service):
    upload_status = []
    for file_ in files:
        file_metadata = {
            'name': file_,
            'mimeType': 'application/vnd.google-apps.spreadsheet',
            'parents': [folder_id]
        }
        print('Doing for file - ', file_)

        media = MediaFileUpload('{}'.format(file_),
                                mimetype='application/vnd.ms-excel',
                                chunksize=512 * 512,
                                resumable=True)
        media.stream()
        file = drive_service.files().create(body=file_metadata,
                                            media_body=media,
                                            fields='id')
        response = None
        while response is None:
            status, response = file.next_chunk()
            
            print('Response - ', response)
            print('Status - ', status.progress() * 100)
 
        logging.info('Uploaded {}'.format(file_))
        upload_status.append('File ID: %s' % file.get('id'))
    return upload_status

##################
# Using HTTP APIs
##################

def disable_stout():
    o_stdout = sys.stdout 
    o_file = open(os.devnull, 'w')
    sys.stdout = o_file
    return (o_stdout, o_file)


def enable_stout(o_stdout, o_file):
    o_file.close()
    sys.stdout = o_stdout


def get_oauth2_token():
    CLIENT_ID = ''
    CLIENT_SECRET = ''
    SCOPE = 'https://www.googleapis.com/auth/drive'
    REDIRECT_URI = 'http://localhost/'

    o_stdout, o_file = disable_stout()

    flow = OAuth2WebServerFlow(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scope=SCOPE,
        redirect_uri=REDIRECT_URI
    )

    storage = Storage('creds.data')
    credentials = run_flow(flow, storage)
    enable_stout(o_stdout, o_file)

    return credentials.access_token


def get_files_to_upload():
    today = datetime.today().strftime('%d-%m-%Y')
    files = [file_ for file_ in os.listdir('foldername') if today in file_]
    logging.info('Files to upload - {}'.format([file_ for file_ in files]))
    return files


def create_folder():
    file_metadata = {
        'name': 'CSV Files',
        'mimeType': 'application/vnd.google-apps.folder'
    }
    file = drive_service.files().create(body=file_metadata,
                                        fields='id').execute()
    print('Folder ID: %s' % file.get('id'))


def upload_via_api(access_token, files, folder_id):
    upload_status = []

    for file_ in files:
        logging.info('Uploading ', file_)
        filename = '{}'.format(file_)

        filesize = os.path.getsize(filename)

        headers = {"Authorization": "Bearer "+ access_token, "Content-Type": "application/json"}
        params = {
            "name": file_,
            "mimeType": "application/vnd.ms-excel",
            "parents": [folder_id]
        }
        r = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
            headers=headers,
            data=json.dumps(params)
        )
        location = r.headers['Location']

        # 2. Upload the file.

        headers = {"Content-Range": "bytes 0-" + str(filesize - 1) + "/" + str(filesize)}
        r = requests.put(
            location,
            headers=headers,
            data=open(filename, 'rb')
        )
        upload_status.append(r.status_code)

    return upload_status


if __name__ == '__main__':
    print('getting token')
    access_token = get_oauth2_token()
    files = get_files_to_upload()
    upload_status = upload_via_api(access_token, files, '')
    logging.info('Upload status - {}'.format([x for x in upload_status]))
    logging.info('--------------------')
