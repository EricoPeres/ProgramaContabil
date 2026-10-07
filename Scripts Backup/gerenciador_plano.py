import os
import sqlite3
import pandas as pd

# ============================================
# CONFIGURAÇÃO DE DIRETÓRIOS E BANCOS
# ============================================

DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_DB = os.path.join(DIRETORIO_BASE, "db")
PASTA_EXCEL = os.path.join(DIRETORIO_BASE, "excel")

os.makedirs(PASTA_DB, exist_ok=True)
os.makedirs(PASTA_EXCEL, exist_ok=True)

BANCO_EMPRESAS = os.path.join(PASTA_DB, "empresas.db")

def sanitizar_cnpj(cnpj):
    """Remove pontuações e caracteres especiais do CNPJ."""
    return "".join(filter(str.isalnum, str(cnpj)))

def conectar_empresas():
    return sqlite3.connect(BANCO_EMPRESAS)

def conectar_plano_contas(cnpj):
    """Conecta ao banco do Plano de Contas da empresa (plano_CNPJ.db)."""
    cnpj_limpo = sanitizar_cnpj(cnpj)
    caminho_db = os.path.join(PASTA_DB, f"plano_{cnpj_limpo}.db")
    return sqlite3.connect(caminho_db)

# ============================================
# CONSULTA E VALIDAÇÃO DE EMPRESAS
# ============================================

def validar_empresa_existente(cnpj):
    """Verifica se a empresa existe no empresas.db comparando CNPJ limpo ou formatado."""
    cnpj_limpo = sanitizar_cnpj(cnpj)
    if not cnpj_limpo:
        return None

    try:
        conn = conectar_empresas()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT cnpj, razao_social 
            FROM empresas 
            WHERE REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '') = ? 
               OR cnpj = ?
        """,
            (cnpj_limpo, cnpj),
        )

        empresa = cursor.fetchone()
        conn.close()
        return empresa  # Retorna a tupla (cnpj, razao_social) ou None
    except sqlite3.Error as e:
        print(f"❌ Erro ao validar empresa no banco: {e}")
        return None

def listar_empresas():
    try:
        conn = conectar_empresas()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT cnpj, razao_social FROM empresas ORDER BY razao_social"
        )
        empresas = cursor.fetchall()
        conn.close()

        if not empresas:
            print("⚠️ Nenhuma empresa encontrada em 'empresas.db'.")
            return []

        print("\n===== SELEÇÃO DE EMPRESA =====")
        for e in empresas:
            print(f"CNPJ: {e[0]} | Razão Social: {e[1]}")
        print("===============================\n")

        return empresas
    except sqlite3.Error as e:
        print(f"❌ Erro ao ler empresas: {e}")
        return []

# ============================================
# BANCO DE DADOS DO PLANO DE CONTAS
# ============================================

def inicializar_banco_plano_contas(cnpj):
    """Cria a tabela do plano de contas no arquivo 'plano_CNPJ.db'."""
    try:
        conn = conectar_plano_contas(cnpj)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plano_contas (
                conta_resumida INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                natureza TEXT NOT NULL CHECK(natureza IN ('D', 'C')),
                tipo TEXT NOT NULL CHECK(tipo IN ('A', 'S'))
            )
        """)

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Erro ao estruturar o Plano de Contas: {e}")

