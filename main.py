import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv(override=True)

favicon_path = os.path.join(os.path.dirname(__file__), "assets", "favicon.ico")

st.set_page_config(
    page_title="Painel de Gestão de Cadastros",
    page_icon=favicon_path if os.path.exists(favicon_path) else "📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Customização do Menu Lateral Nativo (Sidebar) para um Visual Premium Corporativo
st.markdown("""
<style>
/* ── Fundo escuro Premium forçado em todas as camadas da sidebar ── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div:first-child,
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #931B0B 0%, #CC0000 50%, #931B0B 100%) !important;
    background-color: #FFFFFF !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
    box-shadow: 4px 0 15px rgba(0,0,0,0.25) !important;
}

/* ── Força Bruta: Todo texto dentro da sidebar com cor base prateada ── */
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] div:not([data-testid="stSidebarNav"] div), 
[data-testid="stSidebar"] label {
    color: #F3F5F9 !important;
}

/* ── Força Bruta: Ícones SVG base ── */
[data-testid="stSidebar"] svg,
header[data-testid="stHeader"] svg,
[data-testid="stSidebarCollapseButton"] svg,
button svg {
    fill: #E2E8F0 !important;
    color: #E2E8F0 !important;
    transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), fill 0.3s ease !important;
}

/* ── Títulos de seção da navegação: Principal e Painéis ── */
[data-testid="stSidebarNav"] * {
    color: #C0C0C0 !important; /* Prata */
    font-weight: 900 !important;
    font-size: 1.1rem !important; /* Maior */
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
    text-shadow: 0 0 10px rgba(192, 192, 192, 0.4) !important;
}

/* Protegendo os links (para não pegarem o estilo do cabeçalho) */
[data-testid="stSidebarNav"] a * {
    color: rgba(255,255,255,0.7) !important;
    font-weight: 500 !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    font-size: 1.05rem !important;
    text-shadow: none !important;
}

/* Restaura o Hover e Ativo dos links que o curinga * poderia ter quebrado */
[data-testid="stSidebarNav"] a:hover * {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] * {
    color: #FFFFFF !important;
    font-weight: 700 !important;
    text-shadow: 0 0 10px rgba(255,255,255,0.25) !important;
}

/* ── Links de navegação - Estilo Base ── */
[data-testid="stSidebarNav"] a {
    border-radius: 10px !important;
    margin: 2px 10px !important;
    padding: 8px 14px !important;
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
    font-size: 1.05rem !important; /* Aumentado para acompanhar o a * */
    border-left: 0px solid transparent !important;
    background: transparent !important;
    position: relative !important;
    overflow: hidden !important;
}

/* Pseudo-elemento: Efeito de reflexo (shine) passando no hover */
[data-testid="stSidebarNav"] a::after {
    content: "" !important;
    position: absolute !important;
    top: 0 !important;
    left: -100% !important;
    width: 50% !important;
    height: 100% !important;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent) !important;
    transition: all 0.7s ease !important;
    transform: skewX(-20deg) !important;
}

[data-testid="stSidebarNav"] a:hover::after {
    left: 150% !important;
}

[data-testid="stSidebarNav"] a span {
    color: rgba(255,255,255,0.65) !important;
    font-weight: 500 !important;
    transition: color 0.3s ease, font-weight 0.3s ease !important;
}

/* ── Links de navegação - Hover Dinâmico ── */
[data-testid="stSidebarNav"] a:hover {
    background: rgba(255, 255, 255, 0.1) !important;
    transform: translateX(6px) !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important;
}

[data-testid="stSidebarNav"] a:hover span {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}

/* O ícone dá um pulinho e vira levemente ao passar o mouse */
[data-testid="stSidebarNav"] a:hover svg {
    transform: scale(1.3) rotate(-5deg) translateY(-2px) !important;
    fill: #7DD3FC !important;
    color: #7DD3FC !important;
}

/* ── Links de navegação - Item Ativo (Selecionado) ── */
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: linear-gradient(90deg, rgba(56,189,248,0.18) 0%, rgba(56,189,248,0.03) 100%) !important;
    box-shadow: inset 4px 0 0 0 #38BDF8, 0 4px 12px rgba(0,0,0,0.15) !important;
    border-radius: 0 10px 10px 0 !important;
    margin-left: 0 !important;
    padding-left: 28px !important;
}

[data-testid="stSidebarNav"] a[aria-current="page"] span {
    color: #FFFFFF !important;
    font-weight: 700 !important;
    text-shadow: 0 0 10px rgba(255,255,255,0.25) !important;
}

/* O ícone ativo tem um brilho permanente */
[data-testid="stSidebarNav"] a[aria-current="page"] svg {
    fill: #C0C0C0 !important;
    color: #C0C0C0 !important;
    filter: drop-shadow(0 0 6px rgba(192,192,192,1)) !important;
    transform: scale(1.1) !important;
}

/* ── Divisores modernos (hr) estilo neon / degrade ── */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(125,211,252,0.3), transparent) !important;
    margin: 18px 0 !important;
}

/* ── Botão de colapso — SEMPRE VISÍVEL & Redesenhado ── */
[data-testid="stSidebarCollapseButton"] {
    opacity: 1 !important;
    visibility: visible !important;
}

[data-testid="stSidebarCollapseButton"] > button {
    opacity: 1 !important;
    visibility: visible !important;
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    backdrop-filter: blur(10px) !important;
    border-radius: 50% !important;
    width: 34px !important;
    height: 34px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 10px 15px !important;
    cursor: pointer !important;
    transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
}

[data-testid="stSidebarCollapseButton"] > button:hover {
    background: rgba(56,189,248,0.2) !important;
    border-color: #38BDF8 !important;
    transform: rotate(90deg) scale(1.15) !important;
    box-shadow: 0 0 15px rgba(56,189,248,0.4) !important;
}

[data-testid="stSidebarCollapseButton"] > button svg {
    fill: #FFFFFF !important;
    opacity: 1 !important;
    width: 16px !important;
    height: 16px !important;
}

/* ── Botão de expandir (sidebar colapsada) — SEMPRE VISÍVEL ── */
[data-testid="stSidebarCollapsedControl"] {
    opacity: 1 !important;
    visibility: visible !important;
}

[data-testid="stSidebarCollapsedControl"] > button {
    opacity: 1 !important;
    background: #0B1320 !important;
    border: 1px solid rgba(56,189,248,0.5) !important;
    border-left: none !important;
    border-radius: 0 12px 12px 0 !important;
    transition: all 0.3s ease !important;
}

[data-testid="stSidebarCollapsedControl"] > button:hover {
    background: #1A2639 !important;
    box-shadow: 4px 0 15px rgba(56,189,248,0.2) !important;
    transform: scaleX(1.1) !important;
}

[data-testid="stSidebarCollapsedControl"] > button svg {
    fill: #7DD3FC !important;
}

/* ── Scrollbar Customizada da Sidebar ── */
[data-testid="stSidebar"] ::-webkit-scrollbar {
    width: 6px !important;
}
[data-testid="stSidebar"] ::-webkit-scrollbar-track {
    background: transparent !important;
}
[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover {
    background: rgba(255,255,255,0.25) !important;
}

/* ── Alerts na sidebar ── */
[data-testid="stSidebar"] [data-testid="stAlert"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    backdrop-filter: blur(8px) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
}

[data-testid="stSidebar"] [data-testid="stAlert"] p,
[data-testid="stSidebar"] [data-testid="stAlert"] div {
    color: rgba(255,255,255,0.85) !important;
    font-weight: 500 !important;
}

/* ── Logo no Topo do Menu ── */
[data-testid="stSidebarHeader"] {
    padding-top: 10px !important;
    padding-bottom: 25px !important;
    border-bottom: 1px solid rgba(125,211,252,0.3) !important;
    margin-bottom: 15px !important;
}

/* Força a Logo a SÓ EXISTIR dentro da Sidebar. Se minimizar, ela some junto! */
[data-testid="stLogo"] {
    display: none !important;
}

[data-testid="stSidebarHeader"] [data-testid="stLogo"] {
    display: flex !important;
    height: 4.5rem !important;
    max-height: 4.5rem !important;
}

/* Remove a faixa branca do cabeçalho superior que corta o topo da página */
.stAppHeader, 
header[data-testid="stHeader"] {
    background-color: transparent !important;
    background: transparent !important;
}

[data-testid="stSidebarNavItems"] {
    padding-top: 15px !important;
}
/* ── Ocultar Admin Logs nativo e botão View More/Less ── */
[data-testid="stSidebarNav"] a[href*="admin_logs"] {
    display: none !important;
}
[data-testid="stSidebarNav"] ul,
[data-testid="stSidebarNav"] ul li {
    max-height: none !important;
    overflow: visible !important;
}
[data-testid="stSidebarNav"] button {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# Adiciona a Logo da Empresa de forma nativa e fixa na barra superior do Menu
import os
import base64
logo_path = os.path.join(os.path.dirname(__file__), "assets", "Comp Logo.png")
transparent_path = os.path.join(os.path.dirname(__file__), "assets", "transparent_logo.png")

if not os.path.exists(transparent_path):
    # Cria uma imagem 1x1 transparente dinamicamente para usar quando o menu estiver recolhido
    b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    with open(transparent_path, "wb") as f:
        f.write(base64.b64decode(b64))

if os.path.exists(logo_path):
    # 'icon_image' define o que aparece quando a barra está fechada. Usando a imagem transparente, ele "some".
    try:
        st.logo(logo_path, icon_image=transparent_path)
    except TypeError:
        st.logo(logo_path)

# O Bot (Bot.py) não é mais executado pelo Streamlit.
# A execução do Bot agora é de responsabilidade exclusiva do Servidor (via container bot_extrator)
# para garantir que as rotinas funcionem mesmo com o painel fechado ou o PC do usuário desligado.

# --- LÓGICA DE LIMPEZA DE CACHE AUTOMÁTICA ---
# Esta função garante que o cache seja limpo na thread principal do Streamlit logo após 
# a atualização feita pelo servidor em background.
def check_cache_invalidation():
    try:
        import os
        json_path = "/app/data/atualizacoes.json"
        if os.path.exists(json_path):
            mtime = os.path.getmtime(json_path)
            ctrl_path = "/app/data/last_cache_clear.txt"
            
            last_clear = 0
            if os.path.exists(ctrl_path):
                with open(ctrl_path, "r") as f:
                    content = f.read().strip()
                    if content:
                        last_clear = float(content)
                        
            if mtime > last_clear:
                st.cache_data.clear()
                with open(ctrl_path, "w") as f:
                    f.write(str(mtime))
    except Exception:
        pass

check_cache_invalidation()

# Nova engine de Navegação do Streamlit (Cria Sessões Profissionais no Menu)
# Lista crua de páginas
raw_pages = [
    st.Page("views/home_ui/home_ui.py", title="Início", icon="🏠", default=True, url_path="home"),
    st.Page("views/centro_de_custo/centro_de_custo.py", title="Centro de Custo", icon="🏢", url_path="centro_custo"),
    st.Page("views/telefones/Telefone.py", title="Controle Telefones 🔒", icon="📱", url_path="controle_telefones"),
    st.Page("views/grupo_de_aprovadores/grupo_de_aprovadores.py", title="Grupo de Aprovadores", icon="👥", url_path="grupo_de_aprovadores"),
    st.Page("views/produtos/produtos.py", title="Produtos/Fornecedores", icon="📦", url_path="Produtos"),
    st.Page("views/atualizacao_fornecedor/atualizacao_fornecedor.py", title="Atualização Fornecedor 🔒", icon="📋", url_path="atualizacao_fornecedor"),
    st.Page("views/empresax_x_projeto_alfa/empresax_x_projeto_alfa.py", title="Empresa_X x Projeto_Alfa 🔒", icon="📈", url_path="empresax_x_projeto_alfa"),
    st.Page("views/controle_epi/controle_epi.py", title="Controle de EPI 🔒", icon="🦺", url_path="controle_epi"),
    st.Page("views/gestao_projetos/gestao_projetos.py", title="Gestão de Projetos 🔒", icon="📊", url_path="gestao_projetos"),
    st.Page("views/parceiro_y/parceiro_y.py", title="Parceiro_Y 🔒", icon="🛡️", url_path="parceiro_y"),
    st.Page("views/admin/admin_logs.py", title="Admin Logs 🔒", icon="⚙️", url_path="admin_logs"),
]

# Rotina de ordenação automática
home_page = [p for p in raw_pages if p.title == "Início"]
public_pages = sorted([p for p in raw_pages if p.title != "Início" and "🔒" not in p.title], key=lambda x: x.title)
private_pages_filtered = sorted([p for p in raw_pages if p.title != "Início" and "🔒" in p.title and "Admin Logs" not in p.title], key=lambda x: x.title)
admin_page = [p for p in raw_pages if "Admin Logs" in p.title]

# Organizar em dicionário (categorias) para evitar o colapso nativo "show more"
pages_dict = {
    "Principal": home_page,
    "Painéis": public_pages + private_pages_filtered + admin_page
}

try:
    pg = st.navigation(pages_dict, expanded=True)
except TypeError:
    pg = st.navigation(pages_dict)

# Injetar a página Admin Logs manualmente na barra lateral
st.sidebar.markdown("<br><br><br>", unsafe_allow_html=True)
st.sidebar.page_link(page=admin_page[0], label="Admin Logs", icon="⚙️")

# --- Componente de Última Atualização ---
def obter_ultima_atualizacao():
    import os
    import re
    
    log_path = "/app/data/log_execucao.txt"
    if not os.path.exists(log_path):
        return "Não informada"
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            linhas = f.readlines()
            for linha in reversed(linhas):
                if "FINALIZANDO EXECU" in linha or "Bot finalizado sem erros" in linha:
                    match = re.search(r'\[(\d{2}/\d{2}/\d{4} \d{2}:\d{2})', linha)
                    if match:
                        return match.group(1)
    except Exception:
        pass
    return "Não informada"

paginas_com_att = [
    "Centro de Custo", 
    "Grupo de Aprovadores", 
    "Produtos/Fornecedores", 
    "Empresa_X x Projeto_Alfa 🔒",
    "Atualização Fornecedor 🔒",
    "Gestão de Projetos 🔒"
]

if getattr(pg, 'title', None) in paginas_com_att:
    data_hora_att = obter_ultima_atualizacao()
    st.sidebar.success(f"✅ Base atualizada em: {data_hora_att}")

# --- RASTREAMENTO GLOBAL DE ACESSOS ---
def registrar_acesso_global(pagina_acessada):
    try:
        import datetime
        import os
        
        ip = "IP Desconhecido"
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            ip = headers.get("X-Forwarded-For") or headers.get("X-Real-IP") or headers.get("Host") or "IP Desconhecido"
            
        hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        log_acesso_path = "/app/data/acessos_admin.txt"
        os.makedirs("/app/data", exist_ok=True)
        
        usuario = st.session_state.get("username_logado")
        if st.session_state.get("is_root") and not usuario:
            usuario = "admin"
        user_str = f" - Usuário: {usuario}" if usuario else ""
        
        chave_sessao = f"acesso_registrado_{pagina_acessada}"
        if chave_sessao not in st.session_state:
            with open(log_acesso_path, "a", encoding="utf-8") as f:
                f.write(f"[{hoje}] Acesso detectado - IP: {ip}{user_str} - Aba: {pagina_acessada}\n")
            st.session_state[chave_sessao] = True
    except Exception:
        pass

if getattr(pg, 'title', None):
    registrar_acesso_global(pg.title)

pg.run()


