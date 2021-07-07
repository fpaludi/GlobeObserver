from typing import List, Dict
import io
import os
import pickle
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


class GDriveService:
    _SCOPES = ["https://www.googleapis.com/auth/drive"]
    _SERVICE_NAME = "drive"
    _SERVICE_VERSION = "v3"
    _GEN_TOKE_FILE = "token.pickle"

    def __init__(self, cred_file: Path, download_path: Path):
        self._credentials = self._load_credentials(cred_file)
        self._download_path = download_path
        self._client = build(
            self._SERVICE_NAME, self._SERVICE_VERSION, credentials=self._credentials
        )

    @property
    def download_path(self):
        return self._download_path

    @download_path.setter
    def download_path(self, value):
        self._download_path = value

    def _load_credentials(self, cred_file: Path):
        creds = None
        if os.path.exists(self._GEN_TOKE_FILE):
            with open(self._GEN_TOKE_FILE, "rb") as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    cred_file, self._SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self._GEN_TOKE_FILE, "wb") as token:
                pickle.dump(creds, token)
        return creds

    def _run_search(self, file_list):
        result = list()
        page_token = None

        while True:
            file_list.pageToken = page_token
            response = file_list.execute()
            page_token = response.get("nextPageToken", None)
            for file in response.get("files", []):
                result.append(file)
            if not page_token:
                break
        return result

    def _get_folder(self, name: str):
        files = self._client.files()
        folder_filter = files.list(
            q=f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder'",
            spaces="drive",
            fields="nextPageToken, files(id, name)",
        )
        folders = self._run_search(folder_filter)
        return folders

    def list_files(self, folder: str = "", file_extension: str = ".tif") -> List[Dict]:
        folder = self._get_folder(folder)
        query = f"name contains '{file_extension}'"
        if folder:
            query += f" and '{folder[0]['id']}' in parents"
        files = self._client.files()
        file_filter = files.list(
            q=query, spaces="drive", fields="nextPageToken, files(id, name)",
        )
        folders = self._run_search(file_filter)
        return folders

    def _download_file(self, name: str, file_id: str):
        request = self._client.files().get_media(fileId=file_id)
        fh = io.FileIO(self._download_path + name, mode="w")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    def download_file(self, name: str, file_id: str):
        extension = "." + name.split(".")[-1]
        files = self.list_files("drive", file_extension=extension)
        file = [x for x in files if x["name"] == name][0]
        self._download_file(file["name"], file["id"])

    def download_files_from_folder(self, folder: str = "", extension: str = ".tif"):
        files = self.list_files(folder, file_extension=extension)
        for file in files:
            self._download_file(file["name"], file["id"])

    def _remove_file(self, file_id: str):
        self._client.files().delete(fileId=file_id).execute()

    def remove_file(self, name: str, file_id: str):
        extension = "." + name.split(".")[-1]
        files = self.list_files("drive", file_extension=extension)
        file = [x for x in files if x["name"] == name][0]
        self._remove_file(file["id"])

    def remove_files_from_folder(self, folder: str = "", extension: str = ".tif"):
        files = self.list_files(folder, file_extension=extension)
        for file in files:
            self._remove_file(file["id"])

    def remove_folder(self, name: str):
        folder = self._get_folder(name)
        self._remove_file(folder[0]["id"])


class GDriveFactory:
    @classmethod
    def build(cls, download_path="results/") -> GDriveService:
        drive_service = GDriveService("credentials.json", download_path)
        return drive_service
