import streamlit as st


import os
import json
import base64
from datetime import datetime

# Engine de leitura: python-calamine (Rust, streaming) é ordens de magnitude mais
# rápido que o pandas/openpyxl. Se não estiver instalado, cai para o openpyxl.
try:
    from python_calamine import CalamineWorkbook
except Exception:
    CalamineWorkbook = None

# Caminhos
diretorio_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMG_DIR = os.path.join(diretorio_base, "assets")
EXCEL_DIR = "/app/data"
CAMINHO_ONEDRIVE = "Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/Controle Cadastros.xlsx"

# Função pra ler as imagens locais
def carregar_imagem_base64(nome_arquivo):
    caminho = os.path.join(IMG_DIR, nome_arquivo)
    if os.path.exists(caminho):
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# Função auxiliar para pegar timestamp do arquivo de forma barata (para invalidar o cache)
def obter_timestamp(caminho):
    try: return os.path.getmtime(caminho)
    except: return 0

# Abre a planilha uma única vez e devolve (nomes das abas, leitor de linhas, fechar).
# O leitor entrega as linhas como tuplas de valores, sem materializar DataFrames.
def _abrir(caminho):
    if CalamineWorkbook is not None:
        wb = CalamineWorkbook.from_path(caminho)
        return wb.sheet_names, lambda nome: wb.get_sheet_by_name(nome).to_python(skip_empty_area=True), lambda: None
    from openpyxl import load_workbook
    wb = load_workbook(caminho, read_only=True, data_only=True)
    return list(wb.sheetnames), lambda nome: wb[nome].iter_rows(values_only=True), wb.close

# Conta linhas não vazias (ignora o cabeçalho e linhas só com espaços/None)
def _contar_nao_vazias(linhas):
    total = 0
    for i, linha in enumerate(linhas):
        if i == 0:  # cabeçalho
            continue
        if any(v is not None and str(v).strip() != "" for v in linha):
            total += 1
    return total

# Resolve o nome de uma aba aceitando variações de caso/espaço ou texto contido
def _achar_aba(nome, nomes_abas):
    if isinstance(nome, int):
        return nomes_abas[nome] if nome < len(nomes_abas) else None
    if nome in nomes_abas:
        return nome
    alvo = nome.strip().upper()
    for s in nomes_abas:
        if s.strip().upper() == alvo:
            return s
    for s in nomes_abas:
        if alvo in s.strip().upper():
            return s
    return None

# Resolve uma aba (str/int) ou um conjunto de abas (tupla/lista) para somar
def _resolver_aba(aba, nomes_abas):
    if isinstance(aba, (list, tuple)):
        achadas = [r for r in (_achar_aba(n, nomes_abas) for n in aba) if r is not None]
        return achadas if achadas else list(aba)
    r = _achar_aba(aba, nomes_abas)
    if r is not None:
        return r
    return nomes_abas[0] if nomes_abas else aba

# Data de atualização: mtime do arquivo, sobreposto pelo atualizacoes.json quando houver
def _data_atualizacao(caminho, nome_arquivo, abas_alvo):
    timestamp = os.path.getmtime(caminho)
    arquivo_json = os.path.join(os.path.dirname(caminho), 'atualizacoes.json')
    if os.path.exists(arquivo_json):
        try:
            with open(arquivo_json, 'r', encoding='utf-8') as f:
                atualizacoes = json.load(f)
            registro = atualizacoes.get(nome_arquivo, {})
            ts_list = [registro[ab] for ab in abas_alvo if ab in registro]
            if ts_list:
                timestamp = max(ts_list)
        except Exception:
            pass
    return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')

# Função pra ler a planilha COM CACHE
@st.cache_data(show_spinner=False, ttl=14400)
def analisar_planilha(nome_arquivo, aba=0, timestamp=0):
    caminho = os.path.join(EXCEL_DIR, nome_arquivo)
    if not os.path.exists(caminho):
        return "~0", "Arquivo não encontrado"
    try:
        nomes_abas, ler_aba, fechar = _abrir(caminho)
        try:
            aba_resolvida = _resolver_aba(aba, nomes_abas)
            if isinstance(aba_resolvida, list):
                total_linhas = sum(_contar_nao_vazias(ler_aba(n)) for n in aba_resolvida)
                abas_alvo = aba_resolvida
            else:
                total_linhas = _contar_nao_vazias(ler_aba(aba_resolvida))
                abas_alvo = [aba_resolvida]
        finally:
            fechar()
        return f"~{total_linhas}", _data_atualizacao(caminho, nome_arquivo, abas_alvo)
    except Exception as e:
        return "~0", f"Erro: {str(e)[:50]}"


import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from onedrive_downloader import download_excel_from_onedrive, get_onedrive_file_last_modified
import pandas as pd
from datetime import datetime, timedelta

