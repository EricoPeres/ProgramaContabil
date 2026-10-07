from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

# ============================================
# BANCO DE DADOS DE EXEMPLO / PLANO DE CONTAS
# ============================================

PLANO_CONTAS_MOCK = [
    {
        "resumida": "1",
        "codigo": "1.1.1.01",
        "nome": "CAIXA GERAL",
        "nat": "D",
        "tipo": "A",
    },
    {
        "resumida": "2",
        "codigo": "1.1.1.02",
        "nome": "BANCO CONTA MOVIMENTO - ITÁU",
        "nat": "D",
        "tipo": "A",
    },
    {
        "resumida": "3",
        "codigo": "1.1.1.03",
        "nome": "BANCO CONTA MOVIMENTO - BRADESCO",
        "nat": "D",
        "tipo": "A",
    },
    {
        "resumida": "4",
        "codigo": "1.1.2.01",
        "nome": "APLICAÇÕES FINANCEIRAS DE LIQUIDEZ IMEDIATA",
        "nat": "D",
        "tipo": "A",
    },
    {
        "resumida": "10",
        "codigo": "2.1.1.01",
        "nome": "FORNECEDORES NACIONAIS",
        "nat": "C",
        "tipo": "A",
    },
    {
        "resumida": "11",
        "codigo": "2.1.2.01",
        "nome": "SALÁRIOS E ORDENADOS A PAGAR",
        "nat": "C",
        "tipo": "A",
    },
    {
        "resumida": "12",
        "codigo": "2.1.3.01",
        "nome": "INSS A RECOLHER",
        "nat": "C",
        "tipo": "A",
    },
    {
        "resumida": "13",
        "codigo": "2.1.3.02",
        "nome": "FGTS A RECOLHER",
        "nat": "C",
        "tipo": "A",
    },
    {
        "resumida": "50",
        "codigo": "4.1.1.01",
        "nome": "RECEITA DE VENDAS DE MERCADORIAS",
        "nat": "C",
        "tipo": "A",
    },
    {
        "resumida": "51",
        "codigo": "4.1.1.02",
        "nome": "RECEITA DE PRESTAÇÃO DE SERVIÇOS",
        "nat": "C",
        "tipo": "A",
    },
    {
        "resumida": "80",
        "codigo": "3.1.1.01",
        "nome": "DESPESAS COM SALÁRIOS E ORDENADOS",
        "nat": "D",
        "tipo": "A",
    },
    {
        "resumida": "81",
        "codigo": "3.1.1.02",
        "nome": "DESPESAS COM ALUGUEL",
        "nat": "D",
        "tipo": "A",
    },
    {
        "resumida": "82",
        "codigo": "3.1.1.03",
        "nome": "DESPESAS COM ENERGIA ELÉTRICA",
        "nat": "D",
        "tipo": "A",
    },
]

# ============================================
# JANELA POP-UP DE BUSCA DE CONTAS (F9)
# ============================================

