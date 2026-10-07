import os
import sqlite3
from datetime import datetime
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

def conectar_empresas():
    return sqlite3.connect(BANCO_EMPRESAS)

def conectar_empresa_especifica(cnpj):
    """Cria/Conecta ao banco individual da empresa (ex: db/contabilidade_12345678000199.db)."""
    cnpj_limpo = "".join(filter(str.isalnum, cnpj))
    caminho_db = os.path.join(PASTA_DB, f"contabilidade_{cnpj_limpo}.db")
    return sqlite3.connect(caminho_db)

# ============================================
# ESTRUTURA DE TABELAS DA EMPRESA
# ============================================

def inicializar_banco_empresa(cnpj):
    """Cria as tabelas de lotes, lançamentos e partidas no banco da empresa."""
    try:
        conn = conectar_empresa_especifica(cnpj)
        cursor = conn.cursor()

        # Tabela 1: Lotes Contábeis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lotes (
                id_lote INTEGER PRIMARY KEY AUTOINCREMENT,
                data_criacao TEXT NOT NULL,
                descricao TEXT,
                status TEXT NOT NULL DEFAULT 'Em Aberto',
                data_fechamento TEXT
            )
        """)

        # Tabela 2: Lançamentos / Capa do Lançamento
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lancamentos (
                id_lancamento INTEGER PRIMARY KEY AUTOINCREMENT,
                id_lote INTEGER NOT NULL,
                data_lancamento TEXT NOT NULL,
                historico TEXT NOT NULL,
                FOREIGN KEY (id_lote) REFERENCES lotes(id_lote)
            )
        """)

        # Tabela 3: Partidas Contábeis (Débitos e Créditos)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partidas (
                id_partida INTEGER PRIMARY KEY AUTOINCREMENT,
                id_lancamento INTEGER NOT NULL,
                conta_codigo TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('D', 'C')),
                valor REAL NOT NULL,
                FOREIGN KEY (id_lancamento) REFERENCES lancamentos(id_lancamento)
            )
        """)

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Erro ao estruturar banco individual da empresa: {e}")

# ============================================
# CONSULTA DE EMPRESAS
# ============================================

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
# OPERAÇÃO DE LANÇAMENTOS E LOTES
# ============================================

def novo_lote_contabil():
    empresas = listar_empresas()
    if not empresas:
        return

    cnpj = input("Informe o CNPJ da empresa desejada: ").strip()

    # Valida se a empresa existe
    conn_e = conectar_empresas()
    cursor_e = conn_e.cursor()
    cursor_e.execute(
        "SELECT razao_social FROM empresas WHERE cnpj = ?", (cnpj,)
    )
    emp = cursor_e.fetchone()
    conn_e.close()

    if not emp:
        print("❌ Empresa não encontrada.")
        return

    razao_social = emp[0]
    inicializar_banco_empresa(cnpj)

    # Criação do Lote Auto-Numérico
    desc_lote = input(
        "Informe uma descrição/origem para o Lote (ex: Movimento Folha"
        " 03/2026): "
    ).strip()

    conn = conectar_empresa_especifica(cnpj)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO lotes (data_criacao, descricao, status)
        VALUES (?, ?, 'Em Aberto')
    """,
        (datetime.now().strftime("%d/%m/%Y %H:%M"), desc_lote),
    )

    id_lote = cursor.lastrowid
    conn.commit()

    print(
        f"\n✅ LOTE Nº {id_lote} criado com sucesso para {razao_social}! Status:"
        " Em Aberto."
    )

    # Início da inserção de lançamentos no Lote
    data_mov = input("Informe a data dos lançamentos (DD/MM/AAAA): ").strip()

    while True:
        print(f"\n--- Novo Lançamento no Lote Nº {id_lote} ---")
        historico = input(
            "Histórico do Lançamento (ou 'FIM' para encerrar o lote): "
        ).strip()

        if historico.upper() == "FIM":
            break

        cursor.execute(
            """
            INSERT INTO lancamentos (id_lote, data_lancamento, historico)
            VALUES (?, ?, ?)
        """,
            (id_lote, data_mov, historico),
        )

        id_lancamento = cursor.lastrowid

        # Inserção das Partidas (Débitos e Créditos)
        print(
            " -> Cadastre as partidas do lançamento (múltiplos débitos e"
            " créditos):"
        )

        while True:
            tipo = (
                input("Tipo da partida (D = Débito / C = Crédito): ")
                .strip()
                .upper()
            )
            if tipo not in ["D", "C"]:
                print("⚠️ Digite apenas D para Débito ou C para Crédito.")
                continue

            conta = input("Código/Nome da Conta Contábil: ").strip()
            try:
                valor = float(
                    input("Valor da Partida (R$): ").replace(",", ".")
                )
            except ValueError:
                print("❌ Valor numérico inválido.")
                continue

            cursor.execute(
                """
                INSERT INTO partidas (id_lancamento, conta_codigo, tipo, valor)
                VALUES (?, ?, ?, ?)
            """,
                (id_lancamento, conta, tipo, valor),
            )

            conn.commit()

            mais_partida = (
                input("Adicionar outra partida neste lançamento? (s/n): ")
                .strip()
                .lower()
            )
            if mais_partida != "s":
                break

    # ============================================
    # VALIDAÇÃO DO FECHAMENTO DO LOTE
    # ============================================
    validar_e_fechar_lote(conn, id_lote)
    conn.close()

