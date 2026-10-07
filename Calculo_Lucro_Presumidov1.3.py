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

def calcular_trimestral_lp(detalhes_receitas, fator_majoracao=0.10, limite_isento_trimestral=1250000.0):
    """
    Calcula IRPJ e CSLL no Lucro Presumido aplicando o acréscimo na presunção (IN 2306/2026)
    SOMENTE sobre a parcela da receita bruta operacional que exceder R$ 1.250.000,00 no trimestre.
    """
    # 1. Alíquotas de Presunção Base (Originais)
    presuncoes_base = {
        "comercio_industria": {"irpj": 0.08, "csll": 0.12},
        "servicos_geral":     {"irpj": 0.32, "csll": 0.32},
        "transporte":         {"irpj": 0.16, "csll": 0.16},
        "aluguel_objeto_social": {"irpj": 0.32, "csll": 0.32}
    }

    # 2. Alíquotas Majoradas (+10% sobre a presunção)
    presuncoes_majoradas = {}
    for chave, taxas in presuncoes_base.items():
        presuncoes_majoradas[chave] = {
            "irpj": taxas["irpj"] * (1 + fator_majoracao),
            "csll": taxas["csll"] * (1 + fator_majoracao)
        }

    # 3. Cálculo da Proporção da Franquia de R$ 1.250.000,00
    faturamento_operacional_total = sum(
        detalhes_receitas.get(k, 0.0) for k in presuncoes_base.keys()
    )

    base_irpj_op = 0.0
    base_csll_op = 0.0

    if faturamento_operacional_total > 0:
        # Define quanto do faturamento fica dentro da franquia e quanto excede
        parcela_base = min(faturamento_operacional_total, limite_isento_trimestral)
        parcela_excedente = max(0.0, faturamento_operacional_total - limite_isento_trimestral)

        prop_base = parcela_base / faturamento_operacional_total
        prop_excedente = parcela_excedente / faturamento_operacional_total

        # Aplica as taxas originais na parcela dentro do limite e majoradas na parcela excedente
        for chave in presuncoes_base.keys():
            receita_item = detalhes_receitas.get(chave, 0.0)
            if receita_item > 0:
                rec_base = receita_item * prop_base
                rec_excedente = receita_item * prop_excedente

                # IRPJ
                base_irpj_op += (rec_base * presuncoes_base[chave]["irpj"]) + \
                                (rec_excedente * presuncoes_majoradas[chave]["irpj"])
                # CSLL
                base_csll_op += (rec_base * presuncoes_base[chave]["csll"]) + \
                                (rec_excedente * presuncoes_majoradas[chave]["csll"])

    # 4. Outras Receitas e Ganhos (Entram 100% na base de cálculo, sem presunção)
    outras_receitas = detalhes_receitas.get("outras_receitas_integrais", 0.0)

    # Base Final de Cálculo
    base_irpj_total = base_irpj_op + outras_receitas
    base_csll_total = base_csll_op + outras_receitas

    # 5. Apuração dos Impostos
    # IRPJ Normal: 15%
    irpj_normal = base_irpj_total * 0.15

    # Adicional IRPJ: 10% sobre o que exceder R$ 60.000,00 na BASE no Trimestre
    irpj_adicional = 0.0
    if base_irpj_total > 60000.0:
        irpj_adicional = (base_irpj_total - 60000.0) * 0.10

    irpj_total = irpj_normal + irpj_adicional

    # CSLL Normal: 9%
    csll_total = base_csll_total * 0.09

    total_impostos = irpj_total + csll_total

    return {
        "faturamento_operacional": faturamento_operacional_total,
        "parcela_isenta_limite": min(faturamento_operacional_total, limite_isento_trimestral),
        "parcela_excedente_majorada": max(0.0, faturamento_operacional_total - limite_isento_trimestral),
        "base_irpj": base_irpj_total,
        "base_csll": base_csll_total,
        "irpj_normal": irpj_normal,
        "irpj_adicional": irpj_adicional,
        "irpj_total": irpj_total,
        "csll_total": csll_total,
        "total": total_impostos
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
        print("Nenhuma empresa cadastrada no Lucro Presumido.")
        return

    print("\n=== EMPRESAS (LUCRO PRESUMIDO) ===")
    for i, e in enumerate(empresas, 1):
        print(f"{i}. {e[1]} | CNPJ: {e[0]} | Atividade Cadastrada: {e[2]}")

    try:
        escolha = int(input("\nEscolha a empresa: ")) - 1
    except ValueError:
        print("Opção inválida.")
        return

    if escolha < 0 or escolha >= len(empresas):
        print("Empresa inválida.")
        return

    cnpj, nome, atividade_cadastrada = empresas[escolha]

    try:
        trimestre = int(input("Trimestre (1-4): "))
        ano = int(input("Ano: "))
    except ValueError:
        print("Entrada inválida.")
        return

    if trimestre not in [1, 2, 3, 4]:
        print("Trimestre inválido!")
        return

    meses_por_trimestre = {
        1: (1, 2, 3),
        2: (4, 5, 6),
        3: (7, 8, 9),
        4: (10, 11, 12),
    }
    meses_alvo = meses_por_trimestre[trimestre]

    conn = conectar_historico()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT mes, faturamento 
        FROM historico_mensal 
        WHERE cnpj = ? AND ano = ? AND mes IN (?, ?, ?)
    """,
        (cnpj, ano, meses_alvo[0], meses_alvo[1], meses_alvo[2]),
    )

    registros_mensais = cur.fetchall()
    conn.close()

    meses_encontrados = [r[0] for r in registros_mensais]
    meses_faltantes = [m for m in meses_alvo if m not in meses_encontrados]

    if meses_faltantes:
        print(
            f"\n⚠️ Faltam os faturamentos mensais dos meses: {meses_faltantes}."
        )
        print("Cadastre os faturamentos no menu antes de prosseguir.")
        return

    faturamento_operacional_total = sum(r[1] for r in registros_mensais)

    print(
        f"\n--- DISCRIMINAÇÃO DE RECEITAS - {trimestre}º TRIMESTRE DE {ano} ---"
    )
    print(
        f"Faturamento Bruto Operacional Acumulado dos 3 Meses: R$"
        f" {faturamento_operacional_total:,.2f}"
    )

    def ler_valor(prompt_text):
        v = input(prompt_text).strip().replace(",", ".")
        return float(v) if v else 0.0

    try:
        comercio_ind = ler_valor(
            "1. Venda de Mercadorias / Indústria / Prod. RURAL (R$): "
        )
        serv_geral = ler_valor("2. Serviços em Geral (R$): ")
        transporte = ler_valor("3. Serviços de Transporte (R$): ")
        aluguel_objeto = ler_valor(
            "4. Receita de Aluguel (Se consta no Objeto Social/CNPJ) (R$): "
        )

        soma_digitada = comercio_ind + serv_geral + transporte + aluguel_objeto
        if soma_digitada == 0.0:
            if (
                "Comércio" in atividade_cadastrada
                or "Indústria" in atividade_cadastrada
            ):
                comercio_ind = faturamento_operacional_total
            else:
                serv_geral = faturamento_operacional_total

        print(
            "\n--- OUTRAS RECEITAS E GANHOS (Entram 100% na Base de Cálculo)"
            " ---"
        )
        aplic_fin = ler_valor("- Rendimentos de Aplicações Financeiras (R$): ")
        ganho_cap = ler_valor(
            "- Ganho de Capital na Venda de Ativo Imobilizado (R$): "
        )
        jscp = ler_valor("- Juros sobre Capital Próprio - JSCP (R$): ")
        aluguel_fora_objeto = ler_valor(
            "- Locação de Imóveis (FORA do Objeto Social/CNPJ) (R$): "
        )
        descontos = ler_valor("- Descontos Financeiros Obtidos (R$): ")

    except ValueError:
        print("Valor numérico inválido informado.")
        return

    outras_receitas_totais = (
        aplic_fin + ganho_cap + jscp + aluguel_fora_objeto + descontos
    )

    detalhes = {
        "comercio_industria": comercio_ind,
        "servicos_geral": serv_geral,
        "transporte": transporte,
        "aluguel_objeto_social": aluguel_objeto,
        "outras_receitas_integrais": outras_receitas_totais,
    }

    # Aplicação do cálculo com acréscimo da IN RFB 2.306/2026 (LC 224/2025)
    res = calcular_trimestral_lp(detalhes)

    # Exibição do Resultado
    print(f"\n================ RESULTADO {trimestre}º TRIMESTRE / {ano} ================")
    print(f"Empresa: {nome}")
    print(" (Com acréscimo de presunção conforme IN RFB nº 2.306/2026)")
    print("-" * 65)
    print(f"Faturamento Operacional Total:          R$ {res['faturamento_operacional']:,.2f}")
    print(f" -> Parcela com Presunção Normal (Até 1,25M): R$ {res['parcela_isenta_limite']:,.2f}")
    print(f" -> Parcela com Presunção Majorada (Excedente): R$ {res['parcela_excedente_majorada']:,.2f}")
    print("-" * 65)
    print(f"Base de Cálculo Final IRPJ: R$ {res['base_irpj']:,.2f}")
    print(f"Base de Cálculo Final CSLL: R$ {res['base_csll']:,.2f}")
    print("-" * 65)
    print(f"IRPJ Normal (15%):           R$ {res['irpj_normal']:,.2f}")
    print(f"IRPJ Adicional (10% excede 60k): R$ {res['irpj_adicional']:,.2f}")
    print(f"IRPJ Total:                  R$ {res['irpj_total']:,.2f}")
    print(f"CSLL Total (9%):             R$ {res['csll_total']:,.2f}")
    print("-" * 65)
    print(f"TOTAL DE IMPOSTOS TRIMESTRAIS (IRPJ + CSLL): R$ {res['total']:,.2f}")

    # Salva no Histórico
    conn = conectar_historico()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO historico_trimestral VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            cnpj,
            nome,
            f"T{trimestre}",
            ano,
            faturamento_operacional_total + outras_receitas_totais,
            res["base_irpj"],
            res["base_csll"],
            res["irpj_total"],
            res["csll_total"],
            res["total"],
            datetime.now().strftime("%d/%m/%Y %H:%M"),
        ),
    )
    conn.commit()
    conn.close()

    print("\n💾 Cálculo trimestral atualizado e salvo no histórico!")

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