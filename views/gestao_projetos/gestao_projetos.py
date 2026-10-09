import os
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from onedrive_downloader import download_excel_from_onedrive

import auth

auth.exigir_login(
    painel_nome="Gestão de Projetos",
    titulo_painel="Gestão de Projetos",
    subtitulo="Acompanhamento de Portfólio e Tarefas",
    icone="📊"
)

# Paleta corporativa neutra (acentos sóbrios sobre cards claros)
COR_STATUS = {
    "Concluído": "#16A34A",
    "Em andamento": "#D97706",
    "A iniciar": "#7C3AED",
    "Atrasado": "#DC2626",
    "Atraso": "#DC2626",
    "Pendente": "#2563EB",
}
COR_PRIMARIA = "#2563EB"


def obter_emoji_status(status):
    return {
        "Concluído": "🟢",
        "A iniciar": "🟣",
        "Em andamento": "🟡",
        "Atrasado": "🔴",
        "Atraso": "🔴",
    }.get(status, "⚪")


def limpar_filtros():
    st.session_state.projeto_filtro = "Todos"
    st.session_state.status_filtro = "Todos"
    st.session_state.busca_filtro = ""


CSS_DASHBOARD = """
<style>
    .gp-header {
        background: linear-gradient(100deg, rgba(37,99,235,0.10), rgba(37,99,235,0.0));
        border: 1px solid rgba(128,128,128,0.18);
        border-left: 5px solid #2563EB;
        border-radius: 14px;
        padding: 1.1rem 1.4rem;
        margin-bottom: 1.2rem;
    }
    .gp-header h1 {
        font-size: 1.5rem; font-weight: 800; margin: 0;
        color: var(--text-color);
        font-family: 'Segoe UI', Tahoma, sans-serif;
    }
    .gp-header p { margin: .2rem 0 0 0; font-size: .9rem; opacity: .7; }

    /* Grid de KPIs */
    .kpi-grid {
        display: grid; grid-template-columns: repeat(4, 1fr);
        gap: 16px; margin-bottom: .4rem;
    }
    .kpi-card {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 14px; padding: 1rem 1.1rem;
        box-shadow: 0 4px 14px rgba(0,0,0,0.06);
        position: relative; overflow: hidden;
        transition: transform .15s ease, box-shadow .15s ease;
    }
    .kpi-card:hover { transform: translateY(-3px); box-shadow: 0 8px 22px rgba(0,0,0,0.10); }
    .kpi-card::before {
        content: ""; position: absolute; top: 0; left: 0;
        width: 100%; height: 4px; background: var(--accent);
    }
    .kpi-row { display: flex; align-items: center; justify-content: space-between; }
    .kpi-label { font-size: .8rem; font-weight: 600; opacity: .75; text-transform: uppercase; letter-spacing: .4px; }
    .kpi-ic { font-size: 1.5rem; opacity: .9; }
    .kpi-value { font-size: 2.4rem; font-weight: 800; line-height: 1.1; color: var(--text-color); margin: .2rem 0 .1rem 0; }
    .kpi-track { height: 6px; background: rgba(128,128,128,0.18); border-radius: 4px; overflow: hidden; margin-top: .35rem; }
    .kpi-fill { height: 100%; border-radius: 4px; background: var(--accent); }
    .kpi-sub { font-size: .75rem; opacity: .65; margin-top: .35rem; }
    h3 { font-weight: 700 !important; }
</style>
"""


def baixar_planilha_onedrive():
    try:
        local_dir = "/app/data"
        os.makedirs(local_dir, exist_ok=True)
        pasta_onedrive_rel = "Pasta_Compartilhada/Painel_Gestao/Projetos.xlsx"
        
        arquivo_excel = download_excel_from_onedrive(pasta_onedrive_rel)
        local_path = os.path.join(local_dir, "Projetos.xlsx")
        with open(local_path, "wb") as f:
            f.write(arquivo_excel.getvalue())
        return local_path
    except Exception as e:
        print("Erro ao baixar planilha Projetos.xlsx:", e)
        return None


