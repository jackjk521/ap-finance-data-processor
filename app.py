from flask import Flask, render_template, request, redirect, send_file
import pandas as pd
from io import BytesIO
import re

app = Flask(__name__)

# Route for the home page
@app.route('/')
def index():
    return render_template('index.html')

# Route for handling single file upload
@app.route('/upload_single_sql', methods=['POST'])
def upload_single_sql():

    if 'file' not in request.files:
        return redirect('/')
    
    file = request.files['file']
    estate_name = request.form['estate_name'].upper()

    if file.filename == '':
        return redirect('/')
    
    # Read and process CSV using Pandas
    if file:
        # Read Excel file to DataFrame
        rawFinanceDF = pd.read_excel(file, engine="openpyxl")
        # tempDF = pd.read_excel(FILE_PATH, na_values=['N/A'], skiprows=4, dtype=str, engine='openpyxl')

        # NaN Value to NOT DATE
        rawFinanceDF.iloc[:, 1] = rawFinanceDF.iloc[:, 1].fillna('NOT DATE')

        # print(rawFinanceDF)
        # print(tempSQLDF.columns.tolist())
        tempDF = rawFinanceDF
        tempDF['CodeName'] = None
        current_string = None

        # Iterate through each row
        for index, row in tempDF.iterrows():
            first_cell = str(row.iloc[1]).strip() # Get the first cell and strip any whitespace
            description_cell = str(row.iloc[5]).strip()

            # print(first_cell)
            # Define the pattern to match the description cell
            description_pattern_1 = re.compile(r'Late Payment Charges For \w+ \d{4}', re.IGNORECASE)
            description_pattern_2 = re.compile(r'Late Payment Charges From \d{2}/\d{2}/\d{4} - \d{2}/\d{2}/\d{4}', re.IGNORECASE)
            description_pattern_3 = re.compile(r'Late Payment Charges For \d{2}/\d{2}/\d{4} - \d{2}/\d{2}/\d{4}', re.IGNORECASE)

            # Check if the first cell is NaN, skip if it is
            if first_cell == "NOT DATE":
                continue  # Skip to the next iteration if the first cell is NaN

            # Convert to datetime, invalid parsing will be NaT
            parsed_date = pd.to_datetime(first_cell, errors='coerce', infer_datetime_format=True)

            if pd.isna(parsed_date):
                # If parsed_date is NaT, it means first_cell is not a date
                # Extract the code part before the first '('
                code_part = first_cell.split('(', 1)[0].strip()
                # Further split to get the part after 'Code  :'
                current_string = code_part.split(':', 1)[-1].strip()
            else:
                # If parsed_date is not NaT, it means first_cell is a date
                tempDF.at[index, 'CodeName'] = current_string
                tempDF.at[index, 'Post Date'] = parsed_date.strftime('%Y-%m-%d')

            # Update 'Late Payment Charges for %'  OR 'LATE PAYMENT CHARGES FOR %' pattern to INTEREST
            if description_pattern_1.match(description_cell) or description_pattern_2.match(description_cell):
                # print(description_pattern.match(description_cell))
                tempDF.at[index, 'Description'] = 'INTEREST'

        tempDF = tempDF[tempDF['CodeName'].notna()]

        # FORMATTING
        formatted_df = pd.DataFrame({
            'estate_name': estate_name,
            'account_code': tempDF['CodeName'], 
            'posted_date': tempDF['Post Date'],
            'ref_num_1': tempDF['Ref 1'],
            'ref_num_2': tempDF['Ref 2'],
            'description': tempDF['Description'],
            'local_dr': tempDF['Local DR'],
            'local_cr': tempDF['Local CR'],
            'local_balance': tempDF['Local Balance'],
            'remarks': ""
        })

        # print(formatted_df)

        # EXPORT FORMATTED DF
        output = BytesIO()  # Create an in-memory buffer
        formatted_df.to_csv(output, index=False)  # Write the DataFrame to the buffer as CSV
        output.seek(0)  # Move the pointer to the start off the buffer

        return send_file(output, mimetype='text/csv', as_attachment=True, download_name='processed_sql_finance_data.csv')
    
