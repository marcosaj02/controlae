import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from modules.database import *
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import json
import os

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

# --- 2. FUNÇÕES AUXILIARES ---
def formatar_moeda(valor):
    return f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def descobrir_extensao(byte_data):
    if not byte_data: return '.bin'
    if isinstance(byte_data, memoryview): byte_data = byte_data.tobytes()
    elif not isinstance(byte_data, bytes): byte_data = bytes(byte_data)
        
    if byte_data.startswith(b'%PDF'): return '.pdf'
    if byte_data.startswith(b'\xff\xd8'): return '.jpg'
    if byte_data.startswith(b'\x89PNG'): return '.png'
    return '.bin'

def formatar_hhmm(valor_decimal):
    """Converte horas decimais (ex: 1.5) para formato hora (ex: 01:30h)"""
    if pd.isna(valor_decimal): return "00:00h"
    sinal = "-" if valor_decimal < 0 else ""
    valor_abs = abs(valor_decimal)
    horas = int(valor_abs)
    minutos = int(round((valor_abs - horas) * 60))
    return f"{sinal}{horas:02d}:{minutos:02d}h"

# --- 3. CONFIGURAÇÃO DA PÁGINA E BANCO ---
st.set_page_config(page_title="Gestor Financeiro Pro", layout="wide", page_icon="💳")
inicializar_db()

# --- 4. CONFIGURAÇÃO DE TEMAS E BARRA LATERAL (CSS MODERNO) ---
def carregar_tema():
    tema_sel = st.sidebar.selectbox(
        "🎨", 
        ["🌙", "☀️"], 
        help="Alternar Tema: 🌙 Dark Premium | ☀️ Fintech Clean",
        label_visibility="collapsed"
    )

    if tema_sel == "🌙":
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
    .stApp {{ background-color: {cor_fundo}; color: {cor_texto}; }}
    [data-testid="stSidebar"] {{ background-color: {cor_input}; }}
    p, h1, h2, h3, label {{ color: {cor_texto} !important; }}

    [data-testid="stSidebar"] {{
        min-width: 85px !important;
        max-width: 85px !important;
        padding-top: 1rem;
    }}
    
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ align-items: center; }}
    
    [data-testid="stSidebar"] .stRadio label p {{
        font-size: 26px !important;
        text-align: center;
        margin: 0;
        padding: 5px 0;
    }}

    [data-testid="stSidebarNav"] {{ display: none; }}

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

# --- 5. INICIALIZAÇÃO DA SESSÃO ---
if 'logged_in' not in st.session_state:
    st.session_state.update({
        'logged_in': False, 'user_id': None, 'user_nome': None,
        'verificacao_pendente': False, 'codigo_gerado': None, 'dados_novo_user': None
    })

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
                    user_data = verificar_login(usuario.strip(), senha)
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
                            if enviar_email(novo_email.strip(), "Código de Validação", corpo):
                                st.session_state.update({'codigo_gerado': codigo, 'verificacao_pendente': True, 'dados_novo_user': {'user': novo_user.strip(), 'email': novo_email.strip(), 'senha': nova_senha, 'nome': novo_nome.strip()}})
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
                    existe, user_rec = recuperar_senha(email_rec.strip())
                    if existe:
                        enviar_email(email_rec.strip(), "Recuperação", f"Seu usuário é: <b>{user_rec}</b>")
                        st.success("✅ Usuário enviado por e-mail.")
                    else: st.error("❌ E-mail não encontrado.")

