import os

import pandas as pd


class DataLoader:
    def __init__(self, data_folder="data"):
        self.data_folder = data_folder
        self.csv_files = {
            "Market_Cap": "CUR_MKT_CAP.csv",
            "Free_Float": "EQY_FREE_FLOAT_PCT.csv",
            "Shares_Outstanding": "EQY_SH_OUT.csv",
            "PX_LAST": "PX_LAST.csv",
            "Book_Value_Per_Share": "BOOK_VAL_PER_SH.csv",
            "Total_Assets": "BS_TOT_ASSET.csv",
            "Gross_Profit": "GROSS_PROFIT.csv",
            "Operating_Income": "IS_OPER_INC.csv",
            "Return_on_Equity": "RETURN_COM_EQY.csv",
            "Universe_Composition": "compo.csv",
            "EBITDA": "EBITDA.csv",
            "EV_EBITDA_ADJUSTED": "EV_EBITDA_ADJUSTED.csv",
            "EV_EBIT_ADJUSTED": "EV_EBIT_ADJUSTED.csv",
            "DIVIDEND_12_MONTH_YIELD": "DIVIDEND_12_MONTH_YIELD.csv",
        }

        self.lags = {
            "Market_Cap": 0, "Free_Float": 0, "Shares_Outstanding": 0,
            "PX_LAST": 0, "Book_Value_Per_Share": 6,
            "Total_Assets": 6, "Gross_Profit": 6, "Operating_Income": 6,
            "Return_on_Equity": 6, "Universe_Composition": 0,
            "EBITDA": 6,
            "EBIT": 6,
            "EV_EBITDA_ADJUSTED": 6,
            "EV_EBIT_ADJUSTED": 6,
            "DIVIDEND_12_MONTH_YIELD": 0
        }
        self.dataframes = {}

    def load_data(self):
        for metric, file in self.csv_files.items():
            file_path = os.path.join(self.data_folder, file)
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            df.index = pd.to_datetime(df.index).to_period('M').to_timestamp('M')
            df = df.sort_index()
            df.columns = df.columns.str.strip()

            if df.index.duplicated().any():
                df = df[~df.index.duplicated(keep='first')]

            if self.lags[metric] > 0:
                df = df.shift(self.lags[metric])

            self.dataframes[metric] = df

        if "Market_Cap" in self.dataframes and "Free_Float" in self.dataframes:
            market_cap = self.dataframes["Market_Cap"]
            free_float_pct = self.dataframes["Free_Float"].copy() / 100
            free_float_market_cap = market_cap.multiply(free_float_pct)
            self.dataframes["Free_Float_Market_Cap"] = free_float_market_cap

        return self.dataframes
