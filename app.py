import streamlit as st
import datetime
import google.generativeai as genai
from PIL import Image
import re 

# Pegando a chave secreta
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Usando o modelo moderno que a sua chave tem!
modelo = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="Meu Diário Alimentar", page_icon="🥗")
st.title("🥗 Controle com Inteligência Artificial")
st.write("Tire uma foto do seu prato. Eu vou analisar e preencher os dados para você!")

# --- VARIÁVEIS DE MEMÓRIA ---
if "calorias_ia" not in st.session_state:
    st.session_state.calorias_ia = 0.0
if "proteinas_ia" not in st.session_state:
    st.session_state.proteinas_ia = 0.0
if "descricao_alimento" not in st.session_state:
    st.session_state.descricao_alimento = ""
if "etapa" not in st.session_state:
    st.session_state.etapa = 1 # 1: Foto, 2: Revisar texto, 3: Ver resultados
if "ultima_foto" not in st.session_state:
    st.session_state.ultima_foto = None

foto = st.camera_input("Tirar foto do prato")

def extrair_numeros(texto):
    numeros = re.findall(r'\d+\.?\d*', texto.replace(',', '.'))
    return numeros

# Se uma NOVA foto for tirada, reinicia o processo para a Etapa 1
if foto is not None and foto != st.session_state.ultima_foto:
    st.session_state.ultima_foto = foto
    st.session_state.etapa = 1
    st.session_state.descricao_alimento = ""
    st.session_state.calorias_ia = 0.0
    st.session_state.proteinas_ia = 0.0

if foto is not None:
    # --- ETAPA 1: A IA APENAS DESCREVE O QUE VÊ ---
    if st.session_state.etapa == 1:
        with st.spinner("A IA está olhando seu prato... 👀"):
            try:
                imagem = Image.open(foto)
                comando_visao = "Descreva de forma curta e direta quais alimentos e bebidas você vê nesta imagem. Não calcule calorias ainda, apenas diga o que é."
                resposta_visao = modelo.generate_content([comando_visao, imagem])
                
                st.session_state.descricao_alimento = resposta_visao.text.strip()
                st.session_state.etapa = 2 # Avança para a revisão
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao analisar a imagem: {e}")
                st.session_state.descricao_alimento = "Não consegui enxergar bem. Digite o que é:"
                st.session_state.etapa = 2
                st.rerun()

    # --- ETAPA 2: USUÁRIO REVISA E EDITA O TEXTO ---
    if st.session_state.etapa >= 2:
        st.info("💡 Revise os alimentos abaixo. Se eu errei ou se faltou algum detalhe oculto (ex: 'fritei com manteiga', 'adicionei whey'), pode digitar aí!")
        
        # Caixa de texto editável com o que a IA viu
        descricao_editada = st.text_area("O que tem na sua refeição?", value=st.session_state.descricao_alimento)
        
        if st.button("Calcular Nutrientes"):
            with st.spinner("Calculando calorias e proteínas... ⏳"):
                try:
                    comando_calculo = f"Estime as calorias e proteínas para esta refeição: '{descricao_editada}'. Responda APENAS com dois números separados por vírgula. Exemplo: 350, 25"
                    resposta_calculo = modelo.generate_content(comando_calculo)
                    
                    numeros = extrair_numeros(resposta_calculo.text)
                    
                    if len(numeros) >= 2:
                        st.session_state.calorias_ia = float(numeros[0])
                        st.session_state.proteinas_ia = float(numeros[1])
                        st.session_state.descricao_alimento = descricao_editada
                        st.session_state.etapa = 3 # Avança para os resultados
                        st.rerun()
                    else:
                        st.error(f"Erro na leitura. A IA respondeu: {resposta_calculo.text}")
                except Exception as e:
                    st.error(f"🚨 Erro ao calcular: {e}")

    # --- ETAPA 3: MOSTRA A PLANILHA PREENCHIDA ---
    if st.session_state.etapa == 3:
        st.divider() 
        st.success("Cálculo concluído!")
        data = st.date_input("Data da refeição", datetime.date.today())
        refeicao = st.selectbox("Refeição", ["Café da manhã", "Lanche da manhã", "Almoço", "Lanche da tarde", "Jantar"])
        
        calorias = st.number_input("Calorias (kcal)", min_value=0.0, format="%.2f", value=st.session_state.calorias_ia)
        proteinas = st.number_input("Proteínas (g)", min_value=0.0, format="%.2f", value=st.session_state.proteinas_ia)
        
        if st.button("Salvar na Planilha"):
            st.success("Dados prontos para salvar!")
