import streamlit as st
import pandas as pd
import io

# Estilização CSS
st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 4px;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .stSelectbox, .stNumberInput {
        margin-bottom: 15px;
    }
    .dataframe {
        font-size: 14px;
        border-collapse: collapse;
        width: 100%;
    }
    .dataframe th, .dataframe td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: center;
    }
    .dataframe th {
        background-color: #f2f2f2;
    }
</style>
""", unsafe_allow_html=True)

# Dicionário de categorias de ação (atualizado com traduções)
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
        return gamma_g, 0.0, 0.0
    elif load_type == "variavel":
        # Determinar gamma_q com base no tipo de ação variável
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
        return gamma_g, gamma_q, psi_0
    elif load_type == "excepcional":
        return gamma_g, 1.2, 0.0
    return gamma_g, 0.0, 0.0

# Função para calcular o carregamento total Q
def calculate_q(loads, factors):
    total_q = 0.0
    for load, factor in zip(loads, factors):
        total_q += load["value"] * factor
    return total_q

# Função para gerar combinações de carga
def generate_combinations(loads, combination_type, structure_type):
    combinations = []
    
    # Separar cargas por tipo
    permanent_loads = [load for load in loads if ACTION_CATEGORIES[load["category"]]["type"] == "permanente"]
    variable_loads = [load for load in loads if ACTION_CATEGORIES[load["category"]]["type"] == "variavel"]
    exceptional_loads = [load for load in loads if ACTION_CATEGORIES[load["category"]]["type"] == "excepcional"]
    
    # Separar cargas de vento
    wind_loads = [load for load in variable_loads if ACTION_CATEGORIES[load["category"]]["is_wind"]]
    non_wind_variable_loads = [load for load in variable_loads if not ACTION_CATEGORIES[load["category"]]["is_wind"]]
    
    if combination_type == "ELU Normal":
        # Combinações ELU Normal
        # Para cada carga de vento (ou nenhuma), criar combinações com as outras cargas variáveis
        for wind_load in [None] + wind_loads:
            current_variable_loads = non_wind_variable_loads.copy()
            if wind_load:
                current_variable_loads.append(wind_load)
            
            if not current_variable_loads:
                # Apenas cargas permanentes
                factors = [get_factors("permanente", None, None, structure_type)[0] for _ in permanent_loads]
                q = calculate_q(permanent_loads, factors)
                description = " ".join([f"{load['id']} {factor:.2f}" for load, factor in zip(permanent_loads, factors)])
                combinations.append({"description": description, "q": q})
            else:
                # Cada carga variável como principal, uma por vez
                for i, main_load in enumerate(current_variable_loads):
                    loads_in_combination = permanent_loads.copy()
                    factors = [get_factors("permanente", None, None, structure_type)[0] for _ in permanent_loads]
                    
                    # Carga principal
                    main_category = main_load["category"]
                    main_factor = get_factors("variavel", "principal", main_category, structure_type)[1]
                    loads_in_combination.append(main_load)
                    factors.append(main_factor)
                    
                    # Outras cargas variáveis com psi_0
                    for j, secondary_load in enumerate(current_variable_loads):
                        if j != i:
                            secondary_category = secondary_load["category"]
                            frequency = secondary_load["frequency"]
                            gamma_g, gamma_q, psi_0 = get_factors("variavel", frequency, secondary_category, structure_type)
                            factor = gamma_q * psi_0
                            loads_in_combination.append(secondary_load)
                            factors.append(factor)
                    
                    q = calculate_q(loads_in_combination, factors)
                    description = " ".join([f"{load['id']} {factor:.2f}" for load, factor in zip(loads_in_combination, factors)])
                    combinations.append({"description": description, "q": q})
    
    elif combination_type == "ELU Frequente":
        # Combinações ELU Frequente (usando psi_1)
        for wind_load in [None] + wind_loads:
            current_variable_loads = non_wind_variable_loads.copy()
            if wind_load:
                current_variable_loads.append(wind_load)
            
            if not current_variable_loads:
                # Apenas cargas permanentes
                factors = [get_factors("permanente", None, None, structure_type)[0] for _ in permanent_loads]
                q = calculate_q(permanent_loads, factors)
                description = " ".join([f"{load['id']} {factor:.2f}" for load, factor in zip(permanent_loads, factors)])
                combinations.append({"description": description, "q": q})
            else:
                for i, main_load in enumerate(current_variable_loads):
                    loads_in_combination = permanent_loads.copy()
                    factors = [get_factors("permanente", None, None, structure_type)[0] for _ in permanent_loads]
                    
                    # Carga principal com psi_1
                    main_category = main_load["category"]
                    frequency = main_load["frequency"]
                    gamma_g, gamma_q, psi_0 = get_factors("variavel", frequency, main_category, structure_type)
                    psi_1 = ACTION_FACTORS.get(frequency, {"psi_1": 0.0})["psi_1"]
                    main_factor = gamma_q * psi_1
                    loads_in_combination.append(main_load)
                    factors.append(main_factor)
                    
                    # Outras cargas variáveis com psi_2
                    for j, secondary_load in enumerate(current_variable_loads):
                        if j != i:
                            secondary_category = secondary_load["category"]
                            frequency = secondary_load["frequency"]
                            gamma_g, gamma_q, psi_0 = get_factors("variavel", frequency, secondary_category, structure_type)
                            psi_2 = ACTION_FACTORS.get(frequency, {"psi_2": 0.0})["psi_2"]
                            factor = gamma_q * psi_2
                            loads_in_combination.append(secondary_load)
                            factors.append(factor)
                    
                    q = calculate_q(loads_in_combination, factors)
                    description = " ".join([f"{load['id']} {factor:.2f}" for load, factor in zip(loads_in_combination, factors)])
                    combinations.append({"description": description, "q": q})
    
    elif combination_type == "ELS":
        # Combinações ELS (usando psi_2 e gamma = 1.0)
        for wind_load in [None] + wind_loads:
            current_variable_loads = non_wind_variable_loads.copy()
            if wind_load:
                current_variable_loads.append(wind_load)
            
            if not current_variable_loads:
                # Apenas cargas permanentes
                factors = [1.0 for _ in permanent_loads]
                q = calculate_q(permanent_loads, factors)
                description = " ".join([f"{load['id']} {factor:.2f}" for load, factor in zip(permanent_loads, factors)])
                combinations.append({"description": description, "q": q})
            else:
                for i, main_load in enumerate(current_variable_loads):
                    loads_in_combination = permanent_loads.copy()
                    factors = [1.0 for _ in permanent_loads]
                    
                    # Carga principal com psi_2
                    main_category = main_load["category"]
                    frequency = main_load["frequency"]
                    psi_2 = ACTION_FACTORS.get(frequency, {"psi_2": 0.0})["psi_2"]
                    main_factor = psi_2
                    loads_in_combination.append(main_load)
                    factors.append(main_factor)
                    
                    # Outras cargas variáveis com psi_2
                    for j, secondary_load in enumerate(current_variable_loads):
                        if j != i:
                            secondary_category = secondary_load["category"]
                            frequency = secondary_load["frequency"]
                            psi_2 = ACTION_FACTORS.get(frequency, {"psi_2": 0.0})["psi_2"]
                            factor = psi_2
                            loads_in_combination.append(secondary_load)
                            factors.append(factor)
                    
                    q = calculate_q(loads_in_combination, factors)
                    description = " ".join([f"{load['id']} {factor:.2f}" for load, factor in zip(loads_in_combination, factors)])
                    combinations.append({"description": description, "q": q})
    
    return combinations

# Interface Streamlit
st.title("Gerador de Combinações de Carga")

# Seleção do tipo de estrutura
structure_type = st.selectbox(
    "Selecione o tipo de estrutura:",
    options=["Metálica", "Pré-moldada", "Moldada in loco"],
    index=0
)

# Entrada de carregamentos
st.subheader("Entrada de Carregamentos")
if "loads" not in st.session_state:
    st.session_state.loads = []

# Formulário para adicionar carregamento
with st.form(key="load_form"):
    load_id = st.text_input("ID do Carregamento (ex.: 1, 2, 3)", value=str(len(st.session_state.loads) + 1))
    load_value = st.number_input("Valor do Carregamento (kN/m²)", min_value=0.0, value=0.0, step=0.1)
    category = st.selectbox("Categoria da Ação", options=list(ACTION_CATEGORIES.keys()))
    frequency = st.selectbox(
        "Frequência (para cargas variáveis)",
        options=["N/A"] + list(ACTION_FACTORS.keys()),
        index=0
    )
    submit_button = st.form_submit_button(label="Adicionar Carregamento")

    if submit_button:
        load_type = ACTION_CATEGORIES[category]["type"]
        st.session_state.loads.append({
            "id": load_id,
            "value": load_value,
            "category": category,
            "frequency": frequency if load_type == "variavel" else "N/A"
        })

# Exibir carregamentos adicionados
if st.session_state.loads:
    st.subheader("Carregamentos Adicionados")
    for i, load in enumerate(st.session_state.loads):
        st.write(f"ID: {load['id']}, Valor: {load['value']} kN/m², Categoria: {load['category']}, Frequência: {load['frequency']}")
        if st.button(f"Remover Carregamento {load['id']}", key=f"remove_{i}"):
            st.session_state.loads.pop(i)
            st.rerun()

# Seleção de tipos de combinações
st.subheader("Tipos de Combinações")
combination_types = st.multiselect(
    "Selecione os tipos de combinações:",
    options=["ELU Normal", "ELU Frequente", "ELS"],
    default=["ELU Normal"]
)

# Gerar combinações
if st.button("Gerar Combinações"):
    if not st.session_state.loads:
        st.error("Adicione pelo menos um carregamento antes de gerar combinações.")
    else:
        all_combinations = []
        for comb_type in combination_types:
            combinations = generate_combinations(st.session_state.loads, comb_type, structure_type)
            for comb in combinations:
                all_combinations.append({
                    "Tipo": comb_type,
                    "Descrição": comb["description"],
                    "Q (kN/m²)": round(comb["q"], 2)
                })
        
        # Criar DataFrame
        df = pd.DataFrame(all_combinations)
        st.subheader("Tabela de Combinações")
        st.dataframe(df)
        
        # Exportar para Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Combinações")
        excel_data = output.getvalue()
        st.download_button(
            label="Exportar para Excel",
            data=excel_data,
            file_name="combinacoes_carga.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
