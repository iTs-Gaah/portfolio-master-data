import streamlit as st
import pandas as pd
import io
import re
import os
import glob
import json
import unicodedata

# Caminho da planilha hospedada no OneDrive (compartilhada com a gestão)
import sys
import os
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from onedrive_downloader import download_excel_from_onedrive, list_onedrive_folder, download_json_from_onedrive

PASTA_BASE_ONEDRIVE = "Administrativo/Qualidade/Área de Cadastros/Painel Gestão de Cadastros/Parceiro_Y"

def encontrar_planilha_onedrive():
    try:
        local_dir = "/app/data"
        os.makedirs(local_dir, exist_ok=True)
        
        # 1. Procurar Planilha Excel dinamicamente
        planilha_nome = None
        planilha_path = None
        try:
            arquivos_base = list_onedrive_folder(PASTA_BASE_ONEDRIVE)
            for item in arquivos_base:
                nome = item.get("name", "")
                if nome.startswith("FATURAMENTO EMPRESA_01") and (nome.endswith(".xls") or nome.endswith(".xlsx")):
                    planilha_nome = nome
                    planilha_path = f"{PASTA_BASE_ONEDRIVE}/{nome}"
                    break
        except Exception as e:
            print("Erro ao listar pasta base OneDrive:", e)

        if not planilha_nome:
            return None

        # 1.1 Download Planilha Excel
        try:
            arquivo_excel = download_excel_from_onedrive(planilha_path)
            local_path = os.path.join(local_dir, planilha_nome)
            with open(local_path, "wb") as f:
                f.write(arquivo_excel.getvalue())
        except Exception as e:
            print("Erro ao baixar planilha:", e)
            return None
            
        # 2. Download JSON de Ajustes (raiz)
        try:
            arquivo_json = download_json_from_onedrive(f"{PASTA_BASE_ONEDRIVE}/ajustes_painel.json")
            if arquivo_json:
                json_path = os.path.join(local_dir, "ajustes_painel.json")
                with open(json_path, "wb") as f:
                    f.write(arquivo_json.getvalue())
        except Exception:
            pass # Pode não existir ainda
            
        # 3. Download arquivos do Histórico
        try:
            local_hist = os.path.join(local_dir, "Histórico")
            os.makedirs(local_hist, exist_ok=True)
            arquivos_hist = list_onedrive_folder(f"{PASTA_BASE_ONEDRIVE}/Histórico")
            metadata_hist = {}
            for item in arquivos_hist:
                nome = item.get("name")
                if nome and (nome.endswith('.json') or nome.endswith('.xls') or nome.endswith('.xlsx')):
                    metadata_hist[nome] = item.get("lastModifiedDateTime")
                    try:
                        arq_data = download_excel_from_onedrive(f"{PASTA_BASE_ONEDRIVE}/Histórico/{nome}")
                        with open(os.path.join(local_hist, nome), "wb") as f:
                            f.write(arq_data.getvalue())
                    except Exception:
                        pass
            with open(os.path.join(local_hist, "metadata.json"), "w", encoding="utf-8") as fm:
                json.dump(metadata_hist, fm)
        except Exception:
            pass
            
        return local_path
    except Exception:
        return None

# ===== PERSISTÊNCIA COMPARTILHADA DOS AJUSTES =====
# As alterações feitas no painel (alocações, exclusões, descontos, rateios) são gravadas
# num arquivo JSON dentro da MESMA pasta do OneDrive, para que outra pessoa (ex.: a gestora)
# visualize exatamente os mesmos ajustes ao abrir o painel.
_CHAVES_AJUSTES = ['alocacoes_manuais', 'linhas_excluidas', 'unidades_excluidas',
                   'descontos_unidades', 'rateio_psico']

def caminho_ajustes(arquivo_fonte):
    """Caminho do JSON de ajustes, ao lado da planilha (apenas quando a fonte é o OneDrive)."""
    if not arquivo_fonte or not isinstance(arquivo_fonte, str):
        return None
    return os.path.join(os.path.dirname(arquivo_fonte), 'ajustes_painel.json')

def carregar_ajustes(arquivo_fonte, file_id):
    """Carrega os ajustes salvos para ESTA planilha (mesmo file_id). Retorna True se carregou."""
    p = caminho_ajustes(arquivo_fonte)
    if not p or not os.path.exists(p):
        return False
    try:
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return False
    # Só aplica se os ajustes pertencem à mesma planilha, exceto no OneDrive, 
    # onde o ajustes_painel.json da raiz é sempre a fonte da verdade para o mês ativo.
    saved_id = str(data.get('file_id', ''))
    if saved_id != str(file_id) and not str(file_id).startswith('onedrive::'):
        return False
    st.session_state['alocacoes_manuais'] = data.get('alocacoes_manuais', {})
    st.session_state['linhas_excluidas'] = set(data.get('linhas_excluidas', []))
    st.session_state['unidades_excluidas'] = set(data.get('unidades_excluidas', []))
    st.session_state['descontos_unidades'] = data.get('descontos_unidades', {})
    st.session_state['rateio_psico'] = data.get('rateio_psico', {})
    return True

def _serializar_ajustes(file_id):
    return json.dumps({
        'file_id': file_id,
        'alocacoes_manuais': st.session_state.get('alocacoes_manuais', {}),
        'linhas_excluidas': sorted(st.session_state.get('linhas_excluidas', set())),
        'unidades_excluidas': sorted(st.session_state.get('unidades_excluidas', set())),
        'descontos_unidades': st.session_state.get('descontos_unidades', {}),
        'rateio_psico': st.session_state.get('rateio_psico', {}),
        'resumo_snapshot': st.session_state.get('ultimo_resumo_snapshot', {})
    }, ensure_ascii=False, sort_keys=True)

def salvar_ajustes(arquivo_fonte, file_id):
    """Grava os ajustes localmente e no OneDrive. Só escreve quando houve mudança."""
    p = caminho_ajustes(arquivo_fonte)
    if not p:
        return
    blob = _serializar_ajustes(file_id)
    if st.session_state.get('_ajustes_blob') == blob:
        return  # nada mudou desde a última gravação
    try:
        with open(p, 'w', encoding='utf-8') as f:
            f.write(blob)
            
        # Upload para o OneDrive raiz
        try:
            from onedrive_downloader import upload_excel_to_onedrive
            upload_excel_to_onedrive(f"{PASTA_BASE_ONEDRIVE}/ajustes_painel.json", blob.encode('utf-8'))
        except Exception as e:
            print("Erro upload ajustes_painel.json:", e)
            
        # --- Cópia para o histórico de meses (Outros Faturamentos) ---
        if isinstance(arquivo_fonte, str):
            nome_base = os.path.basename(arquivo_fonte)
            nome_sem_ext = os.path.splitext(nome_base)[0]
            pasta_base = os.path.dirname(arquivo_fonte)
            pasta_hist = os.path.join(pasta_base, 'Histórico')
            os.makedirs(pasta_hist, exist_ok=True)
            # Formato: ajustes_hist_NomeDaPlanilha.json
            nome_arq_hist = f"ajustes_hist_{nome_sem_ext}.json"
            p_hist = os.path.join(pasta_hist, nome_arq_hist)
            with open(p_hist, 'w', encoding='utf-8') as f_hist:
                f_hist.write(blob)
                
            # Upload para o OneDrive no Histórico
            try:
                from onedrive_downloader import upload_excel_to_onedrive
                upload_excel_to_onedrive(f"{PASTA_BASE_ONEDRIVE}/Histórico/{nome_arq_hist}", blob.encode('utf-8'))
            except Exception as e:
                print("Erro upload historico:", e)
        # -----------------------------------------------------------
        
        st.session_state['_ajustes_blob'] = blob
    except Exception:
        pass


# ===== CONTROLE DE ACESSO =====
import auth

auth.exigir_login(
    painel_nome="Parceiro_Y",
    titulo_painel="Faturamento Parceiro_Y",
    subtitulo="EMPRESA_01 · Gestão de Faturamento de Saúde Ocupacional",
    icone="🏥"
)

def limpar_string(col):
    if isinstance(col, pd.Series):
        return col.astype(str).str.strip().str.upper()
    return str(col).strip().upper()

def limpar_moeda(val):
    val = str(val).upper().replace('R$', '').strip()
    if ',' in val and '.' in val:
        val = val.replace('.', '').replace(',', '.')
    elif ',' in val:
        val = val.replace(',', '.')
    return val

def formatar_moeda(valor):
    try:
        val = float(valor)
    except (ValueError, TypeError):
        return "R$ 0,00"
    if pd.isna(val):
        return "R$ 0,00"
    sinal = "-" if val < 0 else ""
    formatted = f"{abs(val):,.2f}"
    trans = formatted.maketrans({',': '.', '.': ','})
    return f"{sinal}R$ {formatted.translate(trans)}"

def _norm_txt(s):
    """Normaliza para comparação: maiúsculas, sem acentos e sem espaços nas pontas."""
    s = str(s).strip().upper()
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')

# EMPRESA (coluna EMPRESA da aba CTT) que CADA unidade deve ter nos seus centros de custo.
# Se o CC informado tiver EMPRESA diferente da esperada para a unidade, a linha é destacada.
EMPRESA_ESPERADA_POR_UNIDADE = {
    'EMPRESA_MATRIZ': '01 - EMPRESA_01 DO BRASIL',
    'CONSORCIO_BETA': '07 - EMPRESA_01 DO BRASIL',
    'CONSORCIO_DELTA': '10 - CONSORCIO PROJETO_ALFA',
}

def calcular_divergencia(row):
    # Comparar Unidades (cadastro RM x fatura/planilha) — regra original preservada
    uni_cad = str(row.get('Unidade Cadastro RM', '')).strip().upper()
    uni_orig = str(row.get('Unidade Original FAT', '')).strip().upper()
    uni_diff = (uni_cad != uni_orig) and (uni_cad != '') and (uni_orig != '') and (uni_cad != 'NÃO CADASTRADO') and (uni_orig != 'UNIDADE GERAL')

    # Regra por unidade: a EMPRESA (CTT) do CC precisa bater com a empresa esperada da unidade
    unidade_n = _norm_txt(row.get('Unidade Alocada', ''))
    emp_ctt_n = _norm_txt(row.get('Empresa CTT', ''))
    empresa_diff = False
    for chave, esperado in EMPRESA_ESPERADA_POR_UNIDADE.items():
        if chave in unidade_n:  # casa nome puro ou no formato 'cód - Empresa - Filial'
            if emp_ctt_n and emp_ctt_n != _norm_txt(esperado):
                empresa_diff = True
            break

    # Comparar Centro de Custo (cadastro RM x planilha de faturamento)
    # Obs.: 'Centro de Custo' (RM) é o CC codificado e 'CC Planilha' é a seção operacional —
    # taxonomias diferentes, então o sinal acionável é a AUSÊNCIA de CC (SEM CC) em qualquer lado.
    def _cc_vazio(v):
        s = str(v).strip().upper().replace('.0', '')
        return s in ('', 'NAN', 'NONE', 'SEM CC', 'NÃO CADASTRADO', 'NAO CADASTRADO', 'NÃO INFORMADO', 'NAO INFORMADO')
    cc_sem = _cc_vazio(row.get('Centro de Custo', '')) or _cc_vazio(row.get('CC Planilha', ''))

    issues = []
    if empresa_diff or uni_diff:
        issues.append("🏢 Unidade Divergente")
    if cc_sem:
        issues.append("🏷️ Sem Centro de Custo")

    if issues:
        return " · ".join(issues)
    return "✅ OK"

def processar_faturamento_dados(df_exames, df_vidas, df_faltas, ajustes):
    lista_consolidadas = []
    if not df_exames.empty:
        for idx, row in df_exames.iterrows():
            sit = row.get('Situação_Fatura')
            lista_consolidadas.append({
                'ID_Linha': f"EXAME_{idx}",
                'Tipo de Custo': f"Exame - {row.get('Tipo', 'N/A')}",
                'Nome': row.get('Nome', 'Desconhecido'),
                'Status': str(sit).strip() if pd.notna(sit) and str(sit).strip() not in ('', 'nan', 'NAN') else 'NÃO INFORMADO',
                'Detalhe': row.get('Exame', ''),
                'Centro de Custo': row.get('Centro de custo', ''),
                'CC Planilha': row.get('CC Planilha', 'SEM CC'),
                'Unidade Original FAT': row.get('UNIDADE', 'UNIDADE GERAL'),
                'Unidade Cadastro RM': row.get('Unidade Cadastro RM', 'NÃO LOCALIZADO'),
                'Departamento RM': row.get('Departamento RM', 'NÃO INFORMADO'),
                'Empresa CTT': row.get('Empresa CTT', ''),
                'Filial CTT': row.get('Filial CTT', ''),
                'Unidade Listagem': row.get('Unidade Listagem', ''),
                'Valor (R$)': float(row.get('Vl.Cobrar R$', 0))
            })

    if not df_vidas.empty:
        for idx, row in df_vidas.iterrows():
            detalhe = row.get('Cargo', row.get('Função', 'Vida Ativa'))
            sit = row.get('Situação')
            lista_consolidadas.append({
                'ID_Linha': f"VIDA_{idx}",
                'Tipo de Custo': 'Vida Ativa',
                'Nome': row.get('Nome', 'Desconhecido'),
                'Status': str(sit).strip() if pd.notna(sit) and str(sit).strip() not in ('', 'nan', 'NAN') else 'NÃO INFORMADO',
                'Detalhe': detalhe,
                'Centro de Custo': row.get('Centro de custo', ''),
                'CC Planilha': row.get('Centro de custo', ''),
                'Unidade Original FAT': row.get('UNIDADE', 'UNIDADE GERAL'),
                'Unidade Cadastro RM': row.get('Unidade Cadastro RM', 'NÃO LOCALIZADO'),
                'Departamento RM': row.get('Departamento RM', 'NÃO INFORMADO'),
                'Empresa CTT': row.get('Empresa CTT', ''),
                'Filial CTT': row.get('Filial CTT', ''),
                'Unidade Listagem': row.get('Unidade Listagem', ''),
                'Valor (R$)': 7.85
            })

    if not df_faltas.empty:
        for idx, row in df_faltas.iterrows():
            sit = row.get('Situação')
            lista_consolidadas.append({
                'ID_Linha': f"FALTA_{idx}",
                'Tipo de Custo': 'Falta',
                'Nome': row.get('Nome', 'Desconhecido'),
                'Status': str(sit).strip() if pd.notna(sit) and str(sit).strip() not in ('', 'nan', 'NAN') else 'NÃO INFORMADO',
                'Detalhe': str(row.get('Data_Falta', '')) + " " + str(row.get('Detalhe', '')),
                'Centro de Custo': row.get('Centro de custo', ''),
                'CC Planilha': row.get('Centro de custo', ''),
                'Unidade Original FAT': row.get('UNIDADE', 'UNIDADE GERAL'),
                'Unidade Cadastro RM': row.get('Unidade Cadastro RM', 'NÃO LOCALIZADO'),
                'Departamento RM': row.get('Departamento RM', 'NÃO INFORMADO'),
                'Empresa CTT': row.get('Empresa CTT', ''),
                'Filial CTT': row.get('Filial CTT', ''),
                'Unidade Listagem': row.get('Unidade Listagem', ''),
                'Valor (R$)': float(row.get('Valor_Falta', 0))
            })

    def get_aloc_unidade(id_linha, default_val):
        val = ajustes.get('alocacoes_manuais', {}).get(id_linha)
        if isinstance(val, dict): return val.get('Unidade Alocada', default_val)
        elif isinstance(val, str): return val
        return default_val

    def get_aloc_cc(id_linha, default_val):
        val = ajustes.get('alocacoes_manuais', {}).get(id_linha)
        if isinstance(val, dict): return val.get('CC Alocado', default_val)
        return default_val

    def _eh_psico(linha):
        return ('PSICOSSOCIAL' in str(linha.get('Tipo de Custo', '')).upper()
                or 'PSICOSSOCIAL' in str(linha.get('Detalhe', '')).upper())

    def _unidade_alocada_linha(linha):
        return get_aloc_unidade(linha.get('ID_Linha'), linha.get('Unidade Original FAT'))

    rateio_psico = ajustes.get('rateio_psico', {})
    if rateio_psico:
        novas_linhas_psico = []
        for unidade_rt, ccs_rt in rateio_psico.items():
            ccs_validos = [c for c in (ccs_rt or []) if c and str(c).strip()]
            if not ccs_validos:
                continue
            psico_rows = [l for l in lista_consolidadas
                          if _eh_psico(l)
                          and (_unidade_alocada_linha(l) == unidade_rt
                               or l.get('Unidade Original FAT') == unidade_rt)]
            if not psico_rows:
                continue
            total_psico_uni = sum(float(l.get('Valor (R$)', 0)) for l in psico_rows)
            unidade_base = _unidade_alocada_linha(psico_rows[0])
            for l in psico_rows:
                lista_consolidadas.remove(l)
            valor_cada = total_psico_uni / len(ccs_validos)
            for i, cc in enumerate(ccs_validos):
                base = dict(psico_rows[0])
                base['ID_Linha'] = f"PSICO_{unidade_rt}_{i}"
                base['Nome'] = 'PSICOSSOCIAL'
                base['Departamento RM'] = 'PSICOSSOCIAL'
                base['Tipo de Custo'] = 'Exame - PSICOSSOCIAL'
                base['Detalhe'] = 'PSICOSSOCIAL'
                base['Centro de Custo'] = cc
                base['CC Planilha'] = cc
                base['Unidade Original FAT'] = unidade_base
                base['Valor (R$)'] = valor_cada
                novas_linhas_psico.append(base)
        lista_consolidadas.extend(novas_linhas_psico)

    df_consolidado = pd.DataFrame(lista_consolidadas)
    if not df_consolidado.empty:
        df_consolidado['Unidade Alocada'] = df_consolidado.apply(
            lambda r: get_aloc_unidade(r['ID_Linha'], r['Unidade Original FAT']), axis=1
        )
        df_consolidado['CC Alocado'] = df_consolidado.apply(
            lambda r: get_aloc_cc(r['ID_Linha'], r['Centro de Custo']), axis=1
        )
        
        cc_to_depto = {}
        for df_temp in [df_exames, df_vidas, df_faltas]:
            if not df_temp.empty and 'Centro de custo' in df_temp.columns and 'Departamento RM' in df_temp.columns:
                for _, row_temp in df_temp[['Centro de custo', 'Departamento RM']].dropna().drop_duplicates().iterrows():
                    c_custo = str(row_temp['Centro de custo']).strip()
                    dep = str(row_temp['Departamento RM']).strip()
                    if c_custo and dep and dep.upper() not in ('NÃO INFORMADO', 'NÃO MAPEADO', 'NAN', 'NONE', ''):
                        cc_to_depto[c_custo] = dep
        
        def atualizar_depto(r):
            cc_alocado = str(r.get('CC Alocado', '')).strip()
            if cc_alocado and cc_alocado in cc_to_depto:
                return cc_to_depto[cc_alocado]
            return r.get('Departamento RM', 'NÃO INFORMADO')

        df_consolidado['Departamento RM'] = df_consolidado.apply(atualizar_depto, axis=1)
        df_consolidado['Divergência'] = df_consolidado.apply(calcular_divergencia, axis=1)
    else:
        df_consolidado = pd.DataFrame(columns=['ID_Linha', 'Tipo de Custo', 'Nome', 'Status', 'Detalhe', 'Centro de Custo', 'CC Planilha', 'CC Alocado', 'Unidade Original FAT', 'Unidade Cadastro RM', 'Departamento RM', 'Empresa CTT', 'Filial CTT', 'Unidade Listagem', 'Unidade Alocada', 'Valor (R$)', 'Divergência'])

    _unidades_set = set(df_consolidado['Unidade Alocada'].unique())
    _unidades_set.update(df_consolidado['Unidade Original FAT'].unique())
    _unidades_set = {u for u in _unidades_set if u and str(u).upper() not in ('', 'NAN', 'NONE')}
    unidades_reais = sorted(_unidades_set)
    
    _cc_set = set(df_consolidado['CC Alocado'].unique())
    _cc_set.update(df_consolidado['Centro de Custo'].unique())
    _cc_set = {c for c in _cc_set if c and str(c).upper() not in ('', 'NAN', 'NONE')}
    lista_cc = sorted(_cc_set)

    dados_resumo = []
    linhas_excluidas = set(ajustes.get('linhas_excluidas', []))
    for u in unidades_reais:
        df_u = df_consolidado[(df_consolidado['Unidade Alocada'] == u) & (~df_consolidado['ID_Linha'].isin(linhas_excluidas))]

        mask_psico_u = (df_u['Tipo de Custo'].str.upper().str.contains('PSICOSSOCIAL', na=False) |
                        df_u['Detalhe'].str.upper().str.contains('PSICOSSOCIAL', na=False))
        mask_exame_u = df_u['Tipo de Custo'].str.contains('Exame', na=False) & ~mask_psico_u

        q_ex = len(df_u[mask_exame_u])
        v_ex = df_u[mask_exame_u]['Valor (R$)'].sum()

        q_ps = len(df_u[mask_psico_u])
        v_ps = df_u[mask_psico_u]['Valor (R$)'].sum()

        df_vi_u = df_u[df_u['Tipo de Custo'] == 'Vida Ativa']
        q_vi = len(df_vi_u)
        v_vi = df_vi_u['Valor (R$)'].sum()

        _cont_vi = df_vi_u['Nome'].apply(_norm_txt).value_counts()
        q_vi_dup = int((_cont_vi > 1).sum())
        q_vi_exc = int((_cont_vi[_cont_vi > 1] - 1).sum()) if q_vi_dup else 0

        q_fa = len(df_u[df_u['Tipo de Custo'] == 'Falta'])
        v_fa = df_u[df_u['Tipo de Custo'] == 'Falta']['Valor (R$)'].sum()

        v_tot = v_ex + v_ps + v_vi + v_fa

        dados_resumo.append({
            'Unidade': u,
            'Qtd Exames': q_ex,
            'Exames (R$)': v_ex,
            'Qtd Psicossocial': q_ps,
            'Psicossocial (R$)': v_ps,
            'Qtd Vidas': q_vi,
            'Vidas Ativas (R$)': v_vi,
            'Vidas Duplicadas': q_vi_dup,
            'Vidas Excedentes': q_vi_exc,
            'Qtd Faltas': q_fa,
            'Faltas (R$)': v_fa,
            'Total Geral (R$)': v_tot
        })
    df_resumo_unidades = pd.DataFrame(dados_resumo)

    dados_resumo_parceiro_y = []
    for u in unidades_reais:
        df_u = df_consolidado[df_consolidado['Unidade Original FAT'] == u]
        mask_psico_u = (df_u['Tipo de Custo'].str.upper().str.contains('PSICOSSOCIAL', na=False) |
                        df_u['Detalhe'].str.upper().str.contains('PSICOSSOCIAL', na=False))
        mask_exame_u = df_u['Tipo de Custo'].str.contains('Exame', na=False) & ~mask_psico_u

        q_ex = len(df_u[mask_exame_u])
        v_ex = df_u[mask_exame_u]['Valor (R$)'].sum()

        q_ps = len(df_u[mask_psico_u])
        v_ps = df_u[mask_psico_u]['Valor (R$)'].sum()

        df_vi_u = df_u[df_u['Tipo de Custo'] == 'Vida Ativa']
        q_vi = len(df_vi_u)
        v_vi = df_vi_u['Valor (R$)'].sum()

        _cont_vi = df_vi_u['Nome'].apply(_norm_txt).value_counts()
        q_vi_dup = int((_cont_vi > 1).sum())
        q_vi_exc = int((_cont_vi[_cont_vi > 1] - 1).sum()) if q_vi_dup else 0

        q_fa = len(df_u[df_u['Tipo de Custo'] == 'Falta'])
        v_fa = df_u[df_u['Tipo de Custo'] == 'Falta']['Valor (R$)'].sum()

        v_tot = v_ex + v_ps + v_vi + v_fa

        dados_resumo_parceiro_y.append({
            'Unidade': u,
            'Qtd Exames': q_ex,
            'Exames (R$)': v_ex,
            'Qtd Psicossocial': q_ps,
            'Psicossocial (R$)': v_ps,
            'Qtd Vidas': q_vi,
            'Vidas Ativas (R$)': v_vi,
            'Qtd Faltas': q_fa,
            'Faltas (R$)': v_fa,
            'Total Geral (R$)': v_tot
        })
    df_resumo_parceiro_y = pd.DataFrame(dados_resumo_parceiro_y)

    return df_consolidado, unidades_reais, lista_cc, df_resumo_unidades, df_resumo_parceiro_y

