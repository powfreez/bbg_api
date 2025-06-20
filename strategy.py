"""
Script principal pour exécuter la stratégie d'investissement factorielle
avec les paramètres spécifiés (stratégie conditionnelle).
"""

import os
from datetime import date
from factor_investing_strategy import FactorInvestingStrategy


def main():
    """
    Exécute la stratégie d'investissement factorielle avec les paramètres configurés.
    """
    config = {
        "data_folder": "data",
        "strategy_type": "conditional",
        "start_date": "2012-01-01",
        "end_date": "2024-12-31",
        "use_neutralized": True,
        "weighting_method": "market_cap",

        "top_n": None,
        "allocation_weights": None,

        "value_components": {
            "btm": 0.20,
            "ebit_ev": 0.70,
            "ebitda_ev": 0.10
        },

        "profitability_components": {
            "gpoa": 0.40,
            "op_margin": 0.30,
            "roe": 0.30
        },
        "generate_port": True,

        "volatility_scaling": False,
        "target_volatility": 0.15,
        "volatility_lookback_months": 6
    }

    # Initialisation de la stratégie
    strategy = FactorInvestingStrategy(
        data_folder=config['data_folder'],
        top_n=config['top_n'],
        allocation_weights=config['allocation_weights'],
        start_date=config['start_date'],
        end_date=config['end_date'],
        strategy_type=config['strategy_type'],
        use_neutralized=config['use_neutralized'],
        weighting_method=config['weighting_method'],
        value_components=config['value_components'],
        profitability_components=config['profitability_components'],
        volatility_scaling=config['volatility_scaling'],
        target_volatility=config['target_volatility'],
        volatility_lookback_months=config['volatility_lookback_months']
    )

    strategy.run_strategy(generate_port=config['generate_port'])


if __name__ == "__main__":
    main()