import pandas as pd

from portfolio_weights import PortfolioWeighter

class PortfolioConstructor:
    def __init__(self, price_data, composition_data, start_date=None, end_date=None):
        self.price_data = price_data
        self.all_price_date = price_data
        self.composition_data = composition_data

        if not isinstance(self.price_data.index, pd.DatetimeIndex):
            self.price_data.index = pd.to_datetime(self.price_data.index)

        if not isinstance(self.composition_data.index, pd.DatetimeIndex):
            self.composition_data.index = pd.to_datetime(self.composition_data.index)

        if start_date is not None and end_date is not None:
            self.price_data = self.price_data[(self.price_data.index >= start_date) &
                                              (self.price_data.index <= end_date)]
            self.composition_data = self.composition_data[(self.composition_data.index >= start_date) &
                                                          (self.composition_data.index <= end_date)]

        self.start_date = start_date if start_date is not None else self.price_data.index.min()
        self.end_date = end_date if end_date is not None else self.price_data.index.max()

    def get_tickers_at_date(self, date):
        composition = self.composition_data.loc[date]
        valid_tickers = composition[composition == 1].index.tolist()
        return valid_tickers

    def _prepare_portfolio_construction(self):
        """Prépare les structures communes pour la construction de portefeuille"""
        filtered_dates = self.price_data.index[
            (self.price_data.index >= self.start_date) &
            (self.price_data.index <= self.end_date)
            ]

        rebalance_dates = filtered_dates.sort_values()
        weights = pd.DataFrame(0.0, index=filtered_dates, columns=self.price_data.columns)
        previous_weights = pd.Series(0.0, index=self.price_data.columns)

        # Créer une Series pour associer chaque date à sa période de rééquilibrage
        rebalance_period = pd.Series(index=filtered_dates, dtype='datetime64[ns]')

        # Attribuer à chaque date la date de rééquilibrage correspondante
        for i in range(len(rebalance_dates) - 1):
            current_date = rebalance_dates[i]
            next_date = rebalance_dates[i + 1]
            mask = (filtered_dates >= current_date) & (filtered_dates < next_date)
            rebalance_period.loc[mask] = current_date

        # Traiter la dernière période
        if len(rebalance_dates) > 0:
            mask = filtered_dates >= rebalance_dates[-1]
            rebalance_period.loc[mask] = rebalance_dates[-1]

        return filtered_dates, rebalance_period, weights,  previous_weights

    def _finalize_portfolio(self, filtered_dates, rebalance_period, portfolio_weights, weights,
                            previous_weights):
        """Finalise le calcul du portefeuille"""
        # Appliquer les poids à toutes les dates
        for date in filtered_dates:
            rebal_date = rebalance_period.loc[date]
            weights.loc[date] = portfolio_weights[rebal_date]

        # Calculer les rendements du portefeuille
        monthly_returns = self.price_data.loc[filtered_dates].pct_change(fill_method=None).fillna(0)
        portfolio_returns = (monthly_returns * weights.shift(1)).sum(axis=1)

        # Calculer la valeur cumulative du portefeuille
        portfolio_value = (1 + portfolio_returns).cumprod()

        return portfolio_value, weights

    def construct_portfolio(self, factor, top_n=10,
                            weighting_method="equal", market_cap_data=None,
                            volatility_scaling=False, target_volatility=0.15,
                            volatility_lookback_months=6):

        # Préparation des structures communes
        filtered_dates, rebalance_period, weights, previous_weights = self._prepare_portfolio_construction()
        portfolio_weights = {}

        sort_ascending = False  # valeurs élevées préférées

        for current_date in rebalance_period.unique():

            valid_tickers = self.get_tickers_at_date(current_date)
            current_scores = factor.loc[current_date][valid_tickers].dropna()
            current_scores = pd.to_numeric(current_scores, errors='coerce')

            # Calculer les nouveaux poids
            if weighting_method == "market_cap" and market_cap_data is not None:
                current_mcap = market_cap_data.loc[current_date]
                new_weights = PortfolioWeighter.market_cap_weight(current_scores, top_n, current_mcap,
                                                                  sort_ascending)
            elif weighting_method == "min_variance":
                new_weights = PortfolioWeighter.minimum_variance_weight(
                    current_scores, top_n, self.all_price_date, current_date,
                    volatility_lookback_months, sort_ascending)
            else:  # Par défaut : equal_weight
                new_weights = PortfolioWeighter.equal_weight(current_scores, top_n, sort_ascending)

            # Appliquer le volatility scaling si demandé
            if volatility_scaling:
                new_weights = PortfolioWeighter.volatility_scaling_weight(
                    new_weights, self.all_price_date, current_date,
                    target_volatility, volatility_lookback_months
                )

            portfolio_weights[current_date] = new_weights
            previous_weights = new_weights

        return self._finalize_portfolio(filtered_dates, rebalance_period, portfolio_weights, weights,
                                         previous_weights)

    def construct_conditional_portfolio(self, value_factor, momentum_factor, profitability_factor,
                                                weighting_method="equal",
                                                market_cap_data=None,
                                                volatility_scaling=False, target_volatility=0.15,
                                                volatility_lookback_months=12):
        """
        Implémentation de la méthodologie conditionnelle.

        Cette version implémente des tris emboîtés avec construction de portfolios multiples
        pour chaque combinaison Value/Momentum/Profitability avant agrégation finale.
        """
        filtered_dates, rebalance_period, weights, previous_weights = self._prepare_portfolio_construction()
        portfolio_weights = {}

        for current_date in rebalance_period.unique():
            valid_tickers = self.get_tickers_at_date(current_date)
            value_scores = value_factor.loc[current_date][valid_tickers].dropna()
            momentum_scores = momentum_factor.loc[current_date][valid_tickers].dropna()
            profitability_scores = profitability_factor.loc[current_date][valid_tickers].dropna()

            common_tickers = list(
                set(value_scores.index) & set(momentum_scores.index) & set(profitability_scores.index))

            if len(common_tickers) < 10:  # Minimum de titres requis
                new_weights = pd.Series(0.0, index=self.price_data.columns)
                portfolio_weights[current_date] = new_weights
                continue

            # Étape 1: Tri initial sur Value
            n_tickers = len(common_tickers)
            value_high_n = int(n_tickers * 0.3)
            value_low_n = int(n_tickers * 0.3)

            value_sorted = value_scores[common_tickers].sort_values(ascending=False)
            value_high_tickers = set(value_sorted.head(value_high_n).index)
            value_low_tickers = set(value_sorted.tail(value_low_n).index)
            value_neutral_tickers = set(common_tickers) - value_high_tickers - value_low_tickers

            # Étape 2: Pour chaque groupe Value, trier sur Momentum et Profitability
            conditional_portfolios = {}

            for value_group, value_tickers in [('high', value_high_tickers),
                                               ('neutral', value_neutral_tickers),
                                               ('low', value_low_tickers)]:

                if len(value_tickers) == 0:
                    continue

                value_tickers_list = list(value_tickers)

                # Tri sur Momentum conditionnel au groupe Value
                momentum_subset = momentum_scores[value_tickers_list]
                momentum_high_n = max(1, int(len(value_tickers_list) * 0.3))
                momentum_low_n = max(1, int(len(value_tickers_list) * 0.3))

                momentum_sorted = momentum_subset.sort_values(ascending=False)
                momentum_high = set(momentum_sorted.head(momentum_high_n).index)
                momentum_low = set(momentum_sorted.tail(momentum_low_n).index)
                momentum_neutral = set(value_tickers_list) - momentum_high - momentum_low

                # Tri sur Profitability conditionnel au groupe Value
                profitability_subset = profitability_scores[value_tickers_list]
                profitability_high_n = max(1, int(len(value_tickers_list) * 0.3))
                profitability_low_n = max(1, int(len(value_tickers_list) * 0.3))

                profitability_sorted = profitability_subset.sort_values(ascending=False)
                profitability_high = set(profitability_sorted.head(profitability_high_n).index)
                profitability_low = set(profitability_sorted.tail(profitability_low_n).index)
                profitability_neutral = set(value_tickers_list) - profitability_high - profitability_low

                # Étape 3: Construction des portfolios conditionnels
                for mom_group, mom_tickers in [('high', momentum_high), ('neutral', momentum_neutral),
                                               ('low', momentum_low)]:
                    for prof_group, prof_tickers in [('high', profitability_high), ('neutral', profitability_neutral),
                                                     ('low', profitability_low)]:

                        # Intersection des trois groupes
                        intersection_tickers = list(value_tickers & mom_tickers & prof_tickers)

                        if len(intersection_tickers) > 0:
                            portfolio_name = f"{value_group}_{mom_group}_{prof_group}"
                            conditional_portfolios[portfolio_name] = intersection_tickers

            # Étape 4: Logique d'éligibilité
            # Pour être éligible au "buy list": doit être value_high ET pas momentum_low ET pas profitability_low
            buy_eligible = []
            for portfolio_name, tickers in conditional_portfolios.items():
                value_group, mom_group, prof_group = portfolio_name.split('_')

                # Logique buy: Value high + pas momentum low + pas profitability low
                if (value_group == 'high' and
                        mom_group != 'low' and
                        prof_group != 'low'):
                    buy_eligible.extend(tickers)

            # Logique sell (pour long/short, mais ici on ne l'utilise pas pour long-only)
            sell_eligible = []
            for portfolio_name, tickers in conditional_portfolios.items():
                value_group, mom_group, prof_group = portfolio_name.split('_')

                # Logique sell: Value low + pas momentum high + pas profitability high
                if (value_group == 'low' and
                        mom_group != 'high' and
                        prof_group != 'high'):
                    sell_eligible.extend(tickers)

            # Étape 5: Construction finale du portefeuille long-only
            final_tickers = list(set(buy_eligible))  # Éliminer les doublons

            if len(final_tickers) == 0:
                new_weights = pd.Series(0.0, index=self.price_data.columns)
            else:
                # Calcul des poids selon la méthode choisie
                if weighting_method == "market_cap" and market_cap_data is not None:
                    current_mcap = market_cap_data.loc[current_date]
                    new_weights = PortfolioWeighter.market_cap_weight(final_tickers, None, current_mcap)
                elif weighting_method == "min_variance":
                    new_weights = PortfolioWeighter.minimum_variance_weight(
                        final_tickers, None, self.all_price_date, current_date, volatility_lookback_months)
                else:  # equal_weight
                    new_weights = PortfolioWeighter.equal_weight(final_tickers)

                # Appliquer le volatility scaling si demandé
                if volatility_scaling:
                    new_weights = PortfolioWeighter.volatility_scaling_weight(
                        new_weights, self.all_price_date, current_date,
                        target_volatility, volatility_lookback_months
                    )

            portfolio_weights[current_date] = new_weights
            previous_weights = new_weights

        return self._finalize_portfolio(filtered_dates, rebalance_period, portfolio_weights, weights,
                                        previous_weights)