import streamlit as st
from PIL import Image
import io
import google.generativeai as genai
import openai
from openai import RateLimitError, AuthenticationError, APIError

# ------------------------------------
# CONFIGURAÇÃO DE CHAVES / MODELOS
# ------------------------------------

st.set_page_config(layout="wide")
st.title("🔍 TR (imagens) → Tabelas HTML (Gemini OU ChatGPT)")

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

GEMINI_MODEL = "gemini-1.5-pro"   # ajuste se sua conta usar outro nome
OPENAI_MODEL = "gpt-4o-mini"      # ajuste se preferir outro


# ------------------------------------
# PROMPT ÚNICO PARA AS DUAS IAs
# ------------------------------------

def montar_prompt_html():
    return """
Você receberá uma ou mais imagens de páginas de um Termo de Referência
com tabelas de itens (grupos, código CATMAT, descrição, unidade de fornecimento,
quantidades, preço unitário e preço total).

TAREFA:
- Reconstruir as tabelas em HTML usando <table>, <thead>, <tbody>, <tr>, <th>, <td>.
- Manter a estrutura original: grupos, número do item, descrição, unidade, código CATMAT,
  quantidades, preço unitário e preço total.
- NÃO alterar nem arredondar valores numéricos; copie-os como aparecem.
- Se houver vários grupos, use um <h3> para cada grupo e uma <table> separada.
- Não adicionar explicações em texto; responda apenas com HTML válido.
"""


# ------------------------------------
# 1) TENTAR GEMINI
# ------------------------------------

def tentar_gemini_html(imagens_pil):
    """
    Tenta gerar HTML das tabelas usando Gemini (visão).
    Retorna (html, erro_texto_ou_None).
    """
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY não configurada."

    prompt = montar_prompt_html()

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        contents = [prompt] + imagens_pil
        resp = model.generate_content(contents)
        html = resp.text or ""
        if not html.strip():
            return None, "Gemini retornou resposta vazia."
        return html, None
    except Exception as e:
        return None, f"Erro Gemini: {e}"


# ------------------------------------
# 2) TENTAR CHATGPT (OpenAI)
# ------------------------------------

def tentar_chatgpt_html(imagens_pil):
    """
    Tenta gerar HTML das tabelas usando ChatGPT.
    Versão simples: neste esqueleto, o prompt é apenas textual,
    supondo que você descreva as imagens, ou que tenha OCR antes.
    Para uso real com visão, seria preciso enviar as imagens via modelo com imagem.
    """
    if not OPENAI_API_KEY:
        return None, "OPENAI_API_KEY não configurada."

    prompt = montar_prompt_html() + "\n\n(Observação: esta chamada está em modo texto simples neste esqueleto.)"

    try:
        resp = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt + "\n\nDescreva as tabelas das imagens como HTML, assumindo que as imagens contêm as tabelas."
                }
            ],
            temperature=0.0,
        )
        html = resp.choices[0].message.content or ""
        if not html.strip():
            return None, "ChatGPT retornou resposta vazia."
        return html, None
    except (RateLimitError, AuthenticationError, APIError) as e:
        return None, f"Erro OpenAI: {e}"
    except Exception as e:
        return None, f"Erro OpenAI: {e}"


# ------------------------------------
# 3) ORQUESTRADOR HÍBRIDO
# ------------------------------------

def gerar_html_tabelas_hibrido(imagens_pil):
    """
    Fluxo:
    1) Tenta Gemini.
    2) Se falhar, tenta ChatGPT.
    3) Se nenhum funcionar, retorna None e mensagens de erro.
    """
    erros = []

    # 1) Gemini
    html, err = tentar_gemini_html(imagens_pil)
    if html:
        return html, "Gemini", erros
    if err:
        erros.append(err)

    # 2) ChatGPT
    html, err = tentar_chatgpt_html(imagens_pil)
    if html:
        return html, "ChatGPT", erros
    if err:
        erros.append(err)

    return None, None, erros


# ------------------------------------
# INTERFACE STREAMLIT
# ------------------------------------

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
        img = Image.open(io.BytesIO(f.read()))
        imagens_pil.append(img)
        with cols[i % len(cols)]:
            st.image(img, caption=f"Página {i+1}", use_column_width=True)

    if st.button("🔄 Gerar HTML das tabelas (Gemini → ChatGPT → Fallback)"):
        with st.spinner("Tentando Gemini, depois ChatGPT, para gerar HTML das tabelas..."):
            html, origem, erros = gerar_html_tabelas_hibrido(imagens_pil)

        if origem and html:
            st.success(f"Tabelas geradas via {origem}.")
            st.subheader("📊 Tabelas em HTML")
            st.markdown(html, unsafe_allow_html=True)

            st.subheader("🔎 Código HTML (para inspeção)")
            st.code(html[:4000] + ("..." if len(html) > 4000 else ""), language="html")

            if erros:
                st.info("Mensagens de erro da outra IA (que não foi usada):\n" + "\n".join(erros))
        else:
            st.error("Nenhuma API conseguiu gerar HTML neste momento.")
            if erros:
                st.text("Detalhes dos erros:")
                for e in erros:
                    st.text(f"- {e}")
else:
    st.info("Envie uma ou mais imagens das páginas do TR para começar.")
