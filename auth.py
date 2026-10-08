import streamlit as st
import os
import json
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_users_db_path():
    return "Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/usuarios.json"

def load_users_db():
    import json
    import os
    import sys
    base_dir = os.path.abspath(os.path.dirname(__file__))
    if base_dir not in sys.path:
        sys.path.append(base_dir)
    from onedrive_downloader import download_excel_from_onedrive
    
    path = get_users_db_path()
    try:
        file_bytes_io = download_excel_from_onedrive(path)
        return json.loads(file_bytes_io.read().decode('utf-8'))
    except Exception:
        return {}

def save_users_db(db):
    import json
    import os
    import sys
    base_dir = os.path.abspath(os.path.dirname(__file__))
    if base_dir not in sys.path:
        sys.path.append(base_dir)
    from onedrive_downloader import upload_excel_to_onedrive, download_excel_from_onedrive
    
    path = get_users_db_path()
    json_bytes = json.dumps(db, indent=4, ensure_ascii=False).encode('utf-8')
    upload_excel_to_onedrive(path, json_bytes)
    download_excel_from_onedrive.clear()

def exigir_login(painel_nome, titulo_painel, subtitulo, icone="🔒"):
    auth_key = "autenticado_geral"
    
    # 1. Verifica se já está logado na sessão global
    if st.session_state.get(auth_key):
        # Admin supremo (Root) passa direto
        if st.session_state.get("is_root"):
            return
            
        # Verifica se o usuário tem a permissão específica deste painel
        user_info = st.session_state.get("user_info", {})
        paineis = user_info.get("paineis", [])
        
        if painel_nome in paineis:
            return
        else:
            # Se ele não tem permissão para a tela atual, avisa e para a execução.
            st.error(f"🛑 **Você está logado como '{st.session_state.get('username_logado')}', mas não possui acesso liberado para o painel: {painel_nome}.**\n\nSe houver necessidade de acesso a este painel, favor acionar a Área de Cadastros.")
            st.stop()

    # 2. Tela de Login Exclusiva e Profissional
    # Layout centralizado (3 colunas, usamos a do meio)
    _, col, _ = st.columns([1, 1.5, 1])
    
    with col:
        # Cabeçalho do Login Customizado por Painel
        st.markdown(f"""
        <div style="text-align:center; padding: 2rem 0 1rem 0;">
            <div style="font-size: 3.5rem; margin-bottom: 10px;">{icone}</div>
            <h2 style="margin: 0; font-weight: 700; letter-spacing: -0.5px;">{titulo_painel}</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-top: 5px;">{subtitulo}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Container com borda sutil nativa do Streamlit (se adapta perfeitamente a Claro/Escuro)
        with st.container(border=True):
            if st.session_state.get("usuario_primeiro_login"):
                st.markdown("### Primeiro Acesso")
                st.info("Por favor, cadastre uma nova senha para continuar.")
                with st.form("form_primeiro_login"):
                    nova_senha = st.text_input("Nova Senha", type="password")
                    confirma_senha = st.text_input("Confirme a Nova Senha", type="password")
                    
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    if st.form_submit_button("Salvar Senha e Acessar", type="primary", use_container_width=True):
                        if not nova_senha:
                            st.error("A senha não pode ser vazia.")
                        elif nova_senha != confirma_senha:
                            st.error("As senhas não coincidem.")
                        else:
                            uid = st.session_state["usuario_primeiro_login"]
                            db = load_users_db()
                            db[uid]["senha"] = hash_password(nova_senha)
                            db[uid]["primeiro_login"] = False
                            
                            save_users_db(db)
                                
                            info = db[uid]
                            is_admin = (info.get("perfil") == "Administrador")
                            st.session_state[auth_key] = True
                            st.session_state["is_root"] = is_admin
                            st.session_state["user_info"] = info
                            st.session_state["username_logado"] = uid
                            
                            del st.session_state["usuario_primeiro_login"]
                            st.rerun()
                            
                if st.button("Cancelar", use_container_width=True):
                    del st.session_state["usuario_primeiro_login"]
                    st.rerun()
            else:
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                
                # Formulário permite enviar com a tecla Enter nativamente!
                with st.form("login_form_central", clear_on_submit=False):
                    user = st.text_input("Usuário", placeholder="nome.sobrenome")
                    pwd = st.text_input("Senha", type="password", placeholder="••••••••")
                    
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    submitted = st.form_submit_button("Acessar Painel", type="primary", use_container_width=True)
                    
                    if submitted:
                        user_clean = user.strip().lower()
                        
                        admin_user = os.getenv("ADMIN_USER")
                        admin_pwd = os.getenv("ADMIN_PWD")
                        
                        db = load_users_db()
                        
                        # Checagem 1: É o Administrador Supremo?
                        if user_clean == admin_user and pwd == admin_pwd:
                            st.session_state[auth_key] = True
                            st.session_state["is_root"] = True
                            st.rerun()
                            
                        # Checagem 2: É um usuário cadastrado no JSON?
                        elif user_clean in db:
                            info = db[user_clean]
                            if info.get("bloqueado"):
                                st.error("❌ Seu acesso foi temporariamente bloqueado pelo administrador.")
                            elif info.get("senha") == hash_password(pwd):
                                is_admin = (info.get("perfil") == "Administrador")
                                if is_admin or painel_nome in info.get("paineis", []):
                                    if info.get("primeiro_login", False):
                                        st.session_state["usuario_primeiro_login"] = user_clean
                                        st.rerun()
                                    else:
                                        st.session_state[auth_key] = True
                                        st.session_state["is_root"] = is_admin
                                        st.session_state["user_info"] = info
                                        st.session_state["username_logado"] = user_clean
                                        st.rerun()
                                else:
                                    st.error(f"❌ Você não tem permissão para acessar o painel: {painel_nome}.")
                            else:
                                st.error("❌ Senha incorreta.")
                        else:
                            st.error("❌ Usuário não encontrado no sistema.")
                        
        st.markdown(f"""
        <div style="text-align:center; padding-top: 2rem; color: #94A3B8; font-size: 0.8rem;">
            &copy; 2026 EMPRESA_01 · Segurança de Acesso
        </div>
        """, unsafe_allow_html=True)
    
    # Impede que o resto da página carregue se não estiver logado
    st.stop()
