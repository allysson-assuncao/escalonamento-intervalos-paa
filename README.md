# Escalonamento de Intervalos em Sala Cirúrgica (PAA)

Projeto acadêmico da disciplina **Projeto e Análise de Algoritmos (PAA)** que estende o problema clássico de **Escalonamento de Intervalos (*Interval Scheduling / Activity Selection*)** para o contexto aplicado de uma **sala cirúrgica hospitalar** com **esterilização biológica assimétrica**, **horizonte de fechamento de turno ($H$)** e **janela opcional de troca de plantão ($[A, B]$)**.

O sistema mantém lado a lado as **duas abordagens clássicas da literatura** (Guloso e Programação Dinâmica), um **comparador por redução estática ingênua**, as **duas soluções autorais adaptadas** com otimalidade exata comprovada e mesma complexidade assintótica ($\mathcal{O}(n \log n)$ no caso geral e $\mathcal{O}(n)$ quando pré-ordenado), um **oráculo exato de força bruta ($n \le 20$)**, um **executor de benchmark empírico** e uma **interface web interativa local sem dependências externas** para demonstração ao vivo.

---

## Sumário

- [1. Problema Original vs. Adaptação Autoral](#1-problema-original-vs-adaptação-autoral)
- [2. Fórmula Fechada de Liberação Efetiva ($r_i$) e Contrexemplo `SC-02`](#2-fórmula-fechada-de-liberação-efetiva-r_i-e-contrexemplo-sc-02)
- [3. Comparativo de Complexidade Assintótica](#3-comparativo-de-complexidade-assintótica)
- [4. Arquitetura do Repositório](#4-arquitetura-do-repositório)
- [5. Instalação, Execução e Testes](#5-instalação-execução-e-testes)
- [6. Documentação Complementar](#6-documentação-complementar)

---

## 1. Problema Original vs. Adaptação Autoral

### Problema Clássico (Baseline)
- **Entrada**: conjunto de $n$ solicitações cirúrgicas, cada uma definida exclusivamente pelo intervalo ativo $[s_i, f_i]$ ($0 \le s_i < f_i$).
- **Restrição de compatibilidade**: duas cirurgias $i$ e $j$ são compatíveis se não se sobrepõem ($s_j \ge f_i$).
- **Objetivo**: selecionar um subconjunto compatível de **cardinalidade máxima**.
- **Soluções consolidadas**: *Earliest Finish Time* (Guloso) e Programação Dinâmica com busca de predecessores, ambos em $\mathcal{O}(n \log n)$ geral ou $\mathcal{O}(n)$ pré-ordenado.

### Restrições Adicionais Autorais (Centro Cirúrgico)
Para evitar tanto a quebra da Propriedade da Escolha Gulosa (como ocorreria com pesos arbitrários) quanto uma redução estática trivial ($f'_i = f_i + c_i$), o modelo distingue **ocupação médica ativa** de **esterilização automatizada passiva**:

1. **Risco Biológico Assimétrico ($t_i$ e $c_i$)**:
   - **`CLEAN`**: cirurgia limpa, sem descontaminação pesada ($c_i = 0$).
   - **`CONTAMINATED`**: cirurgia infectada, exigindo ciclo automatizado de ozônio/UV de duração $c_i > 0$ após $f_i$ antes que a próxima cirurgia comece.
2. **Viabilidade Ativa da Equipe Médica ($H$ e $[A, B]$)**:
   - A atuação médica $[s_i, f_i)$ exige equipe presente na sala; logo, uma cirurgia $i$ só é ativamente viável se:
     $$0 \le s_i < f_i \le H$$
     e, quando há janela fixa de troca de plantão $[A, B]$ ($0 \le A < B \le H$), não houver sobreposição ativa com $[A, B)$:
     $$f_i \le A \quad \text{ou} \quad s_i \ge B$$
3. **Esterilização Automatizada Passiva ($[f_i, f_i + c_i)$)**:
   - Como o equipamento de ozônio/UV opera **sem equipe médica**, o resfriamento/esterilização **pode ocorrer durante a janela $[A, B]$** e **pode estender-se além do fechamento $H$** após a última cirurgia do dia.

---

## 2. Fórmula Fechada de Liberação Efetiva ($r_i$) e Contrexemplo `SC-02`

Para toda cirurgia ativamente viável, seja $e_i = f_i + c_i$ o término bruto da esterilização. O **Instante de Liberação Efetiva ($r_i$)** — menor horário em que a sala está simultaneamente esterilizada e liberada para uma nova equipe — é calculado em $\mathcal{O}(1)$:

$$r_i = \begin{cases} B, & \text{se } [A, B] \text{ existe, } f_i \le A \text{ e } A < e_i < B \\ e_i, & \text{caso contrário} \end{cases}$$

A compatibilidade entre uma cirurgia viável $i$ e uma próxima cirurgia viável $j$ reduz-se exatamente à condição $s_j \ge r_i$.

### Prova de Não-Redutibilidade: Contrexemplo `SC-02`
Sob horizonte de fechamento $H = \text{18:00}$ (`1080` min) e três cirurgias vespertinas:

| Cirurgia | Tipo ($t_i$) | Intervalo Ativo $[s_i, f_i]$ | Esterilização ($c_i$) | $r_i$ Efetivo | Viável? |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`S1`** | `CONTAMINATED` | `13:00–14:00` | `120 min` | `16:00` | Sim (`14:00 <= 18:00`) |
| **`S2`** | `CLEAN` | `13:30–15:00` | `0 min` | `15:00` | Sim (`15:00 <= 18:00`) |
| **`S3`** | `CONTAMINATED` | `15:00–17:45` | `60 min` | `18:45` | Sim (`17:45 <= 18:00`) |

- **Guloso Clássico (`ClassicGreedyScheduler`)**: ordena por $f_i$ e escolhe `S1` primeiro (`14:00 < 15:00`). Ao ignorar $c_1 = 2\text{h}$, gera conflito físico com `S3` (`[S1, S3]` é inválido na sala real) ou bloqueia até `16:00` obtendo apenas **1 cirurgia**.
- **Redução Estática Ingênua (`NaiveReductionScheduler`, $f'_i = f_i + c_i \le H$)**: calcula $f'_3 = 18:45 > 18:00$, **descarta `S3` erroneamente** e obtém apenas **1 cirurgia** (`{S2}`).
- **Guloso Adaptado e PD Adaptada**: validam $f_i \le H$ separado de $r_i$, reconhecem $r_2 = 15:00 < r_1 = 16:00$ e selecionam o ótimo global **`{S2, S3}` (`2 cirurgias`)**.

---

## 3. Comparativo de Complexidade Assintótica

| Algoritmo | Tempo (Caso Geral) | Tempo (Pré-ordenado) | Espaço Auxiliar | Garante Ótimo Adaptado? |
| :--- | :---: | :---: | :---: | :---: |
| **Guloso Clássico** ([`classic_greedy.py`](src/schedulers/classic_greedy.py#L15-L61)) | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n)$ | $\mathcal{O}(n)$ | Não (ignora $c_i$, $H$ e $[A, B]$) |
| **PD Clássica** ([`classic_dp.py`](src/schedulers/classic_dp.py#L21-L71)) | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n)$ | $\mathcal{O}(n)$ | Não (ignora $c_i$, $H$ e $[A, B]$) |
| **Redução Ingênua** ([`naive_reduction.py`](src/schedulers/naive_reduction.py#L17-L49)) | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n)$ | $\mathcal{O}(n)$ | Não (descarta $f_i + c_i > H$) |
| **Guloso Adaptado** ([`adapted_greedy.py`](src/schedulers/adapted_greedy.py#L17-L47)) | **$\mathcal{O}(n \log n)$** | **$\mathcal{O}(n)$** | **$\mathcal{O}(n)$** | **Sim (100% exato)** |
| **PD Adaptada** ([`adapted_dp.py`](src/schedulers/adapted_dp.py#L19-L69)) | **$\mathcal{O}(n \log n)$** | **$\mathcal{O}(n)$** | **$\mathcal{O}(n)$** | **Sim (100% exato)** |
| **Oráculo Exato ($n \le 20$)** ([`brute_force_oracle.py`](src/schedulers/brute_force_oracle.py#L22-L56)) | $\mathcal{O}(2^n)$ | $\mathcal{O}(2^n)$ | $\mathcal{O}(n)$ | Sim (somente validação $n \le 20$) |

---

## 4. Arquitetura do Repositório

```text
escalonamento-intervalos-paa/
├── src/
│   ├── domain/
│   │   ├── exceptions.py          # InvalidSchedulingInputError
│   │   ├── models.py              # Modelos imutáveis (SurgeryRequest, ShiftConfig, SchedulingResult)
│   │   └── preprocessing.py       # Filtro de viabilidade ativa, cálculo de r_i e redução ingênua
│   ├── schedulers/
│   │   ├── protocol.py            # IntervalSchedulerProtocol e núcleo compartilhado de DP/ordenação
│   │   ├── classic_greedy.py      # Baseline: Guloso Clássico
│   │   ├── classic_dp.py          # Baseline: Programação Dinâmica Clássica
│   │   ├── naive_reduction.py     # Comparador: Redução Estática Ingênua (f'_i = f_i + c_i)
│   │   ├── adapted_greedy.py      # Autoral: Guloso Adaptado (Earliest Effective Release)
│   │   ├── adapted_dp.py          # Autoral: Programação Dinâmica Adaptada
│   │   └── brute_force_oracle.py  # Oráculo exato por branch-and-bound (n <= 20)
│   ├── benchmark/
│   │   └── runner.py              # Gerador sintético e executor de benchmark empírico
│   ├── ui/
│   │   ├── scenarios_catalog.py   # Catálogo canônico SC-01..SC-05b compartilhado com os testes
│   │   ├── tracer.py              # Tracer passo a passo desacoplado e Arena Comparativa
│   │   ├── server.py              # Servidor HTTP local (127.0.0.1) e API JSON validada
│   │   └── static/                # Frontend HTML5/CSS3/ES6 + SVG nativo (sem dependências)
│   └── main.py                    # Ponto de entrada unificado (Interface Web e CLI headless)
├── tests/                         # Suítes pytest (domínio, algoritmos, oráculo, UI e docs)
├── docs/                          # Relatório empírico e guia de revisão/apresentação
└── openspec/                      # Especificações canônicas e histórico de changes SDD
```

---

## 5. Instalação, Execução e Testes

### Pré-requisitos
- **Python 3.12 ou superior**. Todo o núcleo algorítmico e a interface web utilizam **exclusivamente a Biblioteca Padrão do Python** (`dependencies = []` em [`pyproject.toml`](pyproject.toml)).
- **`pytest >= 8.0.0`** (apenas para execução da suíte de testes automatizados).

### Configuração do Ambiente (`venv`)

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv

# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

# 2. Instalar dependências de desenvolvimento (pytest)
pip install -e ".[dev]"
```

### Executar a Suíte de Testes Automatizados

```bash
python -m pytest -v
```

### Executar a Interface Web Interativa (Simulador de Apresentação)

```bash
python -m src.main
```

- Abre automaticamente o navegador em `http://127.0.0.1:8765/`.
- Opções disponíveis:
  - `--host 127.0.0.1` e `--port 8765`: configura endereço/porta do servidor local.
  - `--no-browser`: inicia o servidor sem abrir nova aba automaticamente.

### Executar via Linha de Comando (*Headless* CLI)

```bash
# Comparar os 5 algoritmos em um cenário pré-configurado (ex: SC-02)
python -m src.main --scenario SC-02

# Executar benchmark empírico no modo geral O(n log n)
python -m src.main --benchmark --sizes 100 500 1000 2500 5000 10000 --repetitions 5

# Executar benchmark empírico no modo pré-ordenado O(n)
python -m src.main --benchmark --sizes 100 500 1000 2500 5000 10000 --repetitions 5 --presorted
```

---

## 6. Documentação Complementar

- 📊 **[Relatório de Testes, Benchmark e Complexidade](docs/relatorio-testes-benchmark-complexidade.md)**: análise completa dos cenários `SC-01` a `SC-05b`, validação cruzada com o Oráculo Exato em 180 instâncias aleatórias, tabelas empíricas para $n \in [100, 10000]$ e gráficos Mermaid de complexidade.
- 🎓 **[Guia de Revisão, Arquitetura e Preparação para Apresentação](docs/guia-revisao-arquitetura-e-apresentacao.md)**: explicação detalhada da arquitetura SOLID, dissecação linha a linha das funções com referências `#Lxx-Lyy`, funcionamento interno do tracer e da interface SVG, roteiro de apresentação e FAQ de defesa.