class JanelaBuscaContas(tk.Toplevel):

  def __init__(self, parent, callback_selecao):
    super().__init__(parent)
    self.title("Pesquisa do Plano de Contas - [F9]")
    self.geometry("700x450")
    self.configure(bg="#ece9d8")
    self.resizable(False, False)

    # Deixa a janela modal
    self.transient(parent)
    self.grab_set()

    self.callback_selecao = callback_selecao

    # Componentes de Pesquisa
    frame_busca = ttk.LabelFrame(self, text=" Filtro de Pesquisa ")
    frame_busca.pack(fill="x", padx=10, pady=5)

    tk.Label(
        frame_busca,
        text="Pesquisar por (Nome, Código ou ID):",
        bg="#ece9d8",
        font=("Tahoma", 8, "bold"),
    ).pack(anchor="w", padx=5, pady=2)

    self.ent_busca = tk.Entry(frame_busca, font=("Tahoma", 10))
    self.ent_busca.pack(fill="x", padx=5, pady=5)
    self.ent_busca.bind("<KeyRelease>", self.filtrar_contas)
    self.ent_busca.focus()

    # Tabela de Contas
    frame_grid = ttk.Frame(self)
    frame_grid.pack(fill="both", expand=True, padx=10, pady=5)

    colunas = ("resumida", "codigo", "nome", "nat", "tipo")
    self.tree = ttk.Treeview(
        frame_grid, columns=colunas, show="headings", height=12
    )

    self.tree.heading("resumida", text="ID Resumida")
    self.tree.heading("codigo", text="Código Estruturado")
    self.tree.heading("nome", text="Descrição da Conta")
    self.tree.heading("nat", text="Nat.")
    self.tree.heading("tipo", text="Tipo")

    self.tree.column("resumida", width=90, anchor="center")
    self.tree.column("codigo", width=120, anchor="center")
    self.tree.column("nome", width=350, anchor="w")
    self.tree.column("nat", width=50, anchor="center")
    self.tree.column("tipo", width=50, anchor="center")

    scrollbar = ttk.Scrollbar(
        frame_grid, orient="vertical", command=self.tree.yview
    )
    self.tree.configure(yscroll=scrollbar.set)

    self.tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Atalhos na janela de busca
    self.tree.bind("<Double-1>", self.confirmar_selecao)
    self.bind("<Return>", self.confirmar_selecao)
    self.bind("<Escape>", lambda event: self.destroy())

    # Inicializa com todas as contas do plano
    self.carregar_contas(PLANO_CONTAS_MOCK)

  def carregar_contas(self, lista_contas):
    for item in self.tree.get_children():
      self.tree.delete(item)

    for c in lista_contas:
      self.tree.insert(
          "",
          "end",
          values=(c["resumida"], c["codigo"], c["nome"], c["nat"], c["tipo"]),
      )

    # Seleciona o primeiro item por padrão
    children = self.tree.get_children()
    if children:
      self.tree.selection_set(children[0])
      self.tree.focus(children[0])

  def filtrar_contas(self, event=None):
    termo = self.ent_busca.get().strip().lower()
    if not termo:
      self.carregar_contas(PLANO_CONTAS_MOCK)
      return

    filtrados = [
        c
        for c in PLANO_CONTAS_MOCK
        if termo in c["nome"].lower()
        or termo in c["codigo"].lower()
        or termo in c["resumida"]
    ]
    self.carregar_contas(filtrados)

  def confirmar_selecao(self, event=None):
    selecao = self.tree.selection()
    if selecao:
      item = self.tree.item(selecao[0])["values"]
      resumida = str(item[0])
      self.callback_selecao(resumida)
      self.destroy()

# ============================================
# APLICAÇÃO PRINCIPAL (SISTEMA DOMÍNIO)
# ============================================

