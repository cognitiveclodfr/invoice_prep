import datetime
import pandas as pd
import os

def get_dates_from_user():
    """Interactively prompts the user for start and end dates with validation."""
    start_date = None
    end_date = None

    while not start_date:
        date_str = input("Введіть початкову дату (формат YYYY-MM-DD): ").strip()
        try:
            start_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print("Неправильний формат дати. Будь ласка, введіть дату у форматі YYYY-MM-DD.")

    while not end_date:
        date_str = input("Введіть кінцеву дату (формат YYYY-MM-DD): ").strip()
        try:
            end_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            if end_date < start_date:
                print("Помилка: Кінцева дата не може бути раніше початкової. Спробуйте ще раз.")
                end_date = None  # Reset to re-prompt
        except ValueError:
            print("Неправильний формат дати. Будь ласка, введіть дату у форматі YYYY-MM-DD.")

    return start_date, end_date

def main():
    """Main function to run the script."""
    start_date, end_date = get_dates_from_user()
    print(f"Script started. Filtering orders from {start_date} to {end_date}")

    input_file = 'Example CSV/orders_export_1.csv'

    # Check for input file existence
    if not os.path.exists(input_file):
        print(f"Error: Input file not found at '{input_file}'")
        return

    # Load the CSV data
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    print(f"Successfully loaded {len(df)} rows from {input_file}")

    # Identify and separate problematic orders
    critical_columns = ['Fulfilled at', 'Lineitem sku', 'Lineitem quantity', 'Lineitem price', 'Name']

    # Verify that critical columns exist
    missing_cols = [col for col in critical_columns if col not in df.columns]
    if missing_cols:
        print(f"Error: The following critical columns are missing from the input file: {', '.join(missing_cols)}")
        return

    # Find rows with nulls in the specified columns. 'Fulfilled at' is intentionally excluded
    # here because it's expected to be null for subsequent line items in a single order.
    # We only check for data that should exist for every line item.
    check_cols = ['Lineitem sku', 'Lineitem quantity', 'Lineitem price']
    rows_with_nulls = df[df[check_cols].isnull().any(axis=1)]

    problematic_order_ids = rows_with_nulls['Name'].unique()

    problematic_orders_df = df[df['Name'].isin(problematic_order_ids)].copy()
    main_df = df[~df['Name'].isin(problematic_order_ids)].copy()

    print(f"Identified {len(problematic_order_ids)} problematic orders with {len(problematic_orders_df)} total line items.")
    print(f"Processing {len(main_df)} remaining line items.")

    # --- New Step 4: Filter by orders, not rows ---
    print("Starting new filtering logic...")

    # Isolate order "header" information to find valid orders.
    # A reliable way to find headers is to find non-null 'Fulfilled at' rows.
    order_headers_df = main_df.dropna(subset=['Fulfilled at', 'Fulfillment Status']).copy()

    # Filter these headers by status
    order_headers_df = order_headers_df[order_headers_df['Fulfillment Status'] == 'fulfilled']

    # Convert 'Fulfilled at' to datetime and handle errors
    order_headers_df['Fulfilled at DT'] = pd.to_datetime(order_headers_df['Fulfilled at'], errors='coerce', utc=True)
    order_headers_df.dropna(subset=['Fulfilled at DT'], inplace=True)

    # Filter by the specified date range
    order_headers_df['Fulfilled at Date'] = order_headers_df['Fulfilled at DT'].dt.date
    date_mask = (order_headers_df['Fulfilled at Date'] >= start_date) & (order_headers_df['Fulfilled at Date'] <= end_date)
    valid_orders_headers_df = order_headers_df[date_mask]

    # Get the unique IDs of the valid orders
    valid_order_ids = valid_orders_headers_df['Name'].unique()
    print(f"Found {len(valid_order_ids)} valid orders within the specified date range.")

    # Get all line items for these valid orders from the clean dataframe
    final_filtered_df = main_df[main_df['Name'].isin(valid_order_ids)].copy()

    print(f"Total line items in the final report: {len(final_filtered_df)}")

    # Step 5: Create and style the output XLSX file
    output_filename = f"filtered_orders_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.xlsx"

    # Define the columns for the final report, including 'Fulfillment Status' for styling
    output_columns = ['Name', 'Fulfilled at', 'Fulfillment Status', 'Lineitem sku', 'Lineitem quantity', 'Lineitem price']

    # Ensure final_filtered_df has all the necessary columns before proceeding
    final_filtered_df = final_filtered_df.reindex(columns=output_columns)

    try:
        with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
            # --- Write and Style Filtered Orders Sheet ---
            if not final_filtered_df.empty:
                final_filtered_df.to_excel(writer, sheet_name='Filtered Orders', index=False)
                worksheet = writer.sheets['Filtered Orders']

                from openpyxl.styles import Font, Border, Side
                from openpyxl.utils import get_column_letter

                bold_font = Font(bold=True)
                thin_top_border = Border(top=Side(style='thin'))

                # Get column indices for styling
                col_indices = {name: i + 1 for i, name in enumerate(final_filtered_df.columns)}
                name_col_idx = col_indices.get('Name')
                status_col_idx = col_indices.get('Fulfillment Status')

                # Style header
                for col_idx in range(1, worksheet.max_column + 1):
                    worksheet.cell(row=1, column=col_idx).font = bold_font

                # Apply styles row by row
                for row_idx in range(2, worksheet.max_row + 1):
                    # Apply bold font to specific columns
                    if name_col_idx:
                        worksheet.cell(row=row_idx, column=name_col_idx).font = bold_font
                    if status_col_idx:
                        worksheet.cell(row=row_idx, column=status_col_idx).font = bold_font

                    # Apply border between orders
                    if name_col_idx and row_idx > 1:
                        current_order_name = worksheet.cell(row=row_idx, column=name_col_idx).value
                        prev_order_name = worksheet.cell(row=row_idx - 1, column=name_col_idx).value
                        if current_order_name != prev_order_name:
                            for col_idx in range(1, worksheet.max_column + 1):
                                worksheet.cell(row=row_idx, column=col_idx).border = thin_top_border

                # Auto-fit columns
                for col_idx, column in enumerate(worksheet.columns, 1):
                    max_length = 0
                    column_letter = get_column_letter(col_idx)
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            # --- Write and Style Problematic Orders Sheet ---
            if not problematic_orders_df.empty:
                problematic_orders_df.to_excel(writer, sheet_name='Problematic Orders', index=False)
                worksheet_prob = writer.sheets['Problematic Orders']
                # Auto-fit columns
                for col_idx, column in enumerate(worksheet_prob.columns, 1):
                    max_length = 0
                    column_letter = get_column_letter(col_idx)
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet_prob.column_dimensions[column_letter].width = adjusted_width

        print(f"Processing complete. Output saved to '{output_filename}'")

    except Exception as e:
        print(f"An error occurred while writing the Excel file: {e}")

if __name__ == "__main__":
    main()
