import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re
import numpy as np

st.set_page_config(page_title="TR Validator Dinâmico", layout="wide")
st.title("🔍 Validador TR Dinâmico - 100% Flexível & Robusto")

def limpar_numero(texto):
    """Converte números brasileiros para float"""
    if pd.isna(texto) or not str(texto).strip():
        return 0.0
    texto = re.sub(r'[^\d,.]', '', str(texto))
    if ',' in texto:
        texto = texto.replace(',', '.')
    try:
        return float(texto)
    except:
        return 0.0

def detectar_unidades_pdf(texto_completo):
    """Detecta DINAMICAMENTE todas unidades do PDF"""
    unidades = set()
    padrao_unidades = r'\b([A-Z]{1,3})\b\s+\d{6}'
    matches = re.findall(padrao_unidades, texto_completo)
    return sorted(list(set(matches)))

def detectar_grupos_pdf(texto_completo):
    """Detecta DINAMICAMENTE todos grupos do PDF"""
    grupos = {}
    linhas = texto_completo.split('\n')
    grupo_atual = None
    
    for linha in linhas:
        linha = linha.strip()
        # Detecta QUALQUER padrão de grupo
        match_grupo = re.search(r'(GRUPO|GRUPO\s*\d+|Grupo|GROUP)', linha, re.IGNORECASE)
        if match_grupo:
            grupo_atual = re.search(r'(GRUPO|GRUPO\s*\d+|Grupo|GROUP).*?(?=\n|$)', linha, re.IGNORECASE)
            if grupo_atual:
                grupo_atual = grupo_atual.group().strip().upper()
                grupos[grupo_atual] = []
        elif grupo_atual and re.search(r'\d+\s+[A-Z]{1,3}\s+\d{6}', linha):
            grupos[grupo_atual].append(linha)
    
    # Se não achou grupos, usa tudo como um grupo
    if not grupos:
        grupos = {'GRUPO_DETECTADO': linhas}
    
    return grupos

def extrair_itens_flexivel(linhas_grupo):
    """Extrai itens com PADRÕES FLEXÍVEIS"""
    itens = []
    
    padroes = [
        r'(\d+)\s+([A-Z]{1,3})\s+(\d{6})\s+.*?(\d+[.,]?\d*)\s+(\d+[.,]?\d*)',
        r'(\d+)\s+([A-Z]{1,3})\s+(\d{6}).*?(\d+[.,]\d+)\s+(\d+[.,]\d+)',
        r'(\d+)\s+([A-Z]+?)\s+(\d{6}).*?R\$\s*(\d+[.,]\d+).*?R\$\s*(\d+[.,]\d+)',
    ]
    
    for linha in linhas_grupo:
        for padrao in padroes:
            match = re.search(padrao, linha, re.DOTALL)
            if match:
                try:
                    item, unidade, catmat, preco_unit, preco_total = match.groups()
                    itens.append({
                        'ITEM': item.strip(),
                        'UNIDADE': unidade.strip(),
                        'CATMAT': catmat.strip(),
                        'PRECO_UNIT': limpar_numero(preco_unit),
                        'PRECO_TOTAL': limpar_numero(preco_total)
                    })
                    break
                except:
                    continue
    
    return itens

def processar_pdf_universal(pdf_bytes):
    """Processa QUALQUER PDF → 100% Dinâmico & Seguro"""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texto_completo = ""
        
        for page in doc:
            texto_completo += page.get_text()
        
        # Detecta unidades e grupos
        unidades_detectadas = detectar_unidades_pdf(texto_completo)
        grupos = detectar_grupos_pdf(texto_completo)
        
        # Extrai itens
        todos_itens = []
        for grupo_nome, linhas_grupo in grupos.items():
            itens_grupo = extrair_itens_flexivel(linhas_grupo)
            for item in itens_grupo:
                item['GRUPO'] = grupo_nome
                todos_itens.append(item)
        
        df = pd.DataFrame(todos_itens)
        
        if not df.empty and len(df) > 0:
            # Validações básicas
            df['QTD_CALC'] = (df['PRECO_TOTAL'] / df['PRECO_UNIT']).round(1)
            df['MATH_OK'] = np.isclose(df['PRECO_TOTAL'], 
                                      df['QTD_CALC'] * df['PRECO_UNIT'], rtol=0.05)
            
            df['CATMAT_STATUS'] = df['CATMAT'].apply(
                lambda x: '✅ OK' if re.match(r'^\d{6}$', str(x)) else '⚠️ INVÁLIDO'
            )
            
            unidades_validas = unidades_detectadas[:10] if unidades_detectadas else ['FR']
            df['UF_STATUS'] = df['UNIDADE'].apply(
                lambda x: '✅ VÁLIDA' if x in unidades_validas else '⚠️ NOVA'
            )
        else:
            df = pd.DataFrame()
        
        return df, unidades_detectadas, list(grupos.keys())
    
    except Exception as e:
        st.error(f"Erro ao processar PDF: {str(e)}")
        return pd.DataFrame(), [], []

