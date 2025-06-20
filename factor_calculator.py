import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.decomposition import PCA


class FactorCalculator:
    def __init__(self, dataframes,
                 value_components=None,
                 profitability_components=None):
        """
        Initialise le calculateur de facteurs avec des options de personnalisation.

        Args:
            dataframes: Dictionnaire de DataFrames contenant les données financières
            value_components: Dictionnaire de pondérations pour les composantes du facteur value
                              Par défaut: {'btm': 0.4, 'ebit_ev': 0.25, 'ebitda_ev': 0.25, 'div_yield': 0.1}
            profitability_components: Dictionnaire de pondérations pour les composantes du facteur profitability
                                     Par défaut: {'gpoa': 0.5, 'op_margin': 0.3, 'roe': 0.2}
        """
        self.dataframes = dataframes

        # Valeurs par défaut pour les composantes value
        self.value_components = {
            'btm': 0.4,
            'ebit_ev': 0.25,
            'ebitda_ev': 0.25,
            'div_yield': 0.1
        }

        # Valeurs par défaut pour les composantes profitability
        self.profitability_components = {
            'gpoa': 0.5,
            'op_margin': 0.3,
            'roe': 0.2
        }

        # Mise à jour avec les composantes personnalisées si fournies
        if value_components:
            total = sum(value_components.values())
            self.value_components = {k: v / total for k, v in value_components.items()}

        if profitability_components:
            total = sum(profitability_components.values())
            self.profitability_components = {k: v / total for k, v in profitability_components.items()}

        # Cache pour optimisations
        self._quantile_cache = {}

    @staticmethod
    def calculate_z_score(df):
        return (df - df.mean(axis=1, skipna=True).values.reshape(-1, 1)) / df.std(axis=1, skipna=True).values.reshape(
            -1, 1)

    def clip_extreme_values(self, df, lower_percentile=0.05, upper_percentile=0.95):

        cache_key = (id(df), lower_percentile, upper_percentile)

        if cache_key not in self._quantile_cache:
            lower_bounds = df.quantile(lower_percentile, axis=1)
            upper_bounds = df.quantile(upper_percentile, axis=1)
            self._quantile_cache[cache_key] = (lower_bounds, upper_bounds)
        else:
            lower_bounds, upper_bounds = self._quantile_cache[cache_key]

        df_clipped = df.clip(lower=lower_bounds.values.reshape(-1, 1),
                             upper=upper_bounds.values.reshape(-1, 1), axis=0)
        return df_clipped

    def calculate_value_factor(self):

        result_components = {}

        # Book-to-Market
        if 'btm' in self.value_components and self.value_components['btm'] > 0:
            book_value_per_share = self.dataframes["Book_Value_Per_Share"]
            shares_outstanding = self.dataframes["Shares_Outstanding"]
            market_cap = self.dataframes["Market_Cap"]

            total_book_value = book_value_per_share * shares_outstanding
            book_to_market = total_book_value / market_cap.replace(0, np.nan)
            book_to_market = book_to_market.replace([np.inf, -np.inf], np.nan)
            book_to_market_clipped = self.clip_extreme_values(book_to_market)
            result_components['btm'] = book_to_market_clipped

        # EBIT/EV
        if 'ebit_ev' in self.value_components and self.value_components['ebit_ev'] > 0:
            ev_ebit = self.dataframes.get("EV_EBIT_ADJUSTED", pd.DataFrame())
            if not ev_ebit.empty:
                ebit_ev = 1 / ev_ebit.replace([0, np.inf, -np.inf], np.nan)
                ebit_ev_clipped = self.clip_extreme_values(ebit_ev)
                result_components['ebit_ev'] = ebit_ev_clipped

        # EBITDA/EV
        if 'ebitda_ev' in self.value_components and self.value_components['ebitda_ev'] > 0:
            ev_ebitda = self.dataframes.get("EV_EBITDA_ADJUSTED", pd.DataFrame())
            if not ev_ebitda.empty:
                ebitda_ev = 1 / ev_ebitda.replace([0, np.inf, -np.inf], np.nan)
                ebitda_ev_clipped = self.clip_extreme_values(ebitda_ev)
                result_components['ebitda_ev'] = ebitda_ev_clipped

        # Dividend Yield
        if 'div_yield' in self.value_components and self.value_components['div_yield'] > 0:
            div_yield = self.dataframes.get("DIVIDEND_12_MONTH_YIELD", pd.DataFrame())
            if not div_yield.empty:
                div_yield_clipped = self.clip_extreme_values(div_yield)
                result_components['div_yield'] = div_yield_clipped

        # Construction du composite et standardisation
        if result_components:
            standardized_components = {}
            for component, data in result_components.items():
                standardized_components[component] = self.calculate_z_score(data)

            weighted_components = []
            for component, weight in self.value_components.items():
                if component in standardized_components:
                    weighted_components.append(weight * standardized_components[component])

            if weighted_components:
                composite = sum(weighted_components)
                return composite

        return pd.DataFrame()

    def calculate_profitability_factor(self):

        result_components = {}

        total_assets = self.dataframes["Total_Assets"].replace(0, np.nan)

        # Gross Profitability
        if 'gpoa' in self.profitability_components and self.profitability_components['gpoa'] > 0:
            gross_profit = self.dataframes["Gross_Profit"]
            gpoa = gross_profit / total_assets
            gpoa = gpoa.replace([np.inf, -np.inf], np.nan)
            gpoa_clipped = self.clip_extreme_values(gpoa)
            result_components['gpoa'] = gpoa_clipped

        # Operating Profitability
        if 'op_margin' in self.profitability_components and self.profitability_components['op_margin'] > 0:
            op_inc = self.dataframes["Operating_Income"]
            op_margin = op_inc / total_assets
            op_margin = op_margin.replace([np.inf, -np.inf], np.nan)
            op_margin_clipped = self.clip_extreme_values(op_margin)
            result_components['op_margin'] = op_margin_clipped

        # Return on Equity
        if 'roe' in self.profitability_components and self.profitability_components['roe'] > 0:
            roe = self.dataframes["Return_on_Equity"]
            roe_clipped = self.clip_extreme_values(roe)
            result_components['roe'] = roe_clipped

        # Même logique de standardisation que Value
        if result_components:
            standardized_components = {}
            for component, data in result_components.items():
                standardized_components[component] = self.calculate_z_score(data)

            weighted_components = []
            for component, weight in self.profitability_components.items():
                if component in standardized_components:
                    weighted_components.append(weight * standardized_components[component])

            if weighted_components:
                composite = sum(weighted_components)
                return composite

        return pd.DataFrame()

    @staticmethod
    def calculate_combined_factor(value_factor, momentum_factor, profitability_factor,
                                  weights=None):
        if weights is None:
            weights = {"value": 0.5, "momentum": 0.25, "profitability": 0.25}

        common_dates = value_factor.index.intersection(momentum_factor.index).intersection(profitability_factor.index)
        common_columns = value_factor.columns.intersection(momentum_factor.columns).intersection(
            profitability_factor.columns)

        value_aligned = value_factor.loc[common_dates, common_columns]
        momentum_aligned = momentum_factor.loc[common_dates, common_columns]
        profitability_aligned = profitability_factor.loc[common_dates, common_columns]

        combined_factor = (weights.get("value", 0.5) * value_aligned +
                           weights.get("momentum", 0.25) * momentum_aligned +
                           weights.get("profitability", 0.25) * profitability_aligned)

        return combined_factor

    def calculate_book_to_market_ratio(self):

        book_value_per_share = self.dataframes["Book_Value_Per_Share"]
        shares_outstanding = self.dataframes["Shares_Outstanding"]
        free_float_market_cap = self.dataframes["Free_Float_Market_Cap"]
        free_float_market_cap_lagged = free_float_market_cap.shift(6)

        total_book_value = book_value_per_share * shares_outstanding
        book_to_market = total_book_value / free_float_market_cap_lagged
        book_to_market = book_to_market.replace([np.inf, -np.inf], np.nan)

        return book_to_market

    def calculate_momentum_factor(self, lookback_period=12):

        price_data = self.dataframes["PX_LAST"]

        # Calcul des rendements avec décalage
        momentum = price_data.pct_change(periods=lookback_period).shift(1)

        momentum_filtered = momentum.where(momentum.abs() > 0.0001, np.nan)  # Seuil plus bas

        rolling_mean = momentum_filtered.rolling(window=36, min_periods=12).mean()
        rolling_std = momentum_filtered.rolling(window=36, min_periods=12).std()
        momentum_z = (momentum_filtered - rolling_mean) / rolling_std

        return momentum_z

    def neutralize_factor(self, factor, reference_factor):
        neutralized_factor = pd.DataFrame(np.nan, index=factor.index, columns=factor.columns)

        # Pré-calculer les dates communes
        common_dates = factor.index.intersection(reference_factor.index)

        for date in common_dates:
            y_data = factor.loc[date].dropna()
            x_data = reference_factor.loc[date].dropna()

            common_tickers = y_data.index.intersection(x_data.index)

            if len(common_tickers) < 5:
                continue

            X = x_data[common_tickers].values.reshape(-1, 1)
            y = y_data[common_tickers].values

            if np.std(X) < 1e-10 or np.std(y) < 1e-10:
                continue

            model = LinearRegression()
            model.fit(X, y)

            residuals = y - model.predict(X)

            neutralized_factor.loc[date, common_tickers] = residuals

        return neutralized_factor

    def neutralize_all_factors(self, value_factor, momentum_factor, profitability_factor):
        # Neutraliser Value et Profitability par rapport à Momentum
        neutralized_value = self.neutralize_factor(value_factor, momentum_factor)
        neutralized_profitability = self.neutralize_factor(profitability_factor, momentum_factor)

        return neutralized_value, neutralized_profitability, momentum_factor