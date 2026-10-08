import streamlit as st
import pandas as pd
import sqlite3
import os
import io
import re
import unicodedata
from datetime import datetime


# --- CSS CUSTOMIZADO PREMIUM (Inspirado no Parceiro_Y) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    :root {
        --bg-card: #ffffff;
        --bg-card-hover: #f8fafc;
        --bg-metric-pill: rgba(15, 23, 42, 0.05);
        --border-card: #e2e8f0;
        --text-main: #0f172a;
        --text-muted: #64748b;
        --text-pill: #FILIAL_26;
        --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        --shadow-hover: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        
        --color-total: #2563eb;
        --bg-total-card: linear-gradient(135deg, #ffffff 0%, #eff6ff 100%);
        --bg-total-card-hover: linear-gradient(135deg, #ffffff 0%, #dbeafe 100%);
        --bg-total-icon: #eff6ff;
        
        --color-transfer: #8b5cf6;
        --bg-transfer-card: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
        --bg-transfer-card-hover: linear-gradient(135deg, #ffffff 0%, #ede9fe 100%);
        --bg-transfer-icon: #f5f3ff;
        
        --color-inactive: #ef4444;
        --bg-inactive-card: linear-gradient(135deg, #ffffff 0%, #fef2f2 100%);
        --bg-inactive-card-hover: linear-gradient(135deg, #ffffff 0%, #fee2e2 100%);
    }
    
    @media (prefers-color-scheme: dark) {
        :root {
            --bg-card: #1e293b;
            --bg-card-hover: #FILIAL_32;
            --border-card: #FILIAL_26;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2);
            --shadow-hover: 0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.25);
            
            --color-total: #3b82f6;
            --bg-total-card: linear-gradient(135deg, #1e293b 0%, rgba(59, 130, 246, 0.12) 100%);
            --bg-total-card-hover: linear-gradient(135deg, var(--bg-card-hover) 0%, rgba(59, 130, 246, 0.20) 100%);
            
            --color-transfer: #a78bfa;
            --bg-transfer-card: linear-gradient(135deg, #1e293b 0%, rgba(167, 139, 250, 0.12) 100%);
            --bg-transfer-card-hover: linear-gradient(135deg, var(--bg-card-hover) 0%, rgba(167, 139, 250, 0.20) 100%);
            
            --color-inactive: #f87171;
            --bg-inactive-card: linear-gradient(135deg, #1e293b 0%, rgba(239, 68, 68, 0.12) 100%);
            --bg-inactive-card-hover: linear-gradient(135deg, var(--bg-card-hover) 0%, rgba(239, 68, 68, 0.20) 100%);
        }
    }

    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    .metric-card {
        display: flex;
        align-items: center;
        background-color: var(--bg-card);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: var(--shadow-card);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 100%;
        min-height: 115px;
        border: 1px solid var(--border-card);
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-hover);
    }
    
    .metric-card.total { background: var(--bg-total-card); border-left: 5px solid var(--color-total); }
    .metric-card.total:hover { background: var(--bg-total-card-hover); }
    
    .metric-card.transfer { background: var(--bg-transfer-card); border-left: 5px solid var(--color-transfer); }
    .metric-card.transfer:hover { background: var(--bg-transfer-card-hover); }

    .metric-card.inactive { background: var(--bg-inactive-card); border-left: 5px solid var(--color-inactive); }
    .metric-card.inactive:hover { background: var(--bg-inactive-card-hover); }

    .metric-content {
        display: flex;
        flex-direction: column;
    }
    .metric-label {
        font-size: 14px;
        font-weight: 700;
        color: var(--text-muted);
        margin-bottom: 3px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: var(--text-main);
    }

    /* Premium visual styling for tables */
    table {
        width: 100%;
        border-collapse: collapse;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
    }
    thead th {
        background-color: #f1f5f9 !important;
        color: #FILIAL_26 !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 12px;
        padding: 12px 16px !important;
        border-bottom: 2px solid #e2e8f0 !important;
        text-align: left !important;
    }
    tbody td {
        padding: 12px 16px !important;
        font-size: 13px;
        border-bottom: 1px solid #f1f5f9 !important;
        color: #FILIAL_29;
        text-align: left !important;
    }
    tbody tr:hover { background-color: #f8fafc !important; }
    
    @media (prefers-color-scheme: dark) {
        thead th {
            background-color: #1e293b !important;
            color: #cbd5e1 !important;
            border-bottom: 2px solid #FILIAL_26 !important;
        }
        tbody td {
            border-bottom: 1px solid #1e293b !important;
            color: #e2e8f0;
        }
        tbody tr:hover { background-color: #0f172a !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'historico_chips.db')

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from onedrive_downloader import download_excel_from_onedrive

ONEDRIVE_PATH = 'QSMS - Administrativo - Área de Cadastros/Painel Gestão de Cadastros/Contatos/Controle Linhas Corporativas.xlsx'
EXCEL_PATH = 'QSMS - Administrativo - Área de Cadastros/Painel Gestão de Cadastros/Contatos/Controle Linhas Corporativas.xlsx'

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_resource
def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS chips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coligada TEXT,
            descricao TEXT,
            chapa22 TEXT,
            nome TEXT,
            funcao TEXT,
            ramal TEXT,
            numero_corporativo TEXT,
            confirmado TEXT,
            regional TEXT,
            tipo TEXT,
            data_cadastro TEXT,
            dt_devolucao TEXT
        )
    ''')
    
    for col in ['dt_devolucao', 'verificado', 'status_chip']:
        try:
            c.execute(f"SELECT {col} FROM chips LIMIT 1")
        except sqlite3.OperationalError:
            c.execute(f"ALTER TABLE chips ADD COLUMN {col} TEXT DEFAULT ''")
            conn.commit()

    c.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chip_id INTEGER,
            numero_corporativo TEXT,
            acao TEXT,
            antigo_nome TEXT,
            novo_nome TEXT,
            data_acao TEXT,
            detalhes TEXT,
            usuario TEXT DEFAULT '',
            regional TEXT DEFAULT '',
            funcao TEXT DEFAULT '',
            ramal TEXT DEFAULT '',
            empresa TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    
    try:
        c.execute("SELECT usuario FROM historico LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE historico ADD COLUMN usuario TEXT DEFAULT ''")
        conn.commit()
        
    for col in ['regional', 'funcao', 'ramal', 'empresa']:
        try:
            c.execute(f"SELECT {col} FROM historico LIMIT 1")
        except sqlite3.OperationalError:
            c.execute(f"ALTER TABLE historico ADD COLUMN {col} TEXT DEFAULT ''")
            conn.commit()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    
    import os
    from dotenv import load_dotenv
    load_dotenv()
    user_gabriel = os.getenv("TELEFONE_USER_GABRIEL", "usuario_1")
    pass_gabriel = os.getenv("TELEFONE_PWD_GABRIEL")
    
    user_dirlei = os.getenv("TELEFONE_USER_DIRLEI", "usuario_3")
    pass_dirlei = os.getenv("TELEFONE_PWD_DIRLEI")
    
    user_bianca = os.getenv("TELEFONE_USER_BIANCA", "usuario_4")
    pass_bianca = os.getenv("TELEFONE_PWD_BIANCA")

    # Inserir usuários caso não existam
    if pass_gabriel:
        c.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", (user_gabriel, pass_gabriel))
        c.execute("UPDATE users SET password = ? WHERE username = ?", (pass_gabriel, user_gabriel))
    if pass_dirlei:
        c.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", (user_dirlei, pass_dirlei))
        c.execute("UPDATE users SET password = ? WHERE username = ?", (pass_dirlei, user_dirlei))
    if pass_bianca:
        c.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", (user_bianca, pass_bianca))
        c.execute("UPDATE users SET password = ? WHERE username = ?", (pass_bianca, user_bianca))
        
    conn.commit()
    
    # Forçar alteração de status ESTOQUE para ATIVO
    c.execute("UPDATE chips SET status_chip = 'ATIVO' WHERE status_chip = 'ESTOQUE'")
    
    # Corrigir chips importados da planilha sem status definido (vazios/nan) para ATIVO
    c.execute("UPDATE chips SET status_chip = 'ATIVO' WHERE status_chip IN ('nan', 'NaN', 'None', '') OR status_chip IS NULL")
    
    # Atualizar padronização de regionais
    c.execute("UPDATE chips SET regional = 'REGIONAL LONDRINA' WHERE regional = 'LONDRINA'")
    c.execute("UPDATE chips SET regional = 'REGIONAL NOROESTE' WHERE regional = 'CIANORTE'")
    c.execute("UPDATE historico SET regional = 'REGIONAL LONDRINA' WHERE regional = 'LONDRINA'")
    c.execute("UPDATE historico SET regional = 'REGIONAL NOROESTE' WHERE regional = 'CIANORTE'")
    
    # Atualizar VERIFICADO de OK para SIM
    c.execute("UPDATE chips SET verificado = 'SIM' WHERE UPPER(TRIM(verificado)) = 'OK'")
    
    conn.commit()
    
    # Importar do excel se o BD estiver vazio
    c.execute('SELECT COUNT(*) FROM chips')
    if c.fetchone()[0] == 0:
        try:
            arquivo_excel = download_excel_from_onedrive(ONEDRIVE_PATH)
            df = pd.read_excel(arquivo_excel, sheet_name='Plan1')
            df.columns = [str(c).strip().upper() for c in df.columns]
            cols = [col for col in df.columns if not col.startswith('UNNAMED:')]
            df = df[cols].dropna(axis=1, how='all')
            
            for _, row in df.iterrows():
                num = str(row.get('NÚMERO', row.get('NUMERO', row.get('NÚMERO CORPORATIVO', '')))).strip()
                if num and num != 'nan':
                    c.execute('''
                        INSERT INTO chips (coligada, descricao, chapa22, nome, funcao, ramal, numero_corporativo, confirmado, regional, tipo, data_cadastro, dt_devolucao, verificado, status_chip)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(row.get('EMPRESA', row.get('COLIGADA', ''))),
                        str(row.get('OBSERVAÇÃO', row.get('OBSERVACAO', row.get('DESCRICAO', '')))),
                        str(row.get('CHAPA', row.get('CHAPA22', ''))),
                        str(row.get('NOME', '')),
                        str(row.get('FUNÇÃO', row.get('FUNCAO', ''))),
                        str(row.get('RAMAL', '')),
                        num,
                        "", 
                        str(row.get('DEPARTAMENTO/REGIONAL', row.get('DEPARTAMENTO', row.get('REGIONAL', '')))),
                        str(row.get('TIPO', '')),
                        str(row.get('DT ENTREGA', row.get('DATA ENTREGA', row.get('DATA', '')))),
                        str(row.get('DT DEVOLUCAO', row.get('DATA DEVOLUCAO', ''))),
                        str(row.get('VERIFICADO?', '')),
                        str(row.get('STATUS', ''))
                    ))
            conn.commit()
        except Exception as e:
            st.error("Falha crítica ao acessar o SharePoint.")
            st.stop()
            
    conn.close()

init_db()

# --- FUNÇÕES DE BD ---
def get_all_chips():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM chips", conn)
    conn.close()
    
    # Remove registros duplicados para o mesmo número.
    # Prioriza manter o registro que estiver 'INATIVO', ou então o de maior ID.
    if not df.empty:
        df['status_peso'] = df['status_chip'].astype(str).str.strip().str.upper().apply(lambda x: 1 if x == 'INATIVO' else 0)
        df = df.sort_values(by=['status_peso', 'id']).drop_duplicates(subset=['numero_corporativo'], keep='last')
        df = df.drop(columns=['status_peso'])
        
    return df

def get_history():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM historico ORDER BY data_acao DESC", conn)
    conn.close()
    return df

def sync_to_excel():
    if os.path.exists(EXCEL_PATH):
        try:
            df = get_all_chips()
            excel_cols = {
                'numero_corporativo': 'NUMERO',
                'nome': 'NOME',
                'funcao': 'FUNÇÃO',
                'coligada': 'EMPRESA',
                'regional': 'DEPARTAMENTO/REGIONAL',
                'descricao': 'OBSERVAÇÃO',
                'verificado': 'VERIFICADO?',
                'data_cadastro': 'DT ENTREGA',
                'dt_devolucao': 'DT DEVOLUCAO',
                'status_chip': 'STATUS'
            }
            for db_col in excel_cols.keys():
                if db_col not in df.columns:
                    df[db_col] = ''
            
            df_export = df[list(excel_cols.keys())].rename(columns=excel_cols)
            df_hist = get_history()
            
            with pd.ExcelWriter(EXCEL_PATH, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                df_export.to_excel(writer, sheet_name='Plan1', index=False)
                if not df_hist.empty:
                    df_hist.to_excel(writer, sheet_name='BD', index=False)
            return True, ""
        except Exception as e:
            return False, str(e)
    return False, "Arquivo não encontrado"

def add_chip(dados):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO chips (coligada, descricao, chapa22, nome, funcao, ramal, numero_corporativo, confirmado, regional, tipo, data_cadastro, dt_devolucao, verificado, status_chip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', dados)
    chip_id = c.lastrowid
    
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usuario = st.session_state.get('username', 'Sistema')
    c.execute('''
        INSERT INTO historico (chip_id, numero_corporativo, acao, antigo_nome, novo_nome, data_acao, detalhes, usuario, regional, funcao, ramal, empresa)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (chip_id, dados[6], 'INCLUSÃO', '', dados[3], data_atual, 'Novo chip cadastrado', usuario, dados[8], dados[4], dados[5], dados[0]))
    
    conn.commit()
    conn.close()
    return sync_to_excel()

def transfer_chip(chip_id, num_corp, antigo_nome, novo_nome, nova_funcao, nova_empresa, nova_regional, data_entrega, novo_ramal):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE chips 
        SET nome = ?, funcao = ?, coligada = ?, regional = ?, data_cadastro = ?, ramal = ?, chapa22 = '', status_chip = 'ATIVO', descricao = ''
        WHERE id = ?
    ''', (novo_nome, nova_funcao, nova_empresa, nova_regional, data_entrega, novo_ramal, chip_id))
    
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usuario = st.session_state.get('username', 'Sistema')
    c.execute('''
        INSERT INTO historico (chip_id, numero_corporativo, acao, antigo_nome, novo_nome, data_acao, detalhes, usuario, regional, funcao, ramal, empresa)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (chip_id, num_corp, 'TRANSFERÊNCIA', antigo_nome, novo_nome, data_atual, f'Transferido de {antigo_nome} para {novo_nome} (Entregue em: {data_entrega})', usuario, nova_regional, nova_funcao, novo_ramal, nova_empresa))
    
    conn.commit()
    conn.close()
    return sync_to_excel()

def update_chip_info(chip_id, novo_numero, novo_nome, nova_funcao, nova_empresa, nova_regional, nova_obs, nova_data_entrega, nova_data_devolucao, novo_conferido, antigo_numero, antigo_nome, novo_status):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE chips 
        SET numero_corporativo = ?, nome = ?, funcao = ?, coligada = ?, regional = ?, descricao = ?, data_cadastro = ?, dt_devolucao = ?, verificado = ?, status_chip = ?
        WHERE id = ?
    ''', (novo_numero, novo_nome, nova_funcao, nova_empresa, nova_regional, nova_obs, nova_data_entrega, nova_data_devolucao, novo_conferido, novo_status, chip_id))
    
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usuario = st.session_state.get('username', 'Sistema')
    c.execute('''
        INSERT INTO historico (chip_id, numero_corporativo, acao, antigo_nome, novo_nome, data_acao, detalhes, usuario, regional, funcao, ramal, empresa)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (chip_id, novo_numero, 'CORREÇÃO', antigo_nome, novo_nome, data_atual, 'Informações do chip corrigidas.', usuario, nova_regional, nova_funcao, '', nova_empresa))
    
    conn.commit()
    conn.close()
    return sync_to_excel()

def delete_chip(chip_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM chips WHERE id = ?", (chip_id,))
    c.execute("DELETE FROM historico WHERE chip_id = ?", (chip_id,))
    conn.commit()
    conn.close()
    return sync_to_excel()

def check_login(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    return user is not None

def change_password(username, old_pass, new_pass):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, old_pass))
    if c.fetchone():
        c.execute("UPDATE users SET password = ? WHERE username = ?", (new_pass, username))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False
def remove_accents(input_str):
    if not isinstance(input_str, str):
        return input_str
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def search_chips_dataframe(df, pesquisa):
    if not pesquisa:
        return df
    mask1 = df.astype(str).apply(lambda x: x.str.contains(pesquisa, case=False, regex=False)).any(axis=1)
    pesquisa_limpa = re.sub(r'[\(\)\-\s]', '', pesquisa)
    if pesquisa_limpa:
        df_view_limpo = df.astype(str).replace(r'[\(\)\-\s]', '', regex=True)
        mask2 = df_view_limpo.apply(lambda x: x.str.contains(pesquisa_limpa, case=False, regex=False)).any(axis=1)
        return df[mask1 | mask2]
    return df[mask1]

def prepare_display_dataframe(df):
    colunas_map = {
        'numero_corporativo': 'NUMERO',
        'nome': 'NOME',
        'funcao': 'FUNÇÃO',
        'coligada': 'EMPRESA',
        'regional': 'DEPARTAMENTO/REGIONAL',
        'descricao': 'OBSERVAÇÃO',
        'verificado': 'VERIFICADO?',
        'data_cadastro': 'DT ENTREGA',
        'dt_devolucao': 'DT DEVOLUCAO',
        'status_chip': 'STATUS',
        'tipo': 'TIPO',
        'ramal': 'RAMAL'
    }
    
    for col in colunas_map.keys():
        if col not in df.columns:
            df[col] = ""
            
    df_display = df[list(colunas_map.keys())].rename(columns=colunas_map)
    df_display = df_display.fillna("")
    df_display = df_display.astype(str).replace(['nan', 'NaN', 'NaT', 'None', '<NA>', 'nan.0'], '')
    
    def format_date_br(val):
        val_str = str(val).strip()
        if not val_str or val_str.lower() in ['nan', 'none', '<na>', 'nat']:
            return ''
        if len(val_str) >= 10 and val_str[4] == '-' and val_str[7] == '-':
            try:
                return datetime.strptime(val_str[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except:
                pass
        return val_str

    if 'DT ENTREGA' in df_display.columns:
        df_display['DT ENTREGA'] = df_display['DT ENTREGA'].apply(format_date_br)
    if 'DT DEVOLUCAO' in df_display.columns:
        df_display['DT DEVOLUCAO'] = df_display['DT DEVOLUCAO'].apply(format_date_br)
    
    if 'DEPARTAMENTO/REGIONAL' in df_display.columns:
        df_display['DEPARTAMENTO/REGIONAL'] = df_display['DEPARTAMENTO/REGIONAL'].str.strip().str.upper()
    if 'EMPRESA' in df_display.columns:
        df_display['EMPRESA'] = df_display['EMPRESA'].str.strip().str.upper()
    
    def formata_status(val):
        val_str = str(val).strip().upper()
        if val_str == 'ATIVO':
            return '✅ ATIVO'
        elif val_str == 'INATIVO':
            return '❌ INATIVO'
        return val

    if 'STATUS' in df_display.columns:
        df_display['STATUS'] = df_display['STATUS'].apply(formata_status)
    
    df_display['RAMAL'] = df_display['RAMAL'].apply(lambda x: str(x).split('.')[0][:4] if x else '')
    return df_display

import auth

auth.exigir_login(
    painel_nome="Controle Telefones",
    titulo_painel="Controle Telefones",
    subtitulo="Gestão de Linhas Corporativas e Chips",
    icone="📱"
)

# Mantém compatibilidade com o histórico do BD interno
st.session_state['username'] = st.session_state.get('username_logado', 'Sistema')

st.title("📱 Painel de Controle de Linhas Corporativas")
st.markdown("Gerenciamento de chips, inclusões e transferências de responsabilidade.")

df_chips = get_all_chips()
total_cadastradas = len(df_chips)
total_inativos = len(df_chips[df_chips['status_chip'].astype(str).str.strip().str.upper() == 'INATIVO'])
df_hist = get_history()
total_transferencias = len(df_hist[df_hist['acao'] == 'TRANSFERÊNCIA'])

# KPIs
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
        <div class="metric-card total">
            <div class="metric-content">
                <div class="metric-label">Linhas Cadastradas</div>
                <div class="metric-value">{total_cadastradas}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
        <div class="metric-card inactive">
            <div class="metric-content">
                <div class="metric-label">Linhas Inativas</div>
                <div class="metric-value">{total_inativos}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
        <div class="metric-card transfer">
            <div class="metric-content">
                <div class="metric-label">Transferências</div>
                <div class="metric-value">{total_transferencias}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Tabs
tab_lista, tab_novo, tab_inativar, tab_historico = st.tabs([
    "📋 Lista de Chips", 
    "➕ Incluir Novo Chip", 
    "❌ Inativar Chips",
    "🕰️ Histórico / Logs"
])

with tab_lista:
    st.subheader("Base Atual de Chips", divider="blue")
    
    def clear_filters():
        st.session_state['pesquisa_lista'] = ""
        st.session_state['empresa_lista'] = "Todas"
        st.session_state['depto_lista'] = "Todos"
        st.session_state['status_lista'] = "Todos"

    col_pesq, col_btn, col_empty = st.columns([4, 2, 4])
    with col_pesq:
        pesquisa = st.text_input("🔍 Pesquisar por Nome ou Número", placeholder="Ex: João, 41999999999", key="pesquisa_lista")
    with col_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        st.button("🧹 Limpar Filtros", use_container_width=True, on_click=clear_filters)
    
    df_view = search_chips_dataframe(df_chips.copy(), pesquisa)
    df_display = prepare_display_dataframe(df_view)
    
    # Filtros na Interface
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        opcoes_empresa = ["Todas"] + sorted([x for x in df_display['EMPRESA'].unique() if x])
        f_empresa = st.selectbox("Filtrar por Empresa", opcoes_empresa, key="empresa_lista")
    with col_f2:
        deptos_originais = [str(x) for x in df_display['DEPARTAMENTO/REGIONAL'].unique() if x]
        opcoes_depto_sem_acento = sorted(list(set([remove_accents(x).upper() for x in deptos_originais])))
        opcoes_depto = ["Todos"] + opcoes_depto_sem_acento
        f_depto = st.selectbox("Filtrar por Departamento", opcoes_depto, key="depto_lista")
    with col_f3:
        opcoes_status = ["Todos"] + sorted([x for x in df_display['STATUS'].unique() if x])
        f_status = st.selectbox("Filtrar por Status", opcoes_status, key="status_lista")
        
    # Aplicar Filtros
    if f_empresa != "Todas":
        df_display = df_display[df_display['EMPRESA'] == f_empresa]
    if f_depto != "Todos":
        df_display = df_display[df_display['DEPARTAMENTO/REGIONAL'].astype(str).apply(lambda x: remove_accents(x).upper()) == f_depto]
    if f_status != "Todos":
        df_display = df_display[df_display['STATUS'] == f_status]
    
    # Ordem EXATA da planilha Final (Ramal e Tipo ficam de fora da visão para espelhar a planilha perfeitamente)
    ordem = ['NUMERO', 'NOME', 'FUNÇÃO', 'EMPRESA', 'DEPARTAMENTO/REGIONAL', 'OBSERVAÇÃO', 'VERIFICADO?', 'DT ENTREGA', 'DT DEVOLUCAO', 'STATUS']
    df_display = df_display[ordem]
    
    c_btn1, c_btn2, c_btn3 = st.columns([1, 1, 1])
    with c_btn3:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df_display.to_excel(writer, sheet_name='Chips', index=False)
        st.download_button(
            label="📥 Exportar Lista (Excel)",
            data=excel_buffer.getvalue(),
            file_name=f"Controle_Chips_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    def render_transfer_form(chip_selecionado):
        chip_id = chip_selecionado['id']
        mode_key = f"mode_{chip_id}"
        
        if mode_key not in st.session_state:
            st.session_state[mode_key] = "view"
            
        def clean_nan(val):
            return "" if str(val).strip().lower() in ['nan', 'none', '<na>', 'nat', ''] else str(val)

        if st.session_state[mode_key] == "view":
            st.markdown("**Informações Atuais**")
            c_atual1, c_atual2 = st.columns(2)
            with c_atual1:
                st.text_input("Número", value=clean_nan(chip_selecionado['numero_corporativo']), disabled=True, key=f"v_num_{chip_id}")
                st.text_input("Responsável Atual", value=clean_nan(chip_selecionado['nome']), disabled=True, key=f"v_nome_{chip_id}")
                st.text_input("Função", value=clean_nan(chip_selecionado.get('funcao', '')), disabled=True, key=f"v_func_{chip_id}")
            with c_atual2:
                st.text_input("Empresa", value=clean_nan(chip_selecionado['coligada']), disabled=True, key=f"v_emp_{chip_id}")
                st.text_input("Regional", value=clean_nan(chip_selecionado['regional']), disabled=True, key=f"v_reg_{chip_id}")
                st.text_input("Observações", value=clean_nan(chip_selecionado['descricao']), disabled=True, key=f"v_obs_{chip_id}")
            
            st.markdown("---")
            
            st.markdown("**Histórico Deste Número**")
            chip_hist = df_hist[df_hist['chip_id'] == chip_id]
            if not chip_hist.empty:
                chip_hist = chip_hist.sort_values(by='data_acao', ascending=False)
                st.dataframe(
                    chip_hist[['data_acao', 'acao', 'antigo_nome', 'novo_nome', 'usuario']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "data_acao": st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY HH:mm"),
                        "acao": st.column_config.TextColumn("Ação"),
                        "antigo_nome": st.column_config.TextColumn("Responsável Anterior"),
                        "novo_nome": st.column_config.TextColumn("Novo Responsável"),
                        "usuario": st.column_config.TextColumn("Feito por")
                    }
                )
            else:
                st.info("Nenhuma movimentação encontrada para este número.")
                
            st.markdown("---")
            cb1, cb2, cb3 = st.columns(3)
            with cb1:
                if st.button("✏️ Alterar / Corrigir", use_container_width=True, key=f"btn_alt_{chip_id}"):
                    st.session_state[mode_key] = "edit"
                    st.rerun()
            with cb2:
                if st.button("🔄 Transferir", use_container_width=True, key=f"btn_trans_{chip_id}"):
                    st.session_state[mode_key] = "transfer"
                    st.rerun()
            with cb3:
                if st.button("🗑️ Excluir", use_container_width=True, key=f"btn_del_{chip_id}"):
                    st.session_state[mode_key] = "delete"
                    st.rerun()
                    
        elif st.session_state[mode_key] == "delete":
            st.warning("⚠️ Tem certeza que deseja excluir permanentemente este chip? O registro será apagado do sistema e da planilha.")
            c_del1, c_del2 = st.columns(2)
            with c_del1:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state[mode_key] = "view"
                    st.rerun()
            with c_del2:
                if st.button("🗑️ Confirmar Exclusão", type="primary", use_container_width=True):
                    status_sync, erro_sync = delete_chip(int(chip_id))
                    if not status_sync and erro_sync:
                        st.warning(f"Excluído do banco, mas erro ao sync com Excel: {erro_sync}")
                    else:
                        st.success("Chip excluído com sucesso!")
                    if "tabela_chips" in st.session_state:
                        del st.session_state["tabela_chips"]
                    st.session_state[mode_key] = "view"
                    st.rerun()
                    
        elif st.session_state[mode_key] == "edit":
            st.markdown("**Modo de Edição / Correção**")
            with st.form(f"form_edit_{chip_id}"):
                c_edit1, c_edit2 = st.columns(2)
                
                def parse_date_local(val):
                    val_str = str(val).strip()
                    if not val_str or val_str.lower() in ['nan', 'none', '<na>', 'nat']:
                        return None
                    try:
                        if len(val_str) >= 10 and val_str[4] == '-' and val_str[7] == '-':
                            return datetime.strptime(val_str[:10], "%Y-%m-%d").date()
                        elif len(val_str) >= 10 and val_str[2] == '/' and val_str[5] == '/':
                            return datetime.strptime(val_str[:10], "%d/%m/%Y").date()
                    except: pass
                    return None
                
                with c_edit1:
                    e_numero = st.text_input("Número *", value=clean_nan(chip_selecionado['numero_corporativo']))
                    e_nome = st.text_input("Responsável Atual *", value=clean_nan(chip_selecionado['nome']))
                    e_funcao = st.text_input("Função", value=clean_nan(chip_selecionado.get('funcao', '')))
                    e_data_entrega = st.date_input("Data de Entrega (DD/MM/AAAA)", value=parse_date_local(clean_nan(chip_selecionado.get('data_cadastro', ''))), format="DD/MM/YYYY")
                    c_conf, c_stat = st.columns(2)
                    with c_conf:
                        val_conferido = clean_nan(chip_selecionado.get('verificado', '')).strip().upper()
                        conferido_opcoes = ["", "SIM", "NÃO", "NAO"]
                        
                        # Map NAO to NÃO or vice versa if you want to be strict. I'll just use SIM/NÃO.
                        if val_conferido == "NAO":
                            val_conferido = "NÃO"
                        
                        opcoes_finais = ["", "SIM", "NÃO"]
                        idx_conferido = opcoes_finais.index(val_conferido) if val_conferido in opcoes_finais else 0
                        e_conferido = st.selectbox("Conferido?", options=opcoes_finais, index=idx_conferido)
                    
                    with c_stat:
                        status_opcoes = ["ATIVO", "A CONFIRMAR", "DISPONIVEL EM ESTOQUE", "INATIVO"]
                        val_status = clean_nan(chip_selecionado.get('status_chip', '')).strip().upper()
                        if val_status and val_status not in status_opcoes:
                            status_opcoes.append(val_status)
                        idx_status = status_opcoes.index(val_status) if val_status in status_opcoes else 0
                        e_status = st.selectbox("Status", options=status_opcoes, index=idx_status)
                with c_edit2:
                    empresas_opcoes = ["", "EMPRESA_01", "EMPRESA_01 EMPRESA_02", "CONSORCIO PROJETO_ALFA", "FAMILIA", "MERCADO MUNICIPAL"]
                    val_empresa = clean_nan(chip_selecionado['coligada'])
                    val_emp_upper = val_empresa.strip().upper() if val_empresa else ""
                    if val_emp_upper and val_emp_upper not in empresas_opcoes:
                        empresas_opcoes.append(val_emp_upper)
                    idx_empresa = empresas_opcoes.index(val_emp_upper) if val_emp_upper in empresas_opcoes else 0
                    e_empresa = st.selectbox("Empresa", options=empresas_opcoes, index=idx_empresa)
                    
                    regionais_opcoes = ["", "FAMILIA", "MERCADO MUNICIPAL", "QSMS", "ENGENHARIA", "SECRETARIA GERAL", "GESTÃO DE PESSOAS", "FINANCEIRO", "COMERCIAL", "GAO", "GESTÃO DE CONTRATOS", "SUPRIMENTOS", "TI", "DIRETORIA", "RECEPÇÃO", "REGIONAL NOROESTE", "REGIONAL SEARA", "REGIONAL LONDRINA", "REGIONAL IMBAU", "REGIONAL LESTE", "REGIONAL PROJETO_ALFA"]
                    val_regional = clean_nan(chip_selecionado['regional'])
                    val_reg_upper = val_regional.strip().upper() if val_regional else ""
                    if val_reg_upper and val_reg_upper not in regionais_opcoes:
                        regionais_opcoes.append(val_reg_upper)
                    idx_regional = regionais_opcoes.index(val_reg_upper) if val_reg_upper in regionais_opcoes else 0
                    e_regional = st.selectbox("Regional", options=regionais_opcoes, index=idx_regional)
                    e_obs = st.text_input("Observações", value=clean_nan(chip_selecionado['descricao']))
                    e_data_devolucao = st.date_input("Data de Devolução (DD/MM/AAAA)", value=parse_date_local(clean_nan(chip_selecionado.get('dt_devolucao', ''))), format="DD/MM/YYYY")
                    
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    btn_cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)
                with c_btn2:
                    btn_save = st.form_submit_button("💾 Salvar Correções", type="primary", use_container_width=True)
                    
                if btn_cancel:
                    st.session_state[mode_key] = "view"
                    st.rerun()
                if btn_save:
                    if e_numero and e_nome:
                        str_data_entrega = e_data_entrega.strftime("%d/%m/%Y") if e_data_entrega else ""
                        str_data_devolucao = e_data_devolucao.strftime("%d/%m/%Y") if e_data_devolucao else ""
                        status_sync, erro_sync = update_chip_info(
                            int(chip_id), e_numero, e_nome, e_funcao, e_empresa, e_regional, e_obs, str_data_entrega, str_data_devolucao, e_conferido,
                            chip_selecionado['numero_corporativo'], chip_selecionado['nome'], e_status
                        )
                        if not status_sync and erro_sync:
                            st.warning(f"Erro ao sync com Excel: {erro_sync}")
                        else:
                            st.success("Informações atualizadas com sucesso!")
                        
                        if "tabela_chips" in st.session_state:
                            del st.session_state["tabela_chips"]
                        st.session_state[mode_key] = "view"
                        st.rerun()
                    else:
                        st.error("Número e Responsável são obrigatórios.")
                        
        elif st.session_state[mode_key] == "transfer":
            st.markdown("**Informações Atuais**")
            c_atual1, c_atual2 = st.columns(2)
            with c_atual1:
                st.text_input("Número", value=clean_nan(chip_selecionado['numero_corporativo']), disabled=True, key=f"t_num_{chip_id}")
                st.text_input("Responsável Atual", value=clean_nan(chip_selecionado['nome']), disabled=True, key=f"t_nome_{chip_id}")
                st.text_input("Função", value=clean_nan(chip_selecionado.get('funcao', '')), disabled=True, key=f"t_func_{chip_id}")
            with c_atual2:
                st.text_input("Empresa", value=clean_nan(chip_selecionado['coligada']), disabled=True, key=f"t_emp_{chip_id}")
                st.text_input("Regional", value=clean_nan(chip_selecionado['regional']), disabled=True, key=f"t_reg_{chip_id}")
                st.text_input("Observações", value=clean_nan(chip_selecionado['descricao']), disabled=True, key=f"t_obs_{chip_id}")
            
            st.markdown("---")
            st.markdown("**Novo Responsável (Transferência)**")
            with st.form(f"form_transferencia_popup_{chip_id}"):
                c1, c2 = st.columns(2)
                with c1:
                    t_nome = st.text_input("Nome *")
                    t_funcao = st.text_input("Função")
                    t_ramal = st.text_input("Ramal")
                with c2:
                    empresas_opcoes = ["", "EMPRESA_01", "EMPRESA_01 EMPRESA_02", "CONSORCIO PROJETO_ALFA", "FAMILIA", "MERCADO MUNICIPAL"]
                    t_empresa = st.selectbox("Empresa", options=empresas_opcoes)
                    
                    regionais_opcoes = ["", "FAMILIA", "MERCADO MUNICIPAL", "QSMS", "ENGENHARIA", "SECRETARIA GERAL", "GESTÃO DE PESSOAS", "FINANCEIRO", "COMERCIAL", "GAO", "GESTÃO DE CONTRATOS", "SUPRIMENTOS", "TI", "DIRETORIA", "RECEPÇÃO", "REGIONAL NOROESTE", "REGIONAL SEARA", "REGIONAL LONDRINA", "REGIONAL IMBAU", "REGIONAL LESTE", "REGIONAL PROJETO_ALFA"]
                    t_regional = st.selectbox("Departamento/Regional", options=regionais_opcoes)
                    t_data_entrega = st.date_input("Data de Entrega (DD/MM/AAAA)", format="DD/MM/YYYY")
                    
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    btn_cancel_t = st.form_submit_button("❌ Cancelar", use_container_width=True)
                with c_btn2:
                    btn_transf = st.form_submit_button("🔄 Confirmar Transferência", type="primary", use_container_width=True)
                    
                if btn_cancel_t:
                    st.session_state[mode_key] = "view"
                    st.rerun()
                if btn_transf:
                    if t_nome:
                        data_entrega_str = t_data_entrega.strftime("%d/%m/%Y")
                        status_sync, erro_sync = transfer_chip(
                            int(chip_id), 
                            chip_selecionado['numero_corporativo'],
                            chip_selecionado['nome'],
                            t_nome, t_funcao, t_empresa, t_regional, data_entrega_str, t_ramal
                        )
                        if not status_sync and erro_sync:
                            st.warning(f"Salvo no banco, mas erro ao sync com Excel: {erro_sync}")
                        else:
                            st.success(f"Linha transferida para {t_nome}! (Marcado como ATIVO automaticamente)")
                        
                        if "tabela_chips" in st.session_state:
                            del st.session_state["tabela_chips"]
                        st.session_state[mode_key] = "view"
                        st.rerun()
                    else:
                        st.error("O Novo Nome é obrigatório.")

    if hasattr(st, "dialog"):
        @st.dialog("Transferir Responsabilidade", width="large")
        def show_popup(chip_selecionado):
            render_transfer_form(chip_selecionado)
    elif hasattr(st, "experimental_dialog"):
        @st.experimental_dialog("Transferir Responsabilidade", width="large")
        def show_popup(chip_selecionado):
            render_transfer_form(chip_selecionado)
    else:
        def show_popup(chip_selecionado):
            st.markdown("---")
            st.subheader(f"Transferir Responsabilidade - {chip_selecionado['numero_corporativo']}")
            render_transfer_form(chip_selecionado)
            st.markdown("---")

    df_display.insert(0, "Ação", False)
    
    edited_df = st.data_editor(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ação": st.column_config.CheckboxColumn("Alt/Transf", help="Selecione para transferir", default=False)
        },
        disabled=df_display.columns.drop("Ação"),
        key="tabela_chips"
    )
    
    selected_rows = edited_df[edited_df["Ação"] == True]
    if not selected_rows.empty:
        selected_num = selected_rows.iloc[0]['NUMERO']
        chip_sel = df_chips[df_chips['numero_corporativo'] == selected_num].iloc[0]
        show_popup(chip_sel)
        
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("👀 Ver Últimas Movimentações (Entregas e Transferências)", expanded=False):
        movs = df_hist[df_hist['acao'] == 'TRANSFERÊNCIA']
        if not movs.empty:
            movs = movs.sort_values(by='data_acao', ascending=False).head(30)
            st.dataframe(
                movs[['data_acao', 'numero_corporativo', 'antigo_nome', 'novo_nome', 'usuario']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "data_acao": st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY HH:mm"),
                    "numero_corporativo": st.column_config.TextColumn("Número"),
                    "antigo_nome": st.column_config.TextColumn("Responsável Anterior"),
                    "novo_nome": st.column_config.TextColumn("Novo Responsável"),
                    "usuario": st.column_config.TextColumn("Feito por")
                }
            )
        else:
            st.info("Nenhuma entrega de chip registrada até o momento.")

with tab_novo:
    st.subheader("Cadastro de Nova Linha", divider="blue")
    with st.form("form_novo_chip"):
        c1, c2 = st.columns(2)
        with c1:
            n_ddd = st.text_input("DDD *", max_chars=2, placeholder="Ex: 41")
            n_num = st.text_input("Número *", max_chars=9, placeholder="Ex: 999999999")
        with c2:
            n_obs = st.text_input("Observações", value="ESTOQUE ")
            
        submitted = st.form_submit_button("💾 Salvar Novo Chip", type="primary", use_container_width=True)
        if submitted:
            n_ddd_clean = "".join(filter(str.isdigit, n_ddd))
            n_num_clean = "".join(filter(str.isdigit, n_num))
            
            if n_ddd_clean and n_num_clean:
                if len(n_num_clean) == 9 and len(n_ddd_clean) == 2:
                    numero_formatado = f"({n_ddd_clean}) {n_num_clean[:5]}-{n_num_clean[5:]}"
                elif len(n_num_clean) == 8 and len(n_ddd_clean) == 2:
                    numero_formatado = f"({n_ddd_clean}) {n_num_clean[:4]}-{n_num_clean[4:]}"
                else:
                    numero_formatado = f"({n_ddd_clean}) {n_num_clean}"
                    
                data_cadastro = datetime.now().strftime("%d/%m/%Y")
                status_sync, erro_sync = add_chip((
                    "", n_obs, "", "", "", 
                    "", numero_formatado, "", "", "", data_cadastro, "", "", "ATIVO"
                ))
                st.success(f"Chip {numero_formatado} cadastrado em Estoque com sucesso!")
                if not status_sync and erro_sync:
                    st.warning(f"Salvo no banco, mas erro ao sync com Excel: {erro_sync}")
                st.rerun()
            else:
                st.error("Por favor, preencha o DDD e o Número.")



with tab_inativar:
    st.subheader("Inativar Chips em Lote", divider="blue")
    pesquisa_inativar = st.text_input("🔍 Pesquisar por Nome ou Número (Inativar)", placeholder="Ex: João, 41999999999", key="pesq_inat")
    
    df_view_inat = search_chips_dataframe(df_chips.copy(), pesquisa_inativar)
    df_display_inat = prepare_display_dataframe(df_view_inat)
    
    ordem = ['NUMERO', 'NOME', 'FUNÇÃO', 'EMPRESA', 'DEPARTAMENTO/REGIONAL', 'OBSERVAÇÃO', 'VERIFICADO?', 'DT ENTREGA', 'DT DEVOLUCAO', 'STATUS']
    df_display_inat = df_display_inat[ordem]
    df_display_inat.insert(0, "Selecionar", False)
    
    edited_df_inat = st.data_editor(
        df_display_inat,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Selecionar": st.column_config.CheckboxColumn("Inativar?", default=False)
        },
        disabled=df_display_inat.columns.drop("Selecionar"),
        key="tabela_inativar"
    )
    
    selected_inat = edited_df_inat[edited_df_inat["Selecionar"] == True]
    if not selected_inat.empty:
        st.warning(f"Você selecionou {len(selected_inat)} chip(s) para inativar.")
        if st.button("❌ Confirmar Inativação", type="primary"):
            conn = get_connection()
            c = conn.cursor()
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for _, row in selected_inat.iterrows():
                num_selecionado = row['NUMERO']
                chip_original = df_chips[df_chips['numero_corporativo'] == num_selecionado].iloc[0]
                chip_id = int(chip_original['id'])
                
                c.execute("UPDATE chips SET status_chip = 'INATIVO' WHERE id = ?", (chip_id,))
                usuario = st.session_state.get('username', 'Sistema')
                c.execute('''
                    INSERT INTO historico (chip_id, numero_corporativo, acao, antigo_nome, novo_nome, data_acao, detalhes, usuario, regional, funcao, ramal, empresa)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (chip_id, num_selecionado, 'INATIVAÇÃO', chip_original['nome'], chip_original['nome'], data_atual, 'Chip inativado em lote pelo painel.', usuario, chip_original.get('regional', ''), chip_original.get('funcao', ''), chip_original.get('ramal', ''), chip_original.get('coligada', '')))
                
            conn.commit()
            conn.close()
            
            status_sync, erro_sync = sync_to_excel()
            if not status_sync and erro_sync:
                st.warning(f"Salvo no banco, mas erro ao sync com Excel: {erro_sync}")
            else:
                st.success("Chips inativados com sucesso!")
            
            if "tabela_inativar" in st.session_state:
                del st.session_state["tabela_inativar"]
            st.rerun()

with tab_historico:
    st.subheader("Log de Histórico e Alterações", divider="blue")
    
    if not df_hist.empty:
        st.dataframe(
            df_hist.drop(columns=['id', 'chip_id']),
            use_container_width=True,
            hide_index=True,
            column_config={
                "data_acao": st.column_config.DatetimeColumn("Data da Ação", format="DD/MM/YYYY HH:mm:ss"),
                "numero_corporativo": st.column_config.TextColumn("Número"),
                "acao": st.column_config.TextColumn("Ação"),
                "antigo_nome": st.column_config.TextColumn("Nome Anterior"),
                "novo_nome": st.column_config.TextColumn("Novo Nome"),
                "detalhes": st.column_config.TextColumn("Detalhes"),
                "usuario": st.column_config.TextColumn("Usuário Resp.")
            }
        )
    else:
        st.info("Nenhum registro no histórico até o momento.")
