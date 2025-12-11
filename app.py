import streamlit as st
import fitz  # PyMuPDF para ler PDF
import re
import pandas as pd

st.set_page_config(layout="wide")
st.title("🔍 TR Validator - Diagnóstico PDF + Regex")

# -------------------------------------------------
# 1. Fallback interno com regex (genérico)
# -------------------------------------------------

def fallback_regex(texto_pdf: str) -> pd.DataFrame:
    """
    Tenta extrair itens com uma regex genérica.
    IMPORTANTE: isso é só um ponto de partida.
    Vamos ajustar depois com base no texto bruto real do seu PDF.
    """
    # Exemplo de padrão: UNID CATMAT QTD... PRECO_UNIT PRECO_TOTAL
    # Você VAI precisar ajustar depois que virmos o texto bruto.
    padrao = r"\b([A-Z]{1,4})\s+(\d{5,7})\b"

    matches = re.findall(padrao, texto_pdf)
    itens = []
    for i, (unid, cat) in enumerate(matches, start=1):
        itens.append(
            {
                "ITEM": i,
                "UNIDADE": unid,
                "CATMAT": cat,
            }
        )
    return pd.DataFrame(itens).drop_duplicates(subset=["UNIDADE", "CATMAT"]).reset_index(drop=True)


# -------------------------------------------------
# 2. Interface Streamlit
# -------------------------------------------------

st.markdown("### 📄 Upload do Termo de Referência em PDF")

uploaded_file = st.file_uploader("Escolha o PDF do TR", type="pdf")

if uploaded_file is not None:
    # Ler PDF em memória com PyMuPDF
    raw_bytes = uploaded_file.read()
    try:
        doc = fitz.open(stream=raw_bytes, filetype="pdf")
    except Exception as e:
        st.error(f"Erro ao abrir PDF: {e}")
        st.stop()

    texto_pdf = ""
    for page in doc:
        texto_pdf += page.get_text()

    st.success("✅ PDF lido com sucesso. Texto extraído.")

    # 1) Preview do texto bruto para diagnóstico
    st.subheader("🔎 Texto bruto do PDF (diagnóstico)")
    st.info("Copie um trecho deste texto e envie aqui na conversa para ajustar a regex especificamente ao seu modelo de TR.")
    st.text_area("Texto bruto (primeiros ~3000 caracteres)", texto_pdf[:3000], height=300)

    # 2) Fallback com regex genérica
    if st.button("Tentar extrair itens com regex genérica"):
        df = fallback_regex(texto_pdf)

        if df.empty:
            st.warning("⚠️ Fallback (regex genérica) não encontrou itens. Precisamos ver o texto bruto para ajustar a regex.")
        else:
            st.subheader("📊 Itens detectados (versão genérica)")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
            st.download_button("📥 Baixar CSV de itens (genérico)", csv, "itens_regex_generica.csv", "text/csv")
else:
    st.info("Envie um arquivo PDF para começar.")