def validar_e_fechar_lote(conn, id_lote):
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            SUM(CASE WHEN p.tipo = 'D' THEN p.valor ELSE 0 END) as total_debito,
            SUM(CASE WHEN p.tipo = 'C' THEN p.valor ELSE 0 END) as total_credito
        FROM partidas p
        INNER JOIN lancamentos l ON p.id_lancamento = l.id_lancamento
        WHERE l.id_lote = ?
    """,
        (id_lote,),
    )

    resultado = cursor.fetchone()
    total_debito = resultado[0] if resultado[0] else 0.0
    total_credito = resultado[1] if resultado[1] else 0.0

    diferenca = abs(total_debito - total_credito)

    print(f"\n================ RESUMO DO LOTE Nº {id_lote} ================")
    print(f" Total de Débitos:  R$ {total_debito:,.2f}")
    print(f" Total de Créditos: R$ {total_credito:,.2f}")
    print(f" Diferença:         R$ {diferenca:,.2f}")
    print("==========================================================")

    # Validação de consistência com tolerância para arredondamentos flutuantes
    if diferenca < 0.001 and total_debito > 0:
        cursor.execute(
            """
            UPDATE lotes
            SET status = 'Fechado', data_fechamento = ?
            WHERE id_lote = ?
        """,
            (datetime.now().strftime("%d/%m/%Y %H:%M"), id_lote),
        )
        conn.commit()
        print(f"✅ LOTE Nº {id_lote} VALIDADO E FECHADO COM SUCESSO!")
    else:
        print(
            f"❌ O LOTE Nº {id_lote} ESTÁ DESBALANCEADO! Permanece com status"
            " 'Em Aberto'."
        )
        print("💡 Ajuste os lançamentos antes de fechar a escrituração.")

# ============================================
# CONSULTA E EXPORTAÇÃO DE RAZONETE / LOTE
# ============================================

def consultar_lotes_empresa():
    empresas = listar_empresas()
    if not empresas:
        return

    cnpj = input("Informe o CNPJ da empresa para consultar: ").strip()

    try:
        conn = conectar_empresa_especifica(cnpj)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT l.id_lote, l.data_criacao, l.descricao, l.status,
                   SUM(CASE WHEN p.tipo = 'D' THEN p.valor ELSE 0 END) as total_lote
            FROM lotes l
            LEFT JOIN lancamentos lan ON l.id_lote = lan.id_lote
            LEFT JOIN partidas p ON lan.id_lancamento = p.id_lancamento
            GROUP BY l.id_lote
            ORDER BY l.id_lote DESC
        """)

        dados = cursor.fetchall()

        if not dados:
            print("⚠️ Nenhum lote contábil registrado para esta empresa.")
            conn.close()
            return

        colunas = [
            "Nº Lote",
            "Data Criação",
            "Descrição",
            "Status",
            "Valor Total (R$)",
        ]
        df = pd.DataFrame(dados, columns=colunas)

        print("\n===== LOTES CONTÁBEIS DA EMPRESA =====")
        print(df.to_string(index=False))
        print("======================================")

        id_detalhe = input(
            "\nInforme o Nº do Lote para ver o Diário/Lançamentos (ou ENTER"
            " para sair): "
        ).strip()
        if id_detalhe:
            exibir_detalhes_lote(cursor, id_detalhe, cnpj)

        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Erro ao acessar o banco da empresa: {e}")

def exibir_detalhes_lote(cursor, id_lote, cnpj):
    cursor.execute(
        """
        SELECT lan.id_lancamento, lan.data_lancamento, lan.historico, p.conta_codigo, p.tipo, p.valor
        FROM lancamentos lan
        INNER JOIN partidas p ON lan.id_lancamento = p.id_lancamento
        WHERE lan.id_lote = ?
        ORDER BY lan.id_lancamento, p.tipo DESC
    """,
        (id_lote,),
    )

    detalhes = cursor.fetchall()
    if not detalhes:
        print("⚠️ Nenhum detalhe encontrado para este lote.")
        return

    colunas = ["ID Lanç.", "Data", "Histórico", "Conta", "D/C", "Valor (R$)"]
    df_detalhe = pd.DataFrame(detalhes, columns=colunas)

    print(f"\n===== DETALHAMENTO DO LOTE Nº {id_lote} =====")
    print(df_detalhe.to_string(index=False))
    print("=============================================")

    exportar = (
        input("Deseja exportar este lote para Excel? (s/n): ").strip().lower()
    )
    if exportar == "s":
        cnpj_limpo = "".join(filter(str.isalnum, cnpj))
        nome_arq = f"Lote_{id_lote}_{cnpj_limpo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        caminho = os.path.join(PASTA_EXCEL, nome_arq)
        df_detalhe.to_excel(caminho, index=False, engine="openpyxl")
        print(f"✅ Arquivo exportado com sucesso em: {caminho}")

# ============================================
# MENU PRINCIPAL
# ============================================

def menu():
    while True:
        print("""
========= MENU DE CONTABILIZAÇÃO =========
1 - Criar Novo Lote e Lançamentos Contábeis
2 - Consultar / Visualizar Lotes da Empresa
0 - Sair
==========================================
""")

        opc = input("Opção: ").strip()

        if opc == "1":
            novo_lote_contabil()
        elif opc == "2":
            consultar_lotes_empresa()
        elif opc == "0":
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    menu()