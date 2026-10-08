import os
import re
import json
import time
import datetime
import pandas as pd
import schedule
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from dotenv import load_dotenv

load_dotenv()

# --- CONEXÃO 1 (MySQL DW) ---
url_conexao = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv("DW_USER"),
    password=os.getenv("DW_PASS"),
    host=os.getenv("DW_HOST"),
    port=int(os.getenv("DW_PORT", 3306)),
    database=os.getenv("DW_NAME")
)
engine_dw = create_engine(url_conexao, pool_pre_ping=True, pool_recycle=1800)

# --- CONEXÃO 2 (Datalake - Postgres) ---
# Atenção: Se for Postgres, use "postgresql+psycopg2" (precisa do pip install psycopg2).
# Se for MySQL, mantenha "mysql+pymysql".
url_conexao2 = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB2_USER"),
    password=os.getenv("DB2_PASS"),
    host=os.getenv("DB2_HOST"),
    port=int(os.getenv("DB2_PORT", 5432)),
    database=os.getenv("DB2_NAME")
)
engine_datalake = create_engine(url_conexao2, pool_pre_ping=True, pool_recycle=1800)

DIRETORIO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DIRETORIO_SAIDA = "/app/data"
os.makedirs(DIRETORIO_SAIDA, exist_ok=True)
ARQUIVO_JSON = os.path.join(DIRETORIO_SAIDA, 'atualizacoes.json')
LOG_PATH = "/app/data/log_execucao.txt"

