import sys
import os
sys.path.append(os.path.abspath("c:/Users/usuario_1/VS Code/Dashboard"))
from dotenv import load_dotenv
load_dotenv(os.path.abspath("c:/Users/usuario_1/VS Code/Dashboard/.env"))
from onedrive_downloader import list_onedrive_folder

PASTA_BASE_ONEDRIVE = "Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/Parceiro_Y"
files = list_onedrive_folder(PASTA_BASE_ONEDRIVE)
for f in files:
    print(f.get("name"))
