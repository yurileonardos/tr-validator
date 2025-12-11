import streamlit as st
from PIL import Image
import io
import google.generativeai as genai

# -------------------------------
# CONFIG GERAL
# -------------------------------

st.set_page_config(layout="wide")
st.title("🔍 TR (imagens) → Tabelas HTML (Gemini)")

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY não encontrada em st.secrets. Configure em Settings → Secrets.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# ATENÇÃO: ajuste o nome do modelo conforme o que aparece para você na doc/console.
# Exemplos comuns atuais: "gemini-2.5-flash", "gemini-2.0-flash"
GEMINI_MODEL = "gemini-2.5-flash"


# -------------------------------
# PROMPT PARA GERAR HTML
# -------------------------------

def montar_prompt_html():
    return """
Você receberá uma ou mais imagens de páginas de um Termo de Referência,
com tabelas de itens contendo, por exemplo:
- número do grupo
- número do item
- código CATMAT
- descrição do item
- unidade de fornecimento
- quantidades
- preço unitário
- preço total

TAREFA:
- Reconstruir as tabelas em HTML usando <table>, <thead>, <tbody>, <tr>, <th>, <td>.
- Manter a estrutura que aparece nas imagens: grupos, itens, colunas, linhas.
- NÃO alterar nem arredondar valores numéricos; copie-os como aparecem.
- Se houver vários grupos, use um <h3> para cada grupo e uma <table> separada.
- Não adicionar nenhum texto explicativo fora do HTML.
Responda SOMENTE com HTML válido.
"""


# -------------------------------
# FUNÇÃO PARA CHAMAR O GEMINI
# -------------------------------

def gerar_html_com_gemini(imagens_pil):
    """
    Envia prompt + imagens para o Gemini e retorna o HTML gerado.
    """
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY não configurada."

    prompt = montar_prompt_html()

    try:
        # Versão multimodal com imagens: prompt + lista de imagens PIL
        model = genai.GenerativeModel(GEMINI_MODEL)
        contents = [prompt] + imagens_pil
        resp = model.generate_content(contents)

        html = resp.text or ""
        if not html.strip():
            return None, "Gemini retornou resposta vazia."
        return html, None
    except Exception as e:
        return None, f"Erro Gemini: {e}"


# -------------------------------
# INTERFACE STREAMLIT
# -------------------------------

st.markdown("### 📄 Envie as páginas do TR como imagens (PNG/JPG)")

files = st.file_uploader(
    "Selecione uma ou mais imagens (páginas do TR escaneado)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if files:
    imagens_pil = []
    st.markdown("#### 🖼️ Pré-visualização das imagens enviadas")
    cols = st.columns(min(3, len(files)))

    for i, f in enumerate(files):
        # Ler o arquivo e converter em PIL
        img = Image.open(io.BytesIO(f.read()))
        imagens_pil.append(img)

        with cols[i % len(cols)]:
            st.image(img, caption=f"Página {i+1}", use_column_width=True)

    if st.button("🔄 Gerar HTML das tabelas (Gemini)"):
        with st.spinner("Chamando o Gemini para gerar o HTML das tabelas..."):
            html, erro = gerar_html_com_gemini(imagens_pil)

        if html:
            st.success("Tabelas geradas com sucesso via Gemini.")

            st.subheader("📊 Tabelas renderizadas")
            st.markdown(html, unsafe_allow_html=True)

            st.subheader("🔎 Código HTML (até 4000 caracteres)")
            st.code(html[:4000] + ("..." if len(html) > 4000 else ""), language="html")
        else:
            st.error("Não foi possível gerar o HTML.")
            if erro:
                st.text(f"Detalhes: {erro}")
else:
    st.info("Envie uma ou mais imagens das páginas do TR para começar.")
