import streamlit as st
import datetime
import os
import sys
import json
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Garante que o diretório raiz está no PYTHONPATH para poder importar Bot.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import Bot

# --- FUNÇÕES DE LÓGICA ---
def get_client_ip():
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            ip = headers.get("X-Forwarded-For")
            if not ip:
                ip = headers.get("X-Real-IP")
            if not ip:
                ip = headers.get("Host")
            return ip or "IP Desconhecido"
    except Exception:
        pass
    return "IP Desconhecido"

def registrar_acesso():
    ip = get_client_ip()
    hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    log_acesso_path = "/app/data/acessos_admin.txt"
    os.makedirs("/app/data", exist_ok=True)
    with open(log_acesso_path, "a", encoding="utf-8") as f:
        f.write(f"[{hoje}] Acesso detectado - IP: {ip}\n")

def ler_acessos():
    log_acesso_path = "/app/data/acessos_admin.txt"
    if os.path.exists(log_acesso_path):
        with open(log_acesso_path, "r", encoding="utf-8") as f:
            return f.readlines()
    return []

def contar_usuarios():
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    usuarios = set()
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if "_USER" in linha and "=" in linha and not linha.startswith("#"):
                    user = linha.split("=", 1)[1].strip()
                    if user:
                        usuarios.add(user)
    return list(usuarios)