def carregar_dados(arquivo):
    nome_arq = getattr(arquivo, 'name', None) or str(arquivo)
    ext = nome_arq.split('.')[-1].lower()
    motor = 'openpyxl' if ext == 'xlsx' else 'xlrd'
    
    try:
        xls = pd.ExcelFile(arquivo, engine=motor)
    except PermissionError:
        st.error(f"❌ O arquivo **{nome_arq}** está aberto em outro programa (provavelmente no Excel).")
        st.info("💡 **Solução:** Feche o arquivo no Excel e atualize a página para continuar.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro ao ler o arquivo {nome_arq}: {e}")
        st.stop()
    
    # Identificar aba da Fatura
    sheet_fat = next((s for s in xls.sheet_names if s.upper() in ['RELATÓRIO DE FATURA', 'FAT']), None)
    if not sheet_fat:
        st.error("❌ Aba de Fatura ('Relatório de Fatura' ou 'FAT') não encontrada na planilha.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {'ausentes': {}, 'ausentes_lista': [], 'cc_inativos': {}, 'cc_inativos_cods': set()}, {}
        
    df_fatura_raw = pd.read_excel(xls, sheet_name=sheet_fat, header=None)
    
    # Extrair a coluna UNIDADE para cada bloco de dados com base nas linhas de cabeçalho de unidade
    def extrair_unidade(val):
        val_str = str(val).strip()
        if val_str.upper().startswith('UNIDADE:'):
            return val_str[8:].strip().upper()
        return None
        
    df_fatura_raw['UNIDADE'] = df_fatura_raw[0].apply(extrair_unidade).ffill().fillna('UNIDADE GERAL')
    
    # ===== EXTRAÇÃO DE PSICOSSOCIAL (DO CABEÇALHO DA FATURA) =====
    registros_psico = []
    mask_psico_row = df_fatura_raw.apply(lambda r: r.astype(str).str.contains('PSICOSSOCIAL', case=False, na=False).any(), axis=1)
    if mask_psico_row.any():
        for idx_row, row in df_fatura_raw[mask_psico_row].iterrows():
            valores_numericos = []
            for val in row.drop('UNIDADE', errors='ignore'):
                if pd.notna(val) and str(val).strip() != '':
                    v_limpo = limpar_moeda(str(val))
                    try:
                        n = float(v_limpo)
                        if n > 0:
                            valores_numericos.append(n)
                    except ValueError:
                        pass
            if valores_numericos:
                valor_psico = valores_numericos[-1]
                uni_psico = row['UNIDADE']
                if valor_psico > 0:
                    registros_psico.append({
                        'Nome': 'SERVICO PSICOSSOCIAL',
                        'Exame': 'PSICOSSOCIAL',
                        'Tipo': 'PSICOSSOCIAL',
                        'UNIDADE': uni_psico,
                        'Vl.Cobrar R$': valor_psico,
                        'Situação_Fatura': 'ATIVO',
                        'CC Planilha': 'SEM CC'
                    })
    
    # 1. Processamento da Fatura (Exames)
    # Procurar a linha de cabeçalho contendo 'Setor' e 'Nome'
    mask_h = df_fatura_raw.apply(lambda r: r.astype(str).str.contains('Setor', case=False, na=False).any() and r.astype(str).str.contains('Nome', case=False, na=False).any(), axis=1)
    if not mask_h.any():
        st.error("❌ Cabeçalho da fatura não localizado.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {'ausentes': {}, 'ausentes_lista': [], 'cc_inativos': {}, 'cc_inativos_cods': set()}, {}
        
    idx_h = df_fatura_raw[mask_h].index[0]
    df_fat = df_fatura_raw.iloc[idx_h+1:].copy()
    
    # Configurar os nomes das colunas preservando a coluna UNIDADE no final
    cols = df_fatura_raw.iloc[idx_h].astype(str).str.strip().tolist()
    cols[-1] = 'UNIDADE'
    
    seen = {}
    for i, c in enumerate(cols):
        if c in seen:
            seen[c] += 1
            cols[i] = f"{c}_{seen[c]}"
        else:
            seen[c] = 0
            
    df_fat.columns = cols
    
    # ===== REGRA: C CUSTO vazio → usar DESCRICAO FORM =====
    # Se a coluna de Seção/C CUSTO existir mas estiver vazia em algum registro,
    # preenche com o valor da coluna DESCRICAO FORM (quando disponível)
    col_secao = [c for c in df_fat.columns if any(x in str(c).upper() for x in ['SEÇÃO', 'SECAO', 'SETOR', 'C CUSTO', 'C.CUSTO', 'CCUSTO'])]
    col_descricao_form = [c for c in df_fat.columns if 'DESCRICAO' in str(c).upper() and 'FORM' in str(c).upper()]
    if col_secao and col_descricao_form:
        c_secao = col_secao[0]
        c_desc  = col_descricao_form[0]
        # Quando C CUSTO estiver vazio/NaN, puxa DESCRICAO FORM
        mask_vazio = df_fat[c_secao].isna() | (df_fat[c_secao].astype(str).str.strip().isin(['', 'nan', 'NAN', 'None', 'NONE']))
        df_fat.loc[mask_vazio, c_secao] = df_fat.loc[mask_vazio, c_desc]
        
    if col_secao:
        df_fat['CC Planilha'] = df_fat[col_secao[0]].fillna('SEM CC').astype(str).str.strip()
    else:
        df_fat['CC Planilha'] = 'SEM CC'

    # Ajuste dinâmico de nomes de colunas
    col_cobrar = [c for c in df_fat.columns if 'COBRAR' in str(c).upper()]
    if col_cobrar and col_cobrar[0] != 'Vl.Cobrar R$':
        df_fat = df_fat.rename(columns={col_cobrar[0]: 'Vl.Cobrar R$'})
    elif not col_cobrar:
        df_fat['Vl.Cobrar R$'] = 0
        
    col_nome = [c for c in df_fat.columns if str(c).strip().upper() == 'NOME']
    if col_nome and col_nome[0] != 'Nome':
        df_fat = df_fat.rename(columns={col_nome[0]: 'Nome'})
        
    col_exame = [c for c in df_fat.columns if str(c).strip().upper() == 'EXAME']
    if col_exame and col_exame[0] != 'Exame':
        df_fat = df_fat.rename(columns={col_exame[0]: 'Exame'})
        
    col_tipo = [c for c in df_fat.columns if str(c).strip().upper() == 'TIPO']
    if col_tipo and col_tipo[0] != 'Tipo':
        df_fat = df_fat.rename(columns={col_tipo[0]: 'Tipo'})
    elif not col_tipo:
        df_fat['Tipo'] = 'N/A'
        
    col_sit_fat = [c for c in df_fat.columns if str(c).upper().strip() in ['SITUAÇÃO', 'SITUACAO', 'STATUS', 'SITUAÇÃO FUNCIONAL', 'SITUACAO FUNCIONAL']]
    if not col_sit_fat:
        col_sit_fat = [c for c in df_fat.columns if 'SITUA' in str(c).upper() or 'STATUS' in str(c).upper()]
    if col_sit_fat and col_sit_fat[0] != 'Situação_Fatura':
        df_fat = df_fat.rename(columns={col_sit_fat[0]: 'Situação_Fatura'})
    elif col_sit_fat:
        pass
    else:
        df_fat['Situação_Fatura'] = 'NÃO INFORMADO'
        
    # Filtragem de registros válidos
    if 'Nome' in df_fat.columns and 'Exame' in df_fat.columns:
        df_fat = df_fat.dropna(subset=['Nome', 'Exame'])
    if 'Setor' in df_fat.columns:
        df_fat = df_fat[~df_fat['Setor'].astype(str).str.contains('Setor|Valor Total|Exames', case=False, na=False)]
    if 'Nome' in df_fat.columns:
        df_fat = df_fat[~df_fat['Nome'].astype(str).str.contains('Valor Total|Setor', case=False, na=False)]
        
    df_fat['Vl.Cobrar R$'] = df_fat['Vl.Cobrar R$'].apply(limpar_moeda)
    df_fat['Vl.Cobrar R$'] = pd.to_numeric(df_fat['Vl.Cobrar R$'], errors='coerce').fillna(0)
    
    # Injetar os registros de PSICOSSOCIAL encontrados
    if registros_psico:
        df_psico = pd.DataFrame(registros_psico)
        df_fat = pd.concat([df_fat, df_psico], ignore_index=True)
    
    # 2. Carregar aba CTT para validação corporativa de Centros de Custo
    # A aba CTT possui: Código do CC, EMPRESA e FILIAL — usada para redirecionar custos à Unidade correta
    mapa_ctt = {}  # { cc_codigo: { 'empresa', 'filial', 'unidade_ctt', 'desc', 'inativo' } }
    sheet_ctt = next((s for s in xls.sheet_names if s.upper() == 'CTT'), None)
    if sheet_ctt:
        df_ctt_raw = pd.read_excel(xls, sheet_name=sheet_ctt)
        # Código do CC: priorizar CTT_CUSTO/CUSTO/CODIGO, evitando casar com DESC/BLOQ
        col_ctt_cc  = ([c for c in df_ctt_raw.columns if 'CUSTO' in str(c).upper() and 'DESC' not in str(c).upper() and 'BLOQ' not in str(c).upper()]
                       or [c for c in df_ctt_raw.columns if any(x in str(c).upper() for x in ['CENTRO DE CUSTO', 'CODIGO', 'CÓDIGO', 'COD'])]
                       or [c for c in df_ctt_raw.columns if 'CTT' in str(c).upper() and 'DESC' not in str(c).upper() and 'BLOQ' not in str(c).upper()])
        col_ctt_emp = [c for c in df_ctt_raw.columns if 'EMPRESA' in str(c).upper()]
        col_ctt_fil = [c for c in df_ctt_raw.columns if 'FILIAL' in str(c).upper()]
        col_ctt_desc = [c for c in df_ctt_raw.columns if 'DESC' in str(c).upper()]  # CTT_DESC01
        col_ctt_bloq = [c for c in df_ctt_raw.columns if 'BLOQ' in str(c).upper()]  # CTT_BLOQ
        col_ctt_dtexsf = [c for c in df_ctt_raw.columns if 'DTEXSF' in str(c).upper()]
        if col_ctt_cc and col_ctt_emp and col_ctt_fil:
            df_ctt = df_ctt_raw[[col_ctt_cc[0], col_ctt_emp[0], col_ctt_fil[0]]].copy()
            df_ctt.columns = ['CC_Codigo', 'Empresa', 'Filial']
            df_ctt['Desc'] = df_ctt_raw[col_ctt_desc[0]].astype(str).str.strip() if col_ctt_desc else ''
            df_ctt['Bloq'] = df_ctt_raw[col_ctt_bloq[0]].astype(str).str.strip().str.upper() if col_ctt_bloq else ''
            if col_ctt_dtexsf:
                df_ctt['dtexsf'] = pd.to_datetime(df_ctt_raw[col_ctt_dtexsf[0]], errors='coerce')
            else:
                df_ctt['dtexsf'] = pd.NaT
            df_ctt['CC_Codigo'] = df_ctt['CC_Codigo'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df_ctt['Empresa'] = df_ctt['Empresa'].astype(str).str.strip().str.upper()
            df_ctt['Filial']  = df_ctt['Filial'].astype(str).str.strip().str.upper()
            df_ctt = df_ctt.dropna(subset=['CC_Codigo'])
            df_ctt = df_ctt[df_ctt['CC_Codigo'] != '']
            for _, row in df_ctt.iterrows():
                cc_cod = row['CC_Codigo']
                empresa = row['Empresa']
                filial = row['Filial']
                
                inativo = (row['Bloq'] == 'INATIVO')
                if not inativo and pd.notna(row['dtexsf']):
                    if row['dtexsf'].date() < pd.Timestamp.today().date():
                        inativo = True
                
                if cc_cod not in mapa_ctt:
                    mapa_ctt[cc_cod] = {
                        'empresa':     empresa,
                        'filial':      filial,
                        'unidade_ctt': empresa + ' - ' + filial,
                        'desc':        row['Desc'],
                        'inativo':     inativo,
                        'inativo_em':  []
                    }
                else:
                    if not inativo and mapa_ctt[cc_cod]['inativo']:
                        mapa_ctt[cc_cod]['empresa'] = empresa
                        mapa_ctt[cc_cod]['filial'] = filial
                        mapa_ctt[cc_cod]['unidade_ctt'] = empresa + ' - ' + filial
                        mapa_ctt[cc_cod]['inativo'] = False
                        
                if inativo and filial not in mapa_ctt[cc_cod]['inativo_em']:
                    mapa_ctt[cc_cod]['inativo_em'].append(filial)
        else:
            st.warning("⚠️ Aba 'CTT' encontrada, mas não foi possível identificar as colunas de Código, Empresa e Filial.")

    # Carregar aba Lista RM para mapear Centro de Custo e Empresa por CPF
    mapa_lista_rm = {}  # { cpf_limpo: { 'cc', 'unidade', 'nome', 'regional', 'cc_cod', 'inativo' } }
    sheet_rm = next((s for s in xls.sheet_names if 'LISTA RM' in s.upper()), None)
    if sheet_rm:
        df_rm_raw = pd.read_excel(xls, sheet_name=sheet_rm)
        col_rm_cpf = [c for c in df_rm_raw.columns if 'CPF' in str(c).upper()]
        col_rm_cc  = [c for c in df_rm_raw.columns if any(x in str(c).upper() for x in ['CENTRO DE CUSTO', 'C.CUSTO', 'C CUSTO', 'CCUSTO']) and 'NOME' not in str(c).upper() and 'SEÇÃO' not in str(c).upper() and 'SECAO' not in str(c).upper()]
        col_rm_ncc = [c for c in df_rm_raw.columns if 'SEÇÃO' in str(c).upper() or 'SECAO' in str(c).upper() or 'NOME CENTRO DE CUSTO' in str(c).upper()]
        col_rm_emp = [c for c in df_rm_raw.columns if ('COLIGADA' in str(c).upper() or 'COLGIADA' in str(c).upper()) and 'COD' not in str(c).upper()]
        if not col_rm_emp:
            col_rm_emp = [c for c in df_rm_raw.columns if 'EMPRESA' in str(c).upper()]
        col_rm_fil = [c for c in df_rm_raw.columns if 'FILIAL' in str(c).upper()]
        col_rm_nome = ([c for c in df_rm_raw.columns if str(c).strip().upper() == 'NOME']
                       or [c for c in df_rm_raw.columns if 'NOME' in str(c).upper() and 'CENTRO' not in str(c).upper() and 'CC' not in str(c).upper()])
        col_rm_reg = ([c for c in df_rm_raw.columns if 'REGIONAL' in str(c).upper()]
                      or [c for c in df_rm_raw.columns if 'SETOR' in str(c).upper()]
                      or [c for c in df_rm_raw.columns if 'DEPARTAMENTO' in str(c).upper()])
        col_rm_depto = [c for c in df_rm_raw.columns if 'DEPARTAMENTO' in str(c).upper()]
        col_rm_demissao = [c for c in df_rm_raw.columns if 'DEMIS' in str(c).upper() or 'DESLIG' in str(c).upper()]
        if col_rm_cpf or col_rm_nome:
            for _idx_rm, row_rm in df_rm_raw.iterrows():
                cpf_key = re.sub(r'\D', '', str(row_rm[col_rm_cpf[0]])) if col_rm_cpf else ''
                nome_raw = str(row_rm[col_rm_nome[0]]).strip() if col_rm_nome else ''
                # Precisa de ao menos um identificador válido (CPF ou nome)
                if not cpf_key and (not nome_raw or nome_raw.upper() in ('NAN', 'NONE')):
                    continue
                # Chave do dicionário: CPF quando houver, senão o nome normalizado
                map_key = cpf_key if cpf_key else f"NOME::{_norm_txt(nome_raw)}"
                cc_cod = str(row_rm[col_rm_cc[0]]).strip().replace('.0', '') if col_rm_cc else ''
                # Padronizar a descrição do CC pela coluna CTT_DESC01 da aba CTT
                info_ctt = mapa_ctt.get(cc_cod)
                cc_nome_rm = str(row_rm[col_rm_ncc[0]]).strip() if col_rm_ncc else ''
                if info_ctt and info_ctt.get('desc') and str(info_ctt['desc']).upper() not in ('NAN', 'NONE', ''):
                    cc_nome_padrao = str(info_ctt['desc'])
                else:
                    cc_nome_padrao = cc_nome_rm
                cc_full = (cc_cod + ' - ' + cc_nome_padrao) if cc_nome_padrao and cc_nome_padrao.upper() not in ('NAN', 'NONE', '') else cc_cod
                emp = str(row_rm[col_rm_emp[0]]).strip().upper() if col_rm_emp else ''
                fil = str(row_rm[col_rm_fil[0]]).strip().upper() if col_rm_fil else ''
                is_coligada = col_rm_emp and ('COLIGADA' in str(col_rm_emp[0]).upper() or 'COLGIADA' in str(col_rm_emp[0]).upper())
                if is_coligada:
                    unidade_rm = emp
                else:
                    unidade_rm = (emp + ' - ' + fil) if emp and fil else (emp or fil or '')
                if unidade_rm in ('EMPRESA_01 CONSÓRCIO PROJETO_ALFA', 'EMPRESA_01 CONSORCIO PROJETO_ALFA'):
                    unidade_rm = 'CONSORCIO PROJETO_ALFA'
                elif unidade_rm == 'CONSÓRCIO EMPRESA_01 EMPRESA_02':
                    unidade_rm = 'CONSORCIO_C'
                nome_rm = nome_raw if nome_raw and nome_raw.upper() not in ('NAN', 'NONE') else 'Desconhecido'
                regional_rm = str(row_rm[col_rm_reg[0]]).strip() if col_rm_reg else 'NÃO INFORMADO'
                depto_rm = str(row_rm[col_rm_depto[0]]).strip() if col_rm_depto else ''
                if not depto_rm or depto_rm.upper() in ('NAN', 'NONE'):
                    depto_rm = 'NÃO INFORMADO'
                    
                is_demitido_antigo = False
                if col_rm_demissao:
                    val_dem = row_rm[col_rm_demissao[0]]
                    if pd.notna(val_dem) and str(val_dem).strip() not in ('', 'NAN', 'NONE'):
                        try:
                            dt_dem = pd.to_datetime(val_dem, dayfirst=True)
                            if pd.notnull(dt_dem):
                                if (pd.Timestamp.today() - dt_dem).days > 30:
                                    is_demitido_antigo = True
                        except:
                            pass
                            
                mapa_lista_rm[map_key] = {
                    'cpf': cpf_key,
                    'cc': cc_full,
                    'unidade': unidade_rm,
                    'nome': nome_rm,
                    'nome_key': _norm_txt(nome_rm),
                    'regional': regional_rm,
                    'departamento': depto_rm,
                    'cc_cod': cc_cod,
                    'cc_nome': cc_nome_padrao if cc_nome_padrao and str(cc_nome_padrao).upper() not in ('NAN', 'NONE', '') else '',
                    'inativo': bool(info_ctt and info_ctt.get('inativo')),
                    'is_demitido_antigo': is_demitido_antigo,
                }
        else:
            st.warning("⚠️ Aba 'Lista RM' encontrada, mas não foi possível identificar as colunas de CPF e Nome.")

    # 3. Carregar e padronizar o RH a partir da aba 'Listagem de Funcionários'
    sheet_func = next((s for s in xls.sheet_names if s.upper() in ['LISTAGEM DE FUNCIONÁRIOS', 'FUNCIONARIOS', 'LISTAGEM DE FUNCIONARIOS']), None)
    info_rh = pd.DataFrame()
    df_func_soc = pd.DataFrame()
    
    if sheet_func:
        df_func_test = pd.read_excel(xls, sheet_name=sheet_func, nrows=2)
        if any('NOME' in str(c).upper() for c in df_func_test.columns):
            df_func_soc = pd.read_excel(xls, sheet_name=sheet_func)
        else:
            df_func_soc = pd.read_excel(xls, sheet_name=sheet_func, skiprows=1)
            
        if not df_func_soc.empty:
            # Encontrar Nome
            col_nf = [c for c in df_func_soc.columns if str(c).strip().upper() == 'NOME']
            if col_nf:
                if col_nf[0] != 'Nome':
                    df_func_soc = df_func_soc.rename(columns={col_nf[0]: 'Nome'})
                df_func_soc['Nome_Key'] = limpar_string(df_func_soc['Nome'])
            else:
                df_func_soc['Nome_Key'] = ''

            # Extrair CPF para cruzar com Lista RM
            col_cpf_func = [c for c in df_func_soc.columns if 'CPF' in str(c).upper()]
            if col_cpf_func:
                df_func_soc['CPF_Key'] = df_func_soc[col_cpf_func[0]].astype(str).apply(lambda x: re.sub(r'\D', '', x))
            else:
                df_func_soc['CPF_Key'] = ''

            # Identificar Unidade fisicamente registrada precocemente
            col_uni_func = [c for c in df_func_soc.columns if ('COLIGADA' in str(c).upper() or 'COLGIADA' in str(c).upper()) and 'COD' not in str(c).upper()]
            if not col_uni_func:
                col_uni_func = [c for c in df_func_soc.columns if str(c).strip().upper() == 'UNIDADE']
                
            if col_uni_func:
                if col_uni_func[0] != 'UNIDADE':
                    df_func_soc = df_func_soc.rename(columns={col_uni_func[0]: 'UNIDADE'})
            else:
                df_func_soc['UNIDADE'] = 'UNIDADE GERAL'
            df_func_soc['UNIDADE'] = df_func_soc['UNIDADE'].astype(str).str.strip().str.upper()
            df_func_soc['UNIDADE'] = df_func_soc['UNIDADE'].replace({
                'EMPRESA_01 CONSÓRCIO PROJETO_ALFA': 'CONSORCIO PROJETO_ALFA',
                'EMPRESA_01 CONSORCIO PROJETO_ALFA': 'CONSORCIO PROJETO_ALFA',
                'CONSÓRCIO EMPRESA_01 EMPRESA_02': 'CONSORCIO_C'
            })
                
            # Identificar Regional/Departamento
            col_regional = [c for c in df_func_soc.columns if 'REGIONAL' in str(c).upper()]
            if not col_regional:
                col_regional = [c for c in df_func_soc.columns if 'SETOR' in str(c).upper()]
            if not col_regional:
                col_regional = [c for c in df_func_soc.columns if 'DEPARTAMENTO' in str(c).upper()]
            depto_col = col_regional[0] if col_regional else None
            df_func_soc['DEPTO_Final'] = df_func_soc[depto_col].fillna('NÃO MAPEADO').astype(str) if depto_col else 'NÃO MAPEADO'
            
            # Identificar Centro de Custo (Código + Nome contido na coluna Seção)
            col_cc = [c for c in df_func_soc.columns if 'CENTRO DE CUSTO' in str(c).upper() and 'NOME' not in str(c).upper() and 'SEÇÃO' not in str(c).upper() and 'SECAO' not in str(c).upper()]
            col_ncc = [c for c in df_func_soc.columns if 'SEÇÃO' in str(c).upper() or 'SECAO' in str(c).upper() or 'NOME CENTRO DE CUSTO' in str(c).upper()]
            
            if col_cc and col_ncc:
                df_func_soc['CC_Final'] = df_func_soc[col_cc[0]].astype(str).str.replace(r'\.0$', '', regex=True) + " - " + df_func_soc[col_ncc[0]].astype(str)
            elif col_cc:
                df_func_soc['CC_Final'] = df_func_soc[col_cc[0]].astype(str).str.replace(r'\.0$', '', regex=True)
            else:
                col_any_cc = [c for c in df_func_soc.columns if 'CENTRO DE CUSTO' in str(c).upper()]
                if col_any_cc:
                    df_func_soc['CC_Final'] = df_func_soc[col_any_cc[0]].astype(str).str.replace(r'\.0$', '', regex=True)
                else:
                    df_func_soc['CC_Final'] = 'SEM CC'

            # Preservar a UNIDADE original da Listagem de Funcionários (antes do enriquecimento Lista RM)
            # Usada para validar contra a EMPRESA do CTT vinculada ao Centro de Custo
            df_func_soc['Unidade_Listagem'] = df_func_soc['UNIDADE']

            # Enriquecer CC_Final e UNIDADE com dados da Lista RM via CPF (vetorizado)
            df_func_soc['Unidade_RM_Mapped'] = 'NÃO LOCALIZADO'
            if mapa_lista_rm and 'CPF_Key' in df_func_soc.columns:
                _invalidos = ('NAN', 'NONE', '')
                cc_map  = {k: v['cc'] for k, v in mapa_lista_rm.items() if v['cc'] and v['cc'].upper() not in _invalidos}
                uni_map = {k: v['unidade'] for k, v in mapa_lista_rm.items() if v['unidade'] and v['unidade'].upper() not in _invalidos}
                df_func_soc['CC_Final'] = df_func_soc['CPF_Key'].map(cc_map).fillna(df_func_soc['CC_Final'])
                df_func_soc['Unidade_RM_Mapped'] = df_func_soc['CPF_Key'].map(uni_map).fillna('NÃO LOCALIZADO')

            # Departamento da Lista RM (por CPF) — usado no filtro dentro do card da unidade
            if mapa_lista_rm and 'CPF_Key' in df_func_soc.columns:
                depto_map = {k: v.get('departamento', '') for k, v in mapa_lista_rm.items() if v.get('departamento')}
                df_func_soc['Departamento_RM'] = df_func_soc['CPF_Key'].map(depto_map).fillna('NÃO INFORMADO')
            else:
                df_func_soc['Departamento_RM'] = 'NÃO INFORMADO'

            if 'Nome_Key' in df_func_soc.columns and not df_func_soc['Nome_Key'].empty:
                col_sit_test = [c for c in df_func_soc.columns if 'SITUA' in str(c).upper() or 'STATUS' in str(c).upper()]
                col_sit_name = None
                if col_sit_test:
                    col_sit_name = col_sit_test[0]
                    df_func_soc['_sit_sort'] = df_func_soc[col_sit_name].astype(str).str.upper()
                    df_func_soc = df_func_soc.sort_values(by=['_sit_sort'], ascending=True)
                    
                cols_extrair = ['Nome_Key', 'DEPTO_Final', 'CC_Final', 'Unidade_RM_Mapped', 'Departamento_RM', 'Unidade_Listagem']
                rename_dict = {'DEPTO_Final': 'DEPARTAMENTO', 'CC_Final': 'Centro de custo', 'Unidade_RM_Mapped': 'Unidade Cadastro RM', 'Departamento_RM': 'Departamento RM', 'Unidade_Listagem': 'Unidade Listagem'}
                if col_sit_name:
                    cols_extrair.append(col_sit_name)
                    rename_dict[col_sit_name] = 'Situação'
                    
                info_rh = df_func_soc[cols_extrair].rename(columns=rename_dict)
                info_rh = info_rh[info_rh['Nome_Key'] != ''].drop_duplicates(subset=['Nome_Key'], keep='first')
    else:
        st.warning("⚠️ Aba 'Listagem de Funcionários' não encontrada. O cruzamento de Regional e Centro de Custo não será possível.")
        
    # Mapear na fatura
    if 'Nome' in df_fat.columns:
        df_fat['Nome_Key'] = limpar_string(df_fat['Nome'])
    else:
        df_fat['Nome_Key'] = ''
        
    # Preservar a Unidade física original da fatura (de onde o exame foi realizado) antes do merge
    if 'UNIDADE' in df_fat.columns:
        df_fat['UNIDADE_Original'] = df_fat['UNIDADE']

    # Evitar sufixos _x e _y removendo colunas de depto/cc da fatura antes do merge
    cols_fat_remover = [c for c in df_fat.columns if any(x in str(c).upper() for x in ['CENTRO DE CUSTO', 'DEPARTAMENTO', 'SEÇÃO', 'SETOR', 'REGIONAL']) and c != 'CC Planilha']
    df_fat_clean = df_fat.drop(columns=cols_fat_remover, errors='ignore')
    
    if not info_rh.empty:
        fatura_final = pd.merge(df_fat_clean, info_rh, on='Nome_Key', how='left')
    else:
        fatura_final = df_fat_clean.copy()
        fatura_final['DEPARTAMENTO'] = 'NÃO MAPEADO'
        fatura_final['Centro de custo'] = 'SEM CC'

    # ===== REGRA DE ALOCAÇÃO DE CUSTOS =====
    # UNIDADE = 'Empresa - Filial' do CTT, baseada EXCLUSIVAMENTE no CC do funcionário
    # Se o CC não está na CTT, marca como não mapeado — NUNCA usa a Regional como UNIDADE
    def alocar_unidade_ctt(row):
        cc_raw = str(row.get('Centro de custo', '')).split(' - ')[0].strip().replace('.0', '')
        if mapa_ctt and cc_raw in mapa_ctt:
            return mapa_ctt[cc_raw]['unidade_ctt']  # 'Empresa - Filial'
        return 'CC NÃO MAPEADO NO CTT'

    if not fatura_final.empty:
        fatura_final['Empresa Custo Real'] = fatura_final.apply(alocar_unidade_ctt, axis=1)
        if 'UNIDADE_Original' in fatura_final.columns:
            fatura_final['UNIDADE'] = fatura_final['UNIDADE_Original']
            fatura_final = fatura_final.drop(columns=['UNIDADE_Original'], errors='ignore')
    
    # 3. Processamento de Vidas Ativas (Listagem de Funcionários)
    if not df_func_soc.empty:
        col_sit = [c for c in df_func_soc.columns if 'SITUA' in str(c).upper()]
        if col_sit and col_sit[0] != 'Situação':
            df_func_soc = df_func_soc.rename(columns={col_sit[0]: 'Situação'})
            
        # Conforme solicitado, trazer todos os funcionários da listagem sem filtrar por status,
        # mantendo a coluna de Situação/Status intacta para exibição
        vidas_final = df_func_soc.copy()
        if 'Situação' not in vidas_final.columns:
            # Procurar se há outra coluna de status
            col_st = [c for c in vidas_final.columns if 'STATUS' in str(c).upper() or 'SITUA' in str(c).upper()]
            if col_st:
                vidas_final = vidas_final.rename(columns={col_st[0]: 'Situação'})
            else:
                vidas_final['Situação'] = 'NÃO INFORMADO'
            
        # Padronizar colunas finais de Vidas
        vidas_final['DEPARTAMENTO'] = vidas_final['DEPTO_Final']
        vidas_final['Centro de custo'] = vidas_final['CC_Final']
        vidas_final['Unidade Cadastro RM'] = vidas_final.get('Unidade_RM_Mapped', 'NÃO LOCALIZADO')
        vidas_final['Departamento RM'] = vidas_final.get('Departamento_RM', 'NÃO INFORMADO')
        vidas_final['Unidade Listagem'] = vidas_final.get('Unidade_Listagem', '')

        # Aplicar mesma regra de alocação 'Empresa - Filial' (CTT) nas Vidas Ativas
        # SEM fallback para Regional — UNIDADE vem exclusivamente da aba CTT
        vidas_final['Empresa Custo Real'] = vidas_final.apply(alocar_unidade_ctt, axis=1)

        # Remover colunas extras antigas para não duplicar na exibição
        cols_remover = [c for c in vidas_final.columns if c in ['DEPTO_Final', 'CC_Final'] or any(x in str(c).upper() for x in ['CENTRO DE CUSTO', 'DEPARTAMENTO', 'SEÇÃO', 'SETOR', 'REGIONAL']) and c not in ['DEPARTAMENTO', 'Centro de custo', 'Departamento RM']]
        vidas_final = vidas_final.drop(columns=cols_remover, errors='ignore')
    else:
        vidas_final = pd.DataFrame()
        
    # 4. Processamento de Faltas (Aba Faltas)
    sheet_faltas = None
    for s in xls.sheet_names:
        if 'FALTA' in s.upper() or 'COMPROMISSO' in s.upper():
            sheet_faltas = s
            break
    faltas_final = pd.DataFrame()
    
    if sheet_faltas:
        df_faltas_raw = pd.read_excel(xls, sheet_name=sheet_faltas, header=None)
        mask_f = df_faltas_raw.apply(lambda r: r.astype(str).str.contains('Observa', case=False, na=False).any(), axis=1)
        if mask_f.any():
            idx_f = df_faltas_raw[mask_f].index[0]
            df_f = df_faltas_raw.iloc[idx_f+1:].copy()
            df_f.columns = df_faltas_raw.iloc[idx_f].astype(str).str.strip()
            
            col_obs = [c for c in df_f.columns if 'OBSERVA' in str(c).upper()]
            col_uni_f = [c for c in df_f.columns if 'NOME UNIDADE' in str(c).upper() or 'NOME UNIDAD' in str(c).upper()]
            if not col_uni_f:
                col_uni_f = [c for c in df_f.columns if 'UNIDADE' in str(c).upper() or 'UNIDAD' in str(c).upper()]
            if not col_uni_f:
                col_uni_f = [c for c in df_f.columns if 'EMPRESA' in str(c).upper()]
            col_val = [c for c in df_f.columns if 'VALOR' in str(c).upper()]
            # Tentar identificar coluna de data/competência da linha de fatura
            col_data_fat = [c for c in df_f.columns if any(x in str(c).upper() for x in ['DATA', 'COMPETENCIA', 'COMPETÊNCIA', 'FATURA'])]
            
            if col_obs and col_uni_f:
                c_obs = col_obs[0]
                c_uni = col_uni_f[0]
                c_val = col_val[0] if col_val else None
                c_data_fat = col_data_fat[0] if col_data_fat else None
                
                registros_faltas = []
                for idx_row, row in df_f.dropna(subset=[c_obs]).iterrows():
                    unidade_f = str(row[c_uni]).strip().upper()
                    obs_str = str(row[c_obs]).strip()
                    # Capturar data da fatura da linha (ex: 13/05/2026)
                    data_fat_linha = str(row[c_data_fat]).strip() if c_data_fat else str(idx_row)
                    
                    if c_val:
                        val_limpo = limpar_moeda(str(row[c_val]))
                        val_total = pd.to_numeric(val_limpo, errors='coerce')
                    else:
                        val_total = 0
                    val_total = val_total if pd.notna(val_total) else 0
                    
                    eventos = [ev.strip() for ev in obs_str.split('|') if ev.strip()]
                    qtd_eventos = len(eventos)
                    val_unit = val_total / qtd_eventos if qtd_eventos > 0 else 0
                    
                    for ev in eventos:
                        partes = ev.split(',')
                        nome_cru = partes[0].strip()
                        nome_key = limpar_string(nome_cru)
                        # Extrair data do evento do próprio detalhe (3ª parte: nome,matric,data,hora)
                        data_evento = partes[2].strip() if len(partes) > 2 else ''
                        # Data_Falta = data do evento (ex: 13/04/2026) ou data da fatura como fallback
                        data_falta = data_evento if data_evento else data_fat_linha
                        
                        registros_faltas.append({
                            'UNIDADE': unidade_f,
                            'Nome': nome_cru,
                            'Nome_Key': nome_key,
                            'Data_Falta': data_falta,
                            'Data_Fatura': data_fat_linha,
                            'Valor_Falta': val_unit,
                            'Detalhe': ev
                        })
                        
                if registros_faltas:
                    df_faltas_det = pd.DataFrame(registros_faltas)
                    if not info_rh.empty:
                        faltas_final = pd.merge(df_faltas_det, info_rh, on='Nome_Key', how='left')
                    else:
                        faltas_final = df_faltas_det.copy()
                        faltas_final['DEPARTAMENTO'] = 'NÃO MAPEADO'
                        faltas_final['Centro de custo'] = 'SEM CC'
                    # Aplicar validação CTT nas Faltas — exclusivamente via aba CTT
                    if not faltas_final.empty:
                        faltas_final['Empresa Custo Real'] = faltas_final.apply(alocar_unidade_ctt, axis=1)
                        
    # ===== Alertas por unidade (Lista RM x Listagem de Funcionários e CTT) =====
    alertas = {'ausentes': {}, 'ausentes_lista': [], 'cc_inativos': {}, 'cc_inativos_cods': set()}
    # Conjunto de códigos de CC inativos no CTT (para pintar linhas e avisar na Validação)
    alertas['cc_inativos_cods'] = {c for c, i in mapa_ctt.items() if i.get('inativo')}

    # (1) Funcionários presentes na Lista RM mas AUSENTES na Listagem de Funcionários
    # Cruzamento robusto: considera presente quem casar por CPF OU por nome normalizado,
    # pois nem sempre as duas abas trazem o CPF no mesmo formato (ou trazem CPF).
    cpfs_listagem = set()
    nomes_listagem = set()
    if not df_func_soc.empty:
        if 'CPF_Key' in df_func_soc.columns:
            cpfs_listagem = {c for c in df_func_soc['CPF_Key'].astype(str) if c and c.upper() not in ('NAN', 'NONE')}
        if 'Nome_Key' in df_func_soc.columns:
            nomes_listagem = {_norm_txt(n) for n in df_func_soc['Nome_Key'].astype(str) if n and n.upper() not in ('NAN', 'NONE')}

    # A Lista RM não traz Empresa/Filial, então a unidade do ausente é derivada do
    # Centro de Custo: 1º pela unidade de funcionários ATIVOS com o mesmo CC (igual ao card),
    # 2º pela EMPRESA do CTT (sem o prefixo numérico), casando com o nome do card quando existir.
    cc_to_unidade_ativa = {}
    for _dfa in [fatura_final, vidas_final, faltas_final]:
        if _dfa is None or _dfa.empty or 'Centro de custo' not in _dfa.columns or 'UNIDADE' not in _dfa.columns:
            continue
        for _, _r in _dfa[['Centro de custo', 'UNIDADE']].dropna().iterrows():
            _cod = str(_r['Centro de custo']).split(' - ')[0].strip().replace('.0', '')
            _u = str(_r['UNIDADE']).strip()
            if _cod and _u and _u.upper() not in ('', 'NAN', 'NONE'):
                cc_to_unidade_ativa.setdefault(_cod, _u)
    unidades_existentes = set(cc_to_unidade_ativa.values())
    cc_to_empresa_nome = {}
    for _cod, _info_ctt in mapa_ctt.items():
        _emp = str(_info_ctt.get('empresa', '')).strip()
        cc_to_empresa_nome[_cod] = _emp.split(' - ', 1)[1].strip() if ' - ' in _emp else _emp

    def _unidade_do_ausente(cc_cod):
        cc_cod = str(cc_cod).strip().replace('.0', '')
        if cc_cod in cc_to_unidade_ativa:
            return cc_to_unidade_ativa[cc_cod]
        emp = cc_to_empresa_nome.get(cc_cod, '')
        if emp:
            for u in unidades_existentes:
                if u.upper() == emp.upper():
                    return u
            return emp
        return 'CC NÃO MAPEADO NO CTT'

    for _map_key, info in mapa_lista_rm.items():
        cpf = info.get('cpf', '')
        nome_key = info.get('nome_key', '')
        presente_por_cpf = bool(cpf) and cpf in cpfs_listagem
        presente_por_nome = bool(nome_key) and nome_key in nomes_listagem
        if presente_por_cpf or presente_por_nome:
            continue
            
        # Não cobrar/alertar funcionários demitidos há mais de 30 dias
        if info.get('is_demitido_antigo'):
            continue
            
        uni_rm = str(info.get('unidade', '')).strip().upper()
        # Limpar possível prefixo '01 - ' ou '10 - '
        if ' - ' in uni_rm and uni_rm.split(' - ', 1)[0].isdigit():
            uni_rm_clean = uni_rm.split(' - ', 1)[1].strip()
        else:
            uni_rm_clean = uni_rm
            
        # Padronizar nomes conhecidos
        if uni_rm_clean in ('EMPRESA_01 CONSÓRCIO PROJETO_ALFA', 'EMPRESA_01 CONSORCIO PROJETO_ALFA'):
            uni_rm_clean = 'CONSORCIO PROJETO_ALFA'
        elif uni_rm_clean in ('CONSÓRCIO EMPRESA_01 EMPRESA_02', 'CONSORCIO_C'):
            uni_rm_clean = 'CONSORCIO_C'
            
        # Se a coligada pertencer a uma dessas 3, forçamos a unidade ser ela mesma
        if uni_rm_clean in ('EMPRESA_01 DO BRASIL', 'CONSORCIO_C', 'CONSORCIO PROJETO_ALFA'):
            uni = uni_rm_clean
        else:
            uni = _unidade_do_ausente(info.get('cc_cod', '')) or 'CC NÃO MAPEADO NO CTT'
        cc_str = info.get('cc', 'SEM CC')
        cc_parts = cc_str.split(' - ', 1)
        registro_ausente = {
            'unidade': uni,
            'nome': info.get('nome', 'Desconhecido'),
            'departamento': info.get('departamento', 'NÃO INFORMADO'),
            'cc': cc_str,
            'cc_cod': info.get('cc_cod', cc_parts[0].strip()),
            'cc_nome': info.get('cc_nome', cc_parts[1].strip() if len(cc_parts) > 1 else ''),
        }
        alertas['ausentes'].setdefault(uni, []).append(registro_ausente)
        alertas['ausentes_lista'].append(registro_ausente)

    # (3) Centros de custo INATIVOS no CTT (CTT_BLOQ = 'INATIVO') presentes nos custos alocados
    for _dfa in [fatura_final, vidas_final, faltas_final]:
        if _dfa is None or _dfa.empty or 'Centro de custo' not in _dfa.columns or 'UNIDADE' not in _dfa.columns:
            continue
        tmp = _dfa[['Centro de custo', 'UNIDADE']].drop_duplicates()
        for _, r in tmp.iterrows():
            cc_cod = str(r['Centro de custo']).split(' - ')[0].strip().replace('.0', '')
            info_ctt = mapa_ctt.get(cc_cod)
            if info_ctt and info_ctt.get('inativo'):
                alertas['cc_inativos'].setdefault(str(r['UNIDADE']), set()).add(str(r['Centro de custo']))
    alertas['cc_inativos'] = {u: sorted(v) for u, v in alertas['cc_inativos'].items()}

    # EMPRESA e FILIAL do CTT (vinculadas ao código do Centro de Custo) — para a validação de divergência
    cc_to_emp = {cod: str(info.get('empresa', '')).strip() for cod, info in mapa_ctt.items()}
    cc_to_fil = {cod: str(info.get('filial', '')).strip() for cod, info in mapa_ctt.items()}
    for df in [fatura_final, vidas_final, faltas_final]:
        if df.empty or 'Centro de custo' not in df.columns:
            continue
        codes = df['Centro de custo'].astype(str).str.split(' - ').str[0].str.strip().str.replace('.0', '', regex=False)
        df['Empresa CTT'] = codes.map(cc_to_emp).fillna('')
        df['Filial CTT'] = codes.map(cc_to_fil).fillna('')

    # Garantir strings nas colunas de agrupamento
    for df in [fatura_final, vidas_final, faltas_final]:
        if not df.empty:
            df['DEPARTAMENTO'] = df['DEPARTAMENTO'].fillna('NÃO MAPEADO').astype(str)
            df['Centro de custo'] = df['Centro de custo'].fillna('SEM CC').astype(str)
            
            # Sobrescrever para garantir visibilidade do PSICOSSOCIAL nos relatórios
            if 'Exame' in df.columns:
                mask_psico = df['Exame'].astype(str).str.upper() == 'PSICOSSOCIAL'
                if mask_psico.any():
                    df.loc[mask_psico, 'Centro de custo'] = 'PSICOSSOCIAL'
                    df.loc[mask_psico, 'DEPARTAMENTO'] = 'PSICOSSOCIAL'
            if 'Unidade Cadastro RM' in df.columns:
                df['Unidade Cadastro RM'] = df['Unidade Cadastro RM'].fillna('NÃO CADASTRADO').astype(str)
            else:
                df['Unidade Cadastro RM'] = 'NÃO CADASTRADO'
            if 'Departamento RM' in df.columns:
                df['Departamento RM'] = df['Departamento RM'].fillna('NÃO INFORMADO').astype(str).str.strip()
                df.loc[df['Departamento RM'].str.upper().isin(['', 'NAN', 'NONE']), 'Departamento RM'] = 'NÃO INFORMADO'
            else:
                df['Departamento RM'] = 'NÃO INFORMADO'
            for _c in ['Empresa CTT', 'Filial CTT', 'Unidade Listagem']:
                if _c in df.columns:
                    df[_c] = df[_c].fillna('').astype(str).str.strip()
                    df.loc[df[_c].str.upper().isin(['NAN', 'NONE']), _c] = ''
                else:
                    df[_c] = ''
            
            # Normalização final das UNIDADES
            if 'UNIDADE' in df.columns:
                df['UNIDADE'] = df['UNIDADE'].replace({
                    'EMPRESA_01 CONSÓRCIO PROJETO_ALFA': 'CONSORCIO PROJETO_ALFA',
                    'EMPRESA_01 CONSORCIO PROJETO_ALFA': 'CONSORCIO PROJETO_ALFA',
                    'CONSÓRCIO EMPRESA_01 EMPRESA_02': 'CONSORCIO_C',
                    'EMPRESA_01 D': 'EMPRESA_01 DO BRASIL',
                    'EMPRESA_01 D8': 'EMPRESA_01 DO BRASIL',
                    'EMPRESA_01 DO BRASIL DISTRIBUIDORA DE DERIVADOS DE PETROLEO LTDA - 30824': 'EMPRESA_01 DO BRASIL'
                })

    return fatura_final, vidas_final, faltas_final, alertas, mapa_ctt

# --- CSS CUSTOMIZADO PREMIUM ---
css = """
<style>
    /* Bot�o Sair na sidebar */
    [class*="st-key-btn_sair"] button {
        background: rgba(255, 255, 255, 0.1) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }
    [class*="st-key-btn_sair"] button:hover {
        background: rgba(255, 255, 255, 0.25) !important;
        color: #ffffff !important;
        border-color: #ffffff !important;
    }
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    :root {
        --bg-card: #ffffff;
        --bg-card-hover: #f8fafc;
        --bg-metric-pill: rgba(15, 23, 42, 0.05);
        --border-card: #e8edf3;
        --text-main: #0f172a;
        --text-muted: #64748b;
        --text-pill: #FILIAL_26;
        --accent: #6366f1;
        --accent-hover: #4f46e5;
        --radius: 16px;
        --radius-sm: 10px;
        --shadow-card: 0 1px 2px rgba(16, 24, 40, 0.04), 0 4px 16px -4px rgba(16, 24, 40, 0.10);
        --shadow-hover: 0 8px 28px -6px rgba(16, 24, 40, 0.18);
        
        --color-total: #dc2626;
        --bg-total-card: linear-gradient(135deg, #ffffff 0%, #fef2f2 100%);
        --bg-total-card-hover: linear-gradient(135deg, #ffffff 0%, #fee2e2 100%);
        --bg-total-icon: #fef2f2;
        
        --color-exames: #8b5cf6;
        --bg-exames-card: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
        --bg-exames-card-hover: linear-gradient(135deg, #ffffff 0%, #ede9fe 100%);
        --bg-exames-icon: #f5f3ff;
        
        --color-vidas: #2563eb;
        --bg-vidas-card: linear-gradient(135deg, #ffffff 0%, #eff6ff 100%);
        --bg-vidas-card-hover: linear-gradient(135deg, #ffffff 0%, #dbeafe 100%);
        --bg-vidas-icon: #eff6ff;
        
        --color-faltas: #b91c1c;
        --bg-faltas-card: linear-gradient(135deg, #ffffff 0%, #fef2f2 100%);
        --bg-faltas-card-hover: linear-gradient(135deg, #ffffff 0%, #fee2e2 100%);
        --bg-faltas-icon: #fef2f2;

        --color-psico: #0891b2;
        --bg-psico-card: linear-gradient(135deg, #ffffff 0%, #ecfeff 100%);
        --bg-psico-card-hover: linear-gradient(135deg, #ffffff 0%, #cffafe 100%);
        --bg-psico-icon: #ecfeff;

        --color-total-uni: #d97706;
        --bg-total-uni-icon: #fef3c7;
    }
    
    @media (prefers-color-scheme: dark) {
        :root {
            --bg-card: #1e293b;
            --bg-card-hover: #FILIAL_27;
            --bg-metric-pill: rgba(255, 255, 255, 0.10);
            --border-card: #FILIAL_26;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-pill: #f1f5f9;
            --accent: #818cf8;
            --accent-hover: #a5b4fc;
            --shadow-card: 0 1px 2px rgba(0, 0, 0, 0.3), 0 6px 20px -6px rgba(0, 0, 0, 0.45);
            --shadow-hover: 0 10px 30px -6px rgba(0, 0, 0, 0.55);
            
            --color-total: #ef4444;
            --bg-total-card: linear-gradient(135deg, #1e293b 0%, rgba(239, 68, 68, 0.12) 100%);
            --bg-total-card-hover: linear-gradient(135deg, var(--bg-card-hover) 0%, rgba(239, 68, 68, 0.20) 100%);
            --bg-total-icon: rgba(239, 68, 68, 0.15);
            
            --color-exames: #a78bfa;
            --bg-exames-card: linear-gradient(135deg, #1e293b 0%, rgba(167, 139, 250, 0.12) 100%);
            --bg-exames-card-hover: linear-gradient(135deg, var(--bg-card-hover) 0%, rgba(167, 139, 250, 0.20) 100%);
            --bg-exames-icon: rgba(167, 139, 250, 0.15);
            
            --color-vidas: #3b82f6;
            --bg-vidas-card: linear-gradient(135deg, #1e293b 0%, rgba(59, 130, 246, 0.12) 100%);
            --bg-vidas-card-hover: linear-gradient(135deg, var(--bg-card-hover) 0%, rgba(59, 130, 246, 0.20) 100%);
            --bg-vidas-icon: rgba(59, 130, 246, 0.15);
            
            --color-faltas: #f87171;
            --bg-faltas-card: linear-gradient(135deg, #1e293b 0%, rgba(248, 113, 113, 0.12) 100%);
            --bg-faltas-card-hover: linear-gradient(135deg, var(--bg-card-hover) 0%, rgba(248, 113, 113, 0.20) 100%);
            --bg-faltas-icon: rgba(248, 113, 113, 0.15);

            --color-psico: #06b6d4;
            --bg-psico-card: linear-gradient(135deg, #1e293b 0%, rgba(6, 182, 212, 0.12) 100%);
            --bg-psico-card-hover: linear-gradient(135deg, var(--bg-card-hover) 0%, rgba(6, 182, 212, 0.20) 100%);
            --bg-psico-icon: rgba(6, 182, 212, 0.15);

            --color-total-uni: #fbbf24;
            --bg-total-uni-icon: rgba(251, 191, 36, 0.15);
        }
    }

    .stApp { font-family: 'Inter', sans-serif; }
    .block-container { max-width: 95% !important; padding-top: 2.2rem; }

    /* Custom metric card styling */
    .metric-card {
        display: flex;
        align-items: center;
        gap: 16px;
        background-color: var(--bg-card);
        border-radius: var(--radius);
        padding: 18px 22px;
        margin-bottom: 14px;
        box-shadow: var(--shadow-card);
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        height: 100%;
        min-height: 104px;
        border: 1px solid var(--border-card);
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-hover);
    }
    
    .metric-card.total { background: var(--bg-total-card); border-left: 5px solid var(--color-total); }
    .metric-card.total:hover { background: var(--bg-total-card-hover); }
    
    .metric-card.exames { background: var(--bg-exames-card); border-left: 5px solid var(--color-exames); }
    .metric-card.exames:hover { background: var(--bg-exames-card-hover); }
    
    .metric-card.vidas { background: var(--bg-vidas-card); border-left: 5px solid var(--color-vidas); }
    .metric-card.vidas:hover { background: var(--bg-vidas-card-hover); }
    
    .metric-card.faltas { background: var(--bg-faltas-card); border-left: 5px solid var(--color-faltas); }
    .metric-card.faltas:hover { background: var(--bg-faltas-card-hover); }

    .metric-card.psico { background: var(--bg-psico-card); border-left: 5px solid var(--color-psico); }
    .metric-card.psico:hover { background: var(--bg-psico-card-hover); }

    .metric-icon-container {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 46px;
        height: 46px;
        border-radius: 12px;
        flex-shrink: 0;
    }
    .metric-card.total .metric-icon-container { background-color: var(--bg-total-icon); color: var(--color-total); }
    .metric-card.exames .metric-icon-container { background-color: var(--bg-exames-icon); color: var(--color-exames); }
    .metric-card.vidas .metric-icon-container { background-color: var(--bg-vidas-icon); color: var(--color-vidas); }
    .metric-card.faltas .metric-icon-container { background-color: var(--bg-faltas-icon); color: var(--color-faltas); }
    .metric-card.psico .metric-icon-container { background-color: var(--bg-psico-icon); color: var(--color-psico); }

    .metric-content {
        display: flex;
        flex-direction: column;
    }
    .metric-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--text-muted);
        margin-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: var(--text-main);
    }
    
                /* Streamlit vertical block border effect custom styling (for unit cards) - FIX final */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.unit-header):not(:has(h3)) {
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-card) !important;
        border-radius: var(--radius) !important;
        box-shadow: var(--shadow-card) !important;
        margin-bottom: 16px !important;
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.unit-header):not(:has(h3)) > div,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.unit-header):not(:has(h3)) fieldset {
        border: none !important;
        background: transparent !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.unit-header):not(:has(h3)):hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-hover) !important;
        border-color: rgba(99, 102, 241, 0.45) !important;
    }
    
    .unit-header {
        font-size: 15px;
        font-weight: 700;
        color: var(--text-main);
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border-card);
        display: flex;
        align-items: center;
        gap: 8px;
        letter-spacing: -0.2px;
    }

    .unit-metric {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 6px;
        min-height: 78px;
    }
    .unit-metric-label {
        font-size: 12px;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.6px;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .unit-metric-value {
        font-size: 21px;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: var(--text-main);
    }
    .unit-metric-value-total {
        font-size: 21px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: var(--text-main);
    }
    .unit-metric-pill {
        font-size: 12px;
        font-weight: 600;
        color: var(--text-pill);
        background-color: var(--bg-metric-pill);
        padding: 4px 11px;
        border-radius: 9999px;
        display: inline-block;
    }
    
    /* === Botões de ação — sistema global robusto via classe st-key-* === */
    .stButton > button {
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        transition: all 0.18s ease !important;
        box-shadow: none !important;
    }
    .stButton > button:hover { transform: translateY(-1px); }

    /* Validar — ação primária (preenchida, alto destaque) */
    [class*="st-key-btn_detalhar"] button {
        background: var(--accent) !important;
        border: 1px solid var(--accent) !important;
        color: #ffffff !important;
    }
    [class*="st-key-btn_detalhar"] button:hover {
        background: var(--accent-hover) !important;
        border-color: var(--accent-hover) !important;
        box-shadow: 0 6px 16px -4px rgba(99, 102, 241, 0.5) !important;
    }

    /* Excluir — ação destrutiva (contorno vermelho) */
    [class*="st-key-btn_excluir_uni"] button {
        background: transparent !important;
        border: 1.5px solid #ef4444 !important;
        color: #ef4444 !important;
    }
    [class*="st-key-btn_excluir_uni"] button:hover {
        background: rgba(239, 68, 68, 0.08) !important;
        border-color: #dc2626 !important;
        color: #dc2626 !important;
    }

    /* Restaurar — ação neutra (contorno accent) */
    [class*="st-key-btn_restaurar_uni"] button {
        background: transparent !important;
        border: 1.5px solid var(--accent) !important;
        color: var(--accent) !important;
    }

    /* Psicossocial Ratear — popover na 4ª coluna do card de unidade (contorno ciano) */
    div[data-testid="column"]:nth-child(4) div[data-testid="stPopover"] > button {
        background: transparent !important;
        border: 1.5px solid #0891b2 !important;
        color: #0891b2 !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        width: 100% !important;
        white-space: nowrap !important;
        transition: all 0.18s ease !important;
    }
    div[data-testid="column"]:nth-child(4) div[data-testid="stPopover"] > button:hover {
        background: rgba(8, 145, 178, 0.08) !important;
        border-color: #0e7490 !important;
        color: #0e7490 !important;
        transform: translateY(-1px);
    }

    /* Desconto — popover na 7ª coluna do card de unidade (contorno verde) */
    div[data-testid="column"]:nth-child(7) div[data-testid="stPopover"] > button {
        background: transparent !important;
        border: 1.5px solid #10b981 !important;
        color: #10b981 !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        width: 100% !important;
        white-space: nowrap !important;
        transition: all 0.18s ease !important;
    }
    div[data-testid="column"]:nth-child(7) div[data-testid="stPopover"] > button:hover {
        background: rgba(16, 185, 129, 0.08) !important;
        border-color: #FILIAL_28 !important;
        color: #FILIAL_28 !important;
        transform: translateY(-1px);
    }

    /* Todos os painéis de popover — largura mínima para evitar corte de conteúdo */
    section[data-testid="stPopoverBody"] {
        min-width: 420px !important;
        max-width: 520px !important;
    }
    
    /* Premium visual styling for tables */
    table {
        width: 100%;
        border-collapse: collapse;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
    }
    
    thead th {
        background-color: #f1f5f9 !important;
        color: #FILIAL_26 !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 12px;
        padding: 12px 16px !important;
        border-bottom: 2px solid #e2e8f0 !important;
        text-align: left !important;
    }
    
    tbody td {
        padding: 12px 16px !important;
        font-size: 13px;
        border-bottom: 1px solid #f1f5f9 !important;
        color: #FILIAL_29;
        text-align: left !important;
    }
    
    tbody tr:hover {
        background-color: #f8fafc !important;
    }
    
    @media (prefers-color-scheme: dark) {
        thead th {
            background-color: #1e293b !important;
            color: #cbd5e1 !important;
            border-bottom: 2px solid #FILIAL_26 !important;
        }
        tbody td {
            border-bottom: 1px solid #1e293b !important;
            color: #e2e8f0;
        }
        tbody tr:hover {
            background-color: #0f172a !important;
        }
    }

    /* Checklist premium styling */
    .checklist-wrapper {
        background-color: var(--bg-card);
        border-radius: 12px;
        padding: 24px;
        margin-top: 32px;
        margin-bottom: 24px;
        border: 1px solid var(--border-card);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .checklist-header-box {
        display: flex;
        align-items: center;
        background-color: rgba(234, 179, 8, 0.1);
        border: 1px solid rgba(234, 179, 8, 0.4);
        border-radius: 8px;
        padding: 14px 20px;
        margin-bottom: 24px;
    }
    .checklist-header-box h4 {
        margin: 0 0 4px 0 !important;
        font-size: 16px;
        font-weight: 600;
        color: #ca8a04;
    }
    .checklist-header-box p {
        margin: 0 !important;
        font-size: 14px;
        color: var(--text-main);
    }
    @media (prefers-color-scheme: dark) {
        .checklist-header-box h4 { color: #facc15; }
    }
    .checklist-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 16px;
    }
    .check-card {
        border-radius: 10px;
        border: 1px solid var(--border-card);
        background-color: var(--bg-card);
        overflow: hidden;
        display: flex;
        flex-direction: column;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .check-card-header {
        padding: 12px 16px;
        font-size: 14px;
        font-weight: 600;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: white;
    }
    .card-blue .check-card-header { background-color: #3b82f6; }
    .card-green .check-card-header { background-color: #10b981; }
    .card-orange .check-card-header { background-color: #f59e0b; }
    .card-purple .check-card-header { background-color: #8b5cf6; }

    .check-card-body {
        padding: 16px;
        font-size: 13px;
        color: var(--text-main);
        flex-grow: 1;
        display: flex;
        flex-direction: column;
    }
    .check-card-body p.desc {
        font-size: 13px;
        color: var(--text-muted);
        margin-bottom: 14px;
        line-height: 1.5;
    }
    .check-card-body ul {
        list-style-type: none;
        padding: 0;
        margin: 0 0 14px 0;
        flex-grow: 1;
    }
    .check-card-body ul li {
        margin-bottom: 8px;
        padding-left: 20px;
        position: relative;
        font-size: 13px;
        line-height: 1.4;
    }
    .check-card-body ul li::before {
        content: "•";
        position: absolute;
        left: 6px;
        color: var(--text-muted);
    }
    .check-card-body .nota {
        font-size: 12px;
        background-color: var(--bg-metric-pill);
        padding: 10px;
        border-radius: 8px;
        color: var(--text-muted);
        margin: 0;
        font-style: italic;
        line-height: 1.4;
    }

    /* === Avisos dentro do card de unidade === */
    .unit-alert {
        font-size: 12.5px;
        line-height: 1.45;
        border-radius: 10px;
        padding: 10px 14px;
        margin: 4px 0 14px 0;
    }
    .unit-alert b { font-weight: 700; }
    .unit-alert ul { margin: 6px 0 0 0; padding-left: 18px; }
    .unit-alert li { margin-bottom: 2px; }
    .unit-alert.alert-danger {
        background: rgba(239, 68, 68, 0.10);
        border: 1px solid rgba(239, 68, 68, 0.35);
        color: #b91c1c;
    }
    .unit-alert.alert-warn {
        background: rgba(245, 158, 11, 0.10);
        border: 1px solid rgba(245, 158, 11, 0.35);
        color: #b45309;
    }
    @media (prefers-color-scheme: dark) {
        .unit-alert.alert-danger { color: #fca5a5; }
        .unit-alert.alert-warn { color: #fcd34d; }
    }

    /* === Validação de Custos: toolbars e badge de seleção === */
    .toolbar-title {
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        color: var(--text-muted);
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .sel-badge {
        display: inline-block;
        width: 100%;
        font-size: 13px;
        font-weight: 700;
        padding: 7px 14px;
        border-radius: 9999px;
        background: var(--bg-metric-pill);
        color: var(--text-muted);
        border: 1px solid var(--border-card);
        text-align: center;
        transition: all 0.18s ease;
    }
    .sel-badge.on {
        background: rgba(99, 102, 241, 0.12);
        color: var(--accent);
        border-color: rgba(99, 102, 241, 0.40);
    }
    /* Compactar os multiselects dos filtros */
    div[data-testid="stMultiSelect"] label p { font-size: 12px !important; font-weight: 600 !important; }

    /* === Cabeçalhos, abas e espaçamento geral === */
    h1, h2, h3 { letter-spacing: -0.4px; }
    h3 { margin-top: 0.4rem !important; }
    hr { margin: 1.1rem 0 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 8px 18px;
        font-weight: 600;
    }
    .stDownloadButton > button {
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
    }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- Dashboard ---
st.title("📑 Gestão Faturamento Parceiro_Y")

with st.sidebar:
    st.caption(f"👤 Conectado como **{st.session_state.get('usuario_logado', 'Usuário')}**")
    if st.button("🚪 Sair", key="btn_sair", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

# Planilha hospedada no OneDrive (lida automaticamente ao abrir o painel)
caminho_onedrive = encontrar_planilha_onedrive()

if caminho_onedrive:
    import datetime as _dt
    _mtime = _dt.datetime.fromtimestamp(os.path.getmtime(caminho_onedrive)).strftime('%d/%m/%Y %H:%M')
    st.success(f"📁 Planilha carregada automaticamente do OneDrive: **{os.path.basename(caminho_onedrive)}** "
               f"· atualizada em {_mtime}")
else:
    st.warning("⚠️ Não encontrei a planilha na pasta do OneDrive "
               f"(`{PASTA_BASE_ONEDRIVE}`). Certifique-se de que o arquivo começa com 'FATURAMENTO EMPRESA_01' e tente novamente ou faça o upload manual abaixo.")

fonte_dados = caminho_onedrive
if caminho_onedrive:
    # Remove mtime para não invalidar o JSON a cada download
    current_file_id = f"onedrive::{os.path.basename(caminho_onedrive)}"
else:
    current_file_id = None
last_file_id = st.session_state.get('last_uploaded_file_id')

if current_file_id != last_file_id:
    # Troca de planilha: zera o estado e tenta carregar os ajustes salvos desta planilha
    for k in _CHAVES_AJUSTES:
        st.session_state.pop(k, None)
    carregar_ajustes(fonte_dados, current_file_id)
    # Marca o estado já carregado para não regravar imediatamente o mesmo conteúdo
    st.session_state['_ajustes_blob'] = _serializar_ajustes(current_file_id)
    st.session_state['last_uploaded_file_id'] = current_file_id

html_checklist = """
<div class="checklist-wrapper">
    <div class="checklist-header-box">
        <div style="font-size: 28px; margin-right: 16px;">📋</div>
        <div>
            <h4>Guia de Preparação da Planilha</h4>
            <p>Para o painel ler seus dados corretamente, sua planilha precisa ter as abas e colunas abaixo. O sistema é flexível e aceita algumas variações nos nomes das colunas, mas siga este padrão para evitar erros:</p>
        </div>
    </div>
    <div class="checklist-grid">
        <!-- Card 1 -->
        <div class="check-card card-blue">
            <div class="check-card-header">
                <span>1. Fatura de Exames</span>
                <span>💲</span>
            </div>
            <div class="check-card-body">
                <p class="desc"><strong>Nome da Aba:</strong> Relatório de fatura ou FAT</p>
                <p class="desc"><strong>Onde o sistema começa a ler:</strong> Ele ignora o cabeçalho bagunçado do topo e procura a primeira linha que tenha Setor e Nome juntos. Deixe a informação de UNIDADE: na primeira coluna antes desse cabeçalho para ele conseguir separar os blocos.</p>
                <p class="desc"><strong>Colunas exatas:</strong></p>
                <ul>
                    <li><strong>NOME</strong></li>
                    <li><strong>EXAME</strong></li>
                    <li><strong>TIPO</strong> (Se não tiver, ele preenche com "N/A")</li>
                </ul>
                <p class="desc" style="margin-top: 10px;"><strong>Colunas flexíveis:</strong></p>
                <ul>
                    <li><strong>Centro de Custo:</strong> O título pode ter SEÇÃO, SECAO, SETOR ou C CUSTO. Dica: Se a célula estiver vazia, ele tenta puxar o valor da coluna DESCRICAO FORM.</li>
                    <li><strong>Valor:</strong> O título precisa conter a palavra COBRAR.</li>
                    <li><strong>Status:</strong> O título precisa conter SITUA ou STATUS (ex: Situação, Status, Situação Funcional).</li>
                </ul>
            </div>
        </div>
        <!-- Card 2 -->
        <div class="check-card card-green">
            <div class="check-card-header">
                <span>2. Base de C. Custo (CTT)</span>
                <span>⚙️</span>
            </div>
            <div class="check-card-body">
                <p class="desc"><strong>Nome da Aba:</strong> CTT</p>
                <p class="desc"><strong>Como funciona:</strong> O painel usa essa aba para cruzar informações e definir a Unidade Real do funcionário juntando Empresa + Filial.</p>
                <p class="desc" style="margin-top: 10px;"><strong>Colunas flexíveis:</strong></p>
                <ul>
                    <li><strong>Código do CC:</strong> O título precisa conter CENTRO DE CUSTO, CODIGO, CTT ou COD.</li>
                    <li><strong>Empresa:</strong> O título precisa conter EMPRESA.</li>
                    <li><strong>Filial:</strong> O título precisa conter FILIAL.</li>
                </ul>
            </div>
        </div>
        <!-- Card 3 -->
        <div class="check-card card-orange">
            <div class="check-card-header">
                <span>3. Funcionários (Vidas Ativas)</span>
                <span>👥</span>
            </div>
            <div class="check-card-body">
                <p class="desc"><strong>Nome da Aba:</strong> Listagem de Funcionários ou Funcionarios</p>
                <p class="desc"><strong>Colunas exatas:</strong></p>
                <ul>
                    <li><strong>NOME:</strong> (Obrigatório. É por aqui que ele cruza o RH com a fatura e as faltas).</li>
                    <li><strong>UNIDADE:</strong> (Unidade física de cadastro).</li>
                    <li><strong>Cargo ou Função:</strong> (Se não existir, ele vai chamar todo mundo de "Vida Ativa").</li>
                </ul>
                <p class="desc" style="margin-top: 10px;"><strong>Colunas flexíveis:</strong></p>
                <ul>
                    <li><strong>Departamento:</strong> Título precisa conter REGIONAL, SETOR ou DEPARTAMENTO.</li>
                    <li><strong>Código do CC:</strong> Título precisa conter CENTRO DE CUSTO (mas não pode ter a palavra "nome" nem "seção").</li>
                    <li><strong>Nome do CC:</strong> Título precisa conter SEÇÃO ou NOME CENTRO DE CUSTO. O sistema vai juntar o Código + Nome automaticamente.</li>
                    <li><strong>Status:</strong> Título precisa conter SITUA ou STATUS.</li>
                </ul>
            </div>
        </div>
        <!-- Card 4 -->
        <div class="check-card card-purple">
            <div class="check-card-header">
                <span>4. Faltas</span>
                <span>📅</span>
            </div>
            <div class="check-card-body">
                <p class="desc"><strong>Nome da Aba:</strong> Faltas</p>
                <p class="desc"><strong>Onde o sistema começa a ler:</strong> Ele desce as linhas até achar a palavra Observa. Ali ele define que é o cabeçalho.</p>
                <p class="desc" style="margin-top: 10px;"><strong>Colunas flexíveis:</strong></p>
                <ul>
                    <li><strong>Observações:</strong> Título precisa conter OBSERVA. É daqui que o sistema arranca o nome do funcionário, a matrícula e a data exata da falta (separados por vírgulas ou |).</li>
                    <li><strong>Unidade:</strong> Título precisa conter NOME UNIDADE ou UNIDADE.</li>
                    <li><strong>Valor:</strong> Título precisa conter VALOR. Ele pega esse valor e divide pelo número de faltas listadas na observação.</li>
                    <li><strong>Data Geral:</strong> Título precisa conter DATA, COMPETENCIA ou FATURA. O sistema só usa isso como plano B se não conseguir achar a data da falta dentro da coluna de observação.</li>
                </ul>
            </div>
        </div>
    </div>
</div>
"""

if not fonte_dados:
    st.markdown(html_checklist, unsafe_allow_html=True)

if fonte_dados:
    df_exames, df_vidas, df_faltas, alertas, mapa_ctt = carregar_dados(fonte_dados)
    
    # Extrair lista única de unidades mapeadas via CTT ('Empresa - Filial')
    # Usa apenas os valores que aparecem nos dados processados (vindos do CTT ou da Listagem como fallback)
    _unidades_set = set()
    for _df in [df_exames, df_vidas, df_faltas]:
        if not _df.empty and 'UNIDADE' in _df.columns:
            _unidades_set.update(_df['UNIDADE'].dropna().astype(str).str.strip().unique())
    # Remover strings vazias ou inválidas
    _unidades_set = {u for u in _unidades_set if u and u.upper() not in ('', 'NAN', 'NONE')}
    lista_unidades = sorted(_unidades_set)

    if lista_unidades:
        lista_unidades.insert(0, 'TODAS AS UNIDADES')

        # Para compatibilidade com as abas inferiores (caso precisem do state antigo)
        if 'transferencias' not in st.session_state:
            st.session_state['transferencias'] = {}

        # ===== CONSTRUÇÃO DO DATAFRAME CONSOLIDADO E ALOCAÇÃO INDIVIDUAL =====
        if 'alocacoes_manuais' not in st.session_state:
            st.session_state['alocacoes_manuais'] = {}
        if 'unidades_excluidas' not in st.session_state:
            st.session_state['unidades_excluidas'] = set()
        if 'descontos_unidades' not in st.session_state:
            st.session_state['descontos_unidades'] = {}
        if 'rateio_psico' not in st.session_state:
            st.session_state['rateio_psico'] = {}

        # Persiste no OneDrive qualquer alteração feita na interação anterior (grava só se mudou)
        salvar_ajustes(fonte_dados, current_file_id)

        # ===== CONSTRUÇÃO DO DATAFRAME CONSOLIDADO (Refatorado) =====
        df_consolidado, unidades_reais, lista_cc, df_resumo_unidades, df_resumo_parceiro_y = processar_faturamento_dados(
            df_exames, df_vidas, df_faltas, st.session_state
        )

        # ===== FORMULÁRIO GIGANTE DE VALIDAÇÃO (MODAL EM TELA CHEIA) =====
        if st.session_state.get('unidade_validacao'):
            uni_val = st.session_state['unidade_validacao']
            
            # --- Filtragem Inteligente de Centros de Custo por Unidade ---
            def obter_ccs_filtrados(uni, cc_list, map_ctt):
                if map_ctt:
                    validos = []
                    uni_n = _norm_txt(uni)
                    for cod, info in map_ctt.items():
                        desc = info.get('desc', '')
                        cc_str = f"{cod} - {desc}" if desc else cod
                        # Evita adicionar opções de CC inativo, melhorando a seleção
                        if info.get('inativo'):
                            continue
                            
                        empresa_n = _norm_txt(info.get('empresa', ''))
                        filial_n = _norm_txt(info.get('filial', ''))
                        
                        if uni_n == _norm_txt('EMPRESA_01 DO BRASIL') or uni_n == _norm_txt('EMPRESA_01'):
                            if empresa_n == _norm_txt('01 - EMPRESA_01 DO BRASIL'):
                                validos.append(cc_str)
                            continue
                            
                        if uni_n == _norm_txt('CONSORCIO_C') or uni_n == _norm_txt('EMPRESA_01 EMPRESA_02'):
                            if empresa_n == _norm_txt('01 - EMPRESA_01 DO BRASIL') and filial_n == _norm_txt('FILIAL_10 - CONSORCIO_C'):
                                validos.append(cc_str)
                            continue
                            
                        if uni_n == _norm_txt('CONSORCIO PROJETO_ALFA') or uni_n == _norm_txt('PROJETO_ALFA'):
                            if empresa_n == _norm_txt('10 - CONSORCIO PROJETO_ALFA'):
                                validos.append(cc_str)
                            continue
                        
                        # Validação geral com o campo empresa ou filial
                        if uni_n in empresa_n or uni_n in filial_n:
                            validos.append(cc_str)
                            
                    if validos:
                        return sorted(validos)
                return cc_list
                
            lista_cc_filtrada = obter_ccs_filtrados(uni_val, lista_cc, mapa_ctt)
            
            if 'linhas_excluidas' not in st.session_state:
                st.session_state['linhas_excluidas'] = set()
                
            st.markdown(f"## 📋 Validação de Custos: {uni_val}")
            if st.button("⬅️ Voltar ao Painel", type="primary"):
                st.session_state['unidade_validacao'] = None
                st.rerun()
                
            df_uni_full = df_consolidado[df_consolidado['Unidade Alocada'] == uni_val]
            
            # Separar ativos e excluídos
            df_uni = df_uni_full[~df_uni_full['ID_Linha'].isin(st.session_state['linhas_excluidas'])]
            df_uni_excluidos = df_uni_full[df_uni_full['ID_Linha'].isin(st.session_state['linhas_excluidas'])]

            # Aviso de Centro(s) de Custo INATIVO(s) no CTT presentes nesta unidade
            inativos_cods = alertas.get('cc_inativos_cods', set())
            def _cc_inativo(cc_label):
                cod = str(cc_label).split(' - ')[0].strip().replace('.0', '')
                return cod in inativos_cods
            ccs_inativos_uni = sorted({str(cc) for cc in df_uni['Centro de Custo'].unique() if _cc_inativo(cc)}) if not df_uni.empty else []
            if ccs_inativos_uni:
                st.markdown(
                    f'<div class="unit-alert alert-danger">⛔ <b>Centro(s) de custo INATIVO(s) no CTT — corrigir o cadastro:</b> {", ".join(ccs_inativos_uni)}'
                    f'<br><span style="font-weight:600;"></span></div>',
                    unsafe_allow_html=True,
                )

            # Lista suspensa para funcionários da Lista RM ausentes na Listagem de Funcionários
            # Casa a unidade visualizada com a unidade da Lista RM de forma normalizada
            _uni_val_n = _norm_txt(uni_val)
            ausentes_uni = [a for a in alertas.get('ausentes_lista', []) if _norm_txt(a.get('unidade', '')) == _uni_val_n]
            if ausentes_uni:
                with st.expander(f"👥 Funcionários na Lista RM não encontrados na Listagem de Funcionários(FAT) ({len(ausentes_uni)})"):
                    df_ausentes = pd.DataFrame([{
                        'Nome': a['nome'],
                        'Departamento': a['departamento'],
                        'Centro de Custo': a.get('cc_cod', a['cc'].split(' - ')[0].strip() if ' - ' in a['cc'] else a['cc']),
                        'Nome do Centro de Custo': a.get('cc_nome', ' - '.join(a['cc'].split(' - ')[1:]).strip() if ' - ' in a['cc'] else ''),
                    } for a in ausentes_uni])
                    st.dataframe(df_ausentes, hide_index=True, use_container_width=True)

            # ===== Aviso: Vida Ativa cobrada em duplicidade nesta unidade =====
            # Sinaliza quando a mesma pessoa aparece mais de uma vez como Vida Ativa
            # (Listagem de Funcionários), ou seja, a vida está sendo cobrada repetidamente.
            _tem_dup = False
            _nomes_duplicados = set()
            if not df_uni.empty:
                _vidas_uni = df_uni[df_uni['Tipo de Custo'] == 'Vida Ativa'].copy()
                if not _vidas_uni.empty:
                    _vidas_uni['_nome_key'] = _vidas_uni['Nome'].apply(_norm_txt)
                    _cont_dup = _vidas_uni.groupby('_nome_key').agg(
                        Nome=('Nome', 'first'), Qtd=('ID_Linha', 'count')
                    ).reset_index()
                    _dups = _cont_dup[_cont_dup['Qtd'] > 1].sort_values('Qtd', ascending=False)
                    if not _dups.empty:
                        _tem_dup = True
                        _nomes_duplicados = set(_dups['Nome'].apply(_norm_txt))
                        _itens_dup = "".join(
                            f"<li><b>{r['Nome']}</b> — cobrada {int(r['Qtd'])}× "
                            f"({int(r['Qtd']) - 1} cobrança(s) a mais)</li>"
                            for _, r in _dups.iterrows()
                        )
                        st.markdown(
                            f'<div class="unit-alert alert-warn">⚠️ <b>Vida Ativa cobrada em duplicidade:</b> '
                            f'{len(_dups)} pessoa(s) aparecem mais de uma vez nesta unidade na Listagem de Funcionários '
                            f'— confira se a vida não está sendo cobrada repetidamente.'
                            f'<ul>{_itens_dup}</ul></div>',
                            unsafe_allow_html=True,
                        )

            aviso_transferencia_container = st.empty()

            # Container para o resumo dinâmico ficar acima dos filtros
            resumo_container = st.container()

            with st.container(border=True):
                st.markdown('<div class="toolbar-title">🔍 Filtros da Consulta</div>', unsafe_allow_html=True)
                f1, f2, f3, f4 = st.columns(4)
                with f1:
                    cc_opts = sorted(df_uni['CC Alocado'].unique()) if not df_uni.empty else []
                    filtro_cc = st.multiselect("Centro de Custo", options=cc_opts, placeholder="Todos")
                with f2:
                    tipo_opts = sorted(df_uni['Tipo de Custo'].unique()) if not df_uni.empty else []
                    filtro_tipo = st.multiselect("Tipo de Custo", options=tipo_opts, placeholder="Todos")
                with f3:
                    status_opts = sorted(df_uni['Status'].unique()) if not df_uni.empty else []
                    filtro_status = st.multiselect("Status", options=status_opts, placeholder="Todos")
                with f4:
                    depto_opts = sorted(df_uni['Departamento RM'].unique()) if not df_uni.empty else []
                    filtro_depto = st.multiselect("Departamento (Lista RM)", options=depto_opts, placeholder="Todos")
                _tem_div = not df_uni.empty and (df_uni['Divergência'] != '✅ OK').any()
                _tem_inativo = bool(ccs_inativos_uni)
                
                filtros_ativos = []
                if _tem_div: filtros_ativos.append("div")
                if _tem_inativo: filtros_ativos.append("inativo")
                if _tem_dup: filtros_ativos.append("dup")
                
                filtro_div = filtro_inativo = filtro_dup = False
                if filtros_ativos:
                    cols = st.columns(len(filtros_ativos))
                    for i, f_tipo in enumerate(filtros_ativos):
                        with cols[i]:
                            if f_tipo == "div":
                                filtro_div = st.checkbox("⚠️ Mostrar apenas divergências (RM vs Planilha)", value=False)
                            elif f_tipo == "inativo":
                                filtro_inativo = st.checkbox("⛔ Mostrar apenas Centros de Custo Inativos", value=False)
                            elif f_tipo == "dup":
                                filtro_dup = st.checkbox("👥 Mostrar apenas cobranças em duplicidade", value=False)
            
            # Aplicar Filtros
            df_filt = df_uni.copy()
            if filtro_cc: df_filt = df_filt[df_filt['CC Alocado'].isin(filtro_cc)]
            if filtro_tipo: df_filt = df_filt[df_filt['Tipo de Custo'].isin(filtro_tipo)]
            if filtro_status: df_filt = df_filt[df_filt['Status'].isin(filtro_status)]
            if filtro_depto: df_filt = df_filt[df_filt['Departamento RM'].isin(filtro_depto)]
            if filtro_div:
                df_filt = df_filt[df_filt['Divergência'] != "✅ OK"]
            if filtro_inativo:
                df_filt = df_filt[df_filt['Centro de Custo'].apply(_cc_inativo)]
            if filtro_dup:
                df_filt = df_filt[df_filt['Nome'].apply(lambda n: _norm_txt(n) in _nomes_duplicados)]
            
            # Exibir resumo dinâmico em card
            if not df_filt.empty:
                mask_psico_f = (df_filt['Tipo de Custo'].str.upper().str.contains('PSICOSSOCIAL', na=False) |
                                df_filt['Detalhe'].str.upper().str.contains('PSICOSSOCIAL', na=False))
                mask_exame_f = df_filt['Tipo de Custo'].str.contains('Exame', na=False) & ~mask_psico_f
                q_ex = len(df_filt[mask_exame_f])
                v_ex = df_filt[mask_exame_f]['Valor (R$)'].sum()
                q_ps = len(df_filt[mask_psico_f])
                v_ps = df_filt[mask_psico_f]['Valor (R$)'].sum()
                q_vi = len(df_filt[df_filt['Tipo de Custo'] == 'Vida Ativa'])
                v_vi = df_filt[df_filt['Tipo de Custo'] == 'Vida Ativa']['Valor (R$)'].sum()
                q_fa = len(df_filt[df_filt['Tipo de Custo'] == 'Falta'])
                v_fa = df_filt[df_filt['Tipo de Custo'] == 'Falta']['Valor (R$)'].sum()
                v_tot = v_ex + v_ps + v_vi + v_fa

                with resumo_container:
                    c1, c2, c3, cp, c4 = st.columns(5)
                    
                    c1.markdown(f"""
                    <div class="metric-card exames">
                        <div class="metric-icon-container">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                        </div>
                        <div class="metric-content">
                            <div class="metric-label" style="font-size: 12px; line-height: 1.4;">EXAMES<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {q_ex} UN</span></div>
                            <div class="metric-value">{formatar_moeda(v_ex)}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c2.markdown(f"""
                    <div class="metric-card vidas">
                        <div class="metric-icon-container">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                        </div>
                        <div class="metric-content">
                            <div class="metric-label" style="font-size: 12px; line-height: 1.4;">VIDAS ATIVAS<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {q_vi} UN</span></div>
                            <div class="metric-value">{formatar_moeda(v_vi)}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c3.markdown(f"""
                    <div class="metric-card faltas">
                        <div class="metric-icon-container">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line><line x1="9" y1="14" x2="15" y2="20"></line><line x1="15" y1="14" x2="9" y2="20"></line></svg>
                        </div>
                        <div class="metric-content">
                            <div class="metric-label" style="font-size: 12px; line-height: 1.4;">FALTAS<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {q_fa} UN</span></div>
                            <div class="metric-value">{formatar_moeda(v_fa)}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    cp.markdown(f"""
                    <div class="metric-card psico">
                        <div class="metric-icon-container">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                        </div>
                        <div class="metric-content">
                            <div class="metric-label" style="font-size: 12px; line-height: 1.4;">PSICOSSOCIAL<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {q_ps} UN</span></div>
                            <div class="metric-value">{formatar_moeda(v_ps)}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if v_ps > 0 or q_ps > 0:
                        rateio_atual_val = st.session_state['rateio_psico'].get(uni_val, [])
                        n_key_ps_val = f"psico_n_val_{uni_val}"
                        _raw_val = st.session_state.get(n_key_ps_val, max(1, len(rateio_atual_val)))
                        try:
                            n_ccs_ps_val = int(_raw_val)
                        except (ValueError, TypeError):
                            n_ccs_ps_val = max(1, len(rateio_atual_val))
                        with cp:
                            with st.popover("Ratear Custo", use_container_width=True):
                                st.markdown(f"**Ratear Psicossocial — {uni_val}**")
                                st.caption(f"Valor total a distribuir: {formatar_moeda(v_ps)}")
                                
                                with st.form(key=f"form_rateio_psico_{uni_val}", border=False):
                                    st.write("Selecione os Centros de Custo (Rateio igualitário):")
                                    defaults = []
                                    opcoes_ms = list(lista_cc_filtrada)
                                    for cc in rateio_atual_val:
                                        if cc not in opcoes_ms:
                                            opcoes_ms.append(cc)
                                        defaults.append(cc)
                                            
                                    ccs_escolhidos_val = st.multiselect(
                                        "Centros de Custo",
                                        options=opcoes_ms,
                                        default=defaults,
                                        key=f"ms_psico_{uni_val}",
                                        label_visibility="collapsed"
                                    )
                                    
                                    if ccs_escolhidos_val:
                                        st.success(f"Cada CC receberá {formatar_moeda(v_ps / len(ccs_escolhidos_val))}  ·  {len(ccs_escolhidos_val)} CC(s)")
                                        
                                    submitted = st.form_submit_button("✅ Finalizar", type="primary", use_container_width=True)
                                    if submitted:
                                        if ccs_escolhidos_val:
                                            st.session_state['rateio_psico'][uni_val] = ccs_escolhidos_val
                                            st.rerun()
                                        else:
                                            st.warning("Informe ao menos um Centro de Custo.")
                                            
                                if rateio_atual_val:
                                    st.write("---")
                                    st.caption("Rateio atual: " + ", ".join(rateio_atual_val))
                                    if st.button("🗑️ Remover rateio", key=f"psico_clr_val_{uni_val}", use_container_width=True):
                                        st.session_state['rateio_psico'].pop(uni_val, None)
                                        st.session_state.pop(n_key_ps_val, None)
                                        st.rerun()

                    c4.markdown(f"""
                    <div class="metric-card total">
                        <div class="metric-icon-container">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M21 18c0 1.66-4 3-9 3s-9-1.34-9-3V6c0-1.66 4-3 9-3s9 1.34 9 3v12zm-9 1c3.5 0 7-1 7-2v-2.12c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V16c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V9.38c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V11c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V4.88C17.28 5.56 14.75 6 12 6s-5.28-.44-7-1.12V6c0 1 3.5 2 7 2z"/></svg>
                        </div>
                        <div class="metric-content">
                            <div class="metric-label" style="line-height: 1.4;">Total Filtrado<br><span style="font-size: 10px; font-weight: 500; opacity: 0;">&nbsp;</span></div>
                            <div class="metric-value">{formatar_moeda(v_tot)}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.write("---")
            else:
                st.warning("Nenhum registro encontrado com os filtros aplicados.")
                
            if not df_filt.empty:
                # Agrupar por pessoa e tipo de custo
                df_agrupado = df_filt.groupby(['Nome', 'Departamento RM', 'Status', 'Tipo de Custo', 'Centro de Custo', 'CC Planilha', 'CC Alocado', 'Unidade Cadastro RM', 'Unidade Original FAT', 'Unidade Alocada', 'Empresa CTT', 'Filial CTT', 'Unidade Listagem']).agg(
                    Valor_Total=('Valor (R$)', 'sum'),
                    IDs=('ID_Linha', list)
                ).reset_index()
                
                df_agrupado['Valor_Total'] = pd.to_numeric(df_agrupado['Valor_Total'], errors='coerce').fillna(0.0)
                df_agrupado['Centro de Custo'] = df_agrupado['Centro de Custo'].astype(str).str.replace('nan - nan', 'SEM CC', regex=False).replace('nan', 'SEM CC')
                df_agrupado['CC Alocado'] = df_agrupado['CC Alocado'].astype(str).str.replace('nan - nan', 'SEM CC', regex=False).replace('nan', 'SEM CC')
                
                # Calcular divergência para o grupo
                df_agrupado['Divergência'] = df_agrupado.apply(calcular_divergencia, axis=1)
                # Marcar linhas cujo Centro de Custo está INATIVO no CTT
                df_agrupado['CC Inativo'] = df_agrupado['Centro de Custo'].apply(_cc_inativo)

                # ===== Barra de ferramentas de seleção em massa =====
                tb = st.container(border=True)
                with tb:
                    st.markdown('<div class="toolbar-title">⚡ Ações em massa</div>', unsafe_allow_html=True)
                    tb1, tb2 = st.columns([3, 2], vertical_alignment="center")
                reset_key = st.session_state.get(f"reset_sel_{uni_val}", 0)
                selecionar_todos = tb1.checkbox("☑️ Selecionar todos os filtrados", key=f"sel_todos_{uni_val}_{reset_key}", help="Marca todos os registros visíveis para alteração em lote")
                count_container = tb2.empty()

                df_agrupado.insert(0, '☑️ Selecionar', selecionar_todos)
                df_agrupado.insert(1, '❌ Excluir', False)
                
                # Reorganizar colunas para exibição lógica
                colunas_display = [
                    'Divergência',
                    'CC Inativo',
                    '☑️ Selecionar',
                    'Nome',
                    'Departamento RM',
                    'Status',
                    'Tipo de Custo',
                    'Valor_Total',
                    'Unidade Original FAT',
                    'Unidade Cadastro RM',
                    'Unidade Alocada',
                    'Centro de Custo',
                    'CC Planilha',
                    'CC Alocado',
                    '❌ Excluir',
                    'IDs'
                ]
                df_edit = df_agrupado[colunas_display].copy()

                # Badge visual de status (apenas exibição — não altera o dado de origem)
                def _status_badge(s):
                    su = str(s).strip().upper()
                    if 'PEND' in su:
                        return f"🟡 {s}"
                    if su in ('ATIVO', 'ATIVA'):
                        return f"🟢 {s}"
                    if su in ('INATIVO', 'INATIVA', 'DEMITIDO', 'DESLIGADO'):
                        return f"🔴 {s}"
                    if su in ('', 'NAN', 'NÃO INFORMADO', 'NAO INFORMADO'):
                        return f"⚪ {s}"
                    return f"🔵 {s}"
                df_edit['Status'] = df_edit['Status'].apply(_status_badge)

                def highlight_row(row):
                    # Vermelho = CC inativo (prioridade) · Amarelo = divergência RM x Planilha · Zebra = contraste
                    if row['CC Inativo']:
                        return ['background-color: rgba(239, 68, 68, 0.22)'] * len(row)
                    if row['Divergência'] != '✅ OK':
                        return ['background-color: rgba(255, 193, 7, 0.22)'] * len(row)
                    if row.name % 2 == 1:
                        return ['background-color: rgba(99, 102, 241, 0.05)'] * len(row)
                    return [''] * len(row)

                styled_df = df_edit.style.format({'Valor_Total': lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')}).apply(highlight_row, axis=1)
                
                with st.form(key=f"form_alteracao_{uni_val}", border=False):
                    with st.popover("🛠️ Alterar Unid/Custo"):
                        st.markdown("#### Selecione a alteração desejada")
                        
                        cc_key = f"novo_cc_{uni_val}"
                        uni_key = f"nova_uni_{uni_val}"
                        
                        novo_cc_lote = st.selectbox("Novo Centro de Custo", options=["(Manter atual)"] + lista_cc_filtrada, key=cc_key)
                        nova_uni_lote = st.selectbox("Nova Unidade", options=["(Manter atual)"] + unidades_reais, key=uni_key)
                        
                        st.markdown('<div class="unit-alert alert-danger" style="margin-top: 10px;">⚠️ <b>Atenção:</b> Ao transferir um custo para outra unidade você está jogando esse valor em outra nota fiscal. Confirmar se essa transferência pode ser feita de acordo com os cadastros na plataforma da Parceiro_Y.<br><br>A nota é emitida conforme o cadastro no sistema, se estiver divergente da nossa base de dados do RM precisamos ajustar no sistema deles.</div>', unsafe_allow_html=True)
                        confirmar = st.checkbox("Estou ciente e desejo confirmar (necessário apenas para alterar Unidade)", key=f"confirm_{uni_val}")
                        
                        submit_btn = st.form_submit_button("Aplicar Selecionados", type="primary", use_container_width=True)

                    edited_df = st.data_editor(
                        styled_df,
                        column_config={
                            "☑️ Selecionar": st.column_config.CheckboxColumn("☑️", help="Selecione para alterar em lote", width="small"),
                            "❌ Excluir": st.column_config.CheckboxColumn("❌", help="Marque para excluir este custo", width="small"),
                            "Divergência": None, # Ocultar (usada só para pintar a linha)
                            "CC Inativo": None, # Ocultar (usada só para pintar a linha)
                            "CC Planilha": None, # Ocultar
                            "IDs": None, # Ocultar
                            "Nome": st.column_config.TextColumn("Nome", width="large"),
                            "Departamento RM": st.column_config.TextColumn("Departamento", width="medium"),
                            "Status": st.column_config.TextColumn("Status", width="small"),
                            "Tipo de Custo": st.column_config.TextColumn("Tipo", width="small"),
                            "Valor_Total": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", width="small"),
                            "Unidade Original FAT": st.column_config.TextColumn("Unid. Original (FAT)", width="medium"),
                            "Unidade Cadastro RM": st.column_config.TextColumn("Unid. Cadastro (RM)", width="medium"),
                            "Unidade Alocada": st.column_config.TextColumn("Unid. Alocada", width="medium"),
                            "Centro de Custo": st.column_config.TextColumn("Centro de Custo", width="medium"),
                            "CC Alocado": st.column_config.TextColumn("CC Alocado", width="medium"),
                        },
                        disabled=["Nome", "Departamento RM", "Status", "Tipo de Custo", "Centro de Custo", "CC Planilha", "Unidade Cadastro RM", "Unidade Original FAT", "Valor_Total", "Unidade Alocada", "CC Alocado"],
                        use_container_width=True,
                        hide_index=True,
                        key=f"editor_modal_{uni_val}_{reset_key}",
                        height=560
                    )

                # Atualiza o contador de seleção na barra de ferramentas
                _n_sel = int(edited_df['☑️ Selecionar'].sum()) if '☑️ Selecionar' in edited_df.columns else 0
                _n_tot = len(edited_df)
                count_container.markdown(
                    f'<div class="sel-badge {"on" if _n_sel else ""}">{_n_sel} de {_n_tot} selecionado(s)</div>',
                    unsafe_allow_html=True,
                )

                if submit_btn:
                    if nova_uni_lote != "(Manter atual)" and not confirmar:
                        st.error("Para transferir para outra Unidade, marque a caixa de confirmação acima.")
                    else:
                        linhas_selecionadas = edited_df[edited_df['☑️ Selecionar']]
                        if not linhas_selecionadas.empty:
                            for _, r_sel in linhas_selecionadas.iterrows():
                                for id_linha in r_sel['IDs']:
                                    aloc = st.session_state['alocacoes_manuais'].get(id_linha, {})
                                    if isinstance(aloc, str):
                                        aloc = {'Unidade Alocada': aloc}
                                    if novo_cc_lote != "(Manter atual)":
                                        aloc['CC Alocado'] = novo_cc_lote
                                    if nova_uni_lote != "(Manter atual)":
                                        aloc['Unidade Alocada'] = nova_uni_lote
                                    st.session_state['alocacoes_manuais'][id_linha] = aloc
                            try:
                                current_val = int(st.session_state.get(f"reset_sel_{uni_val}", 0))
                            except (ValueError, TypeError):
                                current_val = 0
                            st.session_state[f"reset_sel_{uni_val}"] = current_val + 1
                            
                            # Limpa os selects após a ação
                            st.session_state.pop(cc_key, None)
                            st.session_state.pop(uni_key, None)
                            st.session_state.pop(f"confirm_{uni_val}", None)
                            
                            st.rerun()
                        else:
                            st.warning("Selecione ao menos um item na lista abaixo para aplicar a alteração.")
                
                # Detectar exclusões
                if not edited_df.equals(df_edit):
                    diff_excl = edited_df[edited_df['❌ Excluir'] != df_edit['❌ Excluir']]
                    if not diff_excl.empty:
                        for _, r_diff in diff_excl.iterrows():
                            if r_diff['❌ Excluir']:
                                st.session_state['linhas_excluidas'].update(r_diff['IDs'])
                        st.rerun()
                    
                st.write("")
                buf_export = io.BytesIO()
                # O export vai remover os excluidos
                df_export = df_consolidado[~df_consolidado['ID_Linha'].isin(st.session_state['linhas_excluidas'])]
                if 'unidades_excluidas' in st.session_state:
                    df_export = df_export[~df_export['Unidade Alocada'].isin(st.session_state['unidades_excluidas'])]
                df_export = df_export.drop(columns=['ID_Linha'])
                df_export.to_excel(buf_export, index=False, engine='openpyxl')
                st.download_button("📥 Baixar Planilha Consolidada Validada", buf_export.getvalue(), "Relatorio_Final_Validado.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            elif df_uni.empty:
                st.success("Não há mais custos alocados para esta unidade. Ela desaparecerá do painel.")
                
            if not df_uni_excluidos.empty:
                with st.expander(f"🗑️ Custos Excluídos ( {len(df_uni_excluidos)} registros )"):
                    st.dataframe(df_uni_excluidos.drop(columns=['ID_Linha']), use_container_width=True)
                    if st.button("Restaurar Todos os Excluídos Desta Unidade"):
                        st.session_state['linhas_excluidas'] -= set(df_uni_excluidos['ID_Linha'])
                        st.rerun()
            
            st.stop() # Bloqueia a renderização do restante da tela!

        st.subheader("📊 Gestão de Alocação de Custos")

        tab_resumo, tab_parceiro_y, tab_outros = st.tabs([
            "📊 Painel de Resumo (Corrigido)", 
            "📑 Painel de Resumo (Parceiro_Y)",
            "📂 Outros Faturamentos"
        ])
        
        with tab_resumo:
            def gerar_resumo_excel(df_cons):
                linhas_excluidas = st.session_state.get('linhas_excluidas', set())
                unidades_excluidas = st.session_state.get('unidades_excluidas', set())
                
                df_valido = df_cons[~df_cons['ID_Linha'].isin(linhas_excluidas)]
                df_valido = df_valido[~df_valido['Unidade Alocada'].isin(unidades_excluidas)]
                
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                    unidades = sorted(df_valido['Unidade Alocada'].dropna().unique())
                    
                    for u in unidades:
                        df_u = df_valido[df_valido['Unidade Alocada'] == u]
                        if df_u.empty:
                            continue
                            
                        pivot = df_u.groupby(['CC Alocado', 'Tipo de Custo']).agg(
                            Quantidade=('ID_Linha', 'count'),
                            Valor_Total=('Valor (R$)', 'sum')
                        ).reset_index()
                        
                        if pivot.empty:
                            continue
                            
                        pivot_q = pivot.pivot(index='CC Alocado', columns='Tipo de Custo', values='Quantidade').fillna(0)
                        pivot_v = pivot.pivot(index='CC Alocado', columns='Tipo de Custo', values='Valor_Total').fillna(0)
                        
                        df_final = pd.DataFrame(index=pivot_q.index)
                        tipos_custo_ordenados = sorted(pivot['Tipo de Custo'].unique())
                        
                        for tipo in tipos_custo_ordenados:
                            df_final[f"Qtd {tipo}"] = pivot_q[tipo]
                            df_final[f"Valor {tipo}"] = pivot_v[tipo]
                            
                        df_final['Qtd Total'] = df_final[[col for col in df_final.columns if col.startswith('Qtd')]].sum(axis=1)
                        df_final['Valor Total Geral'] = df_final[[col for col in df_final.columns if col.startswith('Valor')]].sum(axis=1)
                        
                        df_final = df_final.reset_index().rename(columns={'CC Alocado': 'Centro de Custo'})
                        
                        # --- ADICIONANDO DESCONTO E O RESUMO ---
                        extra_rows = []
                        extra_rows.append({c: None for c in df_final.columns}) # Empty row separator
                        
                        descontos = st.session_state.get('descontos_unidades', {}).get(u, [])
                        if isinstance(descontos, dict):
                            descontos = [descontos] if descontos.get('valor', 0) > 0 else []
                            
                        valor_total_descontos = 0
                        for d in descontos:
                            if d.get('valor', 0) > 0:
                                extra_rows.append({'Centro de Custo': f"DESCONTO: {d['motivo']}", 'Valor Total Geral': -d['valor']})
                                valor_total_descontos += d['valor']
                                
                        extra_rows.append({c: None for c in df_final.columns})
                        extra_rows.append({'Centro de Custo': 'RESUMO DA UNIDADE'})
                        
                        qtd_ex = len(df_u[df_u['Tipo de Custo'].str.contains('Exame', na=False, case=False)])
                        val_ex = df_u[df_u['Tipo de Custo'].str.contains('Exame', na=False, case=False)]['Valor (R$)'].sum()
                        qtd_vi = len(df_u[df_u['Tipo de Custo'].str.contains('Vida', na=False, case=False)])
                        val_vi = df_u[df_u['Tipo de Custo'].str.contains('Vida', na=False, case=False)]['Valor (R$)'].sum()
                        qtd_fa = len(df_u[df_u['Tipo de Custo'].str.contains('Falta', na=False, case=False)])
                        val_fa = df_u[df_u['Tipo de Custo'].str.contains('Falta', na=False, case=False)]['Valor (R$)'].sum()
                        
                        custo_total_unidade = df_u['Valor (R$)'].sum() - valor_total_descontos
                        if custo_total_unidade < 146 and qtd_ex == 0:
                            extra_rows.append({'Centro de Custo': 'MENSALIDADE SAUDE OCUPACIONAL', 'Valor Total Geral': 146.00})
                            custo_total_unidade = 146.00
                            
                        extra_rows.append({'Centro de Custo': 'Exames', 'Qtd Total': qtd_ex, 'Valor Total Geral': val_ex})
                        extra_rows.append({'Centro de Custo': 'Vidas Ativas', 'Qtd Total': qtd_vi, 'Valor Total Geral': val_vi})
                        extra_rows.append({'Centro de Custo': 'Faltas', 'Qtd Total': qtd_fa, 'Valor Total Geral': val_fa})
                        extra_rows.append({'Centro de Custo': 'CUSTO TOTAL', 'Valor Total Geral': custo_total_unidade})
                        
                        df_final = pd.concat([df_final, pd.DataFrame(extra_rows)], ignore_index=True)
                        # ------------------------------------
                        
                        sheet_name = str(u)[:31]
                        for char in ['[', ']', ':', '*', '?', '/', '\\']:
                            sheet_name = sheet_name.replace(char, '')
                            
                        df_final.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                    if not unidades:
                        pd.DataFrame({'Aviso': ['Sem dados válidos']}).to_excel(writer, sheet_name='Sem Dados', index=False)
    
                return buf.getvalue()

            st.download_button(
                label="📥 Baixar Resumo em Excel (Por Centro de Custo)",
                data=gerar_resumo_excel(df_consolidado),
                file_name="Resumo_Dinamico_Faturamento.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            st.write("")

            df_resumo_ativas = df_resumo_unidades[~df_resumo_unidades['Unidade'].isin(st.session_state['unidades_excluidas'])]
            df_resumo_excluidas = df_resumo_unidades[df_resumo_unidades['Unidade'].isin(st.session_state['unidades_excluidas'])]
            
            tot_ex = df_resumo_ativas['Exames (R$)'].sum()
            tot_ps = df_resumo_ativas['Psicossocial (R$)'].sum()
            tot_vi = df_resumo_ativas['Vidas Ativas (R$)'].sum()
            tot_fa = df_resumo_ativas['Faltas (R$)'].sum()

            total_descontos_geral = 0
            for u in df_resumo_ativas['Unidade']:
                d_info = st.session_state['descontos_unidades'].get(u, [])
                if isinstance(d_info, dict):
                    total_descontos_geral += d_info.get('valor', 0.0)
                else:
                    total_descontos_geral += sum(d.get('valor', 0.0) for d in d_info)
            tot_geral = df_resumo_ativas['Total Geral (R$)'].sum() - total_descontos_geral

            tot_q_ex = df_resumo_ativas['Qtd Exames'].sum()
            tot_q_ps = df_resumo_ativas['Qtd Psicossocial'].sum()
            tot_q_vi = df_resumo_ativas['Qtd Vidas'].sum()
            tot_q_fa = df_resumo_ativas['Qtd Faltas'].sum()

            # --- Criação do Snapshot para Histórico ---
            unidades_list = []
            for _, r in df_resumo_ativas.iterrows():
                u_dict = {}
                for k, v in r.items():
                    if pd.isna(v): u_dict[k] = None
                    elif hasattr(v, 'item'): u_dict[k] = v.item()
                    else: u_dict[k] = v
                unidades_list.append(u_dict)
                
            snapshot = {
                'tot_geral': float(tot_geral),
                'tot_ex': float(tot_ex),
                'tot_ps': float(tot_ps),
                'tot_vi': float(tot_vi),
                'tot_fa': float(tot_fa),
                'tot_q_ex': int(tot_q_ex),
                'tot_q_ps': int(tot_q_ps),
                'tot_q_vi': int(tot_q_vi),
                'tot_q_fa': int(tot_q_fa),
                'unidades': unidades_list
            }
            
            # Só dispara a gravação se o snapshot tiver mudado
            if json.dumps(st.session_state.get('ultimo_resumo_snapshot', {})) != json.dumps(snapshot):
                st.session_state['ultimo_resumo_snapshot'] = snapshot
                salvar_ajustes(fonte_dados, current_file_id)
            # ----------------------------------------

            st.markdown("### Resumo Consolidado do Mês")
            r_c1, r_c2, r_c3, r_cp, r_c4 = st.columns(5)
            
            r_c1.markdown(f"""
            <div class="metric-card exames">
                <div class="metric-icon-container">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                </div>
                <div class="metric-content">
                    <div class="metric-label" style="font-size: 12px; line-height: 1.4;">EXAMES<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {int(tot_q_ex)} UN</span></div>
                    <div class="metric-value">{formatar_moeda(tot_ex)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            r_c2.markdown(f"""
            <div class="metric-card vidas">
                <div class="metric-icon-container">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                </div>
                <div class="metric-content">
                    <div class="metric-label" style="font-size: 12px; line-height: 1.4;">VIDAS ATIVAS<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {int(tot_q_vi)} UN</span></div>
                    <div class="metric-value">{formatar_moeda(tot_vi)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            r_c3.markdown(f"""
            <div class="metric-card faltas">
                <div class="metric-icon-container">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line><line x1="9" y1="14" x2="15" y2="20"></line><line x1="15" y1="14" x2="9" y2="20"></line></svg>
                </div>
                <div class="metric-content">
                    <div class="metric-label" style="font-size: 12px; line-height: 1.4;">FALTAS<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {int(tot_q_fa)} UN</span></div>
                    <div class="metric-value">{formatar_moeda(tot_fa)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            r_cp.markdown(f"""
            <div class="metric-card psico">
                <div class="metric-icon-container">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                </div>
                <div class="metric-content">
                    <div class="metric-label" style="font-size: 12px; line-height: 1.4;">PSICOSSOCIAL<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {int(tot_q_ps)} UN</span></div>
                    <div class="metric-value">{formatar_moeda(tot_ps)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            r_c4.markdown(f"""
            <div class="metric-card total">
                <div class="metric-icon-container">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M21 18c0 1.66-4 3-9 3s-9-1.34-9-3V6c0-1.66 4-3 9-3s9 1.34 9 3v12zm-9 1c3.5 0 7-1 7-2v-2.12c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V16c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V9.38c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V11c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V4.88C17.28 5.56 14.75 6 12 6s-5.28-.44-7-1.12V6c0 1 3.5 2 7 2z"/></svg>
                </div>
                <div class="metric-content">
                    <div class="metric-label" style="line-height: 1.4;">Custo Total<br><span style="font-size: 10px; font-weight: 500; opacity: 0;">&nbsp;</span></div>
                    <div class="metric-value">{formatar_moeda(tot_geral)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.write("---")

            st.markdown("### Detalhamento por Unidade")
            for _, row in df_resumo_ativas.sort_values(by='Total Geral (R$)', ascending=False).iterrows():
                descontos_unidade = st.session_state['descontos_unidades'].get(row['Unidade'], [])
                if isinstance(descontos_unidade, dict):
                    descontos_unidade = [descontos_unidade] if descontos_unidade.get('valor', 0) > 0 else []
                    
                valor_desconto = sum(d.get('valor', 0.0) for d in descontos_unidade)
                total_final = row['Total Geral (R$)'] - valor_desconto
                
                if total_final > 0 or row['Total Geral (R$)'] > 0:
                    with st.container(border=True):
                        st.markdown(f"""
                        <div class="unit-header">
                            🏢 {row['Unidade']}
                        </div>
                        """, unsafe_allow_html=True)

                        c1, c2, c3, cp, c4, c5, cd, c6 = st.columns([1.5, 1.5, 1.5, 1.5, 1.7, 1.15, 1.25, 1.15], vertical_alignment="center")
                        
                        c1.markdown(f"""
                        <div class="unit-metric">
                            <div class="unit-metric-label">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #10b981;"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                                Exames
                            </div>
                            <div class="unit-metric-value">{row['Qtd Exames']} un</div>
                            <div class="unit-metric-pill">{formatar_moeda(row['Exames (R$)'])}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        dup_badge = ""
                        if row.get('Vidas Duplicadas', 0) > 0:
                            dup_badge = (
                                f'<div style="font-size:10px;color:#b45309;font-weight:700;margin-top:4px;'
                                f'background:rgba(245,158,11,0.12);padding:3px 7px;border-radius:5px;'
                                f'display:inline-block;" title="Mesma pessoa cobrada mais de uma vez">'
                                f'⚠️ {int(row["Vidas Duplicadas"])} duplicada(s)</div>'
                            )

                        c2.markdown(f"""
                        <div class="unit-metric">
                            <div class="unit-metric-label">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #3b82f6;"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                                Vidas
                            </div>
                            <div class="unit-metric-value">{row['Qtd Vidas']} un</div>
                            <div class="unit-metric-pill">{formatar_moeda(row['Vidas Ativas (R$)'])}</div>
                            {dup_badge}
                        </div>
                        """, unsafe_allow_html=True)

                        c3.markdown(f"""
                        <div class="unit-metric">
                            <div class="unit-metric-label">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #ef4444;"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line><line x1="9" y1="14" x2="15" y2="20"></line><line x1="15" y1="14" x2="9" y2="20"></line></svg>
                                Faltas
                            </div>
                            <div class="unit-metric-value">{row['Qtd Faltas']} un</div>
                            <div class="unit-metric-pill">{formatar_moeda(row['Faltas (R$)'])}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        cp.markdown(f"""
                        <div class="unit-metric">
                            <div class="unit-metric-label">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #0891b2;"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                                Psicossocial
                            </div>
                            <div class="unit-metric-value">{row['Qtd Psicossocial']} un</div>
                            <div class="unit-metric-pill">{formatar_moeda(row['Psicossocial (R$)'])}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        aviso_mensalidade = ""
                        if total_final < 146 and row['Qtd Exames'] == 0:
                            aviso_mensalidade = """<div style="font-size: 11px; color: #ef4444; font-weight: 700; margin-top: 4px; background-color: rgba(239, 68, 68, 0.1); padding: 4px 8px; border-radius: 4px; display: inline-block;">⚠️ MENSALIDADE SAUDE OCUPACIONAL: R$ 146,00</div>"""

                        aviso_desconto = ""
                        for d in descontos_unidade:
                            if d.get('valor', 0) > 0:
                                aviso_desconto += f"""<div style="font-size: 11px; color: #10b981; font-weight: 700; margin-top: 4px; background-color: rgba(16, 185, 129, 0.1); padding: 4px 8px; border-radius: 4px; display: block; width: fit-content; margin-bottom: 2px;">⬇️ DESCONTO: -R$ {d['valor']:,.2f} ({d['motivo']})</div>"""

                        avisos_html = ""
                        if aviso_desconto or aviso_mensalidade:
                            avisos_html = f"{aviso_desconto}{aviso_mensalidade}"

                        c4.markdown(f"""
                        <div class="unit-metric">
                            <div class="unit-metric-label">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="color: #d97706;"><path d="M21 18c0 1.66-4 3-9 3s-9-1.34-9-3V6c0-1.66 4-3 9-3s9 1.34 9 3v12zm-9 1c3.5 0 7-1 7-2v-2.12c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V16c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V9.38c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V11c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V4.88C17.28 5.56 14.75 6 12 6s-5.28-.44-7-1.12V6c0 1 3.5 2 7 2z"/></svg>
                                Total Unidade
                            </div>
                            <div class="unit-metric-value-total">{formatar_moeda(total_final)}</div>
                            {avisos_html}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with c5:
                            if st.button("🔍 Validar", key=f"btn_detalhar_{row['Unidade']}", use_container_width=True, help="Abrir o formulário de validação detalhada"):
                                st.session_state['unidade_validacao'] = row['Unidade']
                                st.rerun()
                            
                        with cd:
                            with st.popover("✏️ Desconto", use_container_width=True):
                                st.markdown(f"**Descontos para {row['Unidade']}**")
                                
                                if descontos_unidade:
                                    for idx, d in enumerate(descontos_unidade):
                                        st.write(f"- R$ {d['valor']:.2f}: {d['motivo']}")
                                    if st.button("🗑️ Limpar Todos", key=f"clear_desc_{row['Unidade']}", help="Remover descontos desta unidade"):
                                        st.session_state['descontos_unidades'][row['Unidade']] = []
                                        st.rerun()
                                    st.write("---")
                                    
                                st.markdown("**Novo Desconto**")
                                val_desc = st.number_input("Valor (R$)", min_value=0.0, step=0.1, key=f"desc_val_{row['Unidade']}")
                                motivo_desc = st.text_input("Motivo", key=f"desc_mot_{row['Unidade']}")
                                if st.button("Adicionar Desconto", type="primary", key=f"desc_btn_{row['Unidade']}"):
                                    if val_desc > 0:
                                        st.session_state['descontos_unidades'][row['Unidade']] = descontos_unidade
                                        st.session_state['descontos_unidades'][row['Unidade']].append({'valor': val_desc, 'motivo': motivo_desc})
                                        st.rerun()
                                    else:
                                        st.warning("O valor deve ser maior que zero.")
                            
                        with c6:
                            if st.button("❌ Excluir", key=f"btn_excluir_uni_{row['Unidade']}", use_container_width=True, help="Remover esta unidade do faturamento"):
                                st.session_state['unidades_excluidas'].add(row['Unidade'])
                                st.rerun()
                    
            if not df_resumo_excluidas.empty:
                st.write("")
                with st.expander(f"🗑️ Unidades Excluídas ({len(df_resumo_excluidas)})", expanded=False):
                    for _, row in df_resumo_excluidas.sort_values(by='Total Geral (R$)', ascending=False).iterrows():
                        ce1, ce2, ce3 = st.columns([6, 2, 2], vertical_alignment="center")
                        
                        detalhes = []
                        if row.get('Vidas Ativas (R$)', 0) > 0:
                            detalhes.append(f"Vidas: {formatar_moeda(row.get('Vidas Ativas (R$)', 0))}")
                        if row.get('Exames (R$)', 0) > 0:
                            detalhes.append(f"Exames: {formatar_moeda(row.get('Exames (R$)', 0))}")
                        if row.get('Psicossocial (R$)', 0) > 0:
                            detalhes.append(f"Psicossocial: {formatar_moeda(row.get('Psicossocial (R$)', 0))}")
                        if row.get('Faltas (R$)', 0) > 0:
                            detalhes.append(f"Faltas: {formatar_moeda(row.get('Faltas (R$)', 0))}")
                        
                        detalhes_html = f"<br><span style='font-size:12px; color:#64748b; font-weight:500;'>{' &bull; '.join(detalhes)}</span>" if detalhes else ""
                        
                        ce1.markdown(f"<div style='line-height:1.4;'><b>🏢 {row['Unidade']}</b>{detalhes_html}</div>", unsafe_allow_html=True)
                        ce2.markdown(f"<b>{formatar_moeda(row['Total Geral (R$)'])}</b>", unsafe_allow_html=True)
                        with ce3:
                            if st.button("🔄 Restaurar", key=f"btn_restaurar_uni_{row['Unidade']}", use_container_width=True):
                                st.session_state['unidades_excluidas'].remove(row['Unidade'])
                                st.rerun()
                        st.markdown("<hr style='margin: 5px 0; border-color: #e2e8f0;'>", unsafe_allow_html=True)

        with tab_parceiro_y:
            tot_geral_m = df_resumo_parceiro_y['Total Geral (R$)'].sum()
            tot_ex_m = df_resumo_parceiro_y['Exames (R$)'].sum()
            tot_ps_m = df_resumo_parceiro_y['Psicossocial (R$)'].sum()
            tot_vi_m = df_resumo_parceiro_y['Vidas Ativas (R$)'].sum()
            tot_fa_m = df_resumo_parceiro_y['Faltas (R$)'].sum()

            tot_q_ex_m = df_resumo_parceiro_y['Qtd Exames'].sum()
            tot_q_ps_m = df_resumo_parceiro_y['Qtd Psicossocial'].sum()
            tot_q_vi_m = df_resumo_parceiro_y['Qtd Vidas'].sum()
            tot_q_fa_m = df_resumo_parceiro_y['Qtd Faltas'].sum()

            st.markdown("### Resumo Original (Faturado pela Parceiro_Y)")
            rm_c1, rm_c2, rm_c3, rm_cp, rm_c4 = st.columns(5)
            
            rm_c1.markdown(f"""
            <div class="metric-card exames">
                <div class="metric-icon-container">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                </div>
                <div class="metric-content">
                    <div class="metric-label" style="font-size: 12px; line-height: 1.4;">EXAMES<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {int(tot_q_ex_m)} UN</span></div>
                    <div class="metric-value">{formatar_moeda(tot_ex_m)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            rm_c2.markdown(f"""
            <div class="metric-card vidas">
                <div class="metric-icon-container">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                </div>
                <div class="metric-content">
                    <div class="metric-label" style="font-size: 12px; line-height: 1.4;">VIDAS ATIVAS<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {int(tot_q_vi_m)} UN</span></div>
                    <div class="metric-value">{formatar_moeda(tot_vi_m)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            rm_c3.markdown(f"""
            <div class="metric-card faltas">
                <div class="metric-icon-container">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line><line x1="9" y1="14" x2="15" y2="20"></line><line x1="15" y1="14" x2="9" y2="20"></line></svg>
                </div>
                <div class="metric-content">
                    <div class="metric-label" style="font-size: 12px; line-height: 1.4;">FALTAS<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {int(tot_q_fa_m)} UN</span></div>
                    <div class="metric-value">{formatar_moeda(tot_fa_m)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            rm_cp.markdown(f"""
            <div class="metric-card psico">
                <div class="metric-icon-container">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                </div>
                <div class="metric-content">
                    <div class="metric-label" style="font-size: 12px; line-height: 1.4;">PSICOSSOCIAL<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {int(tot_q_ps_m)} UN</span></div>
                    <div class="metric-value">{formatar_moeda(tot_ps_m)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            rm_c4.markdown(f"""
            <div class="metric-card total">
                <div class="metric-icon-container">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M21 18c0 1.66-4 3-9 3s-9-1.34-9-3V6c0-1.66 4-3 9-3s9 1.34 9 3v12zm-9 1c3.5 0 7-1 7-2v-2.12c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V16c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V9.38c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V11c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V4.88C17.28 5.56 14.75 6 12 6s-5.28-.44-7-1.12V6c0 1 3.5 2 7 2z"/></svg>
                </div>
                <div class="metric-content">
                    <div class="metric-label" style="line-height: 1.4;">Custo Total<br><span style="font-size: 10px; font-weight: 500; opacity: 0;">&nbsp;</span></div>
                    <div class="metric-value">{formatar_moeda(tot_geral_m)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.write("---")

            st.markdown("### Faturamento Original por Unidade")
            for _, row in df_resumo_parceiro_y.sort_values(by='Total Geral (R$)', ascending=False).iterrows():
                if row['Total Geral (R$)'] > 0:
                    with st.container(border=True):
                        st.markdown(f"""
                        <div class="unit-header">
                            🏢 {row['Unidade']}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        cm1, cm2, cm3, cmp, cm4 = st.columns([1.5, 1.5, 1.5, 1.5, 1.8])
                        
                        cm1.markdown(f"""
                        <div class="unit-metric">
                            <div class="unit-metric-label">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #10b981;"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                                Exames
                            </div>
                            <div class="unit-metric-value">{row['Qtd Exames']} un</div>
                            <div class="unit-metric-pill">{formatar_moeda(row['Exames (R$)'])}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        dup_badge_m = ""
                        if row.get('Vidas Duplicadas', 0) > 0:
                            dup_badge_m = (
                                f'<div style="font-size:10px;color:#b45309;font-weight:700;margin-top:4px;'
                                f'background:rgba(245,158,11,0.12);padding:3px 7px;border-radius:5px;'
                                f'display:inline-block;" title="Mesma pessoa cobrada mais de uma vez">'
                                f'⚠️ {int(row["Vidas Duplicadas"])} duplicada(s)</div>'
                            )

                        cm2.markdown(f"""
                        <div class="unit-metric">
                            <div class="unit-metric-label">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #3b82f6;"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                                Vidas
                            </div>
                            <div class="unit-metric-value">{row['Qtd Vidas']} un</div>
                            <div class="unit-metric-pill">{formatar_moeda(row['Vidas Ativas (R$)'])}</div>
                            {dup_badge_m}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        cm3.markdown(f"""
                        <div class="unit-metric">
                            <div class="unit-metric-label">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #ef4444;"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line><line x1="9" y1="14" x2="15" y2="20"></line><line x1="15" y1="14" x2="9" y2="20"></line></svg>
                                Faltas
                            </div>
                            <div class="unit-metric-value">{row['Qtd Faltas']} un</div>
                            <div class="unit-metric-pill">{formatar_moeda(row['Faltas (R$)'])}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        cmp.markdown(f"""
                        <div class="unit-metric">
                            <div class="unit-metric-label">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #0891b2;"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                                Psicossocial
                            </div>
                            <div class="unit-metric-value">{row['Qtd Psicossocial']} un</div>
                            <div class="unit-metric-pill">{formatar_moeda(row['Psicossocial (R$)'])}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        cm4.markdown(f"""
                        <div class="unit-metric">
                            <div class="unit-metric-label">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="color: #d97706;"><path d="M21 18c0 1.66-4 3-9 3s-9-1.34-9-3V6c0-1.66 4-3 9-3s9 1.34 9 3v12zm-9 1c3.5 0 7-1 7-2v-2.12c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V16c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V9.38c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V11c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V4.88C17.28 5.56 14.75 6 12 6s-5.28-.44-7-1.12V6c0 1 3.5 2 7 2z"/></svg>
                                Total Faturado
                            </div>
                            <div class="unit-metric-value-total">{formatar_moeda(row['Total Geral (R$)'])}</div>
                        </div>
                        """, unsafe_allow_html=True)

        with tab_outros:
            st.markdown("### 📂 Histórico de Faturamento")
            st.write("Selecione um mês anterior para visualizar o faturamento com a mesma visão do Painel de Resumo.")
            
            if caminho_onedrive:
                pasta = os.path.dirname(caminho_onedrive)
                pasta_hist = os.path.join(pasta, 'Histórico')
                
                # Busca os JSONs na pasta Histórico (se existir), ou usa a pasta principal como fallback (legado)
                arquivos_hist = []
                if os.path.exists(pasta_hist):
                    arquivos_hist.extend(glob.glob(os.path.join(pasta_hist, 'ajustes_hist_*.json')))
                arquivos_hist.extend(glob.glob(os.path.join(pasta, 'ajustes_hist_*.json')))
                if arquivos_hist:
                    metadata_path = os.path.join(pasta_hist, "metadata.json")
                    metadata_hist = {}
                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path, 'r', encoding='utf-8') as fm:
                                metadata_hist = json.load(fm)
                        except Exception:
                            pass
                            
                    def get_sort_key(arq_path):
                        nome_arq = os.path.basename(arq_path)
                        last_mod = metadata_hist.get(nome_arq)
                        if last_mod:
                            return str(last_mod)
                        return str(_dt.datetime.fromtimestamp(os.path.getmtime(arq_path)))
                        
                    arquivos_hist = sorted(list(set(arquivos_hist)), key=get_sort_key, reverse=True)
                    
                    opcoes = {}
                    import datetime as _dt
                    for arq in arquivos_hist:
                        nome_arq = os.path.basename(arq)
                        nome_limpo = nome_arq.replace("ajustes_hist_", "").replace(".json", "")
                        last_mod_str = metadata_hist.get(nome_arq)
                        
                        if last_mod_str:
                            try:
                                dt_obj = _dt.datetime.fromisoformat(last_mod_str.replace("Z", "+00:00"))
                                dt_obj = dt_obj + _dt.timedelta(hours=-3)
                                data_mtime = dt_obj.strftime('%d/%m/%Y %H:%M')
                            except Exception:
                                data_mtime = _dt.datetime.fromtimestamp(os.path.getmtime(arq)).strftime('%d/%m/%Y %H:%M')
                        else:
                            data_mtime = _dt.datetime.fromtimestamp(os.path.getmtime(arq)).strftime('%d/%m/%Y %H:%M')
                            
                        label = f"{nome_limpo} (Atualizado em {data_mtime})"
                        opcoes[label] = arq
                        
                    selecionado = st.selectbox("Selecione a Planilha / Mês:", options=list(opcoes.keys()))
                    
                    if selecionado:
                        arq_selecionado = opcoes[selecionado]
                        try:
                            with open(arq_selecionado, 'r', encoding='utf-8') as f:
                                hist_data = json.load(f)
                                
                            st.write("---")
                            st.markdown(f"#### Consultando: **{selecionado.split(' (')[0]}**")
                            
                            # Tentar achar a planilha excel correspondente na pasta Histórico ou na Principal
                            nome_limpo = os.path.basename(arq_selecionado).replace("ajustes_hist_", "").replace(".json", "")
                            
                            caminhos_tentativa = [
                                os.path.join(pasta_hist, f"{nome_limpo}.xlsx"),
                                os.path.join(pasta_hist, f"{nome_limpo}.xls"),
                                os.path.join(pasta, f"{nome_limpo}.xlsx"),
                                os.path.join(pasta, f"{nome_limpo}.xls")
                            ]
                            
                            excel_path = None
                            for p in caminhos_tentativa:
                                if os.path.exists(p):
                                    excel_path = p
                                    break
                            
                            if excel_path:
                                with st.spinner("Processando histórico e alocações..."):
                                    df_e_hist, df_v_hist, df_f_hist, _, _ = carregar_dados(excel_path)
                                    df_cons_hist, uni_reais_hist, _, df_resumo_hist, _ = processar_faturamento_dados(
                                        df_e_hist, df_v_hist, df_f_hist, hist_data
                                    )

                                # Respeitar os mesmos ajustes salvos naquele mês (exclusões / descontos)
                                unidades_excl_hist = set(hist_data.get('unidades_excluidas', []))
                                linhas_excl_hist = set(hist_data.get('linhas_excluidas', []))
                                descontos_hist = hist_data.get('descontos_unidades', {})
                                df_resumo_hist_ativas = df_resumo_hist[~df_resumo_hist['Unidade'].isin(unidades_excl_hist)]

                                def _desconto_unidade_hist(u):
                                    d_info = descontos_hist.get(u, [])
                                    if isinstance(d_info, dict):
                                        return d_info.get('valor', 0.0) if d_info.get('valor', 0) > 0 else 0.0
                                    return sum(d.get('valor', 0.0) for d in d_info)

                                # ===== Totais do mês (mesma visão do Painel de Resumo) =====
                                h_ex = df_resumo_hist_ativas['Exames (R$)'].sum()
                                h_ps = df_resumo_hist_ativas['Psicossocial (R$)'].sum()
                                h_vi = df_resumo_hist_ativas['Vidas Ativas (R$)'].sum()
                                h_fa = df_resumo_hist_ativas['Faltas (R$)'].sum()
                                h_desc_total = sum(_desconto_unidade_hist(u) for u in df_resumo_hist_ativas['Unidade'])
                                h_geral = df_resumo_hist_ativas['Total Geral (R$)'].sum() - h_desc_total

                                h_q_ex = int(df_resumo_hist_ativas['Qtd Exames'].sum())
                                h_q_ps = int(df_resumo_hist_ativas['Qtd Psicossocial'].sum())
                                h_q_vi = int(df_resumo_hist_ativas['Qtd Vidas'].sum())
                                h_q_fa = int(df_resumo_hist_ativas['Qtd Faltas'].sum())

                                st.markdown("### Resumo Consolidado do Mês")
                                h_c1, h_c2, h_c3, h_cps, h_c4 = st.columns(5)

                                h_c1.markdown(f"""
                                <div class="metric-card exames">
                                    <div class="metric-icon-container">
                                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                                    </div>
                                    <div class="metric-content">
                                        <div class="metric-label" style="font-size: 12px; line-height: 1.4;">EXAMES<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {h_q_ex} UN</span></div>
                                        <div class="metric-value">{formatar_moeda(h_ex)}</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                h_c2.markdown(f"""
                                <div class="metric-card vidas">
                                    <div class="metric-icon-container">
                                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                                    </div>
                                    <div class="metric-content">
                                        <div class="metric-label" style="font-size: 12px; line-height: 1.4;">VIDAS ATIVAS<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {h_q_vi} UN</span></div>
                                        <div class="metric-value">{formatar_moeda(h_vi)}</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                h_c3.markdown(f"""
                                <div class="metric-card faltas">
                                    <div class="metric-icon-container">
                                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line><line x1="9" y1="14" x2="15" y2="20"></line><line x1="15" y1="14" x2="9" y2="20"></line></svg>
                                    </div>
                                    <div class="metric-content">
                                        <div class="metric-label" style="font-size: 12px; line-height: 1.4;">FALTAS<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {h_q_fa} UN</span></div>
                                        <div class="metric-value">{formatar_moeda(h_fa)}</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                h_cps.markdown(f"""
                                <div class="metric-card psico">
                                    <div class="metric-icon-container">
                                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                                    </div>
                                    <div class="metric-content">
                                        <div class="metric-label" style="font-size: 12px; line-height: 1.4;">PSICOSSOCIAL<br><span style="font-size: 10px; font-weight: 500; opacity: 0.8;">TOTAL: {h_q_ps} UN</span></div>
                                        <div class="metric-value">{formatar_moeda(h_ps)}</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                h_c4.markdown(f"""
                                <div class="metric-card total">
                                    <div class="metric-icon-container">
                                        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M21 18c0 1.66-4 3-9 3s-9-1.34-9-3V6c0-1.66 4-3 9-3s9 1.34 9 3v12zm-9 1c3.5 0 7-1 7-2v-2.12c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V16c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V9.38c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V11c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V4.88C17.28 5.56 14.75 6 12 6s-5.28-.44-7-1.12V6c0 1 3.5 2 7 2z"/></svg>
                                    </div>
                                    <div class="metric-content">
                                        <div class="metric-label" style="line-height: 1.4;">Custo Total<br><span style="font-size: 10px; font-weight: 500; opacity: 0;">&nbsp;</span></div>
                                        <div class="metric-value">{formatar_moeda(h_geral)}</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                st.write("---")

                                # ===== Detalhamento por Unidade (cards + funcionários e origem do custo) =====
                                st.markdown("### Detalhamento por Unidade")
                                st.caption("Abra uma unidade para ver o nome do funcionário de cada exame e de qual local (centro de custo / unidade de origem) veio o custo.")

                                for _, row_h in df_resumo_hist_ativas.sort_values(by='Total Geral (R$)', ascending=False).iterrows():
                                    u_h = row_h['Unidade']
                                    valor_desc_h = _desconto_unidade_hist(u_h)
                                    total_final_h = row_h['Total Geral (R$)'] - valor_desc_h

                                    if total_final_h <= 0 and row_h['Total Geral (R$)'] <= 0:
                                        continue

                                    with st.container(border=True):
                                        st.markdown(f"""
                                        <div class="unit-header">
                                            🏢 {u_h}
                                        </div>
                                        """, unsafe_allow_html=True)

                                        hu1, hu2, hu3, hup, hu4 = st.columns([1.5, 1.5, 1.5, 1.5, 1.8])

                                        hu1.markdown(f"""
                                        <div class="unit-metric">
                                            <div class="unit-metric-label">
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #10b981;"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                                                Exames
                                            </div>
                                            <div class="unit-metric-value">{row_h['Qtd Exames']} un</div>
                                            <div class="unit-metric-pill">{formatar_moeda(row_h['Exames (R$)'])}</div>
                                        </div>
                                        """, unsafe_allow_html=True)

                                        hu2.markdown(f"""
                                        <div class="unit-metric">
                                            <div class="unit-metric-label">
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #3b82f6;"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                                                Vidas
                                            </div>
                                            <div class="unit-metric-value">{row_h['Qtd Vidas']} un</div>
                                            <div class="unit-metric-pill">{formatar_moeda(row_h['Vidas Ativas (R$)'])}</div>
                                        </div>
                                        """, unsafe_allow_html=True)

                                        hu3.markdown(f"""
                                        <div class="unit-metric">
                                            <div class="unit-metric-label">
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #ef4444;"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line><line x1="9" y1="14" x2="15" y2="20"></line><line x1="15" y1="14" x2="9" y2="20"></line></svg>
                                                Faltas
                                            </div>
                                            <div class="unit-metric-value">{row_h['Qtd Faltas']} un</div>
                                            <div class="unit-metric-pill">{formatar_moeda(row_h['Faltas (R$)'])}</div>
                                        </div>
                                        """, unsafe_allow_html=True)

                                        hup.markdown(f"""
                                        <div class="unit-metric">
                                            <div class="unit-metric-label">
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #0891b2;"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                                                Psicossocial
                                            </div>
                                            <div class="unit-metric-value">{row_h['Qtd Psicossocial']} un</div>
                                            <div class="unit-metric-pill">{formatar_moeda(row_h['Psicossocial (R$)'])}</div>
                                        </div>
                                        """, unsafe_allow_html=True)

                                        aviso_desc_h = ""
                                        if valor_desc_h > 0:
                                            aviso_desc_h = f"""<div style="font-size: 11px; color: #10b981; font-weight: 700; margin-top: 4px; background-color: rgba(16, 185, 129, 0.1); padding: 4px 8px; border-radius: 4px; display: inline-block;">⬇️ DESCONTO: -{formatar_moeda(valor_desc_h)}</div>"""

                                        hu4.markdown(f"""
                                        <div class="unit-metric">
                                            <div class="unit-metric-label">
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="color: #d97706;"><path d="M21 18c0 1.66-4 3-9 3s-9-1.34-9-3V6c0-1.66 4-3 9-3s9 1.34 9 3v12zm-9 1c3.5 0 7-1 7-2v-2.12c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V16c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V9.38c-1.72.68-4.25 1.12-7 1.12-2.75 0-5.28-.44-7-1.12V11c0 1 3.5 2 7 2zm0-4.5c3.5 0 7-1 7-2V4.88C17.28 5.56 14.75 6 12 6s-5.28-.44-7-1.12V6c0 1 3.5 2 7 2z"/></svg>
                                                Total Unidade
                                            </div>
                                            <div class="unit-metric-value-total">{formatar_moeda(total_final_h)}</div>
                                            {aviso_desc_h}
                                        </div>
                                        """, unsafe_allow_html=True)

                                        with st.expander("🔍 Ver funcionários e origem dos custos"):
                                            df_uni_hist = df_cons_hist[
                                                (df_cons_hist['Unidade Alocada'] == u_h)
                                                & (~df_cons_hist['ID_Linha'].isin(linhas_excl_hist))
                                            ]
                                            if df_uni_hist.empty:
                                                st.info("Sem lançamentos para esta unidade neste mês.")
                                            else:
                                                df_display = df_uni_hist[[
                                                    'Nome', 'Tipo de Custo', 'Status', 'Detalhe',
                                                    'Departamento RM', 'CC Alocado', 'Unidade Original FAT', 'Valor (R$)'
                                                ]].rename(columns={
                                                    'Nome': 'Funcionário',
                                                    'CC Alocado': 'Centro de Custo',
                                                    'Departamento RM': 'Departamento',
                                                    'Unidade Original FAT': 'Unidade'
                                                }).sort_values(by='Valor (R$)', ascending=False)

                                                st.dataframe(
                                                    df_display,
                                                    hide_index=True,
                                                    use_container_width=True,
                                                    column_config={
                                                        "Valor (R$)": st.column_config.NumberColumn(format="R$ %.2f")
                                                    }
                                                )
                            else:
                                st.warning(f"A planilha base de dados ({nome_limpo}.xlsx) não foi encontrada na mesma pasta. Não é possível exibir as pessoas.")
                                
                        except Exception as e:
                            st.error("Erro interno ao carregar o histórico.")
                else:
                    st.info("Nenhum arquivo de histórico encontrado na pasta do OneDrive.")
            else:
                st.warning("A pasta do OneDrive não foi localizada para ler o histórico.")







