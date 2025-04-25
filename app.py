import streamlit as st
import pandas as pd
import io
from itertools import combinations

# Função para determinar os fatores de ponderação com base no tipo e frequência
def get_factors(load_type, frequency, is_main=False):
    if load_type == "Permanente":
        if frequency in ["Normal", "Frequente", "Rara", "Acidental"]:
            return 1.25 if "Normal" in frequency else 1.0
        return 1.0
    elif load_type == "Variável":
        if frequency == "Normal":
            return 1.5 if is_main else 0.84
        elif frequency == "Frequente":
            return 1.05 if is_main else (0.6 if "ELS" in frequency else 1.4)
        elif frequency == "Rara":
            return 1.4 if is_main else 0.6
        elif frequency == "ELS Normal":
            return 1.0
        elif frequency == "ELS Frequente":
            return 0.6 if is_main else 0.4
        elif frequency == "ELS Quase Permanente":
            return 0.4 if is_main else 0.3
        elif frequency == "ELS Rara":
            return 1.0 if is_main else 0.6
    elif load_type == "Excepcional":
        if frequency == "Acidental":
            return 1.6
        return 1.4 if "Rara" in frequency else 1.0
    return 1.0

# Função para gerar combinações de carga (mínimo 40)
def generate_combinations(loads):
    combinations_list = []
    idx = 1

    # Separar cargas por tipo
    permanent_loads = [(i+1, load["name"]) for i, load in enumerate(loads) if load["type"] == "Permanente"]
    variable_loads = [(i+1, load["name"]) for i, load in enumerate(loads) if load["type"] == "Variável"]
    exceptional_loads = [(i+1, load["name"]) for i, load in enumerate(loads) if load["type"] == "Excepcional"]

    # Função auxiliar para adicionar combinações
    def add_combination(perms, vars, freq, type_state, idx):
        nonlocal combinations_list
        combination = []
        for i, _ in perms:
            combination.extend([str(i), str(get_factors("Permanente", freq))])
        for i, _ in vars:
            is_main = (len(vars) == 1 and i == vars[0][0]) or (len(vars) > 1 and i == vars[0][0])
            combination.extend([str(i), str(get_factors("Variável", freq, is_main))])
        combination_str = " ".join(combination)
        combinations_list.append([idx, combination_str, type_state, freq.split(" ")[-1]])
        return idx + 1

    # 1. ELU Normal: Cada variável como principal, outras como secundárias
    for main_var_idx, _ in variable_loads:
        idx = add_combination(permanent_loads, [(main_var_idx, "")] + [(i, "") for i, _ in variable_loads if i != main_var_idx], "Normal", "ELU", idx)

    # 2. ELU Normal: Subgrupos de variáveis (sem outras secundárias)
    for r in range(1, len(variable_loads) + 1):
        for var_combo in combinations(variable_loads, r):
            idx = add_combination(permanent_loads, var_combo, "Normal", "ELU", idx)
            if len(combinations_list) >= 40:
                return combinations_list

    # 3. ELU Frequente: Cada variável como principal, outras com fator 1.4 (vento)
    for main_var_idx, _ in variable_loads:
        idx = add_combination(permanent_loads, [(main_var_idx, "")] + [(i, "") for i, _ in variable_loads if i != main_var_idx], "Frequente", "ELU", idx)

    # 4. ELU Rara: Cada variável (vento) como principal
    for main_var_idx, _ in variable_loads:
        idx = add_combination(permanent_loads, [(main_var_idx, "")] + [(i, "") for i, _ in variable_loads if i != main_var_idx], "Rara", "ELU", idx)

    # 5. ELU Acidental: Cada excepcional como principal
    for exc_idx, _ in exceptional_loads:
        combination = []
        for i, _ in permanent_loads:
            combination.extend([str(i), str(get_factors("Permanente", "Acidental"))])
        combination.extend([str(exc_idx), str(get_factors("Excepcional", "Acidental"))])
        combination_str = " ".join(combination)
        combinations_list.append([idx, combination_str, "ELU", "Acidental"])
        idx += 1

    # 6. ELS Normal: Cada variável isolada
    for var_idx, _ in variable_loads:
        idx = add_combination(permanent_loads, [(var_idx, "")], "ELS Normal", "ELS", idx)

    # 7. ELS Rara: Cada variável isolada
    for var_idx, _ in variable_loads:
        idx = add_combination(permanent_loads, [(var_idx, "")], "ELS Rara", "ELS", idx)

    # 8. ELS Frequente: Cada variável isolada
    for var_idx, _ in variable_loads:
        idx = add_combination(permanent_loads, [(var_idx, "")], "ELS Frequente", "ELS", idx)

    # 9. ELS Quase Permanente: Cada variável isolada
    for var_idx, _ in variable_loads:
        idx = add_combination(permanent_loads, [(var_idx, "")], "ELS Quase Permanente", "ELS", idx)

    # 10. Combinações apenas com permanentes (para preencher até 40, se necessário)
    while len(combinations_list) < 40:
        combination = []
        for i, _ in permanent_loads:
            combination.extend([str(i), str(get_factors("Permanente", "Normal" if idx % 2 == 0 else "ELS Normal"))])
        combination_str = " ".join(combination)
        combinations_list.append([idx, combination_str, "ELU" if idx % 2 == 0 else "ELS", "Normal"])
        idx += 1

    return combinations_list

# Interface Streamlit
st.title("Gerador de Combinações de Carga para Estruturas Metálicas")
st.write("Insira até 10 carregamentos para gerar as combinações de carga conforme NBR 8800 e NBR 8681 (mínimo 40 combinações).")

# Entrada de número de carregamentos
num_loads = st.number_input("Quantidade de carregamentos (máximo 10):", min_value=1, max_value=10, value=1, step=1)

# Entrada dos carregamentos
loads = []
for i in range(num_loads):
    st.subheader(f"Carregamento {i+1}")
    name = st.text_input(f"Nome do carregamento {i+1}", value=f"Carregamento {i+1}", key=f"name_{i}")
    load_type = st.selectbox(f"Tipo do carregamento {i+1}", ["Permanente", "Variável", "Excepcional"], key=f"type_{i}")
    loads.append({"name": name, "type": load_type})

# Botão para gerar combinações
if st.button("Gerar Combinações"):
    if loads:
        # Gerar combinações
        combinations_data = generate_combinations(loads)
        
        # Criar DataFrame
        df = pd.DataFrame(combinations_data, columns=["Nº", "Combinação de Carga", "Tipo", "Frequência"])
        
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
        st.error("Por favor, insira pelo menos um carregamento.")
