import streamlit as st
import pandas as pd
import io

# CSS personalizado (adotado do código anterior)
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
        color: #003087;
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
        background-color: #1A5C34;
        color: #FFFFFF;
        font-weight: 500;
        border: none;
        border-radius: 4px;
        padding: 10px 20px;
        transition: background-color 0.3s;
    }

    .stButton>button:hover {
        background-color: #2E7D32;
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

# Dicionário de categorias de ação
ACTION_CATEGORIES = {
    "Peso próprio de estruturas metálicas": {"type": "permanente", "is_wind": False},
    "Peso próprio de estruturas pré-fabricadas": {"type": "permanente", "is_wind": False},
    "Peso próprio de estruturas construídas in situ": {"type": "permanente", "is_wind": False},
    "Elementos de construção industrializados in situ": {"type": "permanente", "is_wind": False},
    "Elementos de construção e equipamento geral": {"type": "permanente", "is_wind": False},
    "Assentamento": {"type": "permanente", "is_wind": False},
    "Ações de valores máximos": {"type": "variavel", "is_wind": False},
    "Temperatura (sem fogo)": {"type": "variavel", "is_wind": False},
    "Vento": {"type": "variavel", "is_wind": True},
    "Ações variáveis genéricas": {"type": "variavel", "is_wind": False},
    "Excepcional": {"type": "excepcional", "is_wind": False},
    "Sem categoria": {"type": "permanente", "is_wind": False},
}

# Dicionário com os fatores psi (Tabela 2 da NBR 8800)
ACTION_FACTORS = {
    "Locais com predominância de pesos/equipamentos fixos": {"psi_0": 0.7, "psi_1": 0.5, "psi_2": 0.2},
    "Habitações": {"psi_0": 0.5, "psi_1": 0.4, "psi_2": 0.3},
    "Hotéis, dormitórios, quartéis e prisões": {"psi_0": 0.5, "psi_1": 0.4, "psi_2": 0.3},
    "Escritórios": {"psi_0": 0.5, "psi_1": 0.4, "psi_2": 0.3},
    "Escolas e locais de reunião": {"psi_0": 0.7, "psi_1": 0.4, "psi_2": 0.3},
    "Garagens para veículos de passageiros": {"psi_0": 0.7, "psi_1": 0.6, "psi_2": 0.5},
    "Lojas": {"psi_0": 0.7, "psi_1": 0.6, "psi_2": 0.5},
    "Pressão dinâmica do vento": {"psi_0": 0.6, "psi_1": 0.2, "psi_2": 0.0},
    "Variações de temperatura": {"psi_0": 0.6, "psi_1": 0.5, "psi_2": 0.0},
    "Ações excepcionais": {"psi_0": 0.0, "psi_1": 0.0, "psi_2": 0.0},
}

# Dicionário com os fatores gamma_g para diferentes tipos de estruturas
GAMMA_G_FACTORS = {
    "Metálica": 1.25,
    "Pré-moldada": 1.3,
    "Moldada in loco": 1.35,
}

# Função para determinar os fatores de ponderação
def get_factors(load_type, frequency, category, structure_type):
    gamma_g = GAMMA_G_FACTORS[structure_type]
    
    if load_type == "permanente":
        return gamma_g, 0.0, 0.0, 0.0, 0.0
    elif load_type == "variavel":
        if category == "Vento":
            gamma_q = 1.4
        elif category == "Temperatura (sem fogo)":
            gamma_q = 1.2
        else:
            gamma_q = 1.5
        
        if frequency == "principal":
            psi_0 = 1.0
        else:
            psi_0 = ACTION_FACTORS.get(frequency, {"psi_0": 0.0})["psi_0"]
        psi_1 = ACTION_FACTORS.get(frequency, {"psi_1": 0.0})["psi_1"]
        psi_2 = ACTION_FACTORS.get(frequency, {"psi_2": 0.0})["psi_2"]
        return gamma_g, gamma_q, psi_0, psi_1, psi_2
    elif load_type == "excepcional":
        return gamma_g, 1.2, 0.0, 0.0, 0.0
    return gamma_g, 0.0, 0.0, 0.0, 0.0

# Função para calcular o carregamento total Q
def calculate_q(loads, factors):
    total_q = 0.0
    for load, factor in zip(loads, factors):
        total_q += load["value"] * factor
    return total_q

# Função para gerar combinações de carga (mantida do primeiro código)
def generate_combinations(loads, structure_type):
    combinations = []
    
    permanent_loads = [load for load in loads if ACTION_CATEGORIES[load["category"]]["type"] == "permanente"]
    variable_loads = [load for load in loads if ACTION_CATEGORIES[load["category"]]["type"] == "variavel"]
    exceptional_loads = [load for load in loads if ACTION_CATEGORIES[load["category"]]["type"] == "excepcional"]
    
    wind_loads = [load for load in variable_loads if ACTION_CATEGORIES[load["category"]]["is_wind"]]
    non_wind_variable_loads = [load for load in variable_loads if not ACTION_CATEGORIES[load["category"]]["is_wind"]]
    
    # 1. Combinações ELU Normal
    for wind_load in [None] + wind_loads:
        current_variable_loads = non_wind_variable_loads.copy()
        if wind_load:
            current_variable_loads.append(wind_load)
        
        if not current_variable_loads:
            factors = [get_factors("permanente", None, None, structure_type)[0] for _ in permanent_loads]
            q = calculate_q(permanent_loads, factors)
            description = " + ".join([f"{factor:.2f}*{load['id']}" for load, factor in zip(permanent_loads, factors)])
            combinations.append({"type": "ELU Normal", "description": description, "q": q})
        else:
            for i, main_load in enumerate(current_variable_loads):
                loads_in_combination = permanent_loads.copy()
                factors = [get_factors("permanente", None, None, structure_type)[0] for _ in permanent_loads]
                
                main_category = main_load["category"]
                main_factor = get_factors("variavel", "principal", main_category, structure_type)[1]
                loads_in_combination.append(main_load)
                factors.append(main_factor)
                
                for j, secondary_load in enumerate(current_variable_loads):
                    if j != i:
                        secondary_category = secondary_load["category"]
                        frequency = secondary_load["frequency"]
                        gamma_g, gamma_q, psi_0, _, _ = get_factors("variavel", frequency, secondary_category, structure_type)
                        factor = gamma_q * psi_0
                        loads_in_combination.append(secondary_load)
                        factors.append(factor)
                
                q = calculate_q(loads_in_combination, factors)
                description = " + ".join([f"{factor:.2f}*{load['id']}" for load, factor in zip(loads_in_combination, factors)])
                combinations.append({"type": "ELU Normal", "description": description, "q": q})
    
    # 2. Combinações ELS Frequente
    for wind_load in [None] + wind_loads:
        current_variable_loads = non_wind_variable_loads.copy()
        if wind_load:
            current_variable_loads.append(wind_load)
        
        if not current_variable_loads:
            factors = [1.0 for _ in permanent_loads]
            q = calculate_q(permanent_loads, factors)
            description = " + ".join([f"{factor:.2f}*{load['id']}" for load, factor in zip(permanent_loads, factors)])
            combinations.append({"type": "ELS Frequente", "description": description, "q": q})
        else:
            for i, main_load in enumerate(current_variable_loads):
                loads_in_combination = permanent_loads.copy()
                factors = [1.0 for _ in permanent_loads]
                
                main_category = main_load["category"]
                frequency = main_load["frequency"]
                _, _, _, psi_1, _ = get_factors("variavel", frequency, main_category, structure_type)
                main_factor = psi_1
                loads_in_combination.append(main_load)
                factors.append(main_factor)
                
                for j, secondary_load in enumerate(current_variable_loads):
                    if j != i:
                        secondary_category = secondary_load["category"]
                        frequency = secondary_load["frequency"]
                        _, _, _, _, psi_2 = get_factors("variavel", frequency, secondary_category, structure_type)
                        factor = psi_2
                        loads_in_combination.append(secondary_load)
                        factors.append(factor)
                
                q = calculate_q(loads_in_combination, factors)
                description = " + ".join([f"{factor:.2f}*{load['id']}" for load, factor in zip(loads_in_combination, factors)])
                combinations.append({"type": "ELS Frequente", "description": description, "q": q})
    
    # 3. Combinações ELS Quasipermanente
    for wind_load in [None] + wind_loads:
        current_variable_loads = non_wind_variable_loads.copy()
        if wind_load:
            current_variable_loads.append(wind_load)
        
        if not current_variable_loads:
            factors = [1.0 for _ in permanent_loads]
            q = calculate_q(permanent_loads, factors)
            description = " + ".join([f"{factor:.2f}*{load['id']}" for load, factor in zip(permanent_loads, factors)])
            combinations.append({"type": "ELS Quasipermanente", "description": description, "q": q})
        else:
            loads_in_combination = permanent_loads.copy()
            factors = [1.0 for _ in permanent_loads]
            
            for load in current_variable_loads:
                category = load["category"]
                frequency = load["frequency"]
                _, _, _, _, psi_2 = get_factors("variavel", frequency, category, structure_type)
                loads_in_combination.append(load)
                factors.append(psi_2)
            
            q = calculate_q(loads_in_combination, factors)
            description = " + ".join([f"{factor:.2f}*{load['id']}" for load, factor in zip(loads_in_combination, factors)])
            combinations.append({"type": "ELS Quasipermanente", "description": description, "q": q})
    
    return combinations

# Interface Streamlit (adotada do segundo código, com ajustes)
st.markdown('<div class="main-container">', unsafe_allow_html=True)

st.title("Gerador de Combinações de Carga para Estruturas Metálicas")
st.write("Insira no mínimo 4 carregamentos para gerar as combinações de carga conforme ABNT NBR 8800.")

# Seleção do tipo de estrutura
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### Tipo de Estrutura")
structure_type = st.selectbox("Selecione o tipo de estrutura:", ["Metálica", "Pré-moldada", "Moldada in loco"], key="structure_type")
st.markdown('</div>', unsafe_allow_html=True)

# Entrada de número de carregamentos (mínimo 4)
num_loads = st.number_input("Quantidade de carregamentos (mínimo 4, máximo 10):", min_value=4, max_value=10, value=4, step=1)

# Entrada dos carregamentos
loads = []
for i in range(num_loads):
    st.markdown(f'<div class="card">', unsafe_allow_html=True)
    st.markdown(f"### Carregamento {i+1}")
    name = st.text_input(f"Nome do carregamento {i+1}", value=f"CC{i+1}", key=f"name_{i}")
    load_type = st.selectbox(f"Tipo do carregamento {i+1}", ["Permanente", "Variável", "Excepcional"], key=f"type_{i}")
    value = st.number_input(f"Valor do carregamento {i+1} (kN/m²)", min_value=0.0, value=0.0, step=0.01, key=f"value_{i}")
    direction = st.selectbox(f"Direção do carregamento {i+1}", ["Positiva", "Negativa"], key=f"direction_{i}")
    is_favorable = st.checkbox(f"Carregamento {i+1} é favorável à segurança?", value=False, key=f"favorable_{i}")
    
    category = st.selectbox(f"Categoria da ação {i+1}", options=list(ACTION_CATEGORIES.keys()), key=f"category_{i}")
    frequency = "N/A"
    if load_type == "Variável":
        frequency = st.selectbox(
            f"Frequência (para cargas variáveis) {i+1}",
            options=["N/A"] + list(ACTION_FACTORS.keys()),
            key=f"frequency_{i}"
        )
    
    loads.append({
        "id": name,
        "value": value if direction == "Positiva" else -value,
        "category": category,
        "frequency": frequency if load_type == "Variável" else "N/A",
        "type": load_type,
        "is_favorable": is_favorable
    })
    st.markdown('</div>', unsafe_allow_html=True)

# Botão para gerar combinações
if st.button("Gerar Combinações"):
    if len(loads) >= 4 and any(abs(load["value"]) > 0 for load in loads):
        combinations = generate_combinations(loads, structure_type)
        all_combinations = []
        idx = 1
        for comb in combinations:
            all_combinations.append({
                "Nº": idx,
                "Combinação de Carga": comb["description"],
                "Tipo": comb["type"].split()[0],
                "Frequência": comb["type"].replace("ELU ", "").replace("ELS ", ""),
                "Critério": "Resistência" if "ELU" in comb["type"] else "Conforto Visual",
                "Q [kN/m²]": round(comb["q"], 3)
            })
            idx += 1
        
        # Criar DataFrame
        df = pd.DataFrame(all_combinations)
        
        # Exibir tabela na interface
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Combinações Geradas")
        st.dataframe(df)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Exportar para Excel (corrigido para usar openpyxl)
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
        st.error("Por favor, insira pelo menos 4 carregamentos, com pelo menos um valor maior que 0.")

st.markdown('</div>', unsafe_allow_html=True)
