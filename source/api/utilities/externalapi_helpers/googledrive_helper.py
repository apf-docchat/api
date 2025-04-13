import json
import os
import uuid

from google.oauth2 import service_account
from googleapiclient.discovery import build

class GoogleDriveHelper:
    """
    A class to handle Google Drive API interactions.
    """

    def __init__(self, credential_json):
      temp_file_folder_path = os.path.join(os.path.dirname(__file__), 'temp')
      os.makedirs(temp_file_folder_path, exist_ok=True)

      temp_prefix = uuid.uuid4().hex
      gsheets_credentials_file_path = os.path.join(temp_file_folder_path, f"{temp_prefix}.json")
      with open(gsheets_credentials_file_path, 'w') as f:
          json.dump(credential_json, f)
      
      # Load credentials and initialize Sheets API
      SCOPES = [
          'https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/spreadsheets',
      ]

      credentials = service_account.Credentials.from_service_account_file(
          gsheets_credentials_file_path, scopes=SCOPES
      )

      # Drive API client
      self.drive_service = build('drive', 'v3', credentials=credentials)

      SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
      credentials = service_account.Credentials.from_service_account_file(
          gsheets_credentials_file_path, scopes=SCOPES
      )

      self.sheets_service = build('sheets', 'v4', credentials=credentials)

      os.remove(gsheets_credentials_file_path)


    def get_files(self):

      # Only fetch sheets that are in the collection_gsheet_list
      results = self.drive_service.files().list(
              q="mimeType='application/vnd.google-apps.spreadsheet'",
              pageSize=100,
              fields="files(id, name)"
          ).execute()

      #gsheet_files = results.get('files', [])

      return results
    
    def get_filename(self, gsheet_file_id):
        # Extract the file ID from the URL
        #gsheet_file_id = gsheet_file_url.split('/')[5]

        # Only fetch sheets that are in the collection_gsheet_list
        results = self.drive_service.files().list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                pageSize=100,
                fields="files(id, name)"
            ).execute()

        gsheet_files = results.get('files', [])
        gsheet_file_name = None
        for file in gsheet_files:
            if file['id'] == gsheet_file_id:
                gsheet_file_name = file['name']
                break
        if gsheet_file_name is None:
            raise Exception(f"File with ID {gsheet_file_id} not found in Google Drive.")
        return gsheet_file_name

    def get_worksheets(self, gsheet_file_id):

      spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId=gsheet_file_id).execute()

      # Get all worksheet names
      sheet_names = [s['properties']['title'] for s in spreadsheet['sheets']]

      return sheet_names

    def get_worksheet_values(self, gsheet_file_id, worksheet_name):

        RANGE_NAME = worksheet_name
        sheet = self.sheets_service.spreadsheets()
        result = sheet.values().get(spreadsheetId=gsheet_file_id, range=RANGE_NAME).execute()
        values = result.get('values', [])
        return values