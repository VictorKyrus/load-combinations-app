import streamlit as st
import pandas as pd
import io
from itertools import combinations

# CSS personalizado para estilizar a aplicação no estilo do site da TQS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');

    /* Estilo geral */
    body {
        font-family: 'Roboto', sans-serif;
        background-color: #F5F5F5;
        color: #333333;
    }

    /* Container principal */
    .main-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
    }

    /* Títulos */
    h1 {
        color: #003087; /* Azul escuro */
        font-size: 2rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 20px;
    }

    h2 {
        color: #003087;
        font-size: 1.5rem;
        font-weight: 500;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    /* Cards para os campos de entrada */
    .card {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        padding: 20px;
        margin-bottom: 20px;
    }

    /* Estilo dos inputs */
    .stTextInput, .stNumberInput, .stSelectbox, .stCheckbox {
        margin-bottom: 15px;
    }

    .stTextInput input, .stNumberInput input, .stSelectbox select {
        border: 1px solid #E0E0E0 !important;
        border-radius: 4px !important;
        padding: 8px !important;
        background-color: #FFFFFF !important;
    }

    .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox select:focus {
        border-color: #003087 !important;
        box-shadow: 0 0 0 2px rgba(0, 48, 135, 0.2) !important;
    }

    /* Estilo dos checkboxes */
    .stCheckbox label {
        font-size: 1rem;
        color: #333333;
    }

    /* Estilo dos botões */
    .stButton>button {
        background-color: #1A5C34; /* Verde escuro */
        color: #FFFFFF;
        font-weight: 500;
        border: none;
        border-radius: 4px;
        padding: 10px 20px;
        transition: background-color 0.3s;
    }

    .stButton>button:hover {
        background-color: #2E7D32; /* Verde mais claro no hover */
    }

    /* Estilo da tabela */
    .stDataFrame {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        padding: 20px;
    }

    .stDataFrame table {
        width: 100%;
        border-collapse: collapse;
    }

    .stDataFrame th {
        background-color: #F5F5F5;
        color: #003087;
        font-weight: 500;
        padding: 10px;
        border-bottom: 1px solid #E0E0E0;
    }

    .stDataFrame td {
        padding: 10px;
        border-bottom: 1px solid #E0E0E0;
    }

    .stDataFrame tr:nth-child(even) {
        background-color: #FAFAFA;
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
        color: #D32F2F;
        font-weight: 500;
    }
    </style>
""", unsafe_allow_html=True)

# Dicionário com as categorias de ação conforme Tabela 1 da ABNT NBR 8800:2008
ACTION_CATEGORIES = {
    # Ações Permanentes
    "G_Me": {"type": "permanente", "gamma": {"Normal": 1.25, "Especial": 1.15, "Excepcional": 1.10}, "is_wind": False},  # Peso próprio de estruturas metálicas
    "G_Pr": {"type": "permanente", "gamma": {"Normal": 1.30, "Especial": 1.20, "Excepcional": 1.15}, "is_wind": False},  # Peso próprio de estruturas pré-fabricadas
    "G_Si": {"type": "permanente", "gamma": {"Normal": 1.35, "Especial": 1.25, "Excepcional": 1.15}, "is_wind": False},  # Peso próprio de estruturas construídas in situ
    "G_Ec": {"type": "permanente", "gamma": {"Normal": 1.40, "Especial": 1.30, "Excepcional": 1.20}, "is_wind": False},  # Elementos construtivos industrializados com adição in situ
    "G_Eg": {"type": "permanente", "gamma": {"Normal": 1.50, "Especial": 1.40, "Excepcional": 1.30}, "is_wind": False},  # Elementos construtivos em geral e equipamentos
    "SET": {"type": "permanente", "gamma": {"Normal": 1.35, "Especial": 1.25, "Excepcional": 1.15}, "is_wind": False},   # Assentamentos de apoios, retrações

    # Ações Variáveis
    "Q_U": {"type": "variavel", "gamma": {"Normal": 1.50, "Especial": 1.30, "Excepcional": 1.00}, "is_wind": False},    # Ações de valores máximos limitados
    "Q_T": {"type": "variavel", "gamma": {"Normal": 1.20, "Especial": 1.10, "Excepcional": 1.00}, "is_wind": False},    # Temperatura (sem fogo)
    "Q_V": {"type": "variavel", "gamma": {"Normal": 1.40, "Especial": 1.20, "Excepcional": 1.00}, "is_wind": True},     # Vento
    "Q_G": {"type": "variavel", "gamma": {"Normal": 1.50, "Especial": 1.30, "Excepcional": 1.00}, "is_wind": False},    # Ações variáveis genéricas

    # Ações Excepcionais
    "Q_Exc": {"type": "excepcional", "gamma": {"Normal": 1.00, "Especial": 1.00, "Excepcional": 1.00}, "is_wind": False},  # Excepcional

    # Nenhuma
    "NONE": {"type": "permanente", "gamma": {"Normal": 1.00, "Especial": 1.00, "Excepcional": 1.00}, "is_wind": False},  # Nenhuma ação
}

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

# Função para determinar os fatores de ponderação com base na categoria e frequência
def get_factors(load, frequency, is_main=False):
    load_type = load["type"]
    category = load["category"]
    action_info = ACTION_CATEGORIES[category]

    if action_info["type"] == "permanente":
        if frequency in ["Normal", "Frequente", "Rara"]:
            return action_info["gamma"]["Normal"]
        elif frequency == "Acidental":
            return action_info["gamma"]["Excepcional"]
        return 1.0
    elif action_info["type"] == "variavel":
        psi_0 = load["factors"]["ψ₀"]
        psi_1 = load["factors"]["ψ₁"]
        psi_2 = load["factors"]["ψ₂"]
        gamma_q = action_info["gamma"]["Normal"]
        if frequency in ["Frequente", "Rara"]:
            gamma_q = action_info["gamma"]["Especial"]
        elif frequency in ["ELS Normal", "ELS Frequente - Danos Reversíveis", "ELS Frequente - Danos Irreversíveis", "ELS Quase Permanente", "ELS Rara"]:
            gamma_q = 1.0
        
        if frequency == "Normal":
            return gamma_q if is_main else (gamma_q * psi_0)
        elif frequency == "Frequente":
            return (gamma_q * psi_1) if is_main else (gamma_q * psi_0)
        elif frequency == "Rara":
            # Para vento (Q_V), usar apenas ψ₀, independentemente de ser predominante ou não
            if action_info["is_wind"]:
                return psi_0
            return gamma_q if is_main else (gamma_q * psi_0)
        elif frequency == "ELS Normal":
            return 1.0
        elif frequency == "ELS Frequente - Danos Reversíveis":
            return psi_1 if is_main else psi_2
        elif frequency == "ELS Frequente - Danos Irreversíveis":
            return psi_1 if is_main else psi_2
        elif frequency == "ELS Quase Permanente":
            return psi_2
        elif frequency == "ELS Rara":
            return 1.0 if is_main else psi_1
    elif action_info["type"] == "excepcional":
        if frequency == "Acidental":
            return 1.0  # Ajustado conforme referência
        return 1.0  # Ajustado para ELU Rara conforme referência
    return 1.0

# Função para calcular o carregamento total Q [kN/m²]
def calculate_q(loads, combination_str):
    q_total = 0.0
    parts = combination_str.split()
    for i in range(0, len(parts), 2):
        load_idx = int(parts[i]) - 1
        factor = float(parts[i + 1])
        load_value = loads[load_idx]["value"]
        direction = loads[load_idx]["direction"]
        sign = 1 if direction == "Positiva" else -1
        q_total += sign * load_value * factor
    return round(q_total, 3)

# Função para gerar combinações de carga com base nos tipos selecionados
def generate_combinations(loads, selected_types):
    combinations_list = []
    idx = 1

    # Separar cargas por tipo
    permanent_loads = [(i+1, load["name"]) for i, load in enumerate(loads) if ACTION_CATEGORIES[load["category"]]["type"] == "permanente"]
    variable_loads = [(i+1, load["name"]) for i, load in enumerate(loads) if ACTION_CATEGORIES[load["category"]]["type"] == "variavel"]
    exceptional_loads = [(i+1, load["name"]) for i, load in enumerate(loads) if ACTION_CATEGORIES[load["category"]]["type"] == "excepcional"]

    # Separar cargas de vento
    wind_loads = [(i+1, load["name"]) for i, load in enumerate(loads) if ACTION_CATEGORIES[load["category"]]["is_wind"]]
    non_wind_variable_loads = [(i+1, load["name"]) for i, load in enumerate(loads) if ACTION_CATEGORIES[load["category"]]["type"] == "variavel" and not ACTION_CATEGORIES[load["category"]]["is_wind"]]

    # Função auxiliar para adicionar combinações
    def add_combination(perms, vars, freq, type_state, criterion, idx):
        nonlocal combinations_list
        combination = []
        load_indices = []

        # Adicionar cargas permanentes
        for i, _ in perms:
            factor = get_factors(loads[i-1], freq)
            combination.extend([str(i), str(factor)])
            load_indices.append(i-1)

        # Adicionar cargas variáveis
        for i, _ in vars:
            is_main = (i == vars[0][0])
            factor = get_factors(loads[i-1], freq, is_main=is_main)
            if factor > 0:
                combination.extend([str(i), str(factor)])
                load_indices.append(i-1)

        combination_str = " ".join(combination)
        if combination_str:
            q_value = calculate_q(loads, combination_str)
            freq_display = freq.replace("ELS ", "").split(" - ")[0]

            # Obter categorias e frequências das cargas envolvidas
            categories = [loads[idx]["category"] for idx in load_indices]
            frequencies = [loads[idx]["action_type"] if ACTION_CATEGORIES[loads[idx]["category"]]["type"] == "variavel" else "N/A" for idx in load_indices]

            combinations_list.append([
                idx, combination_str, type_state, freq_display, criterion, q_value,
                ", ".join(categories), ", ".join(frequencies)
            ])
        return idx + 1

    # Combinações apenas com cargas permanentes
    if permanent_loads:
        if "ELU Normal" in selected_types:
            combination = []
            load_indices = []
            for i, _ in permanent_loads:
                factor = get_factors(loads[i-1], "Normal")
                combination.extend([str(i), str(factor)])
                load_indices.append(i-1)
            combination_str = " ".join(combination)
            if combination_str:
                q_value = calculate_q(loads, combination_str)
                categories = [loads[idx]["category"] for idx in load_indices]
                frequencies = ["N/A" for _ in load_indices]
                combinations_list.append([
                    idx, combination_str, "ELU", "Normal", "Resistência", q_value,
                    ", ".join(categories), ", ".join(frequencies)
                ])
                idx += 1

        if "ELS Normal" in selected_types:
            combination = []
            load_indices = []
            for i, _ in permanent_loads:
                factor = get_factors(loads[i-1], "ELS Normal")
                combination.extend([str(i), str(factor)])
                load_indices.append(i-1)
            combination_str = " ".join(combination)
            if combination_str:
                q_value = calculate_q(loads, combination_str)
                categories = [loads[idx]["category"] for idx in load_indices]
                frequencies = ["N/A" for _ in load_indices]
                combinations_list.append([
                    idx, combination_str, "ELS", "Normal", "Conforto Visual", q_value,
                    ", ".join(categories), ", ".join(frequencies)
                ])
                idx += 1

    # ELU Normal
    if "ELU Normal" in selected_types:
        # Primeiro, combinações sem cargas de vento
        if non_wind_variable_loads:
            for main_var_idx, _ in non_wind_variable_loads:
                vars_to_combine = [(main_var_idx, "")] + [(i, "") for i, _ in non_wind_variable_loads if i != main_var_idx]
                idx = add_combination(permanent_loads, vars_to_combine, "Normal", "ELU", "Resistência", idx)
        # Depois, combinações com uma carga de vento por vez
        for wind_idx, _ in wind_loads:
            # Se não houver outras cargas variáveis, vento é predominante
            if not non_wind_variable_loads:
                vars_to_combine = [(wind_idx, "")]
                idx = add_combination(permanent_loads, vars_to_combine, "Normal", "ELU", "Resistência", idx)
            else:
                for main_var_idx, _ in non_wind_variable_loads + [(wind_idx, "")]:
                    vars_to_combine = [(main_var_idx, "")]
                    # Adicionar outras cargas variáveis não-vento
                    vars_to_combine += [(i, "") for i, _ in non_wind_variable_loads if i != main_var_idx]
                    # Se a carga principal não for vento, adicionar a carga de vento atual
                    if main_var_idx != wind_idx:
                        vars_to_combine.append((wind_idx, ""))
                    idx = add_combination(permanent_loads, vars_to_combine, "Normal", "ELU", "Resistência", idx)

    # ELU Frequente
    if "ELU Frequente" in selected_types:
        if non_wind_variable_loads:
            for main_var_idx, _ in non_wind_variable_loads:
                vars_to_combine = [(main_var_idx, "")] + [(i, "") for i, _ in non_wind_variable_loads if i != main_var_idx]
                idx = add_combination(permanent_loads, vars_to_combine, "Frequente", "ELU", "Resistência", idx)
        for wind_idx, _ in wind_loads:
            if not non_wind_variable_loads:
                vars_to_combine = [(wind_idx, "")]
                idx = add_combination(permanent_loads, vars_to_combine, "Frequente", "ELU", "Resistência", idx)
            else:
                for main_var_idx, _ in non_wind_variable_loads + [(wind_idx, "")]:
                    vars_to_combine = [(main_var_idx, "")]
                    vars_to_combine += [(i, "") for i, _ in non_wind_variable_loads if i != main_var_idx]
                    if main_var_idx != wind_idx:
                        vars_to_combine.append((wind_idx, ""))
                    idx = add_combination(permanent_loads, vars_to_combine, "Frequente", "ELU", "Resistência", idx)

    # ELU Rara
    if "ELU Rara" in selected_types:
        if non_wind_variable_loads:
            for main_var_idx, _ in non_wind_variable_loads:
                vars_to_combine = [(main_var_idx, "")] + [(i, "") for i, _ in non_wind_variable_loads if i != main_var_idx]
                idx = add_combination(permanent_loads, vars_to_combine, "Rara", "ELU", "Resistência", idx)
        for wind_idx, _ in wind_loads:
            if not non_wind_variable_loads:
                vars_to_combine = [(wind_idx, "")]
                idx = add_combination(permanent_loads, vars_to_combine, "Rara", "ELU", "Resistência", idx)
            else:
                for main_var_idx, _ in non_wind_variable_loads + [(wind_idx, "")]:
                    vars_to_combine = [(main_var_idx, "")]
                    vars_to_combine += [(i, "") for i, _ in non_wind_variable_loads if i != main_var_idx]
                    if main_var_idx != wind_idx:
                        vars_to_combine.append((wind_idx, ""))
                    idx = add_combination(permanent_loads, vars_to_combine, "Rara", "ELU", "Resistência", idx)

    # ELU Acidental
    if "ELU Acidental" in selected_types:
        for exc_idx, _ in exceptional_loads:
            combination = []
            load_indices = []
            for i, _ in permanent_loads:
                combination.extend([str(i), str(get_factors(loads[i-1], "Acidental"))])
                load_indices.append(i-1)
            combination.extend([str(exc_idx), str(get_factors(loads[exc_idx-1], "Acidental"))])
            load_indices.append(exc_idx-1)
            combination_str = " ".join(combination)
            if combination_str:
                q_value = calculate_q(loads, combination_str)
                categories = [loads[idx]["category"] for idx in load_indices]
                frequencies = ["N/A" for _ in load_indices]
                combinations_list.append([
                    idx, combination_str, "ELU", "Acidental", "Resistência", q_value,
                    ", ".join(categories), ", ".join(frequencies)
                ])
                idx += 1

    # ELS Quase Permanente
    if "ELS Quase Permanente" in selected_types:
        if non_wind_variable_loads:
            for var_idx, _ in non_wind_variable_loads:
                idx = add_combination(permanent_loads, [(var_idx, "")], "ELS Quase Permanente", "ELS", "Conforto Visual", idx)
        # Não adicionar vento, pois ψ₂ = 0.0 para Q_V

    # ELS Frequente - Danos Reversíveis
    if "ELS Frequente - Danos Reversíveis" in selected_types:
        if non_wind_variable_loads:
            for var_idx, _ in non_wind_variable_loads:
                idx = add_combination(permanent_loads, [(var_idx, "")], "ELS Frequente - Danos Reversíveis", "ELS", "Danos Reversíveis", idx)
        for wind_idx, _ in wind_loads:
            idx = add_combination(permanent_loads, [(wind_idx, "")], "ELS Frequente - Danos Reversíveis", "ELS", "Danos Reversíveis", idx)

    # ELS Frequente - Danos Irreversíveis
    if "ELS Frequente - Danos Irreversíveis" in selected_types:
        if non_wind_variable_loads:
            for var_idx, _ in non_wind_variable_loads:
                idx = add_combination(permanent_loads, [(var_idx, "")], "ELS Frequente - Danos Irreversíveis", "ELS", "Danos Irreversíveis", idx)
        for wind_idx, _ in wind_loads:
            idx = add_combination(permanent_loads, [(wind_idx, "")], "ELS Frequente - Danos Irreversíveis", "ELS", "Danos Irreversíveis", idx)

    # ELS Rara
    if "ELS Rara" in selected_types:
        if non_wind_variable_loads:
            for var_idx, _ in non_wind_variable_loads:
                vars_to_combine = [(var_idx, "")] + [(i, "") for i, _ in non_wind_variable_loads + wind_loads if i != var_idx]
                idx = add_combination(permanent_loads, vars_to_combine, "ELS Rara", "ELS", "Danos Irreversíveis", idx)
        for wind_idx, _ in wind_loads:
            vars_to_combine = [(wind_idx, "")] + [(i, "") for i, _ in non_wind_variable_loads if i != wind_idx]
            idx = add_combination(permanent_loads, vars_to_combine, "ELS Rara", "ELS", "Danos Irreversíveis", idx)

    return combinations_list

# Interface Streamlit com layout ajustado
st.markdown('<div class="main-container">', unsafe_allow_html=True)

st.title("Gerador de Combinações de Carga para Estruturas Metálicas")
st.write("Insira no mínimo 4 carregamentos para gerar as combinações de carga conforme ABNT NBR 8800.")

# Entrada de número de carregamentos (mínimo 4)
num_loads = st.number_input("Quantidade de carregamentos (mínimo 4, máximo 10):", min_value=4, max_value=10, value=4, step=1)

# Entrada dos carregamentos
loads = []
for i in range(num_loads):
    st.markdown(f'<div class="card">', unsafe_allow_html=True)
    st.markdown(f"### Carregamento {i+1}")
    name = st.text_input(f"Nome do carregamento {i+1}", value=f"Carregamento {i+1}", key=f"name_{i}")
    load_type = st.selectbox(
        f"Categoria do carregamento {i+1} (Tabela 1 - ABNT NBR 8800)",
        [
            "G_Me - Peso próprio de estruturas metálicas",
            "G_Pr - Peso próprio de estruturas pré-fabricadas",
            "G_Si - Peso próprio de estruturas construídas in situ",
            "G_Ec - Elementos construtivos industrializados com adição in situ",
            "G_Eg - Elementos construtivos em geral e equipamentos",
            "SET - Assentamentos de apoios, retrações",
            "Q_U - Ações de valores máximos limitados",
            "Q_T - Temperatura (sem fogo)",
            "Q_V - Vento",
            "Q_G - Ações variáveis genéricas",
            "Q_Exc - Excepcional",
            "NONE - Nenhuma ação"
        ],
        key=f"type_{i}"
    )
    # Extrair apenas o código da categoria (ex.: "G_Me")
    category = load_type.split(" - ")[0]
    value = st.number_input(f"Valor do carregamento {i+1} (kN/m²)", min_value=0.0, value=0.0, step=0.01, key=f"value_{i}")
    direction = st.selectbox(f"Direção do carregamento {i+1}", ["Positiva", "Negativa"], key=f"direction_{i}")
    
    # Se for uma ação variável, permitir escolher a categoria de frequência e associar os fatores ψ
    factors = {"ψ₀": 1.0, "ψ₁": 1.0, "ψ₂": 1.0}
    action_type = ""
    if ACTION_CATEGORIES[category]["type"] == "variavel":
        action_type = st.selectbox(
            f"Categoria da ação variável {i+1} (Tabela 2 - ABNT NBR 8800)",
            list(ACTION_FACTORS.keys()),
            key=f"action_type_{i}"
        )
        factors = ACTION_FACTORS[action_type]
        st.write(f"Fatores para '{action_type}': ψ₀ = {factors['ψ₀']}, ψ₁ = {factors['ψ₁']}, ψ₂ = {factors['ψ₂']}")
    elif ACTION_CATEGORIES[category]["type"] == "excepcional":
        factors = {"ψ₀": 1.0, "ψ₁": 1.0, "ψ₂": 1.0}

    loads.append({
        "name": name, 
        "type": ACTION_CATEGORIES[category]["type"],  # Tipo: permanente, variavel, excepcional
        "category": category,  # Categoria: G_Me, Q_V, etc.
        "value": value, 
        "factors": factors, 
        "action_type": action_type,
        "direction": direction
    })
    st.markdown('</div>', unsafe_allow_html=True)

# Seleção dos tipos de combinações
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### Selecione os Tipos de Combinações a Gerar")
st.write("Escolha os tipos de combinações que deseja gerar:")

# Checkboxes para ELU
st.markdown("#### ELU (Estado Limite Último)")
elu_normal = st.checkbox("ELU Normal (Resistência)", value=True)
elu_frequente = st.checkbox("ELU Frequente (Resistência)", value=True)
elu_rara = st.checkbox("ELU Rara (Resistência)", value=True)
elu_acidental = st.checkbox("ELU Acidental (Resistência)", value=True)

# Checkboxes para ELS
st.markdown("#### ELS (Estado Limite de Serviço)")
els_normal = st.checkbox("ELS Normal (Conforto Visual)", value=True)
els_quase_permanente = st.checkbox("ELS Quase Permanente (Conforto Visual)", value=True)
els_frequente_reversivel = st.checkbox("ELS Frequente - Danos Reversíveis", value=True)
els_frequente_irreversivel = st.checkbox("ELS Frequente - Danos Irreversíveis", value=True)
els_rara = st.checkbox("ELS Rara (Danos Irreversíveis)", value=True)

st.markdown('</div>', unsafe_allow_html=True)

# Lista dos tipos selecionados
selected_types = []
if elu_normal:
    selected_types.append("ELU Normal")
if elu_frequente:
    selected_types.append("ELU Frequente")
if elu_rara:
    selected_types.append("ELU Rara")
if elu_acidental:
    selected_types.append("ELU Acidental")
if els_normal:
    selected_types.append("ELS Normal")
if els_quase_permanente:
    selected_types.append("ELS Quase Permanente")
if els_frequente_reversivel:
    selected_types.append("ELS Frequente - Danos Reversíveis")
if els_frequente_irreversivel:
    selected_types.append("ELS Frequente - Danos Irreversíveis")
if els_rara:
    selected_types.append("ELS Rara")

# Botão para gerar combinações
if st.button("Gerar Combinações"):
    if loads and any(load["value"] > 0 for load in loads):
        if selected_types:
            # Gerar combinações com base nos tipos selecionados
            combinations_data = generate_combinations(loads, selected_types)
            
            if combinations_data:
                # Criar DataFrame com as novas colunas
                df = pd.DataFrame(combinations_data, columns=[
                    "Nº", "Combinação de Carga", "Tipo", "Frequência", "Critério", "Q [kN/m²]",
                    "Categorias Envolvidas", "Frequências Envolvidas"
                ])
                
                # Exibir tabela na interface
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("### Combinações Geradas")
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
                st.error("Nenhuma combinação gerada. Verifique se há cargas suficientes para os tipos selecionados.")
        else:
            st.error("Por favor, selecione pelo menos um tipo de combinação para gerar.")
    else:
        st.error("Por favor, insira pelo menos um carregamento com valor maior que 0.")

st.markdown('</div>', unsafe_allow_html=True)
