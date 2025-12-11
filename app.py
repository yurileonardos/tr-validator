import streamlit as st
import fitz  # PyMuPDF para ler PDF
import openai

# 1) pegar chave dos secrets do Streamlit Cloud (Settings → Secrets)
# Em Secrets, você deve ter: OPENAI_API_KEY = "sk-sua-chave-aqui"
openai.api_key = st.secrets.get("OPENAI_API_KEY", "")

st.set_page_config(layout="wide")
st.title("🔍 Conversor de TR (PDF → HTML com ChatGPT)")

# ------------------------------
# Função: PDF (texto) → HTML tabela
# ------------------------------

def pdf_texto_para_html_tabela(texto_pdf: str) -> str:
    """
    Envia o texto do PDF para o ChatGPT e recebe um HTML com tabelas
    preservando ao máximo a organização original.
    """
    if not openai.api_key:
        return "<p>OPENAI_API_KEY não configurada nos Secrets do Streamlit.</p>"

    prompt = f"""
    Você receberá o texto bruto de um Termo de Referência em português,
    contendo uma ou mais tabelas de itens (grupos, código CATMAT, descrição, unidade, quantidades, preços).

    TAREFA:
    - Reconstruir as tabelas em HTML usando <table>, <thead>, <tbody>, <tr>, <th>, <td>.
    - Manter a estrutura original: grupos, número do item, descrição, unidade, código CATMAT, quantidades, preço unitário, preço total.
    - Não alterar nem arredondar números; copie os valores exatamente como aparecem no texto.
    - Não adicionar comentários; responda somente com HTML válido.
    - Se houver vários grupos, use uma <table> para cada grupo, com um título (por exemplo, <h3>GRUPO X</h3>).

    Texto do PDF (pode estar truncado):
    {texto_pdf[:8000]}
    """

    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
    )

    html = resp.choices[0].message.content
    return html

# ------------------------------
# Interface: upload + conversão
# ------------------------------

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

    if st.button("Converter PDF em HTML (ChatGPT)"):
        with st.spinner("Chamando ChatGPT para montar as tabelas em HTML..."):
            html_tabelas = pdf_texto_para_html_tabela(texto_pdf)

        st.subheader("📊 Tabelas em HTML (geradas pelo ChatGPT)")
        st.markdown(html_tabelas, unsafe_allow_html=True)

        st.subheader("🔎 Código HTML (para inspeção/depuração)")
        st.code(html_tabelas[:3000] + ("..." if len(html_tabelas) > 3000 else ""), language="html")
else:
    st.info("Envie um arquivo PDF para começar.")
