import sys
import os
sys.path.append(os.path.abspath("c:/Caminho/Para/Seu/Projeto"))
from dotenv import load_dotenv
load_dotenv(os.path.abspath("c:/Caminho/Para/Seu/Projeto/.env"))
from onedrive_downloader import list_onedrive_folder

PASTA_BASE_ONEDRIVE = "Pasta_Compartilhada/Painel_Gestao/Parceiro_Y"
files = list_onedrive_folder(PASTA_BASE_ONEDRIVE)
for f in files:
    print(f.get("name"))
