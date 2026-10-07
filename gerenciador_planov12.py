import csv
import os
import re
import sqlite3
import pandas as pd

DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_DB = os.path.join(DIRETORIO_BASE, "db")

if not os.path.exists(PASTA_DB):
  os.makedirs(PASTA_DB)


def sanitizar_cnpj(cnpj):
  """Remove caracteres especiais do CNPJ para uso no nome do arquivo DB."""
  return re.sub(r"\D", "", cnpj)


def conectar_banco_plano(cnpj):
  """Conecta ou cria o banco de dados do Plano de Contas da Empresa."""
  cnpj_limpo = sanitizar_cnpj(cnpj)
  caminho_db = os.path.join(PASTA_DB, f"plano_contas_{cnpj_limpo}.db")
  return sqlite3.connect(caminho_db)


def conectar_banco_empresas():
  """Conecta ao banco global de cadastro de empresas."""
  caminho_db = os.path.join(PASTA_DB, "empresas.db")
  return sqlite3.connect(caminho_db)


def inicializar_banco_plano_contas(cnpj):
  """Cria a tabela do plano de contas caso não exista."""
  conn = conectar_banco_plano(cnpj)
  cursor = conn.cursor()

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS plano_contas (
            conta_resumida INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            natureza TEXT NOT NULL CHECK(natureza IN ('D', 'C')),
            tipo TEXT NOT NULL CHECK(tipo IN ('S', 'A'))
        )
    """)

  conn.commit()
  conn.close()


def listar_empresas():
  """Listar empresas cadastradas."""
  try:
    conn = conectar_banco_empresas()
    cursor = conn.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS empresas (
                cnpj TEXT PRIMARY KEY,
                razao_social TEXT NOT NULL
            )
        """)

    cursor.execute("SELECT cnpj, razao_social FROM empresas ORDER BY razao_social")
    empresas = cursor.fetchall()
    conn.close()

    if not empresas:
      print("\n⚠️ Nenhuma empresa cadastrada no sistema.")
      return []

    print("\n========= EMPRESAS CADASTRADAS =========")
    for emp in empresas:
      print(f"CNPJ: {emp[0]} | Razão Social: {emp[1]}")
    print("========================================")
    return empresas
  except sqlite3.Error as e:
    print(f"❌ Erro ao acessar empresas: {e}")
    return []


def validar_empresa_existente(cnpj):
  cnpj_limpo = sanitizar_cnpj(cnpj)
  conn = conectar_banco_empresas()
  cursor = conn.cursor()

  cursor.execute(
      "SELECT cnpj, razao_social FROM empresas WHERE REPLACE(REPLACE(REPLACE(cnpj,"
      " '.', ''), '/', ''), '-', '') = ?",
      (cnpj_limpo,),
  )

  empresa = cursor.fetchone()
  conn.close()
  return empresa


def buscar_conta_por_resumida(cnpj, conta_resumida):
  """Busca conta específica usando o código de conta resumida (autonumeração)."""
  conn = conectar_banco_plano(cnpj)
  cursor = conn.cursor()

  cursor.execute(
      """
        SELECT conta_resumida, codigo, nome, natureza, tipo
        FROM plano_contas
        WHERE conta_resumida = ?
    """,
      (conta_resumida,),
  )

  conta = cursor.fetchone()
  conn.close()
  return conta