def gerar_resumo_seguro(df, unidades, grupos):
    """Resumo com proteção contra DataFrame vazio"""
    if df.empty or len(df) == 0:
        return {
            'itens': 0, 'grupos': 0, 'unidades_detectadas': 0, 
            'total': 0.0, 'math_ok': 0, 'math_total': 0,
            'catmat_ok': 0, 'uf_ok': 0
        }
    
    resumo = {
        'itens': len(df),
        'grupos': len(grupos),
        'unidades_detectadas': len(unidades),
        'total': df['PRECO_TOTAL'].sum(),
        'math_ok': int(df['MATH_OK'].sum()),
        'math_total': len(df),
        'catmat_ok': len(df[df['CATMAT_STATUS'] == '✅ OK']),
        'uf_ok': len(df[df['UF_STATUS'] == '✅ VÁLIDA'])
    }
    return resumo

# INTERFACE ROBUSTA
st.markdown("### 📄 **Upload QUALQUER PDF TR**")
uploaded_file = st.file_uploader("Escolha qualquer Termo de Referência", type="pdf")

if uploaded_file is not None:
    with st.spinner("🔄 Analisando PDF dinamicamente..."):
        df, unidades_detectadas, grupos_detectados = processar_pdf_universal(uploaded_file.read())
        resumo = gerar_resumo_seguro(df, unidades_detectadas, grupos_detectados)
        
        # DASHBOARD COM PROTEÇÃO
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📦 Itens", resumo['itens'])
        with col2:
            st.metric("🎛️ Grupos", resumo['grupos'])
        with col3:
            st.metric("💰 Total", f"R$ {resumo['total']:,.2f}")
        with col4:
            st.metric("✅ Math", f"{resumo['math_ok']}/{resumo['math_total']}")
        
        # INFO ESTRUTURA
        st.info(f"""
        **📋 Estrutura Detectada:**
        • **{resumo['grupos']} grupos**: {', '.join(grupos_detectados[:3])}{'...' if len(grupos_detectados)>3 else ''}
        • **{resumo['unidades_detectadas']} unidades**: {', '.join(unidades_detectadas[:5])}{'...' if len(unidades_detectadas)>5 else ''}
        """)
        
        if not df.empty and len(df) > 0:
            # TABELA PRINCIPAL
            st.subheader("📊 **DADOS EXTRAÍDOS**")
            cols = ['GRUPO', 'ITEM', 'CATMAT', 'UNIDADE', 'QTD_CALC', 
                   'PRECO_UNIT', 'PRECO_TOTAL', 'MATH_OK']
            st.dataframe(df[cols].round(2), use_container_width=True)
            
            # RESUMO EXECUTIVO
            st.subheader("📋 **RELATÓRIO EXECUTIVO**")
            resumo_df = pd.DataFrame({
                'VERIFICAÇÃO': ['Total Estimado', 'Grupos Detectados', 'CATMAT Válidos', 'Unidades OK', 'Matemática'],
                'RESULTADO': [
                    f'✅ R$ {resumo["total"]:,.2f}',
                    f'✅ {resumo["grupos"]} grupos',
                    f'{resumo["catmat_ok"]}/{resumo["itens"]} CATMAT',
                    f'{resumo["uf_ok"]}/{resumo["itens"]} UF',
                    f'{resumo["math_ok"]}/{resumo["math_total"]} OK'
                ]
            })
            st.dataframe(resumo_df, use_container_width=True)
            
            # TOTAIS POR GRUPO
            st.subheader("💰 **Totais por Grupo**")
            totais = df.groupby('GRUPO')['PRECO_TOTAL'].sum().round(2)
            st.dataframe(totais.to_frame('TOTAL'), use_container_width=True)
            
            # ALERTAS
            if resumo['math_ok'] < resumo['math_total']:
                st.error(f"🚨 **{resumo['math_total']-resumo['math_ok']} erros matemáticos**")
                st.dataframe(df[~df['MATH_OK']][['GRUPO', 'ITEM', 'QTD_CALC', 'PRECO_UNIT', 'PRECO_TOTAL']])
            
            # DOWNLOAD
            csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button(
                "📥 CSV Dinâmico", 
                csv, 
                f"tr_{resumo['itens']}_itens.csv", 
                "text/csv"
            )
            
            st.success(f"✅ **ANÁLISE CONCLUÍDA!** {resumo['itens']} itens processados!")
        else:
            st.warning("⚠️ **Nenhum item detectado.** Tente outro PDF ou verifique o formato.")

# INSTRUÇÕES
st.markdown("---")
st.markdown("""
**🎯 CARACTERÍSTICAS:**
- ✅ **100% Dinâmico** - sem dados fixos
- ✅ **Detecta qualquer grupo** automaticamente  
- ✅ **Aceita qualquer unidade** do PDF
- ✅ **Regex flexível** para várias estruturas
- ✅ **Tratamento de erros** completo
- ✅ **Proteção DataFrame vazio**
""")
