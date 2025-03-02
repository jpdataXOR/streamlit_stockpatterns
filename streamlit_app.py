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

    # Set appropriate period based on interval
    period = "1y" if interval == "1h" else "5y" if interval == "1d" else "max"
    
    instrument = yf.Ticker(stock_symbol)
    array_data = instrument.history(period=period, interval=interval, auto_adjust=False)

    result_string = ''.join(['U' if array_data.iloc[i]['Close'] >= array_data.iloc[i-1]['Close'] else 'D'
                             for i in range(1, len(array_data))])

    array_data = array_data.iloc[::-1]
    result_string = result_string[::-1]

    index_dict = {}
    for iteration in range(8, 5, -1):
        string_to_match = result_string[0:iteration]
        indices = [index.start() for index in re.finditer(string_to_match, result_string)]
        if len(indices) > 2:
            for matched_index in indices[1:]:
                if matched_index not in index_dict:
                    index_dict[matched_index] = len(string_to_match)

    for key, value in index_dict.items():
        indices, matched, future_average = print_difference_data(array_data, key, value, 13)
        index_dict[key] = (value, indices, matched, future_average)

    # Format string based on interval
    date_format = '%d-%b-%Y %H:%M' if interval == "1h" else '%d-%b-%Y'
    
    # Get last 8 values for current values and past prices
    current_values = [{
        'date': array_data.iloc[count].name.strftime(date_format),
        'close': array_data.iloc[count]['Close'],
        'percentage_difference': ((array_data.iloc[count]['Close'] - array_data.iloc[count+1]['Close']) /
                                  array_data.iloc[count+1]['Close']) * 100
    } for count in range(8)]

    # Get past prices
    past_prices = [{
        'date': array_data.iloc[count].name.strftime(date_format),
        'close': array_data.iloc[count]['Close'],
        'percentage_difference': ((array_data.iloc[count]['Close'] - array_data.iloc[count+1]['Close']) /
                                  array_data.iloc[count+1]['Close']) * 100
    } for count in range(8, 16)]

    return index_dict, current_values, past_prices

# The rest of the code remains unchanged


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

    # Mapping of meaningful names to stock symbols
    stock_options = {
        "Australian Stock Exchange": "^AXJO",
        "NASDAQ 100": "^NDX",
        "Bitcoin": "BTC-USD",
        "Nikkei 225 - Japan": "^N225",
        "Hang Seng - Hong Kong": "^HSI",
        "FTSE 100 - UK": "^FTSE",
        "DAX - Germany": "^GDAXI",
        "CAC 40 - France": "^FCHI",
        "S&P 500 - US": "^GSPC",
        "Toronto Stock Exchange": "^GSPTSE",
        "NIFTY 50 - India": "^NSEI",
        "IBEX 35 - Spain": "^IBEX",
        "AEX - Netherlands": "^AEX",
        "FTSE MIB - Italy": "^FTSEMIB",
        "Bovespa - Brazil": "^BVSP",
        "IPC - Mexico": "^MEXBOL",
        "Volatility Index (VIX)": "^VIX",
        "USD/CHF": "USDCHF=X",
        "USD/JPY": "USDJPY=X",
        "AUD/USD": "AUDUSD=X",
        "EUR/USD": "EURUSD=X",
        "iShares Semiconductor ETF": "SOXX"  # SOXX ETF with clean name
    }

    # Create tabs for predefined stocks and custom stock search
    tab1, tab2 = st.tabs(["Predefined Stocks", "Custom Stock Search"])
    
    # Initialize the selected_symbol variable
    selected_symbol = None
    selected_method = None
    
    with tab1:
        selected_stock = st.selectbox("Select a stock or index", list(stock_options.keys()))
        if selected_stock:
            selected_symbol = stock_options[selected_stock]
            selected_method = "dropdown"
    
    with tab2:
        custom_stock = st.text_input("Enter stock ticker symbol (e.g., AAPL, MSFT, GOOGL)", "")
        if custom_stock:
            selected_symbol = custom_stock
            selected_method = "custom"
    
    # Add 1w interval to the dropdown
    selected_interval = st.selectbox("Select an interval", ["1d", "1h", "1wk"])
    
    # Convert "1wk" to "1w" for yfinance compatibility
    if selected_interval == "1wk":
        selected_interval = "1wk"

    if st.button("Analyze"):
        # Use selected symbol from either dropdown or custom entry
        analysis_symbol = selected_symbol
        
        # Default to the dropdown selection if no custom ticker is entered
        if selected_method != "custom" and selected_stock:
            analysis_symbol = stock_options[selected_stock]
            
        if not analysis_symbol:
            st.error("Please select a stock or enter a custom ticker symbol")
            return
            
        try:
            data_dic, current_values, past_prices = get_stock_data(
                analysis_symbol, selected_interval)

            # Show the ticker being analyzed
            st.info(f"Analyzing: {selected_stock if selected_method != 'custom' else analysis_symbol}")

            # Separate columns for current and future projections
            col1, col2 = st.columns(2)

            # Display current values in the first column
            with col1:
                st.subheader("Current Stock Prices")

                # Format based on interval
                date_format = '%d-%b-%Y %H:%M' if selected_interval == "1h" else '%d-%b-%Y'
                
                # Create Plotly chart for current prices
                dates = [datetime.strptime(data['date'], date_format)
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

                    # Set time interval for future dates based on selected interval
                    if selected_interval == "1h":
                        future_dates = [last_date + timedelta(hours=j+1) for j in range(10)]
                    elif selected_interval == "1w":
                        future_dates = [last_date + timedelta(weeks=j+1) for j in range(10)]
                    else:  # 1d
                        future_dates = [last_date + timedelta(days=j+1) for j in range(10)]

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
        except Exception as e:
            st.error(f"Error analyzing stock: {e}")
            st.info("This could be due to an invalid ticker symbol or no data available for the selected interval.")


if __name__ == "__main__":
    main()