# Cache do OneDrive removido daqui, pois a Graph API (onedrive_downloader) já possui cache TTL
def obter_fornecedores():
    try:
        arquivo_excel = download_excel_from_onedrive(CAMINHO_ONEDRIVE)
        df = pd.read_excel(arquivo_excel, sheet_name="Alt_Att Fornec", header=1)
        total = df.dropna(how='all').shape[0]
        # Data formatada de agora já que estamos consumindo em cache
        data_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        try:
            mod_time = get_onedrive_file_last_modified(CAMINHO_ONEDRIVE)
            if mod_time:
                mod_time = mod_time.replace("Z", "+00:00")
                dt = datetime.fromisoformat(mod_time)
                dt = dt - timedelta(hours=3)
                data_str = dt.strftime('%d/%m/%Y %H:%M')
        except Exception:
            pass
            
        return f"~{total}", data_str
    except Exception:
        return "~0", "Erro no SharePoint"

# Processando tudo
img_portal = carregar_imagem_base64("Portal dados logo.png")
img_aprovadores = carregar_imagem_base64("Aprovadores logo.png")
img_projeto_alfa = carregar_imagem_base64("Projeto_Alfa logo.png") 
img_ccusto = carregar_imagem_base64("C.Custo logo.png") 
img_fornecedores = carregar_imagem_base64("Fornecedores logo.png")  
img_produtos = carregar_imagem_base64("Produtos.png")
if not img_produtos:
    img_produtos = img_fornecedores

# Obtemos os timestamps na hora pra decidir se o cache deve atualizar
ts_aprov = obter_timestamp(os.path.join(EXCEL_DIR, "Aprovadores.xlsx"))
ts_ronc = obter_timestamp(os.path.join(EXCEL_DIR, "Projeto_Alfa.xlsx"))
ts_produtos = obter_timestamp(os.path.join(EXCEL_DIR, "Produtos.xlsx"))

# Notar o uso de TUPLA em ("Plan1", "Form") ao invés de lista, pois Cache do Streamlit exige argumentos imutáveis
linhas_aprov, data_aprov = analisar_planilha("Aprovadores.xlsx", aba=("Plan1", "Form"), timestamp=ts_aprov)
linhas_ronc, data_ronc = analisar_planilha("Projeto_Alfa.xlsx", aba=0, timestamp=ts_ronc)
linhas_ccusto, data_ccusto = analisar_planilha("Aprovadores.xlsx", aba="Plan2", timestamp=ts_aprov)
linhas_fornecedores, data_fornecedores = obter_fornecedores()
linhas_produtos, data_produtos = analisar_planilha("Produtos.xlsx", aba=("Plan1", "Plan 3", "Plan3"), timestamp=ts_produtos)

def obter_ultima_atualizacao_bot():
    import re
    log_path = "/app/data/log_execucao.txt"
    if not os.path.exists(log_path):
        return None
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for linha in reversed(f.readlines()):
                if "FINALIZANDO EXECU" in linha or "Bot finalizado sem erros" in linha:
                    match = re.search(r'\[(\d{2}/\d{2}/\d{4} \d{2}:\d{2})', linha)
                    if match:
                        return match.group(1)
    except:
        pass
    return None

ultima_data_bot = obter_ultima_atualizacao_bot()

# Força os módulos processados pelo Bot a mostrarem a última data/hora do log de sucesso
if ultima_data_bot:
    data_aprov = ultima_data_bot
    data_ronc = ultima_data_bot
    data_ccusto = ultima_data_bot
    data_produtos = ultima_data_bot

# Lógica de Cor dos números
def cor_alerta(valor):
    return "#FF3333" if str(valor).strip() in ["~0", "0"] else "var(--text-color)"

cor_aprov = cor_alerta(linhas_aprov)
cor_ronc = cor_alerta(linhas_ronc)
cor_ccusto = cor_alerta(linhas_ccusto)
cor_fornec = cor_alerta(linhas_fornecedores)
cor_produtos = cor_alerta(linhas_produtos)

# CSS de hover dos cards via classe e redução de espaçamento do painel
st.markdown("""
<style>
/* Remove o espaço em branco gigante do topo do Streamlit */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 1rem !important;
}
.portal-card { transition: transform 0.22s ease, box-shadow 0.22s ease !important; }
.portal-card:hover { transform: translateY(-3px) !important; box-shadow: 0 12px 32px rgba(0,0,0,0.15) !important; }
</style>
""", unsafe_allow_html=True)

# Cabeçalho
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
try:
    import ui_utils
    ui_utils.render_standard_panel(
        title="Portal de Gestão de Cadastros",
        subtitle="",
        icon_name="Portal dados logo.png",
        center_title=True
    )
except ImportError:
    pass

# --- LÓGICA DO STATUS GERAL ---
# Se qualquer um dos pipelines retornar ~0, a gente avisa que deu merda
pipelines_zerados = any(str(val).strip() in ["~0", "0"] for val in [linhas_aprov, linhas_ronc, linhas_ccusto, linhas_fornecedores, linhas_produtos])

if pipelines_zerados:
    status_texto = "Um ou mais módulos estão inoperantes"
    status_cor = "#FF3333"
    status_msg_secundaria = "Verifique falhas na leitura ou bases vazias"
else:
    status_texto = "Operacional"
    status_cor = "#32CD32"
    status_msg_secundaria = "Todos os pipelines de dados atualizados"

