# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import os
import re
import time
import base64
from datetime import datetime, date, timedelta
from functools import lru_cache
import altair as alt
from dotenv import load_dotenv

load_dotenv()

# ── Constantes de módulo ───────────────────────────────────────────────────────
CAMINHO_ARQUIVO = (
    "Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/App controle EPI/EPIS 16-01-2026.xlsx"
)
_DIR_ICONS       = os.path.join(os.path.dirname(__file__), '..', 'EPI')
_ICON_ATUALIZAR  = os.path.normpath(os.path.join(_DIR_ICONS, 'atualizar.png'))
_ICON_ESCRITORIO = os.path.normpath(os.path.join(_DIR_ICONS, 'escritorio.png'))

import auth


# ── Helpers visuais ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=14400)
def _carregar_icones() -> tuple:
    """Lê imagens do disco e retorna base64 — executado uma vez por processo."""
    def _b64(path: str) -> str:
        if os.path.exists(path):
            with open(path, 'rb') as f:
                return base64.b64encode(f.read()).decode()
        return ''
    return _b64(_ICON_ATUALIZAR), _b64(_ICON_ESCRITORIO)


def _kpi(label: str, valor, icon: str, cor: str = "var(--epi-primary)", sub: str = "") -> str:
    """Retorna o HTML de um card de métrica (cores via tokens — adapta a claro/escuro)."""
    sub_html = (
        f'<div style="font-size:11px;color:var(--epi-text-subtle);margin-top:5px;">{sub}</div>'
        if sub else ""
    )
    return (
        f'<div class="epi-kpi-card" style="--card-accent:{cor};flex:1;background:var(--epi-surface);border-radius:14px;padding:18px 20px;'
        f'box-shadow:0 1px 4px var(--epi-shadow);border:1px solid var(--epi-border);'
        f'border-top:3px solid {cor};">'
        f'<div style="font-size:10.5px;font-weight:700;color:var(--epi-text-muted);text-transform:uppercase;'
        f'letter-spacing:0.08em;margin-bottom:10px;">{icon}&nbsp; {label}</div>'
        f'<div style="font-size:28px;font-weight:700;color:var(--epi-text);letter-spacing:-0.02em;">{valor}</div>'
        f'{sub_html}</div>'
    )


def _render_kpi_row(*cards: str) -> None:
    st.markdown(
        '<div style="display:flex;gap:14px;margin:0.5rem 0 1.5rem;">'
        + "".join(cards)
        + "</div>",
        unsafe_allow_html=True,
    )


