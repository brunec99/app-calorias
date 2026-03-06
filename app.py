import streamlit as st
import datetime # Importando a biblioteca para lidar com datas

# Configuração da página para ficar com cara de app
st.set_page_config(page_title="Meu Diário Alimentar", page_icon="🥗")

st.title("🥗 Controle de Calorias")
st.write("Tire uma foto do seu prato para calcularmos!")

# Isso aqui vai abrir a câmera do seu celular ou do computador
foto = st.camera_input("Tirar foto do prato")

# Se a foto for tirada, mostra os próximos campos
if foto is not None:
    st.success("Foto capturada com sucesso! (Em breve a IA vai ler isso)")
    
    # NOVO: Campo de data (já vem com a data de hoje por padrão)
    data = st.date_input("Data da refeição", datetime.date.today())
    
    # Campos simulando a planilha (depois a IA preencherá sozinha)
    refeicao = st.selectbox("Refeição", ["Café da manhã", "Lanche da manhã", "Almoço", "Lanche da tarde", "Jantar"])
    calorias = st.number_input("Calorias (kcal)", min_value=0.0, format="%.2f")
    proteinas = st.number_input("Proteínas (g)", min_value=0.0, format="%.2f")
    
    # Botão de salvar
    if st.button("Salvar na Planilha"):
        st.info(f"Botão clicado! Dados de {data.strftime('%d/%m/%Y')} prontos. (Em breve conectaremos com o Google Sheets)")