# --- 7. DASHBOARD & MENU ---
def main_app():
    USER_ID = st.session_state['user_id']
    processar_recorrencias(USER_ID)

    lista_final_cats = ler_categorias_db(USER_ID)
    st.session_state['categorias'] = sorted(lista_final_cats)

    with st.sidebar:
        inicial_nome = st.session_state['user_nome'][0].upper() if st.session_state['user_nome'] else "👤"
        st.markdown(f"<h3 style='text-align: center; color: {st.get_option('theme.primaryColor')};' title='Logado como: {st.session_state['user_nome']}'>👤</h3>", unsafe_allow_html=True)
        st.write("")
        
        mapa_menu = {
            "📊": "Dashboard", 
            "💸": "Lançamentos", 
            "📈": "Investimentos", 
            "⏱️": "Gestão de Projetos",
            "⚙️": "Configurações"
        }
        
        menu_selecionado = st.radio(
            "Navegação", 
            list(mapa_menu.keys()), 
            help="📊 Dashboard | 💸 Lançamentos | 📈 Investimentos | ⏱️ Gestão de Projetos | ⚙️ Configurações",
            label_visibility="collapsed"
        )
        
        menu = mapa_menu[menu_selecionado]
        
        st.write("")
        st.write("")
        if st.button("🚪", help="Sair do Sistema", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- RENDERIZAÇÃO DAS TELAS ---
    if menu == "Dashboard":
        st.title("📊 Visão Estratégica")
        df = ler_transacoes(USER_ID)
        if not df.empty:
            df['data'] = pd.to_datetime(df['data'])
            mes_atual = date.today().strftime("%Y-%m")
            df_mes = df[df['data'].dt.strftime('%Y-%m') == mes_atual]
            
            df_pago = df[df['status'] == 'Pago']
            saldo = df_pago[df_pago['tipo'] == 'Receita']['valor'].sum() - df_pago[df_pago['tipo'] == 'Despesa']['valor'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Saldo Real", f"R$ {formatar_moeda(saldo)}")
            c2.metric("Receitas (Mês)", f"R$ {formatar_moeda(df_mes[(df_mes['tipo'] == 'Receita') & (df_mes['status'] == 'Pago')]['valor'].sum())}")
            c3.metric("Despesas (Mês)", f"R$ {formatar_moeda(df_mes[(df_mes['tipo'] == 'Despesa') & (df_mes['status'] == 'Pago')]['valor'].sum())}", delta_color="inverse")

            st.divider()
            
            visao_grafico = st.radio("🔍 Visão dos Gráficos abaixo:", ["Realizado (Apenas Pagos)", "Projetado (Pagos + Pendentes)"], horizontal=True)
            df_mes_plot = df_mes[df_mes['status'] == 'Pago'].copy() if "Realizado" in visao_grafico else df_mes.copy()

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                df_cat = df_mes_plot[df_mes_plot['tipo'] == 'Despesa'].groupby('categoria')['valor'].sum().reset_index()
                if not df_cat.empty:
                    st.plotly_chart(px.pie(df_cat, values='valor', names='categoria', hole=.5, title="Gastos por Categoria").update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA"), use_container_width=True)
                else:
                    st.info("Nenhum gasto encontrado para a visão selecionada.")
                    
            with col_g2:
                if not df_mes_plot.empty:
                    df_mes_ev = df_mes_plot[df_mes_plot['tipo'].isin(['Receita', 'Despesa'])].groupby('tipo')['valor'].sum().reset_index()
                    fig = px.bar(
                        df_mes_ev, 
                        x='tipo', 
                        y='valor', 
                        color='tipo', 
                        title="Comparativo do Mês Corrente", 
                        color_discrete_map={'Receita': '#10B981', 'Despesa': '#EF4444'}
                    )
                    fig.update_xaxes(title="") 
                    fig.update_yaxes(title="")
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA", showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Nenhum lançamento encontrado para a visão selecionada no mês atual.")
            
            st.divider()
            col_e, col_d = st.columns(2)
            with col_e:
                st.subheader("⚠️ Vencimentos Próximos")
                vencendo = df_mes[(df_mes['status'] == 'Pendente') & (df_mes['tipo'] == 'Despesa') & (df_mes['data'].dt.date <= date.today() + timedelta(days=3))]
                if not vencendo.empty:
                    for _, r in vencendo.iterrows(): st.warning(f"{r['data'].strftime('%d/%m/%Y')} - {r['nome']} (R$ {formatar_moeda(r['valor'])})")
                else: st.success("Tudo em dia!")
            with col_d:
                st.subheader("⏳ Confirmar Pagamento")
                df_p = df[(df['status'] == 'Pendente') & (df['tipo'] != 'Investimento')].sort_values('data')
                
                if not df_p.empty:
                    opts = {f"{r['data'].strftime('%d/%m/%Y')} - {r['nome']}": r['id'] for _, r in df_p.iterrows()}
                    sel = st.selectbox("Lançamento:", list(opts.keys()), key="sel_pgto")
                    dt_pago = st.date_input("Data do Pagamento:", value=date.today(), format="DD/MM/YYYY", key="dt_pgto")
                    
                    anexar_comprovante = st.radio("Anexar Comprovante?", ["Não", "Sim"], horizontal=True)
                    arquivo_comprovante = None
                    
                    if anexar_comprovante == "Sim":
                        arquivo_comprovante = st.file_uploader("Selecione o arquivo", type=["jpg", "jpeg", "png", "pdf"])
                        
                    if st.button("✅ Confirmar Pago", type="primary", use_container_width=True):
                        if anexar_comprovante == "Sim" and arquivo_comprovante is None:
                            st.warning("⚠️ Por favor, selecione um arquivo ou marque a opção 'Não'.")
                        else:
                            arquivo_bytes = arquivo_comprovante.read() if arquivo_comprovante else None
                            confirmar_transacao(opts[sel], dt_pago, arquivo_bytes)
                            st.success("Pagamento confirmado com sucesso!")
                            st.rerun()
                else:
                    st.info("Nenhuma conta pendente para confirmação.")
        else: st.info("Sem lançamentos ainda.")

    elif menu == "Lançamentos":
        st.title("💸 Lançamentos")
        t1, t2 = st.tabs(["✏️ Editar e Excluir", "➕ Novo"])
        
        with t1:
            df_t = ler_transacoes(USER_ID)
            if not df_t.empty:
                df_t['data'] = pd.to_datetime(df_t['data'])
                
                hoje = date.today()
                meses_dict = {
                    1: "01 - Janeiro", 2: "02 - Fevereiro", 3: "03 - Março", 4: "04 - Abril",
                    5: "05 - Maio", 6: "06 - Junho", 7: "07 - Julho", 8: "08 - Agosto",
                    9: "09 - Setembro", 10: "10 - Outubro", 11: "11 - Novembro", 12: "12 - Dezembro"
                }
                
                anos_db = df_t['data'].dt.year.unique().tolist()
                anos_disponiveis = sorted(list(set([hoje.year - 1, hoje.year, hoje.year + 1] + anos_db)))
                
                col_m, col_y = st.columns(2)
                mes_selecionado = col_m.selectbox("Filtrar por Mês:", list(meses_dict.values()), index=hoje.month - 1)
                ano_selecionado = col_y.selectbox("Filtrar por Ano:", anos_disponiveis, index=anos_disponiveis.index(hoje.year))
                
                mes_num = list(meses_dict.keys())[list(meses_dict.values()).index(mes_selecionado)]
                
                df_t_mes = df_t[(df_t['data'].dt.month == mes_num) & (df_t['data'].dt.year == ano_selecionado)].copy()

                if not df_t_mes.empty:
                    df_t_investimentos = df_t_mes[df_t_mes['tipo'] == 'Investimento']
                    df_t_lancamentos = df_t_mes[df_t_mes['tipo'] != 'Investimento']

                    with st.expander("🔍 Filtros Avançados e Ordenação", expanded=False):
                        c_f1, c_f2, c_f3 = st.columns(3)
                        f_texto = c_f1.text_input("Buscar por Descrição")
                        f_cat = c_f2.multiselect("Filtrar Categoria", st.session_state['categorias'])
                        f_status = c_f3.multiselect("Filtrar Status", ["Pago", "Pendente"])
                        
                        st.divider()
                        st.write("**Ordenar por**")
                        c_o1, c_o2 = st.columns(2)
                        coluna_ordenacao = c_o1.selectbox("Coluna", ["Data", "Descrição", "Valor", "Categoria"])
                        direcao_ordenacao = c_o2.radio("Ordem", ["Crescente", "Decrescente"], horizontal=True)

                    df_filtrado = df_t_lancamentos.copy()
                    if f_texto:
                        df_filtrado = df_filtrado[df_filtrado['nome'].str.contains(f_texto, case=False, na=False)]
                    if f_cat:
                        df_filtrado = df_filtrado[df_filtrado['categoria'].isin(f_cat)]
                    if f_status:
                        df_filtrado = df_filtrado[df_filtrado['status'].isin(f_status)]

                    mapa_colunas = {"Data": "data", "Descrição": "nome", "Valor": "valor", "Categoria": "categoria"}
                    coluna_real = mapa_colunas[coluna_ordenacao]
                    
                    df_filtrado = df_filtrado.sort_values(by=coluna_real, ascending=(direcao_ordenacao == "Crescente")).reset_index(drop=True)
                    df_filtrado.insert(0, 'Selecionar', False)

                    df_filtrado_grid = df_filtrado.drop(columns=['comprovante'], errors='ignore')

                    col_config_lancamentos = {
                        "id": None, 
                        "user_id": None, 
                        "origem_recorrencia_id": None, 
                        "Selecionar": st.column_config.CheckboxColumn("🧮 Selecionar", default=False),
                        "data": st.column_config.DateColumn("Data", required=True, format="DD/MM/YYYY"),
                        "nome": st.column_config.TextColumn("Descrição", required=True),
                        "valor": st.column_config.NumberColumn("Valor", required=True, format="%.2f"),
                        "categoria": st.column_config.SelectboxColumn("Categoria", options=st.session_state['categorias']),
                        "tipo": st.column_config.SelectboxColumn("Tipo", options=["Despesa", "Receita"]),
                        "status": st.column_config.SelectboxColumn("Status", options=["Pago", "Pendente"])
                    }

                    metricas_container = st.empty()

                    st.info("💡 **Atenção à Matemática:** Se nenhuma caixa **🧮 Selecionar** estiver marcada, os valores acima refletem o total geral da tabela/filtro. Caso você marque qualquer caixa, a matemática calcula **apenas** o que foi selecionado.")

                    ed = st.data_editor(
                        df_filtrado_grid, 
                        use_container_width=True, 
                        hide_index=True, 
                        num_rows="dynamic", 
                        column_config=col_config_lancamentos,
                        key="editor_lancamentos"
                    )
                    
                    has_selection = ed['Selecionar'].any()
                    
                    if has_selection:
                        receitas_sum = ed[(ed['tipo'] == 'Receita') & (ed['Selecionar'] == True)]['valor'].sum()
                        despesas_sum = ed[(ed['tipo'] == 'Despesa') & (ed['Selecionar'] == True)]['valor'].sum()
                    else:
                        receitas_sum = ed[ed['tipo'] == 'Receita']['valor'].sum()
                        despesas_sum = ed[ed['tipo'] == 'Despesa']['valor'].sum()

                    with metricas_container.container():
                        cm1, cm2 = st.columns(2)
                        cm1.metric("Receita", f"R$ {formatar_moeda(receitas_sum)}")
                        cm2.metric("Despesa", f"R$ {formatar_moeda(despesas_sum)}")
                    
                    if st.button("💾 Salvar Alterações", type="primary"):
                        ids_originais = set(df_filtrado_grid['id'].dropna())
                        ids_editados = set(ed['id'].dropna())
                        ids_excluidos = ids_originais - ids_editados
                        
                        for id_del in ids_excluidos:
                            try: deletar_transacao(id_del)
                            except Exception: pass 

                        ids_no_filtro = df_filtrado_grid['id'].dropna().tolist()
                        df_restante = df_t[~df_t['id'].isin(ids_no_filtro)] 
                        
                        df_salvar_parcial = ed.dropna(subset=['nome', 'valor']).drop(columns=['Selecionar'], errors='ignore')
                        df_salvar_final = pd.concat([df_restante, df_salvar_parcial], ignore_index=True)

                        atualizar_transacoes(USER_ID, df_salvar_final)
                        st.success("Alterações salvas!")
                        st.rerun()

                    st.divider()
                    st.subheader("📎 Anexos e Comprovantes")
                    
                    df_com_anexo = df_filtrado[df_filtrado['comprovante'].notna() & (df_filtrado['comprovante'] != b'')]
                    
                    if not df_com_anexo.empty:
                        opts_comp = {f"{r['data'].strftime('%d/%m/%Y')} - {r['nome']} (R$ {formatar_moeda(r['valor'])})": r['comprovante'] for _, r in df_com_anexo.iterrows()}
                        sel_comp = st.selectbox("Selecione o Lançamento:", list(opts_comp.keys()))
                        
                        if sel_comp:
                            arquivo_bytes = opts_comp[sel_comp]
                            
                            if isinstance(arquivo_bytes, memoryview):
                                arquivo_bytes = arquivo_bytes.tobytes()
                            elif not isinstance(arquivo_bytes, bytes):
                                arquivo_bytes = bytes(arquivo_bytes)
                                
                            extensao = descobrir_extensao(arquivo_bytes)
                            nome_arquivo = f"Comprovante_{sel_comp.split('-')[1].split('(')[0].strip()}{extensao}"
                            
                            st.download_button(
                                label="⬇️ Baixar Comprovante",
                                data=arquivo_bytes,
                                file_name=nome_arquivo,
                                mime="application/octet-stream"
                            )
                    else:
                        st.info("Nenhum comprovante anexado aos lançamentos deste mês.")
                        
                else:
                    st.info(f"Nenhum lançamento encontrado para {mes_selecionado} de {ano_selecionado}.")
            else:
                st.info("Nenhum lançamento encontrado ainda. Vá na aba 'Novo' para começar.")

        with t2:
            with st.form("f_g"):
                c1, c2 = st.columns(2)
                d_l = c1.date_input("Data", date.today(), format="DD/MM/YYYY")
                n_l = c2.text_input("Descrição")
                c3, c4, c5, c6 = st.columns(4)
                v_l = c3.number_input("Valor", min_value=0.0, format="%.2f", step=0.01)
                
                ct_l = c4.selectbox("Categoria", st.session_state['categorias'])
                tp_l = c5.selectbox("Tipo", ["Despesa", "Receita"])
                st_l = c6.selectbox("Status", ["Pago", "Pendente"])
                
                if st.form_submit_button("Salvar", type="primary"):
                    adicionar_transacao(USER_ID, d_l, n_l, v_l, ct_l, tp_l, st_l)
                    st.success("Salvo!")
                    st.rerun()

    elif menu == "Investimentos":
        st.title("📈 Investimentos")
        t1, t2 = st.tabs(["➕ Novo Aporte", "✏️ Carteira"])
        with t1:
            with st.form("f_i"):
                d_i = st.date_input("Data", date.today(), format="DD/MM/YYYY")
                n_i = st.text_input("Descrição")
                v_i = st.number_input("Valor", min_value=0.0, format="%.2f", step=0.01)
                ct_i = st.selectbox("Tipo", ["Reserva de Emergência", "Renda Fixa", "Ações", "Cripto"])
                if st.form_submit_button("Investir"):
                    adicionar_transacao(USER_ID, d_i, n_i, v_i, ct_i, "Investimento", "Pago")
                    st.rerun()
        with t2:
            df_i_full = ler_transacoes(USER_ID)
            df_i = df_i_full[df_i_full['tipo'] == 'Investimento']
            if not df_i.empty:
                df_i['data'] = pd.to_datetime(df_i['data']).dt.date
                
                with st.expander("🔍 Filtros e Ordenação", expanded=False):
                    c_i1, c_i2 = st.columns([2, 1])
                    f_i_texto = c_i1.text_input("Buscar Investimento")
                    
                    c_io1, c_io2 = st.columns(2)
                    coluna_ord_inv = c_io1.selectbox("Ordenar por", ["Data", "Descrição", "Valor", "Tipo"])
                    direcao_ord_inv = c_io2.radio("Ordem", ["Crescente", "Decrescente"], horizontal=True, key="ord_inv")

                if f_i_texto:
                    df_i = df_i[df_i['nome'].str.contains(f_i_texto, case=False, na=False)]

                mapa_colunas_inv = {"Data": "data", "Descrição": "nome", "Valor": "valor", "Tipo": "categoria"}
                
                df_i = df_i.sort_values(by=mapa_colunas_inv[coluna_ord_inv], ascending=(direcao_ord_inv == "Crescente")).reset_index(drop=True)

                st.dataframe(
                    df_i[['data', 'nome', 'valor', 'categoria']], 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        "nome": st.column_config.TextColumn("Descrição"),
                        "valor": st.column_config.NumberColumn("Valor", format="%.2f"),
                        "categoria": st.column_config.TextColumn("Tipo")
                    }
                )

    elif menu == "Gestão de Projetos":
        st.title("⏱️ Gestão de Projetos e Apontamentos")
        
        df_clientes = ler_clientes(USER_ID)
        clientes_lista = df_clientes['nome'].tolist() if not df_clientes.empty else []
        
        t1, t2, t3 = st.tabs(["⏱️ Apontamentos", "📊 Extrato e Dashboard", "👥 Cadastro de Clientes"])
        
        with t1:
            if not clientes_lista:
                st.warning("⚠️ Você precisa cadastrar um cliente na aba 'Cadastro de Clientes' antes de lançar horas.")
            else:
                df_apt_full = ler_apontamentos(USER_ID)
                
                with st.container():
                    st.subheader("Lançar Horas")
                    with st.form("form_apontamento"):
                        c1, c2, c3, c4 = st.columns([1.5, 2.5, 1, 1])
                        apt_data = c1.date_input("Data", date.today(), format="DD/MM/YYYY")
                        apt_cliente = c2.selectbox("Cliente", clientes_lista)
                        
                        apt_h = c3.number_input("Horas", min_value=0, step=1)
                        apt_m = c4.selectbox("Min", ["00", "15", "30", "45"])
                        
                        c5, c6 = st.columns([1, 1])
                        apt_chamado = c5.text_input("Nr. do Chamado", max_chars=20)
                        apt_projeto = c6.text_input("Projeto (Opcional)")
                        
                        c7, c8 = st.columns([3, 1])
                        apt_desc = c7.text_input("Descrição da Atividade")
                        apt_recurso = c8.selectbox("Recurso", ["Funcional", "ABAP"])
                        
                        if st.form_submit_button("💾 Salvar Apontamento", type="primary"):
                            apt_horas_dec = apt_h + (int(apt_m) / 60.0)
                            if apt_horas_dec > 0 and apt_desc:
                                adicionar_apontamento(USER_ID, apt_data, apt_cliente, apt_chamado, apt_projeto, apt_desc, apt_recurso, apt_horas_dec)
                                st.success("Horas lançadas com sucesso!")
                                st.rerun()
                            else:
                                st.warning("Preencha as Horas Gastas e a Descrição.")
                
                st.divider()
                st.subheader("Painel de Saldo Dinâmico")
                cliente_saldo_sel = st.selectbox("Selecione o Cliente para ver o saldo:", clientes_lista)
                
                if cliente_saldo_sel:
                    info_cli = df_clientes[df_clientes['nome'] == cliente_saldo_sel].iloc[0]
                    saldo_anual_contratado = info_cli['saldo_horas']
                    
                    horas_consumidas_ano = 0
                    if not df_apt_full.empty:
                        df_apt_full['data'] = pd.to_datetime(df_apt_full['data'])
                        ano_atual = date.today().year
                        df_cli_ano = df_apt_full[(df_apt_full['cliente'] == cliente_saldo_sel) & (df_apt_full['data'].dt.year == ano_atual)]
                        horas_consumidas_ano = df_cli_ano['horas'].sum()
                        
                    saldo_restante = saldo_anual_contratado - horas_consumidas_ano
                    
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Saldo Anual Contratado", formatar_hhmm(saldo_anual_contratado))
                    mc2.metric("Horas Consumidas no Ano", formatar_hhmm(horas_consumidas_ano))
                    mc3.metric("Saldo Restante", formatar_hhmm(saldo_restante), delta=f"{(saldo_restante/saldo_anual_contratado)*100:.1f}%" if saldo_anual_contratado>0 else "0%")

                st.divider()
                st.write("**Histórico de Lançamentos (Editar/Excluir)**")
                if not df_apt_full.empty:
                    df_apt_edit = df_apt_full.copy()
                    df_apt_edit['data'] = pd.to_datetime(df_apt_edit['data']).dt.date
                    
                    col_config_apt = {
                        "id": None, "user_id": None,
                        "data": st.column_config.DateColumn("Data", required=True, format="DD/MM/YYYY"),
                        "cliente": st.column_config.SelectboxColumn("Cliente", options=clientes_lista),
                        "chamado": st.column_config.TextColumn("Chamado", max_chars=20),
                        "projeto": st.column_config.TextColumn("Projeto"),
                        "descricao": st.column_config.TextColumn("Descrição"),
                        "recurso": st.column_config.SelectboxColumn("Recurso", options=["Funcional", "ABAP"]),
                        "horas": st.column_config.NumberColumn("Horas (Decimais)", required=True, format="%g", help="O banco usa decimais. 1h30 min = 1.5")
                    }
                    
                    with st.form("edit_apontamentos"):
                        st.info("Para apagar uma linha, selecione a lateral esquerda e aperte `Delete`.")
                        ed_apt = st.data_editor(df_apt_edit, use_container_width=True, hide_index=True, column_config=col_config_apt)
                        
                        if st.form_submit_button("Salvar Edições"):
                            atualizar_apontamentos(USER_ID, ed_apt)
                            st.success("Histórico atualizado!")
                            st.rerun()
                else:
                    st.info("Ainda não há lançamentos registrados.")

        with t2:
            st.subheader("Extrato de Cliente")
            if not clientes_lista:
                st.warning("Cadastre um cliente primeiro.")
            else:
                df_apt_extrato = ler_apontamentos(USER_ID)
                
                if not df_apt_extrato.empty:
                    df_apt_extrato['data'] = pd.to_datetime(df_apt_extrato['data'])
                    
                    hoje = date.today()
                    meses_dict = {
                        1: "01 - Janeiro", 2: "02 - Fevereiro", 3: "03 - Março", 4: "04 - Abril",
                        5: "05 - Maio", 6: "06 - Junho", 7: "07 - Julho", 8: "08 - Agosto",
                        9: "09 - Setembro", 10: "10 - Outubro", 11: "11 - Novembro", 12: "12 - Dezembro"
                    }
                    
                    anos_apt = df_apt_extrato['data'].dt.year.unique().tolist()
                    
                    cx1, cx2, cx3 = st.columns(3)
                    ext_cliente = cx1.selectbox("Filtrar Cliente:", clientes_lista)
                    ext_mes = cx2.selectbox("Mês do Extrato:", list(meses_dict.values()), index=hoje.month - 1)
                    ext_ano = cx3.selectbox("Ano Base:", sorted(anos_apt, reverse=True))
                    
                    mes_num = list(meses_dict.keys())[list(meses_dict.values()).index(ext_mes)]
                    
                    df_ano_grafico = df_apt_extrato[(df_apt_extrato['cliente'] == ext_cliente) & 
                                                    (df_apt_extrato['data'].dt.year == ext_ano)]
                                                    
                    df_mes_detalhe = df_ano_grafico[df_ano_grafico['data'].dt.month == mes_num]
                                              
                    if not df_ano_grafico.empty:
                        total_horas_mes = df_mes_detalhe['horas'].sum() if not df_mes_detalhe.empty else 0
                        total_horas_ano = df_ano_grafico['horas'].sum()
                        
                        m1, m2 = st.columns(2)
                        m1.metric(f"Horas Consumidas ({ext_mes})", formatar_hhmm(total_horas_mes))
                        m2.metric(f"Total Acumulado ({ext_ano})", formatar_hhmm(total_horas_ano))
                        
                        st.divider()
                        
                        g1, g2 = st.columns(2)
                        with g1:
                            if not df_mes_detalhe.empty:
                                df_rec = df_mes_detalhe.groupby('recurso')['horas'].sum().reset_index()
                                fig_rec = px.pie(df_rec, values='horas', names='recurso', hole=0.5, title=f"Distribuição por Recurso ({ext_mes})")
                                fig_rec.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA")
                                st.plotly_chart(fig_rec, use_container_width=True)
                            else:
                                st.info(f"Sem horas lançadas em {ext_mes}.")
                                
                        with g2:
                            df_evolucao = df_ano_grafico.copy()
                            df_evolucao['mes_num'] = df_evolucao['data'].dt.month
                            df_grp = df_evolucao.groupby('mes_num')['horas'].sum().reset_index()
                            
                            map_meses = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
                            df_grp['Mês'] = df_grp['mes_num'].map(map_meses)
                            df_grp = df_grp.sort_values('mes_num')
                            
                            # --- AJUSTE: Mês definido como cor para gerar barras coloridas ---
                            fig_ano = px.bar(df_grp, x='Mês', y='horas', color='Mês', title=f"Evolução Mensal do Consumo ({ext_ano})", text_auto='.1f')
                            fig_ano.update_xaxes(title="")
                            fig_ano.update_yaxes(title="")
                            fig_ano.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA", showlegend=False) # Esconde legenda redundante
                            st.plotly_chart(fig_ano, use_container_width=True)
                        
                        st.write(f"**Extrato Detalhado para o Cliente ({ext_mes}):**")
                        if not df_mes_detalhe.empty:
                            df_display = df_mes_detalhe[['data', 'chamado', 'projeto', 'descricao', 'recurso', 'horas']].copy()
                            df_display['data'] = df_display['data'].dt.strftime('%d/%m/%Y')
                            df_display['horas'] = df_display['horas'].apply(formatar_hhmm)
                            st.dataframe(df_display, use_container_width=True, hide_index=True)
                        else:
                            st.info("Nenhum apontamento detalhado para o mês selecionado.")
                    else:
                        st.info("Nenhum apontamento para este cliente no ano selecionado.")
                else:
                    st.info("Faça o seu primeiro apontamento na aba ao lado.")
                    
        with t3:
            st.subheader("Gerenciar Clientes e Franquias")
            st.write("Adicione novos clientes informando o Saldo Anual de horas e a sua Taxa base.")
            
            df_clientes_edit = df_clientes.copy() if not df_clientes.empty else pd.DataFrame(columns=['id', 'nome', 'saldo_horas', 'valor_hora'])
            
            col_config_cli = {
                "id": None,
                "nome": st.column_config.TextColumn("Nome do Cliente", required=True),
                "saldo_horas": st.column_config.NumberColumn("Saldo Anual (Horas)", required=True),
                "valor_hora": st.column_config.NumberColumn("Valor Hora (R$)", required=True, format="%.2f")
            }
            
            with st.form("form_clientes"):
                ed_cli = st.data_editor(
                    df_clientes_edit, 
                    num_rows="dynamic", 
                    use_container_width=True, 
                    hide_index=True, 
                    column_config=col_config_cli
                )
                
                if st.form_submit_button("💾 Salvar Clientes", type="primary"):
                    atualizar_clientes(USER_ID, ed_cli)
                    st.success("Lista de clientes atualizada com sucesso!")
                    st.rerun()

    elif menu == "Configurações":
        st.title("⚙️ Configurações Gerais")
        
        t1, t2 = st.tabs(["⚙️ Contas Fixas", "🏷️ Categorias"])
        
        with t1:
            df_r_full = ler_recorrencias(USER_ID)
            
            with st.expander("🔍 Filtros e Ordenação", expanded=False):
                st.write("**Filtros**")
                c_rf1, c_rf2 = st.columns(2)
                f_r_texto = c_rf1.text_input("Buscar por Descrição")
                f_r_cat = c_rf2.multiselect("Filtrar Categoria", st.session_state['categorias'])

                st.divider()
                st.write("**Ordenar por**")
                c_ro1, c_ro2 = st.columns(2)
                coluna_ord_rec = c_ro1.selectbox("Coluna", ["Descrição", "Valor", "Dia de Vencimento", "Categoria"])
                direcao_ord_rec = c_ro2.radio("Ordem", ["Crescente", "Decrescente"], horizontal=True, key="ord_rec")

            df_r_filtrado = df_r_full.copy() if not df_r_full.empty else df_r_full
            
            if not df_r_filtrado.empty:
                if f_r_texto:
                    df_r_filtrado = df_r_filtrado[df_r_filtrado['nome'].str.contains(f_r_texto, case=False, na=False)]
                if f_r_cat:
                    df_r_filtrado = df_r_filtrado[df_r_filtrado['categoria'].isin(f_r_cat)]
                
                mapa_colunas_rec = {"Descrição": "nome", "Valor": "valor", "Dia de Vencimento": "dia_vencimento", "Categoria": "categoria"}
                
                df_r_filtrado = df_r_filtrado.sort_values(by=mapa_colunas_rec[coluna_ord_rec], ascending=(direcao_ord_rec == "Crescente")).reset_index(drop=True)

            col_config_recorrencias = {
                "id": None, 
                "user_id": None, 
                "nome": st.column_config.TextColumn("Descrição", required=True),
                "valor": st.column_config.NumberColumn("Valor", required=True, format="%.2f"),
                "dia_vencimento": st.column_config.NumberColumn("Dia de Vencimento", min_value=1, max_value=31, required=True),
                "categoria": st.column_config.SelectboxColumn("Categoria", options=st.session_state['categorias']),
                "tipo": st.column_config.SelectboxColumn("Tipo", options=["Despesa", "Receita"]),
                "ativo": st.column_config.CheckboxColumn("Ativo"),
                "data_limite": st.column_config.DateColumn("Data Limite", format="DD/MM/YYYY")
            }

            with st.form("form_editar_recorrencias"):
                st.info("💡 **Dica:** Para excluir uma linha inteira, selecione-a na margem esquerda e aperte `Delete`.")

                ed_r = st.data_editor(
                    df_r_filtrado, 
                    num_rows="dynamic",
                    use_container_width=True, 
                    hide_index=True, 
                    column_config=col_config_recorrencias
                )
                
                if st.form_submit_button("💾 Salvar Recorrências", type="primary"):
                    ids_originais_r = set(df_r_filtrado['id'].dropna())
                    ids_editados_r = set(ed_r['id'].dropna())
                    ids_excluidos_r = ids_originais_r - ids_editados_r
                    
                    for id_del in ids_excluidos_r:
                        try: deletar_recorrencia(id_del)
                        except Exception: pass
                    
                    ids_no_filtro_r = df_r_filtrado['id'].dropna().tolist()
                    df_restante_r = df_r_full[~df_r_full['id'].isin(ids_no_filtro_r)]
                    
                    df_salvar_parcial_r = ed_r.dropna(subset=['nome', 'valor', 'dia_vencimento'])
                    df_salvar_final_r = pd.concat([df_restante_r, df_salvar_parcial_r], ignore_index=True)

                    atualizar_recorrencias(USER_ID, df_salvar_final_r)
                    
                    st.success("Recorrências atualizadas!")
                    st.rerun()

        with t2:
            with st.form("form_editar_categorias"):
                st.subheader("Gerenciar Categorias")
                st.write("Adicione uma nova categoria na última linha ou marque a caixa para excluir uma que não use mais.")
                
                df_categorias = pd.DataFrame(st.session_state['categorias'], columns=['Categoria'])
                df_categorias['Excluir'] = False 
                
                col_config_cat = {
                    "Categoria": st.column_config.TextColumn("Categoria", required=True),
                    "Excluir": st.column_config.CheckboxColumn("Excluir ❌", default=False)
                }
                
                st.info("💡 **Dica:** Marque a caixa **Excluir ❌** para remover uma categoria, ou altere o nome diretamente.")

                ed_categorias = st.data_editor(
                    df_categorias,
                    num_rows="dynamic",
                    use_container_width=True,
                    hide_index=True,
                    column_config=col_config_cat
                )
                
                if st.form_submit_button("💾 Salvar Categorias", type="primary"):
                    df_categorias_salvar = ed_categorias[ed_categorias['Excluir'] == False].copy()
                    
                    novas_categorias = df_categorias_salvar['Categoria'].dropna().str.strip()
                    novas_categorias = novas_categorias[novas_categorias != ""].unique().tolist()
                    
                    st.session_state['categorias'] = novas_categorias
                    salvar_categorias_db(USER_ID, novas_categorias)
                    
                    st.success("Lista de Categorias atualizada com sucesso! banco de dados!")
                    st.rerun()

if not st.session_state['logged_in']: tela_login()
else: main_app()