def _ca_legend() -> None:
    st.markdown(
        '<div style="display:flex;gap:20px;margin-top:6px;margin-bottom:2px;'
        'font-size:11.5px;color:var(--epi-text-muted);">'
        '<span style="display:inline-flex;align-items:center;gap:6px;">'
        '<span style="display:inline-block;width:11px;height:11px;border-radius:3px;'
        'background:rgba(239,68,68,0.18);border:1px solid rgba(239,68,68,0.5);"></span>'
        'CA vencido</span>'
        '<span style="display:inline-flex;align-items:center;gap:6px;">'
        '<span style="display:inline-block;width:11px;height:11px;border-radius:3px;'
        'background:rgba(245,158,11,0.2);border:1px solid rgba(245,158,11,0.5);"></span>'
        'Vence em 30 dias</span>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Helpers de dados ────────────────────────────────────────────────────────────

@lru_cache(maxsize=128)
def extrair_regional_responsavel(col_name: str) -> tuple:
    """Extrai (regional, responsável) a partir do cabeçalho da coluna."""
    partes = col_name.split("-", 1) if "-" in col_name else [col_name]
    regional = partes[0].strip().title()
    if regional.upper().startswith("REG "):
        regional = regional[4:].strip()
    elif regional.upper().startswith("REG"):
        regional = regional[3:].strip()
    regional = regional.lstrip('. ')
    responsavel = partes[1].strip().title() if len(partes) > 1 else "Não Informado"
    return regional, responsavel


def _build_col_config(colunas_base: list) -> dict:
    """Constrói o dict de configuração de colunas."""
    cfg = {col: st.column_config.TextColumn(width="medium") for col in colunas_base}
    for col, width in [("DESCRICAO", "large"), ("COD", "small"), ("UNID", "small"), ("STATUS", "small")]:
        if col in colunas_base:
            cfg[col] = st.column_config.TextColumn(width=width)
    if "VALID CA" in colunas_base:
        cfg["VALID CA"] = st.column_config.DateColumn(
            "Validade CA", width="small", format="DD/MM/YYYY",
            help="Data de validade do Certificado de Aprovação"
        )
    return cfg


def _highlight_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica estilos ao DataFrame inteiro (axis=None) de forma vetorizada.
    Vermelho = CA vencido | Âmbar = vence em ≤30 dias | Cinza = coluna Total Geral.
    """
    hoje_ts = pd.Timestamp.today().normalize()
    em_30_ts = hoje_ts + pd.Timedelta(days=30)
    styles = pd.DataFrame('', index=df.index, columns=df.columns)

    if 'Total Geral' in df.columns:
        styles['Total Geral'] = 'background-color:rgba(100,116,139,0.08);font-weight:600;'

    if 'VALID CA' in df.columns:
        dates = pd.to_datetime(df['VALID CA'], errors='coerce')
        expired  = dates.notna() & (dates < hoje_ts)
        expiring = dates.notna() & (dates >= hoje_ts) & (dates <= em_30_ts)
        styles.loc[expiring] = 'background-color:rgba(245,158,11,0.13);'
        styles.loc[expired]  = 'background-color:rgba(239,68,68,0.13);'

    return styles


def _format_cod_series(series: pd.Series) -> pd.Series:
    """Formata a coluna COD de forma vetorizada."""
    s = series.astype(str).str.strip()
    empty = series.isna() | (s == '') | (s.str.lower() == 'nan')
    s = s.where(~empty, '')
    s = s.str.replace(r'\.0$', '', regex=True)
    numeric = s.str.isdigit() & (s != '')
    return s.where(~numeric, s.str.zfill(10))


def _carregar_dados(caminho: str) -> dict:
    """Lê e processa a planilha Excel; retorna dict com df, bd01 e logs."""
    xl = pd.ExcelFile(caminho)
    df = xl.parse(xl.sheet_names[0])

    if "COD" in df.columns:
        df["COD"] = _format_cod_series(df["COD"])

    if 'CA' in xl.sheet_names:
        df_ca = xl.parse('CA')
        col_ca = next((c for c in df_ca.columns if 'CA' in str(c).upper()), df_ca.columns[0])
        col_val = next(
            (c for c in df_ca.columns if 'VALID' in str(c).upper() or 'VENC' in str(c).upper()),
            df_ca.columns[1] if len(df_ca.columns) > 1 else None,
        )
        if col_val:
            df_ca_build = df_ca[[col_ca, col_val]].dropna(subset=[col_val]).copy()
            parsed = pd.to_datetime(df_ca_build[col_val], errors='coerce')
            df_ca_build['_val_str'] = parsed.dt.strftime('%d/%m/%Y')
            fallback = df_ca_build['_val_str'].isna()
            df_ca_build.loc[fallback, '_val_str'] = (
                df_ca_build.loc[fallback, col_val].astype(str).str.split(' ').str[0]
            )
            df_ca_build['_ca_key'] = (
                df_ca_build[col_ca].astype(str).str.strip().str.extract(r'(\d+)', expand=False)
            )
            df_ca_build = df_ca_build.dropna(subset=['_ca_key'])
            dict_ca = dict(zip(df_ca_build['_ca_key'], df_ca_build['_val_str']))

            def _extrair_ca(descricao):
                if pd.isna(descricao):
                    return None
                matches = re.finditer(
                    r'(?:C\.?A\.?)\s*[:=-]?\s*(\d+(?:[\s,/eE-]+\d+)*)',
                    str(descricao).upper(),
                )
                cas = [n for m in matches for n in re.findall(r'\d+', m.group(1))]
                datas = []
                for ca in cas:
                    val = dict_ca.get(ca)
                    if val:
                        try:
                            datas.append(datetime.strptime(val, '%d/%m/%Y').date())
                        except ValueError:
                            pass
                return min(datas) if datas else None

            col_desc = "DESCRICAO" if "DESCRICAO" in df.columns else (
                df.columns[1] if len(df.columns) > 1 else None
            )
            if col_desc:
                df['VALID CA'] = pd.to_datetime(df[col_desc].apply(_extrair_ca), errors='coerce')
                cols = list(df.columns)
                cols.remove('VALID CA')
                anchor = 'STATUS' if 'STATUS' in cols else col_desc
                cols.insert(cols.index(anchor) + 1, 'VALID CA')
                df = df[cols]

    bd01 = xl.parse('BD01').to_dict('records') if 'BD01' in xl.sheet_names else []

    if 'Logs de Alteração' in xl.sheet_names:
        logs_df = xl.parse('Logs de Alteração')
        sentinel = (
            "Mensagem" in logs_df.columns
            and len(logs_df) == 1
            and logs_df.iloc[0]["Mensagem"] == "Nenhuma alteração registrada."
        )
        logs = [] if sentinel else logs_df.to_dict('records')
    else:
        logs = []

    if 'STATUS' in df.columns:
        df = df[df['STATUS'].astype(str).str.strip().str.upper() == 'ATIVO'].reset_index(drop=True)

    return {"df": df, "bd01": bd01, "logs": logs}


def salvar_planilha():
    """Persiste o estado atual da sessão de volta para o arquivo Excel."""
    try:
        with pd.ExcelWriter(CAMINHO_ARQUIVO, engine='openpyxl') as writer:
            st.session_state['df'].to_excel(writer, sheet_name='Estoque Atualizado', index=False)
            if st.session_state.get('logs'):
                pd.DataFrame(st.session_state['logs']).to_excel(
                    writer, sheet_name='Logs de Alteração', index=False
                )
            else:
                pd.DataFrame({"Mensagem": ["Nenhuma alteração registrada."]}).to_excel(
                    writer, sheet_name='Logs de Alteração', index=False
                )
            if st.session_state.get('bd01'):
                pd.DataFrame(st.session_state['bd01']).to_excel(writer, sheet_name='BD01', index=False)
            else:
                pd.DataFrame({"Mensagem": ["Nenhuma atualização de CA registrada."]}).to_excel(
                    writer, sheet_name='BD01', index=False
                )
    except PermissionError:
        st.error("⚠️ Não foi possível salvar: planilha aberta no Excel. Feche-a e tente novamente.")
    except Exception as e:
        st.error("Erro interno ao salvar a planilha.")



# ── Tela de Login ──────────────────────────────────────────────────────────────

# Tela de login removida para usar o sistema centralizado


# ── Main ───────────────────────────────────────────────────────────────────────

def main():

    b64_atualizar, b64_escritorio = _carregar_icones()

    # ═══════════════════════════════════════════════════════════════
    # CSS GLOBAL — injetado antes do login para cobrir login + app
    # ═══════════════════════════════════════════════════════════════
    st.markdown(f"""
    <style>
    /* Botão Sair na sidebar */
    [class*=" st-key-btn_sair\] button {
 background: var(--epi-surface) !important;
 color: var(--epi-text) !important;
 border: 1px solid var(--epi-border) !important;
 }
 [class*=\st-key-btn_sair\] button:hover {
 background: var(--epi-surface-2) !important;
 border-color: var(--epi-primary) !important;
 }
    /* ══════════════════════════════════════════════════════════
       TOKENS DE TEMA — adaptam ao modo claro/escuro do navegador.
       Toda superfície/texto referencia estas variáveis; nenhuma cor
       sólida é fixada, então nada de card branco no modo escuro.
    ══════════════════════════════════════════════════════════ */
    :root {{
        --epi-page:         #EEF2F6;
        --epi-surface:      #FFFFFF;
        --epi-surface-2:    #F1F5F9;
        --epi-border:       #E2E8F0;
        --epi-text:         #0F172A;
        --epi-text-muted:   #64748B;
        --epi-text-subtle:  #94A3B8;
        --epi-primary:      #2563EB;
        --epi-primary-soft: rgba(37,99,235,0.10);
        --epi-shadow:       rgba(15,23,42,0.06);
        --epi-shadow-hover: rgba(37,99,235,0.16);
    }}
    @media (prefers-color-scheme: dark) {{
        :root {{
            --epi-page:         #0E1117;
            --epi-surface:      #1A2332;
            --epi-surface-2:    #141C2A;
            --epi-border:       #2A3850;
            --epi-text:         #E8EDF4;
            --epi-text-muted:   #9AA7BD;
            --epi-text-subtle:  #6B7A93;
            --epi-primary:      #3B82F6;
            --epi-primary-soft: rgba(59,130,246,0.16);
            --epi-shadow:       rgba(0,0,0,0.35);
            --epi-shadow-hover: rgba(0,0,0,0.50);
        }}
    }}

    /* ── Tipografia e reset global ───────────────────────────── */
    html, body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                     'Helvetica Neue', Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
    }}

    /* ── Oculta elementos do Streamlit ──────────────────────── */
    #MainMenu, footer, [data-testid="stHeader"] {{ visibility: hidden; }}
    .stDeployButton {{ display: none !important; }}
    [data-testid="stToolbar"] {{ display: none !important; }}

    /* ── Mantém o botão de reabrir sidebar e a nav de páginas ─ */
    [data-testid="collapsedControl"],
    [data-testid="collapsedControl"] * {{ visibility: visible !important; }}
    [data-testid="stSidebarNav"] {{ display: block !important; visibility: visible !important; }}
    [data-testid="stSidebarNav"] * {{ visibility: visible !important; }}

    /* ── Scrollbar ───────────────────────────────────────────── */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: var(--epi-border); border-radius: 10px; }}

    /* ── Fundo da página (token, segue o tema) ───────────────── */
    /* .stApp {{ background: var(--epi-page) !important; }} */
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1500px !important;
    }}

    /* ══════════════════════════════════════════════════════════
       SIDEBAR — segue o tema nativo do Streamlit; refinamos apenas
       tipografia/espaçamento para não impor cores fixas.
    ══════════════════════════════════════════════════════════ */
    [data-testid="stSidebar"] .stMarkdown h3 {{
        font-size: 10px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        color: var(--epi-text-subtle) !important;
        padding-bottom: 8px !important;
        border-bottom: 1px solid var(--epi-border) !important;
        margin-bottom: 4px !important;
    }}
    [data-testid="stSidebar"] hr {{
        border-color: var(--epi-border) !important;
        margin: 0.75rem 0 !important;
    }}

    /* ══════════════════════════════════════════════════════════
       BOTÕES — CARDS DE REGIONAL (kind="primary")
    ══════════════════════════════════════════════════════════ */
    button[kind="primary"] {{
        background: var(--epi-surface) !important;
        border: 1.5px solid var(--epi-border) !important;
        color: var(--epi-text) !important;
        border-radius: 14px !important;
        padding: 18px 22px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-start !important;
        justify-content: center !important;
        box-shadow: 0 1px 3px var(--epi-shadow) !important;
        transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s !important;
        min-height: 82px !important;
        white-space: pre-wrap !important;
        text-align: left !important;
        gap: 2px !important;
    }}
    button[kind="primary"]::before {{
        display: none !important;
    }}
    button[kind="primary"]:hover {{
        border-color: var(--epi-primary) !important;
        box-shadow: 0 6px 18px var(--epi-shadow-hover) !important;
        transform: translateY(-3px) !important;
    }}
    button[kind="primary"] p {{
        font-size: 13.5px !important;
        font-weight: 500 !important;
        line-height: 1.6 !important;
        margin: 0 !important;
        color: var(--epi-text-muted) !important;
    }}

    /* ── Botão Recarregar (override via #reload-marker) ──────── */
    div[data-testid="column"]:has(#reload-marker) button[kind="primary"],
    div[data-testid="stColumn"]:has(#reload-marker) button[kind="primary"] {{
        flex-direction: row !important;
        align-items: center !important;
        min-height: 40px !important;
        padding: 8px 14px !important;
        gap: 8px !important;
        border-radius: 8px !important;
        background: var(--epi-surface) !important;
        color: var(--epi-text-muted) !important;
    }}
    div[data-testid="column"]:has(#reload-marker) button[kind="primary"]::before,
    div[data-testid="stColumn"]:has(#reload-marker) button[kind="primary"]::before {{
        content: '';
        display: inline-block !important;
        width: 22px !important;
        height: 22px !important;
        background-image: url('data:image/png;base64,{b64_atualizar}') !important;
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        flex-shrink: 0;
    }}
    div[data-testid="column"]:has(#reload-marker) button[kind="primary"]:hover,
    div[data-testid="stColumn"]:has(#reload-marker) button[kind="primary"]:hover {{
        border-color: var(--epi-primary) !important;
        background: var(--epi-primary-soft) !important;
        transform: none !important;
    }}

    /* ── Botão Login (form submit) — gradiente azul (ok p/ ambos) ── */
    [data-testid="stFormSubmitButton"] button {{
        background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
        border: none !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        min-height: 46px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        flex-direction: row !important;
        justify-content: center !important;
        box-shadow: 0 4px 14px rgba(37,99,235,0.35) !important;
        transition: box-shadow 0.2s, transform 0.15s !important;
    }}
    [data-testid="stFormSubmitButton"] button::before {{
        display: none !important;
    }}
    [data-testid="stFormSubmitButton"] button:hover {{
        box-shadow: 0 6px 20px rgba(37,99,235,0.45) !important;
        transform: translateY(-1px) !important;
    }}

    /* ── Cards KPI (métricas) — efeito hover com cor do card ─── */
    .epi-kpi-card {{
        transition: transform 0.22s ease, box-shadow 0.22s ease, background 0.22s ease !important;
        cursor: default;
    }}
    .epi-kpi-card:hover {{
        transform: translateY(-4px) !important;
        background: color-mix(in srgb, var(--card-accent) 8%, var(--epi-surface)) !important;
        box-shadow: 0 10px 28px color-mix(in srgb, var(--card-accent) 32%, transparent) !important;
    }}

    /* ── Cards de regional — layout horizontal + ícone à esquerda ── */
    div[data-testid="column"]:has(.reg-icon-marker) button[kind="primary"],
    div[data-testid="stColumn"]:has(.reg-icon-marker) button[kind="primary"] {{
        flex-direction: row !important;
        align-items: center !important;
        gap: 14px !important;
    }}
    div[data-testid="column"]:has(.reg-icon-marker) button[kind="primary"]::before,
    div[data-testid="stColumn"]:has(.reg-icon-marker) button[kind="primary"]::before {{
        content: '' !important;
        display: block !important;
        width: 38px !important;
        height: 38px !important;
        min-width: 38px !important;
        background-image: url('data:image/png;base64,{b64_escritorio}') !important;
        background-size: contain !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        flex-shrink: 0 !important;
        opacity: 0.72;
        transition: opacity 0.2s !important;
    }}
    div[data-testid="column"]:has(.reg-icon-marker) button[kind="primary"]:hover::before,
    div[data-testid="stColumn"]:has(.reg-icon-marker) button[kind="primary"]:hover::before {{
        opacity: 1 !important;
    }}
    div[data-testid="column"]:has(.reg-icon-marker) button[kind="primary"] p::first-line,
    div[data-testid="stColumn"]:has(.reg-icon-marker) button[kind="primary"] p::first-line {{
        font-weight: 700 !important;
        color: var(--epi-text) !important;
    }}

    /* ── Botão primário dentro de dialogs ───────────────────── */
    [data-testid="stDialog"] button[kind="primary"],
    [data-testid="stModal"] button[kind="primary"] {{
        flex-direction: row !important;
        align-items: center !important;
        min-height: 42px !important;
        padding: 10px 24px !important;
        background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
        border: none !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(37,99,235,0.28) !important;
        white-space: normal !important;
        width: 100% !important;
    }}
    [data-testid="stDialog"] button[kind="primary"]::before,
    [data-testid="stModal"] button[kind="primary"]::before {{
        display: none !important;
    }}
    [data-testid="stDialog"] button[kind="primary"] p,
    [data-testid="stModal"] button[kind="primary"] p {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }}
    [data-testid="stDialog"] button[kind="primary"]:hover,
    [data-testid="stModal"] button[kind="primary"]:hover {{
        background: linear-gradient(135deg, #1D4ED8, #1E40AF) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 14px rgba(37,99,235,0.42) !important;
    }}

    /* ── Botões secundários ──────────────────────────────────── */
    button[kind="secondary"] {{
        background: var(--epi-surface) !important;
        border: 1.5px solid var(--epi-border) !important;
        color: var(--epi-text) !important;
        border-radius: 8px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        transition: border-color 0.18s, background 0.18s, color 0.18s !important;
    }}
    button[kind="secondary"]:hover {{
        background: var(--epi-surface-2) !important;
        border-color: var(--epi-primary) !important;
        color: var(--epi-primary) !important;
    }}

    /* ══════════════════════════════════════════════════════════
       TABS — estilo pill
    ══════════════════════════════════════════════════════════ */
    [data-testid="stTabs"] [role="tablist"] {{
        background: var(--epi-surface-2) !important;
        border-radius: 10px !important;
        padding: 3px !important;
        gap: 2px !important;
        border-bottom: none !important;
    }}
    [data-testid="stTabs"] button[role="tab"] {{
        border-radius: 8px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        color: var(--epi-text-muted) !important;
        background: transparent !important;
        border: none !important;
        padding: 7px 18px !important;
        transition: all 0.15s !important;
    }}
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
        background: var(--epi-surface) !important;
        color: var(--epi-text) !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 4px var(--epi-shadow) !important;
    }}
    [data-testid="stTabs"] button[role="tab"]:hover:not([aria-selected="true"]) {{
        color: var(--epi-text) !important;
    }}

    /* ══════════════════════════════════════════════════════════
       EXPANDER (Logs)
    ══════════════════════════════════════════════════════════ */
    [data-testid="stExpander"] {{
        border: 1.5px solid var(--epi-border) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        background: var(--epi-surface) !important;
    }}
    [data-testid="stExpander"] summary {{
        font-weight: 600 !important;
        font-size: 14px !important;
        color: var(--epi-text) !important;
        padding: 14px 18px !important;
    }}
    [data-testid="stExpander"] summary:hover {{
        background: var(--epi-surface-2) !important;
    }}
    [data-testid="stExpander"] > div > div {{
        padding: 0 18px 14px !important;
    }}

    /* ══════════════════════════════════════════════════════════
       CONTAINERS COM BORDA
    ══════════════════════════════════════════════════════════ */
    .block-container [data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 14px !important;
        border-color: var(--epi-border) !important;
        background: var(--epi-surface) !important;
    }}

    /* ── Alertas ─────────────────────────────────────────────── */
    [data-testid="stAlert"] {{
        border-radius: 10px !important;
        border-left-width: 4px !important;
        font-size: 13.5px !important;
    }}

    /* ── Inputs (área principal + login) ─────────────────────── */
    .stTextInput input, [data-testid="stNumberInput"] input {{
        border-radius: 8px !important;
        font-size: 13px !important;
        color: var(--epi-text) !important;
        background: var(--epi-surface) !important;
        border-color: var(--epi-border) !important;
    }}
    .stTextInput input:focus {{
        border-color: var(--epi-primary) !important;
        box-shadow: 0 0 0 2px var(--epi-primary-soft) !important;
    }}
    .stTextInput input::placeholder {{
        color: var(--epi-text-subtle) !important;
        opacity: 1 !important;
    }}

    /* ── Divisor / Spinner / Headings ────────────────────────── */
    hr {{
        border-color: var(--epi-border) !important;
        margin: 1.5rem 0 !important;
    }}
    [data-testid="stSpinner"] > div {{
        border-top-color: var(--epi-primary) !important;
    }}
    h2, h3 {{
        color: var(--epi-text) !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    auth.exigir_login(
        painel_nome="Controle de EPI",
        titulo_painel="Controle de EPI",
        subtitulo="EMPRESA_01 · Gestão de Equipamentos de Proteção Individual",
        icone="🦺"
    )

    username = st.session_state.get('username_logado', 'Sistema').title()
    perfil   = st.session_state.get('user_info', {}).get('perfil', 'QSMS')

    # ── Header principal ───────────────────────────────────────────────────────
    col_hdr, col_reload = st.columns([9, 2])
    with col_hdr:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#0F172A 0%,#1E3A5F 100%);'
            f'border-radius:16px;padding:20px 28px;margin-bottom:0.25rem;'
            f'border:1px solid var(--epi-border);box-shadow:0 4px 16px var(--epi-shadow);">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'flex-wrap:wrap;gap:12px;">'
            f'<div>'
            f'<div style="font-size:27px;font-weight:800;color:#FFFFFF;letter-spacing:-0.03em;line-height:1.15;">'
            f'🦺 Painel de Controle de EPI</div>'
            f'<div style="font-size:12.5px;color:#94A3B8;margin-top:4px;">'
            f'EMPRESA_01 · Gestão de Equipamentos de Proteção Individual</div>'
            f'</div>'
            f'<div style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.18);'
            f'border-radius:10px;padding:8px 16px;text-align:right;">'
            f'<div style="font-size:10px;color:#94A3B8;text-transform:uppercase;'
            f'letter-spacing:0.08em;font-weight:600;">Conectado</div>'
            f'<div style="font-size:14px;font-weight:600;color:#F1F5F9;margin-top:2px;">'
            f'{username}</div>'
            f'<div style="font-size:11px;color:#CBD5E1;">{perfil}</div>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )
    with col_reload:
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        st.markdown('<div id="reload-marker" style="display:none"></div>', unsafe_allow_html=True)
        if st.button("Recarregar Planilha", type="primary", key="btn_reload", use_container_width=True):
            for k in ('df', 'bd01', 'logs'):
                st.session_state.pop(k, None)
            st.rerun()

    # ── Carregamento de dados ──────────────────────────────────────────────────
    if 'df' not in st.session_state:
        if not os.path.exists(CAMINHO_ARQUIVO):
            st.error(f"Arquivo não encontrado: {CAMINHO_ARQUIVO}")
            return
        with st.spinner("Carregando planilha do OneDrive..."):
            try:
                st.session_state.update(_carregar_dados(CAMINHO_ARQUIVO))
            except Exception as e:
                st.error("Erro interno ao ler o arquivo.")
                return

    st.session_state.setdefault('logs', [])
    st.session_state.setdefault('bd01', [])

    if 'df' not in st.session_state:
        return

    df = st.session_state['df']
    colunas_regionais = [col for col in df.columns if str(col).upper().startswith("REG")]
    colunas_base = [col for col in df.columns if col not in colunas_regionais]
    coluna_descricao = "DESCRICAO" if "DESCRICAO" in colunas_base else (
        colunas_base[1] if len(colunas_base) > 1 else colunas_base[0]
    )
    reg_map = {col: extrair_regional_responsavel(col) for col in colunas_regionais}

    # ── Sidebar ────────────────────────────────────────────────────────────────

    # Card de perfil na sidebar
    st.sidebar.markdown(
        f'<div style="background:var(--epi-surface-2);border:1px solid var(--epi-border);'
        f'border-radius:10px;padding:12px 14px;margin-top:4px;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<div style="width:36px;height:36px;background:var(--epi-primary);border-radius:8px;'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-size:15px;font-weight:700;color:#FFFFFF;flex-shrink:0;">'
        f'{username[0]}</div>'
        f'<div>'
        f'<div style="font-size:13px;font-weight:600;color:var(--epi-text);">{username}</div>'
        f'<div style="font-size:11px;color:var(--epi-text-subtle);margin-top:1px;">{perfil}</div>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.rerun()
        return

    # ── Popups ─────────────────────────────────────────────────────────────────
    def popup_estoque(df_completo, epi_nome, colunas_reg):
        df_full   = st.session_state['df']
        linha_epi = df_full[df_full[coluna_descricao] == epi_nome]

        if linha_epi.empty:
            st.warning("Produto não encontrado no estoque.")
            return

        # ── Cabeçalho ──────────────────────────────────────────────
        cod_epi = ""
        if 'COD' in df_full.columns:
            v = str(linha_epi.iloc[0].get('COD', ''))
            if v.strip() not in ('', 'nan'):
                cod_epi = v

        cod_badge = (
            f'<span style="font-size:11px;font-weight:600;color:var(--epi-text-muted);'
            f'background:var(--epi-surface-2);border:1px solid var(--epi-border);'
            f'border-radius:5px;padding:2px 8px;margin-right:10px;">CÓD {cod_epi}</span>'
            if cod_epi else ""
        )
        st.markdown(
            f'<div style="margin-bottom:16px;padding-bottom:14px;'
            f'border-bottom:1px solid var(--epi-border);">'
            f'{cod_badge}'
            f'<span style="font-size:15px;font-weight:700;color:var(--epi-text);">'
            f'{epi_nome}</span></div>',
            unsafe_allow_html=True,
        )

        # ── Coleta e ordena por quantidade ─────────────────────────
        dados = sorted(
            [
                {
                    "regional": reg_map[col][0],
                    "qty": int(linha_epi.iloc[0][col]) if pd.notna(linha_epi.iloc[0][col]) else 0,
                }
                for col in colunas_reg
            ],
            key=lambda x: x["qty"],
            reverse=True,
        )
        total        = sum(d["qty"] for d in dados)
        com_estoque  = sum(1 for d in dados if d["qty"] > 0)

        # ── Mini KPIs ──────────────────────────────────────────────
        st.markdown(
            f'<div style="display:flex;gap:10px;margin-bottom:16px;">'
            f'<div style="flex:1;background:var(--epi-surface-2);border:1px solid var(--epi-border);'
            f'border-radius:10px;padding:10px 14px;text-align:center;">'
            f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;color:var(--epi-text-muted);margin-bottom:4px;">Total em Estoque</div>'
            f'<div style="font-size:26px;font-weight:800;color:var(--epi-text);'
            f'letter-spacing:-0.02em;">{total}</div>'
            f'</div>'
            f'<div style="flex:1;background:var(--epi-surface-2);border:1px solid var(--epi-border);'
            f'border-radius:10px;padding:10px 14px;text-align:center;">'
            f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;color:var(--epi-text-muted);margin-bottom:4px;">Regionais c/ Estoque</div>'
            f'<div style="font-size:26px;font-weight:800;color:var(--epi-text);letter-spacing:-0.02em;">'
            f'{com_estoque}'
            f'<span style="font-size:14px;font-weight:500;color:var(--epi-text-muted);">/{len(dados)}</span>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

        # ── Linhas por regional com barra de progresso ─────────────
        linhas = []
        for d in dados:
            pct     = (d["qty"] / total * 100) if total > 0 else 0
            cor_bar = "var(--epi-primary)" if d["qty"] > 0 else "var(--epi-border)"
            cor_qty = "var(--epi-text)"    if d["qty"] > 0 else "var(--epi-text-subtle)"
            linhas.append(
                f'<div style="display:flex;align-items:center;gap:12px;'
                f'padding:9px 12px;border-radius:8px;margin-bottom:5px;'
                f'background:var(--epi-surface-2);border:1px solid var(--epi-border);">'
                f'<span style="font-size:15px;line-height:1;">🏢</span>'
                f'<span style="flex:1;font-size:13px;font-weight:500;color:var(--epi-text);'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{d["regional"]}</span>'
                f'<div style="width:80px;flex-shrink:0;background:var(--epi-border);'
                f'border-radius:4px;height:6px;overflow:hidden;">'
                f'<div style="width:{pct:.1f}%;background:{cor_bar};height:100%;'
                f'border-radius:4px;"></div></div>'
                f'<span style="font-size:14px;font-weight:700;color:{cor_qty};'
                f'min-width:32px;text-align:right;">{d["qty"]}</span>'
                f'</div>'
            )
        st.markdown("".join(linhas), unsafe_allow_html=True)

    def popup_editar(epi_nome, qtd_atual, reg_selecionada):
        force = st.session_state.get('force_reload_epi', False)
        sessao_atual = f"{epi_nome}_{reg_selecionada}"
        if force or 'edit_session_epi' not in st.session_state or st.session_state['edit_session_epi'] != sessao_atual:
            st.session_state['force_reload_epi'] = False
            st.session_state['edit_session_epi'] = sessao_atual
            st.session_state['ca_ids'] = []
            st.session_state['next_ca_id'] = 0
            if 'estoque_cas' in st.session_state and sessao_atual in st.session_state['estoque_cas']:
                saved = st.session_state['estoque_cas'][sessao_atual]
                for idx, entry in enumerate(saved['cas']):
                    st.session_state['ca_ids'].append(idx)
                    st.session_state[f"qtd_ca_{idx}_{epi_nome}"] = entry['qtd']
                    st.session_state[f"num_ca_{idx}_{epi_nome}"] = entry['ca']
                st.session_state['next_ca_id'] = len(saved['cas'])

        nome_reg_limpo, _ = extrair_regional_responsavel(reg_selecionada)
        cod_epi = ""
        if 'COD' in st.session_state['df'].columns:
            linha = st.session_state['df'][st.session_state['df'][coluna_descricao] == epi_nome]
            if not linha.empty:
                cod_epi = str(linha.iloc[0]['COD'])

        if cod_epi and cod_epi.strip() not in ("", "nan"):
            st.markdown(f"**CÓD:** {cod_epi}<br>**EPI:** {epi_nome}<br>**Regional:** {nome_reg_limpo}", unsafe_allow_html=True)
        else:
            st.markdown(f"**EPI:** {epi_nome}<br>**Regional:** {nome_reg_limpo}", unsafe_allow_html=True)

        default_sem_ca = int(qtd_atual)
        if 'estoque_cas' in st.session_state and sessao_atual in st.session_state['estoque_cas']:
            default_sem_ca = st.session_state['estoque_cas'][sessao_atual]['sem_ca']

        # ── Sem CA ──────────────────────────────────────────────────
        nova_qtd_sem_ca = st.number_input(
            "📦 Sem CA",
            value=int(default_sem_ca),
            step=1,
            min_value=0,
            help="Unidades que não possuem certificado de aprovação informado",
        )

        # ── Lotes com CA ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**🔖 Com CA**")
        if not st.session_state['ca_ids']:
            st.caption("Nenhum lote com CA. Clique em **Adicionar lote** para registrar EPIs com certificação específica.")

        def remover_ca(id_remover):
            if id_remover in st.session_state['ca_ids']:
                st.session_state['ca_ids'].remove(id_remover)

        ca_entries = []
        for i in st.session_state['ca_ids']:
            c_ca, c_qtd, c_del = st.columns([5, 3, 1])
            with c_ca:
                st.session_state.setdefault(f"num_ca_{i}_{epi_nome}", "")
                num_ca = st.text_input("Nº CA", key=f"num_ca_{i}_{epi_nome}", placeholder="Ex: 39938")
            with c_qtd:
                st.session_state.setdefault(f"qtd_ca_{i}_{epi_nome}", 1)
                qtd_ca = st.number_input("Quantidade", step=1, min_value=1, key=f"qtd_ca_{i}_{epi_nome}")
            with c_del:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                st.button("✖", key=f"del_ca_{i}_{epi_nome}", on_click=remover_ca, args=(i,), help="Remover lote", use_container_width=True)
            ca_entries.append({'qtd': qtd_ca, 'ca': num_ca})

        if st.button("➕ Adicionar lote com CA", use_container_width=True):
            st.session_state['ca_ids'].append(st.session_state['next_ca_id'])
            st.session_state['next_ca_id'] += 1

        # ── Resumo antes de confirmar ─────────────────────────────────
        st.markdown("---")
        qtd_com_ca  = sum(e['qtd'] for e in ca_entries if str(e['ca']).strip())
        total_novo  = nova_qtd_sem_ca + qtd_com_ca
        delta_val   = total_novo - int(qtd_atual)
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Sem CA", nova_qtd_sem_ca)
        c_m2.metric("Com CA", qtd_com_ca)
        c_m3.metric("Total", total_novo, delta=f"{delta_val:+d}" if delta_val != 0 else None)

        msg_placeholder = st.empty()
        if st.button("💾 Confirmar Ajuste", type="primary", use_container_width=True):
            qtd_total_nova = nova_qtd_sem_ca + sum(
                e['qtd'] for e in ca_entries if str(e['ca']).strip() != ""
            )
            if (
                qtd_total_nova != qtd_atual
                or any(str(e['ca']).strip() != "" for e in ca_entries)
                or nova_qtd_sem_ca != qtd_atual
            ):
                idx = st.session_state['df'].index[
                    st.session_state['df'][coluna_descricao] == epi_nome
                ].tolist()[0]
                st.session_state['df'].at[idx, reg_selecionada] = qtd_total_nova

                st.session_state.setdefault('estoque_cas', {})
                novo_estoque = dict(st.session_state['estoque_cas'])
                novo_estoque[sessao_atual] = {
                    'sem_ca': nova_qtd_sem_ca,
                    'cas': [e for e in ca_entries if str(e['ca']).strip() != ""],
                }
                st.session_state['estoque_cas'] = novo_estoque

                ajuste = qtd_total_nova - qtd_atual
                sinal  = "+" if ajuste > 0 else ""
                agora  = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                detalhes = []
                if nova_qtd_sem_ca > 0:
                    detalhes.append(f"Sem CA: {nova_qtd_sem_ca}")
                for e in ca_entries:
                    if str(e['ca']).strip() != "":
                        detalhes.append(f"CA {str(e['ca']).strip()}: {e['qtd']}")
                detalhes_str = " | ".join(detalhes)

                novos_logs = list(st.session_state['logs'])
                novos_logs.append({
                    "Data/Hora": agora,
                    "Usuário": username,
                    "EPI": epi_nome,
                    "COD": cod_epi if cod_epi and str(cod_epi).strip() not in ("", "nan") else epi_nome,
                    "Regional": reg_selecionada,
                    "Qtd Anterior": qtd_atual,
                    "Ajuste": f"{sinal}{ajuste}",
                    "Nova Qtd": qtd_total_nova,
                    "Detalhes CA": detalhes_str,
                })
                st.session_state['logs'] = novos_logs

                novo_bd01 = list(st.session_state['bd01'])
                novo_bd01.append({
                    "Data/Hora": agora, "Regional": reg_selecionada,
                    "EPI": epi_nome, "CA": "Sem CA",
                    "Quantidade": nova_qtd_sem_ca, "Ação": "Ajuste/Edição",
                })
                for e in ca_entries:
                    if str(e['ca']).strip() != "":
                        novo_bd01.append({
                            "Data/Hora": agora, "Regional": reg_selecionada,
                            "EPI": epi_nome, "CA": str(e['ca']).strip(),
                            "Quantidade": e['qtd'], "Ação": "Ajuste/Edição",
                        })
                st.session_state['bd01'] = novo_bd01

                st.session_state['ca_ids'] = []
                st.session_state['next_ca_id'] = 0
                salvar_planilha()
                msg_placeholder.success("✅ Quantidade atualizada com sucesso!")
                time.sleep(1.2)
                st.rerun()

    if hasattr(st, "dialog"):
        popup_estoque = st.dialog("Estoque em Outras Regionais")(popup_estoque)
        popup_editar  = st.dialog("Editar Quantidade")(popup_editar)
    elif hasattr(st, "experimental_dialog"):
        popup_estoque = st.experimental_dialog("Estoque em Outras Regionais")(popup_estoque)
        popup_editar  = st.experimental_dialog("Editar Quantidade")(popup_editar)

    # ══════════════════════════════════════════════════════════════════════════
    # VISÃO DE REGIONAL SELECIONADA
    # ══════════════════════════════════════════════════════════════════════════
    regional_selecionada = st.session_state.get('regional_selecionada')

    if regional_selecionada and regional_selecionada in colunas_regionais:
        nome_regional_limpo, _ = reg_map[regional_selecionada]

        # Breadcrumb + voltar
        col_back, col_breadcrumb = st.columns([2, 8])
        with col_back:
            if st.button("← Voltar ao Resumo", key="btn_back"):
                st.session_state['regional_selecionada'] = None
                st.rerun()
        with col_breadcrumb:
            st.markdown(
                f'<div style="display:inline-flex;align-items:center;gap:8px;margin-top:6px;'
                f'font-size:13px;background:var(--epi-surface-2);border:1px solid var(--epi-border);'
                f'border-radius:8px;padding:6px 14px;">'
                f'<span style="color:var(--epi-text-muted);">🏠 Resumo Geral</span>'
                f'<span style="color:var(--epi-text-subtle);">›</span>'
                f'<span style="color:var(--epi-primary);font-weight:600;">🏢 {nome_regional_limpo}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        # KPIs da regional
        qtds_reg = pd.to_numeric(df[regional_selecionada], errors='coerce').fillna(0)
        total_reg      = int(qtds_reg.sum())
        com_estoque    = int((qtds_reg > 0).sum())
        sem_estoque    = len(df) - com_estoque
        ca_venc_reg    = 0
        if 'VALID CA' in df.columns:
            datas = pd.to_datetime(df['VALID CA'], errors='coerce')
            ca_venc_reg = int((datas.dt.date < datetime.now().date()).sum())

        _render_kpi_row(
            _kpi("Total da Regional",  f"{total_reg:,}",    "📦", "#2563EB", "unidades em estoque"),
            _kpi("Tipos c/ Estoque",   f"{com_estoque}",    "✅", "#10B981", f"de {len(df)} cadastrados"),
            _kpi("Tipos s/ Estoque",   f"{sem_estoque}",    "⚪", "#64748B", "estoque zerado"),
            _kpi("CAs Vencidos",       f"{ca_venc_reg}",    "🔴",
                 "#EF4444" if ca_venc_reg > 0 else "#64748B", "requerem atenção"),
        )

        # Prepara DataFrame ordenado
        perfil_usuario   = perfil
        pode_editar      = perfil_usuario == "QSMS" or perfil_usuario.upper() == nome_regional_limpo.upper()

        df_exibicao = df[colunas_base + [regional_selecionada]].copy()
        df_exibicao[regional_selecionada] = (
            pd.to_numeric(df_exibicao[regional_selecionada], errors='coerce').fillna(0).astype(int)
        )
        df_ordenado = (
            df_exibicao
            .sort_values(by=regional_selecionada, ascending=False)
            .reset_index(drop=True)
            .rename(columns={regional_selecionada: "Quantidade"})
        )
        colunas_finais = colunas_base + ["Quantidade"]
        df_ordenado    = df_ordenado[colunas_finais]

        col_titulo, col_botoes_acao = st.columns([1, 1.2])
        with col_titulo:
            st.subheader(f"Estoque Atual · {nome_regional_limpo}")
        botoes_acao_placeholder = col_botoes_acao.empty()

        if not pode_editar:
            st.info(f"👁️ Visualização apenas — sem permissão de edição para {nome_regional_limpo}.")

        col_config = _build_col_config(colunas_base)

        try:
            event = st.dataframe(
                df_ordenado.style.apply(_highlight_table, axis=None),
                column_config=col_config,
                hide_index=True,
                use_container_width=True,
                key=f"tabela_{regional_selecionada}",
                on_select="rerun",
                selection_mode="single-row",
            )
            if 'VALID CA' in df_ordenado.columns:
                _ca_legend()

            selected_rows = event.selection.rows
            if selected_rows:
                sel_idx       = selected_rows[0]
                epi_selecionado = df_ordenado.iloc[sel_idx][coluna_descricao]
                qtd_atual       = df_ordenado.iloc[sel_idx]["Quantidade"]
                with botoes_acao_placeholder.container():
                    st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
                    cb1, cb2 = st.columns(2)
                    with cb1:
                        if pode_editar:
                            if st.button("✏️ Editar Quantidade", use_container_width=True):
                                st.session_state['force_reload_epi'] = True
                                if hasattr(st, "dialog") or hasattr(st, "experimental_dialog"):
                                    popup_editar(epi_selecionado, qtd_atual, regional_selecionada)
                                else:
                                    st.warning("Atualize o Streamlit (>=1.34) para utilizar Popups.")
                    with cb2:
                        if st.button("🔍 Consultar Unidades", use_container_width=True):
                            if hasattr(st, "dialog") or hasattr(st, "experimental_dialog"):
                                popup_estoque(df, epi_selecionado, colunas_regionais)
                            else:
                                st.warning("Atualize o Streamlit (>=1.34) para utilizar Popups.")
            else:
                with botoes_acao_placeholder.container():
                    st.markdown(
                        '<div style="text-align:right;margin-top:28px;color:#94A3B8;font-size:13px;">'
                        '💡 Selecione uma linha para exibir ações.</div>',
                        unsafe_allow_html=True,
                    )

        except TypeError:
            if pode_editar:
                df_ordenado["✏️ Editar"] = False
                colunas_finais.append("✏️ Editar")
                col_config["✏️ Editar"] = st.column_config.CheckboxColumn(
                    help="Marque para alterar quantidade e CA", default=False, width="small"
                )
            df_ordenado["🔍 Verificar Unidades"] = False
            colunas_finais.append("🔍 Verificar Unidades")
            col_config["🔍 Verificar Unidades"] = st.column_config.CheckboxColumn(
                help="Estoque nas outras regionais", default=False, width="small"
            )
            df_ordenado = df_ordenado[colunas_finais]
            edited_df = st.data_editor(
                df_ordenado.style.apply(_highlight_table, axis=None),
                column_config=col_config,
                disabled=colunas_base + ["Quantidade"],
                hide_index=True, use_container_width=True,
                key=f"editor_fallback_{regional_selecionada}",
            )
            if 'VALID CA' in df_ordenado.columns:
                _ca_legend()

            if pode_editar:
                editar_sel = edited_df[edited_df["✏️ Editar"] == True]
                if not editar_sel.empty:
                    epi_selecionado = editar_sel.iloc[0][coluna_descricao]
                    qtd_atual       = editar_sel.iloc[0]["Quantidade"]
                    if hasattr(st, "dialog") or hasattr(st, "experimental_dialog"):
                        popup_editar(epi_selecionado, qtd_atual, regional_selecionada)
                    else:
                        st.warning("Atualize o Streamlit (>=1.34) para utilizar Popups.")

            verificar_sel = edited_df[edited_df["🔍 Verificar Unidades"] == True]
            if not verificar_sel.empty:
                epi_sel = verificar_sel.iloc[0][coluna_descricao]
                if hasattr(st, "dialog") or hasattr(st, "experimental_dialog"):
                    popup_estoque(df, epi_sel, colunas_regionais)
                else:
                    st.warning("Atualize o Streamlit (>=1.34) para utilizar Popups.")

    else:
        # ════════════════════════════════════════════════════════════════════
        # RESUMO GERAL
        # ════════════════════════════════════════════════════════════════════

        # KPIs globais
        hoje_kpi = datetime.now().date()
        em_30_kpi = hoje_kpi + timedelta(days=30)
        total_produtos = len(df)
        total_estoque  = int(
            df[colunas_regionais].apply(pd.to_numeric, errors='coerce').fillna(0).sum().sum()
        )
        ca_vencidos = 0
        ca_proximos = 0
        if 'VALID CA' in df.columns:
            datas = pd.to_datetime(df['VALID CA'], errors='coerce')
            ca_vencidos = int((datas.dt.date < hoje_kpi).sum())
            ca_proximos = int(
                ((datas.dt.date >= hoje_kpi) & (datas.dt.date <= em_30_kpi)).sum()
            )

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        _render_kpi_row(
            _kpi("EPI's Ativos",             f"{total_produtos:,}", "📋", "#2563EB", "produtos cadastrados"),
            _kpi("Total de EPI em Estoque", f"{total_estoque:,}".replace(",", "."),  "📦", "#10B981", "unidades somadas"),
            _kpi("CA's Vencidos",           f"{ca_vencidos}",      "🔴",
                 "#EF4444" if ca_vencidos > 0 else "#64748B", "requerem atenção"),
            _kpi("CA's Vencendo em 30 Dias", f"{ca_proximos}",     "⚠️",
                 "#F59E0B" if ca_proximos > 0 else "#64748B", "verificar brevemente"),
        )

        # Cards de seleção das regionais
        st.markdown(
            '<div style="font-size:13px;font-weight:600;color:var(--epi-text-muted);'
            'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:10px;">'
            '🏢 &nbsp;Selecione a Regional</div>',
            unsafe_allow_html=True,
        )

        # Pre-calcula totais por regional para exibir nos cards
        totais_reg = {
            col: int(pd.to_numeric(df[col], errors='coerce').fillna(0).sum())
            for col in colunas_regionais
        }

        num_cols = max(len(colunas_regionais), 1)
        cols_reg = st.columns(num_cols)
        for idx, col in enumerate(colunas_regionais):
            regional, responsavel = reg_map[col]
            total_c = totais_reg[col]
            with cols_reg[idx % num_cols]:
                st.markdown('<div class="reg-icon-marker"></div>', unsafe_allow_html=True)
                btn_text = f"{regional}\n{responsavel}\n{total_c:,} itens em estoque"
                if st.button(btn_text, key=f"btn_{col}", type="primary", use_container_width=True):
                    st.session_state['regional_selecionada'] = col
                    st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Prepara resumo
        df_resumo = df[colunas_base + colunas_regionais].copy()
        for col in colunas_regionais:
            df_resumo[col] = pd.to_numeric(df_resumo[col], errors='coerce').fillna(0).astype(int)

        # Gráfico
        df_totais = pd.DataFrame([
            {"Regional": reg_map[col][0], "Total": totais_reg[col]}
            for col in colunas_regionais
        ])
        hover = alt.selection_point(on='mouseover', empty=False, fields=['Regional'])
        grafico = (
            alt.Chart(df_totais)
            .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(
                x=alt.X('Regional:N', sort='-y',
                         axis=alt.Axis(labelAngle=0, title=None, labelFontSize=13, labelPadding=10)),
                y=alt.Y('Total:Q', title=None,
                         axis=alt.Axis(grid=True, gridOpacity=0.1, labels=False, ticks=False, domain=False)),
                color=alt.Color('Total:Q', scale=alt.Scale(range=['#93C5FD', '#1D4ED8']), legend=None),
                opacity=alt.condition(hover, alt.value(1.0), alt.value(0.62)),
                tooltip=[alt.Tooltip('Regional:N'), alt.Tooltip('Total:Q', title='Qtd. Total de EPIs')],
            )
            .add_params(hover)
            .properties(height=300)
        )
        textos = grafico.mark_text(
            align='center', baseline='bottom', dy=-8, fontSize=14, fontWeight=700
        ).encode(text='Total:Q')

        # Ordena e renomeia
        df_resumo['Total Geral'] = df_resumo[colunas_regionais].sum(axis=1)
        df_resumo = df_resumo.sort_values(by='Total Geral', ascending=False).reset_index(drop=True)
        df_resumo = df_resumo.rename(columns={col: reg_map[col][0] for col in colunas_regionais})

        col_config = _build_col_config(colunas_base)

        tab1, tab2 = st.tabs(["Visão Geral", "Controle de CA"])

        with tab1:
            with st.container(border=True):
                st.altair_chart(grafico + textos, use_container_width=True)

            # ── Barra de filtros inline ───────────────────────────────────────
            with st.container(border=True):
                cf1, cf2 = st.columns(2)
                with cf1:
                    busca_geral = st.text_input(
                        "🔍 Pesquisar por Cód. ou Descrição",
                        placeholder="Ex: LUVA ou 0029",
                        key="tab1_busca_geral",
                    )
                with cf2:
                    busca_desc = st.text_input(
                        "🔍 Pesquisar por Descrição",
                        placeholder="Ex: CANO CURTO",
                        key="tab1_busca_desc",
                    )

            # ── Aplica filtros sobre df_resumo ────────────────────────────────
            df_filtrado = df_resumo.copy()
            q1 = busca_geral.strip().upper()
            if q1:
                mask1 = pd.Series(False, index=df_filtrado.index)
                if 'COD' in df_filtrado.columns:
                    mask1 |= df_filtrado['COD'].astype(str).str.upper().str.contains(q1, na=False)
                if coluna_descricao in df_filtrado.columns:
                    mask1 |= df_filtrado[coluna_descricao].astype(str).str.upper().str.contains(q1, na=False)
                df_filtrado = df_filtrado[mask1]
            q2 = busca_desc.strip().upper()
            if q2 and coluna_descricao in df_filtrado.columns:
                df_filtrado = df_filtrado[
                    df_filtrado[coluna_descricao].astype(str).str.upper().str.contains(q2, na=False)
                ]

            st.dataframe(
                df_filtrado.style.apply(_highlight_table, axis=None),
                hide_index=True, use_container_width=True, height=500,
                column_config=col_config,
            )
            if 'VALID CA' in df_filtrado.columns:
                _ca_legend()

        with tab2:
            st.write("##### Produtos com CA Informado")
            if "VALID CA" in df_resumo.columns:
                cb1, cb2 = st.columns(2)
                with cb1:
                    so_quantidade = st.checkbox(
                        "Somente com Quantidade",
                        value=False,
                        key="tab2_so_quantidade",
                        help="Exibe apenas produtos com CA que possuem quantidade em estoque",
                    )
                with cb2:
                    so_vencidos = st.checkbox(
                        "Somente os Vencidos",
                        value=False,
                        key="tab2_so_vencidos",
                        help="Exibe apenas produtos com CA já vencido",
                    )

                df_ca_tab = df_resumo[df_resumo["VALID CA"].notna()].copy()
                if so_quantidade:
                    df_ca_tab = df_ca_tab[df_ca_tab["Total Geral"] > 0]
                if so_vencidos:
                    hoje_ts = pd.Timestamp.today().normalize()
                    datas = pd.to_datetime(df_ca_tab["VALID CA"], errors='coerce')
                    df_ca_tab = df_ca_tab[datas.notna() & (datas < hoje_ts)]

                if not df_ca_tab.empty:
                    st.dataframe(
                        df_ca_tab.style.apply(_highlight_table, axis=None),
                        hide_index=True, use_container_width=True, height=500,
                        column_config=col_config,
                    )
                    _ca_legend()
                else:
                    st.markdown(
                        '<div style="text-align:center;padding:3rem;color:#94A3B8;">'
                        '✅ Nenhum produto encontrado com os filtros aplicados.</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.warning("Coluna 'VALID CA' não encontrada.")

    # ── Logs ───────────────────────────────────────────────────────────────────
    st.divider()
    with st.expander("📋 Logs de Alteração", expanded=False):
        if not st.session_state.get('logs'):
            st.markdown(
                '<div style="color:#94A3B8;font-size:13px;padding:8px 0;">'
                'Nenhuma alteração registrada.</div>',
                unsafe_allow_html=True,
            )
        else:
            perfil_usuario = perfil
            log_data = []
            for real_idx, log in enumerate(st.session_state['logs']):
                if regional_selecionada and log['Regional'] != regional_selecionada:
                    continue
                nome_reg_log, _ = extrair_regional_responsavel(log['Regional'])
                pode_edit_log   = perfil_usuario == "QSMS" or perfil_usuario.upper() == nome_reg_log.upper()
                log_data.append({
                    "_real_idx": real_idx,
                    "ID": real_idx + 1,
                    "Data/Hora": log.get('Data/Hora', ''),
                    "Usuário": log.get('Usuário', 'Desconhecido'),
                    "Regional": nome_reg_log,
                    "Código": log.get('COD', log['EPI']),
                    "Produto": log['EPI'],
                    "Alteração": (
                        f"Ajuste {log['Ajuste']} "
                        f"(De {log['Qtd Anterior']} → {log['Nova Qtd']})"
                        + (f" · {log['Detalhes CA']}" if log.get('Detalhes CA') else "")
                    ),
                    "↩️ Desfazer": False,
                    "_pode_editar": pode_edit_log,
                })

            if not log_data:
                st.markdown(
                    '<div style="color:#94A3B8;font-size:13px;padding:8px 0;">'
                    'Nenhuma alteração registrada para esta regional.</div>',
                    unsafe_allow_html=True,
                )
            else:
                log_data.reverse()
                df_logs_exib = pd.DataFrame(log_data)
                col_config_logs = {
                    "_real_idx": None,
                    "_pode_editar": None,
                    "ID": st.column_config.NumberColumn(width="small"),
                    "Data/Hora": st.column_config.TextColumn(width="medium"),
                    "Usuário": st.column_config.TextColumn(width="small"),
                    "Regional": st.column_config.TextColumn(width="small"),
                    "Código": st.column_config.TextColumn(width="small"),
                    "Produto": st.column_config.TextColumn(width="large"),
                    "Alteração": st.column_config.TextColumn(width="medium"),
                    "↩️ Desfazer": st.column_config.CheckboxColumn(
                        width="small", help="Marque para desfazer esta alteração"
                    ),
                }
                st.session_state.setdefault('editor_logs_key', 0)
                edited_logs = st.data_editor(
                    df_logs_exib,
                    column_config=col_config_logs,
                    disabled=["ID", "Data/Hora", "Usuário", "Regional", "Código", "Produto", "Alteração"],
                    hide_index=True, use_container_width=True,
                    key=f"editor_logs_{regional_selecionada}_{st.session_state['editor_logs_key']}",
                )

                desfazer_sel = edited_logs[edited_logs["↩️ Desfazer"] == True]
                if not desfazer_sel.empty:
                    real_idx_d    = desfazer_sel.iloc[0]["_real_idx"]
                    pode_edit_d   = desfazer_sel.iloc[0]["_pode_editar"]
                    txt_alt       = desfazer_sel.iloc[0]["Alteração"]

                    if pode_edit_d:
                        log_t        = st.session_state['logs'][real_idx_d]
                        epi_d        = log_t['EPI']
                        reg_d        = log_t['Regional']
                        qtd_ant_d    = log_t['Qtd Anterior']
                        st.session_state['editor_logs_key'] += 1

                        def popup_desfazer_func(idx, e, r, q_ant, txt):
                            st.markdown("Você está prestes a **desfazer** a seguinte alteração:")
                            st.info(f"**Produto:** {e}\n\n**Alteração:** {txt}")
                            st.warning(f"⚠️ Isso reverterá a quantidade para **{q_ant}**.")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("❌ Cancelar", use_container_width=True):
                                    st.rerun()
                            with c2:
                                if st.button("✅ Confirmar", use_container_width=True):
                                    idx_df = st.session_state['df'].index[
                                        st.session_state['df'][coluna_descricao] == e
                                    ].tolist()[0]
                                    st.session_state['df'].at[idx_df, r] = q_ant
                                    novos_logs = list(st.session_state['logs'])
                                    novos_logs.pop(idx)
                                    st.session_state['logs'] = novos_logs
                                    salvar_planilha()
                                    ph = st.empty()
                                    ph.success("✅ Ação desfeita com sucesso!")
                                    time.sleep(1.2)
                                    st.rerun()

                        if hasattr(st, "dialog"):
                            popup_desfazer = st.dialog("Confirmar Desfazer")(popup_desfazer_func)
                        elif hasattr(st, "experimental_dialog"):
                            popup_desfazer = st.experimental_dialog("Confirmar Desfazer")(popup_desfazer_func)
                        else:
                            idx_df = st.session_state['df'].index[
                                st.session_state['df'][coluna_descricao] == epi_d
                            ].tolist()[0]
                            st.session_state['df'].at[idx_df, reg_d] = qtd_ant_d
                            novos_logs = list(st.session_state['logs'])
                            novos_logs.pop(real_idx_d)
                            st.session_state['logs'] = novos_logs
                            salvar_planilha()
                            st.rerun()

                        if hasattr(st, "dialog") or hasattr(st, "experimental_dialog"):
                            popup_desfazer(real_idx_d, epi_d, reg_d, qtd_ant_d, txt_alt)
                    else:
                        st.session_state['editor_logs_key'] += 1
                        st.error("Você não tem permissão para desfazer esta alteração.")
                        time.sleep(1.5)
                        st.rerun()


main()