def gravar_log(mensagem):
    os.makedirs("/app/data", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {mensagem}\n")


def ler_arquivo_sql(caminho):
    with open(caminho, 'r', encoding='utf-8') as arquivo:
        return arquivo.read().strip()


import re
_ILLEGAL_XML_CHARS = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')

def remover_caracteres_ilegais_xml(val):
    if isinstance(val, bytes):
        try:
            val = val.decode('utf-8', errors='ignore')
        except Exception:
            val = str(val)
    if isinstance(val, str):
        return _ILLEGAL_XML_CHARS.sub('', val)
    return val

def ajustar_dataframe(df, query):
    """Respeita a caixa original das colunas e converte para numérico as colunas
    que contêm apenas números. Também limpa caracteres ilegais do XML."""
    novas_colunas = []
    for col in df.columns:
        match = re.search(r'\b' + re.escape(col) + r'\b', query, re.IGNORECASE)
        novas_colunas.append(match.group(0) if match else col.upper())
    df.columns = novas_colunas

    for col in df.columns:
        # Pula as colunas de data/hora para não converter em números (nanossegundos)
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            # Remove fuso horário se houver, pois o openpyxl não suporta
            if getattr(df[col].dtype, 'tz', None) is not None:
                df[col] = df[col].dt.tz_localize(None)
            continue
            
        # Aplica a limpeza em absolutamente todas as colunas para evitar o erro do openpyxl
        df[col] = df[col].apply(remover_caracteres_ilegais_xml)
        
        try:
            if not pd.api.types.is_timedelta64_dtype(df[col]):
                df[col] = pd.to_numeric(df[col])
        except (ValueError, TypeError):
            pass
    return df


def gravar_arquivo_excel(caminho_final, abas):
    """Grava TODAS as abas de um arquivo em uma única abertura da planilha.

    Antes o Aprovadores.xlsx era aberto 4x (uma por aba) e, em cada abertura, o
    openpyxl recarregava e reescrevia a planilha inteira (~1,3 MB). Agora abrimos
    o arquivo uma única vez por arquivo de saída.
    """
    if os.path.exists(caminho_final):
        writer = pd.ExcelWriter(caminho_final, engine='openpyxl',
                                mode='a', if_sheet_exists='replace')
    else:
        writer = pd.ExcelWriter(caminho_final, engine='openpyxl')
    with writer:
        for aba, df in abas:
            df.to_excel(writer, sheet_name=aba, index=False)


def rodar_extracao():
    atualizacoes = {}
    if os.path.exists(ARQUIVO_JSON):
        try:
            with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
                atualizacoes = json.load(f)
        except Exception:
            pass

    # --- MAPEAMENTO DE TAREFAS E ENGINES ---
    # A chave 'motor' indica qual banco usar.
    tarefas = [
        {"arquivo_sql": "Consult_Aprovadores.sql", "arquivo_saida": "Aprovadores.xlsx", "aba": "Plan1", "motor": engine_dw, "painel": "Módulo de Aprovadores"},
        {"arquivo_sql": "Consult_C.Custo.sql", "arquivo_saida": "Aprovadores.xlsx", "aba": "Plan2", "motor": engine_datalake, "painel": "Módulo Centro de Custo"},
        {"arquivo_sql": "Consult_Form.sql", "arquivo_saida": "Aprovadores.xlsx", "aba": "FORM", "motor": engine_datalake, "painel": "Módulo de Aprovadores"},  # banco 2
        {"arquivo_sql": "Consult_Projeto_Alfa.sql", "arquivo_saida": "Projeto_Alfa.xlsx", "aba": "Plan1", "motor": engine_datalake, "painel": "Módulo Empresa_X x Projeto_Alfa"},
        {"arquivo_sql": "Consult_Pendencias_OTIMIZADA.sql", "arquivo_saida": "Aprovadores.xlsx", "aba": "Pendencias", "motor": engine_dw, "painel": "Módulo Centro de Custo"},
        {"arquivo_sql": "Produtos.sql", "arquivo_saida": "Produtos.xlsx", "aba": "Plan1", "motor": engine_datalake, "painel": "Módulo de Produtos"},
        {"arquivo_sql": "Fornecedor.sql", "arquivo_saida": "Produtos.xlsx", "aba": "Plan3", "motor": engine_datalake, "painel": "Módulo de Produtos"}
    ]

    gravar_log("--- INICIANDO EXECUÇÃO DO BOT ---")
    inicio_geral = time.perf_counter()

    # === FASE 1: executar todas as consultas e agrupar os resultados por arquivo ===
    # arquivo_saida -> lista de (aba, df, painel, arquivo_sql)
    resultados = {}
    for tarefa in tarefas:
        arquivo = tarefa['arquivo_saida']
        print(f"Executando consulta para {arquivo} na aba {tarefa['aba']}...")
        try:
            caminho_completo_sql = os.path.join(DIRETORIO, tarefa['arquivo_sql'])
            query = ler_arquivo_sql(caminho_completo_sql)
            query_exec = query.replace('%', '%%')

            t0 = time.perf_counter()
            df = pd.read_sql(query_exec, tarefa['motor'])
            duracao = time.perf_counter() - t0

            df = ajustar_dataframe(df, query)

            if df.empty:
                msg_alerta = (f"ALERTA: A query {tarefa['arquivo_sql']} retornou vazia em "
                              f"{duracao:.1f}s. O arquivo {arquivo} não foi alterado. "
                              f"(Painel impactado: {tarefa['painel']})")
                print(msg_alerta)
                gravar_log(msg_alerta)
                continue

            resultados.setdefault(arquivo, []).append(
                (tarefa['aba'], df, tarefa['painel'], tarefa['arquivo_sql'], duracao)
            )
            print(f"  -> {len(df)} linhas lidas em {duracao:.1f}s")
        except Exception as e:
            msg_erro = f"ERRO: Erro ao consultar {tarefa['arquivo_sql']}. Motivo: {e}"
            print(msg_erro)
            gravar_log(msg_erro)
            raise e

    # === FASE 2: gravar cada arquivo de saída uma única vez ===
    for arquivo, abas in resultados.items():
        caminho_final = os.path.join(DIRETORIO_SAIDA, arquivo)
        try:
            t0 = time.perf_counter()
            gravar_arquivo_excel(caminho_final, [(aba, df) for aba, df, *_ in abas])
            duracao_grav = time.perf_counter() - t0

            agora = datetime.datetime.now().timestamp()
            for aba, df, painel, arquivo_sql, duracao in abas:
                atualizacoes.setdefault(arquivo, {})[aba] = agora
                msg_sucesso = (f"SUCESSO: Aba {aba} de {arquivo} atualizada com {len(df)} "
                               f"linhas (consulta {duracao:.1f}s). (Painel impactado: {painel})")
                print(msg_sucesso)
                gravar_log(msg_sucesso)
            gravar_log(f"INFO: {arquivo} gravado em {duracao_grav:.1f}s "
                       f"({len(abas)} aba(s) em uma única abertura).")

            # --- UPLOAD PARA O SHAREPOINT ---
            try:
                from onedrive_downloader import upload_excel_to_onedrive
                with open(caminho_final, "rb") as f:
                    conteudo = f.read()
                pasta_sharepoint = f"Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/{arquivo}"
                upload_excel_to_onedrive(pasta_sharepoint, conteudo)
                msg_up = f"SUCESSO: {arquivo} sincronizado no SharePoint."
                print(msg_up)
                gravar_log(msg_up)
            except Exception as e_up:
                msg_erro_up = f"ERRO: Falha ao enviar {arquivo} para o SharePoint: {e_up}"
                print(msg_erro_up)
                gravar_log(msg_erro_up)
            # --------------------------------

        except Exception as e:
            msg_erro = f"ERRO: Erro ao gravar {arquivo}. Motivo: {e}"
            print(msg_erro)
            gravar_log(msg_erro)
            raise e

    # === FASE 3: persistir o controle de atualizações (uma única gravação) ===
    try:
        with open(ARQUIVO_JSON, 'w', encoding='utf-8') as f:
            json.dump(atualizacoes, f, indent=4)
    except Exception as e:
        gravar_log(f"ERRO: Falha ao salvar {ARQUIVO_JSON}. Motivo: {e}")

    total = time.perf_counter() - inicio_geral
    gravar_log(f"--- FINALIZANDO EXECUÇÃO DO BOT (tempo total {total:.1f}s) ---\n")


if __name__ == "__main__":
    try:
        rodar_extracao()
    finally:
        engine_dw.dispose()
        engine_datalake.dispose()