def cadastrar_conta_manual():
  empresas = listar_empresas()
  if not empresas:
    return

  cnpj_input = input("Informe o CNPJ da empresa desejada: ").strip()
  empresa = validar_empresa_existente(cnpj_input)

  if not empresa:
    print("❌ Empresa não encontrada.")
    return

  cnpj_limpo = sanitizar_cnpj(empresa[0])
  inicializar_banco_plano_contas(cnpj_limpo)

  print(f"\n--- Novo Cadastro de Conta ({empresa[1]}) ---")
  codigo = input("Código Estruturado (ex: 1.1.1.01): ").strip()
  nome = input("Nome/Descrição da Conta: ").strip()

  natureza = (
      input("Natureza (D = Devedora / C = Credora): ").strip().upper()
  )
  while natureza not in ["D", "C"]:
    print("⚠️ Natureza inválida! Digite 'D' ou 'C'.")
    natureza = (
        input("Natureza (D = Devedora / C = Credora): ").strip().upper()
    )

  tipo = input("Tipo (S = Sintética / A = Analítica): ").strip().upper()
  while tipo not in ["S", "A"]:
    print("⚠️ Tipo inválido! Digite 'S' ou 'A'.")
    tipo = input("Tipo (S = Sintética / A = Analítica): ").strip().upper()

  try:
    conn = conectar_banco_plano(cnpj_limpo)
    cursor = conn.cursor()

    cursor.execute(
        """
            INSERT INTO plano_contas (codigo, nome, natureza, tipo)
            VALUES (?, ?, ?, ?)
        """,
        (codigo, nome, natureza, tipo),
    )

    resumida = cursor.lastrowid
    conn.commit()
    conn.close()

    print(
        f"✅ Conta cadastrada com sucesso! Conta Resumida atribuída:"
        f" [{resumida}]"
    )
  except sqlite3.IntegrityError:
    print(f"❌ Erro: O código contábil '{codigo}' já está cadastrado.")
  except sqlite3.Error as e:
    print(f"❌ Erro ao cadastrar conta: {e}")


# ============================================
# IMPORTAÇÃO DO PLANO DE CONTAS VIA CSV
# ============================================


def importar_plano_contas_csv():
  empresas = listar_empresas()
  if not empresas:
    return

  cnpj_input = input("Informe o CNPJ da empresa desejada: ").strip()
  empresa = validar_empresa_existente(cnpj_input)

  if not empresa:
    print("❌ Empresa não encontrada.")
    return

  cnpj_limpo = sanitizar_cnpj(empresa[0])
  inicializar_banco_plano_contas(cnpj_limpo)

  caminho_csv = input(
      "\nInforme o caminho do arquivo CSV (ex: plano.csv): "
  ).strip()
  caminho_csv = caminho_csv.replace('"', "").replace("'", "")

  if not os.path.exists(caminho_csv):
    print(f"❌ Arquivo não encontrado no caminho informado: '{caminho_csv}'")
    return

  # Tenta ler o arquivo testando encodings comuns (UTF-8, Latin-1, CP1252)
  encodings_suportados = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
  encoding_detectado = None
  delimitador = ","

  for enc in encodings_suportados:
    try:
      with open(caminho_csv, mode="r", encoding=enc) as file:
        primeira_linha = file.readline()
        delimitador = ";" if ";" in primeira_linha else ","
        encoding_detectado = enc
        break
    except UnicodeDecodeError:
      continue

  if not encoding_detectado:
    print(
        "❌ Não foi possível identificar a codificação do arquivo CSV."
        " Verifique o formato do arquivo."
    )
    return

  try:
    with open(
        caminho_csv, mode="r", encoding=encoding_detectado
    ) as file:
      reader = csv.DictReader(file, delimiter=delimitador)

      # Normaliza os nomes das colunas
      colunas = [c.strip().lower() for c in reader.fieldnames]

      # VALIDAÇÃO DO CABEÇALHO OBRIGATÓRIO
      colunas_esperadas = ["codigo", "nome", "natureza", "tipo"]
      for col in colunas_esperadas:
        if col not in colunas:
          print(
              f"❌ Arquivo CSV inválido! A primeira linha deve conter as"
              f" colunas: {', '.join(colunas_esperadas)}"
          )
          return

      conn = conectar_banco_plano(cnpj_limpo)
      cursor = conn.cursor()

      contas_importadas = 0
      erros = 0

      print(
          "\n⏳ Processando importação (Codificação detectada:"
          f" {encoding_detectado})..."
      )

      for num_linha, row in enumerate(reader, start=2):
        dados = {k.strip().lower(): v.strip() for k, v in row.items()}

        codigo = dados.get("codigo", "")
        nome = dados.get("nome", "")
        natureza = dados.get("natureza", "").upper()
        tipo = dados.get("tipo", "").upper()

        if not codigo or not nome:
          print(
              f"⚠️ Linha {num_linha}: Código ou Nome ausentes. Linha ignorada."
          )
          erros += 1
          continue

        if natureza not in ["D", "C"]:
          print(
              f"⚠️ Linha {num_linha} (Código {codigo}): Natureza '{natureza}'"
              " inválida (Deve ser 'D' ou 'C'). Linha ignorada."
          )
          erros += 1
          continue

        if tipo not in ["S", "A"]:
          print(
              f"⚠️ Linha {num_linha} (Código {codigo}): Tipo '{tipo}' inválido"
              " (Deve ser 'S' ou 'A'). Linha ignorada."
          )
          erros += 1
          continue

        try:
          cursor.execute(
              """
                        INSERT INTO plano_contas (codigo, nome, natureza, tipo)
                        VALUES (?, ?, ?, ?)
                    """,
              (codigo, nome, natureza, tipo),
          )
          contas_importadas += 1
        except sqlite3.IntegrityError:
          print(
              f"⚠️ Linha {num_linha}: Código '{codigo}' já cadastrado. Ignorado."
          )
          erros += 1

      conn.commit()
      conn.close()

      print(f"\n✅ IMPORTAÇÃO CONCLUÍDA PARA: {empresa[1]}")
      print(f"   📌 Contas cadastradas: {contas_importadas}")
      if erros > 0:
        print(f"   ⚠️ Registros ignorados / com erro: {erros}")

  except Exception as e:
    print(f"❌ Ocorreu um erro ao processar o arquivo CSV: {e}")


