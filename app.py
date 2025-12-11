import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO

st.set_page_config(layout="wide")
st.title("🔍 TR Validator - CATMAT Oficial (gov.br)")

# ---------------------------------------------------
# 1. BAIXAR CATMAT OFICIAL (SEM NENHUM CÓDIGO FIXO)
# ---------------------------------------------------

@st.cache_data(ttl=3600)
def get_catmat_oficial():
    """
    Baixa a planilha CATMAT oficial em Excel do portal gov.br
    e devolve apenas as colunas relevantes.

    A planilha é atualizada periodicamente pelo governo. [web:50][web:45]
    """
    # URL pública do CATMAT em Excel (atualizada pelo governo)
    url = "https://www.gov.br/compras/pt-br/acesso-a-informacao/consulta-detalhada/planilha-catmat-catser/catmat.xlsx/view"  # [web:50]

    # Baixa o conteúdo (seguindo redirects)
    resp = requests.get(url, allow_redirects=True, timeout=60)
    resp.raise_for_status()

    # Alguns servidores devolvem o Excel direto; outros devolvem via /view.
    # O BytesIO permite ler o conteúdo em memória como um arquivo.
    xls_bytes = BytesIO(resp.content)

    # Lê o Excel. Dependendo da versão, pode precisar de engine="openpyxl".
    df = pd.read_excel(xls_bytes, engine="openpyxl")

    # Padroniza nomes de coluna (retira acentos/variações).
    cols = {c.upper().strip(): c for c in df.columns}
    df.columns = [c.upper().strip() for c in df.columns]

    # Tenta mapear nomes mais comuns de colunas.
    def achar_col(possiveis):
        for p in possiveis:
            if p in df.columns:
                return p
        return None

    col_cod = achar_col(["CODIGO", "CÓDIGO", "CODIGOITEM", "CÓDIGO DO ITEM"])
    col_desc = achar_col(["DESCRICAO", "DESCRIÇÃO"])
    col_und = achar_col(["UNIDADE DE FORNECIMENTO", "UNIDADE_FORNECIMENTO", "UND_FORNECIMENTO", "UNIDADE"])
    col_sit = achar_col(["SITUACAO", "SITUAÇÃO", "SITUAÇÃO DO ITEM"])

    if not all([col_cod, col_desc, col_und, col_sit]):
        st.error("Não foi possível identificar as colunas padrão na planilha CATMAT. Verifique o layout atual do arquivo.")
        return pd.DataFrame()

    catmat = df[[col_cod, col_desc, col_und, col_sit]].copy()
    catmat.columns = ["CODIGO", "DESCRICAO", "UNIDADE_FORNECIMENTO", "SITUACAO"]

    # Remove linhas sem código
    catmat = catmat.dropna(subset=["CODIGO"])
    catmat["CODIGO"] = catmat["CODIGO"].astype(str).str.strip()

    return catmat


# ----------------------------------------
# 2. FUNÇÃO AUXILIAR PARA NÚMERO BRASILEIRO
# ----------------------------------------

def limpar_numero(txt):
    """Converte '1.234,56' ou '1234,56' em float 1234.56."""
    txt = str(txt)
    txt = re.sub(r"[^\d,\.]", "", txt)
    # se tiver vírgula, assume vírgula como decimal
    if "," in txt and "." in txt:
        # remove pontos de milhar e troca vírgula por ponto
        txt = txt.replace(".", "").replace(",", ".")
    elif "," in txt:
        txt = txt.replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return 0.0


# ----------------------------------------------------
# 3. EXTRAIR CÓDIGO CATMAT + UNIDADE A PARTIR DO PDF
# ----------------------------------------------------

def extrair_itens_pdf(texto):
    """
    Tenta extrair pares (UNIDADE, CATMAT, PREÇO_UNIT) do texto do PDF.

    A regex é deliberadamente simples para não travar o fluxo.
    Você pode refiná-la conforme for vendo novos modelos de TR. [web:52]
    """
    # Exemplo de padrão: FR 379429 7 4 2 0 1 1.434,89 10.044,23
    # ou: FR 379429 7 4 2 0 1 1434,89 10044,23
    padrao = r"\b([A-Z]{1,4})\s+(\d{5,7})\b"

    matches = re.findall(padrao, texto)
    itens = []
    for i, (unidade, cod) in enumerate(matches, start=1):
        itens.append(
            {
                "ITEM": i,
                "UNIDADE_TR": unidade.strip(),
                "CATMAT": cod.strip(),
            }
        )
    return pd.DataFrame(itens).drop_duplicates(subset=["UNIDADE_TR", "CATMAT"]).reset_index(drop=True)


