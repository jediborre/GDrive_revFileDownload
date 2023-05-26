import os
import io
import json
from tqdm import tqdm
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
limiter = False
DOWNLOADED_PATH = 'D:/gdrive_restored/'


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


def get_path(service, file_id):
    file = service.files().get(
        fileId=file_id,
        fields='id, name, parents'
    ).execute()
    file_name = file['name']
    parents = file.get('parents', [])
    if not parents:
        return "/" + file_name
    parent_path = ""
    for parent in parents:
        parent_path += get_path(service, parent) + "/"
    return parent_path + file_name


def get_file_name_from_revision(drive_service, file_id, revision_id):
    revision = drive_service.revisions().get(
        fileId=file_id,
        revisionId=revision_id,
        fields='id, originalFilename'
    ).execute()
    return revision.get('originalFilename')


def write_fileListfromGoogleDrive(drive_service, filename):
    query = (
        "trashed = false "
        "and mimeType != 'application/vnd.google-apps.folder' "
        "and fileExtension = 'foty'"
    )
    fields = (
        "nextPageToken, "
        "files(id, name, createdTime, parents, mimeType, size)"
    )
    results = drive_service.files().list(
        q=query,
        fields=fields
    ).execute()

    files = results.get("files", [])

    while results.get('nextPageToken'):
        print(f"Token: {results.get('nextPageToken')}")
        results = drive_service.files().list(
            q=query,
            fields=fields,
            pageToken=results['nextPageToken']
        ).execute()
        files.extend(results.get("files", []))

    if len(files) > 0:
        print(f'{len(files)} Archivos Encontrados.')
        with open(filename, 'w') as writer:
            writer.write(json.dumps(files))


def getFileRevisionsAndPath(drive_service, db_filename):
    global limiter
    data = {}
    str_list = open(db_filename, 'r').read()
    list_files = json.loads(str_list)
    fecha_evento = datetime.strptime(
        '2023-04-25',
        '%Y-%m-%d'
    ).date()
    for n, file in enumerate(list_files):
        revisiones_correctas = []
        file_id = file['id']
        revisions = drive_service.revisions().list(
            fileId=file_id
        ).execute()
        for m, revision in enumerate(revisions['revisions']):
            revision_id = revision['id']
            revision_fecha = revision['modifiedTime']
            revision_parsed_date = datetime.strptime(
                revision_fecha,
                '%Y-%m-%dT%H:%M:%S.%fZ'
            )
            if revision_parsed_date.date() < fecha_evento:
                revision_nombre = get_file_name_from_revision(
                    drive_service,
                    file_id,
                    revision_id
                )
                revisiones_correctas.append([
                    revision,
                    revision_nombre,
                    revision_fecha,
                    revision_id
                ])
        if len(revisiones_correctas) > 0:
            revision = revisiones_correctas[-1]
            revision_nombre = revision[1]
            revision_fecha = revision[2][:10]
            revision_id = revision[3]
            # file_path = get_path(drive_service, file_id)
            file_data = {
                'id': file_id,
                'revision_id': revision_id,
                'path': '',
                'filename': file['name'],
                'mymeType': file['mimeType'],
                'original_filename': revision_nombre,
                'original_date': revision_fecha,
            }
            print(f'{(n*100)/len(list_files):.2f}% | {n}-{len(list_files)}')
            data[file_id] = file_data
            if limiter:
                if n == 5:
                    break
    with open(f'p_{db_filename}', 'w') as writer:
        writer.write(json.dumps(data))


def delete_file(file_path):
    try:
        os.remove(file_path)
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
    except PermissionError:
        print(f"Permission denied to delete file '{file_path}'.")


