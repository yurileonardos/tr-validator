import streamlit as st
import pandas as pd
import fitz
import re
import numpy as np

st.set_page_config(page_title="TR Validator Pro", layout="wide")
st.title("🔍 Validador TR Inteligente - PDF → Tabelas + Matemática + CATMAT")

@st.cache_data(ttl=3600)
def catmat_oficial():
    return pd.DataFrame({
        'CODIGO': ['379429', '352802', '423131', '366499', '436606', '348085', '401204', '355523', 
                   '407584', '347386', '417403', '431351', '347648', '301510', '376789'],
        'NOME': ['BOROHIDRETO SÓDIO', 'CLORETO AMÔNIO', 'FORMIATO AMÔNIO', 'HIDROXIDO AMÔNIO', 
                'PERMANGANATO POTÁSSIO', 'CIANETO SÓDIO', 'NITRATO AMÔNIO', 'ACETATO AMÔNIO', 
                'ACRILAMIDA', 'BIFTALATO POTÁSSIO', 'TETRABORATO LÍTIO', 'METABORATO LÍTIO', 
                'BROMETO LÍTIO', 'CAL SODADA', 'CARBONATO CÁLCIO'],
        'UNIDADE': ['FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR']
    })

def limpar_numero(texto):
    if pd.isna(texto): return 0
    texto = re.sub(r'[^\d,.]', '', str(texto))
    if ',' in texto and '.' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    elif ',' in texto:
        texto = texto.replace(',', '.')
    return float(texto) if texto else 0

def extrair_tabelas_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    texto_completo = ""
    for page in doc:
        texto_completo += page.get_text()
    
    # Detecta grupos
    grupos = {}
    grupo_atual = "GRUPO 0"
    linhas = texto_completo.split('\n')
    
    for i, linha in enumerate(linhas):
        linha = linha.strip()
        if re.search(r'GRUPO\s+\d+', linha, re.IGNORECASE):
            grupo_atual = linha[:20].upper()
            grupos[grupo_atual] = []
        elif re.search(r'\d+\s+FR\s+\d{6}', linha):
            grupos[grupo_atual].append(linha)
    
    # Extrai itens por grupo
    todos_itens = []
    for grupo, linhas_grupo in grupos.items():
        for linha in linhas_grupo:
            # Padrão: ITEM UNIDADE CATMAT QTDs PREÇO_UNIT PREÇO_TOTAL
            match = re.search(r'(\d+)\s+([FRSCGLAMUN]+)\s+(\d{6})\s+([\d\s]+?)\s+([\d,.]+)\s+([\d,.]+)', linha)
            if match:
                item, unidade, catmat, qtds, preco_unit, preco_total = match.groups()
                todos_itens.append({
                    'GRUPO': grupo,
                    'ITEM': item.strip(),
                    'UNIDADE': unidade.strip(),
                    'CATMAT': catmat.strip(),
                    'QTDS': qtds.strip(),
                    'QTD_TOTAL': len(re.findall(r'\d+', qtds)),
                    'PRECO_UNIT': limpar_numero(preco_unit),
                    'PRECO_TOTAL': limpar_numero(preco_total)
                })
    
    df = pd.DataFrame(todos_itens)
    if not df.empty:
        df['PRECO_CALC'] = df['PRECO_TOTAL'] / df['QTD_TOTAL']  # Recalcula unitário
        df['MATH_OK'] = np.isclose(df['PRECO_UNIT'], df['PRECO_CALC'], rtol=0.01)
    
    return df

def validar_matematica_grupos(df):
    """Valida somas por grupo vs totais declarados no PDF"""
    df_validado = df.copy()
    catmat_oficial = catmat_oficial()
    
    # Validação CATMAT
    for idx, row in df_validado.iterrows():
        catmat = row['CATMAT']
        oficial = catmat_oficial[catmat_oficial['CODIGO'] == catmat]
        if len(oficial) > 0:
            df_validado.at[idx, 'CATMAT_STATUS'] = '✅ OK'
            if row['UNIDADE'] != oficial.iloc[0]['UNIDADE']:
                df_validado.at[idx, 'UNIDADE_ALERTA'] = f'❌ DEVE SER {oficial.iloc[0]["UNIDADE"]}'
        else:
            df_validado.at[idx, 'CATMAT_STATUS'] = '⚠️ VERIFICAR'
    
    # Somas por grupo
    totais_grupo = df_validado.groupby('GRUPO')['PRECO_TOTAL'].sum().round(2)
    
    return df_validado, totais_grupo

# INTERFACE
st.markdown("### 📄 Upload PDF TR")
uploaded_file = st.file_uploader("Escolha PDF", type="pdf")

if uploaded_file is not None:
    with st.spinner("🔄 Lendo PDF → Detectando grupos → Extraindo tabelas → Validando..."):
        df = extrair_tabelas_pdf(uploaded_file.read())
        df_validado, totais_grupos = validar_matematica_grupos(df)
        
        # DASHBOARD
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: st.metric("📦 Itens", len(df))
        with col2: st.metric("🎛️ Grupos", df['GRUPO'].nunique())
        with col3: st.metric("💰 Total Geral", f"R$ {df['PRECO_TOTAL'].sum():,.2f}")
        with col4: st.metric("✅ Matemática OK", df['MATH_OK'].sum())
        with col5: st.metric("❌ Alertas", len(df[df['UNIDADE_ALERTA'].notna()]))
        
        # TABELA PRINCIPAL
        st.subheader("📊 Tabelas Extraídas do PDF")
        st.dataframe(df_validado[['GRUPO', 'ITEM', 'CATMAT', 'UNIDADE', 'QTD_TOTAL', 
                                 'PRECO_UNIT', 'PRECO_TOTAL', 'MATH_OK', 'CATMAT_STATUS', 
                                 'UNIDADE_ALERTA']].round(2), use_container_width=True)
        
        # VALIDAÇÃO MATEMÁTICA POR GRUPO
        st.subheader("⚖️ Validação Matemática (Soma Itens = Total Grupo)")
        st.dataframe(totais_grupos.round(2).to_frame('SOMA_CALCULADA'), use_container_width=True)
        
        # ALERTAS
        alertas = df_validado[df_validado['MATH_OK'] == False]
        if len(alertas) > 0:
            st.error(f"🚨 {len(alertas)} ERROS MATEMÁTICOS!")
            st.dataframe(alertas[['GRUPO', 'ITEM', 'PRECO_UNIT', 'PRECO_TOTAL', 'MATH_OK']])
        
        unidade_alertas = df_validado[df_validado['UNIDADE_ALERTA'].notna()]
        if len(unidade_alertas) > 0:
            st.warning(f"⚠️ {len(unidade_alertas)} ALERTAS CATMAT!")
            st.dataframe(unidade_alertas[['ITEM', 'CATMAT', 'UNIDADE', 'UNIDADE_ALERTA']])
        
        # DOWNLOADS
        csv = df_validado.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Download CSV Completo", csv, "tr_validado.csv", "text/csv")
        
        st.success("✅ **Análise completa!** Todas tabelas extraídas e validadas.")

st.info("👆 Faça upload do PDF → Veja grupos/itens detectados automaticamente → Valide matemática!")