def buscar_conta_por_resumida(cnpj, resumida):
    """Verifica se a Conta Resumida existe e retorna seus dados."""
    conn = conectar_plano_contas(cnpj)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT conta_resumida, codigo, nome, natureza, tipo 
        FROM plano_contas 
        WHERE conta_resumida = ?
    """,
        (resumida,),
    )
    conta = cursor.fetchone()
    conn.close()
    return conta

# ============================================
# FUNÇÕES DE GESTÃO DO PLANO DE CONTAS
# ============================================

def cadastrar_conta_plano(cnpj=None):
    if not cnpj:
        empresas = listar_empresas()
        if not empresas:
            return
        cnpj = input(
            "Informe o CNPJ da empresa para gerenciar o Plano de Contas: "
        ).strip()

    empresa = validar_empresa_existente(cnpj)
    if not empresa:
        print("❌ Empresa não encontrada.")
        return

    cnpj_limpo = sanitizar_cnpj(empresa[0])
    razao_social = empresa[1]

    inicializar_banco_plano_contas(cnpj_limpo)

    print(f"\n--- CADASTRO DE CONTA NO PLANO DE CONTAS ({razao_social}) ---")
    codigo = input("Código da Conta (ex: 1.1.1.01.001): ").strip()
    nome = input("Nome/Descrição da Conta: ").strip()

    # Seleção da Natureza (D/C)
    print("Natureza da Conta:")
    print(" 1 - Devedora (D)")
    print(" 2 - Credora (C)")
    opc_nat = input("Opção (1/2): ").strip()

    if opc_nat == "1":
        natureza = "D"
    elif opc_nat == "2":
        natureza = "C"
    else:
        print("❌ Natureza inválida. Operação cancelada.")
        return

    # Seleção do Tipo (A/S)
    print("Tipo da Conta:")
    print(" 1 - Analítica (A) [Recebe lançamentos]")
    print(" 2 - Sintética (S) [Totalizadora]")
    opc_tipo = input("Opção (1/2): ").strip()

    if opc_tipo == "1":
        tipo = "A"
    elif opc_tipo == "2":
        tipo = "S"
    else:
        print("❌ Tipo inválido. Operação cancelada.")
        return

    try:
        conn = conectar_plano_contas(cnpj_limpo)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO plano_contas (codigo, nome, natureza, tipo)
            VALUES (?, ?, ?, ?)
        """,
            (codigo, nome, natureza, tipo),
        )

        conta_resumida = cursor.lastrowid
        conn.commit()
        conn.close()

        print("\n✅ CONTA CADASTRADA COM SUCESSO!")
        print(f" 🔹 Código: {codigo}")
        print(f" 🔹 Nome: {nome}")
        print(f" 🔹 Natureza: {natureza}")
        print(f" 🔹 Tipo: {tipo} ({'Analítica' if tipo == 'A' else 'Sintética'})")
        print(f" 📌 Conta Resumida (ID Automático): {conta_resumida}\n")

    except sqlite3.IntegrityError:
        print(
            f"❌ Erro: O código de conta '{codigo}' já está cadastrado neste"
            " plano."
        )
    except sqlite3.Error as e:
        print(f"❌ Erro ao gravar conta no banco: {e}")

def listar_plano_contas(cnpj=None):
    if not cnpj:
        empresas = listar_empresas()
        if not empresas:
            return
        cnpj = input(
            "Informe o CNPJ da empresa para visualizar o Plano: "
        ).strip()

    empresa = validar_empresa_existente(cnpj)
    if not empresa:
        print("❌ Empresa não encontrada.")
        return

    cnpj_limpo = sanitizar_cnpj(empresa[0])
    inicializar_banco_plano_contas(cnpj_limpo)

    try:
        conn = conectar_plano_contas(cnpj_limpo)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT conta_resumida, codigo, nome, natureza, tipo
            FROM plano_contas
            ORDER BY codigo
        """)

        contas = cursor.fetchall()
        conn.close()

        if not contas:
            print("⚠️ Nenhuma conta cadastrada no Plano de Contas.")
            return

        colunas = [
            "Conta Resumida",
            "Código Estruturado",
            "Nome da Conta",
            "Natureza (D/C)",
            "Tipo (A/S)",
        ]
        df = pd.DataFrame(contas, columns=colunas)

        print(f"\n===== PLANO DE CONTAS DA EMPRESA: {empresa[1]} =====")
        print(df.to_string(index=False))
        print("=====================================================\n")

    except sqlite3.Error as e:
        print(f"❌ Erro ao consultar o Plano de Contas: {e}")

def menu_plano_contas():
    empresas = listar_empresas()
    if not empresas:
        return

    cnpj = input("Informe o CNPJ da empresa para gerenciar o Plano: ").strip()
    empresa = validar_empresa_existente(cnpj)

    if not empresa:
        print("❌ Empresa não encontrada.")
        return

    cnpj_limpo = sanitizar_cnpj(empresa[0])
    print(f"\n📂 Gerenciando Plano de Contas de: {empresa[1]}")

    while True:
        print("""
--- MENU PLANO DE CONTAS ---
1 - Cadastrar Nova Conta
2 - Visualizar Plano de Contas
0 - Voltar ao Menu Anterior
----------------------------
""")
        opc = input("Opção: ").strip()

        if opc == "1":
            cadastrar_conta_plano(cnpj_limpo)
        elif opc == "2":
            listar_plano_contas(cnpj_limpo)
        elif opc == "0":
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    menu_plano_contas()