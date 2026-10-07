from datetime import datetime
import os
import sqlite3
import pandas as pd

# Importações do módulo do plano de contas
from gerenciador_planov12 import (
    buscar_conta_por_resumida,
    inicializar_banco_plano_contas,
    listar_empresas,
    menu_plano_contas,
    sanitizar_cnpj,
    validar_empresa_existente,
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
# INICIALIZAÇÃO DO BANCO CONTÁBIL E CÁLCULO DE SALDO
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


def calcular_saldo_conta(cnpj_limpo, codigo_conta, natureza_conta):
  """Calcula o saldo atualizado da conta com base nos lançamentos realizados."""
  try:
    conn = conectar_empresa_especifica(cnpj_limpo)
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT 
                SUM(CASE WHEN tipo = 'D' THEN valor ELSE 0 END) as total_d,
                SUM(CASE WHEN tipo = 'C' THEN valor ELSE 0 END) as total_c
            FROM partidas
            WHERE conta_codigo = ?
        """,
        (codigo_conta,),
    )

    res = cursor.fetchone()
    conn.close()

    total_d = res[0] if res[0] else 0.0
    total_c = res[1] if res[1] else 0.0

    if natureza_conta == "D":
      saldo = total_d - total_c
    else:
      saldo = total_c - total_d

    nat_str = "D" if saldo >= 0 else "C"
    return abs(saldo), nat_str
  except sqlite3.Error:
    return 0.0, natureza_conta


# ============================================
# NOVO FLUXO DE LANÇAMENTOS E LOTES
# ============================================


def exibir_quadro_lote(conn, id_lote):
  """Exibe um quadro formatado com os lançamentos cadastrados no lote e seus totais."""
  cursor = conn.cursor()
  cursor.execute(
      """
        SELECT 
            p.id_partida,
            lan.data_lancamento,
            p.conta_codigo,
            p.tipo,
            p.valor,
            lan.historico
        FROM partidas p
        INNER JOIN lancamentos lan ON p.id_lancamento = lan.id_lancamento
        WHERE lan.id_lote = ?
        ORDER BY p.id_partida ASC
    """,
      (id_lote,),
  )

  partidas = cursor.fetchall()

  if not partidas:
    print("\n[ NENHUM LANÇAMENTO REGISTRADO NESTE LOTE ]\n")
    return 0.0, 0.0

  colunas = ["Item", "Data", "Conta", "D/C", "Valor (R$)", "Histórico"]
  df = pd.DataFrame(partidas, columns=colunas)

  # Formatação dos valores em moeda
  df["Valor (R$)"] = df["Valor (R$)"].apply(lambda v: f"R$ {v:,.2f}")

  total_debito = sum(
      p[4] for p in partidas if p[3] == "D"
  )  # p[4] é o valor, p[3] é o tipo
  total_credito = sum(p[4] for p in partidas if p[3] == "C")

  print(
      f"\n====================== RESUMO DO LOTE Nº {id_lote}"
      " ======================"
  )
  print(df.to_string(index=False))
  print("------------------------------------------------------------------")
  print(
      f" TOTAL DÉBITOS : R$ {total_debito:,.2f} | TOTAL CRÉDITOS: R$"
      f" {total_credito:,.2f}"
  )
  print(f" DIFERENÇA     : R$ {abs(total_debito - total_credito):,.2f}")
  print(
      "==================================================================\n"
  )

  return total_debito, total_credito


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
      "Informe uma descrição para o Lote (ex: Movimento Folha 03/2026): "
  ).strip()

  conn = conectar_empresa_especifica(cnpj_limpo)
  cursor = conn.cursor()

  # 1. AUTO NUMERAÇÃO E ATRIBUIÇÃO AUTOMÁTICA DO LOTE
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
      f"\n✅ LOTE Nº {id_lote} CRIADO COM SUCESSO PARA {razao_social}! STATUS:"
      " EM ABERTO."
  )

  data_mov = input("Informe a Data Padrão do Lote (DD/MM/AAAA): ").strip()

  while True:
    print(
        f"\n--- [ LOTE Nº {id_lote} ] Adicionar Partida (Digite 'FIM' para"
        " encerrar) ---"
    )

    # 2. SELEÇÃO DO TIPO D OU C EM PRIMEIRO LUGAR
    tipo = (
        input("Tipo da Operação (D = Débito / C = Crédito / FIM): ")
        .strip()
        .upper()
    )

    if tipo == "FIM":
      tot_d, tot_c = exibir_quadro_lote(conn, id_lote)
      diferenca = abs(tot_d - tot_c)

      if diferenca < 0.001 and tot_d > 0:
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
        break
      else:
        print(
            f"❌ O LOTE Nº {id_lote} NÃO PODE SER ENCERRADO! O lote está"
            f" desbalanceado (Diferença: R$ {diferenca:,.2f})."
        )
        print("💡 Faça os lançamentos necessários para zerar a diferença.")
        continue

    if tipo not in ["D", "C"]:
      print("⚠️ Tipo inválido. Escolha 'D' para Débito ou 'C' para Crédito.")
      continue

    # ENTRADA DA CONTA RESUMIDA
    resumida_input = input(
        "Conta Resumida (ID) [ou 'FIM' para encerrar]: "
    ).strip()

    if resumida_input.upper() == "FIM":
      tot_d, tot_c = exibir_quadro_lote(conn, id_lote)
      diferenca = abs(tot_d - tot_c)

      if diferenca < 0.001 and tot_d > 0:
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
        break
      else:
        print(
            f"❌ O LOTE Nº {id_lote} NÃO PODE SER ENCERRADO! O lote está"
            f" desbalanceado (Diferença: R$ {diferenca:,.2f})."
        )
        continue

    if not resumida_input.isdigit():
      print("❌ Digite um número válido para a Conta Resumida.")
      continue

    resumida = int(resumida_input)
    dados_conta = buscar_conta_por_resumida(cnpj_limpo, resumida)

    if not dados_conta:
      print(f"❌ Conta Resumida ID '{resumida}' não existe no Plano de Contas.")
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
          f"❌ A conta [{codigo_c}] {nome_c} é SINTÉTICA ('S'). Lançamentos são"
          " permitidos apenas em contas ANALÍTICAS ('A')."
      )
      continue

    # CÁLCULO E EXIBIÇÃO DA DESCRIÇÃO E SALDO NA MESMA LINHA
    saldo_atual, nat_saldo = calcular_saldo_conta(cnpj_limpo, codigo_c, nat_c)
    print(
        f"   📌 Conta: [{codigo_c}] {nome_c} | Saldo Atual: R$"
        f" {saldo_atual:,.2f} ({nat_saldo})"
    )

    # VALOR DO LANÇAMENTO
    try:
      valor = float(input("   Valor (R$): ").replace(",", "."))
      if valor <= 0:
        print("❌ O valor deve ser maior que zero.")
        continue
    except ValueError:
      print("❌ Valor numérico inválido.")
      continue

    # HISTÓRICO NA LINHA SEGUINTE
    historico = input("   Histórico do lançamento: ").strip()
    if not historico:
      historico = desc_lote

    # GRAVAÇÃO DO LANÇAMENTO E PARTIDA
    cursor.execute(
        """
            INSERT INTO lancamentos (id_lote, data_lancamento, historico)
            VALUES (?, ?, ?)
        """,
        (id_lote, data_mov, historico),
    )
    id_lancamento = cursor.lastrowid

    cursor.execute(
        """
            INSERT INTO partidas (id_lancamento, conta_codigo, tipo, valor)
            VALUES (?, ?, ?, ?)
        """,
        (id_lancamento, codigo_c, tipo, valor),
    )
    conn.commit()

    # QUADRO ATUALIZADO DO LOTE COM OS TOTAIS
    exibir_quadro_lote(conn, id_lote)

  conn.close()


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
        "\nInforme o Nº do Lote para ver o Diário/Lançamentos (ou ENTER para"
        " sair): "
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

  colunas = ["ID Lanç.", "Data", "Histórico", "Código Conta", "D/C", "Valor (R$)"]
  df_detalhe = pd.DataFrame(detalhes, columns=colunas)

  print(f"\n===== DETALHAMENTO DO LOTE Nº {id_lote} =====")
  print(df_detalhe.to_string(index=False))
  print("=============================================")

  exportar = (
      input("Deseja exportar este lote para Excel? (s/n): ").strip().lower()
  )
  if exportar == "s":
    nome_arq = (
        f"Lote_{id_lote}_{cnpj_limpo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )
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