@app.route('/upload_single_qns', methods=['POST'])
def upload_single_qns():
    if 'file' not in request.files:
        return redirect('/')
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect('/')
    
    # Read and process CSV using Pandas
    if file:
        # Load the data from the Excel file
        rawFinanceDF = pd.read_excel(file, engine="openpyxl")  # Use header=None if there is no header row
        # print(rawFinanceDF.columns.toList())
        # print(rawFinanceDF.dtypes)

        # Extract the property name from the cell containing "Property"
        property_row = rawFinanceDF[rawFinanceDF.iloc[:, 0].str.contains("Property", na=False)]
        property_name = property_row.iloc[0, 0].split(":")[1].strip() if not property_row.empty else "Unknown"
        # print(property_name)

        # Initialize a temp dataframe for data manipulation
        offset_rawFinanceDF = pd.read_excel(file, skiprows=4, engine="openpyxl")  
        # NaN Value to NOT DATE
        offset_rawFinanceDF.iloc[:, 0] = offset_rawFinanceDF.iloc[:, 0].fillna('NOT DATE')

        tempDF = offset_rawFinanceDF # Start from the 4th row (index 3) and reset the index
        # print(tempDF.columns)


        tempDF['CodeName'] = None
        current_string = None

        # Iterate through each row
        for index, row in tempDF.iterrows():
            first_cell = str(row.iloc[0]).strip() # Get the first cell and strip any whitespace
            # print(first_cell)
            
            # Check if the first cell is NaN, skip if it is
            if first_cell == "NOT DATE":
                # tempDF.loc[index, 'CodeName'] = None  # Explicitly set CodeName to None
                continue  # Skip to the next iteration if the first cell is NaN

            # Convert to datetime, invalid parsing will be NaT
            parsed_date = pd.to_datetime(first_cell, errors='coerce', infer_datetime_format=True)

            if pd.isna(parsed_date):
                # If parsed_date is NaT, it means first_cell is not a date
                current_string = first_cell.split(' - ', 1)[0].strip()
                # print(current_string)
            else:
                # If parsed_date is not NaT, it means first_cell is a date
                tempDF.at[index, 'CodeName'] = current_string
                tempDF.at[index, 'Date'] = parsed_date.strftime('%Y-%m-%d')


        # Optionally, drop rows where 'CodeName' is still None
        tempDF = tempDF[tempDF['CodeName'].notna()]
        # # Reset the index after dropping rows
        # rawFinanceDF.reset_index(drop=True, inplace=True)

        # FORMATTING

        formatted_df = pd.DataFrame({
            'estate_name': property_name,
            'account_code': tempDF['CodeName'], 
            'ref_num_1': tempDF['Reference'],
            'ref_num_2': tempDF['Offset Reference'],
            'posted_date': tempDF['Date'], # not accurate
            'description': tempDF['Description'],
            'local_dr': tempDF['Debit'],
            'local_cr': tempDF['Credit'],
            'local_balance': tempDF['Balance'],
            'remarks': tempDF['Remarks']
        })


        # EXPORT FORMATTED DF
        output = BytesIO()  # Create an in-memory buffer
        formatted_df.to_csv(output, index=False)  # Write the DataFrame to the buffer as CSV
        output.seek(0)  # Move the pointer to the start off the buffer
        
        return send_file(output, mimetype='text/csv', as_attachment=True, download_name='processed_qns_finance_data.csv')


# Route for handling multiple file uploads
@app.route('/upload_multiple_merge', methods=['POST'])
def upload_multiple_merge():
    files = request.files.getlist('files')
    # Initialize an empty DataFrame to store the merged data
    merged_df = pd.DataFrame()

    if not files:
        return redirect('/')

    # Loop through each uploaded file and process
    for file in files:
        if file.filename == '':
            continue
        
         # Check if the file is a CSV file
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
            
            # Append the DataFrame to the merged DataFrame
            merged_df = pd.concat([merged_df, df], ignore_index=True)

            # Add a new column 'id' with sequential numbers starting from 1 for identification
            merged_df['id'] = range(1, len(merged_df) + 1)

            # Insert the new column 'id' at the first position (index 0)
            merged_df.insert(0, 'id', merged_df.pop('id'))

            # Save the merged DataFrame to a new CSV file
            output = BytesIO()
            merged_df.to_csv(output, index=False)
            output.seek(0)
    
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='merged_finance_data.csv')

if __name__ == '__main__':
    app.run(debug=True)
