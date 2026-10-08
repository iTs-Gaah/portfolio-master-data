import streamlit as st
import pandas as pd
import os
from datetime import datetime
import io
import json

# Configuração da página
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_PAI = os.path.dirname(DIRETORIO_ATUAL)
DIRETORIO_BASE = os.path.dirname(DIRETORIO_PAI)

caminho_logo_protheus = os.path.join(DIRETORIO_BASE, "assets", "Protheus Logo.png")
caminho_logo_fluig = os.path.join(DIRETORIO_BASE, "assets", "Fluig Logo.png")
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Caminho da planilha gerada pelo bot
caminho_fixo = "/app/data/Aprovadores.xlsx"

# Inicializa o estado de visão para usar no CSS dinâmico
if "tipo_visao" not in st.session_state:
    st.session_state.tipo_visao = None

# CSS Dinâmico para alterar a cor do botão selecionado
if st.session_state.tipo_visao == "Protheus":
    cor_primaria = "#0068C9" # Azul Protheus
    cor_hover = "#0052a3"
else:
    cor_primaria = "#FF4B4B" # Vermelho Fluig
    cor_hover = "#FF3333"

st.markdown(f"""
    <style>
    /* ====== AJUSTES GERAIS DE LAYOUT ====== */
    .block-container {{
        padding-top: 2.2rem;
        padding-bottom: 3rem;
    }}
    h1, h2, h3 {{
        letter-spacing: 0.3px;
    }}

    /* ====== BOTÕES ====== */
    .stButton > button {{
        border-radius: 8px;
        font-weight: 600;
        transition: transform 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }}
    button[kind="primary"] {{
        background-color: {cor_primaria} !important;
        border-color: {cor_primaria} !important;
        color: #ffffff !important;
    }}
    button[kind="primary"]:hover {{
        background-color: {cor_hover} !important;
        border-color: {cor_hover} !important;
    }}

    /* ====== CAMPOS DE FILTRO (foco com a cor do sistema) ====== */
    [data-testid="stTextInput"] input:focus {{
        border-color: {cor_primaria} !important;
        box-shadow: 0 0 0 3px {cor_primaria}33 !important;
    }}

    /* ====== CARDS DO EXPLORADOR (ADAPTÁVEL TEMA CLARO/ESCURO) ====== */
    [data-testid="stExpander"] {{
        background-color: var(--secondary-background-color);
        border-radius: 12px;
        border: 1px solid {cor_primaria}26;
        border-left: 5px solid {cor_primaria};
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 12px;
        overflow: hidden;
    }}
    [data-testid="stExpander"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 10px 22px rgba(0, 0, 0, 0.18);
    }}
    [data-testid="stExpander"] summary {{
        padding: 4px 2px;
    }}
    [data-testid="stExpander"] summary p {{
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--text-color);
        letter-spacing: 0.4px;
        transition: color 0.15s ease;
    }}
    [data-testid="stExpander"] summary:hover p {{
        color: {cor_primaria};
    }}

    /* ====== TEXTOS DOS CARDS ====== */
    .card-subtitle {{
        color: var(--text-color);
        opacity: 0.80;
        font-size: 0.95rem;
        margin-bottom: 6px !important;
        line-height: 1.3;
    }}

    /* ====== CAIXAS DE APROVADOR (reutilizadas Protheus/Fluig) ====== */
    .aprovador-box {{
        background-color: {cor_primaria}14;
        border: 1px solid {cor_primaria}40;
        border-radius: 10px;
        padding: 12px 16px;
        width: 270px;
        min-height: 92px;
        display: inline-block;
        vertical-align: top;
        margin: 0 14px 14px 0;
        box-sizing: border-box;
        transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
    }}
    .aprovador-box:hover {{
        transform: translateY(-2px);
        border-color: {cor_primaria};
        box-shadow: 0 6px 14px rgba(0, 0, 0, 0.15);
    }}
    .aprovador-nivel {{
        color: {cor_primaria};
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 5px;
    }}
    .aprovador-nome {{
        color: var(--text-color);
        font-size: 1.05rem;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .aprovador-cargo {{
        color: var(--text-color);
        opacity: 0.75;
        font-size: 0.82rem;
        margin-top: 3px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    </style>
    """, unsafe_allow_html=True)

def gerar_html_card(subtitle_1, subtitle_2, roles, data_str=""):
    """Gera o HTML do card customizado ao invés de usar a tabela nativa do Streamlit."""
    
    lista_html = "".join(roles)
        
    data_html = f"<div style='color: var(--text-color); opacity: 0.85; font-size: 0.85rem; font-weight: 600; text-align: right;'>{data_str}</div>" if data_str else ""
        
    html = f'''<div style="padding-bottom: 15px; margin-top: -5px;">
<div style="display: flex; justify-content: space-between; align-items: flex-start;">
<div>
<p class="card-subtitle">{subtitle_1}</p>
<p class="card-subtitle">{subtitle_2}</p>
</div>
{data_html}
</div>
<div style="margin-top: 20px;">
{lista_html}
</div>
</div>'''
    return html

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
try:
    import ui_utils
    ui_utils.render_standard_panel(
        title="Painel de Aprovadores",
        subtitle="Gestão e Validação de Regras (Protheus & Fluig)",
        icon_name="Aprovadores logo.png"
    )
except ImportError:
    st.title("📋 Painel de Aprovadores")

# Removido o caminho absoluto fixo que substituía o caminho relativo

if os.path.exists(caminho_fixo):
    timestamp = os.path.getmtime(caminho_fixo)
    arquivo_unico = caminho_fixo
else:
    st.sidebar.error("❌ Arquivo não encontrado. Cadê a planilha?")
    arquivo_unico = st.sidebar.file_uploader("Upload da Base Unificada", type=["xlsx"])