def renderizar_dashboard():

    st.session_state.setdefault("projeto_filtro", "Todos")
    st.session_state.setdefault("status_filtro", "Todos")
    st.session_state.setdefault("busca_filtro", "")

    st.markdown(CSS_DASHBOARD, unsafe_allow_html=True)

    @st.cache_data(show_spinner="Carregando portfólio de projetos do Excel...", ttl=14400)
    def carregar_dados():
        caminho_fixo = baixar_planilha_onedrive() or "/app/data/Projetos.xlsx"
        try:
            df = pd.read_excel(caminho_fixo)
            # Garantir que as colunas padrão existam para não quebrar os filtros
            if "Projeto" not in df.columns:
                df["Projeto"] = df.iloc[:, 0] if not df.empty else "N/A"
            if "Status_Projeto" not in df.columns:
                df["Status_Projeto"] = "Em andamento"
            return df
        except Exception as e:
            st.error("Erro interno ao carregar a planilha de projetos.")
            return pd.DataFrame()

    df = carregar_dados()
    if df.empty:
        st.warning("Nenhum dado de projeto foi encontrado na base.")
        return

    # ── Cabeçalho ──────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="gp-header">
            <h1>📊 Visão Geral de Projetos</h1>
            <p>Acompanhamento de portfólio e auditoria de tarefas baseadas na nuvem.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Filtros ────────────────────────────────────────────────────────────
    col_filt1, col_filt2, col_filt3, col_btn = st.columns([3, 3, 3, 1.2])
    projetos_unicos = ["Todos"] + list(df["Projeto"].astype(str).unique())
    projeto_selecionado = col_filt1.selectbox("Filtrar por Projeto", projetos_unicos, key="projeto_filtro")
    status_unicos = ["Todos"] + list(df["Status_Projeto"].astype(str).unique())
    status_selecionado = col_filt2.selectbox("Filtrar por Status do Projeto", status_unicos, key="status_filtro")
    termo_busca = col_filt3.text_input("Pesquisar Projeto (Texto Livre)", key="busca_filtro")
    col_btn.markdown("<br>", unsafe_allow_html=True)
    col_btn.button("Limpar Filtros", on_click=limpar_filtros, use_container_width=True)

    df_filtrado = df.copy()
    if projeto_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Projeto"] == projeto_selecionado]
    if status_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Status_Projeto"] == status_selecionado]
    if termo_busca:
        df_filtrado = df_filtrado[df_filtrado["Projeto"].astype(str).str.contains(termo_busca, case=False, na=False)]

    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    projetos_filtrados = df_filtrado["Projeto"].unique()
    df_unicos = df_filtrado.drop_duplicates(subset=["Projeto"])

    # ── KPIs (render único em grid) ────────────────────────────────────────
    total = len(projetos_filtrados)
    qtd_concl = len(df_unicos[df_unicos["Status_Projeto"] == "Concluído"])
    qtd_and = len(df_unicos[df_unicos["Status_Projeto"] == "Em andamento"])
    qtd_atr = len(df_unicos[df_unicos["Status_Projeto"].isin(["Atrasado", "Atraso"])])

    def pct(parte):
        return int(round((parte / total) * 100)) if total else 0

    cards = [
        ("Total de Projetos", total, 100, COR_PRIMARIA, "📁", "Portfólio monitorado"),
        ("Concluídos", qtd_concl, pct(qtd_concl), COR_STATUS["Concluído"], "✅", f"{pct(qtd_concl)}% do portfólio"),
        ("Em Andamento", qtd_and, pct(qtd_and), COR_STATUS["Em andamento"], "⚙️", f"{pct(qtd_and)}% do portfólio"),
        ("Atrasados", qtd_atr, pct(qtd_atr), COR_STATUS["Atrasado"], "⚠️", f"{pct(qtd_atr)}% do portfólio"),
    ]
    html_cards = "".join(
        f'<div class="kpi-card" style="--accent:{cor};">'
        f'<div class="kpi-row"><span class="kpi-label">{label}</span><span class="kpi-ic">{ic}</span></div>'
        f'<div class="kpi-value">{valor}</div>'
        f'<div class="kpi-track"><div class="kpi-fill" style="width:{p}%;"></div></div>'
        f'<div class="kpi-sub">{sub}</div>'
        f'</div>'
        for label, valor, p, cor, ic, sub in cards
    )
    st.markdown(f'<div class="kpi-grid">{html_cards}</div>', unsafe_allow_html=True)

    st.divider()

    # ── Gráficos + Detalhamento ────────────────────────────────────────────
    st.markdown("### 📋 Detalhamento dos Projetos (Visualização em Tabela)")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)


renderizar_dashboard()
