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

# Função para gerar combinações de carga com base nos tipos selecionados
def generate_combinations(loads, selected_types):
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
            is_main = (i == vars[0][0])  # Apenas a primeira carga variável é principal
            factor = get_factors(loads[i-1], freq, is_main)
            if factor > 0:
                combination.extend([str(i), str(factor)])
        combination_str = " ".join(combination)
        if combination_str:
            q_value = calculate_q(loads, combination_str)
            freq_display = freq.replace("ELS ", "").split(" - ")[0]
            combinations_list.append([idx, combination_str, type_state, freq_display, criterion, q_value])
        return idx + 1

    # Combinações apenas com cargas permanentes (se selecionado)
    if permanent_loads:
        if "ELU Normal" in selected_types:
            combination = []
            for i, _ in permanent_loads:
                combination.extend([str(i), str(get_factors(loads[i-1], "Normal"))])
            combination_str = " ".join(combination)
            if combination_str:
                q_value = calculate_q(loads, combination_str)
                combinations_list.append([idx, combination_str, "ELU", "Normal", "Resistência", q_value])
                idx += 1

        if "ELS Normal" in selected_types:
            combination = []
            for i, _ in permanent_loads:
                combination.extend([str(i), str(get_factors(loads[i-1], "ELS Normal"))])
            combination_str = " ".join(combination)
            if combination_str:
                q_value = calculate_q(loads, combination_str)
                combinations_list.append([idx, combination_str, "ELS", "Normal", "Conforto Visual", q_value])
                idx += 1

    # ELU Normal: Cada variável como principal, outras como secundárias (usando ψ₀)
    if "ELU Normal" in selected_types:
        for main_var_idx, _ in variable_loads:
            idx = add_combination(permanent_loads, [(main_var_idx, "")] + [(i, "") for i, _ in variable_loads if i != main_var_idx], 
                                "Normal", "ELU", "Resistência", idx)

    # ELU Frequente: Cada variável como principal, outras com fator 1.4 (vento)
    if "ELU Frequente" in selected_types:
        for main_var_idx, _ in variable_loads:
            idx = add_combination(permanent_loads, [(main_var_idx, "")] + [(i, "") for i, _ in variable_loads if i != main_var_idx], 
                                "Frequente", "ELU", "Resistência", idx)

    # ELU Rara: Cada variável (vento) como principal
    if "ELU Rara" in selected_types:
        for main_var_idx, _ in variable_loads:
            idx = add_combination(permanent_loads, [(main_var_idx, "")] + [(i, "") for i, _ in variable_loads if i != main_var_idx], 
                                "Rara", "ELU", "Resistência", idx)

    # ELU Acidental: Cada excepcional como principal
    if "ELU Acidental" in selected_types:
        for exc_idx, _ in exceptional_loads:
            combination = []
            for i, _ in permanent_loads:
                combination.extend([str(i), str(get_factors(loads[i-1], "Acidental"))])
            combination.extend([str(exc_idx), str(get_factors(loads[exc_idx-1], "Acidental"))])
            combination_str = " ".join(combination)
            if combination_str:
                q_value = calculate_q(loads, combination_str)
                combinations_list.append([idx, combination_str, "ELU", "Acidental", "Resistência", q_value])
                idx += 1

    # ELS Quase Permanente: Todas as permanentes + cada variável com ψ₂ (Conforto Visual)
    if "ELS Quase Permanente" in selected_types:
        for var_idx, _ in variable_loads:
            idx = add_combination(permanent_loads, [(var_idx, "")], "ELS Quase Permanente", "ELS", "Conforto Visual", idx)

    # ELS Frequente - Danos Reversíveis: Cada variável com ψ₁
    if "ELS Frequente - Danos Reversíveis" in selected_types:
        for var_idx, _ in variable_loads:
            idx = add_combination([], [(var_idx, "")], "ELS Frequente - Danos Reversíveis", "ELS", "Danos Reversíveis", idx)

    # ELS Frequente - Danos Irreversíveis: Cada variável com 1.0
    if "ELS Frequente - Danos Irreversíveis" in selected_types:
        for var_idx, _ in variable_loads:
            idx = add_combination([], [(var_idx, "")], "ELS Frequente - Danos Irreversíveis", "ELS", "Danos Irreversíveis", idx)

    # ELS Rara: Cada variável com 1.0 (Danos Irreversíveis)
    if "ELS Rara" in selected_types:
        for var_idx, _ in variable_loads:
            idx = add_combination([], [(var_idx, "")], "ELS Rara", "ELS", "Danos Irreversíveis", idx)

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
                # Criar DataFrame
                df = pd.DataFrame(combinations_data, columns=["Nº", "Combinação de Carga", "Tipo", "Frequência", "Critério", "Q [kN/m²]"])
                
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
