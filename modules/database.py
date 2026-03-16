import psycopg2
import pandas as pd
import hashlib
from datetime import datetime, date
import streamlit as st

# --- NOVA CONEXÃO (PostgreSQL via Streamlit Secrets) ---
def conectar():
    # Ele vai usar a mesma URL de banco de dados que o Gerenciador de Tarefas já usa
    return psycopg2.connect(st.secrets["DB_URL"])

def hash_senha(senha):
    """Criptografa a senha para segurança básica"""
    return hashlib.sha256(str(senha).encode()).hexdigest()

def inicializar_db():
    conn = conectar()
    c = conn.cursor()
    
    # 1. Tabela de Usuários (Ajustado para sintaxe Postgres: SERIAL)
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE,
                    email TEXT UNIQUE,
                    senha TEXT,
                    nome TEXT)''')

    # 2. Categorias (Já possui user_id)
    c.execute('''CREATE TABLE IF NOT EXISTS categorias (
                    id SERIAL PRIMARY KEY,
                    nome TEXT,
                    tipo TEXT,
                    user_id INTEGER)''') 

    # 3. Recorrências (Ajustado BOOLEAN/INTEGER)
    c.execute('''CREATE TABLE IF NOT EXISTS recorrencias (
                    id SERIAL PRIMARY KEY,
                    nome TEXT,
                    valor REAL,
                    dia_vencimento INTEGER,
                    categoria TEXT,
                    tipo TEXT,
                    ativo INTEGER DEFAULT 1,
                    data_limite DATE,
                    user_id INTEGER)''')

    # 4. Transações
    c.execute('''CREATE TABLE IF NOT EXISTS transacoes (
                    id SERIAL PRIMARY KEY,
                    data DATE,
                    nome TEXT,
                    valor REAL,
                    categoria TEXT,
                    tipo TEXT,
                    status TEXT,
                    origem_recorrencia_id INTEGER,
                    user_id INTEGER)''')
    
    # --- NOVO: Adiciona a coluna para salvar o arquivo de comprovante de forma segura ---
    c.execute('''ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS comprovante BYTEA''')
    
    conn.commit()
    conn.close()

# --- FUNÇÕES DE USUÁRIO (LOGIN & RECUPERAÇÃO) ---
def criar_usuario(username, email, senha, nome):
    conn = conectar()
    c = conn.cursor()
    try:
        # Postgres usa %s em vez de ?
        c.execute("INSERT INTO usuarios (username, email, senha, nome) VALUES (%s, %s, %s, %s)", 
                     (username, email, hash_senha(senha), nome))
        conn.commit()
        return "Sucesso"
    except psycopg2.IntegrityError as e:
        conn.rollback() # Necessário no Postgres em caso de erro
        erro = str(e)
        if "username" in erro:
            return "Erro: Este usuário já existe."
        elif "email" in erro:
            return "Erro: Este e-mail já está cadastrado."
        return "Erro desconhecido ao criar usuário."
    finally:
        conn.close()

def verificar_login(username, senha):
    conn = conectar()
    c = conn.cursor()
    # --- NOVO: Uso de LOWER() para ignorar letras maiúsculas e minúsculas no usuário e no e-mail ---
    c.execute("SELECT id, nome FROM usuarios WHERE (LOWER(username) = LOWER(%s) OR LOWER(email) = LOWER(%s)) AND senha = %s", 
                       (username, username, hash_senha(senha)))
    res = c.fetchone()
    conn.close()
    return res

def recuperar_senha(email):
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT username FROM usuarios WHERE email = %s", (email,))
    res = c.fetchone()
    conn.close()
    if res:
        return True, res[0]
    return False, None

# --- FUNÇÕES FINANCEIRAS ---
def processar_recorrencias(user_id):
    conn = conectar()
    c = conn.cursor()
    hoje = date.today()
    mes_atual = hoje.strftime("%Y-%m")
    
    c.execute("SELECT * FROM recorrencias WHERE user_id = %s AND ativo = 1", (user_id,))
    recorrencias = c.fetchall()
    
    for rec in recorrencias:
        rec_id, nome, valor, dia, cat, tipo, ativo, data_limite, uid = rec
        
        if data_limite:
            # Garante que data_limite é tratada corretamente seja string ou objeto date
            data_lim_str = str(data_limite)[:10]
            data_lim_obj = datetime.strptime(data_lim_str, "%Y-%m-%d").date()
            primeiro_dia_mes_atual = date(hoje.year, hoje.month, 1)
            if primeiro_dia_mes_atual > data_lim_obj:
                continue

        try:
            data_vencimento = f"{mes_atual}-{int(dia):02d}"
        except:
            from calendar import monthrange
            ultimo = monthrange(hoje.year, hoje.month)[1]
            data_vencimento = f"{mes_atual}-{ultimo:02d}"
        
        # O to_char é a versão Postgres do strftime
        c.execute("""
            SELECT count(*) FROM transacoes 
            WHERE origem_recorrencia_id = %s AND to_char(data, 'YYYY-MM') = %s AND user_id = %s
        """, (rec_id, mes_atual, user_id))
        ja_existe = c.fetchone()[0]
        
        if ja_existe == 0:
            c.execute("""
                INSERT INTO transacoes (data, nome, valor, categoria, tipo, status, origem_recorrencia_id, user_id)
                VALUES (%s, %s, %s, %s, %s, 'Pendente', %s, %s)
            """, (data_vencimento, nome, valor, cat, tipo, rec_id, user_id))
            
    conn.commit()
    conn.close()

def ler_transacoes(user_id):
    conn = conectar()
    df = pd.read_sql("SELECT * FROM transacoes WHERE user_id = %(user_id)s ORDER BY data DESC", conn, params={'user_id': user_id})
    conn.close()
    return df

def adicionar_transacao(user_id, data, nome, valor, categoria, tipo, status):
    conn = conectar()
    c = conn.cursor()
    c.execute("INSERT INTO transacoes (data, nome, valor, categoria, tipo, status, user_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                 (data, nome, valor, categoria, tipo, status, user_id))
    conn.commit()
    conn.close()

def ler_recorrencias(user_id):
    conn = conectar()
    df = pd.read_sql("SELECT * FROM recorrencias WHERE user_id = %(user_id)s", conn, params={'user_id': user_id})
    conn.close()
    return df

def atualizar_recorrencias(user_id, df_novo):
    conn = conectar()
    c = conn.cursor()
    
    if 'id' in df_novo.columns:
        ids_mantidos = df_novo['id'].dropna().astype(int).tolist()
        if ids_mantidos:
            marcadores = ','.join(['%s'] * len(ids_mantidos))
            query = f"DELETE FROM recorrencias WHERE user_id = %s AND id NOT IN ({marcadores})"
            c.execute(query, [user_id] + ids_mantidos)
        else:
            c.execute("DELETE FROM recorrencias WHERE user_id = %s", (user_id,))

    registros = df_novo.to_dict('records')
    for row in registros:
        ativo_int = 1 if row.get('ativo') == True else 0
        data_lim = row.get('data_limite')
        if pd.isna(data_lim): 
            data_lim = None
        else:
            data_lim = str(data_lim)[:10]
            
        if pd.isna(row.get('id')):
             c.execute("""
                INSERT INTO recorrencias (nome, valor, dia_vencimento, categoria, tipo, ativo, data_limite, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (row['nome'], row['valor'], row['dia_vencimento'], row['categoria'], row['tipo'], ativo_int, data_lim, user_id))
        else:
             c.execute("""
                UPDATE recorrencias 
                SET nome = %s, valor = %s, dia_vencimento = %s, categoria = %s, tipo = %s, ativo = %s, data_limite = %s
                WHERE id = %s AND user_id = %s
            """, (row['nome'], row['valor'], row['dia_vencimento'], row['categoria'], row['tipo'], 
                  ativo_int, data_lim, row['id'], user_id))
    conn.commit()
    conn.close()

# --- NOVO: LÓGICA DE CONFIRMAÇÃO COM ANEXO ---
def confirmar_transacao(transacao_id, data_real, comprovante_bytes=None):
    conn = conectar()
    c = conn.cursor()
    
    if comprovante_bytes:
        # psycopg2.Binary protege o arquivo e salva como BYTEA
        c.execute("UPDATE transacoes SET status = 'Pago', data = %s, comprovante = %s WHERE id = %s", 
                  (data_real, psycopg2.Binary(comprovante_bytes), transacao_id))
    else:
        c.execute("UPDATE transacoes SET status = 'Pago', data = %s WHERE id = %s", 
                  (data_real, transacao_id))
        
    conn.commit()
    conn.close()

# --- ATUALIZAR/EXCLUIR TRANSAÇÕES MANUAIS ---
def atualizar_transacoes(user_id, df_novo):
    conn = conectar()
    c = conn.cursor()
    
    # 1. DELETAR AS LINHAS QUE FORAM EXCLUÍDAS NA TELA
    if 'id' in df_novo.columns:
        ids_mantidos = df_novo['id'].dropna().astype(int).tolist()
        if ids_mantidos:
            marcadores = ','.join(['%s'] * len(ids_mantidos))
            query = f"DELETE FROM transacoes WHERE user_id = %s AND id NOT IN ({marcadores})"
            c.execute(query, [user_id] + ids_mantidos)
        else:
            c.execute("DELETE FROM transacoes WHERE user_id = %s", (user_id,))

    # 2. INSERIR NOVAS E ATUALIZAR AS EXISTENTES
    registros = df_novo.to_dict('records')
    
    for row in registros:
        data_val = row.get('data')
        if pd.isna(data_val):
            continue 
        
        data_str = str(data_val)[:10] 
        
        if pd.isna(row.get('id')):
             c.execute("""
                INSERT INTO transacoes (data, nome, valor, categoria, tipo, status, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (data_str, row['nome'], row['valor'], row['categoria'], row['tipo'], row['status'], user_id))
        else:
             c.execute("""
                UPDATE transacoes 
                SET data = %s, nome = %s, valor = %s, categoria = %s, tipo = %s, status = %s
                WHERE id = %s AND user_id = %s
            """, (data_str, row['nome'], row['valor'], row['categoria'], row['tipo'], row['status'], row['id'], user_id))
                  
    conn.commit()
    conn.close()

# --- GERENCIAMENTO DE CATEGORIAS POR USUÁRIO ---
def ler_categorias_db(user_id):
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT nome FROM categorias WHERE user_id = %s", (user_id,))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        padroes = ["Alimentação", "Transporte", "Moradia", "Saúde", "Lazer", "Impostos", "Receita", "Outros", "Parcelamentos", "Esportes"]
        salvar_categorias_db(user_id, padroes)
        return padroes
        
    return [row[0] for row in rows]

def salvar_categorias_db(user_id, categorias_lista):
    conn = conectar()
    c = conn.cursor()
    
    c.execute("DELETE FROM categorias WHERE user_id = %s", (user_id,))
    
    for cat in categorias_lista:
        if cat and cat.strip() != "":
            c.execute("INSERT INTO categorias (nome, user_id) VALUES (%s, %s)", (cat.strip(), user_id))
            
    conn.commit()
    conn.close()
