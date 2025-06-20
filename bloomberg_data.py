import datetime as dt

import blpapi
import pandas as pd

DATE = blpapi.Name("date")
ERROR_INFO = blpapi.Name("errorInfo")
EVENT_TIME = blpapi.Name("EVENT_TIME")
FIELD_DATA = blpapi.Name("fieldData")
FIELD_EXCEPTIONS = blpapi.Name("fieldExceptions")
FIELD_ID = blpapi.Name("fieldId")
SECURITY = blpapi.Name("security")
SECURITY_DATA = blpapi.Name("securityData")


class BLP:
    def __init__(self):
        self.session = blpapi.Session()

        if not self.session.start():
            print("Failed to start session.")
            return

        if not self.session.openService("//blp/refdata"):
            print("Failed to open //blp/refdata")
            return

        self.session.openService('//BLP/refdata')
        self.refDataSvc = self.session.getService('//BLP/refdata')

        print('Session open')

    def bdh(self, strSecurity, strFields, startdate, enddate, per='MONTHLY', perAdj='CALENDAR',
            days='NON_TRADING_WEEKDAYS', fill='PREVIOUS_VALUE', curr=None):
        request = self.refDataSvc.createRequest('HistoricalDataRequest')

        if type(strFields) == str:
            strFields = [strFields]

        if type(strSecurity) == str:
            strSecurity = [strSecurity]

        for strF in strFields:
            request.append('fields', strF)

        for strS in strSecurity:
            request.append('securities', strS)

        request.set('startDate', startdate.strftime('%Y%m%d'))
        request.set('endDate', enddate.strftime('%Y%m%d'))
        request.set('periodicitySelection', per)
        request.set('nonTradingDayFillOption', days)
        if curr is not None:
            request.set('currency', curr)
        request.set('periodicityAdjustment', perAdj)
        request.set('nonTradingDayFillMethod', fill)
        requestID = self.session.sendRequest(request)
        print("Sending BDH request")

        list_msg = []

        while True:
            event = self.session.nextEvent()
            if (event.eventType() != blpapi.event.Event.RESPONSE) and (
                    event.eventType() != blpapi.event.Event.PARTIAL_RESPONSE):
                continue

            msg = blpapi.event.MessageIterator(event).__next__()
            list_msg.append(msg)

            if event.eventType() == blpapi.event.Event.RESPONSE:
                break

        dict_Fields_Dataframe = {}
        for fieldd in strFields:
            globals()['dict_' + fieldd] = {}

        for msg in list_msg:

            secur_data = msg.getElement(SECURITY_DATA)
            securityName = str(secur_data.getElement(SECURITY).getValue())
            field_data = secur_data.getElement(FIELD_DATA)

            for fieldd in strFields:
                globals()['dict_' + fieldd][securityName] = {}

            int_nbDate = field_data.numValues()

            for i in range(0, int_nbDate):
                fields = field_data.getValue(i)
                nb_fields = fields.numElements()
                dt_date = fields.getElement(0).getValue()

                for j in range(1, nb_fields):
                    element = fields.getElement(j)
                    field_name = str(element.name())
                    field_value = element.getValue()

                    globals()['dict_' + field_name][securityName][dt_date] = field_value

        for field in strFields:
            dict_Fields_Dataframe[field] = pd.DataFrame.from_dict(globals()['dict_' + field], orient='columns')
        return dict_Fields_Dataframe

    def bds(self, strSecurity, strFields, strOverrideField='', strOverrideValue=''):
        request = self.refDataSvc.createRequest('ReferenceDataRequest')

        if type(strFields) == str:
            strFields = [strFields]

        if type(strSecurity) == str:
            strSecurity = [strSecurity]

        for strD in strFields:
            request.append('fields', strD)

        for strS in strSecurity:
            request.append('securities', strS)

        if strOverrideField != '':
            o = request.getElement('overrides').appendElement()
            o.setElement('fieldId', strOverrideField)
            o.setElement('value', strOverrideValue)

        requestID = self.session.sendRequest(request)
        print("Sending BDS request")

        list_msg = []
        dict_Fields_Dataframe = {}
        for fieldd in strFields:
            globals()['dict_' + fieldd] = {}

        while True:
            event = self.session.nextEvent()
            if (event.eventType() != blpapi.event.Event.RESPONSE) and (
                    event.eventType() != blpapi.event.Event.PARTIAL_RESPONSE):
                continue

            msg = blpapi.event.MessageIterator(event).__next__()
            list_msg.append(msg)
            if event.eventType() == blpapi.event.Event.RESPONSE:
                break

        for msg in list_msg:
            secur_data = msg.getElement(SECURITY_DATA)
            nb_securities = secur_data.numValues()

            for i in range(0, nb_securities):
                security_data = secur_data.getValue(i)
                security_name = security_data.getElement(SECURITY).getValue()
                field_data = security_data.getElement(FIELD_DATA)
                nb_values = field_data.numElements()

                for fieldd in strFields:
                    globals()['dict_' + str(fieldd)][security_name] = {}

                for j in range(0, nb_values):
                    element = field_data.getElement(j)
                    field_name = str(element.name())
                    nb_element = element.numValues()

                    for i_ticker in range(nb_element):
                        ticker = element.getValue(i_ticker)
                        ticker_name = ticker.getElement(0).getValue()
                        field_value = ticker.getElement(1).getValue()
                        globals()['dict_' + str(field_name)][security_name][ticker_name] = field_value

            for field in strFields:
                if len(strFields) == 1 and nb_securities == 1:
                    dict_Fields_Dataframe = pd.DataFrame([globals()['dict_' + field]], index=[dt.datetime.now()]).iloc[
                        0, 0]
                if len(strFields) > 1 and nb_securities == 1:
                    dict_Fields_Dataframe[field] = pd.DataFrame.from_dict(globals()['dict_' + field])
                if len(strFields) == 1 and nb_securities > 1:
                    dict_Fields_Dataframe = pd.DataFrame([globals()['dict_' + field]], index=[dt.datetime.now()])
                if len(strFields) > 1 and nb_securities > 1:
                    dict_Fields_Dataframe[field] = pd.DataFrame([globals()['dict_' + field]], index=[dt.datetime.now()])
        return dict_Fields_Dataframe

    def bdp(self, strSecurity, strFields, strOverrideField='', strOverrideValue=''):
        request = self.refDataSvc.createRequest('ReferenceDataRequest')

        if type(strFields) == str:
            strFields = [strFields]

        if type(strSecurity) == str:
            strSecurity = [strSecurity]

        for strD in strFields:
            request.append('fields', strD)

        for strS in strSecurity:
            request.append('securities', strS)

        if strOverrideField != '':
            o = request.getElement('overrides').appendElement()
            o.setElement('fieldId', strOverrideField)
            o.setElement('value', strOverrideValue)
        requestID = self.session.sendRequest(request)
        print("Sending BDP request")

        list_msg = []
        dict_Fields_Dataframe = {}
        for fieldd in strFields:
            globals()['dict_' + fieldd] = {}

        while True:
            event = self.session.nextEvent()
            if (event.eventType() != blpapi.event.Event.RESPONSE) and (
                    event.eventType() != blpapi.event.Event.PARTIAL_RESPONSE):
                continue

            msg = blpapi.event.MessageIterator(event).__next__()
            list_msg.append(msg)
            if event.eventType() == blpapi.event.Event.RESPONSE:
                break

        for msg in list_msg:
            secur_data = msg.getElement(SECURITY_DATA)
            nb_ticker = secur_data.numValues()

            for i in range(0, nb_ticker):
                security_data = secur_data.getValue(i)
                security_name = security_data.getElement(SECURITY).getValue()
                field_data = security_data.getElement(FIELD_DATA)
                nb_values = field_data.numElements()

                for fieldd in strFields:
                    globals()['dict_' + str(fieldd)][security_name] = {}

                for j in range(0, nb_values):
                    element = field_data.getElement(j)
                    field_value = element.getValue()
                    field_name = str(element.name())
                    globals()['dict_' + str(field_name)][security_name] = field_value

        for field in strFields:
            dict_Fields_Dataframe[field] = pd.DataFrame([globals()['dict_' + field]], index=[dt.datetime.now()])

        return dict_Fields_Dataframe if len(strFields) > 1 else dict_Fields_Dataframe[field]

    def get_compo(self, main_index, start_date, end_date):
        lst_monthly_dates = pd.date_range(start=start_date, end=end_date, freq='M')
        dict_tickers = {}

        for date in lst_monthly_dates:
            str_date = date.strftime('%Y%m%d')
            try:
                bds_data = self.bds(
                    strSecurity=main_index,
                    strFields=["INDX_MWEIGHT_HIST"],
                    strOverrideField="END_DATE_OVERRIDE",
                    strOverrideValue=str_date
                )

                if isinstance(bds_data, pd.DataFrame):
                    tickers = list(bds_data.columns)
                else:
                    tickers = list(bds_data.keys())
                tickers = [ticker + " Equity" for ticker in tickers]
                dict_tickers[date] = tickers
            except Exception as e:
                print(f"Erreur lors de la récupération pour {date}: {e}")
                dict_tickers[date] = []

        all_tickers = sorted(set(ticker for tickers in dict_tickers.values() for ticker in tickers))
        df_compo = pd.DataFrame(0, index=lst_monthly_dates, columns=all_tickers)

        for date, tickers in dict_tickers.items():
            df_compo.loc[date, tickers] = 1

        return df_compo

    def closeSession(self):
        print("Session closed")
        self.session.stop()


