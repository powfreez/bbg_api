import os
from datetime import datetime
import pandas as pd


class PortExporterExcel:
    """
    Classe pour exporter les portefeuilles au format Excel compatible avec Bloomberg.
    """

    def __init__(self, output_directory="output"):
        """
        Initialise l'exportateur de fichiers PORT au format Excel.

        Args:
            output_directory: Répertoire de sortie pour les fichiers
        """
        self.output_directory = output_directory

        # Créer le répertoire s'il n'existe pas
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

    def export_portfolio_to_excel(self, weights_df, strategy_type, optimization_method):
        """
        Exporte un portefeuille au format Excel compatible avec Bloomberg.

        Args:
            weights_df: DataFrame avec les poids du portefeuille (index = dates, colonnes = tickers)
            strategy_type: Type de stratégie (VALUE, MOMENTUM, etc.)
            optimization_method: Méthode d'optimisation (SHARPE, MINVVAR, etc.)

        Returns:
            str: Chemin du fichier Excel généré
        """
        # Créer un DataFrame pour stocker les données au format Bloomberg
        output_df = pd.DataFrame(columns=["PORTFOLIO NAME", "SECURITY_ID", "Weight", "Date"])

        # Compteur pour les lignes
        i_row = 0

        # Pour chaque date dans le DataFrame des poids
        for date in weights_df.index:
            # Récupérer les poids pour cette date
            weights = weights_df.loc[date]

            # Pour chaque ticker avec un poids non nul
            for ticker, weight in weights.items():
                if weight > 0:
                    # Créer une entrée pour ce ticker à cette date
                    row = {
                        'PORTFOLIO NAME': f"Factor {strategy_type}",
                        'SECURITY_ID': ticker,
                        'Weight': weight,
                        'Date': date
                    }

                    # Ajouter la ligne au DataFrame
                    output_df.loc[i_row] = row.values()
                    i_row += 1

        # Générer le nom du fichier
        file_name = f"PORT_Factor {strategy_type}.xlsx"
        file_path = os.path.join(self.output_directory, file_name)

        # Sauvegarder le DataFrame au format Excel
        output_df.to_excel(file_path, index=False)

        return file_path