import streamlit as st
import fitz
import openai
import google.generativeai as genai
import re
import pandas as pd
from openai import RateLimitError

openai.api_key = st.secrets.get("OPENAI_API_KEY", "")
gemini_key = st.secrets.get("GEMINI_API_KEY", "")
if gemini_key:
    genai.configure(api_key=gemini_key)

def prompt_tabelas(texto_pdf: str) -> str:
    return f"""
    Você receberá o texto bruto de um Termo de Referência com tabelas de itens.

    Monte tabelas em HTML (<table>, <thead>, <tbody>, <tr>, <th>, <td>), 
    preservando grupos, número do item, descrição, unidade, código CATMAT, 
    quantidades, preço unitário e preço total.

    Não altere valores numéricos. Responda apenas com HTML válido.

    Texto (pode estar truncado):
    {texto_pdf[:8000]}
    """

def tentar_chatgpt(texto_pdf: str) -> str | None:
    if not openai.api_key:
        return None
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_tabelas(texto_pdf)}],
            temperature=0.0,
        )
        return resp.choices[0].message.content
    except RateLimitError:
        return None
    except Exception:
        return None

def tentar_gemini(texto_pdf: str) -> str | None:
    if not gemini_key:
        return None
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        resp = model.generate_content(prompt_tabelas(texto_pdf))
        return resp.text  # HTML retornado
    except Exception:
        return None

def fallback_regex(texto_pdf: str) -> pd.DataFrame:
    padrao = r"\b([A-Z]{1,4})\s+(\d{5,7})\s+([\d.,]+)\s+([\d.,]+)"
    matches = re.findall(padrao, texto_pdf)
    itens = []
    for i, (unid, catmat, unit, total) in enumerate(matches, start=1):
        itens.append({
            "ITEM": i,
            "UNIDADE": unid,
            "CATMAT": catmat,
            "PRECO_UNIT": unit,
            "PRECO_TOTAL": total,
        })
    return pd.DataFrame(itens)

st.title("TR Validator Híbrido")

uploaded_file = st.file_uploader("PDF do TR", type="pdf")
if uploaded_file:
    raw = uploaded_file.read()
    doc = fitz.open(stream=raw, filetype="pdf")
    texto = "".join(page.get_text() for page in doc)

    html = None
    origem = None

    # 1) tenta ChatGPT
    html = tentar_chatgpt(texto)
    if html:
        origem = "ChatGPT"

    # 2) se não deu, tenta Gemini
    if html is None:
        html = tentar_gemini(texto)
        if html:
            origem = "Gemini"

    if html:
        st.success(f"Tabelas geradas via {origem}.")
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.warning("Nenhuma API de IA pôde gerar HTML agora. Usando fallback interno (regex).")
        df = fallback_regex(texto)
        if df.empty:
            st.error("Fallback também não encontrou itens. Arquivo pode ter estrutura muito diferente.")
        else:
            st.dataframe(df)
            # aqui você pluga suas validações de quantidade, preço e CATMAT
