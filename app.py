import streamlit as st
import pandas as pd
import requests
import feedparser
import camelot
import io
from datetime import datetime

st.set_page_config(page_title="TR Validator", layout="wide")
st.title("🔍 Validador TR - Lei 14.133")

uploaded_file = st.file_uploader("📄 Upload PDF Termo de Referência", type="pdf")

if uploaded_file:
    # Salva temporariamente
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getvalue())
    
    with st.spinner("🔄 Analisando PDF..."):
        tables = camelot.read_pdf("temp.pdf", pages='all')
        
        # Simula extração (exemplo seus dados)
        dados = {
            'ITEM': ['13', '17', '29'],
            'CATMAT': ['379429', '352802', '423131'],
            'DESCRICAO': ['BOROHIDRETO DE SÓDIO', 'CLORETO DE AMÔNIO', 'FORMIATO DE AMÔNIO'],
            'UNIDADE': ['FR', 'FR', 'FR'],
            'QTD': [15, 8, 4],
            'PRECO_UNIT': [1434.89, 656.34, 1825.02]
        }
        df = pd.DataFrame(dados)
        
        # Validação simulada CATMAT oficial
        df['STATUS'] = ['✅ OK', '✅ OK', '⚠️ Verificar']
        df['UNIDADE_OK'] = ['SIM', 'SIM', 'NÃO']
    
    # Dashboard
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Itens", len(df))
        st.metric("OK", df['STATUS'].str.contains('OK').sum())
    with col2:
        st.metric("Alertas", len(df[df['STATUS'].str.contains('Verificar')]))
    
    st.dataframe(df)
    st.download_button("📥 Excel", df.to_csv(index=False), "validacao.csv")
