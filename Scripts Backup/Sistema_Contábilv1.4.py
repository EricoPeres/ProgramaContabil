import os
import sqlite3
from datetime import datetime
import pandas as pd

# Importa funções reutilizáveis do gerenciador do plano
from gerenciador_plano import (
    sanitizar_cnpj,
    validar_empresa_existente,
    listar_empresas,
    inicializar_banco_plano_contas,
    buscar_conta_por_resumida,
    menu_plano_contas,
)

# ============================================
# CONFIGURAÇÃO DE DIRETÓRIOS E BANCOS
# ============================================

DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_DB = os.path.join(DIRETORIO_BASE, "db")
PASTA_EXCEL = os.path.join(DIRETORIO_BASE, "excel")

def conectar_empresa_especifica(cnpj):
    """Conecta ao banco contábil da empresa (contabilidade_CNPJ.db)."""
    cnpj_limpo = sanitizar_cnpj(cnpj)
    caminho_db = os.path.join(PASTA_DB, f"contabilidade_{cnpj_limpo}.db")
    return sqlite3.connect(caminho_db)

# ============================================
# INICIALIZAÇÃO DO BANCO CONTÁBIL
# ============================================

def inicializar_banco_empresa(cnpj):
    """Cria tabelas de lotes, lançamentos e partidas no banco da empresa."""
    try:
        conn = conectar_empresa_especifica(cnpj)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lotes (
                id_lote INTEGER PRIMARY KEY AUTOINCREMENT,
                data_criacao TEXT NOT NULL,
                descricao TEXT,
                status TEXT NOT NULL DEFAULT 'Em Aberto',
                data_fechamento TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lancamentos (
                id_lancamento INTEGER PRIMARY KEY AUTOINCREMENT,
                id_lote INTEGER NOT NULL,
                data_lancamento TEXT NOT NULL,
                historico TEXT NOT NULL,
                FOREIGN KEY (id_lote) REFERENCES lotes(id_lote)
            )
        """)

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
        print(f"❌ Erro ao estruturar banco contábil da empresa: {e}")

# ============================================
# OPERAÇÃO DE LANÇAMENTOS E LOTES
# ============================================

def novo_lote_contabil():
    empresas = listar_empresas()
    if not empresas:
        return

    cnpj_input = input("Informe o CNPJ da empresa desejada: ").strip()
    empresa = validar_empresa_existente(cnpj_input)

    if not empresa:
        print("❌ Empresa não encontrada.")
        return

    cnpj_limpo = sanitizar_cnpj(empresa[0])
    razao_social = empresa[1]

    inicializar_banco_empresa(cnpj_limpo)
    inicializar_banco_plano_contas(cnpj_limpo)

    desc_lote = input(
        "Informe uma descrição/origem para o Lote (ex: Movimento Folha"
        " 03/2026): "
    ).strip()

    conn = conectar_empresa_especifica(cnpj_limpo)
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

            resumida_input = input(
                "Informe a Conta Resumida (ID) para o lançamento: "
            ).strip()

            if not resumida_input.isdigit():
                print("❌ Informe apenas o número da Conta Resumida.")
                continue

            resumida = int(resumida_input)

            # Validação do tipo de conta (Apenas Analítica 'A' é permitida)
            dados_conta = buscar_conta_por_resumida(cnpj_limpo, resumida)

            if not dados_conta:
                print(
                    f"❌ A Conta Resumida ID '{resumida}' NÃO EXISTE no Plano"
                    " de Contas!"
                )
                continue

            # dados_conta: (conta_resumida, codigo, nome, natureza, tipo)
            codigo_c, nome_c, nat_c, tipo_c = (
                dados_conta[1],
                dados_conta[2],
                dados_conta[3],
                dados_conta[4],
            )

            if tipo_c != "A":
                print(
                    f"❌ A conta [{codigo_c}] {nome_c} é SINTÉTICA (Tipo"
                    " 'S')!"
                )
                print(
                    "💡 Lançamentos contábeis são permitidos EXCLUSIVAMENTE em"
                    " Contas ANALÍTICAS ('A')."
                )
                continue

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
                (id_lancamento, codigo_c, tipo, valor),
            )

            conn.commit()
            print(
                f"   -> Partida lançada: [{codigo_c}] {nome_c} | {tipo} | R$"
                f" {valor:,.2f}"
            )

            mais_partida = (
                input("Adicionar outra partida neste lançamento? (s/n): ")
                .strip()
                .lower()
            )
            if mais_partida != "s":
                break

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

def consultar_lotes_empresa():
    empresas = listar_empresas()
    if not empresas:
        return

    cnpj_input = input("Informe o CNPJ da empresa para consultar: ").strip()
    empresa = validar_empresa_existente(cnpj_input)

    if not empresa:
        print("❌ Empresa não encontrada.")
        return

    cnpj_limpo = sanitizar_cnpj(empresa[0])

    try:
        conn = conectar_empresa_especifica(cnpj_limpo)
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

        print(f"\n===== LOTES CONTÁBEIS: {empresa[1]} =====")
        print(df.to_string(index=False))
        print("======================================")

        id_detalhe = input(
            "\nInforme o Nº do Lote para ver o Diário/Lançamentos (ou ENTER"
            " para sair): "
        ).strip()
        if id_detalhe:
            exibir_detalhes_lote(cursor, id_detalhe, cnpj_limpo)

        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Erro ao acessar o banco da empresa: {e}")

def exibir_detalhes_lote(cursor, id_lote, cnpj_limpo):
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

    colunas = [
        "ID Lanç.",
        "Data",
        "Histórico",
        "Código Conta",
        "D/C",
        "Valor (R$)",
    ]
    df_detalhe = pd.DataFrame(detalhes, columns=colunas)

    print(f"\n===== DETALHAMENTO DO LOTE Nº {id_lote} =====")
    print(df_detalhe.to_string(index=False))
    print("=============================================")

    exportar = (
        input("Deseja exportar este lote para Excel? (s/n): ").strip().lower()
    )
    if exportar == "s":
        nome_arq = f"Lote_{id_lote}_{cnpj_limpo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        caminho = os.path.join(PASTA_EXCEL, nome_arq)
        df_detalhe.to_excel(caminho, index=False, engine="openpyxl")
        print(f"✅ Arquivo exportado com sucesso em: {caminho}")

# ============================================
# MENU PRINCIPAL CONTÁBIL
# ============================================

def menu():
    while True:
        print("""
========= MENU DE CONTABILIZAÇÃO =========
1 - Gerenciar Plano de Contas (Cadastrar/Exibir)
2 - Criar Novo Lote e Lançamentos Contábeis
3 - Consultar / Visualizar Lotes da Empresa
0 - Sair
==========================================
""")

        opc = input("Opção: ").strip()

        if opc == "1":
            menu_plano_contas()
        elif opc == "2":
            novo_lote_contabil()
        elif opc == "3":
            consultar_lotes_empresa()
        elif opc == "0":
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    menu()