def ler_arquivos_consultados():
    from onedrive_downloader import get_onedrive_file_last_modified
    
    # Mapeamento de todos os arquivos consultados pelo sistema e seus caminhos EXATOS no SharePoint
    mapa_arquivos = {
        "Controle Linhas Corporativas.xlsx": {
            "Painel": "Controle Telefones", 
            "Caminho": "Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/Contatos/Controle Linhas Corporativas.xlsx"
        },
        "EPIS 16-01-2026.xlsx": {
            "Painel": "Controle de EPI", 
            "Caminho": "Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/App controle EPI/EPIS 16-01-2026.xlsx"
        },
        "Controle Cadastros.xlsx": {
            "Painel": "Atualização Fornecedor", 
            "Caminho": "Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/Controle Cadastros.xlsx"
        },
        "Projetos.xlsx": {
            "Painel": "Gestão de Projetos", 
            "Caminho": "Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/Projetos.xlsx"
        },
        "Aprovadores.xlsx": {
            "Painel": "Grupo de Aprovadores / CC", 
            "Caminho": "Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/Aprovadores.xlsx"
        },
        "Projeto_Alfa.xlsx": {
            "Painel": "EMPRESA_01 x Projeto_Alfa", 
            "Caminho": "Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/Projeto_Alfa.xlsx"
        },
        "Produtos.xlsx": {
            "Painel": "Produtos", 
            "Caminho": "Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/Produtos.xlsx"
        }
    }
    
    dados_tabela = []
    
    for arquivo, info in mapa_arquivos.items():
        painel = info["Painel"]
        caminho_nuvem = info["Caminho"]
        
        try:
            # Puxa diretamente a data de modificação da Graph API (SharePoint)
            sp_date_str = get_onedrive_file_last_modified(caminho_nuvem)
            if sp_date_str:
                # O formato da Microsoft é 'YYYY-MM-DDTHH:MM:SSZ' (UTC)
                # Parse e conversão para o fuso horário local do Brasil (-3h)
                sp_date = datetime.datetime.strptime(sp_date_str.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
                sp_date = sp_date - datetime.timedelta(hours=3)
                dt = sp_date.strftime('%d/%m/%Y %H:%M:%S')
            else:
                dt = "Não encontrado no SharePoint"
        except Exception as e:
            dt = f"Erro na API"
            
        dados_tabela.append({
            "Painel": painel,
            "Arquivo": arquivo,
            "Última Modificação (SharePoint)": dt
        })
        
    return dados_tabela

# --- BANCO DE USUÁRIOS (JSON CRIPTOGRAFADO) ---
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_users_db_path():
    import auth
    return auth.get_users_db_path()

def load_users_db():
    import auth
    return auth.load_users_db()

def save_users_db(data):
    import auth
    auth.save_users_db(data)


# --- DIÁLOGOS (POP-UPS) ---
@st.dialog("Histórico Completo de Execução", width="large")
def modal_logs():
    st.write("Abaixo estão todos os logs de execução do bot.")
    LOG_PATH = "/app/data/log_execucao.txt"
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            logs_raw = f.readlines()
        
        import re
        grouped_logs = []
        current_date = None
        for line in reversed(logs_raw):
            match = re.match(r"^\[(\d{2}/\d{2}/\d{4})", line)
            if match:
                log_date = match.group(1)
                if log_date != current_date:
                    if current_date is not None:
                        grouped_logs.append("\n")
                    grouped_logs.append(f"--- {log_date} ---\n")
                    current_date = log_date
            grouped_logs.append(line)
            
        logs_text = "".join(grouped_logs).strip()
        st.text_area("Registros (Mais recentes primeiro)", value=logs_text, height=450, disabled=True)
        with open(LOG_PATH, "rb") as f:
            st.download_button(label="📥 Baixar Arquivo de Log (.txt)", data=f, file_name="log_execucao.txt", mime="text/plain")
    else:
        st.info("O arquivo log_execucao.txt ainda não existe ou está vazio.")

@st.dialog("Monitoramento de Acessos", width="large")
def modal_acessos():
    st.write("**Histórico de acessos aos painéis do Dashboard:**")
    acessos = ler_acessos()
    if acessos:
        acessos.reverse()
        st.text_area("Registro de IPs e Abas acessadas", value="".join(acessos), height=400, disabled=True)
    else:
        st.info("Nenhum acesso registrado ainda.")

@st.dialog("Gestão de Usuários (Central)", width="large")
def modal_usuarios_gestao():
    db = load_users_db()
    


    # -- Header: Criar Novo Usuário
    st.markdown("### Gestão de Acessos")
    with st.expander("➕ Adicionar Novo Usuário"):
        with st.form("form_novo_user"):
            n_username = st.text_input("Usuário de login (ex: nome.sobrenome)")
            n_nome = st.text_input("Nome Completo (ex: João da Silva)")
            n_email = st.text_input("E-mail corporativo")
            n_senha = st.text_input("Senha Inicial", type="password")
            
            n_perfil = st.selectbox("Perfil de Acesso:", ["Usuário Padrão", "Administrador"])
            
            paineis_disponiveis = [
                "Parceiro_Y", "Centro de Custo (Edição)", "Gestão de Projetos", 
                "Controle Telefones", "Controle de EPI", "EMPRESA_01 x Projeto_Alfa", 
                "Atualização Fornecedor"
            ]
            st.caption("Administradores têm acesso automático a todos os painéis, incluindo o Admin Logs.")
            n_paineis = st.multiselect("Painéis Liberados (apenas para Usuário Padrão):", paineis_disponiveis)
            
            if st.form_submit_button("Salvar Usuário", type="primary"):
                if n_username and n_senha:
                    uid = n_username.strip().lower()
                    if uid in db:
                        st.error("Usuário já existe!")
                    else:
                        db[uid] = {
                            "nome": n_nome,
                            "email": n_email,
                            "senha": hash_password(n_senha),
                            "data_criacao": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "bloqueado": False,
                            "perfil": n_perfil,
                            "paineis": n_paineis if n_perfil == "Usuário Padrão" else paineis_disponiveis,
                            "primeiro_login": True
                        }
                        save_users_db(db)
                        st.success(f"Usuário {n_username} criado!")
                        st.rerun()
                else:
                    st.error("Preencha Usuário e Senha!")

    # -- Lista de Usuários
    st.markdown("#### Usuários Cadastrados")
    for uid, info in db.items():
        with st.container(border=True):
            col_info, col_actions = st.columns([3.5, 1])
            with col_info:
                status = "🔴 BLOQUEADO" if info.get('bloqueado') else "🟢 ATIVO"
                perfil = info.get('perfil', 'Usuário Padrão')
                icone_perfil = "👑" if perfil == "Administrador" else "👤"
                
                st.markdown(f"**{info.get('nome', uid)}** ({uid}) — {status}")
                st.caption(f"{icone_perfil} **{perfil}** | {info.get('email', 'S/ Email')} | Criado em: {info.get('data_criacao', 'Desconhecido')}")
                
                if perfil == "Administrador":
                    st.caption("**Painéis:** Acesso Total (Root)")
                else:
                    st.caption(f"**Painéis:** {', '.join(info.get('paineis', []))}")
            
            with col_actions:
                st.write("")
                if st.button("✏️ Editar", key=f"edit_{uid}", use_container_width=True):
                    st.session_state['usuario_editando'] = uid
                    st.rerun()
                
                btn_txt = "Desbloquear" if info.get('bloqueado') else "Bloquear"
                if st.button(btn_txt, key=f"blk_{uid}", use_container_width=True):
                    db[uid]['bloqueado'] = not db[uid].get('bloqueado', False)
                    save_users_db(db)
                    st.rerun()
                if st.button("Excluir", key=f"del_{uid}", use_container_width=True, type="secondary"):
                    del db[uid]
                    save_users_db(db)
                    st.rerun()

@st.dialog("Editar Cadastro do Usuário")
def modal_editar_usuario():
    db = load_users_db()
    uid = st.session_state.get('usuario_editando')
    if uid not in db: return
    info = db[uid]
    
    with st.form("form_edit_user"):
        n_nome = st.text_input("Nome", value=info.get("nome", ""))
        n_email = st.text_input("E-mail", value=info.get("email", ""))
        n_senha = st.text_input("Nova Senha (deixe em branco para não alterar)", type="password")
        
        n_perfil = st.selectbox("Perfil de Acesso:", ["Usuário Padrão", "Administrador"], index=0 if info.get("perfil", "Usuário Padrão") == "Usuário Padrão" else 1)
        
        paineis_disponiveis = [
            "Parceiro_Y", "Centro de Custo (Edição)", "Gestão de Projetos", 
            "Controle Telefones", "Controle de EPI", "EMPRESA_01 x Projeto_Alfa", 
            "Atualização Fornecedor"
        ]
        
        # Filtra para evitar erro de valores que já não existem
        default_paineis = [p for p in info.get("paineis", []) if p in paineis_disponiveis]
        n_paineis = st.multiselect("Painéis Liberados (Ignorado se Administrador):", paineis_disponiveis, default=default_paineis)
        
        if st.form_submit_button("Salvar Alterações", type="primary"):
            db[uid]["nome"] = n_nome
            db[uid]["email"] = n_email
            db[uid]["perfil"] = n_perfil
            db[uid]["paineis"] = n_paineis if n_perfil == "Usuário Padrão" else paineis_disponiveis
            if n_senha:
                db[uid]["senha"] = hash_password(n_senha)
            save_users_db(db)
            st.success("Usuário atualizado com sucesso!")
            del st.session_state['usuario_editando']
            st.rerun()
    if st.button("Cancelar"):
        del st.session_state['usuario_editando']
        st.rerun()

@st.dialog("Arquivos e Consultas do Bot", width="large")
def modal_arquivos():
    st.write("Data e hora em que cada arquivo foi atualizado pelas consultas SQL.")
    dados_arquivos = ler_arquivos_consultados()
    if dados_arquivos:
        df_arquivos = pd.DataFrame(dados_arquivos)
        st.dataframe(df_arquivos, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum registro de atualização de arquivos encontrado (verifique `atualizacoes.json`).")

@st.dialog("Controle de Execução", width="large")
def modal_bot():
    st.warning("⚠️ Atenção: Esta ação vai forçar a extração dos dados imediatamente.")
    _, col_btn, _ = st.columns([1, 1.5, 1])
    with col_btn:
        if st.button("🔄 Rodar Atualização do Bot Agora", type="primary", use_container_width=True):
            with st.spinner("Rodando a extração..."):
                try:
                    Bot.rodar_extracao()
                    st.success("✅ Extração concluída com sucesso!")
                    st.cache_data.clear()
                    timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    os.makedirs("/app/data", exist_ok=True)
                    with open("/app/data/log_execucao.txt", "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] [EXECUÇÃO MANUAL] Bot finalizado sem erros.\n")
                except Exception as e:
                    st.error(f"Ocorreu um erro interno ao disparar o bot. Detalhes: {e}")
                    timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    os.makedirs("/app/data", exist_ok=True)
                    with open("/app/data/log_execucao.txt", "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] [EXECUÇÃO MANUAL] ERRO CRÍTICO: {str(e)}\n")

@st.dialog("Limpar Cache dos Painéis", width="small")
def modal_limpar_cache():
    st.write("Deseja limpar a memória temporária (cache) de todos os painéis?")
    st.write("Isso fará com que o sistema recarregue os dados diretamente dos arquivos do disco.")
    
    col1, col2 = st.columns(2)
    
    limpou = False
    with col1:
        if st.button("Sim, limpar cache", type="primary", use_container_width=True):
            st.cache_data.clear()
            limpou = True
    with col2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()
            
    if limpou:
        st.success("✅ Cache limpo com sucesso!")

# --- UI PRINCIPAL ---
st.title("Admin Logs & Monitoramento 🔒")

import auth

# Força o login usando o módulo centralizado
auth.exigir_login(
    painel_nome="Admin Logs",
    titulo_painel="Admin Logs & Monitoramento",
    subtitulo="Gestão de Usuários, Acessos e Logs de Execução",
    icone="⚙️"
)

# Se passou do exigir_login, exibe o Dashboard
if st.session_state.get('usuario_editando'):
    modal_editar_usuario()

st.markdown("<p style='color:#7DD3FC; font-weight:600; font-size:1.1rem; margin-bottom: 25px;'>Painel de Monitoramento Geral</p>", unsafe_allow_html=True)
    
# Ajuste CSS para que botões grandes (cards) fiquem mais altos
# Mas apenas fora dos popups (modals)
st.markdown("""
<style>
div.stButton > button {
    height: 120px;
    font-size: 1.1rem;
    font-weight: 600;
    border-radius: 12px;
}
/* Reseta o estilo gigante para botões dentro de modals (dialogs) */
div[role="dialog"] div.stButton > button {
    height: auto !important;
    font-size: 1rem !important;
    font-weight: normal !important;
    border-radius: 0.5rem !important;
}
</style>
""", unsafe_allow_html=True)

# Cria uma grade de botões HTML usando colunas
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📄 Histórico\n\nLogs do sistema e bot", use_container_width=True): modal_logs()

with col2:
    if st.button("👥 Usuários\n\nGestão e permissões", use_container_width=True): modal_usuarios_gestao()

with col3:
    if st.button("👁️ Acessos\n\nRastreio de IPs", use_container_width=True): modal_acessos()

col4, col5, col6 = st.columns(3)

with col4:
    if st.button("📁 Arquivos\n\nMapeamento de dados", use_container_width=True): modal_arquivos()

with col5:
    if st.button("⚙️ Execução\n\nForçar disparo do bot", use_container_width=True): modal_bot()

with col6:
    if st.button("🧹 Limpar Cache\n\nAtualizar memória dos painéis", use_container_width=True): modal_limpar_cache()

st.markdown("<br><hr style='border-color: rgba(255,255,255,0.05);'><br>", unsafe_allow_html=True)

# Resumo Rápido visível diretamente no painel
st.markdown("<p style='color:#7DD3FC; font-weight:600; font-size:1.1rem; margin-bottom: 15px;'>Resumo em Tempo Real 🔗</p>", unsafe_allow_html=True)

db_users = load_users_db()
dados_arquivos = ler_arquivos_consultados()
qtd_tabelas = len(dados_arquivos) if dados_arquivos else 0
ip_admin = get_client_ip()

html_kpis = f"""
<div style="display: flex; gap: 20px; margin-bottom: 20px;">
    <div style="flex: 1; background: linear-gradient(145deg, #1A2639, #0f1724); padding: 20px; border-radius: 12px; border-left: 4px solid #3b82f6; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
        <p style="color: #94A3B8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; font-weight: 700;">👥 Total de Usuários (Central)</p>
        <h3 style="color: #FFFFFF; font-size: 2.2rem; margin: 0; font-weight: 800; text-shadow: 0 0 10px rgba(255,255,255,0.1);">{len(db_users)}</h3>
    </div>
    <div style="flex: 1; background: linear-gradient(145deg, #1A2639, #0f1724); padding: 20px; border-radius: 12px; border-left: 4px solid #10b981; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
        <p style="color: #94A3B8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; font-weight: 700;">🔄 Tabelas Sincronizadas</p>
        <h3 style="color: #10b981; font-size: 2.2rem; margin: 0; font-weight: 800; text-shadow: 0 0 10px rgba(16,185,129,0.2);">{qtd_tabelas}</h3>
    </div>
    <div style="flex: 1; background: linear-gradient(145deg, #1A2639, #0f1724); padding: 20px; border-radius: 12px; border-left: 4px solid #8b5cf6; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
        <p style="color: #94A3B8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; font-weight: 700;">🌐 Seu IP (Admin)</p>
        <h3 style="color: #8b5cf6; font-size: 1.6rem; margin: 0; font-weight: 700; padding-top: 6px;">{ip_admin}</h3>
    </div>
</div>
"""
st.markdown(html_kpis, unsafe_allow_html=True)
