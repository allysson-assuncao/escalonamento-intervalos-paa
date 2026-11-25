# Escalonamento de Intervalos em Sala Cirúrgica (PAA)

Projeto acadêmico da disciplina **Projeto e Análise de Algoritmos (PAA)** que estende o problema clássico de **Escalonamento de Intervalos (*Interval Scheduling / Activity Selection*)** para uma **sala cirúrgica hospitalar** com **esterilização biológica assimétrica**, **horizonte de fechamento de turno ($H$)** e **janela opcional de troca de plantão ($[A, B]$)**.

O sistema mantém lado a lado os **4 algoritmos principais** em complexidade **$\mathcal{O}(n \log n)$** (Guloso Clássico, Programação Dinâmica Clássica, Guloso Adaptado e Programação Dinâmica Adaptada), além de um **Oráculo Exato por força bruta ($n \le 20$)** para validação nos testes automatizados e uma **interface web local em 2 abas (sem dependências externas)** para demonstração passo a passo e comparação visual em sala.

---

## Sumário

- [1. Problema Original vs. Adaptação Autoral](#1-problema-original-vs-adaptação-autoral)
- [2. Fórmula Fechada de Liberação Efetiva ($r_i$) e Contrexemplo `CASE-02`](#2-fórmula-fechada-de-liberação-efetiva-r_i-e-contrexemplo-case-02)
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
- **Soluções consolidadas**: *Earliest Finish Time* (Guloso) e Programação Dinâmica não ponderada com busca binária de predecessores, ambos em $\mathcal{O}(n \log n)$.

### Restrições Adicionais Autorais (Centro Cirúrgico)
Para preservar tanto a **Propriedade da Escolha Gulosa** quanto a complexidade **$\mathcal{O}(n \log n)$**, evitando que o problema se reduza a um simples $f'_i = f_i + c_i$, o modelo separa **atuação médica ativa** de **esterilização automatizada passiva**:

1. **Risco Biológico Assimétrico ($t_i$ e $c_i$)**:
   - **`CLEAN`**: cirurgia limpa, sem necessidade de descontaminação pesada ($c_i = 0$).
   - **`CONTAMINATED`**: cirurgia infectada, exigindo ciclo automatizado de ozônio/UV de duração $c_i > 0$ após $f_i$ antes que a próxima cirurgia comece.
2. **Viabilidade Ativa da Equipe Médica ($H$ e $[A, B]$)**:
   - A atuação médica $[s_i, f_i)$ exige equipe presente; logo, uma cirurgia $i$ só é ativamente viável se:
     $$0 \le s_i < f_i \le H$$
     e, quando há janela fixa de troca de plantão $[A, B]$ ($0 \le A < B \le H$), não houver sobreposição ativa com $[A, B)$:
     $$f_i \le A \quad \text{ou} \quad s_i \ge B$$
3. **Esterilização Automatizada Passiva ($[f_i, f_i + c_i)$)**:
   - Como o equipamento de ozônio/UV opera **sem equipe médica**, a esterilização **pode ocorrer durante a janela $[A, B]$** e **pode estender-se após o fechamento $H$** depois da última cirurgia do dia.

---

## 2. Fórmula Fechada de Liberação Efetiva ($r_i$) e Contrexemplo `CASE-02`

Para toda cirurgia ativamente viável, seja $e_i = f_i + c_i$ o término físico da esterilização. O **Instante de Liberação Efetiva ($r_i$)** — menor horário em que a sala está simultaneamente esterilizada e liberada para uma nova equipe — é calculado em $\mathcal{O}(1)$:

$$r_i = \begin{cases} B, & \text{se } [A, B] \text{ existe, } f_i \le A \text{ e } A < e_i < B \\ e_i, & \text{caso contrário} \end{cases}$$

A compatibilidade entre uma cirurgia viável $i$ e uma próxima cirurgia viável $j$ resume-se exatamente à desigualdade $s_j \ge r_i$.

### Prova de Não-Redutibilidade: Contrexemplo `CASE-02`
Sob horizonte de fechamento $H = \text{18:00}$ (`1080` min) e três cirurgias vespertinas:

| Cirurgia | Tipo ($t_i$) | Intervalo Ativo $[s_i, f_i]$ | Esterilização ($c_i$) | $r_i$ Efetivo | Viável ($f_i \le 18:00$)? |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`S1`** | `CONTAMINATED` | `13:00–14:00` | `120 min` | `16:00` | Sim (`14:00 <= 18:00`) |
| **`S2`** | `CLEAN` | `13:30–15:00` | `0 min` | `15:00` | Sim (`15:00 <= 18:00`) |
| **`S3`** | `CONTAMINATED` | `15:00–17:45` | `60 min` | `18:45` | Sim (`17:45 <= 18:00`) |

- **Abordagens Clássicas (Guloso e PD Clássicos)**: ordenam apenas por $f_i$ e escolhem `{S1, S3}` ignorando que `S1` esteriliza até `16:00` — gerando **conflito físico real** com `S3` (`15:00 < 16:00`).
- **Redução Ingênua ($f'_i = f_i + c_i \le H$)**: descartaria `S3` porque $18:45 > 18:00$, atingindo apenas **1 cirurgia**.
- **Guloso Adaptado e PD Adaptada**: separam viabilidade ativa ($f_i \le H$) de $r_i$, reconhecem $r_2 = 15:00 < r_1 = 16:00$ e encontram o ótimo global válido **`{S2, S3}` (`2 cirurgias`)**.

---

## 3. Comparativo de Complexidade Assintótica

| Algoritmo | Tempo Total | Espaço Auxiliar | Garante Ótimo Adaptado? |
| :--- | :---: | :---: | :---: |
| **Guloso Clássico** ([`classic_greedy.py`](src/schedulers/classic_greedy.py#L15-L58)) | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n)$ | Não (ignora $c_i$, $H$ e $[A, B]$) |
| **PD Clássica** ([`classic_dp.py`](src/schedulers/classic_dp.py#L19-L51)) | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n)$ | Não (ignora $c_i$, $H$ e $[A, B]$) |
| **Guloso Adaptado** ([`adapted_greedy.py`](src/schedulers/adapted_greedy.py#L17-L45)) | **$\mathcal{O}(n \log n)$** | **$\mathcal{O}(n)$** | **Sim (100% exato)** |
| **PD Adaptada** ([`adapted_dp.py`](src/schedulers/adapted_dp.py#L17-L45)) | **$\mathcal{O}(n \log n)$** | **$\mathcal{O}(n)$** | **Sim (100% exato)** |
| **Oráculo Exato ($n \le 20$)** ([`brute_force_oracle.py`](src/schedulers/brute_force_oracle.py#L22-L54)) | $\mathcal{O}(2^n)$ | $\mathcal{O}(n)$ | Sim (usado apenas em testes com $n \le 20$) |

---

## 4. Arquitetura do Repositório

```text
escalonamento-intervalos-paa/
├── src/
│   ├── domain/
│   │   ├── exceptions.py          # InvalidSchedulingInputError
│   │   ├── models.py              # Modelos imutáveis (SurgeryRequest, ShiftConfig, SchedulingResult)
│   │   └── preprocessing.py       # Filtro de viabilidade ativa e cálculo de liberação efetiva r_i
│   ├── schedulers/
│   │   ├── protocol.py            # IntervalSchedulerProtocol e núcleo compartilhado de DP/ordenação
│   │   ├── classic_greedy.py      # Baseline: Guloso Clássico
│   │   ├── classic_dp.py          # Baseline: Programação Dinâmica Clássica
│   │   ├── adapted_greedy.py      # Autoral: Guloso Adaptado (Earliest Effective Release)
│   │   ├── adapted_dp.py          # Autoral: Programação Dinâmica Adaptada
│   │   └── brute_force_oracle.py  # Oráculo exato por branch-and-bound (n <= 20)
│   ├── ui/
│   │   ├── scenarios_catalog.py   # 4 cenários didáticos (CASE-01..CASE-04) compartilhados com os testes
│   │   ├── tracer.py              # Tracer passo a passo, resumo de complexidade e comparativo
│   │   ├── server.py              # Servidor HTTP local (127.0.0.1) e API JSON validada
│   │   └── static/                # Frontend HTML5/CSS3/ES6 + SVG nativo em 2 abas
│   └── main.py                    # Ponto de entrada unificado (Interface Web e CLI --scenario)
├── tests/                         # Suítes pytest (domínio, algoritmos, 180 instâncias oráculo, UI e docs)
├── docs/                          # Guia enxuto de revisão, arquitetura e apresentação
└── openspec/                      # Especificações canônicas e histórico de changes SDD
```

---

## 5. Instalação, Execução e Testes

### Pré-requisitos
- **Python 3.12 ou superior**. Todo o projeto em execução usa **exclusivamente a Biblioteca Padrão do Python** (`dependencies = []` em [`pyproject.toml`](pyproject.toml)).
- **`pytest >= 8.0.0`** (apenas para rodar a suíte de testes automatizados).

### Configuração Rápida (`venv`)

```bash
python -m venv .venv
# Linux / macOS: source .venv/bin/activate
# Windows (PowerShell): .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### Executar os Testes Automatizados

```bash
python -m pytest -v
```

### Abrir a Interface Web de Apresentação

```bash
python -m src.main
```

- Abre automaticamente o navegador em `http://127.0.0.1:8765/`.
- Opções opcionais: `--host`, `--port` e `--no-browser`.

### Executar Cenários via Terminal (*Headless* CLI)

```bash
# Comparar os 4 algoritmos em um cenário padrão (CASE-01 a CASE-04)
python -m src.main --scenario CASE-02

# Filtrar para um algoritmo específico
python -m src.main --scenario CASE-04 --algorithm adapted_dp
```

---

## 6. Documentação Complementar

- 📐 **[Formulação Matemática e Comparativo Algorítmico](docs/formulacao-matematica-e-comparativo-algoritmos.md)**: dicionário completo de notação ($s_i, f_i, c_i, H, [A, B], e_i, r_i, p(i), DP[i]$), comparação matemática formal entre as abordagens clássicas e adaptadas, testes de mesa em `CASE-02`/`CASE-03` e dedução de complexidade.
- 🎓 **[Guia de Revisão, Arquitetura e Preparação para Apresentação](docs/guia-revisao-arquitetura-e-apresentacao.md)**: explicação detalhada dos métodos principais com parâmetros, retornos e fluxo interno (`#Lxx-Lyy`), funcionamento do tracer/interface em 2 abas, checklist guiado de validação da UI (`Ação → Resultado`), roteiro em dupla no DataShow e FAQ da banca.
