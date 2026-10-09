import msal
import requests
import os
from io import BytesIO

import streamlit as st

@st.cache_data(ttl=1800, show_spinner=False)
def download_excel_from_onedrive(caminho_onedrive):
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    
    user_email = os.getenv("AZURE_USER_EMAIL")

    if not all([tenant_id, client_id, client_secret]):
        raise ValueError("VariÃ¡veis de ambiente AZURE_TENANT_ID, AZURE_CLIENT_ID e AZURE_CLIENT_SECRET devem estar configuradas.")

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret
    )
    
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        access_token = result["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        if ".." in caminho_onedrive:
            raise ValueError("Caminho inválido (Path Traversal não permitido).")
        caminho_onedrive = caminho_onedrive.lstrip('/')
        import urllib.parse
        
        if "Controle Cadastros.xlsx" in caminho_onedrive:
            site_id = "corporativo.sharepoint.com,SITE_ID_PLACEHOLDER,WEB_ID_PLACEHOLDER"
            caminho_encoded = urllib.parse.quote(caminho_onedrive)
            url_file = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{caminho_encoded}:/content"
        else:
            site_path = "Intranet-Qualidade"
            url_drive = f"https://graph.microsoft.com/v1.0/sites/corporativo.sharepoint.com:/sites/{site_path}:/drive"
            resp_drive = requests.get(url_drive, headers=headers)
            if resp_drive.status_code != 200:
                raise Exception(f"Erro ao obter o Drive do SharePoint: HTTP {resp_drive.status_code} - {resp_drive.text}")
                
            drive_id = resp_drive.json().get("id")
            caminho_encoded = urllib.parse.quote(caminho_onedrive)
            url_file = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{caminho_encoded}:/content"
        
        response = requests.get(url_file, headers=headers)
        
        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            raise Exception(f"Erro na Graph API: HTTP {response.status_code} - {response.text}")
    else:
        raise Exception(f"Falha de autenticação com MSAL: {result.get('error')} - {result.get('error_description')}")

@st.cache_data(ttl=1800, show_spinner=False)
def get_onedrive_file_last_modified(caminho_onedrive):
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    
    if not all([tenant_id, client_id, client_secret]):
        return None

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(client_id, authority=authority, client_credential=client_secret)
    
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        access_token = result["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        if ".." in caminho_onedrive:
            raise ValueError("Caminho inválido (Path Traversal não permitido).")
        caminho_onedrive = caminho_onedrive.lstrip('/')
        import urllib.parse
        
        if "Controle Cadastros.xlsx" in caminho_onedrive:
            site_id = "corporativo.sharepoint.com,SITE_ID_PLACEHOLDER,WEB_ID_PLACEHOLDER"
            caminho_encoded = urllib.parse.quote(caminho_onedrive)
            url_file = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{caminho_encoded}"
        else:
            site_path = "Intranet-Qualidade"
            url_drive = f"https://graph.microsoft.com/v1.0/sites/corporativo.sharepoint.com:/sites/{site_path}:/drive"
            resp_drive = requests.get(url_drive, headers=headers)
            if resp_drive.status_code != 200:
                return None
                
            drive_id = resp_drive.json().get("id")
            caminho_encoded = urllib.parse.quote(caminho_onedrive)
            url_file = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{caminho_encoded}"
        
        response = requests.get(url_file, headers=headers)
        
        if response.status_code == 200:
            return response.json().get("lastModifiedDateTime")
    return None

def list_onedrive_folder(caminho_onedrive):
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(client_id, authority=authority, client_credential=client_secret)
    
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        access_token = result["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        if ".." in caminho_onedrive:
            raise ValueError("Caminho inválido (Path Traversal não permitido).")
        caminho_onedrive = caminho_onedrive.lstrip('/')
        import urllib.parse
        
        site_path = "Intranet-Qualidade"
        url_drive = f"https://graph.microsoft.com/v1.0/sites/corporativo.sharepoint.com:/sites/{site_path}:/drive"
        resp_drive = requests.get(url_drive, headers=headers)
        if resp_drive.status_code != 200:
            raise Exception(f"Erro ao obter o Drive do SharePoint: HTTP {resp_drive.status_code} - {resp_drive.text}")
            
        drive_id = resp_drive.json().get("id")
        caminho_encoded = urllib.parse.quote(caminho_onedrive)
        url_list = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{caminho_encoded}:/children"
        
        response = requests.get(url_list, headers=headers)
        
        if response.status_code == 200:
            return response.json().get("value", [])
        else:
            return [] # Pasta não existe ou vazia
    else:
        raise Exception(f"Falha de autenticação com MSAL: {result.get('error')}")


def upload_excel_to_onedrive(caminho_onedrive, file_bytes):
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(client_id, authority=authority, client_credential=client_secret)
    
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        access_token = result["access_token"]
        content_type = "application/json" if caminho_onedrive.endswith(".json") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": content_type}
        
        if ".." in caminho_onedrive:
            raise ValueError("Caminho inválido (Path Traversal não permitido).")
        caminho_onedrive = caminho_onedrive.lstrip('/')
        import urllib.parse
        
        if "Controle Cadastros.xlsx" in caminho_onedrive:
            site_id = "corporativo.sharepoint.com,SITE_ID_PLACEHOLDER,WEB_ID_PLACEHOLDER"
            caminho_encoded = urllib.parse.quote(caminho_onedrive)
            url_upload = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{caminho_encoded}:/content"
        else:
            site_path = "Intranet-Qualidade"
            url_drive = f"https://graph.microsoft.com/v1.0/sites/corporativo.sharepoint.com:/sites/{site_path}:/drive"
            resp_drive = requests.get(url_drive, headers=headers)
            if resp_drive.status_code != 200:
                raise Exception(f"Erro ao obter Drive para Upload: HTTP {resp_drive.status_code}")
                
            drive_id = resp_drive.json().get("id")
            caminho_encoded = urllib.parse.quote(caminho_onedrive)
            url_upload = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{caminho_encoded}:/content"
        
        response = requests.put(url_upload, headers=headers, data=file_bytes)
        
        if response.status_code not in (200, 201):
            raise Exception(f"Erro ao fazer upload na Graph API: HTTP {response.status_code} - {response.text}")
    else:
        raise Exception(f"Falha de autenticação com MSAL: {result.get('error')}")

def download_json_from_onedrive(caminho_onedrive):
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    
    if not all([tenant_id, client_id, client_secret]):
        raise ValueError("Variáveis de ambiente AZURE_TENANT_ID, AZURE_CLIENT_ID e AZURE_CLIENT_SECRET devem estar configuradas.")

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret
    )
    
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        access_token = result["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        if ".." in caminho_onedrive:
            raise ValueError("Caminho inválido (Path Traversal não permitido).")
        caminho_onedrive = caminho_onedrive.lstrip('/')
        import urllib.parse
        
        site_path = "Intranet-Qualidade"
        url_drive = f"https://graph.microsoft.com/v1.0/sites/corporativo.sharepoint.com:/sites/{site_path}:/drive"
        resp_drive = requests.get(url_drive, headers=headers)
        if resp_drive.status_code != 200:
            raise Exception(f"Erro ao obter o Drive do SharePoint: HTTP {resp_drive.status_code} - {resp_drive.text}")
            
        drive_id = resp_drive.json().get("id")
        caminho_encoded = urllib.parse.quote(caminho_onedrive)
        url_file = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{caminho_encoded}:/content"
        
        response = requests.get(url_file, headers=headers)
        
        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            raise Exception(f"Erro na Graph API: HTTP {response.status_code} - {response.text}")
    else:
        raise Exception(f"Falha de autenticação com MSAL: {result.get('error')} - {result.get('error_description')}")