def exibir_plano_contas():
  empresas = listar_empresas()
  if not empresas:
    return

  cnpj_input = input("Informe o CNPJ da empresa para exibir o Plano: ").strip()
  empresa = validar_empresa_existente(cnpj_input)

  if not empresa:
    print("❌ Empresa não encontrada.")
    return

  cnpj_limpo = sanitizar_cnpj(empresa[0])

  try:
    conn = conectar_banco_plano(cnpj_limpo)
    cursor = conn.cursor()

    cursor.execute("""
            SELECT conta_resumida, codigo, nome, natureza, tipo
            FROM plano_contas
            ORDER BY codigo ASC
        """)

    contas = cursor.fetchall()
    conn.close()

    if not contas:
      print(f"\n⚠️ Nenhum plano de contas cadastrado para {empresa[1]}.")
      return

    colunas = [
        "ID Resumida",
        "Código Estruturado",
        "Descrição da Conta",
        "Nat.",
        "Tipo",
    ]
    df = pd.DataFrame(contas, columns=colunas)

    print(f"\n===== PLANO DE CONTAS: {empresa[1]} =====")
    print(df.to_string(index=False))
    print("==========================================")

  except sqlite3.Error as e:
    print(f"❌ Erro ao acessar o banco de dados: {e}")


def menu_plano_contas():
  while True:
    print("""
===== GERENCIAMENTO DO PLANO DE CONTAS =====
1 - Cadastrar Conta Manualmente
2 - Importar Plano de Contas via Arquivo CSV
3 - Exibir Plano de Contas da Empresa
0 - Voltar ao Menu Principal
===========================================
""")

    opc = input("Opção: ").strip()

    if opc == "1":
      cadastrar_conta_manual()
    elif opc == "2":
      importar_plano_contas_csv()
    elif opc == "3":
      exibir_plano_contas()
    elif opc == "0":
      break
    else:
      print("Opção inválida.")


if __name__ == "__main__":
  menu_plano_contas()