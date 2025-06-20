import pandas as pd
import numpy as np

class PortfolioWeighter:
    """Classe pour calculer différentes méthodes de pondération de portefeuille."""

    @staticmethod
    def equal_weight(scores_or_tickers, top_n=None, sort_ascending=False):
        """
        Attribue des poids égaux aux titres sélectionnés.

        Args:
            scores_or_tickers: Soit une Series de scores, soit une liste de tickers déjà sélectionnés
            top_n: Nombre de titres à sélectionner (ignoré si scores_or_tickers est une liste)
            sort_ascending: Ordre de tri (ignoré si scores_or_tickers est une liste)

        Returns:
            pd.Series: Série avec les poids attribués
        """
        # Déterminer si l'entrée est une Series de scores ou une liste de tickers
        if isinstance(scores_or_tickers, pd.Series):
            # Cas construct_portfolio (standard)
            scores = scores_or_tickers
            valid_scores = scores.dropna()

            if len(valid_scores) == 0:
                return pd.Series(dtype=float)

            actual_top_n = min(top_n, len(valid_scores)) if top_n is not None else len(valid_scores)

            if actual_top_n == 0:
                return pd.Series(dtype=float)

            if sort_ascending:
                selected_tickers = valid_scores.nsmallest(actual_top_n).index.tolist()
            else:
                selected_tickers = valid_scores.nlargest(actual_top_n).index.tolist()

            weights = pd.Series(0.0, index=scores.index)
        else:
            # Cas construct_conditional_portfolio (liste de tickers déjà sélectionnés)
            selected_tickers = scores_or_tickers
            weights = pd.Series(0.0, index=selected_tickers)

        # Attribuer des poids égaux
        weights[selected_tickers] = 1.0 / len(selected_tickers)
        return weights

    @staticmethod
    def market_cap_weight(scores_or_tickers, top_n=None, market_cap_data=None, sort_ascending=False):
        """
        Attribue des poids proportionnels à la capitalisation boursière des titres sélectionnés.

        Args:
            scores_or_tickers: Soit une Series de scores, soit une liste de tickers déjà sélectionnés
            top_n: Nombre de titres à sélectionner (ignoré si scores_or_tickers est une liste)
            market_cap_data: Données de capitalisation boursière
            sort_ascending: Ordre de tri (ignoré si scores_or_tickers est une liste)

        Returns:
            pd.Series: Série avec les poids attribués
        """
        # Déterminer si l'entrée est une Series de scores ou une liste de tickers
        if isinstance(scores_or_tickers, pd.Series):
            # Cas construct_portfolio (standard)
            scores = scores_or_tickers
            valid_scores = scores.dropna()

            if len(valid_scores) == 0:
                return pd.Series(dtype=float)

            actual_top_n = min(top_n, len(valid_scores)) if top_n is not None else len(valid_scores)

            if actual_top_n == 0:
                return pd.Series(dtype=float)

            if sort_ascending:
                selected_tickers = valid_scores.nsmallest(actual_top_n).index.tolist()
            else:
                selected_tickers = valid_scores.nlargest(actual_top_n).index.tolist()

            weights = pd.Series(0.0, index=scores.index)
        else:
            # Cas construct_conditional_portfolio (liste de tickers déjà sélectionnés)
            selected_tickers = scores_or_tickers
            weights = pd.Series(0.0, index=market_cap_data.index)

        # Filtrer les capitalisations boursières pour les tickers sélectionnés
        mcap_selected = market_cap_data[selected_tickers].fillna(0)

        # Vérifier si la somme des capitalisations est non nulle
        total_mcap = mcap_selected.sum()
        if total_mcap <= 0:
            # En cas de données manquantes, revenir à un poids égal
            weights[selected_tickers] = 1.0 / len(selected_tickers)
        else:
            # Calculer les poids proportionnels à la capitalisation boursière
            weights[selected_tickers] = mcap_selected / total_mcap

        return weights

    @staticmethod
    def volatility_scaling_weight(initial_weights, price_data, current_date,
                                  target_volatility=0.15, lookback_months=12):
        """
        Applique le volatility scaling aux poids initiaux.

        Args:
            initial_weights: Poids initiaux du portefeuille (pd.Series)
            price_data: Données de prix historiques (pd.DataFrame)
            current_date: Date actuelle pour le calcul
            target_volatility: Volatilité cible annuelle (défaut: 15%)
            lookback_months: Nombre de mois pour calculer la volatilité historique

        Returns:
            pd.Series: Poids ajustés avec volatility scaling
        """
        if initial_weights.sum() == 0:
            return initial_weights

        # Calculer la période de lookback
        lookback_start = current_date - pd.DateOffset(months=lookback_months)

        # Filtrer les données de prix pour la période de lookback
        price_subset = price_data[
            (price_data.index >= lookback_start) &
            (price_data.index <= current_date)
            ]

        if len(price_subset) < 2:
            return initial_weights  # Pas assez de données historiques

        # Calculer les rendements mensuels
        price_subset = price_subset.dropna(axis=1)
        returns = price_subset.pct_change(fill_method=None).dropna()

        if len(returns) == 0:
            return initial_weights

        # Calculer la matrice de covariance annualisée
        returns_cov_matrix = returns.cov() * 12  # Annualiser (données mensuelles)

        # Aligner les poids avec la matrice de covariance
        common_assets = initial_weights.index.intersection(returns_cov_matrix.index)
        if len(common_assets) == 0:
            return initial_weights

        aligned_weights = initial_weights.reindex(common_assets).fillna(0)
        aligned_cov = returns_cov_matrix.reindex(common_assets, columns=common_assets).fillna(0)

        # Calculer la volatilité actuelle du portefeuille
        portfolio_variance = np.dot(aligned_weights.values, np.dot(aligned_cov.values, aligned_weights.values))
        current_volatility = np.sqrt(portfolio_variance) if portfolio_variance > 0 else 0.0

        if current_volatility == 0:
            return initial_weights

        # Calculer le facteur de scaling
        scaling_factor = target_volatility / current_volatility

        # Appliquer le scaling
        scaled_weights = initial_weights * scaling_factor

        # Normaliser si nécessaire pour que la somme des poids soit <= 1
        if scaled_weights.sum() > 1:
            scaled_weights = scaled_weights / scaled_weights.sum()

        return scaled_weights

    @staticmethod
    def minimum_variance_weight(scores_or_tickers, top_n=None, price_data=None,
                                current_date=None, lookback_months=12, sort_ascending=False):
        """
        Calcule les poids optimaux selon le critère de variance minimale.

        Args:
            scores_or_tickers: Soit une Series de scores, soit une liste de tickers déjà sélectionnés
            top_n: Nombre de titres à sélectionner (ignoré si scores_or_tickers est une liste)
            price_data: Données de prix historiques (pd.DataFrame) - REQUIS
            current_date: Date actuelle pour le calcul - REQUIS
            lookback_months: Nombre de mois pour calculer la matrice de covariance (défaut: 12)
            sort_ascending: Ordre de tri (ignoré si scores_or_tickers est une liste)

        Returns:
            pd.Series: Série avec les poids optimisés (variance minimale)
        """
        from scipy.optimize import minimize

        if price_data is None or current_date is None:
            raise ValueError("price_data et current_date sont requis pour l'optimisation minimum variance")

        # Déterminer si l'entrée est une Series de scores ou une liste de tickers
        if isinstance(scores_or_tickers, pd.Series):
            # Cas construct_portfolio (standard)
            scores = scores_or_tickers
            valid_scores = scores.dropna()

            if len(valid_scores) == 0:
                return pd.Series(dtype=float)

            actual_top_n = min(top_n, len(valid_scores)) if top_n is not None else len(valid_scores)

            if actual_top_n == 0:
                return pd.Series(dtype=float)

            if sort_ascending:
                selected_tickers = valid_scores.nsmallest(actual_top_n).index.tolist()
            else:
                selected_tickers = valid_scores.nlargest(actual_top_n).index.tolist()

            weights = pd.Series(0.0, index=scores.index)
        else:
            # Cas construct_conditional_portfolio (liste de tickers déjà sélectionnés)
            selected_tickers = scores_or_tickers
            weights = pd.Series(0.0, index=selected_tickers)

        lookback_start = current_date - pd.DateOffset(months=lookback_months)

        # Filtrer les données de prix pour la période de lookback
        price_subset = price_data[
            (price_data.index >= lookback_start) &
            (price_data.index <= current_date)
            ]

        if len(price_subset) < 2:
            # Pas assez de données, revenir à equal weight
            weights[selected_tickers] = 1.0 / len(selected_tickers)
            return weights

        # Filtrer pour les tickers sélectionnés et supprimer les colonnes avec trop de NaN
        price_subset = price_subset[selected_tickers].dropna(axis=1, thresh=len(price_subset) // 2)
        available_tickers = price_subset.columns.tolist()

        if len(available_tickers) < 2:
            # Pas assez de données
            weights[selected_tickers] = 1.0 / len(selected_tickers)
            return weights

        # Calculer les rendements mensuels
        returns = price_subset.pct_change(fill_method=None).dropna()

        if len(returns) < 2:
            weights[selected_tickers] = 1.0 / len(selected_tickers)
            return weights

        # Calculer la matrice de covariance annualisée
        cov_matrix = returns.cov() * 12

        # Vérifier que la matrice est définie positive
        eigenvals = np.linalg.eigvals(cov_matrix.values)
        if np.any(eigenvals <= 1e-8):
            # Matrice singulière, ajouter une petite régularisation
            cov_matrix += np.eye(len(cov_matrix)) * 1e-6

        n_assets = len(available_tickers)

        # Fonction objectif : variance du portefeuille
        def portfolio_variance(w):
            return np.dot(w, np.dot(cov_matrix.values, w))

        # Contraintes : somme des poids = 1
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}

        # Bornes : poids entre 0 et 1
        bounds = tuple((0, 1) for _ in range(n_assets))

        # Point de départ : poids égaux
        initial_guess = np.array([1.0 / n_assets] * n_assets)

        # Optimisation
        try:
            result = minimize(
                portfolio_variance,
                initial_guess,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000, 'ftol': 1e-9}
            )

            if result.success:
                # Assigner les poids optimisés
                optimal_weights = result.x
                for i, ticker in enumerate(available_tickers):
                    weights[ticker] = optimal_weights[i]
            else:
                # Optimisation échouée, revenir à equal weight
                weights[available_tickers] = 1.0 / len(available_tickers)

        except Exception:
            # En cas d'erreur, revenir à equal weight
            weights[available_tickers] = 1.0 / len(available_tickers)

        return weights
