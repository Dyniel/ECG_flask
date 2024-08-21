from flask import Flask, request, render_template, jsonify
import pandas as pd
import datetime
import os
import neurokit2 as nk
from scipy.signal import find_peaks

app = Flask(__name__)

# Function to parse ECG data from a file and return min and max times
def get_time_range(file_path):
    ecg_data = []
    with open(file_path, 'r', encoding='ISO-8859-1') as f:
        for line in f:
            try:
                timestamp, value = line.strip().split('; ')
                datetime_object = datetime.datetime.strptime(timestamp, '%d.%m.%Y %H:%M:%S,%f')
                ecg_data.append(datetime_object)
            except Exception as e:
                continue

    df = pd.DataFrame(ecg_data, columns=['Timestamp'])
    min_time = df['Timestamp'].min().strftime('%H:%M:%S')
    max_time = df['Timestamp'].max().strftime('%H:%M:%S')

    return min_time, max_time

# Function to detect only the highest peaks (R-peaks) in each cycle
def detect_r_peaks(ecg_signal, distance=150, height=None):
    peaks, _ = find_peaks(ecg_signal, distance=distance, height=height)
    r_peaks = [peak for peak in peaks if ecg_signal[peak] > 0]
    return r_peaks

# Function to parse ECG data from a file and extract R-peaks
def parse_ecg_file(file_path, start_time_str=None, end_time_str=None):
    ecg_data = []
    with open(file_path, 'r', encoding='ISO-8859-1') as f:
        for line in f:
            try:
                timestamp, value = line.strip().split('; ')
                datetime_object = datetime.datetime.strptime(timestamp, '%d.%m.%Y %H:%M:%S,%f')
                ecg_data.append({'Timestamp': datetime_object, 'Value': int(value)})
            except Exception as e:
                continue

    df = pd.DataFrame(ecg_data)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df['Value'] = pd.to_numeric(df['Value'])

    # Apply time filtering if start_time and end_time are provided
    if start_time_str:
        start_time = datetime.datetime.strptime(start_time_str, '%H:%M:%S').time()
        df = df[df['Timestamp'].dt.time >= start_time]
    if end_time_str:
        end_time = datetime.datetime.strptime(end_time_str, '%H:%M:%S').time()
        df = df[df['Timestamp'].dt.time <= end_time]

    ecg_signal = df['Value'].values

    # Detect only the highest peaks (R-peaks)
    r_peaks = detect_r_peaks(ecg_signal, height=1000)  # Adjust the height parameter as needed

    peak_data = df.iloc[r_peaks].copy()

    df['Timestamp'] = df['Timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    peak_data['Timestamp'] = peak_data['Timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    return df.to_dict(orient='records'), peak_data.to_dict(orient='records')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})
    if file:
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)

        min_time, max_time = get_time_range(file_path)

        return jsonify({'status': 'success', 'min_time': min_time, 'max_time': max_time, 'file_path': file_path})

@app.route('/visualize', methods=['POST'])
def visualize():
    file_path = request.form.get('file_path')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    if not file_path:
        return jsonify({'status': 'error', 'message': 'File path missing'})

    ecg_data, peak_data = parse_ecg_file(file_path, start_time_str=start_time, end_time_str=end_time)

    # Ensure correct structure and log it for debugging
    response = {
        'status': 'success',
        'data': ecg_data,
        'peaks': peak_data
    }

    print("Response being sent to client:", response)  # Debugging output

    return jsonify(response)

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)
