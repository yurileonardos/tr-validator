import streamlit as st
from PIL import Image
import google.generativeai as genai
import io

# ------------------------------
# CONFIGURAÇÃO GERAL
# ------------------------------

st.set_page_config(layout="wide")
st.title("🔍 TR (imagens) → Tabelas HTML com Gemini")

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY não configurada nos Secrets do Streamlit.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-1.5-pro"  # modelo multimodal com visão


# ------------------------------
# FUNÇÃO: imagens → HTML tabelas
# ------------------------------

def chamar_gemini_html_tabela_imagens(imagens_pil):
    """
    Recebe uma lista de imagens (PIL) de páginas do TR e
    pede ao Gemini para reconstruir as tabelas em HTML.
    """
    prompt = """
    Você receberá uma ou mais imagens de páginas de um Termo de Referência
    com tabelas de itens (grupos, código CATMAT, descrição, unidade de fornecimento,
    quantidades, preço unitário, preço total).

    TAREFA:
    - Reconstruir as tabelas em HTML usando <table>, <thead>, <tbody>, <tr>, <th>, <td>.
    - Manter a estrutura original: grupos, número do item, descrição, unidade, código CATMAT,
      quantidades, preço unitário e preço total.
    - NÃO alterar nem arredondar valores numéricos; copie-os como aparecem.
    - Se houver vários grupos, use um <h3> para cada grupo e uma <table> separada.
    - Não adicionar explicações em texto; responda apenas com HTML válido.
    """

    contents = [prompt] + imagens_pil
    model = genai.GenerativeModel(MODEL_NAME)
    resp = model.generate_content(contents)
    return resp.text or "<p>Resposta vazia do modelo.</p>"


# ------------------------------
# INTERFACE STREAMLIT
# ------------------------------

st.markdown("### 📄 Envie as páginas do TR como imagens (PNG/JPG)")

files = st.file_uploader(
    "Selecione uma ou mais imagens (páginas do TR escaneado)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if files:
    # Carrega as imagens em memória
    imagens_pil = []
    st.markdown("#### 🖼️ Pré-visualização das imagens enviadas")
    cols = st.columns(min(3, len(files)))

    for i, f in enumerate(files):
        img = Image.open(io.BytesIO(f.read()))
        imagens_pil.append(img)
        with cols[i % len(cols)]:
            st.image(img, caption=f"Página {i+1}", use_column_width=True)

    if st.button("🔄 Gerar HTML das tabelas com Gemini"):
        with st.spinner("Chamando Gemini (visão) para reconstruir as tabelas em HTML..."):
            html = chamar_gemini_html_tabela_imagens(imagens_pil)

        st.subheader("📊 Tabelas em HTML (geradas pelo Gemini)")
        st.markdown(html, unsafe_allow_html=True)

        st.subheader("🔎 Código HTML (para inspeção/depuração)")
        st.code(html[:4000] + ("..." if len(html) > 4000 else ""), language="html")
else:
    st.info("Envie uma ou mais imagens das páginas do TR para começar.")