def create_folder(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
        print(f"\nFolder '{directory_path}' created")


def download_file(drive_service, file, download):
    global DOWNLOADED_PATH
    done = False
    filename = file['filename']
    original_filename = file['original_filename']
    path = file['path']
    file_id = file['id']
    revision_id = file['revision_id']
    file_path = os.path.dirname(DOWNLOADED_PATH + path[11:])
    create_folder(file_path)
    if download:
        request = drive_service.revisions().get_media(
            fileId=file_id,
            revisionId=revision_id
        )

        file_handle = io.FileIO(f'{file_path}/{original_filename}', 'wb')
        downloader = MediaIoBaseDownload(file_handle, request)

        while not done:
            try:
                status, done = downloader.next_chunk()
                if status:
                    # print((
                    #     f"\n{original_filename} -> "
                    #     f"{int(status.progress() * 100)}%"
                    # ))
                    pass
            except HttpError as e:
                print(f"\n{original_filename} -> X HTTP")
                print(e._get_reason())
                # print(type(e))
                break
            except Exception as e:
                print(f"\n{original_filename} -> X")
                print(type(e))
                # print(e)
                break
            finally:
                if not done:
                    file_handle.close()
                    delete_file(f'downloaded/{original_filename}')

        if done:
            pass
            # print(f'{filename} -> {original_filename}')
    else:
        print(f' Simulated Download {filename} -> {original_filename}')

    return done


def save_DB(db_filename, db):
    with open(db_filename, 'w') as writer:
        writer.write(json.dumps(db))


def googleDrive(drive_service, db_filename):
    global limiter
    dic_files = json.loads(open(db_filename, 'r').read())
    total_files = 5 if limiter else len(dic_files)
    progress_bar = tqdm(total=total_files)
    try:
        for n, file_id in enumerate(dic_files):
            changes = False
            file = dic_files[file_id]
            # original_filename = file['original_filename']
            if file['path'] == '':
                changes = True
                file['path'] = get_path(drive_service, file_id)
            if 'download' not in file:
                changes = True
                file['download'] = False

            if not file['download']:
                downloaded = download_file(drive_service, file, True)
                if downloaded:
                    changes = True
                    file['download'] = True
            else:
                pass
                # print(f'{original_filename} -> Already Downloaded')

            dic_files[file_id] = file
            if changes:
                save_DB(db_filename, dic_files)

            progress_bar.update(1)
            if limiter:
                if n > total_files:
                    break
    except KeyboardInterrupt:
        save_DB(db_filename, dic_files)


def oldgoogleDrive():
    pass
    # Intento 1
    # MARKETING_ROOTID = '1xxeM5EI7m6KkS9GICO6zy-fAml0XhWr3'
    # root_folder = drive_service.files().get(
    #   fileId=MARKETING_ROOTID
    # ).execute()

    # folders = drive_service.files().list(
    #   q="'{}' in parents and name contains '.foty'".format(
    #       root_folder['id']
    #   ),
    #   fields="nextPageToken,
    #   files(id, name, mimeType, createdTime)"
    # ).execute()

    # if not folders:
    #     print("No folders found in your Drive.")
    # else:
    #     print("Your Drive folders:")
    #     for folder in folders['files']:
    #         print(folder)

    # Intento 2
    # fecha_evento = datetime.strptime(
    #     '2023-04-25',
    #     '%Y-%m-%d'
    # ).date()

    # for n, file in enumerate(files):
    #     revisions = drive_service.revisions().list(
    #         fileId=file['id']
    #     ).execute()
    #     revisiones_correctas = []
    #     for m, revision in enumerate(revisions['revisions']):
    #         nombre_revision = get_file_name_from_revision(
    #             drive_service,
    #             file['id'],
    #             revision['id']
    #         )
    #         date_revision = revision['modifiedTime']
    #         p_date_revision = datetime.strptime(
    #             date_revision,
    #             '%Y-%m-%dT%H:%M:%S.%fZ'
    #         )
    #         if p_date_revision.date() < fecha_evento:
    #             revisiones_correctas.append([
    #                 revision,
    #                 nombre_revision,
    #                 date_revision
    #             ])
    #             # print(f"{m + 1} {nombre_revision} {date_revision}")
    #     if len(revisiones_correctas) > 0:
    #         revision_nombre = revisiones_correctas[-1][1]
    #         revision_fecha = revisiones_correctas[-1][2][:10]
    #         file_data = {
    #             'id': file['id'],
    #             'path': get_path(drive_service, file['id']),
    #             'filename': file['name'],
    #             'mymeType': file['mimeType'],
    #             'original_filename': revision_nombre,
    #             'original_date': revision_fecha,
    #             'revision_id': revision['id']
    #         }
    #         print(json.dumps(file_data, indent=4))
    #     if n == 5:
    #         break


def connectGoogleDrive():
    creds = None
    credentials_file = 'token.json'
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.metadata.readonly',
    ]
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
        return build('drive', 'v3', credentials=creds)
    except HttpError as error:
        print(f'An error occurred: {error}')


def main():
    db_file = 'files_from_googleDrove.json'
    db_file_dic = f'p_{db_file}'
    drive_service = connectGoogleDrive()
    if not os.path.exists(db_file):
        write_fileListfromGoogleDrive(drive_service, db_file)
    if not os.path.exists(db_file_dic):
        getFileRevisionsAndPath(drive_service, db_file)
    googleDrive(drive_service, db_file_dic)


if __name__ == '__main__':
    main()
