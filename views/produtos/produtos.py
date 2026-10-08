import os
import html
import streamlit as st
import pandas as pd

# NOTE: st.set_page_config() NÃO deve ser chamado aqui. Esta é uma página servida
# via st.navigation (main.py), que é o único ponto autorizado a configurar a página.
# Chamá-lo novamente numa página filha levanta StreamlitAPIException.

# -----------------------------------------------------------------------------
# Estilo "cockpit": denso, leitura rápida, acabamento premium e sem frescura.
# Tudo via variáveis de tema do Streamlit (var(--text-color)) + rgba neutro,
# então funciona em tema claro e escuro sem texto ilegível. Escopo restrito ao
# conteúdo principal ([data-testid="stMain"]) para não conflitar com a sidebar.
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

      :root { --ck-accent: #0284c7; }

      [data-testid="stMain"] {
          font-family: 'Geist', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;
      }

      /* Container mais apertado em cima para densidade de cockpit */
      [data-testid="stMain"] .block-container {
          padding-top: 1.6rem;
          padding-bottom: 3rem;
          max-width: 95%;
      }

      /* ---- Faixa de KPIs: sem cards, dividida por linhas de 1px ---- */
      .ck-stats {
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 0;
          margin: 1.1rem 0 1.5rem;
          border-top: 1px solid rgba(128, 128, 128, 0.22);
          border-bottom: 1px solid rgba(128, 128, 128, 0.22);
      }
      .ck-stat {
          padding: 0.85rem 1.05rem 0.9rem;
          border-left: 1px solid rgba(128, 128, 128, 0.16);
          transition: background-color 0.2s ease;
      }
      .ck-stat:first-child {
          border-left: none;
          padding-left: 0.1rem;
      }
      .ck-stat-label {
          font-size: 0.64rem;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: rgba(128, 128, 128, 0.9);
          font-weight: 600;
          margin-bottom: 0.4rem;
          white-space: nowrap;
          transition: color 0.2s ease;
      }
      .ck-stat-value {
          font-family: 'JetBrains Mono', monospace;
          font-size: 1.5rem;
          font-weight: 600;
          letter-spacing: -0.02em;
          line-height: 1;
          color: var(--text-color);
          font-variant-numeric: tabular-nums;
          transition: color 0.2s ease;
      }
      .ck-stat-value.accent { color: var(--ck-accent); }
      .ck-stat-value.pos    { color: #FILIAL_28; }
      .ck-stat-value.neg    { color: #dc2626; }

      /* Hover: fundo neutro discreto + cor da fonte intensificada (mantém o hue) */
      .ck-stat:hover { background-color: rgba(128, 128, 128, 0.07); }
      .ck-stat:hover .ck-stat-label        { color: var(--ck-accent); }
      .ck-stat:hover .ck-stat-value        { color: var(--ck-accent); }
      .ck-stat:hover .ck-stat-value.accent { color: #0ea5e9; }
      .ck-stat:hover .ck-stat-value.pos    { color: #10b981; }
      .ck-stat:hover .ck-stat-value.neg    { color: #f43f5e; }
      .ck-stat-sub {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.64rem;
          color: rgba(128, 128, 128, 0.8);
          margin-top: 0.3rem;
          font-variant-numeric: tabular-nums;
      }

      /* ---- Rótulo de seção: mono, com filete de acento ---- */
      .ck-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.7rem;
          letter-spacing: 0.14em;
          text-transform: uppercase;
          color: rgba(128, 128, 128, 0.95);
          font-weight: 600;
          margin: 0.2rem 0 0.6rem;
          padding-left: 0.6rem;
          border-left: 2px solid var(--ck-accent);
      }

      /* ---- Inputs compactos, foco com o acento ---- */
      [data-testid="stMain"] .stTextInput label {
          font-size: 0.7rem !important;
          font-weight: 600 !important;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: rgba(128, 128, 128, 0.95) !important;
      }
      [data-testid="stMain"] .stTextInput input {
          border-radius: 8px !important;
          font-size: 0.85rem;
      }
      [data-testid="stMain"] .stTextInput input:focus {
          border-color: var(--ck-accent) !important;
          box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15) !important;
      }

      /* ---- Tabela HTML com pills de status ---- */
      .ck-table-wrap {
          border: 1px solid rgba(128, 128, 128, 0.22);
          border-radius: 10px;
          overflow: auto;
          max-height: 560px;
      }
      table.ck-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.82rem;
      }
      table.ck-table thead th {
          position: sticky;
          top: 0;
          z-index: 1;
          background: var(--background-color);
          text-align: left;
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.64rem;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: rgba(128, 128, 128, 0.95);
          font-weight: 600;
          padding: 0.7rem 0.9rem;
          border-bottom: 1px solid rgba(128, 128, 128, 0.28);
          white-space: nowrap;
      }
      table.ck-table tbody td {
          padding: 0.5rem 0.9rem;
          border-bottom: 1px solid rgba(128, 128, 128, 0.14);
          color: var(--text-color);
          vertical-align: middle;
      }
      table.ck-table tbody tr:last-child td { border-bottom: none; }
      table.ck-table tbody tr:hover td { background: rgba(128, 128, 128, 0.06); }
      table.ck-table td.code {
          font-family: 'JetBrains Mono', monospace;
          font-variant-numeric: tabular-nums;
          white-space: nowrap;
          color: rgba(128, 128, 128, 0.95);
      }
      .pill {
          display: inline-block;
          padding: 0.12rem 0.6rem;
          border-radius: 999px;
          font-size: 0.7rem;
          font-weight: 600;
          letter-spacing: 0.04em;
          line-height: 1.45;
          white-space: nowrap;
      }
      .pill-ok      { background: #FILIAL_28; color: #ffffff; border: 1px solid #FILIAL_30; }
      .pill-block   { background: #dc2626; color: #ffffff; border: 1px solid #b91c1c; }
      .pill-neutral { background: rgba(128, 128, 128, 0.14); color: rgba(128, 128, 128, 0.95); border: 1px solid rgba(128, 128, 128, 0.22); }
      .pill-yes     { background: rgba(16, 185, 129, 0.10); color: #FILIAL_28; border: 1px solid rgba(16, 185, 129, 0.22); }
      .pill-no      { background: rgba(128, 128, 128, 0.10); color: rgba(128, 128, 128, 0.9); border: 1px solid rgba(128, 128, 128, 0.20); }

      /* ---- Estado vazio composto ---- */
      .ck-empty {
          border: 1px dashed rgba(128, 128, 128, 0.3);
          border-radius: 10px;
          padding: 2.4rem 1.5rem;
          text-align: center;
      }
      .ck-empty .t {
          font-weight: 600;
          color: var(--text-color);
          margin-bottom: 0.3rem;
      }
      .ck-empty .s {
          font-size: 0.85rem;
          color: rgba(128, 128, 128, 0.95);
      }

      /* ---- Colapso para mobile: KPIs em 2 colunas ---- */
      @media (max-width: 768px) {
          .ck-stats { grid-template-columns: repeat(2, 1fr); }
          .ck-stat {
              border-left: 1px solid rgba(128, 128, 128, 0.16);
              border-top: 1px solid rgba(128, 128, 128, 0.16);
          }
          .ck-stat:nth-child(odd) { border-left: none; padding-left: 0.1rem; }
          .ck-stat:nth-child(-n+2) { border-top: none; }
      }

      /* ---- Estilo das Abas (Botões) no Cabeçalho ---- */
      [data-testid="stMain"] .stButton button {
          border-radius: 8px !important;
          font-weight: 600 !important;
          letter-spacing: 0.02em;
          transition: all 0.2s ease !important;
          height: 2.6rem;
      }
      
      /* Visual limpo: esconde menu/rodapé padrão */
      #MainMenu, footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Caminho do arquivo de base de dados gerado pelo bot
FILE_PRODUTO = "/app/data/Produtos.xlsx"


# Função com cache inteligente baseado na data de modificação do arquivo
@st.cache_data(show_spinner=False, ttl=14400)
def load_data(mtime):
    df = pd.read_excel(FILE_PRODUTO, sheet_name="Plan1")
    df.columns = [str(c).strip() for c in df.columns]

    if "B1_COD" in df.columns:
        df["B1_COD"] = (
            df["B1_COD"].astype(str)
            .str.replace(".0", "", regex=False)
            .str.replace(r"\s+", "", regex=True)
            .str.strip()
        )
        df["B1_COD"] = df["B1_COD"].replace("nan", "")
        df = df[df["B1_COD"] != ""]
        df["B1_COD_FMT"] = df["B1_COD"].astype(str).str.zfill(10)
    else:
        df["B1_COD"] = ""
        df["B1_COD_FMT"] = ""

    # Verifica produtos do Projeto_Alfa e filtra apenas EMPRESA_01
    projeto_alfa_cods = set()
    if "EMPRESA" in df.columns:
        df_ronc = df[df["EMPRESA"].astype(str).str.upper().str.strip() == "CONSORCIO PROJETO_ALFA"]
        projeto_alfa_cods = set(df_ronc["B1_COD_FMT"].unique())
        
        # Manter apenas EMPRESA_01
        df = df[df["EMPRESA"].astype(str).str.upper().str.strip() == "EMPRESA_01"].copy()

    df["CADASTRADO_PROJETO_ALFA"] = df["B1_COD_FMT"].apply(lambda x: "SIM" if x in projeto_alfa_cods else "NÃO")

    if "B1_DESC" in df.columns:
        df["B1_DESC"] = df["B1_DESC"].astype(str).str.strip().replace("nan", "")
    else:
        df["B1_DESC"] = ""

    if "B1_UM" in df.columns:
        df["B1_UM"] = df["B1_UM"].astype(str).str.strip().replace("nan", "")
    else:
        df["B1_UM"] = ""

    if "B1_TIPO" in df.columns:
        df["B1_TIPO"] = df["B1_TIPO"].astype(str).str.strip().replace("nan", "")
    else:
        df["B1_TIPO"] = ""
        
    if "BM_DESC" in df.columns:
        df["BM_DESC"] = df["BM_DESC"].astype(str).str.strip().replace("nan", "")
    else:
        df["BM_DESC"] = ""

    if "B1_MSBLQL" in df.columns:
        df["STATUS"] = df["B1_MSBLQL"].astype(str).str.strip()
        df["STATUS"] = df["STATUS"].map({"1": "BLOQUEADO", "2": "ATIVO", "1.0": "BLOQUEADO", "2.0": "ATIVO"}).fillna(df["STATUS"])
    else:
        df["STATUS"] = ""

    if "B1_XCONTA" in df.columns:
        df["CTA DESPESA"] = df["B1_XCONTA"].astype(str).str.strip().replace("nan", "")
    else:
        df["CTA DESPESA"] = ""

    if "B1_YCONTA" in df.columns:
        df["CTA CUSTO"] = df["B1_YCONTA"].astype(str).str.strip().replace("nan", "")
    else:
        df["CTA CUSTO"] = ""

    if "B1_POSIPI" in df.columns:
        df["NCM"] = df["B1_POSIPI"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip().replace("nan", "")
    else:
        df["NCM"] = ""

    if "B1_XTPCUST" in df.columns:
        df["B1_XTPCUST"] = df["B1_XTPCUST"].astype(str).str.strip().replace("nan", "")
    else:
        df["B1_XTPCUST"] = ""

    if "B1_CODISS" in df.columns:
        df["B1_CODISS"] = df["B1_CODISS"].astype(str).str.strip().replace("nan", "")
    else:
        df["B1_CODISS"] = ""

    if "B1_CODANP" in df.columns:
        df["B1_CODANP"] = df["B1_CODANP"].astype(str).str.strip().replace("nan", "")
    else:
        df["B1_CODANP"] = ""

    # Colunas auxiliares pré-computadas (uma única vez, dentro do cache) para que
    # a filtragem e os KPIs em cada rerun sejam apenas comparações vetorizadas.
    df["B1_DESC_LOW"] = df["B1_DESC"].str.lower()
    df["B1_COD_LOW"] = df["B1_COD"].str.lower()
    df["STATUS_UP"] = df["STATUS"].str.strip().str.upper()
    df["RONC_UP"] = df["CADASTRADO_PROJETO_ALFA"].str.upper()

    # Prepara visualização com Emojis no próprio cache para evitar apply() em tempo real
    df["STATUS_VIEW"] = df["STATUS_UP"].apply(
        lambda s: "🟢 ATIVO" if s == "ATIVO" else (f"🔴 {s}" if s in ("BLOQUEADO", "INATIVO") else s if s else "—")
    )
    df["PROJETO_ALFA_VIEW"] = df["RONC_UP"].apply(
        lambda s: "✅ SIM" if s == "SIM" else ("❌ NÃO" if s == "NÃO" else s)
    )

    # Ordena o DataFrame inteiro de forma crescente pelo código uma única vez
    df = df.sort_values(by="B1_COD_FMT", ascending=True)

    return df


@st.cache_data(show_spinner=False, ttl=14400)
def load_fornecedores(mtime):
    try:
        try:
            df = pd.read_excel(FILE_PRODUTO, sheet_name="Plan 3")
        except ValueError:
            df = pd.read_excel(FILE_PRODUTO, sheet_name="Plan3")
    except ValueError:
        return pd.DataFrame()
        
    df.columns = [str(c).strip() for c in df.columns]

    # Filtro A2_PJ='S' removido a pedido do usuário
    # if "A2_PJ" in df.columns:
    #     df = df[df["A2_PJ"].astype(str).str.strip().str.upper() != "S"].copy()

    def formata_banco(row):
        banco = str(row.get('A6_NREDUZ', '')).replace('nan', '').strip()
        ag = str(row.get('A2_AGENCIA', '')).replace('nan', '').strip()
        dvag = str(row.get('A2_DVAGE', '')).replace('nan', '').strip()
        cc = str(row.get('A2_NUMCON', '')).replace('nan', '').strip()
        dvcc = str(row.get('A2_DVCTA', '')).replace('nan', '').strip()
        pag = str(row.get('A2_FORMPAG', '')).replace('nan', '').strip()

        partes = []
        if banco:
            partes.append(f"🏦 {banco}")
        
        ag_full = f"{ag}-{dvag}" if dvag and dvag != "nan" else ag
        if ag_full and ag_full != "-":
            partes.append(f"Ag: {ag_full}")
            
        cc_full = f"{cc}-{dvcc}" if dvcc and dvcc != "nan" else cc
        if cc_full and cc_full != "-":
            partes.append(f"CC: {cc_full}")
            
        if pag:
            partes.append(f"Form Pag: {pag}")

        return " • ".join(partes) if partes else "—"

    df["BANCO_EMPRESA_X"] = df.apply(formata_banco, axis=1)

    def extrair_cnae(row):
        for col in ["A2_CNAE", "CNAE", "CNAE2", "A2_CNAE2"]:
            if col in row.index:
                val = str(row[col]).replace("nan", "").strip()
                if val: return val
        return "—"
        
    df["CNAE_EMPRESA_X"] = df.apply(extrair_cnae, axis=1)

    projeto_alfa_cgcs = set()
    projeto_alfa_bancos = {}
    projeto_alfa_cnae = {}
    projeto_alfa_cadastral = {}
    if "EMPRESA" in df.columns:
        df_ronc = df[df["EMPRESA"].astype(str).str.upper().str.strip() == "CONSORCIO PROJETO_ALFA"]
        for _, row in df_ronc.iterrows():
            cgc = str(row.get("A2_CGC", "")).strip()
            if cgc and cgc != "nan":
                projeto_alfa_cgcs.add(cgc)
                projeto_alfa_bancos[cgc] = row.get("BANCO_EMPRESA_X", "—")
                projeto_alfa_cnae[cgc] = extrair_cnae(row)
                projeto_alfa_cadastral[cgc] = {
                    "TIPO": str(row.get("A2_TIPO", "—")).replace('nan', '—').strip(),
                    "INSCR": str(row.get("A2_INSCR", "—")).replace('nan', '—').strip(),
                    "INSCRM": str(row.get("A2_INSCRM", "—")).replace('nan', '—').strip(),
                    "EMAIL": str(row.get("A2_EMAIL", "—")).replace('nan', '—').strip(),
                    "DDD": str(row.get("A2_DDD", "—")).replace('nan', '—').strip(),
                    "TEL": str(row.get("A2_TEL", "—")).replace('nan', '—').strip(),
                    "FAX": str(row.get("A2_FAX", "—")).replace('nan', '—').strip(),
                    "END": str(row.get("A2_END", "—")).replace('nan', '—').strip(),
                    "BAIRRO": str(row.get("A2_BAIRRO", "—")).replace('nan', '—').strip(),
                    "MUN": str(row.get("A2_MUN", "—")).replace('nan', '—').strip(),
                    "EST": str(row.get("A2_EST", "—")).replace('nan', '—').strip(),
                    "CODANP": str(row.get("A2_CODANP", "—")).replace('nan', '—').strip(),
                    "AUTSPED": str(row.get("A2_AUTSPED", "—")).replace('nan', '—').strip()
                }
        
        df = df[df["EMPRESA"].astype(str).str.upper().str.strip() == "EMPRESA_01"].copy()
    
    if "A2_LOJA" in df.columns:
        df["A2_LOJA"] = df["A2_LOJA"].astype(str).str.replace(".0", "", regex=False).str.strip().str.zfill(2)

    df["PROJETO_ALFA_VIEW"] = df["A2_CGC"].astype(str).str.strip().apply(lambda x: "✅ SIM" if x in projeto_alfa_cgcs and x != "nan" and x != "" else "❌ NÃO")
    df["BANCO_PROJETO_ALFA"] = df["A2_CGC"].astype(str).str.strip().map(projeto_alfa_bancos).fillna("—")
    df["CNAE_PROJETO_ALFA"] = df["A2_CGC"].astype(str).str.strip().map(projeto_alfa_cnae).fillna("—")
    df["CADASTRO_PROJETO_ALFA"] = df["A2_CGC"].astype(str).str.strip().map(lambda x: projeto_alfa_cadastral.get(x, {}))

    def formata_repr(row):
        nome = str(row.get('A2_NOMRESP', '')).replace('nan', '').strip()
        cpf = str(row.get('A2_REPRCGC', '')).replace('nan', '').strip()
        if nome and cpf:
            return f"{nome} (CPF/CNPJ: {cpf})"
        elif nome:
            return nome
        elif cpf:
            return f"CPF/CNPJ: {cpf}"
        return ""

    df["REPRESENTANTE"] = df.apply(formata_repr, axis=1)

    if "A2_MSBLQL" in df.columns:
        df["STATUS"] = df["A2_MSBLQL"].astype(str).str.strip()
        df["STATUS"] = df["STATUS"].map({"1": "BLOQUEADO", "2": "ATIVO", "1.0": "BLOQUEADO", "2.0": "ATIVO"}).fillna(df["STATUS"])
    else:
        df["STATUS"] = ""

    df["STATUS_UP"] = df["STATUS"].str.strip().str.upper()
    df["STATUS_VIEW"] = df["STATUS_UP"].apply(
        lambda s: "🟢 ATIVO" if s == "ATIVO" else (f"🔴 {s}" if s in ("BLOQUEADO", "INATIVO") else s if s else "—")
    )
    
    for c in ["A2_COD", "A2_NOME", "A2_CGC"]:
        if c not in df.columns:
            df[c] = ""
        else:
            df[c] = df[c].astype(str).str.strip().replace("nan", "")
            
    df["A2_COD_LOW"] = df["A2_COD"].str.lower()
    df["A2_NOME_LOW"] = df["A2_NOME"].str.lower()
    df["A2_CGC_LOW"] = df["A2_CGC"].str.lower()
    
    return df


# Formata inteiros no padrão BR (1.234)
def fmt(n):
    return f"{int(n):,}".replace(",", ".")


# --- Carregamento + estados de erro/vazio ---------------------------------
if not os.path.exists(FILE_PRODUTO):
    st.markdown(
        f'<div class="ck-empty"><div class="t">Base de dados não encontrada</div>'
        f'<div class="s">Esperado em <code>{FILE_PRODUTO}</code>. '
        f"Verifique se o arquivo Produto.xlsx está na pasta data.</div></div>",
        unsafe_allow_html=True,
    )
    st.stop()

try:
    mtime = os.path.getmtime(FILE_PRODUTO) if os.path.exists(FILE_PRODUTO) else 0
    with st.spinner("Carregando base de dados..."):
        df_produtos = load_data(mtime)
        df_fornecedores = load_fornecedores(mtime)
except Exception as e:
    st.error("Falha ao ler a planilha.")
    st.stop()

if df_produtos.empty and df_fornecedores.empty:
    st.markdown(
        '<div class="ck-empty"><div class="t">Nenhum registro na base</div>'
        '<div class="s">A planilha foi lida, mas não há registros de produtos nem de fornecedores.</div></div>',
        unsafe_allow_html=True,
    )
    st.stop()

# --- Cabeçalho ---
if "visao_ativa" not in st.session_state:
    st.session_state["visao_ativa"] = "📦 Produtos"

col_title, col_tabs = st.columns([1.5, 1])

with col_title:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    try:
        import ui_utils
        ui_utils.render_standard_panel(
            title="Consulta Produtos e Fornecedores",
            subtitle="Consulta de Produtos e Fornecedores",
            icon_name="Produtos.png"
        )
    except ImportError:
        st.title("📦 Consulta Produtos e Fornecedores")

with col_tabs:
    st.write("")
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📦 Produtos", use_container_width=True, type="primary" if st.session_state["visao_ativa"] == "📦 Produtos" else "secondary"):
            st.session_state["visao_ativa"] = "📦 Produtos"
            st.rerun()
    with c2:
        if st.button("🏢 Fornecedores", use_container_width=True, type="primary" if st.session_state["visao_ativa"] == "🏢 Fornecedores" else "secondary"):
            st.session_state["visao_ativa"] = "🏢 Fornecedores"
            st.rerun()

visao = st.session_state["visao_ativa"]



if visao == "📦 Produtos":
    total_base = len(df_produtos)

    # --- Filtros --------------------------------------------------------------
    st.markdown('<div class="ck-label">Filtros de pesquisa (Produtos)</div>', unsafe_allow_html=True)

    CAMPOS_FILTRO = ("f_codigo", "f_desc_1", "f_desc_2", "f_desc_3", "f_status", "f_tipo", "f_grupo")

    def _limpar_filtros():
        for chave in CAMPOS_FILTRO:
            st.session_state[chave] = ""

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pesquisa_codigo = st.text_input("Código", placeholder="Ex.: 0000012345", key="f_codigo")
    with col2:
        pesquisa_desc_1 = st.text_input("Descrição contém", placeholder="Palavra 1", key="f_desc_1")
    with col3:
        pesquisa_desc_2 = st.text_input("E também contém", placeholder="Palavra 2", key="f_desc_2")
    with col4:
        pesquisa_desc_3 = st.text_input("E também contém ", placeholder="Palavra 3", key="f_desc_3")

    col5, col6, col7 = st.columns(3)
    with col5:
        opcoes_status = [""] + sorted([str(x) for x in df_produtos["STATUS"].unique() if str(x).strip()])
        pesquisa_status = st.selectbox("Status", options=opcoes_status, format_func=lambda x: "Todos" if x == "" else x, key="f_status")
    with col6:
        opcoes_tipo = [""] + sorted([str(x) for x in df_produtos["B1_TIPO"].unique() if str(x).strip()])
        pesquisa_tipo = st.selectbox("Tipo", options=opcoes_tipo, format_func=lambda x: "Todos" if x == "" else x, key="f_tipo")
    with col7:
        df_grupos = df_produtos[df_produtos["B1_TIPO"] == pesquisa_tipo] if pesquisa_tipo else df_produtos
        opcoes_grupo = [""] + sorted([str(x) for x in df_grupos["BM_DESC"].unique() if str(x).strip()])
        
        if st.session_state.get("f_grupo") and st.session_state.get("f_grupo") not in opcoes_grupo:
            st.session_state["f_grupo"] = ""
            
        pesquisa_grupo = st.selectbox("Grupo", options=opcoes_grupo, format_func=lambda x: "Todos" if x == "" else x, key="f_grupo")

    if any(st.session_state.get(c, "") for c in CAMPOS_FILTRO):
        st.button("🧹 Limpar filtros", on_click=_limpar_filtros)

    def _aplicar_filtros(df, cod, desc_1, desc_2, desc_3, status, tipo, grupo):
        mask = pd.Series(True, index=df.index)

        cod = (cod or "").strip()
        if cod:
            codigo_digits = "".join(ch for ch in cod if ch.isdigit())
            if codigo_digits:
                codigo_fmt = codigo_digits.zfill(10)
                if len(codigo_digits) == 10:
                    mask &= df["B1_COD_FMT"] == codigo_fmt
                else:
                    mask &= df["B1_COD_FMT"].str.startswith(codigo_fmt)
            else:
                mask &= df["B1_COD_LOW"].str.contains(cod.lower(), regex=False, na=False)

        for termo in (desc_1, desc_2, desc_3):
            termo = (termo or "").strip()
            if termo:
                mask &= df["B1_DESC_LOW"].str.contains(termo.lower(), regex=False, na=False)

        if status:
            mask &= df["STATUS"] == status
        if tipo:
            mask &= df["B1_TIPO"] == tipo
        if grupo:
            mask &= df["BM_DESC"] == grupo

        return df[mask]

    filtro_com_erro = False
    try:
        df_filtrado = _aplicar_filtros(
            df_produtos, pesquisa_codigo, pesquisa_desc_1, pesquisa_desc_2, pesquisa_desc_3,
            pesquisa_status, pesquisa_tipo, pesquisa_grupo
        )
    except Exception:
        filtro_com_erro = True
        df_filtrado = df_produtos.iloc[0:0] 
        st.warning(
            "Não foi possível aplicar a pesquisa com os termos informados. "
            "Revise os campos e tente novamente usando apenas o código ou palavras da descrição."
        )

    total_result = len(df_filtrado)
    status_up = df_filtrado["STATUS_UP"]
    ativos = int((status_up == "ATIVO").sum())
    bloqueados = int(status_up.isin(["BLOQUEADO", "INATIVO"]).sum())
    ronc_sim = int((df_filtrado["RONC_UP"] == "SIM").sum())
    pct_ronc = (ronc_sim / total_result * 100) if total_result else 0
    filtros_ativos = sum(bool(x) for x in [pesquisa_codigo, pesquisa_desc_1, pesquisa_desc_2, pesquisa_desc_3, pesquisa_status, pesquisa_tipo, pesquisa_grupo])

    st.markdown(
        f"""
        <div class="ck-stats">
            <div class="ck-stat">
                <div class="ck-stat-label">Resultados</div>
                <div class="ck-stat-value accent">{fmt(total_result)}</div>
            </div>
            <div class="ck-stat">
                <div class="ck-stat-label">Ativos</div>
                <div class="ck-stat-value pos">{fmt(ativos)}</div>
            </div>
            <div class="ck-stat">
                <div class="ck-stat-label">Bloq. / inativos</div>
                <div class="ck-stat-value neg">{fmt(bloqueados)}</div>
            </div>
            <div class="ck-stat">
                <div class="ck-stat-label">base Projeto_Alfa</div>
                <div class="ck-stat-value">{fmt(ronc_sim)}</div>
                <div class="ck-stat-sub">{pct_ronc:.1f}% do resultado</div>
            </div>
            <div class="ck-stat">
                <div class="ck-stat-label">Filtros ativos</div>
                <div class="ck-stat-value">{filtros_ativos}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Resultados", divider="blue")

    if total_result == 0:
        st.markdown(
            '<div class="ck-empty"><div class="t">Nenhum produto encontrado</div>'
            '<div class="s">Ajuste o código ou as palavras da descrição para ampliar a busca.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        colunas_exibicao = {
            "B1_COD_FMT": "CÓDIGO",
            "B1_DESC": "DESCRIÇÃO",
            "B1_UM": "UN MEDIDA",
            "B1_TIPO": "TIPO",
            "BM_DESC": "GRUPO",
            "STATUS_VIEW": "STATUS",
            "PROJETO_ALFA_VIEW": "BASE PROJETO_ALFA",
            "CTA DESPESA": "CTA DESPESA",
            "CTA CUSTO": "CTA CUSTO",
            "NCM": "NCM",
            "B1_XTPCUST": "TIPO CUSTO",
            "B1_CODISS": "COD ISS",
            "B1_CODANP": "COD ANP",
        }
        colunas_presentes = [c for c in colunas_exibicao if c in df_filtrado.columns]
        df_final = df_filtrado[colunas_presentes].rename(columns=colunas_exibicao)
        ordem_cols = [c for c in ["CÓDIGO", "DESCRIÇÃO", "UN MEDIDA", "TIPO", "GRUPO", "STATUS", "BASE PROJETO_ALFA", "CTA DESPESA", "CTA CUSTO", "NCM", "TIPO CUSTO", "COD ISS", "COD ANP"] if c in df_final.columns]
        df_view = df_final[ordem_cols].copy()

        st.dataframe(
            df_view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "CÓDIGO": st.column_config.TextColumn("CÓDIGO", width="small"),
                "DESCRIÇÃO": st.column_config.TextColumn("DESCRIÇÃO", width="large"),
                "UN MEDIDA": st.column_config.TextColumn("UN MEDIDA", width="small"),
                "TIPO": st.column_config.TextColumn("TIPO", width="small"),
                "GRUPO": st.column_config.TextColumn("GRUPO", width="medium"),
                "STATUS": st.column_config.TextColumn("STATUS", width="small"),
                "BASE PROJETO_ALFA": st.column_config.TextColumn("BASE PROJETO_ALFA", width="small"),
                "CTA DESPESA": st.column_config.TextColumn("CTA DESPESA", width="small"),
                "CTA CUSTO": st.column_config.TextColumn("CTA CUSTO", width="small"),
                "NCM": st.column_config.TextColumn("NCM", width="small"),
                "TIPO CUSTO": st.column_config.TextColumn("TIPO CUSTO", width="small"),
                "COD ISS": st.column_config.TextColumn("COD ISS", width="small"),
                "COD ANP": st.column_config.TextColumn("COD ANP", width="small"),
            }
        )
else:
    # 🏢 FORNECEDORES
    total_base = len(df_fornecedores)

    st.markdown('<div class="ck-label">Filtros de pesquisa (Fornecedores)</div>', unsafe_allow_html=True)

    CAMPOS_FILTRO_FORN = ("f_forn_codigo", "f_forn_nome", "f_forn_nome_comp", "f_forn_cgc", "f_forn_status")

    def _limpar_filtros_forn():
        for chave in CAMPOS_FILTRO_FORN:
            st.session_state[chave] = ""

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        f_forn_codigo = st.text_input("Código", placeholder="Ex.: FILIAL_31", key="f_forn_codigo")
    with col2:
        f_forn_nome = st.text_input("Nome/Razão Social", placeholder="Nome", key="f_forn_nome")
    with col3:
        f_forn_nome_comp = st.text_input("Complemento Nome/Razão Social", placeholder="Complemento", key="f_forn_nome_comp")
    with col4:
        f_forn_cgc = st.text_input("CPF/CNPJ", placeholder="Apenas números", key="f_forn_cgc")
    with col5:
        opcoes_status_f = [""] + sorted([str(x) for x in df_fornecedores["STATUS"].unique() if str(x).strip()])
        f_forn_status = st.selectbox("Status", options=opcoes_status_f, format_func=lambda x: "Todos" if x == "" else x, key="f_forn_status")

    if any(st.session_state.get(c, "") for c in CAMPOS_FILTRO_FORN):
        st.button("🧹 Limpar filtros", on_click=_limpar_filtros_forn)

    def _aplicar_filtros_forn(df, cod, nome, nome_comp, cgc, status):
        mask = pd.Series(True, index=df.index)

        cod = (cod or "").strip().lower()
        if cod:
            mask &= df["A2_COD_LOW"].str.contains(cod, regex=False, na=False)

        nome = (nome or "").strip().lower()
        if nome:
            mask &= df["A2_NOME_LOW"].str.contains(nome, regex=False, na=False)
            
        nome_comp = (nome_comp or "").strip().lower()
        if nome_comp:
            mask &= df["A2_NOME_LOW"].str.contains(nome_comp, regex=False, na=False)
            
        cgc = (cgc or "").strip()
        if cgc:
            cgc_digits = "".join(ch for ch in cgc if ch.isdigit())
            if cgc_digits:
                mask &= df["A2_CGC_LOW"].str.contains(cgc_digits, regex=False, na=False)

        if status:
            mask &= df["STATUS"] == status

        return df[mask]

    try:
        df_filtrado = _aplicar_filtros_forn(
            df_fornecedores, f_forn_codigo, f_forn_nome, f_forn_nome_comp, f_forn_cgc, f_forn_status
        )
    except Exception:
        df_filtrado = df_fornecedores.iloc[0:0]
        st.warning("Erro ao aplicar filtros de fornecedores.")

    total_result = len(df_filtrado)
    status_up = df_filtrado["STATUS_UP"] if "STATUS_UP" in df_filtrado.columns else pd.Series()
    ativos = int((status_up == "ATIVO").sum())
    bloqueados = int(status_up.isin(["BLOQUEADO", "INATIVO"]).sum())
    
    ronc_sim = int((df_filtrado["PROJETO_ALFA_VIEW"] == "✅ SIM").sum()) if "PROJETO_ALFA_VIEW" in df_filtrado.columns else 0
    pct_ronc = (ronc_sim / total_result * 100) if total_result else 0
    
    filtros_ativos = sum(bool(x) for x in [f_forn_codigo, f_forn_nome, f_forn_nome_comp, f_forn_cgc, f_forn_status])

    st.markdown(
        f"""
        <div class="ck-stats">
            <div class="ck-stat">
                <div class="ck-stat-label">Resultados</div>
                <div class="ck-stat-value accent">{fmt(total_result)}</div>
            </div>
            <div class="ck-stat">
                <div class="ck-stat-label">Ativos</div>
                <div class="ck-stat-value pos">{fmt(ativos)}</div>
            </div>
            <div class="ck-stat">
                <div class="ck-stat-label">Bloq. / inativos</div>
                <div class="ck-stat-value neg">{fmt(bloqueados)}</div>
            </div>
            <div class="ck-stat">
                <div class="ck-stat-label">base Projeto_Alfa</div>
                <div class="ck-stat-value">{fmt(ronc_sim)}</div>
                <div class="ck-stat-sub">{pct_ronc:.1f}% do resultado</div>
            </div>
            <div class="ck-stat">
                <div class="ck-stat-label">Filtros ativos</div>
                <div class="ck-stat-value">{filtros_ativos}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Resultados", divider="blue")

    if total_result == 0:
        st.markdown(
            '<div class="ck-empty"><div class="t">Nenhum fornecedor encontrado</div>'
            '<div class="s">Ajuste os termos para ampliar a busca.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        colunas_exibicao = {
            "A2_COD": "CÓDIGO",
            "A2_LOJA": "LOJA",
            "A2_CGC": "CPF/CNPJ",
            "A2_NOME": "NOME",
            "A2_TIPO": "TIPO",
            "A2_INSCR": "INSC EST",
            "A2_INSCRM": "INSC MUN",
            "A2_EMAIL": "E-MAIL",
            "A2_END": "ENDEREÇO",
            "A2_BAIRRO": "BAIRRO",
            "A2_MUN": "MUNICIPIO",
            "A2_EST": "ESTADO",
            "STATUS_VIEW": "STATUS",
            "PROJETO_ALFA_VIEW": "BASE PROJETO_ALFA",
            "REPRESENTANTE": "REPRESENTANTE",
            "BANCO_EMPRESA_X": "BANCO_EMPRESA_X",
            "BANCO_PROJETO_ALFA": "BANCO_PROJETO_ALFA"
        }
        colunas_presentes = [c for c in colunas_exibicao if c in df_filtrado.columns]
        df_final = df_filtrado[colunas_presentes].rename(columns=colunas_exibicao)
        
        df_final["📁 DADOS CADASTRAIS"] = False
        df_final["🏦 BANCÁRIOS E REP."] = False
        
        ordem_cols = [c for c in ["BASE PROJETO_ALFA", "CÓDIGO", "LOJA", "CPF/CNPJ", "NOME", "📁 DADOS CADASTRAIS", "🏦 BANCÁRIOS E REP.", "STATUS"] if c in df_final.columns]
        df_view = df_final[ordem_cols].copy()
        
        colunas_desabilitadas = [c for c in ordem_cols if c not in ("📁 DADOS CADASTRAIS", "🏦 BANCÁRIOS E REP.")]

        if "editor_key" not in st.session_state:
            st.session_state["editor_key"] = 0

        def on_editor_change():
            key_atual = f"editor_fornecedores_{st.session_state['editor_key']}"
            state = st.session_state.get(key_atual, {})
            edited = state.get("edited_rows", {})
            for row_idx_str, edits in edited.items():
                if edits.get("📁 DADOS CADASTRAIS") or edits.get("🏦 BANCÁRIOS E REP."):
                    row_idx = int(row_idx_str)
                    st.session_state["modal_fornecedor_idx"] = row_idx
                    st.session_state["modal_fornecedor_cad"] = edits.get("📁 DADOS CADASTRAIS", False)
                    st.session_state["modal_fornecedor_ban"] = edits.get("🏦 BANCÁRIOS E REP.", False)
            
            # Força a recriação do componente para resetar os checkboxes visualmente
            st.session_state["editor_key"] += 1

        edited_df = st.data_editor(
            df_view,
            key=f"editor_fornecedores_{st.session_state['editor_key']}",
            on_change=on_editor_change,
            use_container_width=True,
            hide_index=True,
            disabled=colunas_desabilitadas,
            column_config={
                "BASE PROJETO_ALFA": st.column_config.TextColumn("BASE PROJETO_ALFA", width="small"),
                "CÓDIGO": st.column_config.TextColumn("CÓDIGO", width="small"),
                "LOJA": st.column_config.TextColumn("LOJA", width="small"),
                "CPF/CNPJ": st.column_config.TextColumn("CPF/CNPJ", width="medium"),
                "NOME": st.column_config.TextColumn("NOME", width="large"),
                "STATUS": st.column_config.TextColumn("STATUS", width="small"),
                "📁 DADOS CADASTRAIS": st.column_config.CheckboxColumn("📁 DADOS CADASTRAIS", width="small", help="Visualizar empresa, inscrição, endereço e CNAE"),
                "🏦 BANCÁRIOS E REP.": st.column_config.CheckboxColumn("🏦 BANCÁRIOS E REP.", width="small", help="Visualizar dados bancários e representante"),
            }
        )

        if st.session_state.get("modal_fornecedor_idx") is not None:
            row_idx = st.session_state["modal_fornecedor_idx"]
            
            if row_idx < len(df_view):
                row = df_view.iloc[row_idx]
                cnpj = row["CPF/CNPJ"]
                
                orig_row_final = df_final[df_final["CPF/CNPJ"] == cnpj].iloc[0]
                orig_row_filt = df_filtrado[df_filtrado["A2_CGC"] == cnpj].iloc[0]
                
                show_cadastrais = st.session_state.get("modal_fornecedor_cad", False)
                show_bancos = st.session_state.get("modal_fornecedor_ban", False)
                
                # Deleta da sessão para garantir que o modal não reabra após fechado
                del st.session_state["modal_fornecedor_idx"]
                
                # Função de exibição do Pop Up
                def mostrar_popup():
                    st.write(f"**Fornecedor:** {row['NOME']} (CPF/CNPJ: {cnpj})")
                    
                    if show_cadastrais:
                        st.markdown("---")
                        st.subheader("📁 Dados Cadastrais", divider="blue")
                        
                        tipo = str(orig_row_filt.get("A2_TIPO", "—")).replace('nan', '—').strip()
                        insc = str(orig_row_filt.get("A2_INSCR", "—")).replace('nan', '—').strip()
                        inscm = str(orig_row_filt.get("A2_INSCRM", "—")).replace('nan', '—').strip()
                        email = str(orig_row_filt.get("A2_EMAIL", "—")).replace('nan', '—').strip()
                        ddd = str(orig_row_filt.get("A2_DDD", "—")).replace('nan', '—').strip()
                        tel = str(orig_row_filt.get("A2_TEL", "—")).replace('nan', '—').strip()
                        fax = str(orig_row_filt.get("A2_FAX", "—")).replace('nan', '—').strip()
                        
                        cnae_empresax = orig_row_filt.get("CNAE_EMPRESA_X", "—")
                        cnae_ronc = orig_row_filt.get("CNAE_PROJETO_ALFA", "—")
                        
                        endereco = str(orig_row_filt.get("A2_END", "—")).replace('nan', '—').strip()
                        bairro = str(orig_row_filt.get("A2_BAIRRO", "—")).replace('nan', '—').strip()
                        municipio = str(orig_row_filt.get("A2_MUN", "—")).replace('nan', '—').strip()
                        estado = str(orig_row_filt.get("A2_EST", "—")).replace('nan', '—').strip()
                        codanp = str(orig_row_filt.get("A2_CODANP", "—")).replace('nan', '—').strip()
                        autsped = str(orig_row_filt.get("A2_AUTSPED", "—")).replace('nan', '—').strip()
                        
                        st.info(f"""**🏢 Base EMPRESA_01:**

- **Tipo:** {tipo}
- **CNAE:** {cnae_empresax}
- **Inscrição Estadual:** {insc}
- **Inscrição Municipal:** {inscm}
- **E-mail:** {email}
- **DDD:** {ddd}
- **Telefone 01:** {tel}
- **Telefone 02:** {fax}
- **Endereço:** {endereco} - {bairro}, {municipio} - {estado}
- **Cod ANP:** {codanp}
- **Aut s/ Pedido:** {autsped}""")
                        
                        cad_ronc = orig_row_filt.get("CADASTRO_PROJETO_ALFA", {})
                        if isinstance(cad_ronc, dict) and cad_ronc:
                            tipo_r = cad_ronc.get("TIPO", "—")
                            insc_r = cad_ronc.get("INSCR", "—")
                            inscm_r = cad_ronc.get("INSCRM", "—")
                            email_r = cad_ronc.get("EMAIL", "—")
                            ddd_r = cad_ronc.get("DDD", "—")
                            tel_r = cad_ronc.get("TEL", "—")
                            fax_r = cad_ronc.get("FAX", "—")
                            end_r = cad_ronc.get("END", "—")
                            bairro_r = cad_ronc.get("BAIRRO", "—")
                            mun_r = cad_ronc.get("MUN", "—")
                            est_r = cad_ronc.get("EST", "—")
                            codanp_r = cad_ronc.get("CODANP", "—")
                            autsped_r = cad_ronc.get("AUTSPED", "—")
                            
                            st.success(f"""**🚜 Base PROJETO_ALFA:**

- **Tipo:** {tipo_r}
- **CNAE:** {cnae_ronc}
- **Inscrição Estadual:** {insc_r}
- **Inscrição Municipal:** {inscm_r}
- **E-mail:** {email_r}
- **DDD:** {ddd_r}
- **Telefone 01:** {tel_r}
- **Telefone 02:** {fax_r}
- **Endereço:** {end_r} - {bairro_r}, {mun_r} - {est_r}
- **Cod ANP:** {codanp_r}
- **Aut s/ Pedido:** {autsped_r}""")
                        else:
                            st.success("**🚜 Base PROJETO_ALFA:**\n\nFornecedor não possui cadastro nesta base.")
                    
                    if show_bancos:
                        st.markdown("---")
                        st.subheader("🏦 Dados Bancários & Representante", divider="blue")
                        
                        banco_empresax = orig_row_filt.get("BANCO_EMPRESA_X", "—")
                        banco_ronc = orig_row_filt.get("BANCO_PROJETO_ALFA", "—")
                        repr_nome = orig_row_filt.get("REPRESENTANTE", "—")
                        
                        st.write(f"**🗣️ Representante:** {repr_nome}")
                        st.info(f"**🏢 Base EMPRESA_01 (Bancos):**\n\n{banco_empresax}")
                        st.success(f"**🚜 Base PROJETO_ALFA (Bancos):**\n\n{banco_ronc}")
                    
                # Verifica se st.dialog está disponível na versão atual do Streamlit
                titulo_modal = "Detalhes do Fornecedor"
                if hasattr(st, "dialog"):
                    @st.dialog(titulo_modal)
                    def modal_detalhes():
                        mostrar_popup()
                    modal_detalhes()
                elif hasattr(st, "experimental_dialog"):
                    @st.experimental_dialog(titulo_modal)
                    def modal_detalhes():
                        mostrar_popup()
                    modal_detalhes()
                else:
                    with st.expander(f"📋 {titulo_modal} (Selecionado)", expanded=True):
                        mostrar_popup()
