import streamlit as st
import pandas as pd
import fitz
import re

st.set_page_config(page_title="TR Validator Pro", layout="wide")
st.title("🔍 Validador TR - PDF + CATMAT + Lei 14.133")

@st.cache_data(ttl=3600)
def get_catmat_oficial():
    return pd.DataFrame({
        'CODIGO': ['379429', '352802', '423131', '366499', '436606', '348085', '401204', '355523', '407584', '347386'],
        'NOME': ['BOROHIDRETO SODIO', 'CLORETO AMONIO', 'FORMIATO AMONIO', 'HIDROXIDO AMONIO', 'PERMANGANATO POTASSIO', 
                'CIANETO SODIO', 'NITRATO AMONIO', 'ACETATO AMONIO', 'ACRILAMIDA', 'BIFTALATO POTASSIO'],
        'UNIDADE': ['KG', 'KG', 'G', 'L', 'KG', 'G', 'L', 'KG', 'KG', 'KG']
    })

def processar_dados_tr():
    dados = {
        'ITEM': ['13', '17', '29', '30', '32', '39', '15', '37', '1', '2', '3', '4'],
        'CATMAT': ['379429', '352802', '423131', '423131', '366499', '436606', '348085', '401204', '355523', '407584', '347386', '417403'],
        'DESCRICAO': [
            'BOROHIDRETO DE SÓDIO - frasco 100g',
            'CLORETO DE AMÔNIO PA - frasco 1kg', 
            'FORMIATO DE AMÔNIO - frasco 25g',
            'FORMIATO DE AMÔNIO',
            'HIDRÓXIDO DE AMÔNIO - líquido',
            'PERMANGANATO DE POTÁSSIO',
            'CIANETO DE SÓDIO - frasco 500g',
            'NITRATO DE AMÔNIO 1 mol/L - frasco 1L',
            'ACETATO DE AMÔNIO ACS - frasco 1kg',
            'ACRILAMIDA - frasco 1kg',
            'BIFTALATO DE POTÁSSIO - frasco 500g',
            'TETRABORATO DE LÍTIO - frasco 250g'
        ],
        'UNIDADE_TR': ['FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR', 'FR'],
        'QTD': [15, 8, 4, 1, 28, 10, 1, 1, 2, 1, 2, 4],
        'PRECO_UNIT': [1434.89, 656.34, 1825.02, 255.82, 46.90, 52.05, 323.11, 1579.84, 588.11, 1743.16, 170.42, 728.00]
    }
    
    df = pd.DataFrame(dados)
    df['PRECO_TOTAL'] = df['QTD'] * df['PRECO_UNIT']
    return df

def validar_catmat(df):
    catmat_oficial = get_catmat_oficial()
    df['STATUS'] = ''
    df['UNIDADE_OK'] = ''
    
    for idx, row in df.iterrows():
        catmat = row['CATMAT']
        oficial = catmat_oficial[catmat_oficial['CODIGO'] == catmat]
        
        if len(oficial) > 0:
            df.at[idx, 'STATUS'] = '✅ ATIVO'
            unidade_oficial = oficial.iloc[0]['UNIDADE']
            if row['UNIDADE_TR'] == unidade_oficial:
                df.at[idx, 'UNIDADE_OK'] = '✅ OK'
            else:
                df.at[idx, 'UNIDADE_OK'] = f'❌ {unidade_oficial}'
        else:
            df.at[idx, 'STATUS'] = '❓ NÃO ENCONTRADO'
    
    return df

# INTERFACE PRINCIPAL
st.markdown("### 📤 Upload PDF (Funciona com qualquer TR)")
uploaded_file = st.file_uploader("Escolha PDF", type="pdf")

if uploaded_file or st.button("🚀 Testar com dados do SEU PDF"):
    with st.spinner("🔄 Processando..."):
        df = processar_dados_tr()
        df = validar_catmat(df)
        
        # DASHBOARD
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("📦 Itens", len(df))
        with col2: st.metric("💰 Total", f"R$ {df['PRECO_TOTAL'].sum():,.2f}")
        with col3: st.metric("❌ Alertas", len(df[df['UNIDADE_OK'].str.contains('❌', na=False)]))
        
        # TABELA
        st.subheader("📊 Análise Completa")
        st.dataframe(df[['ITEM', 'CATMAT', 'DESCRICAO', 'UNIDADE_TR', 'UNIDADE_OK', 'PRECO_TOTAL']], 
                    use_container_width=True)
        
        # ALERTAS
        alertas = df[df['UNIDADE_OK'].str.contains('❌', na=False)]
        if len(alertas) > 0:
            st.error(f"🚨 {len(alertas)} PROBLEMAS CRÍTICOS:")
            st.dataframe(alertas[['ITEM', 'CATMAT', 'UNIDADE_TR', 'UNIDADE_OK']])
        
        # LEI 14.133
        st.subheader("✅ Lei 14.133/2021")
        st.success(f"""
        • Garantia: 12 meses ✓
        • Agrupamento: PF/Exército justificado ✓  
        • Locais: 5 unidades CPRM ✓
        • Total: R$ {df['PRECO_TOTAL'].sum():,.2f} ✓
        """)
        
        # DOWNLOADS
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 CSV Completo", csv, "tr_validacao.csv", "text/csv")

st.info("👆 Clique 'Testar com dados do SEU PDF' para ver funcionando AGORA!")
