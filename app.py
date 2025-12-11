import fitz  # PyMuPDF

uploaded_file = st.file_uploader("PDF TR", type="pdf")

if uploaded_file is not None:
    # Ler PDF em texto (você pode usar seu método atual)
    raw_bytes = uploaded_file.read()
    doc = fitz.open(stream=raw_bytes, filetype="pdf")
    texto_pdf = ""
    for page in doc:
        texto_pdf += page.get_text()

    if st.button("Converter PDF em HTML (ChatGPT)"):
        with st.spinner("Chamando ChatGPT para montar as tabelas em HTML..."):
            html_tabelas = pdf_texto_para_html_tabela(texto_pdf)

        st.subheader("HTML gerado pelo ChatGPT")
        # Renderiza o HTML da tabela do jeito que veio
        st.markdown(html_tabelas, unsafe_allow_html=True)

        # Se quiser, também mostrar o código HTML puro para inspeção:
        st.code(html_tabelas[:2000] + ("..." if len(html_tabelas) > 2000 else ""), language="html")
