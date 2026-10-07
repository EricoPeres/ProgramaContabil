from datetime import datetime
import os
import re
import sqlite3
import pandas as pd

# =========================================================
# CONFIGURAÇÃO DE DIRETÓRIOS E BANCOS DE DADOS
# =========================================================
DB_DIR = "db"
XLSX_DIR = "Excel"

EMPRESA_DB = os.path.join(DB_DIR, "empresas.db")
HISTORICO_DB = os.path.join(DB_DIR, "historico_presumido.db")


# ---------------------------------------------------------
#                 FUNÇÕES DE CONEXÃO
# ---------------------------------------------------------
def conectar_empresas():
    return sqlite3.connect(EMPRESA_DB)

def conectar_historico():
    # Garantir que a pasta /db existe antes de conectar
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(HISTORICO_DB)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_mensal (
            cnpj TEXT,
            empresa TEXT,
            mes INTEGER,
            ano INTEGER,
            faturamento REAL,
            pis REAL,
            cofins REAL,
            total_impostos REAL,
            data_calculo TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_trimestral (
            cnpj TEXT,
            empresa TEXT,
            trimestre TEXT,
            ano INTEGER,
            faturamento REAL,
            base_irpj REAL,
            base_csll REAL,
            irpj REAL,
            csll REAL,
            total_impostos REAL,
            data_calculo TEXT
        )
    """)

    conn.commit()
    return conn

# ---------------------------------------------------------
#                     UTILITÁRIOS
# ---------------------------------------------------------

def sanitize_filename(s: str) -> str:
    if s is None:
        return ""
    s = s.replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9\-_]", "", s)

# ---------------------------------------------------------
#       LISTAR EMPRESAS LUCRO PRESUMIDO
# ---------------------------------------------------------

def listar_empresas_lucro_presumido():
    if not os.path.exists(EMPRESA_DB):
        print(
            "⚠️ Banco de empresas não encontrado. Cadastre uma empresa primeiro."
        )
        return []

    conn = conectar_empresas()
    cur = conn.cursor()
    cur.execute("""
        SELECT cnpj, razao_social, atividade
        FROM empresas
        WHERE regime_tributario = 'Lucro Presumido'
    """)
    empresas = cur.fetchall()
    conn.close()
    return empresas

# ---------------------------------------------------------
#               CÁLCULOS MENSAL / TRIMESTRAL
# ---------------------------------------------------------

def calcular_mensal_lp(faturamento):
    pis = faturamento * 0.0065
    cofins = faturamento * 0.03
    total = pis + cofins
    return {"pis": pis, "cofins": cofins, "total": total}

def calcular_trimestral_lp(faturamento, atividade):
    presuncoes = {
        "Comércio": {"irpj": 0.08, "csll": 0.12},
        "Indústria": {"irpj": 0.08, "csll": 0.12},
        "Serviços": {"irpj": 0.32, "csll": 0.32},
    }

    # Verifica se a atividade é válida no dicionário
    taxas = presuncoes.get(atividade, {"irpj": 0.32, "csll": 0.32})

    base_irpj = faturamento * taxas["irpj"]
    base_csll = faturamento * taxas["csll"]

    # Alíquota normal de IRPJ (15%)
    irpj = base_irpj * 0.15

    # Adicional de IRPJ (10% sobre o que exceder R$ 60.000,00 na BASE no trimestre)
    if base_irpj > 60000:
        adicional_irpj = (base_irpj - 60000) * 0.10
        irpj += adicional_irpj

    # CSLL (9%)
    csll = base_csll * 0.09
    total = irpj + csll

    return {
        "base_irpj": base_irpj,
        "base_csll": base_csll,
        "irpj": irpj,
        "csll": csll,
        "total": total,
    }

# ---------------------------------------------------------
#               EXECUTAR CÁLCULO MENSAL
# ---------------------------------------------------------

def calculo_mensal():
    empresas = listar_empresas_lucro_presumido()
    if not empresas:
        print("Nenhuma empresa cadastrada no Lucro Presumido.")
        return

    print("\n=== EMPRESAS (LUCRO PRESUMIDO) ===")
    for i, e in enumerate(empresas, 1):
        print(f"{i}. {e[1]} | CNPJ: {e[0]} | Atividade: {e[2]}")

    try:
        escolha = int(input("\nEscolha a empresa: ")) - 1
    except ValueError:
        print("Opção inválida.")
        return

    if escolha < 0 or escolha >= len(empresas):
        print("Empresa inválida.")
        return

    cnpj, nome, atividade = empresas[escolha]

    try:
        mes = int(input("Mês (1-12): "))
        ano = int(input("Ano: "))
        faturamento = float(input("Faturamento do mês: ").replace(",", "."))
    except ValueError:
        print("Entrada inválida!")
        return

    resultados = calcular_mensal_lp(faturamento)

    print("\n=== RESULTADO MENSAL (PIS / COFINS) ===")
    print(f"PIS (0.65%): R$ {resultados['pis']:.2f}")
    print(f"COFINS (3.00%): R$ {resultados['cofins']:.2f}")
    print(f"TOTAL MENSAL: R$ {resultados['total']:.2f}")

    conn = conectar_historico()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO historico_mensal VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            cnpj,
            nome,
            mes,
            ano,
            faturamento,
            resultados["pis"],
            resultados["cofins"],
            resultados["total"],
            datetime.now().strftime("%d/%m/%Y %H:%M"),
        ),
    )
    conn.commit()
    conn.close()

    print("\n💾 Cálculo salvo no histórico.")

# ---------------------------------------------------------
#            EXECUTAR CÁLCULO TRIMESTRAL
# ---------------------------------------------------------

def calculo_trimestral():
    empresas = listar_empresas_lucro_presumido()
    if not empresas:
        print("Nenhuma empresa cadastrada.")
        return

    print("\n=== EMPRESAS (LUCRO PRESUMIDO) ===")
    for i, e in enumerate(empresas, 1):
        print(f"{i}. {e[1]} | CNPJ: {e[0]} | Atividade: {e[2]}")

    try:
        escolha = int(input("\nEscolha a empresa: ")) - 1
    except ValueError:
        print("Opção inválida.")
        return

    if escolha < 0 or escolha >= len(empresas):
        print("Empresa inválida.")
        return

    cnpj, nome, atividade = empresas[escolha]

    try:
        trimestre = int(input("Trimestre (1-4): "))
        ano = int(input("Ano: "))
    except ValueError:
        print("Entrada inválida.")
        return

    if trimestre not in [1, 2, 3, 4]:
        print("Trimestre inválido! Escolha um valor entre 1 e 4.")
        return

    # Dicionário mapeando cada trimestre para seus respectivos meses
    meses_por_trimestre = {
        1: (1, 2, 3),
        2: (4, 5, 6),
        3: (7, 8, 9),
        4: (10, 11, 12)
    }
    meses_alvo = meses_por_trimestre[trimestre]

    # Busca o faturamento acumulado dos 3 meses no histórico mensal
    conn = conectar_historico()
    cur = conn.cursor()
    cur.execute("""
        SELECT mes, faturamento 
        FROM historico_mensal 
        WHERE cnpj = ? AND ano = ? AND mes IN (?, ?, ?)
    """, (cnpj, ano, meses_alvo[0], meses_alvo[1], meses_alvo[2]))
    
    registros_mensais = cur.fetchall()
    conn.close()

    # Validação dos meses encontrados
    meses_encontrados = [r[0] for r in registros_mensais]
    meses_faltantes = [m for m in meses_alvo if m not in meses_encontrados]

    if meses_faltantes:
        print(f"\n⚠️ Não é possível calcular o {trimestre}º Trimestre de {ano}.")
        print(f"Faltam os faturamentos dos meses: {meses_faltantes}")
        print("Cadastre o faturamento mensal desses meses antes de prosseguir.")
        return

    # Soma o faturamento dos 3 meses
    faturamento_trimestral = sum(r[1] for r in registros_mensais)

    # Executa o cálculo com o faturamento somado
    resultados = calcular_trimestral_lp(faturamento_trimestral, atividade)

    # Exibição do Resultado
    print(f"\n=== RESULTADO {trimestre}º TRIMESTRE / {ano} ===")
    print(f"Empresa: {nome}")
    print(f"Faturamento Total Acumulado (Meses {meses_alvo}): R$ {faturamento_trimestral:,.2f}")
    print("-" * 45)
    print(f"Base IRPJ: R$ {resultados['base_irpj']:.2f}")
    print(f"Base CSLL: R$ {resultados['base_csll']:.2f}")
    print(f"IRPJ Total (com Adicional se houver): R$ {resultados['irpj']:.2f}")
    print(f"CSLL: R$ {resultados['csll']:.2f}")
    print(f"TOTAL TRIMESTRAL (IRPJ + CSLL): R$ {resultados['total']:.2f}")

    # Salva o cálculo trimestral no banco
    conn = conectar_historico()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO historico_trimestral VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cnpj, nome, f"T{trimestre}", ano, faturamento_trimestral,
        resultados["base_irpj"], resultados["base_csll"],
        resultados["irpj"], resultados["csll"],
        resultados["total"],
        datetime.now().strftime("%d/%m/%Y %H:%M")
    ))
    conn.commit()
    conn.close()

    print("\n💾 Cálculo trimestral salvo com sucesso no histórico!")

# ---------------------------------------------------------
#               IMPRESSÃO DO RELATÓRIO EXCEL
# ---------------------------------------------------------

def imprimir_relatorio():
    print("\n=== Tipo de Relatório ===")
    print("1 - Mensal (PIS/COFINS)")
    print("2 - Trimestral (IRPJ/CSLL)")
    tipo = input("Escolha: ")

    empresas = listar_empresas_lucro_presumido()

    if not empresas:
        print("Nenhuma empresa cadastrada.")
        return

    print("\n=== EMPRESAS ===")
    for i, e in enumerate(empresas, 1):
        print(f"{i}. {e[1]} | CNPJ: {e[0]}")

    try:
        escolha = int(input("\nEscolha a empresa: ")) - 1
    except ValueError:
        print("Entrada inválida.")
        return

    if escolha < 0 or escolha >= len(empresas):
        print("Empresa inválida.")
        return

    cnpj, nome, _ = empresas[escolha]
    safe_cnpj = sanitize_filename(cnpj)

    conn = conectar_historico()
    cur = conn.cursor()

    if tipo == "1":
        mes = int(input("Mês (1-12): "))
        ano = int(input("Ano: "))

        cur.execute(
            """
            SELECT * FROM historico_mensal
            WHERE cnpj = ? AND mes = ? AND ano = ?
        """,
            (cnpj, mes, ano),
        )

        registros = cur.fetchall()

        if not registros:
            print("\nNenhum cálculo encontrado para este mês.")
            conn.close()
            return

        df = pd.DataFrame(
            registros,
            columns=[
                "CNPJ",
                "Empresa",
                "Mês",
                "Ano",
                "Faturamento",
                "PIS",
                "COFINS",
                "Total",
                "Calculado em",
            ],
        )

        nome_arquivo = f"relatorio_mensal_{safe_cnpj}_{ano}_{mes}.xlsx"

    elif tipo == "2":
        trimestre = int(input("Trimestre (1-4): "))
        ano = int(input("Ano: "))

        cur.execute(
            """
            SELECT * FROM historico_trimestral
            WHERE cnpj = ? AND trimestre = ? AND ano = ?
        """,
            (cnpj, f"T{trimestre}", ano),
        )

        registros = cur.fetchall()

        if not registros:
            print("\nNenhum cálculo encontrado para este trimestre.")
            conn.close()
            return

        df = pd.DataFrame(
            registros,
            columns=[
                "CNPJ",
                "Empresa",
                "Trimestre",
                "Ano",
                "Faturamento",
                "Base IRPJ",
                "Base CSLL",
                "IRPJ",
                "CSLL",
                "Total",
                "Calculado em",
            ],
        )

        nome_arquivo = f"relatorio_trimestral_{safe_cnpj}_{ano}_T{trimestre}.xlsx"

    else:
        print("Opção inválida.")
        conn.close()
        return

    conn.close()

    # --- SALVAMENTO NA PASTA /Excel ---
    if not os.path.exists(XLSX_DIR):
        os.makedirs(XLSX_DIR)

    caminho_salvamento = os.path.join(XLSX_DIR, nome_arquivo)

    try:
        df.to_excel(caminho_salvamento, index=False)
        print(f"\n📄 Relatório gerado com sucesso em: /{caminho_salvamento}")
    except Exception as e:
        print("Erro ao gerar arquivo:", e)

# ---------------------------------------------------------
#                     MENU PRINCIPAL
# ---------------------------------------------------------

def menu():
    # Inicializa o banco de histórico na abertura do programa
    conectar_historico().close()

    while True:
        print("\n============ LUCRO PRESUMIDO ============")
        print("1 - Calcular Mensal (PIS/COFINS)")
        print("2 - Calcular Trimestral (IRPJ/CSLL)")
        print("3 - Imprimir Relatório em Excel")
        print("0 - Sair")

        opc = input("> ")

        if opc == "1":
            calculo_mensal()
        elif opc == "2":
            calculo_trimestral()
        elif opc == "3":
            imprimir_relatorio()
        elif opc == "0":
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    menu()