# -------------------------
# 4. INTERFACE STREAMLIT
# -------------------------

st.markdown("### 📄 Upload do Termo de Referência (PDF)")
uploaded_file = st.file_uploader("Escolha o PDF", type="pdf")

if uploaded_file:
    # Lê o PDF bruto como texto (simples, baseado em encoding latino).
    # Para maior robustez, você pode trocar por PyMuPDF ou pdfplumber.
    raw_bytes = uploaded_file.read()
    try:
        texto_pdf = raw_bytes.decode("latin-1", errors="ignore")
    except Exception:
        texto_pdf = raw_bytes.decode(errors="ignore")

    with st.spinner("⬇️ Baixando CATMAT oficial do gov.br e processando..."):
        catmat_df = get_catmat_oficial()
        if catmat_df.empty:
            st.stop()

        itens_df = extrair_itens_pdf(texto_pdf)

        if itens_df.empty:
            st.warning("Nenhum possível par (unidade, CATMAT) foi detectado no PDF com a regex atual.")
            st.stop()

        # Validação contra CATMAT oficial
        itens_df["CATMAT"] = itens_df["CATMAT"].astype(str)
        itens_df["CATMAT_STATUS"] = ""
        itens_df["UF_STATUS"] = ""
        itens_df["DESCRICAO_OFICIAL"] = ""
        itens_df["UNIDADE_OFICIAL"] = ""
        itens_df["SITUACAO_CATMAT"] = ""

        for idx, row in itens_df.iterrows():
            cod = row["CATMAT"]
            filtro = catmat_df["CODIGO"].astype(str) == cod
            match = catmat_df[filtro]

            if match.empty:
                itens_df.at[idx, "CATMAT_STATUS"] = "⚠️ NÃO ENCONTRADO NO CATMAT"
                itens_df.at[idx, "UF_STATUS"] = "⚠️ VERIFICAR"
            else:
                oficial = match.iloc[0]
                itens_df.at[idx, "DESCRICAO_OFICIAL"] = str(oficial["DESCRICAO"])
                itens_df.at[idx, "UNIDADE_OFICIAL"] = str(oficial["UNIDADE_FORNECIMENTO"])
                itens_df.at[idx, "SITUACAO_CATMAT"] = str(oficial["SITUACAO"])

                if str(oficial["SITUACAO"]).upper().startswith("ATIVO"):
                    itens_df.at[idx, "CATMAT_STATUS"] = "✅ ATIVO"
                else:
                    itens_df.at[idx, "CATMAT_STATUS"] = f"❌ {oficial['SITUACAO']}"

                if row["UNIDADE_TR"] == str(oficial["UNIDADE_FORNECIMENTO"]):
                    itens_df.at[idx, "UF_STATUS"] = "✅ CONFERE"
                else:
                    itens_df.at[idx, "UF_STATUS"] = f"❌ ESPERADO: {oficial['UNIDADE_FORNECIMENTO']}"

    # --------------------
    # 5. DASHBOARD / SAÍDA
    # --------------------

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Itens detectados no PDF", len(itens_df))
    col2.metric("✅ CATMAT ativo", int((itens_df["CATMAT_STATUS"] == "✅ ATIVO").sum()))
    col3.metric("✅ Unidades conferem", int((itens_df["UF_STATUS"] == "✅ CONFERE").sum()))

    st.subheader("📊 Validação CATMAT x TR (por Código)")

    st.dataframe(
        itens_df[
            [
                "ITEM",
                "CATMAT",
                "UNIDADE_TR",
                "DESCRICAO_OFICIAL",
                "UNIDADE_OFICIAL",
                "SITUACAO_CATMAT",
                "CATMAT_STATUS",
                "UF_STATUS",
            ]
        ],
        use_container_width=True,
    )

    # Download CSV
    csv = itens_df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    st.download_button("📥 Baixar CSV de validação", csv, "validacao_catmat_tr.csv", "text/csv")

    st.success("✅ Validação concluída usando SOMENTE o CATMAT oficial, sem códigos fixos no script.")
else:
    st.info("Faça upload de um PDF de Termo de Referência para iniciar a validação.")
