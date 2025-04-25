import streamlit as st
import pandas as pd
import io
from itertools import combinations

# Função para determinar os fatores de ponderação com base no tipo e frequência
def get_factors(load_type, frequency, is_main=False, psi_1=0.60, psi_2=0.40):
    if load_type == "Permanente":
        if frequency in ["Normal", "Frequente", "Rara", "Acidental"]:
            return 1.25 if "Normal" in frequency else 1.0
        return 1.0
    elif load_type == "Variável":
        if frequency == "Normal":
            return 1.5 if is_main else 0.84
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
def generate_combinations(loads, psi_1, psi_2):
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
            combination.extend([str(i), str(get_factors("Permanente", freq))])
        for i, _ in vars:
            is_main = (len(vars) == 1 and i == vars[0][0]) or (len(vars) > 1 and i == vars[0][0])
            factor = get_factors("Variável", freq, is_main, psi_1, psi_2)
            if factor > 0:
                combination.extend([str(i), str(factor)])
        combination_str = " ".join(combination)
        if combination_str:
            q_value = calculate_q(loads, combination_str)
            freq_display = freq.replace("ELS ", "").split(" - ")[0]
            combinations_list.append([idx, combination_str, type_state, freq_display, criterion, q_value])
        return idx + 1

    # 1. ELU Normal: Cada variável como principal, outras como secundárias
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
            combination.extend([str(i), str(get_factors("Permanente", "Acidental"))])
        combination.extend([str(exc_idx), str(get_factors("Excepcional", "Acidental"))])
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
            combination.extend([str(i), str(get_factors("Permanente", "Normal" if idx % 2 == 0 else "ELS Normal"))])
        combination_str = " ".join(combination)
        q_value = calculate_q(loads, combination_str) if combination_str else 0.0
        combinations_list.append([idx, combination_str, "ELU" if idx % 2 == 0 else "ELS", 
                                "Normal" if idx % 2 == 0 else "Quase Permanente", 
                                "Resistência" if idx % 2 == 0 else "Conforto Visual", q_value])
        idx += 1

    return combinations_list

# Interface Streamlit
st.title("Gerador de Combinações de Carga para Estruturas Metálicas")
st.write("Insira até 10 carregamentos para gerar as combinações de carga conforme ABNT NBR 8800 (mínimo 40 combinações).")

# Entrada de fatores de redução
st.subheader("Fatores de Redução (ABNT NBR 8800)")
psi_1 = st.number_input("Fator ψ₁ (Combinação Frequente)", min_value=0.0, max_value=1.0, value=0.60, step=0.01)
psi_2 = st.number_input("Fator ψ₂ (Combinação Quase Permanente)", min_value=0.0, max_value=1.0, value=0.40, step=0.01)

# Entrada de número de carregamentos
num_loads = st.number_input("Quantidade de carregamentos (máximo 10):", min_value=1, max_value=10, value=1, step=1)

# Entrada dos carregamentos
loads = []
for i in range(num_loads):
    st.subheader(f"Carregamento {i+1}")
    name = st.text_input(f"Nome do carregamento {i+1}", value=f"Carregamento {i+1}", key=f"name_{i}")
    load_type = st.selectbox(f"Tipo do carregamento {i+1}", ["Permanente", "Variável", "Excepcional"], key=f"type_{i}")
    value = st.number_input(f"Valor do carregamento {i+1} (kN/m²)", min_value=0.0, value=0.0, step=0.01, key=f"value_{i}")
    loads.append({"name": name, "type": load_type, "value": value})

# Botão para gerar combinações
if st.button("Gerar Combinações"):
    if loads and any(load["value"] > 0 for load in loads):
        # Gerar combinações
        combinations_data = generate_combinations(loads, psi_1, psi_2)
        
        # Criar DataFrame
        df = pd.DataFrame(combinations_data, columns=["Nº", "Combinação de Carga", "Tipo", "Frequência", "Critério", "Q [kN/m²]"])
        
        # Exibir tabela na interface
        st.write("### Combinações Geradas")
        st.dataframe(df)
        
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
