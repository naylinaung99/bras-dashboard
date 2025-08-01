import streamlit as st
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO
import base64

def get_data_path(filename):
    """Get absolute path to data file with multiple fallback options"""
    # List of possible base directories to check
    base_dirs = [
        os.path.dirname(__file__),  # Current script directory
        os.getcwd(),  # Current working directory
        os.path.join(os.path.dirname(__file__), ".."),  # One level up
        os.path.join(os.getcwd(), "..")  # One level up from cwd
    ]
    
    # List of possible data folder structures
    data_folders = [
        os.path.join("raw_data", "bras" if "BRAS" in filename else "aaa"),
        os.path.join("data", "bras" if "BRAS" in filename else "aaa"),
        "raw_data",
        "data"
    ]
    
    # Try all combinations of base directories and data folders
    for base_dir in base_dirs:
        for data_folder in data_folders:
            path = os.path.join(base_dir, data_folder, filename)
            if os.path.exists(path):
                st.write(f"Found file at: {path}")
                return path
    
    # If not found, show all attempted paths
    attempted_paths = "\n".join(
        os.path.join(base_dir, data_folder, filename)
        for base_dir in base_dirs
        for data_folder in data_folders
    )
    raise FileNotFoundError(
        f"Could not find {filename} in any expected location.\n"
        f"Attempted paths:\n{attempted_paths}"
    )

