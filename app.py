import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def get_foty_files(root_dir):
    foty_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if os.path.splitext(filename)[1] == '.foty':
                archivo = os.path.join(dirpath, filename)
                foty_files.append((archivo[19:], os.path.getsize(archivo)))
    return foty_files


def read_affected_files():
    file_path = 'files.tsv'
    foty_files = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            lines = content.split("\n")
            for line in lines:
                if '|' in line:
                    filepath, size = line.split("|")
                    foty_files.append((filepath, size))
    return foty_files


def write_affected_files():
    FOLDER = '//PROPROM/Marketing/'
    print('Encontrando archivos afectados en el server.')
    foty_files = get_foty_files(FOLDER)
    print('Ordenando por tamano.')
    sorted_files = sorted(foty_files, key=lambda x: x[1], reverse=True)
    with open('files.tsv', 'w', encoding='utf-8') as file:
        print(f'Escribiendo {len(sorted_files)} archivos.')
        for filepath, size in sorted_files:
            file.write(f"{filepath}|{size}\n")
        print('Terminado.')
    return sorted_files


def googleDrive(file_name):
    creds = None
    credentials_file = 'token.json'
    SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
    if os.path.exists(credentials_file):
        creds = Credentials.from_authorized_user_file(credentials_file)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    try:
        drive_service = build('drive', 'v3', credentials=creds)

        MARKETING_ROOTID = '1xxeM5EI7m6KkS9GICO6zy-fAml0XhWr3'
        # root_folder = drive_service.files().get(fileId=MARKETING_ROOTID).execute()

        # folders = drive_service.files().list(q="'{}' in parents and name contains '.foty'".format(root_folder['id']), fields="nextPageToken, files(id, name, mimeType, createdTime)").execute()

        # if not folders:
        #     print("No folders found in your Drive.")
        # else:
        #     print("Your Drive folders:")
        #     for folder in folders['files']:
        #         print(folder)
        query = "trashed = false and mimeType != 'application/vnd.google-apps.folder' and fileExtension = 'foty'"

        # Use the files().list() method with the query parameter to retrieve all matching files
        results = drive_service.files().list(q=query,fields="nextPageToken, files(id, name, createdTime, size)").execute()

        files = results.get("files", [])

        # If there are more than 100 files, paginate through the results
        while results.get('nextPageToken'):
            results = drive_service.files().list(q=query,fields="nextPageToken, files(id, name, createdTime, size)",pageToken=results['nextPageToken']).execute()
            files.extend(results.get("files", []))
        
        for item in files:
            print(f'{item["name"]} ({item["id"]})')

    except HttpError as error:
        print(f'An error occurred: {error}')


def main():
    # if not os.path.exists('files.tsv'):
    #     affected_files = write_affected_files()
    # else:
    #     affected_files = read_affected_files()
    # _file = affected_files[0][0]
    # print(f'Hay {len(affected_files)} archivos afectados.')
    _file = ''
    googleDrive(_file)


if __name__ == '__main__':
    main()