@st.cache_data(ttl=14400)
def carregar_dados(arquivo, data_modificacao):
    if arquivo is not None:
        df_regras = pd.read_excel(arquivo, sheet_name='Plan1', dtype=str)
        df_base_cc = pd.read_excel(arquivo, sheet_name='Plan2', dtype=str)
        df_empresas = pd.read_excel(arquivo, sheet_name='Base', dtype=str)
        
        # Detecta e carrega a aba Form com flexibilidade
        try:
            xls = pd.ExcelFile(arquivo)
            
            # Procura exatamente pela aba "Form" (ignora variações de espaço/case)
            sheet_form = None
            for sheet in xls.sheet_names:
                if sheet.strip().upper() == 'FORM':
                    sheet_form = sheet
                    break
            
            # Se não achar exato, procura qualquer aba que contenha "FORM"
            if sheet_form is None:
                for sheet in xls.sheet_names:
                    if 'FORM' in sheet.strip().upper():
                        sheet_form = sheet
                        break
            
            if sheet_form:
                df_form = pd.read_excel(arquivo, sheet_name=sheet_form, dtype=str)
                df_form.columns = df_form.columns.str.strip().str.upper()
                
                # Remove apenas linhas completamente vazias (todos os valores são NaN ou string vazia)
                df_form = df_form.dropna(how='all')
                df_form = df_form[~df_form.astype(str).apply(lambda x: (x.str.strip() == '').all(), axis=1)]
                
                # Remove linhas onde todos os valores são "nan" ou "NAN"
                df_form = df_form[~df_form.astype(str).apply(lambda x: (x.str.strip().str.upper() == 'NAN').all(), axis=1)]
                
                if 'C CUSTO' in df_form.columns:
                    df_form['C CUSTO'] = df_form['C CUSTO'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            else:
                df_form = pd.DataFrame()
        except Exception as e:
            df_form = pd.DataFrame()

            if 'C CUSTO' in df_form.columns:
                    df_form['C CUSTO'] = df_form['C CUSTO'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            else:
                df_form = pd.DataFrame()
        except:
            df_form = pd.DataFrame()

        col_filial = 'Z01_FILIAL' if 'Z01_FILIAL' in df_regras.columns else 'FILIAL'
        col_cc_regras = 'Z01_CC' if 'Z01_CC' in df_regras.columns else 'C CUSTO'
        col_desc_regras = 'Z01_DECCC' if 'Z01_DECCC' in df_regras.columns else 'C CUSTO DESC'
        
        col_cc_mestre = 'CTT_CUSTO' if 'CTT_CUSTO' in df_base_cc.columns else 'Cod_cc'
        col_desc_mestre = 'CTT_DESC01' if 'CTT_DESC01' in df_base_cc.columns else 'Descrição'
        
        col_cod_emp = 'COD FILIAL' if 'COD FILIAL' in df_empresas.columns else 'Cod_gp'
        col_nome_emp = 'DESC' if 'DESC' in df_empresas.columns else 'Descrição'

        df_regras[col_cc_regras] = df_regras[col_cc_regras].astype(str).str.strip()
        df_base_cc[col_cc_mestre] = df_base_cc[col_cc_mestre].astype(str).str.strip()
        df_regras[col_filial] = df_regras[col_filial].astype(str).str.strip()
        df_empresas[col_cod_emp] = df_empresas[col_cod_emp].astype(str).str.strip()
        df_base_cc['FILIAL_FORMAT'] = df_base_cc['CTT_FILIAL'].astype(str).str.strip().str.zfill(2) + "0101"
        
        col_bloq_auditoria = 'CTT_BLOQ' if 'CTT_BLOQ' in df_base_cc.columns else 'CTT_BLOQ'
        df_base_cc[col_bloq_auditoria] = df_base_cc[col_bloq_auditoria].astype(str).str.strip().str.upper()
        
        return df_regras, df_base_cc, df_empresas, df_form, col_filial, col_cc_regras, col_desc_regras, col_cc_mestre, col_desc_mestre, col_cod_emp, col_nome_emp, col_bloq_auditoria
    return None, None, None, None, None, None, None, None, None, None, None, None

df_regras, df_base_cc, df_empresas, df_form, col_filial, col_cc_regras, col_desc_regras, col_cc_mestre, col_desc_mestre, col_cod_emp, col_nome_emp, col_bloq_auditoria = carregar_dados(arquivo_unico, timestamp)

if df_regras is None:
    st.warning("Aguardando o arquivo para carregar os dados...")
    st.stop()

# --- INICIALIZAÇÃO DE SESSION STATE ---
if "filtro_cc" not in st.session_state: st.session_state.filtro_cc = ""
if "filtro_grupo" not in st.session_state: st.session_state.filtro_grupo = ""
if "filtro_aprovador" not in st.session_state: st.session_state.filtro_aprovador = ""
if "filtro_status_cc" not in st.session_state: st.session_state.filtro_status_cc = "Todos"
if "filtro_empresa" not in st.session_state: st.session_state.filtro_empresa = "Todas" 

if "filtro_cc_fluig" not in st.session_state: st.session_state.filtro_cc_fluig = ""
if "filtro_secao_fluig" not in st.session_state: st.session_state.filtro_secao_fluig = ""
if "filtro_aprovador_fluig" not in st.session_state: st.session_state.filtro_aprovador_fluig = ""
if "filtro_grp_usu_fluig" not in st.session_state: st.session_state.filtro_grp_usu_fluig = ""

if "expandir_todos" not in st.session_state: st.session_state.expandir_todos = False
if "update_key" not in st.session_state: st.session_state.update_key = 0 

def limpar_tudo():
    st.session_state.filtro_base = "Todas"
    st.session_state.filtro_cc = ""
    st.session_state.filtro_grupo = ""
    st.session_state.filtro_aprovador = ""
    st.session_state.filtro_status_cc = "Todos"
    st.session_state.filtro_empresa = "Todas" 
    st.session_state.filtro_cc_fluig = ""
    st.session_state.filtro_secao_fluig = ""
    st.session_state.filtro_aprovador_fluig = ""
    st.session_state.filtro_grp_usu_fluig = ""
    st.session_state.filtro_sem_secao = False
    st.session_state.update_key = int(st.session_state.update_key or 0) + 1

def set_expandir(valor):
    st.session_state.expandir_todos = valor
    st.session_state.update_key = int(st.session_state.update_key or 0) + 1



# ==============================================================================
# --- SELEÇÃO DE SISTEMA CENTRALIZADA COM LOGOS E BOTÕES DINÂMICOS ---
# ==============================================================================


st.markdown("<h3 style='text-align: center;'>🖥️ Qual sistema você quer acessar?</h3>", unsafe_allow_html=True)
st.write("") 

col_esq1, col_img_p, col_meio1, col_img_f, col_dir1 = st.columns([3, 1.5, 1, 1.5, 3])

with col_img_p:
    st.image(caminho_logo_protheus, use_column_width=True)

with col_img_f:
    st.image(caminho_logo_fluig, use_column_width=True)

col_esq2, col_btn_p, col_meio2, col_btn_f, col_dir2 = st.columns([3, 1.5, 1, 1.5, 3])

with col_btn_p:
    cor_btn_p = "primary" if st.session_state.tipo_visao == "Protheus" else "secondary"
    if st.button("Grupo de Aprovadores", use_container_width=True, type=cor_btn_p):
        st.session_state.tipo_visao = "Protheus"
        st.rerun()

with col_btn_f:
    cor_btn_f = "primary" if st.session_state.tipo_visao == "Fluig" else "secondary"
    if st.button("Formulário de Aprovadores", use_container_width=True, type=cor_btn_f):
        st.session_state.tipo_visao = "Fluig"
        st.rerun()
        
if st.session_state.tipo_visao is None:
    st.markdown("""
        <div style='text-align: center; margin-top: 30px;'>
            👆 <i>Clique no botão abaixo da logo correspondente para carregar o painel.</i>
        </div>
    """, unsafe_allow_html=True)
    st.stop() 

tipo_visao = st.session_state.tipo_visao
st.write("---")
espaco_hack = " " * (int(st.session_state.update_key or 0) % 2)
# ==============================================================================
# --- LÓGICA PROTHEUS COMPLETA ---
# ==============================================================================
if tipo_visao == "Protheus":
    
    # Limpa os espaços fantasmas dos cabeçalhos pra você não encher o saco com erro oculto
    df_regras.columns = df_regras.columns.str.strip()
    df_base_cc.columns = df_base_cc.columns.str.strip()
    df_empresas.columns = df_empresas.columns.str.strip()

    # Caça a porra da coluna de Empresa independente da frescura de nome que você colocou
    col_emp_regras = next((c for c in df_regras.columns if 'EMPRE' in c.upper()), None)
    col_emp_mestre = next((c for c in df_base_cc.columns if 'EMPRE' in c.upper()), None)

    if not col_emp_regras or not col_emp_mestre:
        st.error(f"🚨 ERRO: Sua planilha tá uma merda. Não achei a coluna com a palavra EMPRESA na Plan1 ou Plan2.")
        st.write("Colunas Plan1:", df_regras.columns.tolist())
        st.write("Colunas Plan2:", df_base_cc.columns.tolist())
        st.stop()

    # Chave de validação blindada: EMPRESA + FILIAL + CC
    col_filial_mestre = 'CTT_FILIAL' if 'CTT_FILIAL' in df_base_cc.columns else df_base_cc.columns[1]

    emp_mestre_limpo = df_base_cc[col_emp_mestre].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(2)
    fil_mestre_limpo = df_base_cc[col_filial_mestre].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(6)
    cc_mestre_limpo = df_base_cc[col_cc_mestre].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_base_cc['CHAVE_VALIDACAO'] = emp_mestre_limpo + "_" + fil_mestre_limpo + "_" + cc_mestre_limpo

    emp_regras_limpo = df_regras[col_emp_regras].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(2)
    fil_regras_limpo = df_regras[col_filial].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(6)
    cc_regras_limpo = df_regras[col_cc_regras].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_regras['CHAVE_VALIDACAO'] = emp_regras_limpo + "_" + fil_regras_limpo + "_" + cc_regras_limpo
    
    cc_ativos_plan2 = df_base_cc[df_base_cc[col_bloq_auditoria].isin(['2', 'ATIVO'])].copy()
    cc_sem_aprovador = cc_ativos_plan2[~cc_ativos_plan2['CHAVE_VALIDACAO'].isin(df_regras['CHAVE_VALIDACAO'])]

    if not cc_sem_aprovador.empty:
        st.error("🚨 **Atenção: Existem Centros de Custo ativos sem grupo de aprovação cadastrado no Protheus!**")
        with st.expander(f"Ver lista de pendências ({len(cc_sem_aprovador)} encontradas):"):
            for index, row in cc_sem_aprovador.iterrows():
                emp_erro = str(row[col_emp_mestre]).replace('.0', '').zfill(2)
                fil_erro = str(row[col_filial_mestre]).replace('.0', '').zfill(6)
                cc_erro = str(row[col_cc_mestre]).strip()
                desc_erro = str(row[col_desc_mestre]).strip() if pd.notna(row.get(col_desc_mestre)) else 'Sem descrição'
                status_erro = str(row[col_bloq_auditoria]).strip()
                
                st.write(f"❌ {emp_erro} - {fil_erro} - {cc_erro} - {desc_erro} - {status_erro}")
    else:
        st.success("✅ Tudo certo! Todos os Centros de Custo ativos tem Grupo de Aprovadores.")
    
    st.write("---")

    st.write("### 🔍 Filtros de Pesquisa")
    col_topo0, col_topo1, col_topo2 = st.columns(3)
    
    # Pegando as colunas pela posição pra ignorar a cagada de nomes duplicados que você fez no Excel
    col_cod_emp_a = df_empresas.columns[0]  
    col_cod_filial_b = df_empresas.columns[1] 
    col_desc_filial_c = df_empresas.columns[2] 
    
    with col_topo0:
        if df_empresas is not None and not df_empresas.empty:
            # Puxa a maldita coluna nova que você criou
            if 'COD EMPRESA Z01' in df_empresas.columns:
                col_cod_base = 'COD EMPRESA Z01'
            elif 'COD EMPRESA.1' in df_empresas.columns:
                col_cod_base = 'COD EMPRESA.1'
            else:
                col_cod_base = col_cod_emp_a
                
            col_desc_base = 'DESC EMPRESA' if 'DESC EMPRESA' in df_empresas.columns else df_empresas.columns[-1]

            # Filtra só quem tem nome válido e arranca os NaN
            df_bases = df_empresas[df_empresas[col_desc_base].notna() & (df_empresas[col_desc_base].astype(str).str.lower() != 'nan')].copy()
            
            if not df_bases.empty:
                # Converte o código pra número inteiro na força bruta pra matar qualquer sujeira do Excel
                df_bases['COD_BASE_NUM'] = pd.to_numeric(df_bases[col_cod_base], errors='coerce').fillna(-999).astype(int)
                df_bases = df_bases[df_bases['COD_BASE_NUM'] != -999]
                
                # Bota o zero à esquerda e monta a string (ex: "01 - GRUPO EMPRESA_01")
                df_bases['BASE_NOME'] = df_bases['COD_BASE_NUM'].astype(str).str.zfill(2) + " - " + df_bases[col_desc_base].astype(str).str.strip()
                
                # Tira as duplicatas e ordena
                df_bases = df_bases.drop_duplicates(subset=['BASE_NOME']).sort_values(by='COD_BASE_NUM')
                lista_bases = ["Todas"] + df_bases['BASE_NOME'].tolist()
            else:
                lista_bases = ["Todas"]
                
            base_focada = st.selectbox("🏢 Selecione a Base:", options=lista_bases, key="filtro_base")
        else:
            base_focada = "Todas"

    with col_topo1:
        if df_empresas is not None and not df_empresas.empty:
            df_filiais = df_empresas.copy()
            
            # Filtro em cascata da Base para a Filial
            if base_focada != "Todas":
                # Pega o "01" da tela e transforma em "1" limpo pra bater com a primeira coluna do Excel
                cod_base_selecionada = str(int(base_focada.split("-")[0].strip()))
                
                # Força a coluna da esquerda da base a virar número inteiro antes de bater a informação
                df_filiais['COD_EMP_LIMPO'] = pd.to_numeric(df_filiais[col_cod_emp_a], errors='coerce').fillna(-999).astype(int).astype(str)
                df_filiais = df_filiais[df_filiais['COD_EMP_LIMPO'] == cod_base_selecionada]

            # Tira os nan da lista de filiais
            df_filiais = df_filiais[df_filiais[col_cod_filial_b].notna() & (df_filiais[col_cod_filial_b].astype(str).str.lower() != 'nan')]
            
            if not df_filiais.empty:
                df_filiais[col_cod_filial_b] = df_filiais[col_cod_filial_b].astype(str).str.strip().str.zfill(6)
                
                # Puxa o código e soca o zero à esquerda
                cod_base_formatado = pd.to_numeric(df_filiais[col_cod_emp_a], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(2)
                df_filiais['NOME_LISTA'] = cod_base_formatado + " - " + df_filiais[col_cod_filial_b] + " - " + df_filiais[col_desc_filial_c].astype(str).str.strip()
                
                df_filiais = df_filiais.sort_values(by='NOME_LISTA')
                lista_selecao = ["Todas"] + df_filiais['NOME_LISTA'].unique().tolist()
            else:
                lista_selecao = ["Todas"]
                
            # O selectbox volta pro lugar certo aqui
            empresa_focada = st.selectbox("🏭 Selecione a Filial:", options=lista_selecao, key="filtro_empresa")
        else:           
            empresa_focada = "Todas"

    with col_topo2:
        busca_status_cc = st.selectbox("🚩 Status do Centro de Custo", ["Todos", "Ativo", "Bloqueado"], key="filtro_status_cc")

    col1, col2, col3 = st.columns(3)
    with col1: busca_cc = st.text_input("Centro de Custo/Descrição:", key="filtro_cc")
    with col2: busca_grupo = st.text_input("Grupo de Aprovação:", key="filtro_grupo")
    with col3: busca_aprovador = st.text_input("Aprovador:", key="filtro_aprovador")

    # Botões alinhados na esquerda com espaço vazio jogado pra direita
    btn_col1, btn_col2, btn_col3, _ = st.columns([1, 1, 1, 3])
    
    with btn_col1: st.button("🧹 Limpar Filtros", on_click=limpar_tudo, use_container_width=True, key="btn_limpa_protheus")
    with btn_col2: st.button("➕ Expandir Todos", on_click=set_expandir, args=(True,), use_container_width=True, key="btn_exp_protheus")
    with btn_col3: st.button("➖ Recolher Todos", on_click=set_expandir, args=(False,), use_container_width=True, key="btn_rec_protheus")
    st.write("---")
    # AQUI VOCÊ CRIA A VARIÁVEL. DEPOIS DISSO É QUE VEM O FILTRO, CARALHO.
    df_filtrado = df_regras.copy()
    
    #FILTRO BASE
    if base_focada != "Todas":
        # Pega a primeira parte antes do traço (Ex: de "03 - CONSORCIOS" vira "03")
        numero_base = base_focada.split("-")[0].strip()
        
        # Força o que veio da tela a virar um número inteiro limpo em texto (arranca os zeros à esquerda, "03" -> "3")
        try:
            cod_base_limpo = str(int(float(numero_base)))
        except:
            cod_base_limpo = numero_base # Fallback caso venha alguma sujeira
            
        # Converte a coluna EMPRESA da Plan1 inteira pra número inteiro na marra, matando os ".0" (Ex: "3.0" -> "3")
        df_filtrado['EMP_FILTRO_LIMPO'] = pd.to_numeric(df_filtrado[col_emp_regras], errors='coerce').fillna(-999).astype(int).astype(str)
        
        # Filtra cruzando as duas strings numéricas blindadas
        df_filtrado = df_filtrado[df_filtrado['EMP_FILTRO_LIMPO'] == cod_base_limpo]

    # Filtro de Filial
    if empresa_focada != "Todas":
        # Como o texto agora é "BASE - FILIAL - DESC", a filial tá na posição [1] do split
        cod_filial_selecionada = empresa_focada.split(" - ")[1].strip()
        df_filtrado = df_filtrado[
            (df_filtrado[col_filial].astype(str).str.strip() == cod_filial_selecionada.lstrip('0')) |
            (df_filtrado[col_filial].astype(str).str.strip() == cod_filial_selecionada)
        ]
    df_filtrado['CHAVE_UNICA'] = df_filtrado[col_emp_regras].astype(str).str.strip() + " | " + df_filtrado[col_filial].astype(str).str.strip() + " | " + df_filtrado[col_cc_regras].astype(str).str.strip()

    # --- O PULO DO GATO ---
    # Como a Plan1 tem descrições zoadas nas outras filiais, puxamos a descrição Mestre da Plan2 antes de filtrar
    col_fil_plan2 = 'CTT_FILIAL' if 'CTT_FILIAL' in df_base_cc.columns else df_base_cc.columns[1]
    
    # Prepara as chaves pra bater as duas planilhas
    df_filtrado['_EMP_MATCH'] = pd.to_numeric(df_filtrado[col_emp_regras], errors='coerce').fillna(-999).astype(int).astype(str).str.zfill(2)
    df_filtrado['_FIL_MATCH'] = pd.to_numeric(df_filtrado[col_filial], errors='coerce').fillna(-999).astype(int).astype(str).str.zfill(6)
    df_filtrado['_CC_MATCH'] = df_filtrado[col_cc_regras].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

    df_base_cc['_EMP_MATCH'] = pd.to_numeric(df_base_cc[col_emp_mestre], errors='coerce').fillna(-999).astype(int).astype(str).str.zfill(2)
    df_base_cc['_FIL_MATCH'] = pd.to_numeric(df_base_cc[col_fil_plan2], errors='coerce').fillna(-999).astype(int).astype(str).str.zfill(6)
    df_base_cc['_CC_MATCH'] = df_base_cc[col_cc_mestre].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

    # Traz a descrição certa e o status da Plan2 pro df_filtrado
    df_base_cc_to_merge = df_base_cc[['_EMP_MATCH', '_FIL_MATCH', '_CC_MATCH', col_desc_mestre, col_bloq_auditoria]].drop_duplicates()
    df_base_cc_to_merge = df_base_cc_to_merge.rename(columns={col_bloq_auditoria: '_STATUS_PLAN2'})
    df_filtrado = df_filtrado.merge(
        df_base_cc_to_merge,
        on=['_EMP_MATCH', '_FIL_MATCH', '_CC_MATCH'],
        how='left'
    )

    # Agora o text_input bate no código OU na descrição MESTRE validada
    import re
    if busca_cc:
        termo_limpo = re.sub(r'[\s\-_]+', ' ', busca_cc.strip())
        termo_regex = re.escape(termo_limpo).replace(r'\ ', r'[\s\-_]+')
        # Usa (?:^|[^a-zA-Z0-9]) para garantir que encontre a palavra isolada, no início ou após caracteres especiais (ex: "TI" não traz "LOGISTICA", mas "SEARA" traz "-SEARA-")
        pattern_desc = rf'(?:^|[^a-zA-Z0-9]){termo_regex}'
        df_filtrado = df_filtrado[
            df_filtrado[col_cc_regras].astype(str).str.contains(termo_regex, case=False, na=False, regex=True) |
            df_filtrado[col_desc_mestre].astype(str).str.contains(pattern_desc, case=False, na=False, regex=True)
        ]
    if busca_grupo:
        col_grupo_busca = 'AL_DESC' if 'AL_DESC' in df_filtrado.columns else 'NOME GRUPO'
        df_filtrado = df_filtrado[df_filtrado[col_grupo_busca].str.contains(busca_grupo, case=False, na=False)]
    if busca_aprovador:
        col_aprov_busca = 'AK_NOME' if 'AK_NOME' in df_filtrado.columns else 'NOME APROVADOR'
        df_filtrado = df_filtrado[df_filtrado[col_aprov_busca].str.contains(busca_aprovador, case=False, na=False)]
    if busca_status_cc != "Todos":
        # Filtra pelo status que veio da Plan2
        if busca_status_cc.upper() == "ATIVO":
            df_filtrado = df_filtrado[df_filtrado['_STATUS_PLAN2'].astype(str).str.strip().str.upper().isin(['2', 'ATIVO'])]
        elif busca_status_cc.upper() == "BLOQUEADO":
            df_filtrado = df_filtrado[df_filtrado['_STATUS_PLAN2'].astype(str).str.strip().str.upper().isin(['1', 'BLOQUEADO', 'INATIVO'])]

    # --- ORDENAÇÃO BRUTA PARA NÃO FICAR UMA ZONA ---
    # Cria colunas temporárias com os zeros à esquerda só pra forçar a ordem certa
    df_filtrado['_ORDEM_EMP'] = pd.to_numeric(df_filtrado[col_emp_regras], errors='coerce').fillna(999).astype(int).astype(str).str.zfill(2)
    df_filtrado['_ORDEM_FIL'] = pd.to_numeric(df_filtrado[col_filial], errors='coerce').fillna(FILIAL_25).astype(int).astype(str).str.zfill(6)
    df_filtrado['_ORDEM_CC'] = df_filtrado[col_cc_regras].astype(str).str.strip()
    
    # Ordena a porra toda por Empresa > Filial > Centro de Custo
    df_filtrado = df_filtrado.sort_values(by=['_ORDEM_EMP', '_ORDEM_FIL', '_ORDEM_CC'])

    chaves_filtradas = df_filtrado['CHAVE_UNICA'].unique()

   # Dividi em colunas pra o botão ficar alinhado com o título, senão fica uma zona
    col_tit, col_btn = st.columns([3, 1])
    with col_tit:
        try:
            total_b = len(df_regras['CHAVE_UNICA'].unique())
        except:
            total_b = len(df_regras)
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 5px; margin-top:20px;">
            <h3 style="margin:0; padding:0; color:var(--text-color); font-weight: bold; border-left: 4px solid #0068C9; padding-left: 10px;">🏢 Explorador Protheus</h3>
            <div style="display: flex; gap: 24px; text-align: center; font-size: 0.8rem; font-weight: 800; color: var(--text-color); opacity: 0.7;">
                <div>TOTAL<br><span style="color:var(--text-color); font-size:1.1rem; opacity: 1;">{total_b}</span></div>
                <div>VISÍVEIS<br><span style="color:var(--text-color); font-size:1.1rem; opacity: 1;">{len(chaves_filtradas)}</span></div>
                <div>STATUS<br><span style="color:#2ecc71; font-size:1.1rem; opacity: 1;">Ativo</span></div>
            </div>
        </div>
        <hr style="margin-top: 5px; border-color: var(--secondary-background-color); border-width: 1px;">
        """, unsafe_allow_html=True)

    if len(chaves_filtradas) == 0:
        st.warning("Nenhum resultado encontrado com esses filtros.")
    else:
        # Gera o botão de download na memória
        with col_btn:
            buffer = io.BytesIO()
            # Removendo aquelas colunas de lixo temporárias que criamos só pro código funcionar
            colunas_lixo = ['CHAVE_UNICA', 'CHAVE_VALIDACAO', '_ORDEM_EMP', '_ORDEM_FIL', '_ORDEM_CC', 'EMP_FILTRO_LIMPO', '_EMP_MATCH', '_FIL_MATCH', '_CC_MATCH']
            df_limpo_pra_baixar = df_filtrado.drop(columns=colunas_lixo, errors='ignore')
            
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_limpo_pra_baixar.to_excel(writer, index=False, sheet_name='Filtrado')
            
            st.download_button(
                label="📥 Baixar Excel",
                data=buffer.getvalue(),
                file_name="Aprovadores_Filtrados_Protheus.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        df_regras['CHAVE_UNICA'] = df_regras[col_emp_regras].astype(str).str.strip() + " | " + df_regras[col_filial].astype(str).str.strip() + " | " + df_regras[col_cc_regras].astype(str).str.strip()
        
        # Cria colunas limpas na Base Mestre (Plan2) UMA ÚNICA VEZ antes do loop para não engasgar o servidor
        col_fil_plan2 = 'CTT_FILIAL' if 'CTT_FILIAL' in df_base_cc.columns else df_base_cc.columns[1]
        df_base_cc['_EMP_MATCH'] = pd.to_numeric(df_base_cc[col_emp_mestre], errors='coerce').fillna(-999).astype(int).astype(str).str.zfill(2)
        df_base_cc['_FIL_MATCH'] = pd.to_numeric(df_base_cc[col_fil_plan2], errors='coerce').fillna(-999).astype(int).astype(str).str.zfill(6)
        df_base_cc['_CC_MATCH'] = df_base_cc[col_cc_mestre].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

        for chave in chaves_filtradas:
            dados_cc = df_regras[df_regras['CHAVE_UNICA'] == chave]
            if dados_cc.empty: continue
            
            # 1. Traz a Empresa, Filial e CC puramente da Plan1
            emp_plan1 = str(dados_cc[col_emp_regras].iloc[0]).strip()
            fil_plan1 = str(dados_cc[col_filial].iloc[0]).strip()
            cc_plan1 = str(dados_cc[col_cc_regras].iloc[0]).strip()
            
            # Formata matando os ".0" escrotos que o Pandas inventa
            try: emp_fmt = str(int(float(emp_plan1))).zfill(2)
            except: emp_fmt = emp_plan1.zfill(2)
                
            try: fil_fmt = str(int(float(fil_plan1))).zfill(6)
            except: fil_fmt = fil_plan1.zfill(6)

            cc_fmt = cc_plan1[:-2] if cc_plan1.endswith(".0") else cc_plan1
            
            # 2. Cruza a Plan1 formatada com as colunas limpas da Plan2
            info_base = df_base_cc[
                (df_base_cc['_EMP_MATCH'] == emp_fmt) & 
                (df_base_cc['_FIL_MATCH'] == fil_fmt) & 
                (df_base_cc['_CC_MATCH'] == cc_fmt)
            ]
            
            # 3. Puxa a descrição e o status da Plan2
            if not info_base.empty:
                desc_final = str(info_base[col_desc_mestre].iloc[0]).strip()
                status_cc = str(info_base[col_bloq_auditoria].iloc[0]).strip().upper()
            else:
                desc_final = "[CC NÃO ENCONTRADO NA PLAN2]"
                col_status_cc = 'CTT_BLOQ' if 'CTT_BLOQ' in dados_cc.columns else 'Status do CC'
                status_cc = str(dados_cc[col_status_cc].iloc[0]).strip().upper() if col_status_cc in dados_cc.columns else ""
            
            icone_grupo = "🟢" if status_cc in ["2", "ATIVO"] else "🔴"
            alerta_cc = " ⚠️ [CC BLOQUEADO]" if status_cc in ["1", "BLOQUEADO", "INATIVO"] else ""
        
            # Monta o título e os subtitulos para o HTML
            titulo_card = f"{cc_fmt} - {desc_final.upper()}"
            sub_1 = f"Centro de Custo: {emp_fmt} | {fil_fmt} | {cc_fmt}"
            
            # Buscar sub_2 que é o "Grupo Resp"
            col_grupo = 'AL_DESC' if 'AL_DESC' in dados_cc.columns else 'NOME GRUPO'
            nome_grupo = str(dados_cc[col_grupo].iloc[0]).strip() if col_grupo in dados_cc.columns else "N/A"
            sub_2 = f"Grupo de Usuários: {nome_grupo}"
            
            # Formata a data de atualização
            data_str = "ATUALIZADO: " + (data_formatada.split(' ')[0] if 'data_formatada' in globals() else "AGORA")
            
            # Extrair os aprovadores do loop de linhas agrupando nas badges
            roles = []
            col_nome_aprovador = 'AK_NOME' if 'AK_NOME' in dados_cc.columns else 'NOME APROVADOR'
            col_perfil = 'DHL_DESCRI' if 'DHL_DESCRI' in dados_cc.columns else 'Perfil'
            
            dados_cc_sorted = dados_cc.copy()
            col_nivel = 'AL_NIVEL' if 'AL_NIVEL' in dados_cc_sorted.columns else 'NIVEL APROV'
            if col_nivel in dados_cc_sorted.columns:
                dados_cc_sorted = dados_cc_sorted.sort_values(by=col_nivel, ascending=True)

            for i, (_, row_usr) in enumerate(dados_cc_sorted.iterrows(), 1):
                cargo = str(row_usr.get(col_perfil, 'Aprovador')).strip()
                nome = str(row_usr.get(col_nome_aprovador, '')).strip()
                nivel = str(row_usr.get(col_nivel, '')).strip()
                
                # Puxa o AL_TPLIBER se existir
                col_tpliber = 'AL_TPLIBER' if 'AL_TPLIBER' in dados_cc_sorted.columns else None
                tpliber = str(row_usr.get(col_tpliber, '')).strip() if col_tpliber else ""
                
                # Tenta puxar o AL_NIVEL/NIVEL APROV, senão usa a ordem do próprio laço
                try: 
                    nivel_num = int(float(nivel))
                    nivel_prefixo = f"{nivel_num}º Aprovador"
                except:
                    nivel_prefixo = f"{i}º Aprovador"
                    
                if tpliber and tpliber.lower() != 'nan':
                    nivel_prefixo = f"{nivel_prefixo} - {tpliber.title()}"
                    
                nome_formatado = nome.title() if nome and nome.lower() != 'nan' else "Não Definido"
                
                # Exibe o limite de aprovação no lugar do cargo
                lim_min = str(row_usr.get('DHL_LIMMIN', '')).strip()
                if lim_min and lim_min.lower() != 'nan':
                    try:
                        # Tenta formatar caso o Excel mande como float (ex: 1500.5 -> 1.500,50)
                        valor_float = float(lim_min)
                        lim_min_formatado = f"{valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    except ValueError:
                        # Se já vier formatado (ex: "0,01"), mantém como está
                        lim_min_formatado = lim_min
                    cargo_formatado = f"Aprovação Acima De R$ {lim_min_formatado}"
                else:
                    # Cargo formatado vazio se não tiver valor
                    cargo_formatado = ""
                
                # Monta a caixa (Nível, Nome, Perfil) usando as classes CSS reutilizáveis
                texto_item = f"<div class='aprovador-box'><div class='aprovador-nivel'>{nivel_prefixo}</div><div class='aprovador-nome'>{nome_formatado}</div>"
                if cargo_formatado:
                    texto_item += f"<div class='aprovador-cargo'>{cargo_formatado}</div>"
                texto_item += "</div>"
                
                if cargo.lower() != 'nan':
                    roles.append(texto_item)
            
            # Checagem de status
            card_ativo = True if status_cc in ["2", "ATIVO"] else False

            # GERA O COMPONENTE HTML CUSTOMIZADO DE VEZ!
            titulo_expander = f"{icone_grupo} {titulo_card} {alerta_cc}".strip()
            
            with st.expander(titulo_expander, expanded=(str(st.session_state.expandir_todos).lower() == 'true')):
                html_final = gerar_html_card(sub_1, sub_2, roles, data_str)
                st.markdown(html_final, unsafe_allow_html=True)
# ==============================================================================
# --- LÓGICA FLUIG CORRIGIDA
# ==============================================================================
elif tipo_visao == "Fluig":
    
    if df_form is None or df_form.empty:
        st.warning("A aba 'Form' não foi encontrada ou está vazia na planilha.")
        try:
            xls_debug = pd.ExcelFile(arquivo_unico)
            abas_disponiveis = xls_debug.sheet_names
            st.info(f"**Abas disponíveis no arquivo:** {', '.join(abas_disponiveis)}")
        except:
            pass
    else:
        # --- BLINDAGEM CONTRA KEYERROR ---
        # Procura a coluna de custo mesmo que o nome esteja sutilmente diferente (espaço vs underline)
        if 'C CUSTO' not in df_form.columns:
            col_cc_detectada = next((c for c in df_form.columns if 'CUSTO' in c.upper() or 'CC' in c.upper()), None)
            if col_cc_detectada:
                df_form = df_form.rename(columns={col_cc_detectada: 'C CUSTO'})
            else:
                st.error("🚨 Não achei nenhuma coluna de Centro de Custo no Form. Ajusta essa query ou o Excel!")
                st.stop()

        # Agora cria as colunas de limpeza sem medo de KeyError
        df_base_cc['CC_CLEAN'] = df_base_cc[col_cc_mestre].astype(str).str.strip().str.upper().str.replace(r'\.0$', '', regex=True)
        df_form['CC_CLEAN'] = df_form['C CUSTO'].astype(str).str.strip().str.upper().str.replace(r'\.0$', '', regex=True)

        # Filtra e remove as duplicatas com base nessa nova coluna limpa
        df_base_cc_unicos = df_base_cc.drop_duplicates(subset=['CC_CLEAN']).copy()
        ccs_no_fluig_unicos = df_form['CC_CLEAN'].unique()

        # O mesmo código de CC pode existir em mais de uma empresa/filial e estar
        # ATIVO numa e BLOQUEADO noutra. Como o Form não traz empresa/filial, guardamos
        # aqui (a partir da Plan2 COMPLETA, sem dedup) todo CC que está ativo em pelo
        # menos uma empresa/filial, pra não mandar excluir formulário de CC que ainda vive.
        ccs_ativos_qualquer_filial = set(
            df_base_cc[df_base_cc[col_bloq_auditoria].isin(['2', 'ATIVO'])]['CC_CLEAN']
        )

        # Ativos da Plan2 que NÃO estão no Form
        cc_ativos_plan2 = df_base_cc_unicos[df_base_cc_unicos[col_bloq_auditoria].isin(['2', 'ATIVO'])]
        cc_sem_form = cc_ativos_plan2[~cc_ativos_plan2['CC_CLEAN'].isin(ccs_no_fluig_unicos)]

        if 'CTT_XFINAN' in cc_sem_form.columns:
            cc_sem_form = cc_sem_form[cc_sem_form['CTT_XFINAN'].astype(str).str.strip().str.upper() != 'S']

        # Inativos da Plan2 que ESTÃO no Form.
        # Só vira pendência de exclusão se o CC estiver bloqueado em TODAS as empresas/filiais
        # (ou seja, não aparece como ativo em nenhuma). Assim o mesmo código bloqueado só
        # numa empresa/filial, mas ativo em outra, deixa de gerar falso alerta de exclusão.
        cc_inativos_plan2 = df_base_cc_unicos[df_base_cc_unicos[col_bloq_auditoria].isin(['1', 'BLOQUEADO', 'INATIVO'])]
        cc_inativo_com_form = cc_inativos_plan2[
            cc_inativos_plan2['CC_CLEAN'].isin(ccs_no_fluig_unicos) &
            ~cc_inativos_plan2['CC_CLEAN'].isin(ccs_ativos_qualquer_filial)
        ]

        if not cc_sem_form.empty:
            cc_sem_form_unico = cc_sem_form.drop_duplicates(subset=[col_cc_mestre])
            st.error(f"🚨 **Atenção: Existem {len(cc_sem_form_unico)} CCs ativos sem Formulário cadastrado!**")
            with st.expander("Ver lista para cadastrar formulário:"):
                for index, row in cc_sem_form_unico.iterrows():
                    cc_erro = str(row[col_cc_mestre]).strip()
                    desc_erro = str(row[col_desc_mestre]).strip() if pd.notna(row.get(col_desc_mestre)) else 'Sem descrição'
                    st.write(f"❌ {cc_erro} - {desc_erro}")
                    
        if not cc_inativo_com_form.empty:
            st.warning(f"⚠️ **Atenção: Existem {len(cc_inativo_com_form)} CCs inativos com Formulário cadastrado!**")
            with st.expander("Ver lista para excluir formulário:"):
                for index, row in cc_inativo_com_form.iterrows():
                    cc_erro = str(row[col_cc_mestre]).strip()
                    desc_erro = str(row[col_desc_mestre]).strip() if pd.notna(row.get(col_desc_mestre)) else 'Sem descrição'
                    st.write(f"🗑️ {cc_erro} - {desc_erro}")

        if cc_sem_form.empty and cc_inativo_com_form.empty:
            st.success("✅ Tudo nos conformes! Zero pendências entre Protheus e Fluig.")
        
        # --- VALIDAÇÃO DE SEÇÃO VAZIA NO FLUIG ---
        if 'SECAO' in df_form.columns:
            form_sem_secao = df_form[df_form['SECAO'].isna() | (df_form['SECAO'].astype(str).str.strip() == '') | (df_form['SECAO'].astype(str).str.upper() == 'NAN')].copy()
            
            if not form_sem_secao.empty:
                form_sem_secao = form_sem_secao.merge(df_base_cc, left_on='CC_CLEAN', right_on='CC_CLEAN', how='left')
                
                if 'CODIGO' in form_sem_secao.columns:
                    form_sem_secao['CODIGO_LIMPO'] = form_sem_secao['CODIGO'].astype(str).str.strip()
                    form_sem_secao = form_sem_secao[form_sem_secao['CODIGO_LIMPO'].str.len() == 15]
                else:
                    form_sem_secao = pd.DataFrame() 

                if not form_sem_secao.empty:
                    form_sem_secao.fillna('N/A', inplace=True)
                    st.warning("⚠️ **Atenção: Tem formulário no Fluig com o campo SEÇÃO em branco!**")
                    with st.expander(f"Ver formulários sem seção ({len(form_sem_secao)} encontrados):"):
                        for index, row in form_sem_secao.iterrows():
                            cc_erro = str(row['C CUSTO']).strip()
                            desc_erro = str(row[col_desc_mestre]).strip() if col_desc_mestre in row else 'N/A'
                            codigo_plan2 = str(row['CODIGO']).strip() if 'CODIGO' in row else 'N/A'
                            desc_secao = str(row['DESCRICAO']).strip() if 'DESCRICAO' in row else 'N/A'
                            status_rm = str(row[col_bloq_auditoria]).strip() if col_bloq_auditoria in row else 'N/A'
                            
                            desc_erro = 'N/A' if desc_erro.lower() == 'nan' else desc_erro
                            codigo_plan2 = 'N/A' if codigo_plan2.lower() == 'nan' else codigo_plan2
                            desc_secao = 'N/A' if desc_secao.lower() == 'nan' else desc_secao
                            status_rm = 'N/A' if status_rm.lower() == 'nan' else status_rm

                            st.write(f"⚠️ CC: {cc_erro} - {desc_erro} - SEÇÃO RM: {codigo_plan2} - {desc_secao} - STATUS RM: {status_rm}")

        st.write("### 🔍 Filtros de Pesquisa (Fluig)")
        
        col1_f, col2_f, col3_f = st.columns(3)
        with col1_f: busca_cc_fluig = st.text_input("Centro de Custo/Descrição:", key="filtro_cc_fluig")
        with col2_f: busca_secao_fluig = st.text_input("Seção RM:", key="filtro_secao_fluig")
        with col3_f: busca_aprovador_fluig = st.text_input("Aprovador:", key="filtro_aprovador_fluig")
        
        col4_f, col5_f = st.columns([1, 2])
        with col4_f: busca_grp_usu_fluig = st.text_input("Grupo de Usuário:", key="filtro_grp_usu_fluig")
        with col5_f: 
            st.write("") # Quebra de linha porca pra empurrar o checkbox pra baixo e alinhar com o texto
            # Arrumei a indentação dessa bosta que tava fora da coluna
            apenas_sem_secao = st.checkbox("Mostrar apenas formulários sem Seção", key="filtro_sem_secao")
        
        btn_col1, btn_col2, btn_col3, _ = st.columns([1, 1, 1, 3])
        # Chaves mantidas pra não bugar
        with btn_col1: st.button("🧹 Limpar Filtros", on_click=limpar_tudo, use_container_width=True, key="btn_limpa_fluig")
        with btn_col2: st.button("➕ Expandir Todos", on_click=set_expandir, args=(True,), use_container_width=True, key="btn_exp_fluig")
        with btn_col3: st.button("➖ Recolher Todos", on_click=set_expandir, args=(False,), use_container_width=True, key="btn_rec_fluig")

        st.write("---")

        df_form_filtrado = df_form.copy()
        
        # Essa é a porra do merge que você deve ter deletado. É ele que traz a descrição.
        if 'CC_CLEAN' in df_form_filtrado.columns and 'CC_CLEAN' in df_base_cc_unicos.columns:
            df_form_filtrado = df_form_filtrado.merge(
                df_base_cc_unicos[['CC_CLEAN', col_desc_mestre]], 
                on='CC_CLEAN', 
                how='left'
            )

        # Regra do seu Checkbox
        if apenas_sem_secao and 'SECAO' in df_form_filtrado.columns:
            df_form_filtrado = df_form_filtrado[
                df_form_filtrado['SECAO'].isna() | 
                (df_form_filtrado['SECAO'].astype(str).str.strip() == '') | 
                (df_form_filtrado['SECAO'].astype(str).str.upper() == 'NAN')
            ]

        # Resto dos filtros
        import re
        if busca_cc_fluig:
            # Usa get() aqui para não quebrar se a coluna de descrição der merda no futuro
            termo_limpo_fluig = re.sub(r'[\s\-_]+', ' ', busca_cc_fluig.strip())
            termo_regex_fluig = re.escape(termo_limpo_fluig).replace(r'\ ', r'[\s\-_]+')
            # Usa (?:^|[^a-zA-Z0-9]) para garantir que a busca na descrição encontre o início de uma palavra ou após caracteres especiais
            pattern_desc_fluig = rf'(?:^|[^a-zA-Z0-9]){termo_regex_fluig}'
            df_form_filtrado = df_form_filtrado[
                df_form_filtrado['C CUSTO'].str.contains(termo_regex_fluig, case=False, na=False, regex=True) |
                df_form_filtrado.get(col_desc_mestre, pd.Series(dtype=str)).astype(str).str.contains(pattern_desc_fluig, case=False, na=False, regex=True)
            ]
            
        if busca_secao_fluig and 'SECAO' in df_form_filtrado.columns:
            df_form_filtrado = df_form_filtrado[df_form_filtrado['SECAO'].str.contains(busca_secao_fluig, case=False, na=False)]
            
        if busca_grp_usu_fluig and 'GRUPO USUARIOS' in df_form_filtrado.columns:
            df_form_filtrado = df_form_filtrado[df_form_filtrado['GRUPO USUARIOS'].str.contains(busca_grp_usu_fluig, case=False, na=False)]
            
        if busca_aprovador_fluig:
            cols_aprovadores = ['ENCARREGADO', 'ENGENHEIRO', 'SUPERINTENDENTE', 'DIRETOR', 'RH LOCAL', 'CONT MANUT']
            cols_existentes_aprov = [c for c in cols_aprovadores if c in df_form_filtrado.columns]
            
            if cols_existentes_aprov:
                mask = pd.Series(False, index=df_form_filtrado.index)
                for col in cols_existentes_aprov:
                    mask = mask | df_form_filtrado[col].astype(str).str.contains(busca_aprovador_fluig, case=False, na=False)
                df_form_filtrado = df_form_filtrado[mask]

        # Mantém todas as linhas para que CCs com seções diferentes apareçam
        indices_fluig = df_form_filtrado.index.tolist()
        
        col_tit_f, col_btn_f = st.columns([3, 1])
        with col_tit_f:
            try:
                total_f = len(df_form)
            except:
                total_f = len(df_form)
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 5px; margin-top:20px;">
                <h3 style="margin:0; padding:0; color:var(--text-color); font-weight: bold; border-left: 4px solid #e74c3c; padding-left: 10px;">📝 Explorador Fluig</h3>
                <div style="display: flex; gap: 24px; text-align: center; font-size: 0.8rem; font-weight: 800; color: var(--text-color); opacity: 0.7;">
                    <div>TOTAL FLUIG<br><span style="color:var(--text-color); font-size:1.1rem; opacity: 1;">{total_f}</span></div>
                    <div>VISÍVEIS<br><span style="color:var(--text-color); font-size:1.1rem; opacity: 1;">{len(indices_fluig)}</span></div>
                    <div>STATUS<br><span style="color:#2ecc71; font-size:1.1rem; opacity: 1;">Ativo</span></div>
                </div>
            </div>
            <hr style="margin-top: 5px; border-color: var(--secondary-background-color); border-width: 1px;">
            """, unsafe_allow_html=True)
        
        if len(indices_fluig) == 0:
            st.warning("Nenhum resultado encontrado no Fluig com esses filtros.")
        else:
            # Gera a porra do botão de download igual no Protheus
            with col_btn_f:
                buffer_f = io.BytesIO()
                # Tira o lixo de coluna que você usou pra cruzar
                df_fluig_baixar = df_form_filtrado.drop(columns=['CC_CLEAN'], errors='ignore')
                
                with pd.ExcelWriter(buffer_f, engine='openpyxl') as writer:
                    df_fluig_baixar.to_excel(writer, index=False, sheet_name='Fluig_Filtrado')
                
                st.download_button(
                    label="📥 Baixar Excel",
                    data=buffer_f.getvalue(),
                    file_name="Aprovadores_Filtrados_Fluig.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            for idx in indices_fluig:
                dados_cc_fluig = df_form_filtrado.loc[[idx]]
                cc = dados_cc_fluig['C CUSTO'].iloc[0]
                
                if dados_cc_fluig.empty:
                    continue
                
                # Trava de segurança contra o seu KeyError:
                if col_desc_mestre in dados_cc_fluig.columns:
                    valor_desc = dados_cc_fluig[col_desc_mestre].iloc[0]
                    desc_cc = valor_desc if pd.notna(valor_desc) else "Sem descrição"
                else:
                    desc_cc = "Sem descrição"

                # ===== REGRA: Usar DESCRICAO FORM como título principal =====
                col_desc_form = next((c for c in dados_cc_fluig.columns if 'DESCRICAO' in c.upper() and 'FORM' in c.upper()), None)
                desc_form_limpa = None
                if col_desc_form:
                    val_desc_form = str(dados_cc_fluig[col_desc_form].iloc[0]).strip()
                    if val_desc_form.lower() not in ('nan', '', 'none'):
                        desc_form_limpa = val_desc_form
                
                if desc_form_limpa:
                    titulo_card = desc_form_limpa
                else:
                    # Fallback para NOME FORM ou padrão
                    col_nome_form = next((c for c in dados_cc_fluig.columns if 'NOME' in c.upper() and 'FORM' in c.upper()), None)
                    nome_form_limpo = None
                    if col_nome_form:
                        val_nome_form = str(dados_cc_fluig[col_nome_form].iloc[0]).strip()
                        if val_nome_form.lower() not in ('nan', '', 'none'):
                            nome_form_limpo = val_nome_form
                    
                    if nome_form_limpo:
                        titulo_card = nome_form_limpo
                    else:
                        cc_str = str(cc).strip()
                        titulo_card = f"{cc_str} - {desc_cc.upper()}"
                
                secao_x = str(dados_cc_fluig['SECAO'].iloc[0]).strip() if 'SECAO' in dados_cc_fluig.columns else "N/A"
                secao_x = "Não Informado" if secao_x.lower() == 'nan' else secao_x
                sub_1 = f"Centro de Custo: {cc} | Seção RM: {secao_x}"
                
                grupo_x = str(dados_cc_fluig['GRUPO USUARIOS'].iloc[0]).strip() if 'GRUPO USUARIOS' in dados_cc_fluig.columns else "Padrão"
                sub_2 = f"Grupo de Usuários: {grupo_x}"
                
                # Pega as datas de criação e edição
                datas_info = []
                
                if 'CRIACAO FORM' in dados_cc_fluig.columns:
                    val_criacao = str(dados_cc_fluig['CRIACAO FORM'].iloc[0]).strip()
                    if val_criacao and val_criacao.lower() != 'nan':
                        datas_info.append(f"CRIADO: {val_criacao}")
                        
                if 'EDICAO FORM' in dados_cc_fluig.columns:
                    val_edicao = str(dados_cc_fluig['EDICAO FORM'].iloc[0]).strip()
                    if val_edicao and val_edicao.lower() != 'nan':
                        datas_info.append(f"EDITADO: {val_edicao}")
                
                if not datas_info:
                    data_str = "ATUALIZADO: " + (data_formatada.split(' ')[0] if 'data_formatada' in globals() else "AGORA")
                else:
                    data_str = "<br>".join(datas_info)
                
                cargos_mapeados = ['ENCARREGADO', 'ENGENHEIRO', 'SUPERINTENDENTE', 'DIRETOR', 'RH LOCAL', 'CONT MANUT']
                aprovadores_encontrados = []
                for c_cargo in cargos_mapeados:
                    if c_cargo in dados_cc_fluig.columns:
                        nome_resp = str(dados_cc_fluig[c_cargo].iloc[0]).strip()
                        if nome_resp and nome_resp.lower() != 'nan':
                            aprovadores_encontrados.append((c_cargo.title(), nome_resp.title()))
                            
                titulo_expander = f"📝 {titulo_card}"
                with st.expander(titulo_expander, expanded=(str(st.session_state.expandir_todos).lower() == 'true')):
                    html_caixas = ""
                    for cargo, nome_resp in aprovadores_encontrados:
                        # Caixa reutilizando as classes CSS (adapta a cor ao sistema selecionado)
                        html_caixas += f"<div class='aprovador-box'><div class='aprovador-nivel'>{cargo.upper()}</div><div class='aprovador-nome'>{nome_resp}</div></div>"
                        
                    if not aprovadores_encontrados:
                        html_caixas = "<div style='color: #a0aab2; font-style: italic;'>Nenhum aprovador encontrado.</div>"
                        
                    html_final = f"<div style='padding-bottom: 15px; margin-top: -5px;'><div style='display: flex; justify-content: space-between; align-items: flex-start;'><div><p class='card-subtitle'>{sub_1}</p><p class='card-subtitle'>{sub_2}</p></div><div style='color: var(--text-color); opacity: 0.85; font-size: 0.85rem; font-weight: 600; text-align: right;'>{data_str}</div></div><div style='margin-top: 20px;'>{html_caixas}</div></div>"
                    st.markdown(html_final, unsafe_allow_html=True)