if __name__ == '__main__':
    blp = BLP()
    get_compo = False
    get_data = True

    startDate = dt.datetime(2007, 1, 1)
    endDate = dt.datetime(2025, 3, 21)
    if get_compo:
        main_indices = ["RIY Index"]

        list_compo = []
        for main_index in main_indices:
            print(f"\nComposition historique pour {main_index} :")
            df_compo = blp.get_compo(main_index, startDate, endDate)
            print(df_compo)
            list_compo.append(df_compo)

        df_concat = pd.concat(list_compo, axis=1)
        df_univers = df_concat.groupby(df_concat.columns, axis=1).max()
        df_univers.to_csv("data/compo.csv")

    if get_data:
        try:
            tickers = pd.read_csv("data/compo.csv", index_col=0).columns.to_list()
            fields = [
                "PX_LAST",
                # "CUR_MKT_CAP",
                # "EQY_FREE_FLOAT_PCT",
                # "EQY_SH_OUT",
                # "MARKET_CAPITALIZATION_TO_BV"
                # "EBIT",
                # "EBIT_EV_YIELD",
                # "EBITDA",
                # "GROSS_PROFIT",
                # "BS_TOT_ASSET",
                # "ESG_SCORE",
                # "EV_EBITDA_ADJUSTED",
                # "EV_EBIT_ADJUSTED",
                # "NORMALIZED_ROE",
                # "BOOK_VAL_PER_SH",
                # "RETURN_COM_EQY",
                # "IS_OPER_INC",
                # "TOT_RETURN_INDEX_GROSS_DVDS",
                # "DIVIDEND_12_MONTH_YIELD",
                # "VOLATILITY_30D",
                # "TOT_DEBT_TO_COM_EQY",
                # "GROSS_MARGIN",
                "EQY_DVD_YLD_12M_NET"
            ]
            # fields = []
            for field in fields:
                print(f'\nRetrieving {field} via BDH...')
                bdh_result = blp.bdh(tickers, field, startDate, endDate)
                df = bdh_result[field]
                df.to_csv(f"data_am/{field}.csv")
                print(f"Exported {field} data")
        except Exception as e:
            print(f"Error retrieving {field} via BDH: {e}")


    blp.closeSession()