class DominioLancamentoApp(tk.Tk):

  def __init__(self):
    super().__init__()
    self.title("Lançamentos - [Sistema Domínio Contábil]")
    self.geometry("1020x720")
    self.configure(bg="#ece9d8")

    self.configurar_estilos()

    self.criar_abas()
    self.criar_cabecalho(self.tab_geral)
    self.criar_formulario_lancamento(self.tab_geral)
    self.criar_grid_lancamentos(self.tab_geral)
    self.criar_rodape_totais(self.tab_geral)
    self.criar_barra_botoes_principal()

    # ATALHOS GLOBAIS ESTILO DOMÍNIO
    self.bind("<F8>", lambda event: self.gravar_lote())
    self.bind("<F9>", lambda event: self.abrir_busca_contas())
    self.bind("<Return>", self.navegar_com_enter)

  def configurar_estilos(self):
    style = ttk.Style()
    style.theme_use("default")
    style.configure("TNotebook", background="#ece9d8", borderwidth=0)
    style.configure("TNotebook.Tab", background="#ece9d8", padding=[8, 4])
    style.configure("TFrame", background="#ece9d8")
    style.configure("TLabelframe", background="#ece9d8")
    style.configure(
        "TLabelframe.Label", background="#ece9d8", font=("Tahoma", 8, "bold")
    )

  def converter_valor_para_float(self, valor_str):
    if not valor_str:
      return 0.0
    try:
      limpo = str(valor_str).replace(".", "").replace(",", ".").strip()
      return float(limpo)
    except ValueError:
      return 0.0

  def formatar_float_para_moeda(self, valor_float):
    return (
        f"{valor_float:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

  def navegar_com_enter(self, event):
    focus = self.focus_get()
    if isinstance(focus, (tk.Entry, ttk.Combobox, ttk.Entry)):
      focus.tk_focusNext().focus()

  def abrir_busca_contas(self):
    """Abre a janela modal de pesquisa F9."""
    JanelaBuscaContas(self, self.preencher_conta_selecionada)

  def preencher_conta_selecionada(self, resumida):
    """Callback executada quando o usuário escolhe uma conta na janela F9."""
    self.ent_conta.delete(0, tk.END)
    self.ent_conta.insert(0, resumida)
    self.atualizar_descricao_conta()
    self.ent_valor.focus()

  # ============================================
  # CONSTRUÇÃO DA INTERFACE
  # ============================================

  def criar_abas(self):
    self.notebook = ttk.Notebook(self)
    self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

    self.tab_geral = ttk.Frame(self.notebook)
    self.notebook.add(self.tab_geral, text="  Geral  ")

  def criar_cabecalho(self, parent):
    frame = ttk.LabelFrame(parent, text=" Dados do Lote ")
    frame.pack(fill="x", padx=5, pady=2)

    tk.Label(frame, text="Lote:", bg="#ece9d8").grid(
        row=0, column=0, padx=5, pady=5, sticky="e"
    )
    self.ent_lote = tk.Entry(frame, width=10, font=("Tahoma", 9, "bold"))
    self.ent_lote.insert(0, "000001")
    self.ent_lote.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(frame, text="Data:", bg="#ece9d8").grid(
        row=0, column=2, padx=5, pady=5, sticky="e"
    )
    self.ent_data = tk.Entry(frame, width=12)
    self.ent_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
    self.ent_data.grid(row=0, column=3, padx=5, pady=5)

    tk.Label(frame, text="Descrição:", bg="#ece9d8").grid(
        row=0, column=4, padx=5, pady=5, sticky="e"
    )
    self.ent_desc_lote = tk.Entry(frame, width=50)
    self.ent_desc_lote.insert(0, "MOVIMENTO CONTÁBIL DIÁRIO")
    self.ent_desc_lote.grid(row=0, column=5, padx=5, pady=5, sticky="we")

  def criar_formulario_lancamento(self, parent):
    frame = ttk.LabelFrame(parent, text=" Partida do Lançamento ")
    frame.pack(fill="x", padx=5, pady=2)

    # Linha 1: Tipo, Conta Resumida, Botão F9 e Nome da Conta
    tk.Label(frame, text="Tipo (D/C):", bg="#ece9d8").grid(
        row=0, column=0, padx=5, pady=2, sticky="e"
    )
    self.cmb_tipo = ttk.Combobox(
        frame, values=["D", "C"], width=3, state="readonly"
    )
    self.cmb_tipo.set("D")
    self.cmb_tipo.grid(row=0, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame, text="Conta Resumida:", bg="#ece9d8").grid(
        row=0, column=2, padx=5, pady=2, sticky="e"
    )
    self.ent_conta = tk.Entry(frame, width=10)
    self.ent_conta.grid(row=0, column=3, padx=5, pady=2, sticky="w")
    self.ent_conta.bind("<FocusOut>", self.atualizar_descricao_conta)
    self.ent_conta.bind("<F9>", lambda event: self.abrir_busca_contas())

    btn_f9 = tk.Button(
        frame,
        text="F9 Pesquisar",
        bg="#d4d0c8",
        relief="raised",
        font=("Tahoma", 7),
        command=self.abrir_busca_contas,
    )
    btn_f9.grid(row=0, column=4, padx=2, pady=2, sticky="w")

    self.lbl_nome_conta = tk.Label(
        frame,
        text="[Informe a Conta]",
        font=("Tahoma", 9, "bold"),
        fg="#000080",
        bg="#ece9d8",
    )
    self.lbl_nome_conta.grid(
        row=0, column=5, padx=5, pady=2, sticky="w"
    )

    # Linha 2: Valor e Histórico
    tk.Label(frame, text="Valor (R$):", bg="#ece9d8").grid(
        row=1, column=0, padx=5, pady=2, sticky="e"
    )
    self.ent_valor = tk.Entry(frame, width=15, justify="right")
    self.ent_valor.grid(
        row=1, column=1, columnspan=2, padx=5, pady=2, sticky="w"
    )

    tk.Label(frame, text="Histórico:", bg="#ece9d8").grid(
        row=1, column=3, padx=5, pady=2, sticky="e"
    )
    self.ent_historico = tk.Entry(frame, width=50)
    self.ent_historico.grid(
        row=1, column=4, columnspan=2, padx=5, pady=2, sticky="we"
    )

    btn_add = tk.Button(
        frame,
        text="Adicionar (Enter)",
        bg="#d4d0c8",
        relief="raised",
        command=self.adicionar_partida,
    )
    btn_add.grid(row=1, column=6, padx=5, pady=2)

  def atualizar_descricao_conta(self, event=None):
    resumida = self.ent_conta.get().strip()
    conta_encontrada = next(
        (c for c in PLANO_CONTAS_MOCK if c["resumida"] == resumida), None
    )

    if conta_encontrada:
      desc = f"[{conta_encontrada['codigo']}] {conta_encontrada['nome']}"
    else:
      desc = (
          "[ CONTA NÃO ENCONTRADA ]" if resumida else "[Informe a Conta]"
      )

    self.lbl_nome_conta.config(text=desc)

  def criar_grid_lancamentos(self, parent):
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True, padx=5, pady=2)

    colunas = ("item", "tipo", "conta", "descricao", "valor", "historico")
    self.tree = ttk.Treeview(frame, columns=colunas, show="headings", height=8)

    self.tree.heading("item", text="Item")
    self.tree.heading("tipo", text="D/C")
    self.tree.heading("conta", text="Conta")
    self.tree.heading("descricao", text="Descrição da Conta")
    self.tree.heading("valor", text="Valor (R$)")
    self.tree.heading("historico", text="Histórico")

    self.tree.column("item", width=50, anchor="center")
    self.tree.column("tipo", width=40, anchor="center")
    self.tree.column("conta", width=80, anchor="center")
    self.tree.column("descricao", width=220, anchor="w")
    self.tree.column("valor", width=120, anchor="e")
    self.tree.column("historico", width=350, anchor="w")

    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
    self.tree.configure(yscroll=scrollbar.set)

    self.tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

  def criar_rodape_totais(self, parent):
    frame = ttk.LabelFrame(parent, text=" Totais do Lote ")
    frame.pack(fill="x", padx=5, pady=2)

    tk.Label(frame, text="Total Débitos:", bg="#ece9d8").grid(
        row=0, column=0, padx=5, pady=5
    )
    self.ent_tot_deb = tk.Entry(
        frame,
        width=15,
        state="readonly",
        justify="right",
        font=("Tahoma", 9, "bold"),
    )
    self.ent_tot_deb.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(frame, text="Total Créditos:", bg="#ece9d8").grid(
        row=0, column=2, padx=5, pady=5
    )
    self.ent_tot_cred = tk.Entry(
        frame,
        width=15,
        state="readonly",
        justify="right",
        font=("Tahoma", 9, "bold"),
    )
    self.ent_tot_cred.grid(row=0, column=3, padx=5, pady=5)

    tk.Label(frame, text="Diferença:", bg="#ece9d8").grid(
        row=0, column=4, padx=5, pady=5
    )
    self.ent_diferenca = tk.Entry(
        frame,
        width=15,
        state="readonly",
        justify="right",
        font=("Tahoma", 9, "bold"),
        fg="red",
    )
    self.ent_diferenca.grid(row=0, column=5, padx=5, pady=5)

    self.recalcular_totais()

  def criar_barra_botoes_principal(self):
    frame = tk.Frame(self, bg="#d4d0c8", bd=1, relief="raised")
    frame.pack(fill="x", side="bottom", padx=2, pady=2)

    btn_gravar = tk.Button(
        frame,
        text="[F8] Gravar Lote",
        bg="#ece9d8",
        relief="raised",
        command=self.gravar_lote,
    )
    btn_gravar.pack(side="left", padx=5, pady=3)

    btn_busca = tk.Button(
        frame,
        text="[F9] Buscar Conta",
        bg="#ece9d8",
        relief="raised",
        command=self.abrir_busca_contas,
    )
    btn_busca.pack(side="left", padx=5, pady=3)

    btn_limpar = tk.Button(
        frame,
        text="Novo / Limpar",
        bg="#ece9d8",
        relief="raised",
        command=self.limpar_formulario,
    )
    btn_limpar.pack(side="left", padx=5, pady=3)

    btn_sair = tk.Button(
        frame, text="Sair", bg="#ece9d8", relief="raised", command=self.destroy
    )
    btn_sair.pack(side="right", padx=5, pady=3)

  # ============================================
  # LÓGICA DE NEGÓCIO E REGRAS CONTÁBEIS
  # ============================================

  def adicionar_partida(self):
    tipo = self.cmb_tipo.get()
    conta = self.ent_conta.get().strip()
    desc = self.lbl_nome_conta.cget("text")
    val_str = self.ent_valor.get().strip()
    hist = self.ent_historico.get().strip()

    valor = self.converter_valor_para_float(val_str)

    if not conta or "NÃO ENCONTRADA" in desc or "[Informe" in desc:
      messagebox.showwarning("Aviso", "Informe uma conta contábil válida.")
      self.ent_conta.focus()
      return

    if valor <= 0:
      messagebox.showwarning("Aviso", "Informe um valor maior que zero.")
      self.ent_valor.focus()
      return

    item_idx = len(self.tree.get_children()) + 1
    val_formatado = self.formatar_float_para_moeda(valor)

    self.tree.insert(
        "", "end", values=(item_idx, tipo, conta, desc, val_formatado, hist)
    )

    self.ent_conta.delete(0, tk.END)
    self.ent_valor.delete(0, tk.END)
    self.lbl_nome_conta.config(text="[Informe a Conta]")
    self.cmb_tipo.focus()

    self.recalcular_totais()

  def recalcular_totais(self):
    total_deb, total_cred = 0.0, 0.0

    for item in self.tree.get_children():
      row = self.tree.item(item)["values"]
      tipo = str(row[1])
      val = self.converter_valor_para_float(row[4])

      if tipo == "D":
        total_deb += val
      elif tipo == "C":
        total_cred += val

    diferenca = abs(total_deb - total_cred)

    self.atualizar_campo_readonly(
        self.ent_tot_deb, self.formatar_float_para_moeda(total_deb)
    )
    self.atualizar_campo_readonly(
        self.ent_tot_cred, self.formatar_float_para_moeda(total_cred)
    )
    self.atualizar_campo_readonly(
        self.ent_diferenca, self.formatar_float_para_moeda(diferenca)
    )

  def atualizar_campo_readonly(self, campo, texto):
    campo.config(state="normal")
    campo.delete(0, tk.END)
    campo.insert(0, texto)
    campo.config(state="readonly")

  def gravar_lote(self):
    if not self.tree.get_children():
      messagebox.showwarning(
          "Aviso", "Não existem partidas lançadas neste lote."
      )
      return

    diferenca = self.converter_valor_para_float(self.ent_diferenca.get())

    if diferenca != 0.0:
      messagebox.showerror(
          "Erro de Partida Dobrada",
          f"O lote está desbalanceado!\n\n"
          f"Diferença entre Débitos e Créditos: R$"
          f" {self.ent_diferenca.get()}\n"
          f"Ajuste os valores antes de gravar.",
      )
      return

    messagebox.showinfo(
        "Sucesso", f"Lote Nº {self.ent_lote.get()} gravado com sucesso!"
    )
    self.limpar_formulario()

  def limpar_formulario(self):
    for item in self.tree.get_children():
      self.tree.delete(item)
    self.ent_conta.delete(0, tk.END)
    self.ent_valor.delete(0, tk.END)
    self.ent_historico.delete(0, tk.END)
    self.lbl_nome_conta.config(text="[Informe a Conta]")
    self.recalcular_totais()

if __name__ == "__main__":
  app = DominioLancamentoApp()
  app.mainloop()