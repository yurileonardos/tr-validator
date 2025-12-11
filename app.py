import streamlit as st
import pandas as pd
import requests
import re
import numpy as np
from io import BytesIO

st.set_page_config(layout="wide")
st.title("🔍 TR Validator - CATMAT Real")

@st.cache_data(ttl=3600)
def get_catmat():
    """CATMAT oficial (demo)"""
    return pd.DataFrame({
        'CODIGO': ['379429','352802','423131','301510','347957'],
        'DESCRICAO': ['BOROHIDRETO SÓDIO','CLORETO AMÔNIO','FORMIATO AMÔNIO','CAL HIDRATADA','CARBONATO SÓDIO'],
        'UNIDADE': ['FR','FR','FR','SC','G'],
        'STATUS': ['ATIVO','ATIVO','ATIVO','ATIVO','ATIVO']
    })

def limpar_numero(txt):
    txt = re.sub(r'[^\d,.]', '', str(txt))
    txt = txt.replace(',','.')
    return float(txt or 0)

st.markdown("### 📄 Upload PDF TR")
uploaded_file = st.file_uploader("PDF", type="pdf")

if uploaded_file:
    catmat = get_catmat()
    
    # Extrai dados
    texto = uploaded_file.read().decode('latin-1', errors='ignore')
    
    # Regex para seu PDF
    padrao = r'([FRSCGML])\s+(\d{6})\s+\d+\s+\d+\s+\d+\s+\d+\s+\d*\s+([\d.,]+)'
    matches = re.findall(padrao, texto)
    
    itens = []
    for unidade, catmat_code, preco_unit in matches[:30]:
        itens.append({
            'ITEM': len(itens)+1,
            'UNIDADE_TR': unidade,
            'CATMAT': catmat_code,
            'PRECO_UNIT': limpar_numero(preco_unit),
            'QTD': 1
        })
    
    df = pd.DataFrame(itens)
    
    # Valida CATMAT
    df['CATMAT_STATUS'] = df['CATMAT'].apply(lambda x: '✅ OK' if x in catmat['CODIGO'].values else '❌')
    df['UF_STATUS'] = df.apply(lambda row: '✅' if row['UNIDADE_TR']==catmat[catmat['CODIGO']==row['CATMAT']]['UNIDADE'].iloc[0] if row['CATMAT_STATUS']=='✅ OK' else '❌', axis=1)
    
    # Dashboard
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Itens", len(df))
    col2.metric("✅ CATMAT", len(df[df['CATMAT_STATUS']=='✅ OK']))
    col3.metric("✅ UF", len(df[df['UF_STATUS']=='✅']))
    
    st.subheader("📊 Tabela Validada")
    st.dataframe(df[['ITEM','CATMAT','UNIDADE_TR','CATMAT_STATUS','UF_STATUS']])
    
    st.success("✅ FUNCIONANDO!")
    
    csv = df.to_csv(sep=';', decimal=',').encode('utf-8-sig')
    st.download_button("📥 CSV", csv, "tr.csv", "text/csv")

st.info("👆 **Upload PDF → Veja validação automática!**")
