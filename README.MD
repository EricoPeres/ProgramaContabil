# Projeto Programa Contábil 

- **cadastro_empresasv1.1.py**: cadastro geral das empresas, já está gerando o arquivo .db na pasta correta;
- **depreciacao_imobilizadov1.2.py**: cálculo da depreciação por item, falta testar mas a fundo e possíveis implementações (gerar lançamento contábil em formato excel);
- **Simples_Nacionalv1.2.py**: o cálculo está correto, falta testar mais comparando com empresas que tem mais movimento, só está pegando as empresas que foram cadastradas como Simples Nacional no cadastro de empresas, persistência de dados resolvida;
- **Calculo_Lucro_Presumidov1.3.py**: já está calculando com base na alteração da IN RFB 2306/2026 que acrecenta 10% a base presumida da parcela que exceder 1.250.000,00 no trimestre, falta fazer mais testes gerais. Acrescentar a próxima versão o valor da retenção no trimestre pra reduzir o valor a pagar. Testar o cálculo do PIS e Cofins;
- **Calculo_Lucro_Real.py**: arquivo testado, o cálculo está batendo com a planilha de Lalur, temos que informar antes do cálculo se teve prejuízo fiscal, a parte B está controlando o saldo corretamente, basta informar o saldo;
- **Calculo_PIS_Cofins_Real.py**:
- **Calculo_ISS.py**:
- **gerenciador_planov12.py**: gerenciador de planos de contas, com a importação via arquivo csv já implementada;
- **lancamento_contabilv14.py**: app de lançamento contábil já desenvolvido no tkinter, falta implementar o lançamento utilizando o plano de contas de cada empresa;