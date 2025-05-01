import streamlit as st
import pandas as pd
import altair as alt
import re # Import regex for search
from datetime import datetime # For date filtering
import random # For study blocks
import os # To check file existence
import json # To store user credentials
import bcrypt # For password hashing
import pickle # To save/load user data (read status)
from pathlib import Path # To handle file paths
import logging # For activity logging
import csv # For CSV report

import openai

# --- OpenAI API Key Configuration ---
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise Exception("OPENAI_API_KEY não configurada.")
openai.api_key = openai_api_key

# --- Page Config ---
st.set_page_config(
    page_title="Informativos STF | Mentoria de Resultado",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load CSS --- 
def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Arquivo CSS '{file_name}' não encontrado.")
load_css("style.css")

# --- Custom Authentication & Logging Setup --- 

USER_CREDENTIALS_FILE = Path("./user_credentials.json")
USER_DATA_DIR = Path("./user_data")
LOG_FILE = Path("./activity_log.csv")
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Setup Logging
log_formatter = logging.Formatter('%(asctime)s,%(levelname)s,%(message)s')
log_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger('activity_logger')
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

# Ensure CSV header exists
if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
    with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'level', 'username', 'action', 'details'])

def log_activity(username, action, details=""):
    # Use logger to write structured CSV data
    logger.info(f"{username},{action},{details}")

# Password Hashing Functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password)

# User Credential Management
def load_credentials():
    if USER_CREDENTIALS_FILE.exists():
        with open(USER_CREDENTIALS_FILE, "r") as f:
            try:
                creds = json.load(f)
                # Decode passwords back to bytes for bcrypt
                for username, data in creds.items():
                    if 'password' in data and isinstance(data['password'], str):
                        creds[username]['password'] = data['password'].encode('latin-1') # Assuming latin-1 was used for saving
                return creds
            except json.JSONDecodeError:
                return {}
    return {}

def save_credentials(credentials):
    with open(USER_CREDENTIALS_FILE, "w") as f:
        creds_to_save = {}
        for username, data in credentials.items():
            creds_to_save[username] = data.copy()
            # Encode bytes password to string for JSON serialization
            if 'password' in data and isinstance(data['password'], bytes):
                creds_to_save[username]['password'] = data['password'].decode('latin-1') # Use latin-1 for reversibility
        json.dump(creds_to_save, f)

# User Read Status Data Management
def save_user_data(username, data):
    filepath = USER_DATA_DIR / f"{username}.pkl"
    with open(filepath, "wb") as f:
        pickle.dump(data, f)

def load_user_data(username):
    filepath = USER_DATA_DIR / f"{username}.pkl"
    if filepath.exists():
        with open(filepath, "rb") as f:
            try:
                return pickle.load(f)
            except Exception as e:
                print(f"Error loading data for {username}: {e}")
                return {"read_ids": set()}
    return {"read_ids": set()}

# Initialize session state for login status
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "name" not in st.session_state:
    st.session_state.name = None

# --- Login/Registration Forms --- 

