import streamlit as st
import pandas as pd
import io
from itertools import combinations

# CSS personalizado para estilizar a aplicação
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    /* Estilo geral */
    body {
        font-family: 'Poppins', sans-serif;
        background-color: #F5F5F5;
        color: #333333;
    }

    /* Container principal */
    .main-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }

    /* Logo */
    .logo {
        display: block;
        margin: 0 auto 20px auto;
        max-width: 300px;
    }

    /* Títulos */
    h1 {
        color: #FF6200; /* Cor laranja do logo */
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 20px;
    }

    h2 {
        color: #003087;
        font-size: 1.5rem;
        font-weight: 600;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    /* Cards para os campos de entrada */
    .card {
        background-color: #FFFFFF;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 20px;
        margin-bottom: 20px;
    }

    /* Estilo dos inputs */
    .stTextInput, .stNumberInput, .stSelectbox {
        margin-bottom: 15px;
    }

    /* Estilo dos botões */
    .stButton>button {
        background-color: #FF6200;
        color: #333333; /* Texto em cinza escuro para melhor contraste */
        font-weight: 600;
        border: none;
        border-radius: 5px;
        padding: 10px 20px;
        transition: background-color 0.3s;
    }

    .stButton>button:hover {
        background-color: #E05500;
    }

    /* Estilo da tabela */
    .stDataFrame {
        background-color: #FFFFFF;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 20px;
    }

    /* Separadores */
    hr {
        border: 0;
        height: 1px;
        background: #E0E0E0;
        margin: 20px 0;
    }

    /* Mensagens de erro */
    .stError {
        color: #FF6200;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Dicionário com os fatores de combinação ψ₀, ψ₁, ψ₂ conforme Tabela 2 da ABNT NBR 8800
ACTION_FACTORS = {
    "Locais sem predominância de pesos/equipamentos fixos ou elevadas concentrações de pessoas": {"ψ₀": 0.5, "ψ₁": 0.4, "ψ₂": 0.3},
    "Locais com predominância de pesos/equipamentos fixos ou elevadas concentrações de pessoas": {"ψ₀": 0.7, "ψ₁": 0.6, "ψ₂": 0.4},
    "Bibliotecas, arquivos, depósitos, oficinas, garagens e coberturas": {"ψ₀": 0.8, "ψ₁": 0.7, "ψ₂": 0.6},
    "Pressão dinâmica do vento nas estruturas em geral": {"ψ₀": 0.6, "ψ₁": 0.3, "ψ₂": 0.0},
    "Variações uniformes de temperatura em relação à média anual local": {"ψ₀": 0.6, "ψ₁": 0.5, "ψ₂": 0.3},
    "Passarelas de pedestres": {"ψ₀": 0.6, "ψ₁": 0.4, "ψ₂": 0.3},
    "Vigas de rolamento de pontes rolantes": {"ψ₀": 1.0, "ψ₁": 0.8, "ψ₂": 0.5},
    "Pilares e subestruturas que suportem vigas de rolamento de pontes rolantes": {"ψ₀": 0.7, "ψ₁": 0.6, "ψ₂": 0.4}
}

# Função para determinar os fatores de ponderação com base no tipo e frequência
def get_factors(load, frequency, is_main=False):
    load_type = load["type"]
    if load_type == "Permanente":
        if frequency in ["Normal", "Frequente", "Rara", "Acidental"]:
            return 1.25 if "Normal" in frequency else 1.0
        return 1.0
    elif load_type == "Variável":
        psi_0 = load["factors"]["ψ₀"]
        psi_1 = load["factors"]["ψ₁"]
        psi_2 = load["factors"]["ψ₂"]
        if frequency == "Normal":
            return 1.5 if is_main else psi_0
        elif frequency == "Frequente":
            return 1.05 if is_main else (psi_1 if "ELS" in frequency else 1.4)
        elif frequency == "Rara":
            return 1.4 if is_main else 0.6
        elif frequency == "ELS Normal":
            return 1.0
        elif frequency == "ELS Frequente - Danos Reversíveis":
            return psi_1 if is_main else 0.0
        elif frequency == "ELS Frequente - Danos Irreversíveis":
            return 1.0 if is_main else 0.0
        elif frequency == "ELS Quase Permanente":
            return psi_2 if is_main else 0.0
        elif frequency == "ELS Rara":
            return 1.0 if is_main else 0.0
    elif load_type == "Excepcional":
        if frequency == "Acidental":
            return 1.6
        return 1.4 if "Rara" in frequency else 1.0
    return 1.0

# Função para calcular o carregamento total Q [kN/m²]
def calculate_q(loads, combination_str):
    q_total = 0.0
    parts = combination_str.split()
    for i in range(0, len(parts), 2):
        load_idx = int(parts[i]) - 1
        factor = float(parts[i + 1])
        load_value = loads[load_idx]["value"]
        q_total += load_value * factor
    return round(q_total, 3)

# Função para gerar combinações de carga (mínimo 40)
def generate_combinations(loads):
    combinations_list = []
    idx = 1

    # Separar cargas por tipo
    permanent_loads = [(i+1, load["name"]) for i, load in enumerate(loads) if load["type"] == "Permanente"]
    variable_loads = [(i+1, load["name"]) for i, load in enumerate(loads) if load["type"] == "Variável"]
    exceptional_loads = [(i+1, load["name"]) for i, load in enumerate(loads) if load["type"] == "Excepcional"]

    # Função auxiliar para adicionar combinações
    def add_combination(perms, vars, freq, type_state, criterion, idx):
        nonlocal combinations_list
        combination = []
        for i, _ in perms:
            combination.extend([str(i), str(get_factors(loads[i-1], freq))])
        for i, _ in vars:
            is_main = (len(vars) == 1 and i == vars[0][0]) or (len(vars) > 1 and i == vars[0][0])
            factor = get_factors(loads[i-1], freq, is_main)
            if factor > 0:
                combination.extend([str(i), str(factor)])
        combination_str = " ".join(combination)
        if combination_str:
            q_value = calculate_q(loads, combination_str)
            freq_display = freq.replace("ELS ", "").split(" - ")[0]
            combinations_list.append([idx, combination_str, type_state, freq_display, criterion, q_value])
        return idx + 1

    # 1. ELU Normal: Cada variável como principal, outras como secundárias (usando ψ₀)
    for main_var_idx, _ in variable_loads:
        idx = add_combination(permanent_loads, [(main_var_idx, "")] + [(i, "") for i, _ in variable_loads if i != main_var_idx], 
                            "Normal", "ELU", "Resistência", idx)

    # 2. ELU Frequente: Cada variável como principal, outras com fator 1.4 (vento)
    for main_var_idx, _ in variable_loads:
        idx = add_combination(permanent_loads, [(main_var_idx, "")] + [(i, "") for i, _ in variable_loads if i != main_var_idx], 
                            "Frequente", "ELU", "Resistência", idx)

    # 3. ELU Rara: Cada variável (vento) como principal
    for main_var_idx, _ in variable_loads:
        idx = add_combination(permanent_loads, [(main_var_idx, "")] + [(i, "") for i, _ in variable_loads if i != main_var_idx], 
                            "Rara", "ELU", "Resistência", idx)

    # 4. ELU Acidental: Cada excepcional como principal
    for exc_idx, _ in exceptional_loads:
        combination = []
        for i, _ in permanent_loads:
            combination.extend([str(i), str(get_factors(loads[i-1], "Acidental"))])
        combination.extend([str(exc_idx), str(get_factors(loads[exc_idx-1], "Acidental"))])
        combination_str = " ".join(combination)
        q_value = calculate_q(loads, combination_str)
        combinations_list.append([idx, combination_str, "ELU", "Acidental", "Resistência", q_value])
        idx += 1

    # 5. ELS Quase Permanente: Todas as permanentes + cada variável com ψ₂ (Conforto Visual)
    for var_idx, _ in variable_loads:
        idx = add_combination(permanent_loads, [(var_idx, "")], "ELS Quase Permanente", "ELS", "Conforto Visual", idx)

    # 6. ELS Frequente - Danos Reversíveis: Cada variável com ψ₁
    for var_idx, _ in variable_loads:
        idx = add_combination([], [(var_idx, "")], "ELS Frequente - Danos Reversíveis", "ELS", "Danos Reversíveis", idx)

    # 7. ELS Frequente - Danos Irreversíveis: Cada variável com 1.0
    for var_idx, _ in variable_loads:
        idx = add_combination([], [(var_idx, "")], "ELS Frequente - Danos Irreversíveis", "ELS", "Danos Irreversíveis", idx)

    # 8. ELS Rara: Cada variável com 1.0 (Danos Irreversíveis)
    for var_idx, _ in variable_loads:
        idx = add_combination([], [(var_idx, "")], "ELS Rara", "ELS", "Danos Irreversíveis", idx)

    # 9. Combinações apenas com permanentes (para preencher até 40, se necessário)
    while len(combinations_list) < 40:
        combination = []
        for i, _ in permanent_loads:
            combination.extend([str(i), str(get_factors(loads[i-1], "Normal" if idx % 2 == 0 else "ELS Normal"))])
        combination_str = " ".join(combination)
        q_value = calculate_q(loads, combination_str) if combination_str else 0.0
        combinations_list.append([idx, combination_str, "ELU" if idx % 2 == 0 else "ELS", 
                                "Normal" if idx % 2 == 0 else "Quase Permanente", 
                                "Resistência" if idx % 2 == 0 else "Conforto Visual", q_value])
        idx += 1

    return combinations_list

# Interface Streamlit com novo layout
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# Adicionar o logo no topo
st.markdown('<img src="https://imgur.com/a/BNWw8KX alt="Nascoli Engenharia" class="logo">', unsafe_allow_html=True)

st.title("Gerador de Combinações de Carga para Estruturas Metálicas")
st.write("Insira no mínimo 4 carregamentos para gerar as combinações de carga conforme ABNT NBR 8800 (mínimo 40 combinações).")

# Entrada de número de carregamentos (mínimo 4)
num_loads = st.number_input("Quantidade de carregamentos (mínimo 4, máximo 10):", min_value=4, max_value=10, value=4, step=1)

# Entrada dos carregamentos
loads = []
for i in range(num_loads):
    st.markdown(f'<div class="card">', unsafe_allow_html=True)
    st.markdown(f"### Carregamento {i+1} 🏗️")
    name = st.text_input(f"Nome do carregamento {i+1}", value=f"Carregamento {i+1}", key=f"name_{i}")
    load_type = st.selectbox(f"Tipo do carregamento {i+1}", ["Permanente", "Variável", "Excepcional"], key=f"type_{i}")
    value = st.number_input(f"Valor do carregamento {i+1} (kN/m²)", min_value=0.0, value=0.0, step=0.01, key=f"value_{i}")
    
    # Se for uma ação variável, permitir escolher a categoria e associar os fatores ψ
    factors = {"ψ₀": 1.0, "ψ₁": 1.0, "ψ₂": 1.0}  # Valores padrão para Permanente e Excepcional
    if load_type == "Variável":
        action_type = st.selectbox(
            f"Categoria da ação variável {i+1} (Tabela 2 - ABNT NBR 8800)",
            list(ACTION_FACTORS.keys()),
            key=f"action_type_{i}"
        )
        factors = ACTION_FACTORS[action_type]
        st.write(f"Fatores para '{action_type}': ψ₀ = {factors['ψ₀']}, ψ₁ = {factors['ψ₁']}, ψ₂ = {factors['ψ₂']}")
    elif load_type == "Excepcional":
        factors = {"ψ₀": 1.0, "ψ₁": 1.0, "ψ₂": 1.0}  # Para ações excepcionais (ex.: sismos)

    loads.append({"name": name, "type": load_type, "value": value, "factors": factors})
    st.markdown('</div>', unsafe_allow_html=True)

# Botão para gerar combinações
if st.button("Gerar Combinações"):
    if loads and any(load["value"] > 0 for load in loads):
        # Gerar combinações
        combinations_data = generate_combinations(loads)
        
        # Criar DataFrame
        df = pd.DataFrame(combinations_data, columns=["Nº", "Combinação de Carga", "Tipo", "Frequência", "Critério", "Q [kN/m²]"])
        
        # Exibir tabela na interface
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Combinações Geradas 📊")
        st.dataframe(df)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Exportar para Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Combinações")
        excel_data = output.getvalue()
        
        # Botão para download
        st.download_button(
            label="Baixar arquivo .xlsx",
            data=excel_data,
            file_name="combinacoes_carga.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Por favor, insira pelo menos um carregamento com valor maior que 0.")

st.markdown('</div>', unsafe_allow_html=True)
