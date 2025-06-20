import os

import pandas as pd

from data_loader import DataLoader
from factor_calculator import FactorCalculator
from portfolio_analysis import PortfolioAnalysis
from portfolio_constructor import PortfolioConstructor


class FactorInvestingStrategy:
    def __init__(self, data_folder="data", top_n=None,
                 allocation_weights=None, start_date=None, end_date=None,
                 strategy_type=None, use_neutralized=True, weighting_method=None,
                 value_components=None, profitability_components=None,
                 volatility_scaling=False, target_volatility=0.15,
                 volatility_lookback_months=12):
        """
        Initialise la stratégie d'investissement par facteurs.

        Args:
            data_folder: Dossier contenant les données
            top_n: Nombre de titres à sélectionner par facteur
            allocation_weights: Pondération entre les différents facteurs
            start_date: Date de début de la stratégie
            end_date: Date de fin de la stratégie
            strategy_type: Type de stratégie ('conditional' ou 'unconditional')
            use_neutralized: Utiliser les facteurs neutralisés par rapport au momentum
            weighting_method: Méthode de pondération ('equal', 'market_cap', 'min_variance')
            value_components: Dictionnaire des composantes du facteur value et leurs pondérations
            profitability_components: Dictionnaire des composantes du facteur profitability et leurs pondérations
            volatility_scaling: Appliquer le volatility scaling (True/False)
            target_volatility: Volatilité cible annuelle (défaut: 15%)
            volatility_lookback_months: Période de lookback pour calculer la volatilité
        """
        self.data_loader = DataLoader(data_folder)
        self.dataframes = None
        self.factor_calculator = None
        self.portfolio_constructor = None

        self.top_n = top_n
        self.start_date = pd.to_datetime(start_date) if start_date else None
        self.end_date = pd.to_datetime(end_date) if end_date else None
        self.strategy_type = strategy_type
        self.use_neutralized = use_neutralized
        self.weighting_method = weighting_method
        self.allocation_weights = allocation_weights

        self.value_components = value_components
        self.profitability_components = profitability_components

        self.volatility_scaling = volatility_scaling
        self.target_volatility = target_volatility
        self.volatility_lookback_months = volatility_lookback_months

        self.value_factor = None
        self.profitability_factor = None
        self.momentum_factor = None
        self.neutralized_value = None
        self.neutralized_profitability = None

        self.portfolio_momentum = None
        self.portfolio_value = None
        self.portfolio_profitability = None
        self.combined_portfolio = None
        self.combined_weights = None

        self.metrics = None

        self.port_data = None

    def load_data(self):
        self.dataframes = self.data_loader.load_data()
        return self.dataframes

    def calculate_factors(self):
        # Initialiser FactorCalculator avec les composantes personnalisées si spécifiées
        self.factor_calculator = FactorCalculator(
            self.dataframes,
            value_components=self.value_components,
            profitability_components=self.profitability_components
        )

        self.value_factor = self.factor_calculator.calculate_value_factor()
        self.profitability_factor = self.factor_calculator.calculate_profitability_factor()
        self.momentum_factor = self.factor_calculator.calculate_momentum_factor()

        if self.use_neutralized:
            self.neutralized_value, self.neutralized_profitability, _ = self.factor_calculator.neutralize_all_factors(
                self.value_factor, self.momentum_factor, self.profitability_factor
            )
        else:
            self.neutralized_value = self.value_factor
            self.neutralized_profitability = self.profitability_factor

        return (self.value_factor, self.profitability_factor, self.momentum_factor)

    def construct_portfolios(self):
        value_factor = self.neutralized_value if self.use_neutralized else self.value_factor
        profitability_factor = self.neutralized_profitability if self.use_neutralized else self.profitability_factor
        momentum_factor = self.momentum_factor

        self.portfolio_constructor = PortfolioConstructor(
            self.dataframes["PX_LAST"],
            self.dataframes["Universe_Composition"],
            start_date=self.start_date,
            end_date=self.end_date
        )

        # Pour la pondération par capitalisation boursière
        market_cap_data = self.dataframes["Free_Float_Market_Cap"] if self.weighting_method == "market_cap" else None

        if self.strategy_type == "conditional":
            combined_portfolio, combined_weights = self.portfolio_constructor.construct_conditional_portfolio(
                value_factor, momentum_factor, profitability_factor,
                weighting_method=self.weighting_method,
                market_cap_data=market_cap_data,
                volatility_scaling=self.volatility_scaling,
                target_volatility=self.target_volatility,
                volatility_lookback_months=self.volatility_lookback_months
            )

            self.combined_portfolio = combined_portfolio
            self.combined_weights = combined_weights

        else:  # "unconditional"
            self.portfolio_momentum, weights_momentum = self.portfolio_constructor.construct_portfolio(
                momentum_factor, self.top_n,
                weighting_method=self.weighting_method,
                market_cap_data=market_cap_data,
                volatility_scaling=self.volatility_scaling,
                target_volatility=self.target_volatility,
                volatility_lookback_months=self.volatility_lookback_months
            )

            self.portfolio_value, weights_value = self.portfolio_constructor.construct_portfolio(
                factor=value_factor,
                top_n=self.top_n,
                weighting_method=self.weighting_method,
                market_cap_data=market_cap_data,
                volatility_scaling=self.volatility_scaling,
                target_volatility=self.target_volatility,
                volatility_lookback_months=self.volatility_lookback_months
            )

            self.portfolio_profitability, weights_profitability = self.portfolio_constructor.construct_portfolio(
                factor=profitability_factor,
                top_n=self.top_n,
                weighting_method=self.weighting_method,
                market_cap_data=market_cap_data,
                volatility_scaling=self.volatility_scaling,
                target_volatility=self.target_volatility,
                volatility_lookback_months=self.volatility_lookback_months
            )

            combined_scores = self.factor_calculator.calculate_combined_factor(
                value_factor, momentum_factor, profitability_factor,
                weights=self.allocation_weights
            )

            self.combined_portfolio, self.combined_weights = self.portfolio_constructor.construct_portfolio(
                combined_scores, self.top_n,
                weighting_method=self.weighting_method,
                market_cap_data=market_cap_data,
                volatility_scaling=self.volatility_scaling,
                target_volatility=self.target_volatility,
                volatility_lookback_months=self.volatility_lookback_months
            )

        return (self.portfolio_momentum, self.portfolio_value,
                self.portfolio_profitability, self.combined_portfolio)

    def generate_outputPORT(self):
        """
        Génère un fichier PORT au format Excel pour Bloomberg.

        Returns:
            str: Chemin du fichier PORT généré
        """
        # Créer le dossier output s'il n'existe pas
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        i_row = 0
        df = pd.DataFrame(columns=["PORTFOLIO NAME", "SECURITY_ID", "Weight", "Date"])

        # Créer le nom du portefeuille basé sur les paramètres réels
        vol_suffix = f"_VolScaling{int(self.target_volatility * 100)}" if self.volatility_scaling else ""
        portfolio_name = f"Factor_{self.strategy_type}_{self.weighting_method}{vol_suffix}"

        # Pour chaque date dans les poids du portefeuille
        for date in self.combined_weights.index:
            # Récupérer les poids pour cette date
            weights = self.combined_weights.loc[date]

            # Pour chaque titre avec un poids positif
            for ticker, weight in weights.items():
                if weight > 0:
                    # Créer une ligne pour ce titre
                    row = {
                        'PORTFOLIO NAME': portfolio_name,
                        'SECURITY_ID': ticker,
                        'Weight': weight,
                        'Date': date
                    }

                    # Ajouter la ligne au DataFrame
                    df.loc[i_row] = list(row.values())
                    i_row += 1

        # Sauvegarder le DataFrame
        self.port_data = df.copy()
        file_path = os.path.join(output_dir, f"PORT_{portfolio_name}.xlsx")
        self.port_data.to_excel(file_path, index=False)

        return file_path

    def run_strategy(self, generate_port=False):
        """
        Exécute la stratégie d'investissement complète.

        Args:
            generate_port: Si True, génère un fichier PORT Excel pour Bloomberg
        Returns:
            str: Chemin du fichier PORT généré ou None si generate_port est False
        """
        self.load_data()
        print("data loaded")
        self.calculate_factors()
        print("factors computed")
        self.construct_portfolios()

        vol_scaling_info = f" with volatility scaling ({self.target_volatility:.1%} target)" if self.volatility_scaling else ""
        print(
            f"portfolios constructed using {self.strategy_type} strategy with {self.weighting_method} weighting{vol_scaling_info}")

        combined_returns = self.combined_portfolio.pct_change()

        # Préparer les paramètres de stratégie pour le rapport
        strategy_params = {
            "Strategy Type": self.strategy_type,
            "Weighting Method": self.weighting_method,
            "Start Date": self.start_date.strftime("%Y-%m-%d") if self.start_date else "Not specified",
            "End Date": self.end_date.strftime("%Y-%m-%d") if self.end_date else "Not specified",
            "Use Neutralized Factors": "Yes" if self.use_neutralized else "No",
            "Volatility Scaling": f"Yes (target: {self.target_volatility:.1%})" if self.volatility_scaling else "No",
            "Volatility Lookback": f"{self.volatility_lookback_months} months",
        }

        # Ajouter top_n seulement pour unconditional
        if self.strategy_type == "unconditional" and self.top_n:
            strategy_params["Top N Securities"] = str(self.top_n)

        # Ajouter les allocations pour unconditional
        if self.strategy_type == "unconditional" and self.allocation_weights:
            strategy_params["Value Allocation"] = f"{self.allocation_weights.get('value', 0):.1%}"
            strategy_params["Momentum Allocation"] = f"{self.allocation_weights.get('momentum', 0):.1%}"
            strategy_params["Profitability Allocation"] = f"{self.allocation_weights.get('profitability', 0):.1%}"

        # Ajouter les composantes personnalisées si définies
        if self.value_components:
            value_comp_str = ", ".join([f"{k}: {v:.1%}" for k, v in self.value_components.items()])
            strategy_params["Custom Value Components"] = value_comp_str

        if self.profitability_components:
            prof_comp_str = ", ".join([f"{k}: {v:.1%}" for k, v in self.profitability_components.items()])
            strategy_params["Custom Profitability Components"] = prof_comp_str

        # Créer l'analyseur avec les paramètres
        analyzer = PortfolioAnalysis(combined_returns, strategy_params=strategy_params, weights_df=self.combined_weights)
        self.metrics = analyzer.calculate_metrics(annualization_factor=12)


        report_file = analyzer.generate_quantstats_report(serie=self.combined_portfolio)

        # Générer le fichier PORT si demandé
        port_file_path = None
        if generate_port:
            port_file_path = self.generate_outputPORT()
            print(f"\nFichier PORT Excel généré: {port_file_path}")

        return report_file, port_file_path