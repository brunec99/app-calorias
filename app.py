import streamlit as st
import datetime
import google.generativeai as genai
from PIL import Image
import re 
import gspread
import json
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÕES IMPORTANTES ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
modelo = genai.GenerativeModel('gemini-2.5-flash')

# Seu link real!
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1AHYq5qolaKtb1WfHiojwELrdp_u9kLEdFzrCB-aj2g8/edit?gid=1351016745#gid=1351016745"

st.set_page_config(page_title="Meu Diário Alimentar", page_icon="🥗")
st.title("🥗 Controle com Inteligência Artificial")
st.write("Tire uma foto do seu prato. Eu vou analisar e salvar direto na sua planilha!")

# Variáveis de memória
if "calorias_ia" not in st.session_state:
    st.session_state.calorias_ia = 0.0
if "proteinas_ia" not in st.session_state:
    st.session_state.proteinas_ia = 0.0
if "descricao_alimento" not in st.session_state:
    st.session_state.descricao_alimento = ""
if "etapa" not in st.session_state:
    st.session_state.etapa = 1 
if "ultima_foto" not in st.session_state:
    st.session_state.ultima_foto = None

def extrair_numeros(texto):
    return re.findall(r'\d+\.?\d*', texto.replace(',', '.'))

# --- FUNÇÃO DO ROBÔ DA PLANILHA ---
def conectar_planilha():
    try:
        # Pegamos o texto bruto do cofre
        cred_text = st.secrets["GOOGLE_CREDENTIALS"]
        
        # MÁGICA AQUI: O 'strict=False' manda o Python ignorar caracteres invisíveis/quebras de linha ruins!
        dict_credenciais = json.loads(cred_text, strict=False)
        
        escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credenciais = Credentials.from_service_account_info(dict_credenciais, scopes=escopos)
        cliente = gspread.authorize(credenciais)
        
        return cliente.open_by_url(URL_PLANILHA).worksheet("APP_Calorias")
    except Exception as e:
        st.error(f"Erro ao conectar com a Planilha: {e}")
        return None

foto = st.camera_input("Tirar foto do prato")

if foto is not None and foto != st.session_state.ultima_foto:
    st.session_state.ultima_foto = foto
    st.session_state.etapa = 1
    st.session_state.descricao_alimento = ""
    st.session_state.calorias_ia = 0.0
    st.session_state.proteinas_ia = 0.0

if foto is not None:
    # ETAPA 1: Visão
    if st.session_state.etapa == 1:
        with st.spinner("A IA está olhando seu prato... 👀"):
            try:
                imagem = Image.open(foto)
                resposta_visao = modelo.generate_content(["Descreva de forma curta e direta quais alimentos e bebidas você vê nesta imagem.", imagem])
                st.session_state.descricao_alimento = resposta_visao.text.strip()
                st.session_state.etapa = 2 
                st.rerun()
            except Exception as e:
                st.session_state.descricao_alimento = "Não consegui enxergar bem. Digite o que é:"
                st.session_state.etapa = 2
                st.rerun()

    # ETAPA 2: Revisão
    if st.session_state.etapa >= 2:
        st.info("💡 Revise os alimentos abaixo e adicione detalhes se quiser!")
        descricao_editada = st.text_area("O que tem na sua refeição?", value=st.session_state.descricao_alimento)
        
        if st.button("Calcular Nutrientes"):
            with st.spinner("Calculando calorias e proteínas... ⏳"):
                try:
                    comando = f"Estime calorias e proteínas para: '{descricao_editada}'. Responda APENAS com dois números separados por vírgula. Exemplo: 350, 25"
                    resposta_calculo = modelo.generate_content(comando)
                    numeros = extrair_numeros(resposta_calculo.text)
                    
                    if len(numeros) >= 2:
                        st.session_state.calorias_ia = float(numeros[0])
                        st.session_state.proteinas_ia = float(numeros[1])
                        st.session_state.descricao_alimento = descricao_editada
                        st.session_state.etapa = 3 
                        st.rerun()
                    else:
                        st.error("Erro na leitura da IA.")
                except Exception as e:
                    st.error("Erro ao calcular.")

    # ETAPA 3: Salvar no Google Sheets
    if st.session_state.etapa == 3:
        st.divider() 
        st.success("Cálculo concluído!")
        data = st.date_input("Data da refeição", datetime.date.today())
        refeicao = st.selectbox("Refeição", ["Café da manhã", "Lanche da manhã", "Almoço", "Lanche da tarde", "Jantar"])
        
        calorias = st.number_input("Calorias (kcal)", min_value=0.0, format="%.2f", value=st.session_state.calorias_ia)
        proteinas = st.number_input("Proteínas (g)", min_value=0.0, format="%.2f", value=st.session_state.proteinas_ia)
        
        if st.button("Salvar na Planilha 🚀"):
            with st.spinner("O Robô está escrevendo na sua planilha... 🤖✍️"):
                planilha = conectar_planilha()
                if planilha:
                    try:
                        data_formatada = data.strftime("%d/%m/%Y")
                        
                        # Mapeando em qual coluna cada refeição deve entrar
                        mapa_colunas = {
                            "Café da manhã": (2, 3), "Lanche da manhã": (4, 5),
                            "Almoço": (6, 7), "Lanche da tarde": (8, 9), "Jantar": (10, 11)
                        }
                        col_kcal, col_prot = mapa_colunas[refeicao]

                        # Buscando a linha da data correta
                        datas_na_planilha = planilha.col_values(1)
                        linha_alvo = None
                        
                        # Pula o cabeçalho (linhas 1 e 2) na busca
                        for i, valor_data in enumerate(datas_na_planilha):
                            if data_formatada in str(valor_data): 
                                linha_alvo = i + 1 
                                break
                        
                        if linha_alvo is None:
                            # Se não achar a data, cria uma linha nova no final
                            nova_linha = [data_formatada] + [""] * 13 
                            planilha.append_row(nova_linha)
                            linha_alvo = len(planilha.col_values(1))

                        # Escrevendo os dados formatados com vírgula para o Sheets entender como número no BR
                        planilha.update_cell(linha_alvo, col_kcal, f"{calorias}".replace(".", ","))
                        planilha.update_cell(linha_alvo, col_prot, f"{proteinas}".replace(".", ","))

                        st.success(f"🎉 SUCESSO! Valores salvos no {refeicao} do dia {data_formatada}!")
                        st.balloons() 
                    except Exception as e:
                        st.error(f"Erro ao escrever na planilha: {e}")
