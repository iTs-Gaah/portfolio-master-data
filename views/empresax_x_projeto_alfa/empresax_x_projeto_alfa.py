import streamlit as st
import pandas as pd
import plotly.express as px
import os
# Remove a variável de ambiente GOOGLE_API_KEY se existir para evitar conflito com GEMINI_API_KEY
if 'GOOGLE_API_KEY' in os.environ:
    del os.environ['GOOGLE_API_KEY']
from google import genai
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import auth

auth.exigir_login(
    painel_nome="Empresa_X x Projeto_Alfa",
    titulo_painel="Inconsistências Cadastrais",
    subtitulo="Auditoria de Base EMPRESA_X vs PROJETO_ALFA",
    icone="🚨"
)

try:
    # O novo SDK utiliza a inicialização da classe Client
    import os
    from dotenv import load_dotenv
    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    # No novo formato, armazena-se o nome do modelo como string para uso posterior
    modelo_ia = 'gemini-2.5-flash'
except Exception as e:
    st.error("Não localizado a chave da API do Gemini. Verifique as configurações.")
    st.stop()
# --- CSS ANABOLIZADO PRA DEIXAR O VISUAL DECENTE ---
st.markdown("""
<style>
/* Estilo dos cards (KPIs) com sombra e borda para dar profundidade */
[data-testid="stMetric"] {
    background-color: var(--secondary-background-color);
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(128, 128, 128, 0.2);
}

/* Destaque nos títulos (Subheaders) pra não ficarem apagados */
h3 {
    font-weight: 700 !important;
    padding-bottom: 8px;
    border-bottom: 2px solid rgba(128, 128, 128, 0.3);
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
try:
    import ui_utils
    ui_utils.render_standard_panel(
        title="Painel de Inconsistências",
        subtitle="EMPRESA_X vs PROJETO_ALFA",
        icon_name="Projeto_Alfa logo.png"
    )
except ImportError:
    st.title(" 🚨 Painel de Inconsistências - EMPRESA_X vs PROJETO_ALFA")
    st.markdown("---")
    st.markdown("")

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Caminho do arquivo gerado pelo bot
caminho_fixo = "/app/data/Projeto_Alfa.xlsx"
arquivo_unico = None

# Verifica de onde vai vir o arquivo
if os.path.exists(caminho_fixo):
    timestamp = os.path.getmtime(caminho_fixo)
    arquivo_unico = caminho_fixo
else:
    st.sidebar.error("❌ Arquivo não encontrado no caminho padrão.")
    arquivo_unico = st.sidebar.file_uploader("Upload da Base Unificada", type=["xlsx"])

# Função blindada por Cache Inteligente (Lê e limpa o DataFrame em milissegundos)
@st.cache_data(show_spinner="Analisando Base de Dados Unificada...", ttl=14400)
def importar_e_limpar_dados(arquivo, ts=0):
    try:
        df_lido = pd.read_excel(arquivo)
        # MÁGICA PRA LIMPAR O LIXO DA BASE E MATAR O ERRO DO PYARROW
        colunas_pra_limpar = ['COD_EMPRESA_X', 'COD_COMPAS', 'COD_PROJETO_ALFA']
        for col in colunas_pra_limpar:
            if col in df_lido.columns:
                # Transforma em texto, limpa os lixos e tira espaços
                df_lido[col] = df_lido[col].astype(str).str.replace('.0', '', regex=False).str.replace('\t', '', regex=False).str.strip()
                # Mata a palavra "nan" que o Pandas cria nos campos vazios
                df_lido[col] = df_lido[col].replace('nan', None)
        return df_lido, None
    except Exception as erro:
        return None, erro

# Só roda o resto se tiver um arquivo válido carregado
if arquivo_unico:
    # Captura a data de modificação se for o arquivo fixo, ou zero se for upload manual
    tempo_modificacao = timestamp if 'timestamp' in locals() else 0
    
    df, erro_leitura = importar_e_limpar_dados(arquivo_unico, ts=tempo_modificacao)
    
    if erro_leitura:
        st.error("Não foi possível ler o arquivo da base.")
        st.stop()
        
    if df is None or df.empty:
        st.error("O arquivo lido gerou uma planilha vazia. Verifique a formatação.")
        st.stop()
# --- ALERTA CRÍTICO: PROJETO_ALFA SEM EMPRESA_X ---
    col_empresax_val = 'COD_EMPRESA_X' if 'COD_EMPRESA_X' in df.columns else ('COD_COMPAS' if 'COD_COMPAS' in df.columns else None)

    if col_empresax_val and 'COD_PROJETO_ALFA' in df.columns:
        # Filtra quem tá no Projeto_Alfa mas não na Empresa_X
        erros_projeto_alfa = df[(df['COD_PROJETO_ALFA'].notna()) & (df[col_empresax_val].isna())]

        if not erros_projeto_alfa.empty:
            st.error(f"🚨 ALERTA CRÍTICO: Encontrado {len(erros_projeto_alfa)} cadastro(s) no PROJETO_ALFA que não existem na EMPRESA_X!")
            
            cols_exibir = [c for c in ['TIPO', 'COD_PROJETO_ALFA', 'DESC_PROJETO_ALFA'] if c in erros_projeto_alfa.columns]
            st.dataframe(erros_projeto_alfa[cols_exibir].reset_index(drop=True), use_container_width=True)
        else:
            st.success("✅ Todos os cadastros base estão OK.")

    # --- ALERTA DE DIVERGÊNCIA CADASTRAL (CNPJ/DESCRIÇÃO) ---
    if 'VALIDACAO' in df.columns:
        erros_divergentes = df[df['VALIDACAO'].astype(str).str.contains('divergente para mesmo código', case=False, na=False)]
        
        if not erros_divergentes.empty:
            st.warning(f"⚠️ AVISO: Encontrados {len(erros_divergentes)} código(s) com informações divergentes (CNPJ ou Descrição) entre as bases!")
            cols_exibir_div = [c for c in ['TIPO', col_empresax_val, 'COD_PROJETO_ALFA', 'DESC_EMPRESA_X', 'DESC_PROJETO_ALFA', 'VALIDACAO'] if c and c in df.columns]
            st.dataframe(erros_divergentes[cols_exibir_div].reset_index(drop=True), use_container_width=True)

    # --- SETUP DOS CONTAINERS ---
    container_kpi = st.container()
    container_grafico = st.container()
    container_filtros = st.container()
    container_tabela = st.container()
    container_rodape = st.container()

    # --- LÓGICA DE ESTADO DOS FILTROS ---
    if 'filtro_tipo' not in st.session_state:
        st.session_state.filtro_tipo = "TODOS"
    if 'filtro_val' not in st.session_state:
        st.session_state.filtro_val = "TODAS"
    if 'busca_desc' not in st.session_state:
        st.session_state.busca_desc = ""
    if 'busca_cod' not in st.session_state:
        st.session_state.busca_cod = ""

    def limpar_filtros():
        st.session_state.filtro_tipo = "TODOS"
        st.session_state.filtro_val = "TODAS"
        st.session_state.busca_desc = ""
        st.session_state.busca_cod = ""

    def resetar_validacao():
        st.session_state.filtro_val = "TODAS"

    # --- RENDERIZA OS FILTROS ---
    with container_filtros:
        st.subheader("Filtros e Buscas")
        
        col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
        
        with col_f1:
            opcoes_tipo = ["TODOS", "FORNECEDOR", "PRODUTO", "CLIENTE"]
            tipo_selecionado = st.selectbox("TIPO", options=opcoes_tipo, key='filtro_tipo', on_change=resetar_validacao)

        df_temp = df.copy()
        if tipo_selecionado != "TODOS":
            df_temp = df_temp[df_temp['TIPO'] == tipo_selecionado]
            
        val_disponiveis = df_temp['VALIDACAO'].dropna().unique().tolist() if 'VALIDACAO' in df_temp.columns else []

        with col_f2:
            if val_disponiveis:
                opcoes_val = ["TODAS"] + val_disponiveis
                val_selecionada = st.selectbox("Validação", options=opcoes_val, key='filtro_val')
            else:
                val_selecionada = "TODAS"
                st.warning("Coluna 'VALIDACAO' não encontrada.")

        with col_f3:
            st.write("") 
            st.write("")
            st.button("🧹 Limpar Filtros", on_click=limpar_filtros)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            busca_desc = st.text_input("Buscar por Descrição", key='busca_desc')
        with col_b2:
            busca_cod = st.text_input("Buscar por Código", key='busca_cod')

    # Aplicando filtros
    df_filtrado = df.copy()
    
    if tipo_selecionado != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['TIPO'] == tipo_selecionado]
        
    if val_selecionada != "TODAS":
        df_filtrado = df_filtrado[df_filtrado['VALIDACAO'] == val_selecionada]

    if busca_desc:
        desc_comp = df_filtrado['DESC_EMPRESA_X'].astype(str).str.contains(busca_desc, case=False, na=False) if 'DESC_EMPRESA_X' in df_filtrado.columns else False
        desc_ronc = df_filtrado['DESC_PROJETO_ALFA'].astype(str).str.contains(busca_desc, case=False, na=False) if 'DESC_PROJETO_ALFA' in df_filtrado.columns else False
        df_filtrado = df_filtrado[desc_comp | desc_ronc]

    if busca_cod:
        col_empresax = 'COD_EMPRESA_X' if 'COD_EMPRESA_X' in df_filtrado.columns else ('COD_COMPAS' if 'COD_COMPAS' in df_filtrado.columns else None)
        cod_comp = df_filtrado[col_empresax].astype(str).str.contains(busca_cod, case=False, na=False) if col_empresax else False
        cod_ronc = df_filtrado['COD_PROJETO_ALFA'].astype(str).str.contains(busca_cod, case=False, na=False) if 'COD_PROJETO_ALFA' in df_filtrado.columns else False
        df_filtrado = df_filtrado[cod_comp | cod_ronc]

    # --- KPIs ---
    with container_kpi:
        col1, col2, col3, col4 = st.columns(4)
        
        total_itens = len(df_filtrado)
        
        if "VALIDACAO" in df.columns:
            df_val_lower = df_filtrado['VALIDACAO'].astype(str).str.lower()
            
            cadastros_iguais = len(df_val_lower[df_val_lower == 'cadastros iguais'])
            nao_cad_prod = len(df_val_lower[df_val_lower == 'produto não cadastrado'])
            nao_cad_forn = len(df_val_lower[df_val_lower == 'fornecedor não cadastrado'])
            nao_cad_cli = len(df_val_lower[df_val_lower == 'cliente não cadastrado']) 
            
            nao_cadastrado = nao_cad_prod + nao_cad_forn + nao_cad_cli 
            divergentes = len(df_val_lower[df_val_lower.str.contains('diferente|divergente', regex=True, na=False)])
        else:
            cadastros_iguais = nao_cadastrado = divergentes = 0

        col1.metric("Total de Cadastros", total_itens)
        col2.metric("Cadastros Iguais", cadastros_iguais)
        col3.metric("Não Cadastrados", nao_cadastrado) 
        col4.metric("Divergentes", divergentes)

    # --- GRÁFICO ---
    with container_grafico:
        if "VALIDACAO" in df_filtrado.columns and not df_filtrado.empty:
            st.subheader("Distribuição dos Status")
            
            df_grafico_limpo = df_filtrado[~df_filtrado['VALIDACAO'].astype(str).str.contains('1900', na=False)]
            
            df_grafico = df_grafico_limpo['VALIDACAO'].value_counts().reset_index()
            df_grafico.columns = ['Status', 'Quantidade']
            
            fig = px.bar(
                df_grafico,
                x='Status',
                y='Quantidade',
                text='Quantidade',
                color='Status',
                color_discrete_map={
                    'Cadastros iguais': '#28a745',          # Verde
                    'Produto não cadastrado': '#003399',    # Azul Escuro
                    'Fornecedor não cadastrado': '#87CEFA', # Azul Claro
                    'Cliente não cadastrado': '#FF8C00',    # Laranja
                    'Valores são diferentes entre as bases': '#DC143C', # Vermelho
                    'CNPJ divergente para mesmo código': '#DC143C',
                    'Descrição divergente para mesmo código': '#DC143C'
                }
            )
            st.plotly_chart(fig, use_container_width=True)

        elif df_filtrado.empty:
            st.warning("Nenhum dado com esses filtros.")

        else:
            st.info("Faz o upload do arquivo ali na barra lateral pra começar.")

    # --- TABELA DETALHADA ---
    with container_tabela:
        st.subheader("📊 Dados detalhados")
        
        # Remove colunas duplicadas que podem causar crash no st.dataframe (React Error 185)
        df_filtrado_unico = df_filtrado.loc[:, ~df_filtrado.columns.duplicated()].copy()
        
        colunas_exibir = df_filtrado_unico.columns.tolist()
        
        colunas_lixo = ["RECNO_EMPRESA_X", "RECNO_PROJETO_ALFA", "STAMP_EMPRESA_X", "STAMP_PROJETO_ALFA"]
        colunas_exibir = [col for col in colunas_exibir if col not in colunas_lixo and col != "S_T_A_M_P_" and not col.startswith("Unnamed")]
        
        if tipo_selecionado == "PRODUTO":
            colunas_exibir = [col for col in colunas_exibir if col not in ["LOJA_EMPRESA_X", "LOJA_PROJETO_ALFA"]]

        df_display = df_filtrado_unico[colunas_exibir].reset_index(drop=True)
        # Limpar "nan" indesejados nas colunas
        df_display = df_display.replace(['nan', 'NaN', 'None', '<NA>', 'NoneType'], '')
        
        st.dataframe(df_display, use_container_width=True)

    # --- AUDITORIA DE RECNO E PRÓXIMO CÓDIGO ---
    with container_rodape:
        st.markdown("---")
        st.subheader("🕵️ Últimos Registros")

        tipo_ultimos = st.radio("Selecione o tipo:", ["PRODUTO", "FORNECEDOR", "CLIENTE"], horizontal=True)

        df_base_ultimos = df[df['TIPO'] == tipo_ultimos].copy() if 'TIPO' in df.columns else df.copy()

        col_comp, col_ronc = st.columns(2)

        # EMPRESA_X por RECNO
        with col_comp:
            st.markdown(f"**Últimos 50 cadastros - EMPRESA_X**")
            if "RECNO_EMPRESA_X" in df_base_ultimos.columns:
                df_base_ultimos['RECNO_NUM_EMPRESA_X'] = pd.to_numeric(df_base_ultimos['RECNO_EMPRESA_X'], errors='coerce')
                
                ultimos_comp = df_base_ultimos.sort_values(by="RECNO_NUM_EMPRESA_X", ascending=False).head(50)
                
                ultimos_comp = ultimos_comp.sort_values(by="RECNO_NUM_EMPRESA_X", ascending=True)
                
                # Formatar o RECNO sem pontos ou vírgulas
                ultimos_comp['RECNO_EMPRESA_X'] = ultimos_comp['RECNO_NUM_EMPRESA_X'].apply(
                    lambda x: str(int(x)) if pd.notna(x) else ""
                )
                
                col_cod_comp = 'COD_EMPRESA_X' if 'COD_EMPRESA_X' in ultimos_comp.columns else ('COD_COMPAS' if 'COD_COMPAS' in ultimos_comp.columns else None)
                cols_comp = [c for c in [col_cod_comp, 'DESC_EMPRESA_X', 'RECNO_EMPRESA_X'] if c and c in ultimos_comp.columns]
                
                if "STAMP_EMPRESA_X" in ultimos_comp.columns: 
                    ultimos_comp['STAMP_EMPRESA_X'] = ultimos_comp['STAMP_EMPRESA_X'].astype(str).replace(['nan', 'NaN', 'None', '<NA>'], '')
                    cols_comp.append("STAMP_EMPRESA_X")
                elif "S_T_A_M_P_" in ultimos_comp.columns: 
                    ultimos_comp['S_T_A_M_P_'] = ultimos_comp['S_T_A_M_P_'].astype(str).replace(['nan', 'NaN', 'None', '<NA>'], '')
                    cols_comp.append("S_T_A_M_P_")
                
                st.dataframe(ultimos_comp[cols_comp].reset_index(drop=True), use_container_width=True)
            else:
                st.warning("Sem coluna RECNO_EMPRESA_X pra ordenar.")

        # PROJETO_ALFA por RECNO
        with col_ronc:
            st.markdown(f"**Últimos 50 cadastros - PROJETO_ALFA**")
            if "RECNO_PROJETO_ALFA" in df_base_ultimos.columns:
                df_base_ultimos['RECNO_NUM_PROJETO_ALFA'] = pd.to_numeric(df_base_ultimos['RECNO_PROJETO_ALFA'], errors='coerce')
                
                ultimos_ronc = df_base_ultimos.sort_values(by="RECNO_NUM_PROJETO_ALFA", ascending=False).head(50)
                ultimos_ronc = ultimos_ronc.sort_values(by="RECNO_NUM_PROJETO_ALFA", ascending=True)
                
                # Formatar o RECNO sem pontos ou vírgulas
                ultimos_ronc['RECNO_PROJETO_ALFA'] = ultimos_ronc['RECNO_NUM_PROJETO_ALFA'].apply(
                    lambda x: str(int(x)) if pd.notna(x) else ""
                )
                
                cols_ronc = [c for c in ['COD_PROJETO_ALFA', 'DESC_PROJETO_ALFA', 'RECNO_PROJETO_ALFA'] if c in ultimos_ronc.columns]
                
                if "STAMP_PROJETO_ALFA" in ultimos_ronc.columns: 
                    ultimos_ronc['STAMP_PROJETO_ALFA'] = ultimos_ronc['STAMP_PROJETO_ALFA'].astype(str).replace(['nan', 'NaN', 'None', '<NA>'], '')
                    cols_ronc.append("STAMP_PROJETO_ALFA")
                
                st.dataframe(ultimos_ronc[cols_ronc].reset_index(drop=True), use_container_width=True)
            else:
                st.warning("Sem coluna RECNO_PROJETO_ALFA pra ordenar.")

        # FUNÇÃO PARA CALCULAR PRÓXIMO CÓDIGO (BASEADA NO MAIOR RECNO)
        def calcular_proximo_codigo_por_recno(df_calc, col_cod, col_recno, prefixo, tamanho):
            if col_cod not in df_calc.columns or col_recno not in df_calc.columns: 
                return "Base corrompida"
            
            df_temp = df_calc[[col_cod, col_recno]].dropna().copy()
            
            df_temp['COD_LIMPO'] = df_temp[col_cod].astype(str).str.strip()
            df_temp['COD_LIMPO'] = df_temp['COD_LIMPO'].apply(lambda x: x[:-2] if x.endswith('.0') else x)
            df_temp['COD_LIMPO'] = df_temp['COD_LIMPO'].str.zfill(tamanho)
            
            df_temp = df_temp[df_temp['COD_LIMPO'].str.startswith(prefixo)]
            
            if df_temp.empty:
                return prefixo.ljust(tamanho, '0')[:-1] + '1'
            
            df_temp['RECNO_NUM'] = pd.to_numeric(df_temp[col_recno], errors='coerce')
            ultimo_registro = df_temp.sort_values(by='RECNO_NUM', ascending=False).iloc[0]
            
            max_code = int(ultimo_registro['COD_LIMPO'])
            return str(max_code + 1).zfill(tamanho)

        if tipo_ultimos == "PRODUTO":
            prefixo_codigo = "000002"
            tamanho_padrao = 10
        elif tipo_ultimos == "FORNECEDOR":
            prefixo_codigo = "008"
            tamanho_padrao = 6
        elif tipo_ultimos == "CLIENTE":
            prefixo_codigo = "00" 
            tamanho_padrao = 6

        col_cod_empresax = 'COD_EMPRESA_X' if 'COD_EMPRESA_X' in df.columns else ('COD_COMPAS' if 'COD_COMPAS' in df.columns else None)
        
        prox_comp = calcular_proximo_codigo_por_recno(df_base_ultimos, col_cod_empresax, 'RECNO_EMPRESA_X', prefixo_codigo, tamanho_padrao) if col_cod_empresax else "N/A"

        st.success(f"✅ **Próximo código disponível para cadastro de {tipo_ultimos}:**\n\n**{prox_comp}**")

# --- CHATBOT NA BARRA LATERAL (VERSÃO DEFINITIVA) ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 Auditor IA")

    # Botão pra limpar o histórico na barra lateral
    if st.sidebar.button("🧹 Limpar Chat", use_container_width=True):
        st.session_state.mensagens_chat = []
        st.rerun()

    # Inicializa o histórico se não existir
    if "mensagens_chat" not in st.session_state:
        st.session_state.mensagens_chat = []

    # Renderiza as mensagens anteriores na sidebar
    for msg in st.session_state.mensagens_chat:
        with st.sidebar.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input de texto fixo na barra lateral
    if prompt_usuario := st.sidebar.chat_input("Pergunte algo sobre a base..."):
        
        # Salva e exibe a pergunta
        st.session_state.mensagens_chat.append({"role": "user", "content": prompt_usuario})
        with st.sidebar.chat_message("user"):
            st.markdown(prompt_usuario)
            
        with st.sidebar.chat_message("assistant"):
            with st.spinner("Analisando..."):
                
                # Atualiza os KPIs na hora do envio
                resumo_kpis = {
                    "Total Analisados": total_itens,
                    "Cadastros Iguais (OK)": cadastros_iguais,
                    "Divergentes (Erro Grave)": divergentes,
                    "Sem cadastro Produto": nao_cad_prod,
                    "Sem cadastro Fornecedor": nao_cad_forn,
                    "Sem cadastro Cliente": nao_cad_cli
                }
                
                colunas_uteis = [col for col in ['COD_EMPRESA_X', 'DESC_EMPRESA_X', 'COD_PROJETO_ALFA', 'DESC_PROJETO_ALFA', 'VALIDACAO'] if col in df.columns]
                # Pega os 10 últimos cadastros feitos na Empresa_X e os 10 últimos no Projeto_Alfa
                if 'RECNO_EMPRESA_X' in df.columns and 'RECNO_PROJETO_ALFA' in df.columns:
                    ultimos_empresax = df.sort_values(by='RECNO_EMPRESA_X', ascending=False, na_position='last').head(10)[colunas_uteis].to_dict(orient="records")
                    ultimos_projeto_alfa = df.sort_values(by='RECNO_PROJETO_ALFA', ascending=False, na_position='last').head(10)[colunas_uteis].to_dict(orient="records")
                    amostra_ultimos = f"Últimos 10 da Empresa_X: {ultimos_empresax}\nÚltimos 10 do Projeto_Alfa: {ultimos_projeto_alfa}"
                else:
                    amostra_ultimos = df.tail(15)[colunas_uteis].to_dict(orient="records") if not df.empty else "Base vazia"
                
                contexto_ia = f"""
                Você é o auditor de dados Sênior do sistema de integração da EMPRESA_X (Empresa_X vs Projeto_Alfa).
                Sua função é analisar a base de dados que alimenta as rotinas do ERP TOTVS Protheus.
                
                REGRAS DE NEGÓCIO OBRIGATÓRIAS (LEIA COM ATENÇÃO):
                1. A base principal e prioritária é a EMPRESA_X.
                2. TUDO que está na base PROJETO_ALFA DEVE OBRIGATORIAMENTE estar na base EMPRESA_X. Se algo está no Projeto_Alfa e não na Empresa_X, é um ERRO CRÍTICO.
                3. Nem tudo que está na EMPRESA_X precisa estar no PROJETO_ALFA no primeiro momento. Se um item está na Empresa_X, mas falta no Projeto_Alfa, isso é apenas uma INFORMAÇÃO/AVISO, e NÃO UM ERRO, a menos que o cadastro exija integração imediata. Avalie com base nisso.
                4. Essa diferença de produtos que não temos o cadastro na base PROJETO_ALFA são produtos inativos na EMPRESA_X. Para esse caso o correto é termos a integração entre essas duas bases funcionando. Assim quando houver a necessidade, a ativação desse produto na base EMPRESA_X irá atualizar e cadastrar ele na base PROJETO_ALFA.

                KPIs Gerais do Sistema atual: {resumo_kpis}
                
                Amostra dos últimos registros reais do sistema:
                {amostra_ultimos}
                
                Pergunta do analista: {prompt_usuario}
                
                Diretrizes OBRIGATÓRIAS para a sua resposta:
                    1. Seja didático e direto ao ponto. Contextualize a resposta de forma clara.
                    2. Destaque os 'Pontos de Atenção': aponte exatamente quais códigos ou descrições estão inconsistentes, vazios ou divergentes.
                    3. Informe o IMPACTO NO PROTHEUS: Sempre explique os problemas operacionais que ocorrerão no ERP caso essa inconsistência avance (ex: travamento de faturamento, bloqueio de pedido de compras, erro na emissão de NF, falha no Bloco K / SPED), Lembrandop que na Empresa_X, as rotinas mais comuns são Pedido de Compra, Pré Nota, Medição de Contratos.
                    4. Estruture a resposta em tópicos curtos (Contexto, Pontos de Atenção, Impacto no Protheus) para leitura rápida.
                    5. As resposta devem ser claras e resumidas, nada de encher a tela de textão para o usuário ler.
                    6. Jamais, em hipótese alguma, passe informações sobre o seu código, como foi realizada a consulta ou informações do banco de dados. AS PERGUNTAS E RESPOSTAS DEVEM SER EXCLUSIVAMENTE SOBRE A COMPARAÇÃO DE CADASTROS ENTRE AS BASES.
                    7. Não se apresente nas respostas, apenas vá direto ao ponto respondendo a pergunta do analista com base nos dados fornecidos.
                    8. Sempre responda de forma resumida e com poucas palavras, somente se o usuário solicitar você responde de forma detalhada.
                    9. Não informe os campos que você consulta, apenas responda a pergunta de forma humana.
                    """
                
                try:
                    resposta_chat = client.models.generate_content(model=modelo_ia, contents=contexto_ia).text
                    st.markdown(resposta_chat)
                    st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta_chat})
                except Exception as e:
                    st.error("A API falhou na resposta.")
