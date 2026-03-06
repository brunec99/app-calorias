import streamlit as st
import datetime
import google.generativeai as genai
from PIL import Image

# 1. Pegando a chave secreta
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 2. Escolhendo o modelo de IA
modelo = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Meu Diário Alimentar", page_icon="🥗")
st.title("🥗 Controle com Inteligência Artificial")
st.write("Tire uma foto do seu prato. Eu vou analisar e preencher os dados para você!")

# Guardando variáveis na memória para a tela não resetar sozinha
if "calorias_ia" not in st.session_state:
    st.session_state.calorias_ia = 0.0
if "proteinas_ia" not in st.session_state:
    st.session_state.proteinas_ia = 0.0
if "falha_ia" not in st.session_state:
    st.session_state.falha_ia = False

foto = st.camera_input("Tirar foto do prato")

if foto is not None:
    # Se for uma foto nova, a IA analisa
    if "ultima_foto" not in st.session_state or st.session_state.ultima_foto != foto:
        with st.spinner("A IA está analisando sua foto... ⏳"):
            try:
                imagem = Image.open(foto)
                comando = "Analise este prato de comida. Estime as calorias e proteínas. Responda EXATAMENTE neste formato, apenas com números: Calorias, Proteínas. Exemplo: 350, 25"
                resposta = modelo.generate_content([comando, imagem])
                
                valores = resposta.text.split(",")
                st.session_state.calorias_ia = float(valores[0].strip())
                st.session_state.proteinas_ia = float(valores[1].strip())
                st.session_state.falha_ia = False # Deu certo!
                
            except Exception as e:
                # Deu erro (ex: não viu comida na foto, só o copo)
                st.session_state.falha_ia = True
                st.session_state.calorias_ia = 0.0
                st.session_state.proteinas_ia = 0.0

        st.session_state.ultima_foto = foto
        st.rerun() # Atualiza a tela rápido para mostrar os resultados

    # SE A FOTO FALHAR: Abre o campo de texto pedindo descrição
    if st.session_state.falha_ia:
        st.warning("Ops, não consegui identificar a comida pela foto (pode estar muito perto ou escondida).")
        descricao = st.text_input("Descreva o que você está consumindo (Ex: 1 copo grande de café com leite integral)")
        
        if st.button("Calcular pela descrição"):
            with st.spinner("Calculando pela sua descrição... ⏳"):
                try:
                    comando_texto = f"Estime as calorias e proteínas para esta refeição: {descricao}. Responda EXATAMENTE neste formato, apenas com números: Calorias, Proteínas. Exemplo: 350, 25"
                    resposta_texto = modelo.generate_content(comando_texto)
                    valores = resposta_texto.text.split(",")
                    
                    st.session_state.calorias_ia = float(valores[0].strip())
                    st.session_state.proteinas_ia = float(valores[1].strip())
                    st.session_state.falha_ia = False # Tiramos o aviso de erro
                    st.rerun()
                except Exception as e:
                    st.error("Ainda não entendi. Por favor, preencha manualmente abaixo.")

    # --- Mostrando os campos da planilha ---
    st.divider() # Linha para separar visualmente
    data = st.date_input("Data da refeição", datetime.date.today())
    refeicao = st.selectbox("Refeição", ["Café da manhã", "Lanche da manhã", "Almoço", "Lanche da tarde", "Jantar"])
    
    calorias = st.number_input("Calorias (kcal)", min_value=0.0, format="%.2f", value=st.session_state.calorias_ia)
    proteinas = st.number_input("Proteínas (g)", min_value=0.0, format="%.2f", value=st.session_state.proteinas_ia)
    
    if st.button("Salvar na Planilha"):
        st.success(f"Dados prontos: {calorias} kcal e {proteinas}g de proteína. (Em breve nas Planilhas Google!)")