# Set page config
st.set_page_config(
    page_title="BRAS Utilization Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom styling
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    .header-style {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1.5rem;
        color: #1f77b4;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 1rem;
        color: #7f7f7f;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="header-style">BRAS Bandwidth Utilization Dashboard</div>', unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def load_bras_data():
    """Load BRAS traffic forecast data (Jan 2025-Jul 2025 actuals only)"""
    try:
        file_path = get_data_path("BRAS_traffic_forecast_final.xlsx")
        df = pd.read_excel(file_path, sheet_name='Traffic_Forecast')
        
        # Filter date range and actual data only
        df['Month'] = pd.to_datetime(df['Month'])
        df = df[(df['Month'] >= '2025-01-01') & 
                (df['Month'] <= '2025-12-31') &
                (df['Data Type'] == 'Actual')]
        
        # Melt to long format
        bras_df = df.melt(
            id_vars=['Month', 'Data Type'], 
            value_vars=['MDY_BRAS01', 'MDY_BRAS02', 'NPT_BRAS01', 'NPT_BRAS02'],
            var_name='Location',
            value_name='MaxSendTrafficRate(Gbps)'
        )
        
        # Convert to Mbps and calculate utilization
        bras_df['MaxSendTrafficRate(Mbps)'] = bras_df['MaxSendTrafficRate(Gbps)'] * 1000
        bras_df['Total_Capacity'] = 100000  # 100G in Mbps
        bras_df['Utilization_Pct'] = (bras_df['MaxSendTrafficRate(Mbps)'] / bras_df['Total_Capacity']) * 100
        bras_df['Month_Name'] = bras_df['Month'].dt.strftime('%b %Y')
        bras_df['Is_Forecast'] = False
        
        return bras_df
        
    except Exception as e:
        st.error(f"Error loading BRAS data: {str(e)}")
        st.error(f"Current working directory: {os.getcwd()}")
        st.error(f"Attempted to load from: {os.path.join('raw_data', 'bras', 'BRAS_traffic_forecast_final.xlsx')}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_aaa_data():
    """Load AAA users data (Jan 2025-Jul 2025 actuals only)"""
    try:
        file_path = get_data_path("Monthly_AAA.xlsx")
        df = pd.read_excel(file_path, sheet_name='AAA Users')
        
        # Filter date range and actual data only
        df['Month'] = pd.to_datetime(df['Month'])
        df = df[(df['Month'] >= '2025-01-01') & 
                (df['Month'] <= '2025-12-31') &
                (df['Data Type'] == 'Actual')]
        
        # Melt to long format
        aaa_df = df.melt(
            id_vars=['Month', 'Data Type'], 
            value_vars=['MDY_AAA', 'NPT_AAA'],
            var_name='Location',
            value_name='AAA_Users'
        )
        
        aaa_df['Month_Name'] = aaa_df['Month'].dt.strftime('%b %Y')
        aaa_df['Is_Forecast'] = False
        
        return aaa_df
        
    except Exception as e:
        st.error(f"Error loading AAA data: {str(e)}")
        st.error(f"Current working directory: {os.getcwd()}")
        st.error(f"Attempted to load from: {os.path.join('raw_data', 'aaa', 'Monthly_AAA.xlsx')}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_full_data():
    """Load full data including forecasts for visualization"""
    try:
        # BRAS data
        bras_path = get_data_path("BRAS_traffic_forecast_final.xlsx")
        bras_df = pd.read_excel(bras_path, sheet_name='Traffic_Forecast')
        bras_df['Month'] = pd.to_datetime(bras_df['Month'])
        bras_df = bras_df[(bras_df['Month'] >= '2025-01-01') & (bras_df['Month'] <= '2025-12-31')]
        
        bras_df = bras_df.melt(
            id_vars=['Month', 'Data Type'], 
            value_vars=['MDY_BRAS01', 'MDY_BRAS02', 'NPT_BRAS01', 'NPT_BRAS02'],
            var_name='Location',
            value_name='MaxSendTrafficRate(Gbps)'
        )
        
        bras_df['MaxSendTrafficRate(Mbps)'] = bras_df['MaxSendTrafficRate(Gbps)'] * 1000
        bras_df['Total_Capacity'] = 100000
        bras_df['Utilization_Pct'] = (bras_df['MaxSendTrafficRate(Mbps)'] / bras_df['Total_Capacity']) * 100
        bras_df['Month_Name'] = bras_df['Month'].dt.strftime('%b %Y')
        bras_df['Is_Forecast'] = bras_df['Data Type'] == 'Forecast'
        
        # AAA data
        aaa_path = get_data_path("Monthly_AAA.xlsx")
        aaa_df = pd.read_excel(aaa_path, sheet_name='AAA Users')
        aaa_df['Month'] = pd.to_datetime(aaa_df['Month'])
        aaa_df = aaa_df[(aaa_df['Month'] >= '2025-01-01') & (aaa_df['Month'] <= '2025-12-31')]
        
        aaa_df = aaa_df.melt(
            id_vars=['Month', 'Data Type'], 
            value_vars=['MDY_AAA', 'NPT_AAA'],
            var_name='Location',
            value_name='AAA_Users'
        )
        
        aaa_df['Month_Name'] = aaa_df['Month'].dt.strftime('%b %Y')
        aaa_df['Is_Forecast'] = aaa_df['Data Type'] == 'Forecast'
        
        return pd.concat([bras_df, aaa_df], ignore_index=True)
        
    except Exception as e:
        st.error(f"Error loading full data: {str(e)}")
        return pd.DataFrame()

def create_combined_chart(data, region):
    """Create visualization with enhanced display"""
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(16, 8))  # Larger figure size
    
    # Filter for region and sort
    region_data = data[data['Location'].str.startswith(region)].copy()
    region_data = region_data.sort_values('Month')
    region_data['Month_Name'] = region_data['Month'].dt.strftime('%b %Y')

    # Plot AAA Users (bars)
    aaa_data = region_data[region_data['Location'] == f"{region}_AAA"]
    if not aaa_data.empty:
        actual_aaa = aaa_data[~aaa_data['Is_Forecast']]
        forecast_aaa = aaa_data[aaa_data['Is_Forecast']]

        # Actual AAA (gray bars)
        ax.bar(
            actual_aaa['Month_Name'],
            actual_aaa['AAA_Users'],
            color='gray',
            alpha=0.7,
            width=0.4,
            label=f'{region}_AAA Users'
        )
        
        # Forecast AAA (light yellow bars)
        if not forecast_aaa.empty:
            ax.bar(
                forecast_aaa['Month_Name'],
                forecast_aaa['AAA_Users'],
                color='lightyellow',
                edgecolor='gray',
                width=0.4,
                label=f'{region}_AAA Users (Forecast)'
            )
        
        # Data labels
        for _, row in aaa_data.iterrows():
            ax.annotate(
                f"{row['AAA_Users']:,.0f}",
                (row['Month_Name'], row['AAA_Users']),
                textcoords="offset points",
                xytext=(0, 0),
                ha='center',
                va='center',
                fontsize=9,
                fontweight='bold',
                fontname='Arial',
                color='black',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8)
            )

    # Secondary y-axis for BRAS utilization
    ax2 = ax.twinx()

    bras_devices = {
        f"{region}_BRAS01": {'color': 'blue', 'offset': 10, 'multiplier': 1},
        f"{region}_BRAS02": {'color': 'green', 'offset': 10, 'multiplier': 50}  # 50x multiplier for BRAS02
    }

    for device, style in bras_devices.items():
        device_data = region_data[region_data['Location'] == device]
        if not device_data.empty:
            actual_data = device_data[~device_data['Is_Forecast']]
            forecast_data = device_data[device_data['Is_Forecast']]

            # Apply multiplier (50x for BRAS02)
            actual_y_values = actual_data['Utilization_Pct'] * style['multiplier']
            forecast_y_values = forecast_data['Utilization_Pct'] * style['multiplier']

            label = f"{device} Utilization" + (" (×50)" if style['multiplier'] == 50 else "")

            # Plot actual utilization (solid line)
            ax2.plot(
                actual_data['Month_Name'],
                actual_y_values,
                marker='o',
                markersize=8,
                linewidth=2,
                color=style['color'],
                label=label,
                zorder=3
            )

            # Connect last actual to first forecast
            if not forecast_data.empty and not actual_data.empty:
                connecting_x = [
                    actual_data['Month_Name'].iloc[-1],
                    forecast_data['Month_Name'].iloc[0]
                ]
                connecting_y = [
                    actual_y_values.iloc[-1],
                    forecast_y_values.iloc[0]
                ]
                ax2.plot(
                    connecting_x,
                    connecting_y,
                    linestyle='--',
                    linewidth=2,
                    color=style['color'],
                    zorder=3
                )

            # Plot forecast (dotted line)
            if not forecast_data.empty:
                ax2.plot(
                    forecast_data['Month_Name'],
                    forecast_y_values,
                    linestyle='--',
                    linewidth=2,
                    color=style['color'],
                    label=f"{label} (Forecast)",
                    zorder=3
                )

            # Data labels
            for _, row in device_data.iterrows():
                y_val = row['Utilization_Pct'] * style['multiplier']
                ax2.annotate(
                    f"{y_val:.1f}%",
                    (row['Month_Name'], y_val),
                    textcoords="offset points",
                    xytext=(0, style['offset']),
                    ha='center',
                    fontsize=9,
                    fontweight='bold',
                    fontname='Arial',
                    color=style['color'],
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8),
                    zorder=4
                )

    # Formatting
    ax.set_xlabel('Month', fontsize=12)
    ax.set_ylabel('AAA Users', fontsize=12)
    ax2.set_ylabel('Utilization (%)', fontsize=12)
    ax2.set_ylim(0, 100)
    ax2.axhline(y=80, color='red', linestyle=':', label='80% Threshold', zorder=2)

    # Combine legends and position them better
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(
        lines1 + lines2, 
        labels1 + labels2, 
        loc='upper center',
        bbox_to_anchor=(0.5, -0.15),
        ncol=3,
        fontsize=10
    )

    plt.title(f'{region} - BRAS Utilization & AAA Users (Actual & Forecast)', fontsize=14, pad=20)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    return fig

def get_image_download_link(fig, filename):
    """Generate a download link for the chart image"""
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}">Download Chart Image</a>'
    return href
    
