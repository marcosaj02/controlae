import streamlit as st
import pandas as pd
from datetime import date, timedelta
from modules.database import *
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random

# --- FUNÇÃO DE ENVIO DE E-MAIL ---
def enviar_email(destinatario, assunto, corpo):
    try:
        remetente = st.secrets["EMAIL_USER_CONTROLAE"]
        senha = st.secrets["EMAIL_PASS_CONTROLAE"]
        
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

# --- FUNÇÃO AUXILIAR PARA FORMATAR MOEDA NO PADRÃO BRASILEIRO ---
def formatar_moeda(valor):
    return f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# --- 1. CONFIGURAÇÃO INICIAL (Deve ser a primeira linha) ---
st.set_page_config(page_title="Gestor Financeiro Pro", layout="wide", page_icon="💳")
inicializar_db()

# --- 2. CONFIGURAÇÃO DE TEMAS (CSS MODERNO) ---
def carregar_tema():
    tema_escolhido = st.sidebar.selectbox(
        "🎨 Escolha o Tema", 
        ["Dark Premium", "Fintech Clean"]
    )

    if tema_escolhido == "Dark Premium":
        cor_fundo = "#0E1117"
        cor_texto = "#FAFAFA"
        cor_input = "#262730"
        cor_accent = "#8B5CF6" # Roxo moderno para combinar com a tela
        cor_borda = "rgba(255,255,255,0.1)"
    else:
        cor_fundo = "#F0F2F6"
        cor_texto = "#111827"
        cor_input = "#FFFFFF"
        cor_accent = "#007BFF" # Azul clássico para versão light
        cor_borda = "rgba(0,0,0,0.1)"

    css = f"""
    <style>
    /* Fundos e Textos Base */
    .stApp {{ background-color: {cor_fundo}; color: {cor_texto}; }}
    [data-testid="stSidebar"] {{ background-color: {cor_input}; }}
    p, h1, h2, h3, label {{ color: {cor_texto} !important; }}

    /* --- INPUTS MODERNOS --- */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, 
    .stSelectbox>div>div>div, .stDateInput>div>div>input {{
        border-radius: 8px;
        border: 1px solid {cor_borda};
        background-color: {cor_input};
        color: {cor_texto};
        transition: all 0.2s ease-in-out;
    }}
    
    /* Efeito ao clicar no Input */
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus, 
    .stSelectbox>div>div>div:focus, .stDateInput>div>div>input:focus {{
        border-color: {cor_accent};
        box-shadow: 0 0 0 2px {cor_accent}33;
    }}

    /* --- BOTÕES MODERNOS --- */
    .stButton>button, .stFormSubmitButton>button {{
        border-radius: 8px;
        background-color: {cor_accent};
        color: #FFFFFF !important;
        border: none;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }}
    
    /* Efeito Hover do Botão */
    .stButton>button:hover, .stFormSubmitButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 12px {cor_accent}40;
        filter: brightness(1.1);
        color: #FFFFFF !important;
    }}

    /* --- FORMULÁRIOS E CONTAINERS --- */
    [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 12px;
        border: 1px solid {cor_borda};
        background-color: transparent;
        padding: 1rem;
    }}
    
    /* Estilização das Abas (Tabs) */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 24px;
    }}
    .stTabs [data-baseweb="tab"] {{
        padding-top: 10px;
        padding-bottom: 10px;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

carregar_tema()

# --- 3. INICIALIZAÇÃO DA SESSÃO ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.session_state['user_nome'] = None

# Novas variáveis para controlar a validação de e-mail no cadastro
if 'verificacao_pendente' not in st.session_state:
    st.session_state['verificacao_pendente'] = False
if 'codigo_gerado' not in st.session_state:
    st.session_state['codigo_gerado'] = None
if 'dados_novo_user' not in st.session_state:
    st.session_state['dados_novo_user'] = None

# --- 4. TELA DE LOGIN ---
def tela_login():
    # Deixa o formulário centralizado com mais espaço nas laterais para ficar elegante
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    with col2:
        st.write("") # Respiro superior
        st.write("")
        st.markdown(f"<h1 style='text-align: center;'>💰 Controlaê</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size: 1.2rem; opacity: 0.8;'>Gestão de gastos pessoais</p>", unsafe_allow_html=True)
        st.write("")
        
        tab1, tab2, tab3 = st.tabs(["Login", "Criar Conta", "Esqueci a Senha"])
        
        with tab1:
            with st.form("login_form"):
                usuario = st.text_input("Usuário ou E-mail", placeholder="Ex: email@email.com")
                senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
                
                st.write("") # Espaço antes do botão
                # O parâmetro use_container_width faz o botão ocupar toda a largura, padrão em telas de login modernas
                submit_login = st.form_submit_button("Entrar", type="primary", use_container_width=True)
                
                if submit_login:
                    user_data = verificar_login(usuario, senha)
                    if user_data:
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = user_data[0]
                        st.session_state['user_nome'] = user_data[1]
                        st.rerun()
                    else:
                        st.error("❌ Usuário/E-mail ou senha incorretos.")
        
        with tab2:
            st.write("Crie sua conta para começar.")
            
            # ETAPA 1: Pede os dados e envia o e-mail
            if not st.session_state['verificacao_pendente']:
                with st.form("cadastro_form", clear_on_submit=False):
                    novo_user = st.text_input("Usuário (Login)")
                    novo_email = st.text_input("E-mail (Para validação)")
                    
                    c_s1, c_s2 = st.columns(2)
                    nova_senha = c_s1.text_input("Senha", type="password")
                    confirma_senha = c_s2.text_input("Repita a Senha", type="password")
                    
                    novo_nome = st.text_input("Seu Nome")
                    submit_cadastro = st.form_submit_button("Receber Código de Validação", use_container_width=True)
                    
                    if submit_cadastro:
                        if not novo_user or not novo_email or not nova_senha:
                            st.warning("⚠️ Preencha todos os campos obrigatórios.")
                        elif nova_senha != confirma_senha:
                            st.error("❌ As senhas não coincidem!")
                        else:
                            # Gera um código de 6 dígitos aleatório
                            codigo = str(random.randint(100000, 999999))
                            corpo_html = f"""
                            <div style="font-family: sans-serif; padding: 20px;">
                                <h3>Olá, {novo_nome}!</h3>
                                <p>Bem-vindo ao <b>Controlaê</b>. Para finalizar a criação da sua conta, use o código de validação abaixo:</p>
                                <h2 style='color: #8B5CF6; letter-spacing: 5px; background: #f4f4f5; padding: 10px; border-radius: 8px; display: inline-block;'>{codigo}</h2>
                                <p>Insira este código na tela de cadastro para liberar seu acesso.</p>
                            </div>
                            """
                            
                            with st.spinner("Enviando código para seu e-mail..."):
                                if enviar_email(novo_email, "Código de Validação - Controlaê", corpo_html):
                                    # Salva os dados na sessão temporariamente para usar na etapa 2
                                    st.session_state['codigo_gerado'] = codigo
                                    st.session_state['dados_novo_user'] = {
                                        'user': novo_user, 'email': novo_email, 
                                        'senha': nova_senha, 'nome': novo_nome
                                    }
                                    st.session_state['verificacao_pendente'] = True
                                    st.rerun()

            # ETAPA 2: Aguarda o usuário digitar o código recebido
            else:
                st.info(f"📧 Enviamos um código de 6 dígitos para **{st.session_state['dados_novo_user']['email']}**.")
                
                with st.form("validacao_form"):
                    codigo_digitado = st.text_input("Digite o código recebido", max_chars=6)
                    
                    col_v1, col_v2 = st.columns(2)
                    submit_validacao = col_v1.form_submit_button("Confirmar Cadastro", type="primary", use_container_width=True)
                    cancelar_validacao = col_v2.form_submit_button("Voltar/Cancelar", use_container_width=True)
                    
                    if submit_validacao:
                        if codigo_digitado == st.session_state['codigo_gerado']:
                            # Código correto! Agora sim salvamos no banco de dados
                            dados = st.session_state['dados_novo_user']
                            resultado = criar_usuario(dados['user'], dados['email'], dados['senha'], dados['nome'])
                            
                            if resultado == "Sucesso":
                                st.success("✅ Conta criada com sucesso! Pode fazer o Login.")
                                # Limpa a sessão para não travar a tela
                                st.session_state['verificacao_pendente'] = False
                                st.session_state['codigo_gerado'] = None
                                st.session_state['dados_novo_user'] = None
                            else:
                                st.error(f"❌ Erro no banco: {resultado}")
                        else:
                            st.error("❌ Código incorreto. Verifique o e-mail e tente novamente.")
                            
                    if cancelar_validacao:
                        # Desiste do cadastro e volta para o formulário inicial limpo
                        st.session_state['verificacao_pendente'] = False
                        st.session_state['codigo_gerado'] = None
                        st.session_state['dados_novo_user'] = None
                        st.rerun()                        
        with tab3:
            st.write("Informe seu e-mail para recuperar o acesso.")
            with st.form("recupera_form"):
                email_rec = st.text_input("Seu E-mail cadastrado")
                submit_rec = st.form_submit_button("Recuperar Acesso", use_container_width=True)
                
                if submit_rec:
                    existe, username_rec = recuperar_senha(email_rec)
                    if existe:
                        corpo_html = f"""
                        <div style="font-family: sans-serif; padding: 20px;">
                            <h3>Olá!</h3>
                            <p>Você solicitou a recuperação de acesso do seu <b>Controlaê</b>.</p>
                            <p>Seu nome de usuário para fazer o login é: <b style='color: #8B5CF6; font-size: 1.2rem;'>{username_rec}</b></p>
                            <p><i>(Como o sistema é de uso pessoal e seguro, caso tenha esquecido a senha, precisaremos redefini-la diretamente no banco de dados).</i></p>
                        </div>
                        """
                        with st.spinner("Enviando e-mail..."):
                            if enviar_email(email_rec, "Recuperação de Acesso - Controlaê", corpo_html):
                                st.success(f"✅ E-mail enviado com sucesso para: {email_rec}")
                    else:
                        st.error("❌ E-mail não encontrado no sistema.")

# --- 5. APLICAÇÃO PRINCIPAL (SÓ RODA SE LOGADO) ---
def main_app():
    USER_ID = st.session_state['user_id']
    processar_recorrencias(USER_ID)

    with st.sidebar:
        st.write(f"Olá, **{st.session_state['user_nome']}** 👋")
        st.divider()
        menu = st.radio("Menu", ["Dashboard", "Lançamentos", "Investimentos", "Configurar Recorrências"])
        st.divider()
        if st.button("Sair", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- OPÇÃO 1: DASHBOARD ---
    if menu == "Dashboard":
        col_titulo, col_invest = st.columns([2, 1])
        
        with col_titulo:
            st.title("📊 Visão Geral")
            
        df = ler_transacoes(USER_ID)
        
        if not df.empty:
            df['data'] = pd.to_datetime(df['data'])
            mes_atual = date.today().strftime("%Y-%m")
            df_mes = df[df['data'].dt.strftime('%Y-%m') == mes_atual]
            
            df_realizado = df[df['status'] == 'Pago']
            
            rec_total = df_realizado[df_realizado['tipo'] == 'Receita']['valor'].sum()
            desp_total = df_realizado[df_realizado['tipo'] == 'Despesa']['valor'].sum()
            inv_total = df_realizado[df_realizado['tipo'] == 'Investimento']['valor'].sum()
            
            saldo_conta = rec_total - desp_total

            rec_real = df_mes[(df_mes['tipo'] == 'Receita') & (df_mes['status'] == 'Pago')]['valor'].sum()
            rec_prev = df_mes[(df_mes['tipo'] == 'Receita') & (df_mes['status'] == 'Pendente')]['valor'].sum()

            desp_real = df_mes[(df_mes['tipo'] == 'Despesa') & (df_mes['status'] == 'Pago')]['valor'].sum()
            desp_prev = df_mes[(df_mes['tipo'] == 'Despesa') & (df_mes['status'] == 'Pendente')]['valor'].sum()
            
            inv_real = df_mes[(df_mes['tipo'] == 'Investimento') & (df_mes['status'] == 'Pago')]['valor'].sum()

            with col_invest:
                st.write("") 
                st.metric("Total Reservado 📈", f"R$ {formatar_moeda(inv_total)}", f"+ R$ {formatar_moeda(inv_real)} no mês" if inv_real > 0 else None, delta_color="normal")

            st.divider()

            c1, c2, c3 = st.columns(3)
            with st.container(border=True):
                c1.metric("Saldo Real em Conta", f"R$ {formatar_moeda(saldo_conta)}")
            with st.container(border=True):
                c2.metric("Receitas (Mês)", f"R$ {formatar_moeda(rec_real)}", f"+ R$ {formatar_moeda(rec_prev)} pendente" if rec_prev > 0 else None, delta_color="normal")
            with st.container(border=True):
                c3.metric("Despesas (Mês)", f"R$ {formatar_moeda(desp_real)}", f"- R$ {formatar_moeda(desp_prev)} pendente" if desp_prev > 0 else None, delta_color="inverse")
            
            st.divider()

            col_esq, col_dir = st.columns([1, 1])

            with col_esq:
                st.subheader("⚠️ Alertas de Vencimento")
                hoje = pd.to_datetime(date.today())
                contas_vencendo = df_mes[
                    (df_mes['status'] == 'Pendente') & 
                    (df_mes['tipo'] == 'Despesa') & 
                    (df_mes['data'] <= hoje + timedelta(days=3))
                ]
                if not contas_vencendo.empty:
                    st.error(f"🚨 {len(contas_vencendo)} contas vencendo nos próximos 3 dias!")
                    for _, row in contas_vencendo.iterrows():
                        st.write(f"📅 {row['data'].strftime('%d/%m')} - {row['nome']} (R$ {formatar_moeda(row['valor'])})")
                else:
                    st.success("✅ Nenhuma despesa próxima do vencimento!")

            with col_dir:
                st.subheader("⏳ Confirmar Transação")
                df_pendentes_total = df[(df['status'] == 'Pendente') & (df['tipo'] != 'Investimento')].sort_values('data')
                
                if not df_pendentes_total.empty:
                    with st.container(border=True):
                        opcoes = {f"{row['data'].strftime('%d/%m')} - {row['nome']} (R$ {formatar_moeda(row['valor'])})": row['id'] for _, row in df_pendentes_total.iterrows()}
                        conta_selecionada = st.selectbox("Selecione o lançamento pendente:", list(opcoes.keys()))
                        
                        id_selecionado = opcoes[conta_selecionada]
                        data_vencimento_original = df_pendentes_total[df_pendentes_total['id'] == id_selecionado].iloc[0]['data'].date()
                        
                        data_pagamento = st.date_input("Data Real (quando o dinheiro entrou/saiu):", value=data_vencimento_original, format="DD/MM/YYYY")
                        
                        if st.button("✅ Confirmar como Pago/Recebido", type="primary", use_container_width=True):
                            confirmar_transacao(id_selecionado, data_pagamento)
                            st.rerun()
                else:
                    st.info("🎉 Você não tem nenhum lançamento de despesa/receita pendente!")

            st.divider()
            st.subheader("Extrato do Mês")
            
            df_exibicao = df_mes[df_mes['tipo'] != 'Investimento'].copy()
            
            if not df_exibicao.empty:
                df_exibicao['origem'] = df_exibicao['origem_recorrencia_id'].apply(
                    lambda x: "Lançamento Avulso" if pd.isna(x) else "Conta Fixa"
                )
                df_exibicao['data'] = df_exibicao['data'].dt.strftime('%d/%m/%Y')
                df_exibicao = df_exibicao.drop(columns=['id', 'origem_recorrencia_id', 'user_id'])
                df_exibicao = df_exibicao.rename(columns={
                    'data': 'Data', 'nome': 'Descrição', 'valor': 'Valor (R$)',
                    'categoria': 'Categoria', 'tipo': 'Tipo', 'status': 'Status', 'origem': 'Origem'
                })
                
                df_exibicao['Valor (R$)'] = df_exibicao['Valor (R$)'].apply(lambda x: formatar_moeda(x))
                
                st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
            else:
                st.write("Nenhuma movimentação de receita ou despesa neste mês.")
            
        else:
            st.info("Bem-vindo! Comece lançando seus gastos ou investimentos.")

    # --- OPÇÃO 2: LANÇAMENTOS E GESTÃO DE HISTÓRICO ---
    elif menu == "Lançamentos":
        st.title("💸 Gestão de Lançamentos")
        
        tab1, tab2 = st.tabs(["➕ Novo Lançamento", "✏️ Editar / Excluir Histórico"])
        
        with tab1:
            with st.container(border=True):
                with st.form("form_gasto", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    data_lanc = col1.date_input("Data", date.today(), format="DD/MM/YYYY")
                    nome_lanc = col2.text_input("Descrição", placeholder="Ex: Mercado, Combustível, Salário...")
                    
                    col3, col4, col5, col6 = st.columns(4)
                    valor_lanc = col3.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
                    cat_lanc = col4.selectbox("Categoria", ["Alimentação", "Transporte", "Moradia", "Saúde", "Lazer", "Impostos", "Receita", "Outros"])
                    tipo_lanc = col5.selectbox("Tipo", ["Despesa", "Receita"])
                    
                    status_ui = col6.selectbox("Status", ["Já Pago/Recebido", "Pendente (Agendar)"])
                    
                    submitted = st.form_submit_button("Salvar Lançamento", type="primary", use_container_width=True)
                    
                    if submitted:
                        status_db = "Pago" if status_ui == "Já Pago/Recebido" else "Pendente"
                        adicionar_transacao(USER_ID, data_lanc, nome_lanc, valor_lanc, cat_lanc, tipo_lanc, status_db)
                        st.success(f"✅ Lançamento salvo: {nome_lanc} - R$ {formatar_moeda(valor_lanc)}")
                        st.rerun()

        with tab2:
            st.info("💡 **Dica:** Edite os valores ou marque a caixinha **❌ Excluir?** para apagar um lançamento.")
            df_transacoes = ler_transacoes(USER_ID)
            
            if not df_transacoes.empty:
                df_filtrado = df_transacoes[df_transacoes['tipo'] != 'Investimento'].copy()
                
                if not df_filtrado.empty:
                    df_filtrado['data'] = pd.to_datetime(df_filtrado['data']).dt.date
                    df_filtrado['Excluir'] = False
                    
                    edited_transacoes = st.data_editor(
                        df_filtrado,
                        num_rows="fixed", 
                        use_container_width=True,
                        hide_index=True, 
                        column_order=["Excluir", "data", "nome", "valor", "categoria", "tipo", "status"],
                        column_config={
                            "Excluir": st.column_config.CheckboxColumn("❌ Excluir?", default=False),
                            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", required=True),
                            "nome": st.column_config.TextColumn("Descrição", required=True),
                            "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", min_value=0.0, required=True),
                            "categoria": st.column_config.SelectboxColumn("Categoria", options=["Alimentação", "Transporte", "Moradia", "Saúde", "Lazer", "Impostos", "Receita", "Outros"], required=True),
                            "tipo": st.column_config.SelectboxColumn("Tipo", options=["Despesa", "Receita"], required=True),
                            "status": st.column_config.SelectboxColumn("Status", options=["Pago", "Pendente"], required=True)
                        }
                    )
                    
                    if st.button("💾 Salvar Alterações no Histórico", type="primary"):
                        try:
                            transacoes_para_salvar = edited_transacoes[edited_transacoes['Excluir'] == False]
                            atualizar_transacoes(USER_ID, transacoes_para_salvar)
                            st.success("✅ Histórico atualizado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                else:
                    st.write("Nenhum lançamento comum encontrado no histórico.")
            else:
                st.write("Nenhum lançamento encontrado.")

    # --- OPÇÃO NOVO: INVESTIMENTOS ---
    elif menu == "Investimentos":
        st.title("📈 Meus Investimentos & Reservas")
        
        tab1, tab2 = st.tabs(["➕ Novo Aporte (Guardar Dinheiro)", "✏️ Gerenciar Carteira"])
        
        with tab1:
            st.info("💡 **Informativo:** O valor guardado aqui constará no painel 'Total Reservado' do Dashboard, separado das suas contas do dia a dia.")
            with st.container(border=True):
                with st.form("form_investimento", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    data_inv = col1.date_input("Data do Aporte", date.today(), format="DD/MM/YYYY")
                    nome_inv = col2.text_input("Descrição", placeholder="Ex: CDB Nubank, Tesouro Selic, Caixinha...")
                    
                    col3, col4, col5 = st.columns([2, 2, 2])
                    valor_inv = col3.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
                    cat_inv = col4.selectbox("Tipo de Investimento", ["Reserva de Emergência", "Poupança", "Renda Fixa (CDB, Tesouro)", "Ações / FIIs", "Criptomoedas", "Outros"])
                    status_inv = col5.selectbox("Status", ["Dinheiro já guardado (Pago)", "Apenas Agendado (Pendente)"])
                    
                    submitted = st.form_submit_button("Salvar Aporte", type="primary", use_container_width=True)
                    
                    if submitted:
                        status_db = "Pago" if status_inv == "Dinheiro já guardado (Pago)" else "Pendente"
                        adicionar_transacao(USER_ID, data_inv, nome_inv, valor_inv, cat_inv, "Investimento", status_db)
                        st.success(f"✅ Investimento salvo: {nome_inv} - R$ {formatar_moeda(valor_inv)}")
                        st.rerun()

        with tab2:
            st.write("Histórico completo dos seus investimentos:")
            df_transacoes = ler_transacoes(USER_ID)
            
            if not df_transacoes.empty:
                df_investimentos = df_transacoes[df_transacoes['tipo'] == 'Investimento'].copy()
                
                if not df_investimentos.empty:
                    df_investimentos['data'] = pd.to_datetime(df_investimentos['data']).dt.date
                    df_investimentos['Excluir'] = False
                    
                    edited_investimentos = st.data_editor(
                        df_investimentos,
                        num_rows="fixed", 
                        use_container_width=True,
                        hide_index=True, 
                        column_order=["Excluir", "data", "nome", "valor", "categoria", "status"], 
                        column_config={
                            "Excluir": st.column_config.CheckboxColumn("❌ Resgatar/Excluir?", default=False),
                            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", required=True),
                            "nome": st.column_config.TextColumn("Descrição", required=True),
                            "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", min_value=0.0, required=True),
                            "categoria": st.column_config.SelectboxColumn("Tipo de Investimento", options=["Reserva de Emergência", "Poupança", "Renda Fixa (CDB, Tesouro)", "Ações / FIIs", "Criptomoedas", "Outros"], required=True),
                            "status": st.column_config.SelectboxColumn("Status", options=["Pago", "Pendente"], required=True)
                        }
                    )
                    
                    if st.button("💾 Atualizar Carteira de Investimentos", type="primary"):
                        try:
                            edited_investimentos['tipo'] = 'Investimento'
                            transacoes_para_salvar = edited_investimentos[edited_investimentos['Excluir'] == False]
                            atualizar_transacoes(USER_ID, transacoes_para_salvar)
                            st.success("✅ Carteira atualizada!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                else:
                    st.write("Nenhum investimento registrado ainda.")
            else:
                st.write("Nenhum lançamento encontrado.")

    # --- OPÇÃO 3: RECORRÊNCIAS (Tabela Editável) ---
    elif menu == "Configurar Recorrências":
        st.title("⚙️ Contas Fixas & Assinaturas")
        st.info("Configure aqui o que se repete todo mês (Ex: Aluguel, Salário, Netflix).")
        
        df_rec = ler_recorrencias(USER_ID)
        if not df_rec.empty and "ativo" in df_rec.columns:
            df_rec["ativo"] = df_rec["ativo"].apply(lambda x: True if x == 1 else False)

        edited_df = st.data_editor(
            df_rec, num_rows="dynamic", use_container_width=True,
            column_order=["nome", "valor", "dia_vencimento", "categoria", "tipo", "data_limite", "ativo"],
            column_config={
                "nome": st.column_config.TextColumn("Descrição", required=True, default=""),
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", min_value=0.0, default=0.0),
                "dia_vencimento": st.column_config.NumberColumn("Dia Venc.", min_value=1, max_value=31, step=1, format="%d"),
                "categoria": st.column_config.SelectboxColumn("Categoria", options=["Alimentação", "Transporte", "Moradia", "Saúde", "Lazer", "Impostos", "Receita", "Outros"], required=True),
                "tipo": st.column_config.SelectboxColumn("Tipo", options=["Despesa", "Receita"], required=True),
                "data_limite": st.column_config.DateColumn("Válido Até (Opcional)"),
                "ativo": st.column_config.CheckboxColumn("Ativo?", default=True)
            }
        )

        if st.button("💾 Salvar Alterações", type="primary"):
            try:
                atualizar_recorrencias(USER_ID, edited_df)
                st.success("✅ Configurações salvas com sucesso!")
                processar_recorrencias(USER_ID)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

if not st.session_state['logged_in']:
    tela_login()
else:
    main_app()