status_bg = "rgba(255,68,68,0.10)" if pipelines_zerados else "rgba(46,204,113,0.10)"
status_border = "rgba(255,68,68,0.28)" if pipelines_zerados else "rgba(46,204,113,0.28)"
status_icon = "⚠" if pipelines_zerados else "✓"

st.markdown(f"""
<div style="
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 20px;
    background: {status_bg};
    border: 1px solid {status_border};
    border-radius: 10px;
    margin-bottom: 24px;
">
    <span style="
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px; height: 28px;
        background: {status_cor};
        border-radius: 50%;
        color: white;
        font-weight: 900;
        font-size: 0.82em;
        flex-shrink: 0;
    ">{status_icon}</span>
    <div>
        <span style="font-weight: 700; color: {status_cor}; font-size: 0.93em;">Status: {status_texto}</span>
        <span style="color: #888; font-size: 0.87em; margin-left: 10px;">— {status_msg_secundaria}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Função para renderizar um card de forma padronizada
def render_card(link, cor_borda, img_b64, titulo, subtitulo, titulo_metrica, valor_metrica, cor_metrica, data_att):
    is_error = str(valor_metrica).strip() in ["~0", "0"]
    is_updated = (ultima_data_bot is not None) and (ultima_data_bot[:10] in data_att)

    if is_error:
        label_style = 'color: #FF3333; font-weight: 800;'
        data_att_styled = f'<span style="{label_style}">{data_att}</span>'
    elif is_updated:
        label_style = 'color: #2ECC71; font-weight: 800;'
        data_att_styled = f'<span style="{label_style}">{data_att}</span>'
    else:
        label_style = ''
        data_att_styled = data_att

    html_card = f"""
    <a href="{link}" target="_self" class="glass-card" style="border-left: 4px solid {cor_borda}; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center;">
                <div style="background: var(--background-color); border: 1px solid rgba(128,128,128,0.15); border-radius: 12px; padding: 10px; margin-right: 20px; display: flex; align-items: center; justify-content: center;">
                    <img src="data:image/png;base64,{img_b64}" style="width: 50px; height: 50px; object-fit: contain;">
                </div>
                <div>
                    <h3>{titulo}</h3>
                    <p>{subtitulo}</p>
                </div>
            </div>
            <div style="text-align: right; min-width: 190px;">
                <p class="metric-title">{titulo_metrica}</p>
                <p class="metric-value" style="color: {cor_metrica};">{valor_metrica}</p>
                <p class="metric-date"><span style="{label_style}">Atualizado:</span> {data_att_styled}</p>
            </div>
        </div>
    </a>
    """
    st.markdown(html_card, unsafe_allow_html=True)

# Injetar o CSS global
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
try:
    import ui_utils
    ui_utils.load_css()
except ImportError:
    pass

# Cartão: Aprovadores
render_card(
    link="/grupo_de_aprovadores",
    cor_borda="var(--color-aprovadores)",
    img_b64=img_aprovadores,
    titulo="Módulo de Aprovadores",
    subtitulo="Gestão e Validação de Regras de (Protheus & Fluig)",
    titulo_metrica="Total de Regras",
    valor_metrica=linhas_aprov,
    cor_metrica=cor_aprov,
    data_att=data_aprov
)

# Cartão: Projeto_Alfa
render_card(
    link="/empresax_x_projeto_alfa",
    cor_borda="var(--color-empresax)",
    img_b64=img_projeto_alfa,
    titulo="Módulo EMPRESA_01 x Projeto_Alfa",
    subtitulo="Análise e Consulta de Produtos e Fornecedores",
    titulo_metrica="Total de Registros",
    valor_metrica=linhas_ronc,
    cor_metrica=cor_ronc,
    data_att=data_ronc
)

# Cartão: Centro de Custo
render_card(
    link="/centro_custo",
    cor_borda="var(--color-ccusto)",
    img_b64=img_ccusto,
    titulo="Módulo Centro de Custo",
    subtitulo="Relação de Centro de Custo",
    titulo_metrica="Total de Registros",
    valor_metrica=linhas_ccusto,
    cor_metrica=cor_ccusto,
    data_att=data_ccusto
)

# Cartão: Fornecedores
render_card(
    link="/atualizacao_fornecedor",
    cor_borda="var(--color-fornecedores)",
    img_b64=img_fornecedores,
    titulo="Módulo Atualização de Fornecedores",
    subtitulo="Relação de Fornecedores Atualizados",
    titulo_metrica="Total de Registros",
    valor_metrica=linhas_fornecedores,
    cor_metrica=cor_fornec,
    data_att=data_fornecedores
)

# Cartão: Produtos/Fornecedores
render_card(
    link="/Produtos",
    cor_borda="var(--color-produtos)",
    img_b64=img_produtos,
    titulo="Módulo Produtos/Fornecedores",
    subtitulo="Consulta de Produtos e Fornecedores",
    titulo_metrica="Total de Registros",
    valor_metrica=linhas_produtos,
    cor_metrica=cor_produtos,
    data_att=data_produtos
)
