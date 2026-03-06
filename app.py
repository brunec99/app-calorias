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

# 🎯 SUAS METAS DIÁRIAS (Altere os números aqui se precisar!)
META_KCAL = 1800.0
META_PROT = 180.0

st.set_page_config(page_title="Meu Diário Alimentar", page_icon="🥗")
st.title("🥗 Controle com Inteligência Artificial")

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

# Variáveis dos gráficos de resumo
if "resumo_atualizado" not in st.session_state:
    st.session_state.resumo_atualizado = False
    st.session_state.total_kcal = 0.0
    st.session_state.total_prot = 0.0

def extrair_numeros(texto):
    return re.findall(r'\d+\.?\d*', texto.replace(',', '.'))

# Transforma textos da planilha como "1.500,50" em números matemáticos
def extrair_numero_planilha(texto):
    texto = str(texto).strip()
    if not texto: return 0.0
    if texto.count(',') == 1 and texto.count('.') <= 1:
        texto = texto.replace('.', '').replace(',', '.')
    else:
        texto = texto.replace(',', '.')
    try:
        return float(texto)
    except:
        return 0.0

# --- FUNÇÃO DO ROBÔ DA PLANILHA ---
def conectar_planilha():
    try:
        cred_text = st.secrets["GOOGLE_CREDENTIALS"]
        dict_credenciais = json.loads(cred_text, strict=False)
        
        if "private_key" in dict_credenciais:
            dict_credenciais["private_key"] = dict_credenciais["private_key"].replace('\\n', '\n')
            
        escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credenciais = Credentials.from_service_account_info(dict_credenciais, scopes=escopos)
        cliente = gspread.authorize(credenciais)
        
        return cliente.open_by_url(URL_PLANILHA).worksheet("APP_Calorias")
    except Exception as e:
        return None

# Função que varre a planilha somando o dia de hoje
def buscar_resumo_hoje():
    planilha = conectar_planilha()
    if not planilha: return 0.0, 0.0
    
    try:
        data_hoje = datetime.date.today().strftime("%d/%m/%Y")
        registros = planilha.get_all_values()
        
        for linha in registros[2:]: # Pula cabeçalho de 2 linhas
            if len(linha) > 0 and data_hoje in str(linha[0]):
                total_kcal = 0.0
                total_prot = 0.0
                
                # Colunas de Kcal: B, D, F, H, J (Índices 1, 3, 5, 7, 9)
                for i in [1, 3, 5, 7, 9]:
                    if len(linha) > i: total_kcal += extrair_numero_planilha(linha[i])
                        
                # Colunas de Prot: C, E, G, I, K (Índices 2, 4, 6, 8, 10)
                for i in [2, 4, 6, 8, 10]:
                    if len(linha) > i: total_prot += extrair_numero_planilha(linha[i])
                        
                return total_kcal, total_prot
                
        return 0.0, 0.0
    except Exception as e:
        return 0.0, 0.0

# ==========================================
# --- SEÇÃO 1: GRÁFICOS DE RESUMO ---
# ==========================================
if not st.session_state.resumo_atualizado:
    with st.spinner("Buscando o quanto você já comeu hoje... 🔄"):
        st.session_state.total_kcal, st.session_state.total_prot = buscar_resumo_hoje()
        st.session_state.resumo_atualizado = True

st.subheader("📊 Seu Progresso Hoje")
col1, col2 = st.columns(2)
with col1:
    st.metric("🔥 Calorias", f"{st.session_state.total_kcal:.0f} / {META_KCAL:.0f} kcal")
    progresso_kcal = min(st.session_state.total_kcal / META_KCAL, 1.0)
    st.progress(progresso_kcal)
    
with col2:
    st.metric("💪 Proteínas", f"{st.session_state.total_prot:.0f} / {META_PROT:.0f} g")
    progresso_prot = min(st.session_state.total_prot / META_PROT, 1.0)
    st.progress(progresso_prot)

st.divider()

# ==========================================
# --- SEÇÃO 2: CÂMERA E IA ---
# ==========================================
st.write("Tire uma foto do seu prato. Eu vou analisar e salvar direto na sua planilha!")
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
                        
                        mapa_colunas = {
                            "Café da manhã": (2, 3), "Lanche da manhã": (4, 5),
                            "Almoço": (6, 7), "Lanche da tarde": (8, 9), "Jantar": (10, 11)
                        }
                        col_kcal, col_prot = mapa_colunas[refeicao]

                        datas_na_planilha = planilha.col_values(1)
                        linha_alvo = None
                        
                        for i, valor_data in enumerate(datas_na_planilha):
                            if data_formatada in str(valor_data): 
                                linha_alvo = i + 1 
                                break
                        
                        if linha_alvo is None:
                            nova_linha = [data_formatada] + [""] * 13 
                            planilha.append_row(nova_linha)
                            linha_alvo = len(planilha.col_values(1))

                        planilha.update_cell(linha_alvo, col_kcal, f"{calorias}".replace(".", ","))
                        planilha.update_cell(linha_alvo, col_prot, f"{proteinas}".replace(".", ","))

                        # MÁGICA: Atualiza as barras de progresso na hora, sem precisar recarregar a página!
                        st.session_state.total_kcal += calorias
                        st.session_state.total_prot += proteinas
                        st.session_state.resumo_atualizado = False 

                        st.success(f"🎉 SUCESSO! Valores salvos no {refeicao} do dia {data_formatada}!")
                        st.balloons() 
                    except Exception as e:
                        st.error(f"Erro ao salvar na planilha: {type(e).__name__} - {str(e)}")
