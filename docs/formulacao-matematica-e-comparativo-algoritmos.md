# Formulação Matemática e Comparativo Algorítmico

Este documento traduz toda a **notação matemática** do projeto para português claro, explicando exatamente o que muda entre o **problema clássico** da literatura e a **adaptação autoral para sala cirúrgica**, por que as soluções clássicas falham e como os 4 algoritmos funcionam passo a passo mantendo complexidade **$\mathcal{O}(n \log n)$**.

---

## Sumário

- [1. Dicionário Completo de Notação](#1-dicionário-completo-de-notação)
- [2. Formulação do Problema Clássico vs. Adaptação Autoral](#2-formulação-do-problema-clássico-vs-adaptação-autoral)
- [3. Comparativo Matemático dos 4 Algoritmos](#3-comparativo-matemático-dos-4-algoritmos)
- [4. Teste de Mesa Matemático Comparado (`CASE-02` e `CASE-03`)](#4-teste-de-mesa-matemático-comparado-case-02-e-case-03)
- [5. Dedução da Complexidade Assintótica Fase a Fase](#5-dedução-da-complexidade-assintótica-fase-a-fase)

---

## 1. Dicionário Completo de Notação

Todos os horários no código são representados como **números inteiros em minutos a partir de `00:00`** (ex.: `08:00 = 480`, `12:00 = 720`, `18:00 = 1080`).

| Símbolo | Nome / Significado | Unidade / Domínio | Onde aparece no código e na interface |
| :---: | :--- | :--- | :--- |
| $I$ | Conjunto de solicitações de cirurgia recebidas | Lista com $n$ itens | Parâmetro `surgeries` em [`schedule`](../src/schedulers/protocol.py#L25-L31) |
| $n$ | Quantidade total de cirurgias de entrada | Inteiro $n \ge 0$ | `len(items)` no pré-processamento |
| $n'$ | Quantidade de cirurgias **ativamente viáveis** | Inteiro $0 \le n' \le n$ | `len(feasible)` após filtragem |
| $i$ | Índice de uma cirurgia específica | $i \in \{1, \dots, n\}$ | `SurgeryRequest` em [`models.py`](../src/domain/models.py#L73-L122) |
| $s_i$ | Horário de **início** da atuação médica (*start*) | Inteiro $s_i \ge 0$ | `surgery.start_time` |
| $f_i$ | Horário de **término** da atuação médica (*finish*) | Inteiro $f_i > s_i$ | `surgery.finish_time` |
| $t_i$ | Risco biológico da cirurgia | $\{\text{CLEAN}, \text{CONTAMINATED}\}$ | [`SurgeryType`](../src/domain/models.py#L14-L18) |
| $c_i$ | Duração da esterilização automatizada pós-cirurgia | $c_i = 0$ (`CLEAN`) ou $c_i > 0$ (`CONTAMINATED`) | `surgery.sterilization_duration` |
| $H$ | Horizonte de fechamento do turno médico | Inteiro $H > 0$ (ex.: `1080` = `18:00`) | `shift_config.closing_horizon` |
| $[A, B]$ | Janela opcional de troca de plantão | Inteiros $0 \le A < B \le H$ (ex.: `[720, 780]`) | [`ShiftWindow`](../src/domain/models.py#L22-L41) (`start=A`, `end=B`) |
| $e_i$ | Término físico bruto da esterilização | $e_i = f_i + c_i$ | `raw_end` em [`preprocessing.py`](../src/domain/preprocessing.py#L80-L88) |
| $r_i$ | **Instante de Liberação Efetiva** (*release time*) | Inteiro $r_i \ge f_i$ | `effective_release_time` em [`ProcessedSurgery`](../src/domain/models.py#L126-L145) |
| $p(i)$ | Índice do último predecessor compatível antes de $i$ | $p(i) \in \{0, 1, \dots, i-1\}$ (`0` = nenhum) | Vetor `predecessors[i]` (`p[i]` na UI) |
| $DP[i]$ | Cardinalidade máxima usando prefixo $\{1, \dots, i\}$ | Inteiro $DP[i] \ge 0$ | Vetor `dp[i]` (`DP[i]` na UI) |
| $S^*$ | Subconjunto ótimo final de cirurgias selecionadas | $S^* \subseteq I$ | `selected_surgeries` em [`SchedulingResult`](../src/domain/models.py#L149-L186) |

---

## 2. Formulação do Problema Clássico vs. Adaptação Autoral

### 2.1. Problema Clássico (*Interval Scheduling* / *Activity Selection*)
- **Entrada**: $n$ intervalos $[s_i, f_i)$ com $0 \le s_i < f_i$.
- **Objetivo**: encontrar um subconjunto $S \subseteq I$ de **tamanho máximo** ($\max |S|$).
- **Restrição única**: para quaisquer duas cirurgias escolhidas $i$ (anterior) e $j$ (posterior), não há sobreposição:
  $$s_j \ge f_i$$
- **O que ele ignora**: não existe $c_i$ (tempo de limpeza), não existe $H$ (fechamento) e não existe $[A, B]$ (troca de plantão).

### 2.2. Problema Adaptado (Centro Cirúrgico com Esterilização e Turno)
A adaptação autoral divide o tempo pós-cirúrgico em **atuação médica ativa** (exige equipe na sala) e **esterilização automatizada passiva** (máquina de ozônio/UV operando sem equipe).

#### Diferença 1 — Predicado de Viabilidade Ativa ($\text{Viável}(i)$)
Uma cirurgia $i$ só pode ser incluída se a **atuação médica** $[s_i, f_i)$ respeitar o turno:
$$\text{Viável}(i) \iff (0 \le s_i < f_i \le H) \;\land\; \Big([A, B] = \varnothing \;\lor\; f_i \le A \;\lor\; s_i \ge B\Big)$$

- **Por que `f_i <= A` ou `s_i >= B`?**
  - Se $f_i \le A$, a equipe termina antes (ou exatamente no início) da troca de plantão.
  - Se $s_i \ge B$, a equipe só entra após (ou exatamente no fim) da troca de plantão.
  - Qualquer cirurgia que invada o intervalo semiaberto $[A, B)$ tem equipe médica ativa durante a troca e é **descartada** por [`is_actively_feasible`](../src/domain/preprocessing.py#L41-L63).

#### Diferença 2 — Esterilização Automatizada Passiva ($[f_i, e_i)$)
Para cirurgias contaminadas ($c_i > 0$), a sala fica interditada pela máquina de esterilização até:
$$e_i = f_i + c_i$$
Como não há médicos na sala durante $[f_i, e_i)$:
1. **Pode passar de $H$**: se a cirurgia termina às `17:45` ($f_i \le 18:00$) e esteriliza até `18:45`, ela **continua viável** como última cirurgia do dia.
2. **Pode cruzar $[A, B]$**: a máquina pode esterilizar em paralelo enquanto a equipe faz a troca de plantão.

#### Diferença 3 — Fórmula Fechada de Liberação Efetiva ($r_i$)
Qual o menor horário a partir do qual **outra** cirurgia $j$ pode entrar na sala após $i$? Calculado em $\mathcal{O}(1)$ por [`compute_effective_release_time`](../src/domain/preprocessing.py#L66-L88):

$$r_i = \begin{cases} B, & \text{se } [A, B] \text{ existe, } f_i \le A \text{ e } A < e_i < B \\ e_i, & \text{caso contrário} \end{cases}$$

**Os 3 casos de fronteira em relação à janela $[A, B]$:**
1. **Esterilização termina antes ou em $A$ ($e_i \le A$)**: a sala já está limpa antes da pausa, então $r_i = e_i$ (ainda cabe outra cirurgia antes de $A$ ou depois de $B$).
2. **Esterilização termina estritamente dentro de $(A, B)$ ($f_i \le A$ e $A < e_i < B$)**: embora a máquina acabe em $e_i$, nenhuma equipe pode entrar antes de $B$. Logo, a liberação efetiva **salta para $r_i = B$**.
3. **Esterilização termina em $B$ ou transborda $B$ ($e_i \ge B$)**: a sala só fica estéril em $e_i$, então $r_i = e_i$ (bloqueando até mesmo parte do início pós-pausa se $e_i > B$).

**Resultado matemático chave:** entre duas cirurgias ativamente viáveis $i$ e $j$, toda a regra de esterilização + turno se reduz a **uma única desigualdade**:
$$s_j \ge r_i$$

---

## 3. Comparativo Matemático dos 4 Algoritmos

| Aspecto | Guloso Clássico | Guloso Adaptado | PD Clássica | PD Adaptada |
| :--- | :--- | :--- | :--- | :--- |
| **Pré-processamento** | Nenhum ($r_i = f_i$) | Filtra $\text{Viável}(i)$ e calcula $r_i$ | Nenhum ($r_i = f_i$) | Filtra $\text{Viável}(i)$ e calcula $r_i$ |
| **Chave de Ordenação** | $(f_i, s_i)$ crescente | $(r_i, f_i, s_i)$ crescente | $(f_i, s_i)$ crescente | $(r_i, f_i, s_i)$ crescente |
| **Teste de Compatibilidade** | $s_i \ge f_{\text{última}}$ | $s_i \ge r_{\text{última}}$ | $p(i) = \max\{j < i \mid f_j \le s_i\}$ | $p(i) = \max\{j < i \mid r_j \le s_i\}$ |
| **Recorrência / Seleção** | Varredura linear | Varredura linear | $DP[i] = \max(DP[i-1], 1 + DP[p(i)])$ | $DP[i] = \max(DP[i-1], 1 + DP[p(i)])$ |
| **Complexidade Total** | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n \log n)$ |

### 3.1. Por que o Guloso Adaptado continua 100% Ótimo? (*Exchange Argument*)
No problema clássico, escolher o menor $f_i$ deixa a sala livre o mais cedo possível. Na versão adaptada, depois de filtrar as cirurgias ativamente viáveis, o instante em que a sala realmente volta a ficar utilizável é **$r_i$** (e não $f_i$).
- Seja $G = \{g_1, g_2, \dots, g_k\}$ a agenda do Guloso Adaptado (ordenado por menor $r_i$) e $O = \{o_1, o_2, \dots, o_m\}$ qualquer agenda ótima válida em ordem cronológica.
- Como $g_1$ tem o menor $r_i$ possível entre todas as cirurgias viáveis, $r_{g_1} \le r_{o_1}$. Logo, podemos trocar $o_1$ por $g_1$ em $O$ sem conflitar com $o_2$ (pois $s_{o_2} \ge r_{o_1} \ge r_{g_1}$).
- Por indução (*"Greedy Stays Ahead"*), no passo $t$, $r_{g_t} \le r_{o_t}$ garante que $o_{t+1}$ continua elegível e $r_{g_{t+1}} \le r_{o_{t+1}}$. Logo $k = m$.

### 3.2. Como a Programação Dinâmica Adaptada Funciona?
1. Ordenam-se as $n'$ cirurgias viáveis por $r_1 \le r_2 \le \dots \le r_{n'}$.
2. Para cada posição $i \in \{1, \dots, n'\}$, como os valores de $r_j$ estão ordenados crescentemente, todas as cirurgias compatíveis antes de $i$ formam um **prefixo contínuo** $\{1, \dots, p(i)\}$, encontrado por **busca binária** (`bisect_right`) em $\mathcal{O}(\log n')$:
   $$p(i) = \max\big(\{0\} \cup \{j \in \{1, \dots, i-1\} \mid r_j \le s_i\}\big)$$
3. Define-se $DP[0] = 0$ e, para $i = 1 \dots n'$:
   $$DP[i] = \max\big(DP[i - 1],\; 1 + DP[p(i)]\big)$$
   - **Excluir $i$**: mantém a melhor solução até $i-1$ (`DP[i - 1]`).
   - **Incluir $i$**: soma $1$ à melhor solução compatível antes de $i$ (`1 + DP[p(i)]`).
4. **Reconstrução (*Backtracking*)**: partindo de $i = n'$, se $1 + DP[p(i)] > DP[i - 1]$, incluímos a cirurgia $i$ e saltamos para $i \leftarrow p(i)$; caso contrário, ignoramos $i$ e recuamos para $i \leftarrow i - 1$.

---

## 4. Teste de Mesa Matemático Comparado (`CASE-02` e `CASE-03`)

### 4.1. `CASE-02` — Esterilização ($c_i$) e Horizonte ($H = 18:00 = 1080$)

**Entrada:**
- `S1`: $[13:00, 14:00]$ (`[780, 840]`), `CONTAMINATED`, $c_1 = 120$ min $\implies e_1 = 960$ (`16:00`).
- `S2`: $[13:30, 15:00]$ (`[810, 900]`), `CLEAN`, $c_2 = 0$ min $\implies e_2 = 900$ (`15:00`).
- `S3`: $[15:00, 17:45]$ (`[900, 1065]`), `CONTAMINATED`, $c_3 = 60$ min $\implies e_3 = 1125$ (`18:45`).

**O que os Clássicos fazem (Erro por ignorar $c_i$):**
1. Ordenam por $f_i$: `[S1 (14:00), S2 (15:00), S3 (17:45)]`.
2. **Guloso Clássico**: escolhe `S1` (`last_finish = 14:00`), rejeita `S2` (`13:30 < 14:00`) e escolhe `S3` (`15:00 >= 14:00`).
3. **PD Clássica**: `p = [0, 0, 2]`, `DP = [0, 1, 1, 2]`, também escolhe `{S1, S3}`.
4. **Por que falha?** Na sala real, `S1` só termina a esterilização às `16:00`, logo `{S1, S3}` gera **conflito físico** (`S3` inicia às `15:00 < 16:00`).
5. *(Nota: uma soma ingênua $f'_i = f_i + c_i \le H$ descartaria `S3` porque `18:45 > 18:00`, ficando presa em 1 cirurgia.)*

**O que os Adaptados fazem (Acerto exato):**
1. **Pré-processamento**: todas têm $f_i \le 1080$, logo todas permanecem viáveis ($n' = 3$). Valores: $r_1 = 960$ (`16:00`), $r_2 = 900$ (`15:00`), $r_3 = 1125$ (`18:45`).
2. **Ordenação por $r_i$**: `[1: S2 (15:00), 2: S1 (16:00), 3: S3 (18:45)]`.
3. **Guloso Adaptado**:
   - `i=1 (S2)`: `13:30 >= -1` $\implies$ **seleciona `S2`**, `last_release = 15:00`.
   - `i=2 (S1)`: `13:00 < 15:00` $\implies$ rejeita `S1`.
   - `i=3 (S3)`: `15:00 >= 15:00` $\implies$ **seleciona `S3`**, `last_release = 18:45`.
4. **PD Adaptada**:
   - Predecessores por busca binária: `p[1] = 0` (`S2`), `p[2] = 0` (`S1`), `p[3] = 1` (`S3` compatível com `S2` pois $900 \le 900$).
   - Tabela DP: `DP[0] = 0`, `DP[1] = 1`, `DP[2] = max(1, 1 + DP[0]) = 1`, `DP[3] = max(1, 1 + DP[1]) = 2`.
   - *Backtracking*: `i=3`: $1 + DP[1] = 2 > DP[2] = 1$ (pega `S3`, salta para `1`); `i=1`: $1 + DP[0] = 1 > DP[0] = 0$ (pega `S2`, salta para `0`).
   - Resultado idêntico: **`{S2, S3}` (2 cirurgias válidas)**.

---

### 4.2. `CASE-03` — Janela de Troca de Plantão $[A, B] = [12:00, 13:00]$ (`[720, 780]`)

**Entrada ($H = 18:00$):**
- `S1`: `10:00–11:30`, `CONTAMINATED`, $c_1 = 60$ $\implies e_1 = 12:30 \in (12:00, 13:00) \implies$ **`r_1 = 13:00` (`780`, salto para $B$)**.
- `S2`: `11:30–12:30`, `CLEAN` $\implies$ invade `[12:00, 13:00)` $\implies$ **descartada**.
- `S3`: `12:30–14:00`, `CLEAN` $\implies$ invade `[12:00, 13:00)` $\implies$ **descartada**.
- `S4`: `13:00–15:00`, `CONTAMINATED`, $c_4 = 30$ $\implies r_4 = 15:30$.
- `S5`: `15:30–17:30`, `CLEAN` $\implies r_5 = 17:30$.

**Comparação:**
- **Clássicos**: ignoram a troca de plantão e $c_1$, selecionando `{S1, S2, S3, S5}` (múltiplos conflitos com `[12:00, 13:00)` e com a esterilização de `S1`).
- **Adaptados**: descartam `S2` e `S3` no pré-processamento ($n'=3$), ajustam $r_1 = B = 13:00$ e selecionam exatamente **`{S1, S4, S5}` (3 cirurgias válidas)**, pois `S4` inicia às `13:00 >= r_1` e `S5` inicia às `15:30 >= r_4`.

---

## 5. Dedução da Complexidade Assintótica Fase a Fase

| Fase do Algoritmo | Guloso Clássico | Guloso Adaptado | PD Clássica | PD Adaptada |
| :--- | :---: | :---: | :---: | :---: |
| **1. Validação / Pré-processamento** | $\mathcal{O}(n)$ | $\mathcal{O}(n)$ | $\mathcal{O}(n)$ | $\mathcal{O}(n)$ |
| **2. Ordenação (Timsort)** | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n \log n)$ |
| **3. Busca de Predecessores $p(i)$** | — | — | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n \log n)$ |
| **4. Seleção Linear / Tabela DP + Backtracking** | $\mathcal{O}(n)$ | $\mathcal{O}(n)$ | $\mathcal{O}(n)$ | $\mathcal{O}(n)$ |
| **Tempo Total ($T(n)$)** | **$\mathcal{O}(n \log n)$** | **$\mathcal{O}(n \log n)$** | **$\mathcal{O}(n \log n)$** | **$\mathcal{O}(n \log n)$** |
| **Espaço Auxiliar** | **$\mathcal{O}(n)$** | **$\mathcal{O}(n)$** | **$\mathcal{O}(n)$** | **$\mathcal{O}(n)$** |

- **Por que a busca de predecessores da PD é $\mathcal{O}(n \log n)$?**
  Em [`compute_predecessors_binary_search`](../src/schedulers/protocol.py#L79-L90), o laço executa $n'$ iterações; em cada iteração $i$, `bisect.bisect_right` realiza no máximo $\lceil \log_2(i + 1) \rceil \le \lceil \log_2 n \rceil$ comparações. Logo, $\sum_{i=1}^{n'} \mathcal{O}(\log i) = \mathcal{O}(n \log n)$.
- **Por que o Oráculo Exato é $\mathcal{O}(2^n)$?**
  Em [`_search_exact_optimum`](../src/schedulers/brute_force_oracle.py#L57-L84), cada cirurgia gera até duas ramificações recursivas (*incluir* vs. *excluir*), totalizando até $2^n$ folhas no pior caso (mitigado por poda *branch-and-bound* e bloqueado para $n > 20$).
