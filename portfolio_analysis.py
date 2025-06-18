import numpy as np
import pandas as pd
import tempfile
import os


class PortfolioAnalysis:
    def __init__(self, returns, risk_free_rate=0.0, strategy_params=None):
        """
        Initialise l'analyse du portefeuille.

        Args:
            returns: Série Pandas de rendements
            risk_free_rate: Taux sans risque annualisé (défaut: 0.0)
            strategy_params: Dictionnaire contenant les paramètres de la stratégie
        """
        self.returns = returns
        self.risk_free_rate = risk_free_rate
        self.strategy_params = strategy_params or {}

    def calculate_metrics(self, annualization_factor=12):
        """
        Calcule les métriques de performance du portefeuille.

        Args:
            annualization_factor: Facteur d'annualisation (12 pour mensuel)

        Returns:
            dict: Dictionnaire contenant toutes les métriques calculées
        """
        metrics = {}

        # Rendement cumulatif
        cumulative_returns = (1 + self.returns).cumprod() - 1
        metrics['cumulative_return'] = cumulative_returns.iloc[-1]

        # Rendement annualisé
        n_periods = len(self.returns)
        metrics['annualized_return'] = (1 + metrics['cumulative_return']) ** (annualization_factor / n_periods) - 1

        # Volatilité
        metrics['volatility'] = self.returns.std() * np.sqrt(annualization_factor)

        # Ratio de Sharpe
        excess_return = metrics['annualized_return'] - self.risk_free_rate
        metrics['sharpe_ratio'] = excess_return / metrics['volatility'] if metrics['volatility'] != 0 else 0

        # Maximum Drawdown
        wealth_index = (1 + self.returns).cumprod()
        previous_peaks = wealth_index.cummax()
        drawdowns = (wealth_index - previous_peaks) / previous_peaks
        metrics['max_drawdown'] = drawdowns.min()

        return metrics

    def _generate_params_table_html(self):
        """
        Génère un tableau HTML avec les paramètres de la stratégie.

        Returns:
            str: Code HTML du tableau des paramètres
        """
        if not self.strategy_params:
            return ""

        html = """
        <div style="margin: 20px 0;">
            <h3>Strategy Parameters</h3>
            <table style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Parameter</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Value</th>
                    </tr>
                </thead>
                <tbody>
        """

        for param, value in self.strategy_params.items():
            html += f"""
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px;">{param}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{value}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        return html

    def generate_quantstats_report(self, serie, benchmark=None, output_file=None, title="Portfolio Analysis"):
        from quantstats import reports
        """
        Génère un rapport complet avec QuantStats.

        Args:
            benchmark: Série Pandas des rendements du benchmark (optionnel)
            output_file: Chemin du fichier HTML de sortie (optionnel)
            title: Titre du rapport

        Returns:
            str: Chemin du fichier HTML généré
        """

        try:
            benchmark = pd.read_excel(r"data/sp500_historical.xlsx", index_col=0).pct_change().dropna()
            benchmark.index = pd.to_datetime(benchmark.index)
        except:
            benchmark = None
        if not isinstance(serie.index, pd.DatetimeIndex):
            if isinstance(serie.index, pd.RangeIndex):
                start_date = pd.Timestamp.now() - pd.DateOffset(months=len(serie))
                serie.index = pd.date_range(start=start_date, periods=len(serie), freq='M')
            else:
                serie.index = pd.to_datetime(serie.index)

        # Génération du fichier de sortie
        if output_file is None:
            # Créer un fichier temporaire
            temp_dir = "output/"
            output_file = os.path.join(temp_dir,
                                       f"portfolio_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html")

        # Génération du rapport HTML complet
        if benchmark is not None:
            # Rapport avec benchmark
            benchmark_series = benchmark.copy()
            if not isinstance(benchmark_series.index, pd.DatetimeIndex):
                benchmark_series.index = serie.index

            reports.html(
                returns=serie,
                benchmark=benchmark_series,
                rf=self.risk_free_rate,
                output=output_file,
                title=title,
                mode="full"
            )
        else:
            # Rapport sans benchmark
            reports.html(
                returns=serie,
                rf=self.risk_free_rate,
                output=output_file,
                mode="full",
                title=title,
            )

        # Ajouter le tableau des paramètres au rapport HTML
        if self.strategy_params:
            self._inject_params_table(output_file)

        print(f"Rapport QuantStats généré: {output_file}")
        return output_file

    def _inject_params_table(self, html_file_path):
        """
        Injecte le tableau des paramètres dans le fichier HTML existant.

        Args:
            html_file_path: Chemin vers le fichier HTML
        """
        try:
            # Lire le fichier HTML
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Générer le tableau des paramètres
            params_table = self._generate_params_table_html()

            # Chercher où injecter le tableau (après le titre principal)
            injection_point = html_content.find('<h1>')
            if injection_point == -1:
                injection_point = html_content.find('<body>') + len('<body>')
            else:
                # Trouver la fin du titre
                end_title = html_content.find('</h1>', injection_point) + len('</h1>')
                injection_point = end_title

            # Injecter le tableau
            modified_html = (
                    html_content[:injection_point] +
                    params_table +
                    html_content[injection_point:]
            )

            # Écrire le fichier modifié
            with open(html_file_path, 'w', encoding='utf-8') as f:
                f.write(modified_html)

        except Exception as e:
            print(f"Erreur lors de l'injection du tableau des paramètres: {e}")