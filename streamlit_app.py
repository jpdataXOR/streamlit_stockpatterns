import streamlit as st
import yfinance as yf
import pandas as pd
import re
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Global variables
data_dic = {}
current_values = []


def get_stock_data(stock_symbol, interval):
    global data_dic, current_values

    instrument = yf.Ticker(stock_symbol)
    array_data = instrument.history(
        period="1y", interval=interval, auto_adjust=False)  # Use interval here

    result_string = ''.join(['U' if array_data.iloc[i]['Close'] >= array_data.iloc[i-1]['Close'] else 'D'
                             for i in range(1, len(array_data))])

    array_data = array_data.iloc[::-1]
    result_string = result_string[::-1]

    index_dict = {}
    for iteration in range(8, 5, -1):
        string_to_match = result_string[0:iteration]
        indices = [index.start()
                   for index in re.finditer(string_to_match, result_string)]
        if len(indices) > 2:
            for matched_index in indices[1:]:
                if matched_index not in index_dict:
                    index_dict[matched_index] = len(string_to_match)

    for key, value in index_dict.items():
        indices, matched, future_average = print_difference_data(
            array_data, key, value, 13)
        index_dict[key] = (value, indices, matched, future_average)

    # Get last 8 values for current values and past prices
    current_values = [{
        'date': array_data.iloc[count].name.strftime('%d-%b-%Y %H:%M' if interval == "1h" else '%d-%b-%Y'),
        'close': array_data.iloc[count]['Close'],
        'percentage_difference': ((array_data.iloc[count]['Close'] - array_data.iloc[count+1]['Close']) /
                                  array_data.iloc[count+1]['Close']) * 100
    } for count in range(8)]

    # Get past prices
    past_prices = [{
        'date': array_data.iloc[count].name.strftime('%d-%b-%Y %H:%M' if interval == "1h" else '%d-%b-%Y'),
        'close': array_data.iloc[count]['Close'],
        'percentage_difference': ((array_data.iloc[count]['Close'] - array_data.iloc[count+1]['Close']) /
                                  array_data.iloc[count+1]['Close']) * 100
    } for count in range(8, 16)]

    return index_dict, current_values, past_prices


def print_difference_data(arg_array, index, matched_length, forward_length):
    matched = [{
        'date': arg_array.iloc[count].name.strftime('%d-%b-%Y %H:%M'),
        'close': arg_array.iloc[count]['Close'],
        'percentage_difference': ((arg_array.iloc[count]['Close'] - arg_array.iloc[count+1]['Close']) /
                                  arg_array.iloc[count+1]['Close']) * 100
    } for count in range(index, index + matched_length)]

    indices = [{
        'date': arg_array.iloc[count].name.strftime('%d-%b-%Y %H:%M'),
        'close': arg_array.iloc[count]['Close'],
        'percentage_difference': ((arg_array.iloc[count-1]['Close'] - arg_array.iloc[count]['Close']) /
                                  arg_array.iloc[count]['Close']) * 100
    } for count in range(index, index - forward_length, -1)]

    future_average = sum(index['percentage_difference']
                         for index in indices) / len(indices)
    return indices, matched, future_average


def main():
    st.title("Stock Analysis App")

    stock_options = {
        "ASX": "^AXJO",
        "NDQ": "^IXIC",
        "BTC": "BTC-USD",
        "NIKKEI": "^N225",
        "HANG_SENG": "^HSI",
        "FTSE_100": "^FTSE",
        "DAX": "^GDAXI",
        "CAC_40": "^FCHI",
        "S&P_500": "^GSPC",
        "TSX": "^GSPTSE",
        "NSE_INDIA": "^NSEI",
        "IBEX_35": "^IBEX",
        "AEX": "^AEX",
        "MIB": "^FTSEMIB",
        "BOVESPA": "^BVSP",
        "IPC": "^MEXBOL",
        "VIX": "^VIX",
        "USDCHF": "USDCHF=X",
        "USDJPY": "USDJPY=X",
        "AUDUSD": "AUDUSD=X",
        "EURUSD": "EURUSD=X"

    }

    selected_stock = st.selectbox("Select a stock", list(stock_options.keys()))
    selected_interval = st.selectbox("Select an interval", ["1d", "1h"])

    if st.button("Analyze"):
        data_dic, current_values, past_prices = get_stock_data(
            stock_options[selected_stock], selected_interval)

        # Separate columns for current and future projections
        col1, col2 = st.columns(2)

        # Display current values in the first column
        with col1:
            st.subheader("Current Stock Prices")

            # Create Plotly chart for current prices
            dates = [datetime.strptime(data['date'], '%d-%b-%Y %H:%M' if selected_interval == "1h" else '%d-%b-%Y')
                     for data in current_values]
            current_prices = [data['close'] for data in current_values]
            current_trace = go.Scatter(x=dates, y=current_prices, mode='lines+markers',
                                       name='Current Stock Prices', marker=dict(color='blue'))

            fig_current = go.Figure(data=[current_trace])
            fig_current.update_layout(
                title="Current Stock Prices",
                xaxis_title="Date & Time" if selected_interval == "1h" else "Date",
                yaxis_title="Price",
                showlegend=False
            )
            st.plotly_chart(fig_current)

            # Display current prices table below the chart
            current_df = pd.DataFrame(current_values)
            st.dataframe(current_df)

        # Display future values in the second column
        with col2:
            st.subheader("Future Stock Projections")

            # Plot future projections
            future_traces = []
            colors = ['green', 'red', 'purple', 'orange', 'brown']
            last_close = current_prices[-1]
            last_date = dates[-1]

            for i, (_, data) in enumerate(list(data_dic.items())[:5]):
                pattern, indices, _, _ = data
                future_returns = [
                    index['percentage_difference'] / 100 for index in indices[:10]]
                future_prices = [last_close]
                for j in range(10):
                    future_prices.append(
                        future_prices[-1] * (1 + future_returns[j]))

                future_dates = [last_date + timedelta(hours=j+1) if selected_interval ==
                                "1h" else last_date + timedelta(days=j+1) for j in range(10)]

                future_trace = go.Scatter(
                    x=future_dates, y=future_prices[1:], mode='lines', name=f'Future Return {i+1} ({pattern})', marker=dict(color=colors[i]))
                future_traces.append(future_trace)

            fig_future = go.Figure(data=future_traces)
            fig_future.update_layout(
                title="Future Projections",
                xaxis_title="Date & Time" if selected_interval == "1h" else "Date",
                yaxis_title="Price",
                showlegend=False
            )
            st.plotly_chart(fig_future)

            # Display future projections table below the chart
            matched_data = []
            for i, (_, data) in enumerate(list(data_dic.items())[:5]):
                pattern, indices, _, _ = data
                for index in indices[:10]:
                    matched_data.append({
                        'date': index['date'],
                        'percentage_difference': index['percentage_difference']
                    })

            future_df = pd.DataFrame(matched_data)
            st.dataframe(future_df)


if __name__ == "__main__":
    main()
