from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk


class DominioLancamentoApp(tk.Tk):

  def __init__(self):
    super().__init__()
    self.title("Lançamentos Contábeis")
    self.geometry("1020x720")
    self.configure(bg="#ece9d8")  # Cor bege clássica do Windows/Domínio

    # Estilo dos componentes
    self.configurar_estilos()

    # Inicialização das seções
    self.criar_abas()
    self.criar_cabecalho(self.tab_geral)
    self.criar_formulario_lancamento(self.tab_geral)
    self.criar_grid_lancamentos(self.tab_geral)
    self.criar_rodape_totais(self.tab_geral)
    self.criar_barra_botoes_principal()

    # Atalhos Globais estilo Domínio
    self.bind("<F8>", lambda event: self.gravar_lote())
    self.bind("<Return>", self.navegar_com_enter)

  def configurar_estilos(self):
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "TNotebook", background="#ece9d8", borderwidth=0
    )
    style.configure(
        "TNotebook.Tab", background="#ece9d8", padding=[8, 4]
    )
    style.configure("TFrame", background="#ece9d8")
    style.configure("TLabelframe", background="#ece9d8")
    style.configure("TLabelframe.Label", background="#ece9d8", font=("Tahoma", 8, "bold"))

  def converter_valor_para_float(self, valor_str):
    """Converte strings monetárias no formato BR (1.250,50) para float Python (1250.50)."""
    if not valor_str:
      return 0.0
    try:
      limpo = str(valor_str).replace(".", "").replace(",", ".").strip()
      return float(limpo)
    except ValueError:
      return 0.0

  def formatar_float_para_moeda(self, valor_float):
    """Formata float para string no formato brasileiro (1.250,50)."""
    return f"{valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

  def navegar_com_enter(self, event):
    """Permite navegar entre os campos do formulário usando a tecla ENTER."""
    focus = self.focus_get()
    if isinstance(focus, (tk.Entry, ttk.Combobox, ttk.Entry)):
      focus.tk_focusNext().focus()

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

    tk.Label(frame, text="Lote:", bg="#ece9d8").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    self.ent_lote = tk.Entry(frame, width=10, font=("Tahoma", 9, "bold"))
    self.ent_lote.insert(0, "000001")
    self.ent_lote.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(frame, text="Data:", bg="#ece9d8").grid(row=0, column=2, padx=5, pady=5, sticky="e")
    self.ent_data = tk.Entry(frame, width=12)
    self.ent_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
    self.ent_data.grid(row=0, column=3, padx=5, pady=5)

    tk.Label(frame, text="Descrição:", bg="#ece9d8").grid(row=0, column=4, padx=5, pady=5, sticky="e")
    self.ent_desc_lote = tk.Entry(frame, width=50)
    self.ent_desc_lote.insert(0, "MOVIMENTO CONTÁBIL DIÁRIO")
    self.ent_desc_lote.grid(row=0, column=5, padx=5, pady=5, sticky="we")

  def criar_formulario_lancamento(self, parent):
    frame = ttk.LabelFrame(parent, text=" Partida do Lançamento ")
    frame.pack(fill="x", padx=5, pady=2)

    # Linha 1: Tipo, Conta Resumida e Nome da Conta
    tk.Label(frame, text="Tipo (D/C):", bg="#ece9d8").grid(row=0, column=0, padx=5, pady=2, sticky="e")
    self.cmb_tipo = ttk.Combobox(frame, values=["D", "C"], width=3, state="readonly")
    self.cmb_tipo.set("D")
    self.cmb_tipo.grid(row=0, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame, text="Conta Resumida:", bg="#ece9d8").grid(row=0, column=2, padx=5, pady=2, sticky="e")
    self.ent_conta = tk.Entry(frame, width=10)
    self.ent_conta.grid(row=0, column=3, padx=5, pady=2, sticky="w")
    self.ent_conta.bind("<FocusOut>", self.atualizar_descricao_conta)

    self.lbl_nome_conta = tk.Label(frame, text="[Informe a Conta]", font=("Tahoma", 9, "italic"), fg="#000080", bg="#ece9d8")
    self.lbl_nome_conta.grid(row=0, column=4, columnspan=2, padx=5, pady=2, sticky="w")

    # Linha 2: Valor e Histórico
    tk.Label(frame, text="Valor (R$):", bg="#ece9d8").grid(row=1, column=0, padx=5, pady=2, sticky="e")
    self.ent_valor = tk.Entry(frame, width=15, justify="right")
    self.ent_valor.grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky="w")

    tk.Label(frame, text="Histórico:", bg="#ece9d8").grid(row=1, column=3, padx=5, pady=2, sticky="e")
    self.ent_historico = tk.Entry(frame, width=50)
    self.ent_historico.grid(row=1, column=4, padx=5, pady=2, sticky="we")

    btn_add = tk.Button(frame, text="Adicionar (Enter)", bg="#d4d0c8", relief="raised", command=self.adicionar_partida)
    btn_add.grid(row=1, column=5, padx=5, pady=2)

  def atualizar_descricao_conta(self, event=None):
    """Simula a busca da conta no Plano de Contas ao sair do campo."""
    conta = self.ent_conta.get().strip()
    simulacao_plano = {
        "1": "1.1.1.01 - CAIXA GERAL",
        "2": "1.1.1.02 - BANCO CONTA MOVIMENTO",
        "10": "2.1.1.01 - FORNECEDORES NACIONAIS",
        "50": "4.1.1.01 - RECEITA DE VENDAS",
    }
    desc = simulacao_plano.get(conta, "[ CONTA NÃO ENCONTRADA ]" if conta else "[Informe a Conta]")
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

    tk.Label(frame, text="Total Débitos:", bg="#ece9d8").grid(row=0, column=0, padx=5, pady=5)
    self.ent_tot_deb = tk.Entry(frame, width=15, state="readonly", justify="right", font=("Tahoma", 9, "bold"))
    self.ent_tot_deb.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(frame, text="Total Créditos:", bg="#ece9d8").grid(row=0, column=2, padx=5, pady=5)
    self.ent_tot_cred = tk.Entry(frame, width=15, state="readonly", justify="right", font=("Tahoma", 9, "bold"))
    self.ent_tot_cred.grid(row=0, column=3, padx=5, pady=5)

    tk.Label(frame, text="Diferença:", bg="#ece9d8").grid(row=0, column=4, padx=5, pady=5)
    self.ent_diferenca = tk.Entry(frame, width=15, state="readonly", justify="right", font=("Tahoma", 9, "bold"), fg="red")
    self.ent_diferenca.grid(row=0, column=5, padx=5, pady=5)

    self.recalcular_totais()

  def criar_barra_botoes_principal(self):
    frame = tk.Frame(self, bg="#d4d0c8", bd=1, relief="raised")
    frame.pack(fill="x", side="bottom", padx=2, pady=2)

    btn_gravar = tk.Button(frame, text="[F8] Gravar Lote", bg="#ece9d8", relief="raised", command=self.gravar_lote)
    btn_gravar.pack(side="left", padx=5, pady=3)

    btn_limpar = tk.Button(frame, text="Novo / Limpar", bg="#ece9d8", relief="raised", command=self.limpar_formulario)
    btn_limpar.pack(side="left", padx=5, pady=3)

    btn_sair = tk.Button(frame, text="Sair", bg="#ece9d8", relief="raised", command=self.destroy)
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

    self.tree.insert("", "end", values=(item_idx, tipo, conta, desc, val_formatado, hist))

    # Limpa campos para a próxima partida
    self.ent_conta.delete(0, tk.END)
    self.ent_valor.delete(0, tk.END)
    self.lbl_nome_conta.config(text="[Informe a Conta]")
    self.cmb_tipo.focus()

    self.recalcular_totais()

  def recalcular_totais(self):
    """Soma os débitos e créditos percorrendo a Treeview e calcula a diferença das partidas dobradas."""
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

    # Atualiza as entradas do rodapé
    self.atualizar_campo_readonly(self.ent_tot_deb, self.formatar_float_para_moeda(total_deb))
    self.atualizar_campo_readonly(self.ent_tot_cred, self.formatar_float_para_moeda(total_cred))
    self.atualizar_campo_readonly(self.ent_diferenca, self.formatar_float_para_moeda(diferenca))

  def atualizar_campo_readonly(self, campo, texto):
    campo.config(state="normal")
    campo.delete(0, tk.END)
    campo.insert(0, texto)
    campo.config(state="readonly")

  def gravar_lote(self):
    """Valida as partidas dobradas antes de efetivar o lançamento."""
    if not self.tree.get_children():
      messagebox.showwarning("Aviso", "Não existem partidas lançadas neste lote.")
      return

    diferenca = self.converter_valor_para_float(self.ent_diferenca.get())

    if diferenca != 0.0:
      messagebox.showerror(
          "Erro de Partida Dobrada",
          f"O lote está desbalanceado!\n\n"
          f"Diferença entre Débitos e Créditos: R$ {self.ent_diferenca.get()}\n"
          f"Ajuste os valores antes de gravar.",
      )
      return

    messagebox.showinfo("Sucesso", f"Lote Nº {self.ent_lote.get()} gravado com sucesso!")
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