import streamlit as st
import os
import base64

def load_css():
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def carregar_imagem_base64_local(caminho_imagem):
    if os.path.exists(caminho_imagem):
        with open(caminho_imagem, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def render_standard_panel(title, subtitle, icon_name="Portal dados logo.png", content_function=None, center_title=False):
    """
    Renderiza um painel padronizado com cabeçalho, injetando o CSS global.
    """
    load_css()
    
    diretorio_base = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(diretorio_base, "assets", icon_name)
    img_b64 = carregar_imagem_base64_local(img_path)
    
    justify = "center" if center_title else "flex-start"
    
    html_subtitle = f'<p style="margin: 6px 0 0; color: var(--text-color); opacity: 0.7; font-size: 0.95em; letter-spacing: 0.2px;">{subtitle}</p>' if subtitle else ''
    
    html_cabecalho = f"""
    <div style="
        display: flex;
        align-items: center;
        justify-content: {justify};
        padding: 0 0 16px;
        margin-bottom: 0px;
    ">
        <div style="
            background: var(--secondary-background-color);
            border: 1px solid rgba(128,128,128,0.15);
            border-radius: 16px;
            padding: 14px;
            margin-right: 22px;
            display: flex;
            align-items: center;
            justify-content: center;
        ">
            <img src="data:image/png;base64,{img_b64}" style="width: 68px; height: 68px; object-fit: contain;">
        </div>
        <div>
            <h1 style="margin: 0; font-size: 2.4em; font-weight: 800; letter-spacing: -0.5px; line-height: 1.1; color: var(--text-color);">{title}</h1>{html_subtitle}
        </div>
    </div>
    """
    st.markdown(html_cabecalho, unsafe_allow_html=True)
    st.markdown("<hr style='border: none; border-top: 1px solid rgba(200,200,200,0.15); margin: 4px 0 20px;'>", unsafe_allow_html=True)
    
    if content_function:
        content_function()
