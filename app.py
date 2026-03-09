import streamlit as st
import datetime
import google.generativeai as genai
from PIL import Image
import re 
import gspread
import json
import pandas as pd
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÕES IMPORTANTES ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
modelo = genai.GenerativeModel('gemini-2.5-flash')

# Seu link real!
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1AHYq5qolaKtb1WfHiojwELrdp_u9kLEdFzrCB-aj2g8/edit?gid=1351016745#gid=1351016745"

# 🎯 SUAS METAS DIÁRIAS
META_KCAL = 1800.0
META_PROT = 180.0

# 🕒 FUSO HORÁRIO DO BRASIL (UTC-3)
FUSO_BR = datetime.timezone(datetime.timedelta(hours=-3))

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
if "erro_ia" not in st.session_state:
    st.session_state.erro_ia = ""

if "resumo_atualizado" not in st.session_state:
    st.session_state.resumo_atualizado = False
    st.session_state.total_kcal = 0.0
    st.session_state.total_prot = 0.0
    st.session_state.historico = []

def extrair_numeros(texto):
    return re.findall(r'\d+\.?\d*', texto.replace(',', '.'))

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

def buscar_resumo_hoje():
    planilha = conectar_planilha()
    if not planilha: return 0.0, 0.0
    
    try:
        data_hoje = datetime.datetime.now(FUSO_BR).strftime("%d/%m/%Y")
        registros = planilha.get_all_values()
        
        soma_kcal = 0.0
        soma_prot = 0.0
        
        for linha in registros[2:]: 
            if len(linha) > 0 and data_hoje in str(linha[0]):
                for i in [1, 3, 5, 7, 9]:
                    if len(linha) > i: soma_kcal += extrair_numero_planilha(linha[i])
                for i in [2, 4, 6, 8, 10]:
                    if len(linha) > i: soma_prot += extrair_numero_planilha(linha[i])
                return soma_kcal, soma_prot
                
        return 0.0, 0.0
    except Exception as e:
        return 0.0, 0.0

def buscar_historico(dias=7):
    planilha = conectar_planilha()
    if not planilha: return []
    
    try:
        registros = planilha.get_all_values()[2:] 
        historico = []
        
        for linha in reversed(registros):
            if not linha or not str(linha[0]).strip(): continue
            data_str = str(linha[0]).strip()
            
            total_kcal = 0.0
            total_prot = 0.0
            for i in [1, 3, 5, 7, 9]:
                if len(linha) > i: total_kcal += extrair_numero_planilha(linha[i])
            for i in [2, 4, 6, 8, 10]:
                if len(linha) > i: total_prot += extrair_numero_planilha(linha[i])
            
            if total_kcal == 0 and total_prot == 0:
                continue
                
            data_curta = data_str[:5] 
            historico.insert(0, {"Data": data_curta, "Calorias (kcal)": total_kcal, "Proteínas (g)": total_prot})
            
            if len(historico) >= dias:
                break
        return historico
    except Exception as e:
        return []

# ==========================================
# --- PAINEL DE DADOS ---
# ==========================================
if not st.session_state.resumo_atualizado:
    with st.spinner("Buscando seus dados na planilha... 🔄"):
        st.session_state.total_kcal, st.session_state.total_prot = buscar_resumo_hoje()
        st.session_state.historico = buscar_historico(7)
        st.session_state.resumo_atualizado = True

aba_hoje, aba_graficos = st.tabs(["📊 Progresso de Hoje", "📈 Histórico Semanal"])

with aba_hoje:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🔥 Calorias", f"{st.session_state.total_kcal:.0f} / {META_KCAL:.0f} kcal")
        progresso_kcal = min(st.session_state.total_kcal / META_KCAL, 1.0)
        st.progress(progresso_kcal)
        
    with col2:
        st.metric("💪 Proteínas", f"{st.session_state.total_prot:.0f} / {META_PROT:.0f} g")
        progresso_prot = min(st.session_state.total_prot / META_PROT, 1.0)
        st.progress(progresso_prot)

with aba_graficos:
    if st.session_state.historico:
        df = pd.DataFrame(st.session_state.historico)
        df.set_index("Data", inplace=True)
        
        st.markdown("**Calorias nos últimos 7 dias**")
        st.bar_chart(df["Calorias (kcal)"], color="#ff5a5f") 
        
        st.markdown("**Proteínas nos últimos 7 dias**")
        st.bar_chart(df["Proteínas (g)"], color="#1f77b4") 
    else:
        st.info("Ainda não há refeições suficientes registradas para gerar o gráfico.")

st.divider()

# ==========================================
# --- CÂMERA E IA ---
# ==========================================
st.write("Envie uma foto do seu prato. Eu vou analisar e salvar direto na sua planilha!")

