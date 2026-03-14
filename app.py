import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from modules.database import *
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random

# --- 1. FUNÇÃO DE ENVIO DE E-MAIL ---
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

# --- 2. FUNÇÃO AUXILIAR PARA FORMATAR MOEDA ---
def formatar_moeda(valor):
    return f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# --- 3. CONFIGURAÇÃO DA PÁGINA E BANCO ---
st.set_page_config(page_title="Gestor Financeiro Pro", layout="wide", page_icon="💳")
inicializar_db()

# --- 4. CONFIGURAÇÃO DE TEMAS (CSS MODERNO) ---
def carregar_tema():
    tema_escolhido = st.sidebar.selectbox(
        "🎨 Escolha o Tema", 
        ["Dark Premium", "Fintech Clean"]
    )

    if tema_escolhido == "Dark Premium":
        cor_fundo = "#0E1117"
        cor_texto = "#FAFAFA"
        cor_input = "#262730"
        cor_accent = "#8B5CF6" 
        cor_borda = "rgba(255,255,255,0.1)"
    else:
        cor_fundo = "#F0F2F6"
        cor_texto = "#111827"
        cor_input = "#FFFFFF"
        cor_accent = "#007BFF" 
        cor_borda = "rgba(0,0,0,0.1)"

    css = f"""
    <style>
    /* Remover atrasos e animações de transição para deixar mais rápido */
    .stApp, .main, [data-testid="stAppViewBlockContainer"], .block-container {{
        animation: none !important;
        transition: none !important;
    }}

    .stApp {{ background-color: {cor_fundo}; color: {cor_texto}; }}
    [data-testid="stSidebar"] {{ background-color: {cor_input}; }}
    p, h1, h2, h3, label {{ color: {cor_texto} !important; }}

    .stTextInput>div>div>input, .stNumberInput>div>div>input, 
    .stSelectbox>div>div>div, .stDateInput>div>div>input {{
        border-radius: 8px;
        border: 1px solid {cor_borda};
        background-color: {cor_input};
        color: {cor_texto};
    }}
    
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus, 
    .stSelectbox>div>div>div:focus, .stDateInput>div>div>input:focus {{
        border-color: {cor_accent};
        box-shadow: 0 0 0 2px {cor_accent}33;
    }}

    .stButton>button, .stFormSubmitButton>button {{
        border-radius: 8px;
        background-color: {cor_accent};
        color: #FFFFFF !important;
        border: none;
        font-weight: 600;
        padding: 0.5rem 1rem;
    }}
    
    .stButton>button:hover, .stFormSubmitButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 12px {cor_accent}40;
        filter: brightness(1.1);
        color: #FFFFFF !important;
    }}

    [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 12px;
        border: 1px solid {cor_borda};
        background-color: transparent;
        padding: 1rem;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

carregar_tema()

# --- 5. INICIALIZAÇÃO DA SESSÃO E VARIÁVEIS GLOBAIS ---
if 'logged_in' not in st.session_state:
    st.session_state.update({
        'logged_in': False, 'user_id': None, 'user_nome': None,
        'verificacao_pendente': False, 'codigo_gerado': None, 'dados_novo_user': None
    })

# Lista de categorias dinâmica na sessão
if 'categorias' not in st.session_state:
    st.session_state['categorias'] = ["Alimentação", "Transporte", "Moradia", "Saúde", "Lazer", "Impostos", "Receita", "Outros"]

# --- 6. TELA DE LOGIN & CADASTRO ---
def tela_login():
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    with col2:
        st.write("")
        st.markdown("<h1 style='text-align: center;'>💰 Controlaê</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 1.2rem; opacity: 0.8;'>Gestão de gastos pessoais</p>", unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["Login", "Criar Conta", "Esqueci a Senha"])
        
        with tab1:
            with st.form("login_form"):
                usuario = st.text_input("Usuário ou E-mail", placeholder="Ex: email@email.com")
                senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
                submit_login = st.form_submit_button("Entrar", type="primary", use_container_width=True)
                
                if submit_login:
                    user_data = verificar_login(usuario, senha)
                    if user_data:
                        st.session_state.update({'logged_in': True, 'user_id': user_data[0], 'user_nome': user_data[1]})
                        st.rerun()
                    else:
                        st.error("❌ Usuário/E-mail ou senha incorretos.")
        
        with tab2:
            if not st.session_state['verificacao_pendente']:
                with st.form("cadastro_form"):
                    novo_user = st.text_input("Usuário (Login)")
                    novo_email = st.text_input("E-mail (Para validação)")
                    c_s1, c_s2 = st.columns(2)
                    nova_senha = c_s1.text_input("Senha", type="password")
                    confirma_senha = c_s2.text_input("Repita a Senha", type="password")
                    novo_nome = st.text_input("Seu Nome")
                    submit_cadastro = st.form_submit_button("Receber Código de Validação", use_container_width=True)
                    
                    if submit_cadastro:
                        if not novo_user or not novo_email or not nova_senha:
                            st.warning("⚠️ Preencha todos os campos.")
                        elif nova_senha != confirma_senha:
                            st.error("❌ As senhas não coincidem!")
                        else:
                            codigo = str(random.randint(100000, 999999))
                            corpo = f"<h3>Seu código Controlaê:</h3><h2 style='color: #8B5CF6;'>{codigo}</h2>"
                            if enviar_email(novo_email, "Código de Validação", corpo):
                                st.session_state.update({'codigo_gerado': codigo, 'verificacao_pendente': True, 'dados_novo_user': {'user': novo_user, 'email': novo_email, 'senha': nova_senha, 'nome': novo_nome}})
                                st.rerun()
            else:
                with st.form("validacao_form"):
                    st.info(f"📧 Código enviado para {st.session_state['dados_novo_user']['email']}")
                    codigo_digitado = st.text_input("Código", max_chars=6)
                    if st.form_submit_button("Confirmar Cadastro", type="primary"):
                        if codigo_digitado == st.session_state['codigo_gerado']:
                            d = st.session_state['dados_novo_user']
                            if criar_usuario(d['user'], d['email'], d['senha'], d['nome']) == "Sucesso":
                                st.success("✅ Conta criada!")
                                st.session_state.update({'verificacao_pendente': False, 'codigo_gerado': None})
                            else: st.error("Erro ao criar usuário.")
                        else: st.error("❌ Código incorreto.")
                    if st.form_submit_button("Cancelar"):
                        st.session_state.update({'verificacao_pendente': False})
                        st.rerun()

        with tab3:
            with st.form("recupera_form"):
                email_rec = st.text_input("E-mail cadastrado")
                if st.form_submit_button("Recuperar Acesso", use_container_width=True):
                    existe, user_rec = recuperar_senha(email_rec)
                    if existe:
                        enviar_email(email_rec, "Recuperação", f"Seu usuário é: <b>{user_rec}</b>")
                        st.success("✅ Usuário enviado por e-mail.")
                    else: st.error("❌ E-mail não encontrado.")

# --- 7. DASHBOARD & MENU ---
def main_app():
    USER_ID = st.session_state['user_id']
    processar_recorrencias(USER_ID)

    with st.sidebar:
        st.write(f"Olá, **{st.session_state['user_nome']}** 👋")
        menu = st.radio("Menu", ["Dashboard", "Lançamentos", "Investimentos", "Configurar Recorrências"])
        if st.button("Sair", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    if menu == "Dashboard":
        st.title("📊 Visão Estratégica")
        df = ler_transacoes(USER_ID)
        if not df.empty:
            df['data'] = pd.to_datetime(df['data'])
            mes_atual = date.today().strftime("%Y-%m")
            df_mes = df[df['data'].dt.strftime('%Y-%m') == mes_atual]
            
            # Métricas
            df_pago = df[df['status'] == 'Pago']
            saldo = df_pago[df_pago['tipo'] == 'Receita']['valor'].sum() - df_pago[df_pago['tipo'] == 'Despesa']['valor'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Saldo Real", f"R$ {formatar_moeda(saldo)}")
            c2.metric("Receitas (Mês)", f"R$ {formatar_moeda(df_mes[(df_mes['tipo'] == 'Receita') & (df_mes['status'] == 'Pago')]['valor'].sum())}")
            c3.metric("Despesas (Mês)", f"R$ {formatar_moeda(df_mes[(df_mes['tipo'] == 'Despesa') & (df_mes['status'] == 'Pago')]['valor'].sum())}", delta_color="inverse")

            # Gráficos
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                df_cat = df_mes[df_mes['tipo'] == 'Despesa'].groupby('categoria')['valor'].sum().reset_index()
                st.plotly_chart(px.pie(df_cat, values='valor', names='categoria', hole=.5, title="Gastos por Categoria").update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA"), use_container_width=True)
            with col_g2:
                df['mes_ano'] = df['data'].dt.to_period('M').astype(str)
                df_ev = df[df['tipo'].isin(['Receita', 'Despesa'])].groupby(['mes_ano', 'tipo'])['valor'].sum().reset_index()
                st.plotly_chart(px.bar(df_ev, x='mes_ano', y='valor', color='tipo', barmode='group', title="Evolução Mensal", color_discrete_map={'Receita': '#10B981', 'Despesa': '#EF4444'}).update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA"), use_container_width=True)
            
            st.divider()
            col_e, col_d = st.columns(2)
            with col_e:
                st.subheader("⚠️ Vencimentos Próximos")
                vencendo = df_mes[(df_mes['status'] == 'Pendente') & (df_mes['tipo'] == 'Despesa') & (df_mes['data'].dt.date <= date.today() + timedelta(days=3))]
                if not vencendo.empty:
                    for _, r in vencendo.iterrows(): st.warning(f"{r['data'].strftime('%d/%m')} - {r['nome']} (R$ {formatar_moeda(r['valor'])})")
                else: st.success("Tudo em dia!")
            with col_d:
                st.subheader("⏳ Confirmar Pagamento")
                df_p = df[(df['status'] == 'Pendente') & (df['tipo'] != 'Investimento')].sort_values('data')
                if not df_p.empty:
                    opts = {f"{r['data'].strftime('%d/%m')} - {r['nome']}": r['id'] for _, r in df_p.iterrows()}
                    sel = st.selectbox("Lançamento:", list(opts.keys()))
                    dt_pago = st.date_input("Data do Pagamento:", value=date.today())
                    if st.button("✅ Confirmar Pago", type="primary", use_container_width=True):
                        confirmar_transacao(opts[sel], dt_pago)
                        st.rerun()
        else: st.info("Sem lançamentos ainda.")

    elif menu == "Lançamentos":
        st.title("💸 Lançamentos")
        t1, t2 = st.tabs(["➕ Novo", "✏️ Editar e Excluir"])
        with t1:
            with st.form("f_g"):
                c1, c2 = st.columns(2)
                d_l = c1.date_input("Data", date.today())
                n_l = c2.text_input("Descrição")
                c3, c4, c5, c6 = st.columns(4)
                v_l = c3.number_input("Valor", min_value=0.0)
                
                # Categoria agora vem da lista dinâmica
                ct_l = c4.selectbox("Categoria", st.session_state['categorias'])
                tp_l = c5.selectbox("Tipo", ["Despesa", "Receita"])
                st_l = c6.selectbox("Status", ["Pago", "Pendente"])
                
                if st.form_submit_button("Salvar", type="primary"):
                    adicionar_transacao(USER_ID, d_l, n_l, v_l, ct_l, tp_l, st_l)
                    st.success("Salvo!")
                    st.rerun()
        with t2:
            df_t = ler_transacoes(USER_ID)
            if not df_t.empty:
                df_t['data'] = pd.to_datetime(df_t['data']).dt.date
                df_t['Excluir'] = False 
                
                col_config_lancamentos = {
                    "id": None, 
                    "user_id": None, 
                    "origem_recorrencia_id": None, 
                    "data": st.column_config.DateColumn("Data", required=True),
                    "nome": st.column_config.TextColumn("Descrição", required=True),
                    "valor": st.column_config.NumberColumn("Valor", required=True),
                    # Aplicação da lista dinâmica de categorias
                    "categoria": st.column_config.SelectboxColumn("Categoria", options=st.session_state['categorias']),
                    "tipo": st.column_config.SelectboxColumn("Tipo", options=["Despesa", "Receita"]),
                    "status": st.column_config.SelectboxColumn("Status", options=["Pago", "Pendente"]),
                    "Excluir": st.column_config.CheckboxColumn("Excluir ❌", default=False)
                }

                st.info("💡 Dica: Dê um duplo clique nas colunas Categoria e Tipo para abrir a lista de opções.")

                ed = st.data_editor(
                    df_t[df_t['tipo'] != 'Investimento'], 
                    use_container_width=True, 
                    hide_index=True, 
                    num_rows="dynamic", 
                    column_config=col_config_lancamentos
                )
                
                if st.button("💾 Salvar Alterações / Remover Excluídos", type="primary"):
                    linhas_para_excluir = ed[ed['Excluir'] == True]
                    for _, row in linhas_para_excluir.iterrows():
                        if pd.notna(row.get('id')):
                            try:
                                deletar_transacao(row['id'])
                            except Exception:
                                pass 

                    df_salvar = ed[ed['Excluir'] == False].copy()
                    df_salvar = df_salvar.dropna(subset=['nome', 'valor'])
                    df_salvar = df_salvar.drop(columns=['Excluir'])
                    atualizar_transacoes(USER_ID, df_salvar)
                    
                    st.success("Alterações salvas e registros limpos!")
                    st.rerun()

    elif menu == "Investimentos":
        st.title("📈 Investimentos")
        t1, t2 = st.tabs(["➕ Novo Aporte", "✏️ Carteira"])
        with t1:
            with st.form("f_i"):
                d_i = st.date_input("Data", date.today())
                n_i = st.text_input("Descrição")
                v_i = st.number_input("Valor", min_value=0.0)
                ct_i = st.selectbox("Tipo", ["Reserva de Emergência", "Renda Fixa", "Ações", "Cripto"])
                if st.form_submit_button("Investir"):
                    adicionar_transacao(USER_ID, d_i, n_i, v_i, ct_i, "Investimento", "Pago")
                    st.rerun()
        with t2:
            df_i = ler_transacoes(USER_ID)
            df_i = df_i[df_i['tipo'] == 'Investimento']
            if not df_i.empty:
                st.dataframe(df_i[['data', 'nome', 'valor', 'categoria']], use_container_width=True, hide_index=True)

    elif menu == "Configurar Recorrências":
        st.title("⚙️ Contas Fixas e Parâmetros")
        
        # Criação da nova aba de Categorias
        t1, t2 = st.tabs(["⚙️ Contas Fixas", "🏷️ Categorias"])
        
        with t1:
            df_r = ler_recorrencias(USER_ID)
            
            if 'Excluir' not in df_r.columns:
                df_r['Excluir'] = False

            col_config_recorrencias = {
                "id": None, 
                "user_id": None, 
                "nome": st.column_config.TextColumn("Descrição", required=True),
                "valor": st.column_config.NumberColumn("Valor", required=True),
                "dia_vencimento": st.column_config.NumberColumn("Dia de Vencimento", min_value=1, max_value=31, required=True),
                # Aplicação da lista dinâmica de categorias
                "categoria": st.column_config.SelectboxColumn("Categoria", options=st.session_state['categorias']),
                "tipo": st.column_config.SelectboxColumn("Tipo", options=["Despesa", "Receita"]),
                "ativo": st.column_config.CheckboxColumn("Ativo"),
                "data_limite": st.column_config.DateColumn("Data Limite"),
                "Excluir": st.column_config.CheckboxColumn("Excluir ❌", default=False)
            }

            st.info("💡 Dica: Dê um duplo clique nas colunas Categoria e Tipo para abrir a lista de opções.")

            ed_r = st.data_editor(
                df_r, 
                num_rows="dynamic",
                use_container_width=True, 
                hide_index=True, 
                column_config=col_config_recorrencias
            )
            
            if st.button("Salvar Recorrências / Remover Excluídos", type="primary"):
                linhas_para_excluir_r = ed_r[ed_r['Excluir'] == True]
                for _, row in linhas_para_excluir_r.iterrows():
                    if pd.notna(row.get('id')):
                        try:
                            deletar_recorrencia(row['id'])
                        except Exception:
                            pass
                
                df_salvar_r = ed_r[ed_r['Excluir'] == False].copy()
                df_salvar_r = df_salvar_r.dropna(subset=['nome', 'valor', 'dia_vencimento'])
                df_salvar_r = df_salvar_r.drop(columns=['Excluir'])
                atualizar_recorrencias(USER_ID, df_salvar_r)
                
                st.success("Recorrências atualizadas e registros limpos!")
                st.rerun()

        # --- NOVA ABA DE CATEGORIAS ---
        with t2:
            st.subheader("Gerenciar Categorias")
            st.write("Adicione, edite ou remova as categorias que aparecerão nas listas do sistema. Use a linha em branco no final para adicionar uma nova.")
            
            # Converte a lista da sessão para um DataFrame
            df_categorias = pd.DataFrame(st.session_state['categorias'], columns=['Categoria'])
            
            # Grid editável para as categorias
            ed_categorias = st.data_editor(
                df_categorias,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("💾 Salvar Categorias", type="primary"):
                # Pega as categorias editadas, remove vazios e espaços extras
                novas_categorias = ed_categorias['Categoria'].dropna().str.strip()
                # Remove strings vazias e duplicadas, transforma de volta em lista
                novas_categorias = novas_categorias[novas_categorias != ""].unique().tolist()
                
                # Salva na sessão
                st.session_state['categorias'] = novas_categorias
                st.success("Lista de Categorias atualizada com sucesso! As alterações já estão valendo nas outras abas.")
                st.rerun()

if not st.session_state['logged_in']: tela_login()
else: main_app()
