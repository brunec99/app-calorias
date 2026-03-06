import streamlit as st
import datetime
import google.generativeai as genai
from PIL import Image

# 1. Pegando a chave secreta que você guardou lá nos Secrets
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 2. Escolhendo o modelo de IA que lê imagens rapidamente
modelo = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Meu Diário Alimentar", page_icon="🥗")
st.title("🥗 Controle com Inteligência Artificial")
st.write("Tire uma foto do seu prato. Eu vou analisar e preencher os dados para você!")

foto = st.camera_input("Tirar foto do prato")

if foto is not None:
    # Mostrando aviso de carregamento
    st.success("Foto capturada! A IA está analisando seu prato... ⏳")
    
    # Lógica para a IA analisar a foto apenas uma vez quando tirada
    if "ultima_foto" not in st.session_state or st.session_state.ultima_foto != foto:
        try:
            # Transformando a foto em um formato que a IA entende
            imagem = Image.open(foto)
            
            # O comando que vamos dar para a IA
            comando = "Analise este prato de comida. Estime as calorias e proteínas. Responda EXATAMENTE neste formato, apenas com números: Calorias, Proteínas. Exemplo: 350, 25"
            
            # Pedindo para a IA olhar a foto
            resposta = modelo.generate_content([comando, imagem])
            
            # Pegando a resposta (ex: "350, 25") e quebrando nos dois campos
            valores = resposta.text.split(",")
            st.session_state.calorias_ia = float(valores[0].strip())
            st.session_state.proteinas_ia = float(valores[1].strip())
            st.session_state.ultima_foto = foto
            
        except Exception as e:
            st.error("Ops, não consegui identificar os alimentos com clareza. Você pode preencher manualmente abaixo.")
            st.session_state.calorias_ia = 0.0
            st.session_state.proteinas_ia = 0.0

    # Os campos agora já vêm preenchidos com o valor que a IA calculou!
    data = st.date_input("Data da refeição", datetime.date.today())
    refeicao = st.selectbox("Refeição", ["Café da manhã", "Lanche da manhã", "Almoço", "Lanche da tarde", "Jantar"])
    
    calorias = st.number_input("Calorias (kcal)", min_value=0.0, format="%.2f", value=st.session_state.calorias_ia)
    proteinas = st.number_input("Proteínas (g)", min_value=0.0, format="%.2f", value=st.session_state.proteinas_ia)
    
    if st.button("Salvar na Planilha"):
        st.info(f"Sucesso! Prato de {calorias} kcal e {proteinas}g de proteína pronto para ser salvo.")