aba_camera, aba_galeria = st.tabs(["📸 Tirar Foto", "📁 Enviar da Galeria"])

with aba_camera:
    foto_camera = st.camera_input("Tirar foto na hora")
    
with aba_galeria:
    foto_galeria = st.file_uploader("Escolha uma foto da sua galeria", type=["png", "jpg", "jpeg"])

foto = foto_camera or foto_galeria

if foto is not None and foto != st.session_state.ultima_foto:
    st.session_state.ultima_foto = foto
    st.session_state.etapa = 1
    st.session_state.descricao_alimento = ""
    st.session_state.calorias_ia = 0.0
    st.session_state.proteinas_ia = 0.0
    st.session_state.erro_ia = ""

if foto is not None:
    if st.session_state.etapa == 1:
        with st.spinner("A IA está olhando seu prato... 👀"):
            try:
                imagem = Image.open(foto)
                resposta_visao = modelo.generate_content(["Descreva de forma curta e direta quais alimentos e bebidas você vê nesta imagem.", imagem])
                st.session_state.descricao_alimento = resposta_visao.text.strip()
                st.session_state.erro_ia = ""
                st.session_state.etapa = 2 
                st.rerun()
            except Exception as e:
                st.session_state.erro_ia = str(e)
                st.session_state.descricao_alimento = "Não consegui enxergar bem. Digite o que é:"
                st.session_state.etapa = 2
                st.rerun()

    if st.session_state.etapa >= 2:
        if st.session_state.erro_ia:
            st.warning(f"🔍 Aviso técnico da Visão: {st.session_state.erro_ia}")

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
                        st.session_state.erro_ia = ""
                        st.session_state.etapa = 3 
                        st.rerun()
                    else:
                        st.error(f"Erro na leitura da IA: {resposta_calculo.text}")
                except Exception as e:
                    st.error(f"🚨 Erro técnico ao calcular: {e}")

    if st.session_state.etapa == 3:
        st.divider() 
        st.success("Cálculo concluído!")
        
        data = st.date_input("Data da refeição", datetime.datetime.now(FUSO_BR).date())
        
        hora_atual = datetime.datetime.now(FUSO_BR).hour
        if hora_atual < 11: refeicao_sugerida = 0 
        elif hora_atual < 13: refeicao_sugerida = 1 
        elif hora_atual < 16: refeicao_sugerida = 2 
        elif hora_atual < 19: refeicao_sugerida = 3 
        else: refeicao_sugerida = 4 
            
        refeicao = st.selectbox("Refeição", ["Café da manhã", "Lanche da manhã", "Almoço", "Lanche da tarde", "Jantar"], index=refeicao_sugerida)
        
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

                        # Pega todos os registros para descobrirmos a linha certa e o que já tem lá
                        registros = planilha.get_all_values()
                        datas_na_planilha = [linha[0] if len(linha) > 0 else "" for linha in registros]
                        
                        linha_alvo = None
                        for i, valor_data in enumerate(datas_na_planilha):
                            if data_formatada in str(valor_data): 
                                linha_alvo = i + 1 
                                break
                        
                        valor_atual_kcal = 0.0
                        valor_atual_prot = 0.0
                        
                        # Se o dia não existe, cria nova linha
                        if linha_alvo is None:
                            nova_linha = [data_formatada] + [""] * 13 
                            planilha.append_row(nova_linha)
                            linha_alvo = len(planilha.col_values(1))
                        else:
                            # Se o dia existe, o robô LÊ o que já tem lá na coluna antes de escrever!
                            linha_dados = registros[linha_alvo - 1]
                            if len(linha_dados) >= col_kcal:
                                valor_atual_kcal = extrair_numero_planilha(linha_dados[col_kcal - 1])
                            if len(linha_dados) >= col_prot:
                                valor_atual_prot = extrair_numero_planilha(linha_dados[col_prot - 1])

                        # A MÁGICA: Soma as calorias da refeição atual com o que já estava na planilha
                        novo_kcal = valor_atual_kcal + calorias
                        novo_prot = valor_atual_prot + proteinas

                        # Escreve o valor SOMADO
                        planilha.update_cell(linha_alvo, col_kcal, f"{novo_kcal:.2f}".replace(".", ","))
                        planilha.update_cell(linha_alvo, col_prot, f"{novo_prot:.2f}".replace(".", ","))

                        st.session_state.resumo_atualizado = False 

                        st.success(f"🎉 SUCESSO! Refeição adicionada ao {refeicao} do dia {data_formatada}!")
                        st.balloons() 
                    except Exception as e:
                        st.error(f"Erro ao salvar na planilha: {type(e).__name__} - {str(e)}")
