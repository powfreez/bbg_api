import os
import webbrowser
from datetime import date

import pandas as pd
import streamlit as st

from factor_investing_strategy import FactorInvestingStrategy


def open_report_file(report_file_path):
    """Ouvre automatiquement le fichier de rapport dans le navigateur"""
    if report_file_path and os.path.exists(report_file_path):
        # Convertir le chemin en URL file://
        file_url = f"file://{os.path.abspath(report_file_path)}"
        webbrowser.open(file_url)
        return True
    return False


def validate_components(components):
    """Vérifie que la somme des pondérations vaut 1.0"""
    if not components:
        return False, "Aucune composante sélectionnée"

    total = sum(components.values())
    if abs(total - 1.0) > 1e-6:
        return False, f"La somme des pondérations est {total:.2f}. Elle doit être égale à 1.0"
    return True, "Pondérations valides!"


def main():
    st.title("Stratégie d'Investissement Factorielle")

    st.sidebar.header("Paramètres de la stratégie")

    # Paramètres généraux
    data_folder = st.sidebar.text_input("Dossier de données", "data")

    # Type de stratégie (placé avant les paramètres qui en dépendent)
    strategy_type = st.sidebar.selectbox(
        "Type de stratégie",
        ["unconditional", "conditional"]
    )

    # Top N (désactivé pour conditional)
    if strategy_type == "conditional":
        st.sidebar.text("Nombre d'actions: Non applicable pour la stratégie conditionnelle")
        top_n = None  # Valeur par défaut pour conditional
    else:
        top_n = st.sidebar.slider("Nombre d'actions (top N)", 5, 50, 30)

    # Dates
    start_date = st.sidebar.date_input("Date de début",
                                       value=date(2012, 1, 1),
                                       min_value=date(2012, 1, 1),
                                       max_value=date(2023, 12, 31))
    end_date = st.sidebar.date_input("Date de fin",
                                     value=date(2024, 12, 31),
                                     min_value=start_date,
                                     max_value=date(2024, 12, 31))

    # Neutralisation
    use_neutralized = st.sidebar.checkbox("Utiliser la neutralisation", True)

    # Méthode de pondération
    weighting_method = st.sidebar.selectbox(
        "Méthode de pondération",
        ["equal", "market_cap", "min_variance"],
        help="equal: poids égaux, market_cap: pondération par capitalisation, min_variance: optimisation variance minimale"
    )

    # Section Options de sortie
    st.sidebar.markdown("---")
    st.sidebar.subheader("Options de sortie")

    generate_port_file = st.sidebar.checkbox(
        "Générer fichier PORT Excel",
        value=True,
        help="Génère un fichier Excel au format Bloomberg PORT avec les poids du portefeuille"
    )

    # Section Volatility Scaling
    st.sidebar.markdown("---")
    st.sidebar.subheader("Volatility Scaling")

    volatility_scaling = st.sidebar.checkbox("Activer le volatility scaling", False)

    if volatility_scaling:
        st.sidebar.info("Ajuste dynamiquement les poids pour atteindre une volatilité cible")

        target_volatility = st.sidebar.slider(
            "Volatilité cible (%)",
            min_value=5.0,
            max_value=30.0,
            value=15.0,
            step=1.0,
            help="Volatilité annuelle cible en pourcentage"
        ) / 100.0  # Convertir en décimal

        volatility_lookback_months = st.sidebar.slider(
            "Période de lookback (mois)",
            min_value=6,
            max_value=36,
            value=12,
            help="Nombre de mois pour calculer la volatilité historique"
        )

        st.sidebar.success(f"Volatilité cible: {target_volatility:.1%}")
    else:
        target_volatility = 0.15  # Valeur par défaut
        volatility_lookback_months = 12  # Valeur par défaut

    # Allocation des facteurs (désactivé pour conditional)
    st.sidebar.subheader("Allocation des facteurs")

    if strategy_type == "conditional":
        st.sidebar.info("L'allocation des facteurs n'est pas applicable pour la stratégie conditionnelle.")
        # Valeurs par défaut pour conditional
        value_weight = 0.33
        momentum_weight = 0.33
        profitability_weight = 0.34
        can_run = True
    else:
        st.sidebar.info("La somme des allocations doit être égale à 1.0")

        col1, col2, col3 = st.sidebar.columns(3)

        with col1:
            value_weight = st.number_input("Value", min_value=0.0, max_value=1.0, value=0.5, step=0.1)

        with col2:
            momentum_weight = st.number_input("Momentum", min_value=0.0, max_value=1.0, value=0.25, step=0.1)

        with col3:
            profitability_weight = st.number_input("Profitability", min_value=0.0, max_value=1.0, value=0.25, step=0.1)

        total_weight = value_weight + momentum_weight + profitability_weight
        if abs(total_weight - 1.0) > 1e-6:
            st.sidebar.error(f"La somme des allocations est {total_weight:.2f}. Elle doit être égale à 1.0")
            can_run = False
        else:
            st.sidebar.success("Allocation valide!")
            can_run = True

    allocation_weights = {
        "value": value_weight,
        "momentum": momentum_weight,
        "profitability": profitability_weight
    }

    # Section pour personnaliser les composantes des facteurs
    st.sidebar.markdown("---")
    st.sidebar.subheader("Personnalisation des facteurs")

    # Personnalisation du facteur Value
    st.sidebar.subheader("Facteur Value")
    value_components = {}

    # Option pour activer/désactiver la personnalisation des facteurs
    custom_value = st.sidebar.checkbox("Personnaliser le facteur Value", False)

    if custom_value:
        st.sidebar.info("Sélectionnez les composantes et leurs pondérations (somme = 1.0)")

        # Book-to-Market
        use_btm = st.sidebar.checkbox("Book-to-Market (BTM)", True)
        if use_btm:
            btm_weight = st.sidebar.slider("Pondération BTM", 0.0, 1.0, 0.4, 0.1)
            value_components["btm"] = btm_weight

        # EBIT/EV
        use_ebit_ev = st.sidebar.checkbox("EBIT/EV", True)
        if use_ebit_ev:
            ebit_ev_weight = st.sidebar.slider("Pondération EBIT/EV", 0.0, 1.0, 0.2, 0.1)
            value_components["ebit_ev"] = ebit_ev_weight

        # EBITDA/EV
        use_ebitda_ev = st.sidebar.checkbox("EBITDA/EV", True)
        if use_ebitda_ev:
            ebitda_ev_weight = st.sidebar.slider("Pondération EBITDA/EV", 0.0, 1.0, 0.3, 0.1)
            value_components["ebitda_ev"] = ebitda_ev_weight

        # Dividend Yield
        use_div_yield = st.sidebar.checkbox("Dividend Yield", True)
        if use_div_yield:
            div_yield_weight = st.sidebar.slider("Pondération Dividend Yield", 0.0, 1.0, 0.10, 0.1)
            value_components["div_yield"] = div_yield_weight

        # Validation des pondérations du facteur value
        is_valid_value, value_message = validate_components(value_components)
        if not is_valid_value:
            st.sidebar.error(value_message)
            can_run = False
        else:
            st.sidebar.success(value_message)
    else:
        # Utiliser les valeurs par défaut si non personnalisé
        value_components = None

    # Personnalisation du facteur Profitability
    st.sidebar.markdown("---")
    st.sidebar.subheader("Facteur Profitability")
    profitability_components = {}

    custom_profitability = st.sidebar.checkbox("Personnaliser le facteur Profitability", False)

    if custom_profitability:
        st.sidebar.info("Sélectionnez les composantes et leurs pondérations (somme = 1.0)")

        # Gross Profitability (GPOA)
        use_gpoa = st.sidebar.checkbox("Gross Profitability (GPOA)", True)
        if use_gpoa:
            gpoa_weight = st.sidebar.slider("Pondération GPOA", 0.0, 1.0, 0.5, 0.1)
            profitability_components["gpoa"] = gpoa_weight

        # Operating Margin
        use_op_margin = st.sidebar.checkbox("Operating Margin", True)
        if use_op_margin:
            op_margin_weight = st.sidebar.slider("Pondération Operating Margin", 0.0, 1.0, 0.3, 0.1)
            profitability_components["op_margin"] = op_margin_weight

        # Return on Equity
        use_roe = st.sidebar.checkbox("Return on Equity (ROE)", True)
        if use_roe:
            roe_weight = st.sidebar.slider("Pondération ROE", 0.0, 1.0, 0.2, 0.1)
            profitability_components["roe"] = roe_weight

        # Validation des pondérations du facteur profitability
        is_valid_prof, prof_message = validate_components(profitability_components)
        if not is_valid_prof:
            st.sidebar.error(prof_message)
            can_run = False
        else:
            st.sidebar.success(prof_message)
    else:
        # Utiliser les valeurs par défaut si non personnalisé
        profitability_components = None

    # Affichage des paramètres choisis
    st.subheader("Récapitulatif des paramètres")

    # Paramètres généraux - ajustés selon le type de stratégie
    if strategy_type == "conditional":
        general_params = {
            "Paramètre": ["Dossier de données", "Type de stratégie", "Date de début", "Date de fin",
                          "Neutralisation", "Méthode de pondération", "Générer fichier PORT", "Volatility Scaling"],
            "Valeur": [data_folder, strategy_type, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"),
                       "Oui" if use_neutralized else "Non", weighting_method,
                       "Oui" if generate_port_file else "Non",
                       f"Oui ({target_volatility:.1%})" if volatility_scaling else "Non"]
        }
    else:
        general_params = {
            "Paramètre": ["Dossier de données", "Top N", "Type de stratégie", "Date de début", "Date de fin",
                          "Neutralisation", "Méthode de pondération", "Générer fichier PORT", "Volatility Scaling"],
            "Valeur": [data_folder, top_n, strategy_type, start_date.strftime("%Y-%m-%d"),
                       end_date.strftime("%Y-%m-%d"),
                       "Oui" if use_neutralized else "Non", weighting_method,
                       "Oui" if generate_port_file else "Non",
                       f"Oui ({target_volatility:.1%})" if volatility_scaling else "Non"]
        }

    # Affichage des paramètres généraux
    st.table(pd.DataFrame(general_params))

    # Affichage des paramètres de volatility scaling si activé
    if volatility_scaling:
        vol_params = {
            "Paramètre": ["Volatilité cible", "Période de lookback"],
            "Valeur": [f"{target_volatility:.1%}", f"{volatility_lookback_months} mois"]
        }
        st.subheader("Paramètres Volatility Scaling")
        st.table(pd.DataFrame(vol_params))

    # Paramètres d'allocation - affichés uniquement pour unconditional
    if strategy_type != "conditional":
        allocation_params = {
            "Paramètre": ["Allocation: Value", "Allocation: Momentum", "Allocation: Profitability"],
            "Valeur": [f"{value_weight:.2f} ({value_weight * 100:.1f}%)",
                       f"{momentum_weight:.2f} ({momentum_weight * 100:.1f}%)",
                       f"{profitability_weight:.2f} ({profitability_weight * 100:.1f}%)"]
        }
        st.table(pd.DataFrame(allocation_params))

    # Affichage des composantes personnalisées si activées
    if custom_value:
        st.subheader("Composantes personnalisées du facteur Value")
        value_comp_list = []
        value_weight_list = []

        for comp, weight in value_components.items():
            value_comp_list.append(comp)
            value_weight_list.append(f"{weight:.2f} ({weight * 100:.1f}%)")

        st.table(pd.DataFrame({"Composante": value_comp_list, "Pondération": value_weight_list}))

    if custom_profitability:
        st.subheader("Composantes personnalisées du facteur Profitability")
        prof_comp_list = []
        prof_weight_list = []

        for comp, weight in profitability_components.items():
            prof_comp_list.append(comp)
            prof_weight_list.append(f"{weight:.2f} ({weight * 100:.1f}%)")

        st.table(pd.DataFrame({"Composante": prof_comp_list, "Pondération": prof_weight_list}))

    # Exécution de la stratégie
    if st.button("Exécuter la stratégie", disabled=not can_run):
        with st.spinner("Exécution de la stratégie en cours..."):
            try:
                strategy = FactorInvestingStrategy(
                    data_folder=data_folder,
                    top_n=top_n,
                    allocation_weights=allocation_weights if strategy_type != "conditional" else None,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    strategy_type=strategy_type,
                    use_neutralized=use_neutralized,
                    weighting_method=weighting_method,
                    value_components=value_components,
                    profitability_components=profitability_components,
                    volatility_scaling=volatility_scaling,
                    target_volatility=target_volatility,
                    volatility_lookback_months=volatility_lookback_months
                )

                report_file, port_file_path = strategy.run_strategy(generate_port=generate_port_file)

                if generate_port_file and port_file_path:
                    st.success(f"Fichier PORT généré avec succès: {port_file_path}")
                elif not generate_port_file:
                    st.info("Fichier PORT non généré (option désactivée)")

                if report_file:
                    st.success(f"Fichier report généré avec succès: {report_file}")
                    open_report_file(report_file)

            except Exception as e:
                st.error(f"Erreur lors de l'exécution de la stratégie: {str(e)}")


if __name__ == "__main__":
    main()