def main():
    # Debug information
    st.sidebar.title("Debug Info")
    st.sidebar.write("Current working directory:", os.getcwd())
    
    try:
        # Check if data files exist
        bras_path = get_data_path("BRAS_traffic_forecast_final.xlsx")
        aaa_path = get_data_path("Monthly_AAA.xlsx")
        st.sidebar.write("BRAS file exists:", os.path.exists(bras_path))
        st.sidebar.write("AAA file exists:", os.path.exists(aaa_path))
        
        # Load actual data for KPIs (Jan-Jul 2025)
        bras_df = load_bras_data()
        aaa_df = load_aaa_data()
        kpi_df = pd.concat([bras_df, aaa_df], ignore_index=True)
        
        # Load full data for visualization (including forecasts)
        full_df = load_full_data()
        
        if not kpi_df.empty and not full_df.empty:
            region = st.sidebar.selectbox("Select Region:", ['MDY', 'NPT'])
            
            # Display KPIs (using actual data only)
            st.markdown("### Key Performance Indicators (Jan-Jul 2025 Actual Data)")
            cols = st.columns(3)
            
            # Get actual data for selected region
            region_kpi_data = kpi_df[kpi_df['Location'].str.startswith(region)]
            
            # BRAS01 Peak Utilization
            bras01_data = region_kpi_data[region_kpi_data['Location'] == f"{region}_BRAS01"]
            if not bras01_data.empty:
                peak_util = bras01_data['MaxSendTrafficRate(Gbps)'].max()
                peak_month = bras01_data.loc[bras01_data['MaxSendTrafficRate(Gbps)'].idxmax()]['Month_Name']
                with cols[0]:
                    st.markdown(f'<div class="metric-card">'
                              f'<div class="metric-value">{peak_util:.1f} Gbps</div>'
                              f'<div class="metric-label">{region}_BRAS01 Peak</div>'
                              f'<div class="metric-label">({peak_month})</div></div>', 
                              unsafe_allow_html=True)
            
            # BRAS02 Peak Utilization
            bras02_data = region_kpi_data[region_kpi_data['Location'] == f"{region}_BRAS02"]
            if not bras02_data.empty:
                peak_util = bras02_data['MaxSendTrafficRate(Gbps)'].max()
                peak_month = bras02_data.loc[bras02_data['MaxSendTrafficRate(Gbps)'].idxmax()]['Month_Name']
                with cols[1]:
                    st.markdown(f'<div class="metric-card">'
                              f'<div class="metric-value">{peak_util:.1f} Gbps</div>'
                              f'<div class="metric-label">{region}_BRAS02 Peak</div>'
                              f'<div class="metric-label">({peak_month})</div></div>', 
                              unsafe_allow_html=True)
            
            # AAA Peak Users
            aaa_data = region_kpi_data[region_kpi_data['Location'] == f"{region}_AAA"]
            if not aaa_data.empty:
                peak_users = aaa_data['AAA_Users'].max()
                peak_month = aaa_data.loc[aaa_data['AAA_Users'].idxmax()]['Month_Name']
                with cols[2]:
                    st.markdown(f'<div class="metric-card">'
                              f'<div class="metric-value">{peak_users:,.0f}</div>'
                              f'<div class="metric-label">{region}_AAA Peak Users</div>'
                              f'<div class="metric-label">({peak_month})</div></div>', 
                              unsafe_allow_html=True)
            
            # Main visualization (with forecasts)
            st.markdown("### Bandwidth Utilization & AAA Users (With Forecast)")
            fig = create_combined_chart(full_df, region)
            st.pyplot(fig)
            
            # Create downloadable report
            st.markdown("### Download Report")
            
            # Create a DataFrame for KPIs
            kpi_report = pd.DataFrame({
                'Metric': [
                    f'{region}_BRAS01 Peak Utilization (Gbps)',
                    f'{region}_BRAS02 Peak Utilization (Gbps) (×50)',
                    f'{region}_AAA Peak Users'
                ],
                'Value': [
                    bras01_data['MaxSendTrafficRate(Gbps)'].max(),
                    bras02_data['MaxSendTrafficRate(Gbps)'].max() * 50,
                    aaa_data['AAA_Users'].max()
                ],
                'Month': [
                    bras01_data.loc[bras01_data['MaxSendTrafficRate(Gbps)'].idxmax()]['Month_Name'],
                    bras02_data.loc[bras02_data['MaxSendTrafficRate(Gbps)'].idxmax()]['Month_Name'],
                    aaa_data.loc[aaa_data['AAA_Users'].idxmax()]['Month_Name']
                ]
            })
            
            # Create Excel file with KPIs and chart
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                kpi_report.to_excel(writer, sheet_name='KPIs', index=False)
                
                # Add chart image to Excel
                workbook = writer.book
                worksheet = workbook.add_worksheet('Chart')
                buf = BytesIO()
                fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
                buf.seek(0)
                worksheet.insert_image('A1', 'chart.png', {'image_data': buf})
            
            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📥 Download Full Data as Excel",
                    data=output.getvalue(),
                    file_name=f"{region}_BRAS_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            with col2:
                st.markdown(get_image_download_link(fig, f"{region}_chart.png"), unsafe_allow_html=True)

            # Data tables
            st.markdown("### Detailed Data")
            
            tab1, tab2 = st.tabs(["BRAS Utilization", "AAA Users"])
            
            with tab1:
                bras_data = full_df[
                    (full_df['Location'].str.startswith(f"{region}_BRAS")) &
                    (full_df['Month'] <= '2025-12-31')
                ][['Month_Name', 'Location', 'MaxSendTrafficRate(Gbps)', 'Utilization_Pct', 'Is_Forecast']]
                st.dataframe(
                    bras_data.rename(columns={
                        'Month_Name': 'Month',
                        'MaxSendTrafficRate(Gbps)': 'Peak Utilization (Gbps)',
                        'Utilization_Pct': 'Utilization (%)',
                        'Is_Forecast': 'Is Forecast'
                    }).style.format({
                        'Peak Utilization (Gbps)': '{:,.2f}',
                        'Utilization (%)': '{:.1f}%'
                    }).apply(lambda x: ['background: lightyellow' if x['Is Forecast'] else '' for i in x], axis=1),
                    height=400
                )
            
            with tab2:
                aaa_data = full_df[
                    (full_df['Location'] == f"{region}_AAA") &
                    (full_df['Month'] <= '2025-12-31')
                ][['Month_Name', 'AAA_Users', 'Is_Forecast']]
                st.dataframe(
                    aaa_data.rename(columns={
                        'Month_Name': 'Month',
                        'Is_Forecast': 'Is Forecast'
                    }).style.format({
                        'AAA_Users': '{:,.0f}'
                    }).apply(lambda x: ['background: lightyellow' if x['Is Forecast'] else '' for i in x], axis=1),
                    height=400
                )

        else:
            st.warning("No data available to display. Please check your data files.")

    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.error("Please ensure:")
        st.error("1. Your data files exist in the correct location")
        st.error("2. The files have the correct names")
        st.error("3. You have all required permissions to access the files")

if __name__ == "__main__":
    main()