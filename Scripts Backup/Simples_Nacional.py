import sqlite3
import pandas as pd
from datetime import datetime

# ============================================
# CONEXÃO COM O BANCO DE EMPRESAS
# ============================================

def conectar_empresas():
    return sqlite3.connect("empresas.db")

def listar_empresas_simples():
    """Lista somente empresas com regime Simples Nacional."""
    conn = conectar_empresas()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cnpj, razao_social, regime_tributario, atividade
        FROM empresas
        WHERE regime_tributario = 'Simples Nacional'
    """)

    empresas = cursor.fetchall()
    conn.close()

    if not empresas:
        print("⚠️ Nenhuma empresa cadastrada no Simples Nacional.")
        return []

    print("\n===== EMPRESAS DO SIMPLES NACIONAL =====")
    for e in empresas:
        print(f"CNPJ: {e[0]} | {e[1]} | Atividade: {e[3]}")
    print("========================================\n")

    return empresas

# ============================================
# TABELAS SIMPLIFICADAS DO SIMPLES NACIONAL
# ============================================

TABELAS = {
    "Comércio": [
        (180000.00, 0.04, 0.00),
        (360000.00, 0.073, 5940.00),
        (720000.00, 0.095, 13860.00),
        (1800000.00, 0.107, 22500.00),
        (3600000.00, 0.143, 87300.00),
        (4800000.00, 0.19, 378000.00)
    ],
    "Indústria": [
        (180000.00, 0.045, 0.00),
        (360000.00, 0.078, 5940.00),
        (720000.00, 0.10, 13860.00),
        (1800000.00, 0.112, 22500.00),
        (3600000.00, 0.147, 85500.00),
        (4800000.00, 0.30, 720000.00)
    ],
    "Serviços": [
        (180000.00, 0.06, 0.00),
        (360000.00, 0.112, 9360.00),
        (720000.00, 0.135, 17640.00),
        (1800000.00, 0.16, 35640.00),
        (3600000.00, 0.21, 125640.00),
        (4800000.00, 0.33, 648000.00)
    ]
}

# ============================================
# CRIA TABELA DE HISTÓRICO (se não existir)
# ============================================

def criar_tabela_historico():
    conn = conectar_empresas()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_simples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT NOT NULL,
            mes_ano TEXT NOT NULL,
            faturamento REAL NOT NULL,
            rbt12 REAL NOT NULL,
            atividade TEXT NOT NULL,
            aliquota_nominal REAL NOT NULL,
            parcela_deduzir REAL NOT NULL,
            aliquota_efetiva REAL NOT NULL,
            valor_das REAL NOT NULL,
            data_processamento TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

# ============================================
# SALVAR APURAÇÃO NO HISTÓRICO
# ============================================

def salvar_historico(cnpj, mes_ano, faturamento, rbt12, atividade,
                     aliq_nominal, deducao, aliq_efetiva, das):

    conn = conectar_empresas()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO historico_simples (
            cnpj, mes_ano, faturamento, rbt12, atividade,
            aliquota_nominal, parcela_deduzir, aliquota_efetiva,
            valor_das, data_processamento
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cnpj,
        mes_ano,
        faturamento,
        rbt12,
        atividade,
        aliq_nominal,
        deducao,
        aliq_efetiva,
        das,
        datetime.now().strftime("%d/%m/%Y %H:%M")
    ))

    conn.commit()
    conn.close()

# ============================================
# CONSULTA DE RELATÓRIO ANUAL
# ============================================

def consulta_anual():
    ano = input("Informe o ano para consultar (AAAA): ")

    conn = conectar_empresas()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cnpj, mes_ano, faturamento, valor_das
        FROM historico_simples
        WHERE substr(mes_ano, 4, 4) = ?
        ORDER BY cnpj, mes_ano
    """, (ano,))

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        print("⚠️ Nenhum registro encontrado para este ano.")
        return

    df = pd.DataFrame(dados, columns=["CNPJ", "Mês/Ano", "Faturamento", "DAS"])
    print("\n===== RELATÓRIO ANUAL =====")
    print(df)
    print("===========================\n")

# ============================================
# CÁLCULO PRINCIPAL
# ============================================

def calcular_simples():
    criar_tabela_historico()

    empresas = listar_empresas_simples()
    if not empresas:
        return

    cnpj = input("Informe o CNPJ da empresa para cálculo: ").strip()

    # buscar dados da empresa
    conn = conectar_empresas()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT razao_social, regime_tributario, atividade
        FROM empresas
        WHERE cnpj = ?
    """, (cnpj,))

    empresa = cursor.fetchone()
    conn.close()

    if not empresa:
        print("⚠️ Empresa não encontrada.")
        return

    razao, trib, atividade = empresa

    print(f"\n🧾 Empresa selecionada: {razao} | {trib}")

    mes_ano = input("Informe o mês/ano (mm/aaaa): ")
    faturamento = float(input("Faturamento bruto do mês (R$): ").replace(",", "."))
    rbt12 = float(input("RBT12 (últimos 12 meses) (R$): ").replace(",", "."))

    if atividade not in TABELAS:
        print("⚠️ Tipo de atividade inválido no cadastro da empresa.")
        return

    tabela = TABELAS[atividade]

    faixa = None
    for limite, aliq, deduz in tabela:
        if rbt12 <= limite:
            faixa = (limite, aliq, deduz)
            break
    if not faixa:
        faixa = tabela[-1]

    limite, aliq_nominal, deducao = faixa

    # Cálculo
    aliquota_efetiva = ((rbt12 * aliq_nominal) - deducao) / rbt12
    imposto_mensal = faturamento * aliquota_efetiva

    print("\n===== RESULTADO DO CÁLCULO =====")
    print(f"Empresa: {razao}")
    print(f"CNPJ: {cnpj}")
    print(f"Atividade: {atividade}")
    print(f"Alíquota nominal: {aliq_nominal*100:.2f}%")
    print(f"Parcela a deduzir: R$ {deducao:,.2f}")
    print(f"Alíquota efetiva: {aliquota_efetiva*100:.2f}%")
    print(f"DAS a pagar: R$ {imposto_mensal:,.2f}")
    print("================================\n")

    # Salvar histórico
    salvar_historico(
        cnpj, mes_ano, faturamento, rbt12, atividade,
        aliq_nominal, deducao, aliquota_efetiva, imposto_mensal
    )

    print("💾 Registro salvo no histórico!")

# ============================================
# MENU
# ============================================

def menu():
    while True:
        print("""
========= MENU =========
1 - Calcular Simples Nacional
2 - Consultar Relatório Anual
0 - Sair
========================
""")

        opc = input("Escolha: ")

        if opc == "1":
            calcular_simples()
        elif opc == "2":
            consulta_anual()
        elif opc == "0":
            break
        else:
            print("Opção inválida.")

# EXECUÇÃO
if __name__ == "__main__":
    menu()