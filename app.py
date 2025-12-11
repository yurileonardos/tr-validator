import streamlit as st
import io
from PIL import Image
import google.generativeai as genai
import PyPDF2

# ------------------------------
# CONFIGURAÇÃO GERAL
# ------------------------------

st.set_page_config(layout="wide")
st.title("🔍 TR PDF Escaneado → Tabela HTML (Gemini)")

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY não configurada nos Secrets do Streamlit.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

# Escolha do modelo de visão (ajuste se sua conta suportar outro)
MODEL_NAME = "gemini-1.5-pro"  # modelo multimodal com visão


# ------------------------------
# FUNÇÕES AUXILIARES
# ------------------------------

def pdf_para_imagens(pdf_bytes: bytes, max_paginas: int = 2) -> list[Image.Image]:
    """
    Converte as primeiras páginas do PDF em imagens (JPEG/PNG) usando PyPDF2 + Pillow.

    Observação: como o PDF já é escaneado, cada página é uma imagem;
    aqui extraímos essas páginas para enviar ao Gemini. [web:118][web:115]
    """
    # PyPDF2 não renderiza direto para imagem, mas o PDF escaneado geralmente já contém
    # as páginas como imagens incorporadas. Para simplificar, vamos extrair cada página
    # como imagem via renderização do leitor do navegador não é trivial no backend,
    # então o exemplo aqui supõe que o PDF tenha sido salvo com imagens raster.
    # Para um cenário mais robusto, você poderia usar pdf2image ou similar.

    # Como o ambiente do Streamlit Cloud pode não ter poppler, este exemplo faz:
    # - Tenta abrir o PDF como se cada página fosse uma imagem única (casos simples).
    # - Se não funcionar, devolve lista vazia.

    imagens = []

    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        num_pages = min(len(reader.pages), max_paginas)

        for i in range(num_pages):
            page = reader.pages[i]

            # Para simplificar, usamos a "imagem" exportada como raster via layout de página.
            # PyPDF2 em si não renderiza, então este trecho funciona melhor com PDFs
            # onde as páginas são basicamente imagens incorporadas.
            # Se não houver fluxo de imagem, não teremos como extrair aqui.
            if "/XObject" in page["/Resources"]:
                xObject = page["/Resources"]["/XObject"].get_object()
                for obj in xObject:
                    if xObject[obj]["/Subtype"] == "/Image":
                        size = (xObject[obj]["/Width"], xObject[obj]["/Height"])
                        data = xObject[obj]._data

                        if xObject[obj]["/ColorSpace"] == "/DeviceRGB":
                            mode = "RGB"
                        else:
                            mode = "P"

                        img = Image.frombytes(mode, size, data)
                        imagens.append(img)
                        break  # pega a primeira imagem principal
            # Se não achar imagem, simplesmente segue

    except Exception as e:
        st.warning(f"Não foi possível extrair imagens das páginas do PDF: {e}")
        return []

    return imagens


def chamar_gemini_html_tabela(imagens: list[Image.Image]) -> str:
    """
    Envia as imagens das páginas do PDF para o Gemini e pede
    que reconstrua as tabelas em HTML. [web:111][web:114]
    """
    if not imagens:
        return "<p>Não foi possível extrair imagens das páginas do PDF.</p>"

    prompt = """
    Você receberá uma ou mais imagens de páginas de um Termo de Referência
    escaneado, com tabelas de itens (GRUPOS, código CATMAT, descrição,
    unidade de fornecimento, quantidades, preço unitário, preço total).

    TAREFA:
    - Reconstruir as tabelas em HTML, usando <table>, <thead>, <tbody>, <tr>, <th>, <td>.
    - Manter a estrutura original das tabelas: grupos, número do item, descrição,
      unidade, código CATMAT, quantidades, preço unitário e preço total.
    - NÃO arredondar ou modificar valores numéricos; copie-os como estão.
    - Se houver vários grupos, use um <h3> para o título de cada grupo
      e uma <table> separada para cada um.
    - Não explique nada em texto corrido; responda apenas com HTML válido.
    """

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        # Conteúdo multimodal: primeiro o prompt de texto, depois as imagens
        contents = [prompt]
        for img in imagens:
            contents.append(img)

        response = model.generate_content(contents)
        return response.text or "<p>Resposta vazia do modelo.</p>"
    except Exception as e:
        return f"<p>Erro ao chamar Gemini: {e}</p>"


# ------------------------------
# INTERFACE STREAMLIT
# ------------------------------

st.markdown("### 📄 Upload do Termo de Referência (PDF escaneado)")

uploaded_file = st.file_uploader("Escolha o PDF do TR (escaneado)", type="pdf")

if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()
    st.success("✅ PDF carregado.")

    st.markdown("### 🖼️ Pré-visualização das páginas como imagem (se possível)")

    # Extrai imagens das primeiras páginas
    imagens = pdf_para_imagens(pdf_bytes, max_paginas=2)

    if not imagens:
        st.warning("Não foi possível extrair imagens diretamente do PDF. Para PDFs escaneados, pode ser necessário outro método (ex: pdf2image).")
    else:
        cols = st.columns(len(imagens))
        for col, img in zip(cols, imagens):
            with col:
                st.image(img, caption="Página")

    if st.button("🔄 Enviar ao Gemini para gerar HTML das tabelas"):
        with st.spinner("Chamando Gemini (visão) para reconstruir as tabelas em HTML..."):
            html_tabelas = chamar_gemini_html_tabela(imagens)

        st.subheader("📊 Tabelas em HTML (geradas pelo Gemini)")
        st.markdown(html_tabelas, unsafe_allow_html=True)

        st.subheader("🔎 Código HTML (para inspeção)")
        st.code(html_tabelas[:4000] + ("..." if len(html_tabelas) > 4000 else ""), language="html")
else:
    st.info("Envie um PDF escaneado de TR para começar.")
