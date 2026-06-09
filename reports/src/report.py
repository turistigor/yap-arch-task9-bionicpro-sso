from datetime import date, datetime

from pandas import DataFrame


css_styles = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #333333;
        margin: 30px;
        background-color: #f9f9f9;
    }
    .report-header {
        margin-bottom: 25px;
        padding: 15px;
        background: #ffffff;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .report-header h2 { margin: 0 0 10px 0; color: #1a1a1a; }
    .report-header p { margin: 4px 0; color: #666666; font-size: 14px; }

    .styled-table {
        border-collapse: collapse;
        margin: 25px 0;
        font-size: 14px;
        min-width: 400px;
        width: 100%;
        background: #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border-radius: 6px;
        overflow: hidden;
    }
    .styled-table thead tr {
        background-color: #0052cc;
        color: #ffffff;
        text-align: left;
        font-weight: bold;
    }
    .styled-table th, .styled-table td {
        padding: 12px 15px;
    }
    .styled-table tbody tr {
        border-bottom: 1px solid #dddddd;
    }
    .styled-table tbody tr:nth-of-type(even) {
        background-color: #f3f3f3;
    }
    .styled-table tbody tr:last-of-type {
        border-bottom: 2px solid #0052cc;
    }
    .styled-table tbody tr:hover {
        background-color: #f1f5f9;
    }
</style>
"""

def create_html_report(
    user_name: str, user_id: str, table_data: DataFrame, period: date,
) -> str:
    creation_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    table_html = table_data.to_html(classes='dataframe styled-table', index_names=False)

    return _create_html_report(user_name, user_id, creation_dt, table_html, period)


def _create_html_report(
    user_name: str, user_id: str, creation_dt: str, table_html: str, period: date,
) -> str:
    return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Telemetry Report</title>
            {css_styles}
        </head>
        <body>
            <div class="report-header">
                <h2>Report for {user_name}</h2>
                <p><b>Created at:</b> {creation_dt}</p>
                <p><b>Creator ID:</b> {user_id}</p>
                <p><b>Report for the period:</b> {str(period)}</p>
            </div>
            {table_html}
        </body>
        </html>
    '''
