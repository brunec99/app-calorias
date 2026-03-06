import streamlit as st
import datetime
import google.generativeai as genai
from PIL import Image
import re 

# Pegando a chave secreta
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# NOVO: Usando o nome completo da versão mais atualizada do modelo
modelo = genai.GenerativeModel('gemini-1.5-flash-latest')

st.set_page_config(page_title="Meu Diário Alimentar", page_icon="🥗")
st.title("🥗 Controle com Inteligência Artificial")
st.write("Tire uma foto do seu prato. Eu vou analisar e preencher os dados para você!")

if "calorias_ia" not in st.session_state:
    st.session_state.calorias_ia = 0.0
if "proteinas_ia" not in st.session_state:
    st.session_state.proteinas_ia = 0.0
if "falha_ia" not in st.session_state:
    st.session_state.falha_ia = False
if "erro_tecnico" not in st.session_state:
    st.session_state.erro_tecnico = ""

foto = st.camera_input("Tirar foto do prato")

def extrair_numeros(texto):
    numeros = re.findall(r'\d+\.?\d*', texto.replace(',', '.'))
    return numeros

if foto is not None:
    if "ultima_foto" not in st.session_state or st.session_state.ultima_foto != foto:
        with st.spinner("A IA está analisando sua foto... ⏳"):
            try:
                imagem = Image.open(foto)
                comando = "Estime as calorias e proteínas deste prato. Responda APENAS com os dois números separados por vírgula. Exemplo: 350, 25"
                resposta = modelo.generate_content([comando, imagem])
                
                numeros = extrair_numeros(resposta.text)
                
                if len(numeros) >= 2:
                    st.session_state.calorias_ia = float(numeros[0])
                    st.session_state.proteinas_ia = float(numeros[1])
                    st.session_state.falha_ia = False 
                    st.session_state.erro_tecnico = ""
                else:
                    st.session_state.falha_ia = True
                    st.session_state.erro_tecnico = f"A IA não mandou números: {resposta.text}"
                    
            except Exception as e:
                st.session_state.falha_ia = True
                st.session_state.erro_tecnico = str(e)
                st.session_state.calorias_ia = 0.0
                st.session_state.proteinas_ia = 0.0

        st.session_state.ultima_foto = foto
        st.rerun()

    if st.session_state.falha_ia:
        st.warning("Ops, não consegui calcular pela foto.")
        
        if st.session_state.erro_tecnico:
            st.error(f"🔍 Detalhe técnico do erro: {st.session_state.erro_tecnico}")
            
        descricao = st.text_input("Descreva o que você está consumindo:")
        
        if st.button("Calcular pela descrição"):
            with st.spinner("Calculando pela descrição... ⏳"):
                try:
                    comando_texto = f"Estime calorias e proteínas para: '{descricao}'. Responda APENAS com dois números separados por vírgula. Exemplo: 150, 8"
                    resposta_texto = modelo.generate_content(comando_texto)
                    
                    numeros = extrair_numeros(resposta_texto.text)
                    
                    if len(numeros) >= 2:
                        st.session_state.calorias_ia = float(numeros[0])
                        st.session_state.proteinas_ia = float(numeros[1])
                        st.session_state.falha_ia = False 
                        st.session_state.erro_tecnico = ""
                        st.rerun()
                    else:
                        st.error(f"Erro na leitura. A IA respondeu: {resposta_texto.text}")
                except Exception as e:
                    st.error(f"🚨 Erro crítico ao conectar: {e}")

    st.divider() 
    data = st.date_input("Data da refeição", datetime.date.today())
    refeicao = st.selectbox("Refeição", ["Café da manhã", "Lanche da manhã", "Almoço", "Lanche da tarde", "Jantar"])
    
    calorias = st.number_input("Calorias (kcal)", min_value=0.0, format="%.2f", value=st.session_state.calorias_ia)
    proteinas = st.number_input("Proteínas (g)", min_value=0.0, format="%.2f", value=st.session_state.proteinas_ia)
    
    if st.button("Salvar na Planilha"):
        st.success("Dados prontos para salvar!")