def show_login_form():
    st.subheader("Login")
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        if submitted:
            credentials = load_credentials()
            if username in credentials and 'password' in credentials[username] and check_password(credentials[username]['password'], password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.name = credentials[username].get('name', username)
                log_activity(username, "login") # Log login
                st.rerun() # Force rerun after successful login
            else:
                st.error("Usuário ou senha inválidos.")

def show_registration_form():
    st.subheader("Registrar Novo Usuário")
    with st.form("registration_form"):
        username = st.text_input("Escolha um nome de usuário")
        name = st.text_input("Seu nome (para exibição)")
        password = st.text_input("Escolha uma senha", type="password")
        confirm_password = st.text_input("Confirme a senha", type="password")
        submitted = st.form_submit_button("Registrar")
        if submitted:
            credentials = load_credentials()
            if not username or not password or not name:
                 st.error("Por favor, preencha todos os campos.")
            elif username in credentials:
                st.error("Nome de usuário já existe.")
            elif password != confirm_password:
                st.error("As senhas não coincidem.")
            else:
                hashed_pw = hash_password(password)
                credentials[username] = {"password": hashed_pw, "name": name}
                save_credentials(credentials)
                log_activity(username, "register") # Log registration
                st.success("Usuário registrado com sucesso! Você já pode fazer o login.")
                st.info("Retornando à tela de login...")
                # Consider adding a small delay or just letting the user switch tabs

# Inicializa as variáveis com valores padrão
df_informativos_exploded, df_informativos_original = None, None

# Carrega os dados necessários
data_path = "Dados_InformativosSTF_2021-2025.xlsx"
df_informativos_exploded, df_informativos_original = load_data(data_path)

# --- Display Login/Registration or Main App --- 
if not st.session_state.logged_in:
    # Display Logo Centered on Login Page
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        col1_logo, col2_logo, col3_logo = st.columns([1,1,1])
        with col2_logo:
             st.image(logo_path, width=200) # Adjust width as needed
    else:
        st.warning("Arquivo de logo 'logo.png' não encontrado.")

    login_tab, register_tab = st.tabs(["Login", "Registrar"])
    with login_tab:
        show_login_form()
    with register_tab:
        show_registration_form()

else:
    # --- Main App Logic (User is Logged In) ---
    current_username = st.session_state.username
    current_name = st.session_state.name

    # --- Load User Specific Data --- 
    user_data = load_user_data(current_username)
    read_ids = user_data.get("read_ids", set())

    # --- Load Data (Moved to Main Scope) ---
    @st.cache_data
    def load_data(excel_path):
        try:
            df = pd.read_excel(excel_path)
            # --- Data Cleaning and Preparation (Keep existing logic) ---
            potential_names = {
                'Informativo': ['Informativo', 'Numero do informativo', 'Número do Informativo'],
                'Classe Processo': ['Classe Processo'],
                'Data Julgamento': ['Data Julgamento', 'Data do Julgamento'],
                'Título': ['Título', 'Titulo'],
                'Tese Julgado': ['Tese Julgado', 'Tese do Julgado'],
                'Resumo': ['Resumo'],
                'Ramo Direito': ['Ramo Direito', 'Ramo do Direito'],
                'Matéria': ['Matéria', 'Materia'],
                'Repercussão Geral': ['Repercussão Geral', 'Repercussao Geral'],
                'Tema RG': ['Tema RG', 'Tema de RG', 'Tema Repercussão Geral'],
                'Legislação': ['Legislação', 'Legislacao'],
                'Notícia Completa': ['Notícia Completa', 'Noticia Completa', 'Notícia completa']
            }
            actual_cols = {}
            missing_essential = []
            essential_user_cols = ['Classe Processo', 'Data Julgamento', 'Título', 'Tese Julgado', 'Resumo', 'Ramo Direito', 'Matéria', 'Repercussão Geral', 'Notícia Completa']
            for target_name, possible_names in potential_names.items():
                found = False
                for name in possible_names:
                    if name in df.columns:
                        actual_cols[target_name] = name
                        found = True
                        break
                if not found:
                    # If essential, mark as missing, otherwise create empty
                    if target_name in essential_user_cols:
                        missing_essential.append(target_name)
                    df[target_name] = '' # Create empty column
                elif actual_cols[target_name] != target_name:
                    # Rename found column to target name
                    df.rename(columns={actual_cols[target_name]: target_name}, inplace=True)
            
            # Check for critical missing columns
            if 'Data Julgamento' in missing_essential:
                 raise ValueError("Erro Crítico: Coluna essencial 'Data Julgamento' não encontrada no Excel.")
            elif missing_essential:
                 st.warning(f"Aviso: Colunas essenciais não encontradas e criadas vazias: {', '.join(missing_essential)}. Algumas funcionalidades podem ser afetadas.")
            
            # Ensure all target columns exist, even if empty
            user_cols_to_keep = list(potential_names.keys())
            for col in user_cols_to_keep:
                if col not in df.columns:
                    df[col] = ''
                    
            df = df[user_cols_to_keep] # Select and order columns
            
            # Data Type Conversions and Cleaning
            df['Data Julgamento'] = pd.to_datetime(df['Data Julgamento'], errors='coerce')
            df.dropna(subset=['Data Julgamento'], inplace=True)
            df['ano_julgamento'] = df['Data Julgamento'].dt.year
            df['mes_julgamento'] = df['Data Julgamento'].dt.month
            df['ano_mes_julgamento'] = df['Data Julgamento'].dt.strftime('%Y-%m')
            
            text_cols = ['Título', 'Tese Julgado', 'Resumo', 'Ramo Direito', 'Matéria', 'Tema RG', 'Legislação', 'Notícia Completa', 'Classe Processo']
            for col in text_cols:
                if col in df.columns:
                    df[col] = df[col].fillna('').astype(str)
                else:
                    df[col] = '' # Ensure column exists as string
                    
            if 'Informativo' in df.columns:
                 df['Informativo'] = pd.to_numeric(df['Informativo'], errors='coerce')
                 df['Informativo'] = df['Informativo'].astype('Int64').astype(str).replace('<NA>', '')
            else:
                df['Informativo'] = ''
                
            if 'Repercussão Geral' in df.columns:
                df['Repercussão Geral'] = df['Repercussão Geral'].fillna('Não Informado').astype(str).str.strip().str.capitalize()
                df['Repercussão Geral'] = df['Repercussão Geral'].replace({'Nao': 'Não'}, regex=False)
                valid_rg_values = ['Sim', 'Não', 'Não Informado']
                df.loc[~df['Repercussão Geral'].isin(valid_rg_values), 'Repercussão Geral'] = 'Não Informado'
            else:
                df['Repercussão Geral'] = 'Não Informado'
                
            df['id'] = range(len(df))
            df['id'] = df['id'].astype(str)
            
            # Process 'Ramo Direito' - Ensure it's a list of strings
            if 'Ramo Direito' in df.columns:
                df['Ramo Direito'] = df['Ramo Direito'].apply(lambda x: [item.strip() for item in str(x).split(';') if item.strip()])
            else:
                 df['Ramo Direito'] = [[] for _ in range(len(df))]
                 
            # Keep the original DataFrame before exploding for unique ID operations
            df_original = df.copy()
            
            # Explode only if the column exists and has lists
            if 'Ramo Direito' in df.columns and df['Ramo Direito'].apply(isinstance, args=(list,)).any():
                df_exploded = df.explode('Ramo Direito')
                df_exploded['Ramo Direito'] = df_exploded['Ramo Direito'].fillna('') # Fill NaNs created by explode
            else:
                df_exploded = df # No explosion needed or possible
                if 'Ramo Direito' not in df_exploded.columns:
                     df_exploded['Ramo Direito'] = '' # Ensure column exists
                else:
                     df_exploded['Ramo Direito'] = df_exploded['Ramo Direito'].fillna('')
                     
            # Filter by year range after processing
            df_exploded = df_exploded[(df_exploded['ano_julgamento'] >= 2021) & (df_exploded['ano_julgamento'] <= 2025)]
            
            return df_exploded, df_original
        except FileNotFoundError:
            st.error(f"Erro: Arquivo Excel não encontrado em {excel_path}")
            return None, None
        except ValueError as ve:
            st.error(f"Erro de Valor: {ve}")
            return None, None
        except Exception as e:
            st.error(f"Erro ao carregar ou processar os dados do Excel: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None

    # Inicializa as variáveis com valores padrão
    df_informativos_exploded = None
    df_informativos_original = None

    data_path = "Dados_InformativosSTF_2021-2025.xlsx"
    df_informativos_exploded, df_informativos_original = load_data(data_path)

    # --- Sidebar --- 
    with st.sidebar:
        # Logo at the top of the sidebar
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=150) # Adjust width as needed
        else:
            st.warning("Arquivo de logo 'logo.png' não encontrado.")
        
        st.subheader(f'Bem-vindo(a), {current_name}!')
        if st.button("Logout"):
            log_activity(current_username, "logout") # Log logout
            # Clear session state related to the user
            for key in list(st.session_state.keys()):
                if key not in ['logged_in', 'username', 'name']: # Keep basic login state
                    del st.session_state[key]
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.name = None
            st.rerun() # Force rerun after logout
        st.divider()
        st.header("Filtros Principais")
        
        # Add filters to sidebar (only if data loaded)
        if df_informativos_exploded is not None:
            anos_disponiveis = sorted(df_informativos_exploded['ano_julgamento'].dropna().unique().astype(int), reverse=True)
            meses_anos_disponiveis = sorted(df_informativos_exploded['ano_mes_julgamento'].dropna().unique(), reverse=True)
            # Get unique ramos from the exploded dataframe
            ramos_disponiveis = sorted(df_informativos_exploded['Ramo Direito'].dropna().unique())
            # Filter out empty strings if present
            ramos_disponiveis = [ramo for ramo in ramos_disponiveis if ramo]
            classes_disponiveis = sorted(df_informativos_exploded['Classe Processo'].dropna().unique())
            rg_options = ['Todos'] + sorted(df_informativos_exploded['Repercussão Geral'].dropna().unique())

            date_filter_type = st.radio("Filtrar Data Por:", ["Ano", "Mês/Ano"], index=0, key="sidebar_date_filter", help="Selecione como deseja filtrar os julgados por data.")
            selected_anos = []
            selected_meses_anos = []
            if date_filter_type == "Ano":
                selected_anos = st.multiselect("Ano do Julgamento", anos_disponiveis, default=anos_disponiveis, key="sidebar_ano", help="Selecione um ou mais anos.")
            else:
                selected_meses_anos = st.multiselect("Mês/Ano do Julgamento", meses_anos_disponiveis, default=[], key="sidebar_mes_ano", help="Selecione um ou mais meses/anos.", placeholder="Selecione uma opção")

            selected_ramos = st.multiselect("Ramo do Direito", ramos_disponiveis, default=[], key="sidebar_ramo", help="Selecione um ou mais ramos.", placeholder="Selecione uma opção")
            selected_classes = st.multiselect("Classe Processual", classes_disponiveis, default=[], key="sidebar_classe", help="Selecione uma ou mais classes.", placeholder="Selecione uma opção")
            selected_rg = st.radio("Repercussão Geral", rg_options, index=rg_options.index('Todos') if 'Todos' in rg_options else 0, key="sidebar_rg", help="Filtrar por reconhecimento de Repercussão Geral.")
            # Read status filter using radio buttons
            read_status_filter = st.radio(
                "Mostrar:", 
                ("Todos", "Apenas Não Lidos", "Apenas Lidos"), 
                index=0, 
                key="sidebar_read_status", 
                horizontal=True, 
                help="Filtrar julgados com base no status de leitura."
            )
            # show_unread_only = st.checkbox("Mostrar Apenas Não Lidos", value=False, key="sidebar_unread", help="Exibe apenas os julgados que você ainda não marcou como lidos.")
        else:
            st.error("Não foi possível carregar os dados. Filtros indisponíveis.")
            selected_anos = []
            selected_meses_anos = []
            selected_ramos = []
            selected_rg = 'Todos'
            show_unread_only = False
            date_filter_type = "Ano"

# --- Main Content Area --- 
if df_informativos_exploded is not None and df_informativos_original is not None:
    # Initialize session state for other selections
    if 'selected_julgado_id_assertiva' not in st.session_state:
        st.session_state.selected_julgado_id_assertiva = None
    if 'selected_julgado_id_caso' not in st.session_state:
        st.session_state.selected_julgado_id_caso = None
    if 'selected_julgado_id_pergunta' not in st.session_state: # NEW: For questions
        st.session_state.selected_julgado_id_pergunta = None
    if 'show_caso_pratico_dialog' not in st.session_state:
        st.session_state.show_caso_pratico_dialog = False
    if 'caso_pratico_content' not in st.session_state: # NEW: To store generated content for dialog
        st.session_state.caso_pratico_content = None
    if 'caso_pratico_error' not in st.session_state: # NEW: To store potential errors for dialog
        st.session_state.caso_pratico_error = None
    if 'selected_meta_julgado_id' not in st.session_state:
        st.session_state.selected_meta_julgado_id = None
    if 'informativos_page_number' not in st.session_state: # NEW: For pagination
        st.session_state.informativos_page_number = 0
    if 'informativos_items_per_page' not in st.session_state: # NEW: For pagination items per page
        st.session_state.informativos_items_per_page = 10

    # --- Logo at the very top of the main content area --- 
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        # Use columns to potentially center or control width
        col_logo_left, col_logo_center, col_logo_right = st.columns([1, 2, 1]) # Adjust ratios as needed
        with col_logo_center:
             st.image(logo_path, use_container_width=True) # Changed from use_column_width="auto"
    else:
        st.warning("Arquivo de logo 'logo.png' não encontrado.")
    st.divider() # Add a divider below the logo

    # --- Filtering Logic --- 
    # Start with the original (non-exploded) dataframe for unique julgados
    df_filtrado_unique = df_informativos_original.copy()

    # Apply main filters from sidebar
    if date_filter_type == "Ano" and selected_anos:
        df_filtrado_unique = df_filtrado_unique[df_filtrado_unique['ano_julgamento'].isin(selected_anos)]
    elif date_filter_type == "Mês/Ano" and selected_meses_anos:
        df_filtrado_unique = df_filtrado_unique[df_filtrado_unique['ano_mes_julgamento'].isin(selected_meses_anos)]
    
    # Filter by Ramo Direito (check if any selected ramo is in the list for the row)
    if selected_ramos:
         df_filtrado_unique = df_filtrado_unique[df_filtrado_unique['Ramo Direito'].apply(lambda ramos: any(ramo in selected_ramos for ramo in ramos))]
         
    if selected_classes:
        df_filtrado_unique = df_filtrado_unique[df_filtrado_unique['Classe Processo'].isin(selected_classes)]
    if selected_rg != 'Todos':
        df_filtrado_unique = df_filtrado_unique[df_filtrado_unique['Repercussão Geral'] == selected_rg]
    # Apply read status filter
    if read_status_filter == "Apenas Não Lidos":
        df_filtrado_unique = df_filtrado_unique[~df_filtrado_unique["id"].isin(read_ids)]
    elif read_status_filter == "Apenas Lidos":
        df_filtrado_unique = df_filtrado_unique[df_filtrado_unique["id"].isin(read_ids)]
    # No filtering needed if read_status_filter == "Todos"

    df_filtrado_unique = df_filtrado_unique.sort_values(by="Data Julgamento", ascending=False)

    # --- Search Functionality (Moved to Informativos Tab) --- 
    # search_term = st.text_input("Buscar por palavra-chave no Título ou Matéria", key="search_box", placeholder="Digite aqui para buscar...")
    # if search_term:
    #     search_term_lower = search_term.lower()
    #     # Ensure columns exist before searching
    #     search_cols = [col for col in ['Título', 'Matéria'] if col in df_filtrado_unique.columns]
    #     if search_cols:
    #         # Build filter dynamically
    #         filter_condition = None
    #         for col in search_cols:
    #             condition = df_filtrado_unique[col].str.lower().str.contains(search_term_lower, regex=False, na=False)
    #             if filter_condition is None:
    #                 filter_condition = condition
    #             else:
    #                 filter_condition |= condition
    #         if filter_condition is not None:
    #             df_filtrado_unique = df_filtrado_unique[filter_condition]
    #     else:
    #         st.warning("Colunas 'Título' ou 'Matéria' não encontradas para busca.")

    # --- Tabs --- 
    tab_informativos, tab_assertivas, tab_perguntas, tab_metas = st.tabs(["Informativos", "Assertivas", "Perguntas", "Metas de Leitura"])

    # --- Dialog for Caso Prático (Must be outside tabs) --- 
    if st.session_state.show_caso_pratico_dialog:
        @st.dialog("Caso Prático (RESULT)")
        def show_caso_pratico():
            if st.session_state.caso_pratico_error:
                st.error(st.session_state.caso_pratico_error)
            elif st.session_state.caso_pratico_content:
                st.markdown(st.session_state.caso_pratico_content)
            else:
                # If content/error not ready yet, show spinner (or message)
                st.spinner("Gerando caso prático...") 
                # Ideally, generation is triggered before dialog opens, 
                # but this handles cases where it might still be running.
            
            if st.button("Fechar", key="close_caso_dialog"):
                st.session_state.show_caso_pratico_dialog = False
                st.session_state.selected_julgado_id_caso = None # Clear selection
                st.session_state.caso_pratico_content = None
                st.session_state.caso_pratico_error = None
                st.rerun()
        
        # Call the dialog function to display it
        show_caso_pratico()

    # --- Callback and Rendering Functions --- 
    def select_julgado_for_assertiva(julgado_id):
        st.session_state.selected_julgado_id_assertiva = julgado_id
        st.session_state.selected_julgado_id_caso = None
        st.session_state.selected_julgado_id_pergunta = None # Deselect for other features
        st.session_state.show_caso_pratico_dialog = False
        st.toast(f"Julgado ID {julgado_id} selecionado. Verifique a aba 'Assertivas'.")

    def select_julgado_for_caso(julgado_id):
        st.session_state.selected_julgado_id_caso = julgado_id
        st.session_state.selected_julgado_id_assertiva = None
        st.session_state.selected_julgado_id_pergunta = None
        st.session_state.caso_pratico_content = None # Clear previous content
        st.session_state.caso_pratico_error = None # Clear previous error
        st.session_state.show_caso_pratico_dialog = True # Signal to show dialog
        st.toast(f"Gerando Caso Prático para Julgado ID {julgado_id}...")
        # Trigger generation immediately, result will be shown in dialog
        generate_caso_pratico_content(julgado_id)
        st.rerun() # Rerun to potentially open the dialog if generation was fast

    # NEW Function to generate content for the dialog
    def generate_caso_pratico_content(julgado_id):
        try:
            selected_row_caso = df_informativos_original[df_informativos_original["id"] == julgado_id].iloc[0]
            noticia_completa_caso = selected_row_caso["Notícia Completa"]
            if not noticia_completa_caso:
                st.session_state.caso_pratico_error = "A coluna 'Notícia Completa' está vazia para este julgado."
                return
            if not openai_api_key:
                st.session_state.caso_pratico_error = "Chave da API OpenAI não configurada."
                return

            # Use spinner within the generation logic if desired, though dialog implies waiting
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um assistente que cria exemplos práticos da vida real baseados em notícias de julgados do STF. Descreva uma situação cotidiana, profissional ou hipotética onde o entendimento deste julgado seria aplicado, ilustrando suas consequências práticas. Evite o formato de questão de concurso. Foque em um exemplo claro e contextualizado."},
                    {"role": "user", "content": f"Baseado na seguinte notícia completa do STF, crie um caso prático:\n\n{noticia_completa_caso}"}
                ]
            )
            st.session_state.caso_pratico_content = response.choices[0].message.content
        except Exception as e:
            st.session_state.caso_pratico_error = f"Erro ao gerar caso prático: {e}"
            # Log detailed error if needed
            print(f"Error generating caso pratico: {e}") # Print to console/logs


    # NEW Callback for selecting julgado for questions
    def select_julgado_for_pergunta(julgado_id):
        st.session_state.selected_julgado_id_pergunta = julgado_id
        st.session_state.selected_julgado_id_assertiva = None
        st.session_state.selected_julgado_id_caso = None
        st.session_state.show_caso_pratico_dialog = False
        st.toast(f"Julgado ID {julgado_id} selecionado. Verifique a aba 'Perguntas'.")

    def select_meta_julgado(julgado_id):
        st.session_state.selected_meta_julgado_id = julgado_id
        st.toast(f"Exibindo detalhes do julgado ID {julgado_id} da meta.")

    def toggle_read_status(julgado_id, current_username):
        user_data = load_user_data(current_username)
        read_ids = user_data.get("read_ids", set())
        action_taken = "" # To log the specific action
        if julgado_id in read_ids:
            read_ids.remove(julgado_id)
            action_taken = "mark_unread"
            st.toast(f"Julgado ID {julgado_id} marcado como NÃO LIDO.")
        else:
            read_ids.add(julgado_id)
            action_taken = "mark_read"
            st.toast(f"Julgado ID {julgado_id} marcado como LIDO.")
        user_data["read_ids"] = read_ids
        save_user_data(current_username, user_data)
        log_activity(current_username, action_taken, details=f"julgado_id:{julgado_id}") # Log read/unread action
        st.rerun() # Rerun to update the UI immediately

    def render_card(row, context="informativos", current_username=None, current_read_ids=None):
        date_str = row['Data Julgamento'].strftime('%d/%m/%Y') if pd.notna(row['Data Julgamento']) else 'Data Indisponível'
        card_title_raw = row['Título']
        # Remove potential markdown bold markers from the source
        card_title_clean = re.sub(r'^\*\*|\*\*$', '', str(card_title_raw)).strip()
        card_title = f"**{card_title_clean}** (Inf. {row['Informativo']} - {date_str})" # Apply bold correctly
        
        is_read = row['id'] in current_read_ids if current_read_ids is not None else False
        read_icon = "✅" if is_read else "📖"
        read_button_text = f"{read_icon} {'Lido' if is_read else 'Marcar Lido'}"
        read_button_help = "Marcar como Não Lido" if is_read else "Marcar como Lido"

        key_prefix = f"{context}_{row['id']}"
        expanded_default = (context == 'meta' and row['id'] == st.session_state.get('selected_meta_julgado_id'))

        with st.expander(card_title, expanded=expanded_default):
            if current_username:
                 st.button(read_button_text, key=f"read_{key_prefix}", on_click=toggle_read_status, args=(row['id'], current_username), help=read_button_help)

            st.markdown(f"**Classe:** {row['Classe Processo']}")
            # Display Ramo Direito correctly (handle list from original df)
            ramos_list = row['Ramo Direito'] # Get the list directly from the row
            ramos_str_list = [str(ramo) for ramo in ramos_list if ramo and pd.notna(ramo)]
            st.markdown(f"**Ramo(s) do Direito:** {', '.join(ramos_str_list)}")
            st.markdown(f"**Matéria:** {row['Matéria']}")
            st.markdown(f"**Repercussão Geral:** {row['Repercussão Geral']} {(' (Tema ' + str(row['Tema RG']) + ')') if pd.notna(row['Tema RG']) and row['Tema RG'] else ''}")
            st.markdown("**Tese:**")
            st.markdown(f"> {row['Tese Julgado']}")
            st.markdown("**Resumo:**")
            st.markdown(f"> {row['Resumo']}")
            st.markdown("**Legislação:**")
            st.markdown(f"> {row['Legislação']}")
            st.markdown("**Notícia Completa:**")
            st.markdown(f"> {row['Notícia Completa']}")

            # Buttons for AI features - Renamed text
            col1, col2, col3 = st.columns(3) # Added a third column for the new button
            with col1:
                if row['Resumo']:
                    st.button("Gerar Assertiva (RESULT)", key=f"assertiva_{key_prefix}", on_click=select_julgado_for_assertiva, args=(row['id'],))
                else:
                    st.button("Gerar Assertiva (RESULT)", key=f"assertiva_{key_prefix}", disabled=True, help="Coluna 'Resumo' vazia.")
            with col2:
                if row['Notícia Completa']:
                    st.button("Gerar Caso Prático (RESULT)", key=f"caso_{key_prefix}", on_click=select_julgado_for_caso, args=(row['id'],))
                else:
                    st.button("Gerar Caso Prático (RESULT)", key=f"caso_{key_prefix}", disabled=True, help="Coluna 'Notícia Completa' vazia.")
            # NEW Button for Questions
            with col3:
                if row['Notícia Completa']:
                    st.button("Fazer Pergunta (RESULT)", key=f"pergunta_{key_prefix}", on_click=select_julgado_for_pergunta, args=(row['id'],))
                else:
                    st.button("Fazer Pergunta (RESULT)", key=f"pergunta_{key_prefix}", disabled=True, help="Coluna 'Notícia Completa' vazia.")

    # --- Tab: Informativos --- 
    with tab_informativos:
        st.title("Informativos STF - 2021 a 2025")
        st.caption("Mentoria de Resultado - Prof. Leonardo Aquino")
        st.divider()
        
        # Search bar can go here, below title/caption
        search_term = st.text_input("Buscar por palavra-chave no Título ou Matéria", "", key="search_term_main", placeholder="Digite aqui para buscar...")
        st.divider()

        st.subheader("Julgados Filtrados")

        # Pagination: Items per page selector
        items_per_page_options = [10, 20, 30, 50]
        st.session_state.informativos_items_per_page = st.selectbox(
            "Itens por página:", 
            items_per_page_options, 
            index=items_per_page_options.index(st.session_state.informativos_items_per_page), # Keep current selection
            key="selectbox_items_per_page"
        )

        if df_filtrado_unique.empty:
            st.info("Nenhum julgado encontrado com os filtros aplicados.")
        else:
            st.write(f"{len(df_filtrado_unique)} julgados encontrados.")
            # Apply search term filter here, after main filters
            if search_term:
                df_to_display = df_filtrado_unique[
                    df_filtrado_unique['Título'].str.contains(search_term, case=False, na=False) |
                    df_filtrado_unique['Matéria'].str.contains(search_term, case=False, na=False)
                ]
                st.write(f"{len(df_to_display)} julgados encontrados após busca por '{search_term}'.")
            else:
                df_to_display = df_filtrado_unique

            if df_to_display.empty and search_term:
                 st.info(f"Nenhum julgado encontrado para o termo de busca 	'{search_term}	' nos filtros atuais.")
            elif not df_to_display.empty:
                # --- Pagination Logic ---
                total_items = len(df_to_display)
                items_per_page = st.session_state.informativos_items_per_page
                total_pages = (total_items + items_per_page - 1) // items_per_page
                current_page = st.session_state.informativos_page_number

                # Ensure current page is valid after changing items_per_page or filters
                if current_page >= total_pages:
                    st.session_state.informativos_page_number = max(0, total_pages - 1)
                    current_page = st.session_state.informativos_page_number

                start_idx = current_page * items_per_page
                end_idx = start_idx + items_per_page
                df_paginated = df_to_display.iloc[start_idx:end_idx]

                # Display items for the current page
                for _, row in df_paginated.iterrows():
                    render_card(row, context="informativos", current_username=current_username, current_read_ids=read_ids)
                
                st.divider()
                # --- Pagination Controls ---
                col_prev, col_page_info, col_next = st.columns([1, 2, 1])

                with col_prev:
                    if st.button("⬅️ Anterior", key="prev_page", disabled=(current_page == 0)):
                        st.session_state.informativos_page_number -= 1
                        st.rerun()

                with col_page_info:
                    st.write(f"Página {current_page + 1} de {total_pages}")

                with col_next:
                    if st.button("Próxima ➡️", key="next_page", disabled=(current_page >= total_pages - 1)):
                        st.session_state.informativos_page_number += 1
                        st.rerun()
            # else: # Case where df_to_display is empty but search_term is not set (already handled by outer if)
            #     pass 
       # --- Caso Prático Dialog is now handled outside the tab using st.dialog ---

    # --- Tab: Assertivas --- 
    with tab_assertivas:
        st.subheader("Gerador de Assertivas (Certo/Errado) - RESULT")
        if st.session_state.selected_julgado_id_assertiva:
            # Use original df to get full data for the selected ID
            selected_row_assertiva = df_informativos_original[df_informativos_original['id'] == st.session_state.selected_julgado_id_assertiva].iloc[0]
            resumo_assertiva = selected_row_assertiva['Resumo']
            if resumo_assertiva and openai_api_key:
                st.markdown(f"**Julgado Selecionado (ID: {st.session_state.selected_julgado_id_assertiva}):** {selected_row_assertiva['Título']}")
                st.markdown(f"**Resumo:** {resumo_assertiva}")
                if st.button("Gerar Nova Assertiva (RESULT)", key="btn_gerar_assertiva"):
                    with st.spinner("Gerando assertiva (RESULT)..."):
                        try:
                            response = openai.chat.completions.create(
                                model="gpt-3.5-turbo",
                                messages=[
                                    {"role": "system", "content": "Você é um assistente que cria assertivas (Certo/Errado) baseadas em resumos de julgados do STF. Crie uma única assertiva clara e objetiva. Indique se a assertiva está CERTA ou ERRADA em relação ao julgado, colocando a resposta (CERTO ou ERRADO) entre colchetes no final, assim: [RESPOSTA]."},
                                    {"role": "user", "content": f"Baseado no seguinte resumo do STF, crie uma assertiva (Certo/Errado):\n\n{resumo_assertiva}"}
                                ]
                            )
                            assertiva_gerada_com_resposta = response.choices[0].message.content
                            # Use regex to reliably extract assertiva and answer (more flexible)
                            match = re.search(r"(.*?)\s*\[(CERTO|ERRADO)\]\s*(.*)", assertiva_gerada_com_resposta, re.IGNORECASE | re.DOTALL)
                            if match:
                                # Combine text before and after the answer tag
                                text_before = match.group(1).strip()
                                text_after = match.group(3).strip()
                                st.session_state.assertiva_atual = f"{text_before} {text_after}".strip()
                                st.session_state.resposta_correta_assertiva = match.group(2).upper()
                                st.session_state.feedback_assertiva = None # Clear previous feedback
                            else:
                                # Fallback if format is unexpected or answer tag is missing
                                st.session_state.assertiva_atual = assertiva_gerada_com_resposta # Show the full response
                                st.session_state.resposta_correta_assertiva = "DESCONHECIDA"
                                st.session_state.feedback_assertiva = "Formato de resposta inesperado da IA."
                                st.warning("Não foi possível extrair a resposta (Certo/Errado) da IA.")
                            
                        except Exception as e:
                            st.error(f"Erro ao gerar assertiva: {e}")
                            st.session_state.assertiva_atual = None
                            st.session_state.resposta_correta_assertiva = None
                            st.session_state.feedback_assertiva = None

                if 'assertiva_atual' in st.session_state and st.session_state.assertiva_atual:
                    st.markdown("**Assertiva:**")
                    st.write(st.session_state.assertiva_atual)
                    
                    col_resp1, col_resp2 = st.columns(2)
                    with col_resp1:
                        if st.button("Certo", key="btn_certo"):
                            if st.session_state.resposta_correta_assertiva == "CERTO":
                                st.session_state.feedback_assertiva = "Correto!" 
                                st.success("Correto!")
                            else:
                                st.session_state.feedback_assertiva = f"Errado. A resposta correta é {st.session_state.resposta_correta_assertiva}."
                                st.error(f"Errado. A resposta correta é {st.session_state.resposta_correta_assertiva}.")
                    with col_resp2:
                        if st.button("Errado", key="btn_errado"):
                            if st.session_state.resposta_correta_assertiva == "ERRADO":
                                st.session_state.feedback_assertiva = "Correto!" 
                                st.success("Correto!")
                            else:
                                st.session_state.feedback_assertiva = f"Errado. A resposta correta é {st.session_state.resposta_correta_assertiva}."
                                st.error(f"Errado. A resposta correta é {st.session_state.resposta_correta_assertiva}.")
                                
                    # Display feedback if available
                    # if 'feedback_assertiva' in st.session_state and st.session_state.feedback_assertiva:
                    #     if "Correto!" in st.session_state.feedback_assertiva:
                    #         st.success(st.session_state.feedback_assertiva)
                    #     else:
                    #         st.error(st.session_state.feedback_assertiva)
            elif not openai_api_key:
                 st.warning("Chave da API OpenAI não configurada. Não é possível gerar assertivas.")
            else:
                st.warning("A coluna 'Resumo' está vazia para este julgado. Não é possível gerar assertivas.")
        else:
            st.info("Selecione um julgado na aba 'Informativos' e clique em 'Gerar Assertiva (RESULT)' para começar.")

    # --- Tab: Perguntas --- 
    with tab_perguntas:
        st.subheader("Perguntas sobre Julgados (RESULT)")
        if st.session_state.selected_julgado_id_pergunta:
            # Use original df to get full data for the selected ID
            selected_row_pergunta = df_informativos_original[df_informativos_original['id'] == st.session_state.selected_julgado_id_pergunta].iloc[0]
            noticia_completa_pergunta = selected_row_pergunta['Notícia Completa']
            if noticia_completa_pergunta and openai_api_key:
                st.markdown(f"**Julgado Selecionado (ID: {st.session_state.selected_julgado_id_pergunta}):** {selected_row_pergunta['Título']}")
                st.markdown("**Notícia Completa (Contexto):**")
                with st.expander("Ver/Ocultar Notícia Completa"):
                    st.markdown(f"> {noticia_completa_pergunta}")
                
                user_question = st.text_input("Faça sua pergunta sobre este julgado:", key="user_question_input")
                if st.button("Enviar Pergunta (RESULT)", key="btn_send_question") and user_question:
                    with st.spinner("Buscando resposta (RESULT)..."):
                        try:
                            response = openai.chat.completions.create(
                                model="gpt-3.5-turbo", # Or potentially gpt-4 if context is very long
                                messages=[
                                    {"role": "system", "content": "Você é um assistente especialista em responder perguntas sobre julgados específicos do STF, baseado exclusivamente na notícia completa fornecida. Responda de forma objetiva e direta à pergunta do usuário, utilizando apenas as informações contidas no texto do julgado."},
                                    {"role": "user", "content": f"Contexto do Julgado:\n{noticia_completa_pergunta}\n\nPergunta do Usuário:\n{user_question}"}
                                ]
                            )
                            answer = response.choices[0].message.content
                            st.markdown("**Resposta (RESULT):**")
                            st.markdown(answer)
                        except Exception as e:
                            st.error(f"Erro ao processar a pergunta: {e}")
            elif not openai_api_key:
                 st.warning("Chave da API OpenAI não configurada. Não é possível fazer perguntas.")
            else:
                st.warning("A coluna 'Notícia Completa' está vazia para este julgado. Não é possível fazer perguntas.")
        else:
            st.info("Selecione um julgado na aba 'Informativos' e clique em 'Fazer Pergunta (RESULT)' para começar.")

    # --- Tab: Metas de Leitura --- 
    with tab_metas:
        st.subheader("Metas de Leitura")
        st.write("Defina quantos julgados não lidos você quer incluir na sua meta de leitura hoje.")
        
        # Get unread items based on current filters (excluding read status filter itself)
        df_filtrado_para_meta = df_informativos_original.copy()
        if date_filter_type == "Ano" and selected_anos:
            df_filtrado_para_meta = df_filtrado_para_meta[df_filtrado_para_meta['ano_julgamento'].isin(selected_anos)]
        elif date_filter_type == "Mês/Ano" and selected_meses_anos:
            df_filtrado_para_meta = df_filtrado_para_meta[df_filtrado_para_meta['ano_mes_julgamento'].isin(selected_meses_anos)]
        if selected_ramos:
             df_filtrado_para_meta = df_filtrado_para_meta[df_filtrado_para_meta['Ramo Direito'].apply(lambda ramos: any(ramo in selected_ramos for ramo in ramos))]
        if selected_classes:
            df_filtrado_para_meta = df_filtrado_para_meta[df_filtrado_para_meta['Classe Processo'].isin(selected_classes)]
        if selected_rg != 'Todos':
            df_filtrado_para_meta = df_filtrado_para_meta[df_filtrado_para_meta['Repercussão Geral'] == selected_rg]
        
        # Filter for unread items
        df_nao_lidos_filtrados = df_filtrado_para_meta[~df_filtrado_para_meta["id"].isin(read_ids)]
        
        num_nao_lidos = len(df_nao_lidos_filtrados)
        st.write(f"Você tem {num_nao_lidos} julgados não lidos com os filtros atuais.")
        
        if num_nao_lidos > 0:
            num_meta = st.number_input("Número de julgados para a meta:", min_value=1, max_value=num_nao_lidos, value=min(5, num_nao_lidos), step=1, key="num_meta")
            
            if st.button("Gerar Meta de Leitura", key="btn_gerar_meta"):
                if num_meta > num_nao_lidos:
                    st.warning(f"Você solicitou {num_meta} julgados, mas só há {num_nao_lidos} não lidos com os filtros atuais. Ajustando a meta para {num_nao_lidos}.")
                    num_meta = num_nao_lidos
                
                # Select random items
                st.session_state.meta_atual = df_nao_lidos_filtrados.sample(n=num_meta).sort_values(by="Data Julgamento", ascending=False)
                st.session_state.selected_meta_julgado_id = None # Reset detailed view
                log_activity(current_username, "generate_reading_goal", details=f"count:{num_meta}") # Log goal generation
                st.success(f"Meta de {num_meta} julgados gerada!")
        else:
            st.info("Não há julgados não lidos com os filtros atuais para gerar uma meta.")

        # Display current goal if exists
        if 'meta_atual' in st.session_state and not st.session_state.meta_atual.empty:
            st.divider()
            st.subheader("Sua Meta Atual")
            meta_df = st.session_state.meta_atual
            
            # Display details if a specific julgado is selected
            if st.session_state.selected_meta_julgado_id:
                selected_row_meta = meta_df[meta_df['id'] == st.session_state.selected_meta_julgado_id]
                if not selected_row_meta.empty:
                    st.markdown("--- DETALHES DO JULGADO SELECIONADO ---")
                    render_card(selected_row_meta.iloc[0], context="meta_detail", current_username=current_username, current_read_ids=read_ids)
                    if st.button("Voltar para a lista da meta", key="back_to_meta_list"):
                        st.session_state.selected_meta_julgado_id = None
                        st.rerun()
                    st.markdown("--- FIM DOS DETALHES ---")
                else:
                    st.warning("Julgado selecionado não encontrado na meta atual.")
                    st.session_state.selected_meta_julgado_id = None # Reset if not found
            
            # Display list of items in the goal (only if not viewing details)
            if not st.session_state.selected_meta_julgado_id:
                for _, row in meta_df.iterrows():
                    date_str_meta = row['Data Julgamento'].strftime('%d/%m/%Y') if pd.notna(row['Data Julgamento']) else 'Data Indisponível'
                    card_title_meta_raw = row['Título']
                    card_title_meta_clean = re.sub(r'^\*\*|\*\*$', '', str(card_title_meta_raw)).strip()
                    card_title_meta = f"**{card_title_meta_clean}** (Inf. {row['Informativo']} - {date_str_meta})"
                    
                    is_read_meta = row['id'] in read_ids
                    read_icon_meta = "✅" if is_read_meta else "📖"
                    
                    # Use columns for layout: Title + Button
                    col_title, col_button = st.columns([4, 1])
                    with col_title:
                        st.markdown(f"{read_icon_meta} {card_title_meta}")
                    with col_button:
                        if st.button("Ver Detalhes", key=f"detail_meta_{row['id']}", help="Clique para ver os detalhes e marcar como lido"):
                            select_meta_julgado(row['id'])
                            st.rerun()
                    st.divider()

else:
    st.error("Falha ao carregar os dados dos informativos. A aplicação não pode continuar.")
