import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO

st.set_page_config(layout="wide")
st.title("🔍 TR Validator - CATMAT Oficial (gov.br)")

# ---------------------------------------------------
# 1. BAIXAR CATMAT OFICIAL COM TRATAMENTO DE ERRO
# ---------------------------------------------------

@st.cache_data(ttl=3600)
def get_catmat_oficial():
    """
    Tenta baixar a planilha CATMAT oficial em Excel do portal gov.br.
    Se o conteúdo não for um Excel válido, retorna DataFrame vazio
    e o app exibe mensagem de alerta. [web:50][web:45]
    """
    # URL pública da relação em Excel (pode ser atualizada pelo gov.br).
    url = "https://www.gov.br/compras/pt-br/acesso-a-informacao/consulta-detalhada/planilha-catmat-catser/catmat.xlsx/view"  # [web:50]

    resp = requests.get(url, allow_redirects=True, timeout=60)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "").lower()

    # Se o servidor não devolveu Excel, evita tentar ler como xlsx.
    if "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" not in content_type and not url.lower().endswith(".xlsx"):
        # Tentativa alternativa: às vezes o link correto é sem o /view
        alt_url = url.replace("/view", "")
        alt_resp = requests.get(alt_url, allow_redirects=True, timeout=60)
        alt_type = alt_resp.headers.get("Content-Type", "").lower()
        if "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in alt_type or alt_url.lower().endswith(".xlsx"):
            xls_bytes = BytesIO(alt_resp.content)
        else:
            # Não conseguiu Excel de forma segura
            st.warning("Não foi possível obter a planilha CATMAT.xlsx como arquivo Excel. Verifique o link oficial ou baixe manualmente e trate fora do app.")
            return pd.DataFrame()
    else:
        xls_bytes = BytesIO(resp.content)

    try:
        df = pd.read_excel(xls_bytes, engine="openpyxl")
    except Exception:
        st.warning("O conteúdo baixado do CATMAT não é um arquivo Excel válido. O layout/link pode ter mudado no gov.br.")
        return pd.DataFrame()

    # Padroniza nomes de coluna
    df.columns = [c.upper().strip() for c in df.columns]

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
        st.warning("Planilha CATMAT baixada, mas as colunas esperadas (código, descrição, unidade, situação) não foram encontradas. O layout pode ter sido alterado.")
        return pd.DataFrame()

    catmat = df[[col_cod, col_desc, col_und, col_sit]].copy()
    catmat.columns = ["CODIGO", "DESCRICAO", "UNIDADE_FORNECIMENTO", "SITUACAO"]
    catmat = catmat.dropna(subset=["CODIGO"])
    catmat["CODIGO"] = catmat["CODIGO"].astype(str).str.strip()

    return catmat

# ----------------------------------------
# 2. FUNÇÃO AUXILIAR PARA NÚMERO BRASILEIRO
# ----------------------------------------

def limpar_numero(txt):
    txt = str(txt)
    txt = re.sub(r"[^\d,\.]", "", txt)
    if "," in txt and "." in txt:
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
    Extrai pares (UNIDADE, CATMAT) a partir do texto do PDF.
    Regex genérica: UM a quatro letras maiúsculas + código com 5–7 dígitos. [web:52]
    """
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
    # Remove duplicados básicos
    return pd.DataFrame(itens).drop_duplicates(subset=["UNIDADE_TR", "CATMAT"]).reset_index(drop=True)

# -------------------------
# 4. INTERFACE STREAMLIT
# -------------------------

st.markdown("### 📄 Upload do Termo de Referência (PDF)")
uploaded_file = st.file_uploader("Escolha o PDF", type="pdf")

if uploaded_file:
    raw_bytes = uploaded_file.read()
    try:
        texto_pdf = raw_bytes.decode("latin-1", errors="ignore")
    except Exception:
        texto_pdf = raw_bytes.decode(errors="ignore")

    with st.spinner("⬇️ Baixando CATMAT oficial e validando..."):
        catmat_df = get_catmat_oficial()
        if catmat_df.empty:
            st.stop()

        itens_df = extrair_itens_pdf(texto_pdf)

        if itens_df.empty:
            st.warning("Nenhum possível par (unidade, CATMAT) foi detectado no PDF com a regex atual.")
            st.stop()

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

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Itens detectados", len(itens_df))
    col2.metric("✅ CATMAT ativo", int((itens_df["CATMAT_STATUS"] == "✅ ATIVO").sum()))
    col3.metric("✅ UF confere", int((itens_df["UF_STATUS"] == "✅ CONFERE").sum()))

    st.subheader("📊 Validação CATMAT x TR (por código)")

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

    csv = itens_df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    st.download_button("📥 Baixar CSV de validação", csv, "validacao_catmat_tr.csv", "text/csv")

    st.success("✅ Validação concluída usando apenas CATMAT oficial, sem códigos fixos.")
else:
    st.info("Faça upload de um PDF de Termo de Referência para iniciar a validação.")
