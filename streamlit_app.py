import streamlit as st
import yfinance as yf
import pandas as pd
import re
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Global variables
data_dic = {}
current_values = []

def get_stock_data(stock_symbol):
    global data_dic, current_values
    
    instrument = yf.Ticker(stock_symbol)
    array_data = instrument.history(period="max")

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

    current_values = [{
        'date': array_data.iloc[count].name,
        'close': array_data.iloc[count]['Close'],
        'percentage_difference': ((array_data.iloc[count]['Close'] - array_data.iloc[count+1]['Close']) / 
                                  array_data.iloc[count+1]['Close']) * 100
    } for count in range(8)]

    return index_dict, current_values

def print_difference_data(arg_array, index, matched_length, forward_length):
    matched = [{
        'date': arg_array.iloc[count].name,
        'close': arg_array.iloc[count]['Close'],
        'percentage_difference': ((arg_array.iloc[count]['Close'] - arg_array.iloc[count+1]['Close']) / 
                                  arg_array.iloc[count+1]['Close']) * 100
    } for count in range(index, index + matched_length)]

    indices = [{
        'date': arg_array.iloc[count].name,
        'close': arg_array.iloc[count]['Close'],
        'percentage_difference': ((arg_array.iloc[count-1]['Close'] - arg_array.iloc[count]['Close']) / 
                                  arg_array.iloc[count]['Close']) * 100
    } for count in range(index, index - forward_length, -1)]

    future_average = sum(index['percentage_difference'] for index in indices) / len(indices)
    return indices, matched, future_average

def get_cell_color(value):
    if value < -2:
        return "#800000"
    elif value < -1:
        return "#FF0000"
    elif value < -0.5:
        return "#FFA07A"
    elif value < 0:
        return "#FF4500"
    elif value == 0:
        return "white"
    elif value < 0.5:
        return "#90EE90"
    elif value < 1:
        return "#006400"
    elif value < 2:
        return "#008000"
    else:
        return "#006400"

def main():
    st.title("Stock Analysis App")

    stock_options = {
        "ASX": "^AXJO",
        "NDQ": "^IXIC",
        "BTC": "BTC-USD"
    }

    selected_stock = st.selectbox("Select a stock", list(stock_options.keys()))

    if st.button("Analyze"):
        data_dic, current_values = get_stock_data(stock_options[selected_stock])

        # Display current values table
        st.subheader("Current Stock Values")
        current_df = pd.DataFrame(current_values[::-1])
        current_df['color'] = current_df['percentage_difference'].apply(get_cell_color)
        st.dataframe(current_df.style.apply(lambda x: ['background-color: ' + x['color']] * len(x), axis=1))

        # Display matched entries table
        st.subheader("Pattern Matches and Projections")
        matched_data = []
        for find, data in data_dic.items():
            pattern, indices, matched, future_average = data
            row = {
                'Date': indices[0]['date'],
                'Pattern': pattern,
                'Future Avg': future_average
            }
            for i, index in enumerate(reversed(matched + indices[:5])):
                row[f'Day {i+1}'] = index['percentage_difference']
            matched_data.append(row)
        
        matched_df = pd.DataFrame(matched_data)
        st.dataframe(matched_df.style.background_gradient(cmap='RdYlGn', subset=[col for col in matched_df.columns if col.startswith('Day')]))

        # Create Plotly chart
        st.subheader("Stock Prices and Future Projections")
        dates = [data['date'] for data in current_values]
        current_prices = [data['close'] for data in current_values]
        current_trace = go.Scatter(x=dates, y=current_prices, mode='lines+markers', name='Current Stock Prices', marker=dict(color='blue'))

        future_traces = []
        colors = ['green', 'red', 'purple', 'orange', 'brown']
        last_close = current_values[-1]['close']
        last_date = current_values[-1]['date']

        for i, (_, data) in enumerate(list(data_dic.items())[:5]):
            pattern, indices, _, _ = data
            future_returns = [index['percentage_difference'] / 100 for index in indices[:10]]
            future_prices = [last_close]
            for j in range(10):
                future_prices.append(future_prices[-1] * (1 + future_returns[j]))
            future_dates = [last_date + timedelta(days=j+1+8) for j in range(10)]
            future_trace = go.Scatter(x=future_dates, y=future_prices[1:], mode='lines', name=f'Future Return {i+1} ({pattern})', marker=dict(color=colors[i]))
            future_traces.append(future_trace)

        fig = go.Figure(data=[current_trace] + future_traces)
        fig.update_layout(title='Stock Prices and Future Projections', xaxis_title='Date', yaxis_title='Price')
        st.plotly_chart(fig)

if __name__ == "__main__":
    main()