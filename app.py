import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime
import re
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

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
    .warning {
        color: #d62728;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="header-style">BRAS Bandwidth Utilization Dashboard</div>', unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def load_bras_data():
    """Load and process BRAS data"""
    try:
        # Try multiple possible paths
        possible_paths = [
            os.path.join('raw_data', 'bras', 'combined_bw_utilization.csv'),
            os.path.join('data', 'bras', 'combined_bw_utilization.csv'),
            os.path.join('bras', 'combined_bw_utilization.csv'),
            'combined_bw_utilization.csv'
        ]
        
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break
        
        if not file_path:
            st.error("BRAS data file not found")
            return pd.DataFrame()
            
        # Read and process data
        df = pd.read_csv(file_path, engine='python', encoding='latin1')
        
        # Extract BRAS device info
        df['BRAS_Device'] = df['NE Location'].str.extract(r'(BRAS\d+)')
        df['Location'] = df['NE Location'].str.split(',').str[0] + '_' + df['BRAS_Device']
        
        # Filter for 100GE interfaces
        df = df[df['MO Location'].str.contains('100GE', na=False)]
        
        if not df.empty:
            # Clean and convert numeric values
            df['MaxSendTrafficRate(Mbps)'] = (
                df['MaxSendTrafficRate(Mbps)']
                .astype(str).str.replace(',', '')
                .astype(float)
            )
            
            # Calculate capacity (100G per BRAS)
            df['Total_Capacity'] = 100000  # 100 Gbps in Mbps
            
            # Process dates
            df['Date'] = pd.to_datetime(df['End Time'])
            df['Month'] = df['Date'].dt.to_period('M')
            
            # Aggregate data
            monthly_bras = df.groupby(['Month', 'Location']).agg({
                'MaxSendTrafficRate(Mbps)': 'max',
                'Total_Capacity': 'first'
            }).reset_index()
            
            # Calculate utilization
            monthly_bras['Utilization_Pct'] = (
                monthly_bras['MaxSendTrafficRate(Mbps)'] / 
                monthly_bras['Total_Capacity']
            ) * 100
            
            # Format for display
            monthly_bras['Month'] = monthly_bras['Month'].dt.to_timestamp()
            monthly_bras['Month_Name'] = monthly_bras['Month'].dt.strftime('%b %Y')
            
            return monthly_bras
            
    except Exception as e:
        st.error(f"Error loading BRAS data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_aaa_data():
    """Load and process AAA users data with comprehensive date handling"""
    try:
        # Try multiple possible paths
        possible_paths = [
            os.path.join('raw_data', 'aaa', 'Monthly AAA.xlsx'),
            os.path.join('data', 'aaa', 'Monthly AAA.xlsx'),
            os.path.join('aaa', 'Monthly AAA.xlsx'),
            'Monthly AAA.xlsx'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                df = pd.read_excel(path)
                break
        else:
            st.error("AAA data file not found")
            return pd.DataFrame()
        
        # Fix month names and standardize date format
        df['Month/Year'] = df['Month/Year'].astype(str).str.replace('Aprl', 'Apr')
        
        def parse_date(date_val):
            try:
                # Try parsing as datetime
                if isinstance(date_val, datetime):
                    return date_val
                # Try parsing as Excel serial date
                try:
                    return pd.to_datetime(float(date_val), unit='D', origin='1899-12-30')
                except:
                    pass
                # Try parsing as string (Apr-25 format)
                try:
                    return datetime.strptime(date_val, '%b-%y')
                except:
                    pass
                # Try parsing as YYYY-MM-DD
                try:
                    return pd.to_datetime(date_val)
                except:
                    pass
                return None
            except:
                return None
        
        df['Month'] = df['Month/Year'].apply(parse_date)
        df['Location'] = df['AAA Location'].str.split('_').str[0] + '_AAA'
        df.rename(columns={'User Quantity': 'AAA_Users'}, inplace=True)
        df['AAA_Users'] = pd.to_numeric(df['AAA_Users'], errors='coerce')
        df = df[df['Month'].notna()]
        
        # Create Month_Name for display
        df['Month_Name'] = df['Month'].dt.strftime('%b %Y')
        
        return df[['Month', 'Month_Name', 'Location', 'AAA_Users']].sort_values('Month')
        
    except Exception as e:
        st.error(f"Error loading AAA data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def combine_data(bras_df, aaa_df):
    """Combine BRAS and AAA data"""
    try:
        if bras_df.empty or aaa_df.empty:
            return pd.DataFrame()
            
        combined = pd.merge(
            bras_df, 
            aaa_df, 
            on=['Month', 'Month_Name', 'Location'], 
            how='outer'
        )
        
        # Fill missing values
        combined['MaxSendTrafficRate(Mbps)'] = combined['MaxSendTrafficRate(Mbps)'].fillna(0)
        combined['Utilization_Pct'] = combined['Utilization_Pct'].fillna(0)
        combined['AAA_Users'] = combined['AAA_Users'].fillna(0)
        combined['Total_Capacity'] = combined['Total_Capacity'].fillna(100000)
        
        return combined.sort_values('Month')
        
    except Exception as e:
        st.error(f"Error combining data: {str(e)}")
        return pd.DataFrame()

def create_combined_chart(data, region):
    """Create visualization with consistent data label styling"""
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # Filter for region
    region_data = data[data['Location'].str.startswith(region)].copy()
    
    if region_data.empty:
        st.warning(f"No data available for {region}")
        return fig
    
    # Get all months in dataset
    all_months = region_data['Month_Name'].unique()
    
   # Plot BRAS devices with exact label positioning
    bras_devices = {
        f"{region}_BRAS01": {'color': 'blue', 'offset': 10},  # Above line
        f"{region}_BRAS02": {'color': 'green', 'offset': -10}  # Below line
    }
    
    for device, style in bras_devices.items():
        device_data = region_data[region_data['Location'] == device].sort_values('Month')
        if not device_data.empty:
            # Apply 10x multiplier only for MDY_BRAS02
            y_values = device_data['Utilization_Pct'] * (10 if (region == 'MDY' and device.endswith('BRAS02')) else 1)
            label = f"{device} Utilization" + (" (×10)" if (region == 'MDY' and device.endswith('BRAS02')) else "")
            
            # Plot the line
            ax.plot(
                device_data['Month_Name'],
                y_values,
                marker='o',
                linewidth=2,
                color=style['color'],
                label=label
            )
            
            # Add data labels with precise positioning
            for i, row in device_data.iterrows():
                y_val = y_values.loc[i]
                ax.annotate(
                    f"{y_val:.1f}%", 
                    (row['Month_Name'], y_val),
                    textcoords="offset points",
                    xytext=(0, style['offset']),  # Exact positioning
                    ha='center',
                    fontsize=9,
                    fontweight='bold',
                    color=style['color'],
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8)
                )
    
 # Plot AAA Users on secondary axis
    ax2 = ax.twinx()
    aaa_data = region_data[region_data['Location'] == f"{region}_AAA"].sort_values('Month')
    if not aaa_data.empty:
        bars = ax2.bar(
            aaa_data['Month_Name'],
            aaa_data['AAA_Users'],
            color='gray',
            alpha=0.3,
            width=0.4,
            label=f'{region}_AAA Users'
        )
        # Add AAA data labels (centered)
        for i, row in aaa_data.iterrows():
            ax2.annotate(
                f"{row['AAA_Users']:,.0f}",
                (row['Month_Name'], row['AAA_Users']),
                textcoords="offset points",
                xytext=(0, 0),
                ha='center',
                va='center',
                fontsize=9,
                fontweight='bold',
                color='black',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8)
            )
    
    # Formatting
    ax.set_xlabel('Month')
    ax.set_ylabel('Utilization (%)')
    if not aaa_data.empty:
        ax2.set_ylabel('AAA Users')
    
    ax.set_ylim(0, 100)
    ax.axhline(y=80, color='red', linestyle=':', label='80% Threshold')
    
    # Combine legends
    lines1, labels1 = ax.get_legend_handles_labels()
    if not aaa_data.empty:
        lines2, labels2 = ax2.get_legend_handles_labels()
        lines1 += lines2
        labels1 += labels2
    ax.legend(lines1, labels1, loc='upper left')
    
    plt.title(f'{region} - BRAS Utilization & AAA Users')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig

def main():
    try:
        bras_df = load_bras_data()
        aaa_df = load_aaa_data()
        combined_df = combine_data(bras_df, aaa_df)

        if not combined_df.empty:
            # Sidebar filters
            st.sidebar.header("Dashboard Filters")
            region = st.sidebar.selectbox("Select Region:", ['MDY', 'NPT'])
            
            # Display KPIs - Showing Peak Values
            st.markdown("### Key Performance Indicators")
            cols = st.columns(3)
            
            # Get peak values for the selected region
            region_data = combined_df[combined_df['Location'].str.startswith(region)]
            
            # BRAS01 Peak Utilization
            bras01_data = region_data[region_data['Location'] == f"{region}_BRAS01"]
            if not bras01_data.empty:
                peak_util = bras01_data['MaxSendTrafficRate(Mbps)'].max() / 1000
                peak_month = bras01_data.loc[bras01_data['MaxSendTrafficRate(Mbps)'].idxmax()]['Month_Name']
                with cols[0]:
                    st.markdown(f'<div class="metric-card">'
                              f'<div class="metric-value">{peak_util:.1f} Gbps</div>'
                              f'<div class="metric-label">{region}_BRAS01 Peak</div>'
                              f'<div class="metric-label">({peak_month})</div></div>', 
                              unsafe_allow_html=True)
            
            # BRAS02 Peak Utilization
            bras02_data = region_data[region_data['Location'] == f"{region}_BRAS02"]
            if not bras02_data.empty:
                peak_util = bras02_data['MaxSendTrafficRate(Mbps)'].max() / 1000
                peak_month = bras02_data.loc[bras02_data['MaxSendTrafficRate(Mbps)'].idxmax()]['Month_Name']
                with cols[1]:
                    st.markdown(f'<div class="metric-card">'
                              f'<div class="metric-value">{peak_util:.1f} Gbps</div>'
                              f'<div class="metric-label">{region}_BRAS02 Peak</div>'
                              f'<div class="metric-label">({peak_month})</div></div>', 
                              unsafe_allow_html=True)
            
            # AAA Peak Users
            aaa_data = region_data[region_data['Location'] == f"{region}_AAA"]
            if not aaa_data.empty:
                peak_users = aaa_data['AAA_Users'].max()
                peak_month = aaa_data.loc[aaa_data['AAA_Users'].idxmax()]['Month_Name']
                with cols[2]:
                    st.markdown(f'<div class="metric-card">'
                              f'<div class="metric-value">{peak_users:,.0f}</div>'
                              f'<div class="metric-label">{region}_AAA Peak Users</div>'
                              f'<div class="metric-label">({peak_month})</div></div>', 
                              unsafe_allow_html=True)

            # Main visualization
            st.markdown("### Bandwidth Utilization & AAA Users")
            fig = create_combined_chart(combined_df, region)
            st.pyplot(fig)
            
            # Data tables
            st.markdown("### Detailed Data")
            
            # Create separate tabs for BRAS and AAA data
            tab1, tab2 = st.tabs(["BRAS Utilization", "AAA Users"])
            
            with tab1:
                bras_data = combined_df[
                    combined_df['Location'].str.startswith(f"{region}_BRAS")
                ][['Month_Name', 'Location', 'MaxSendTrafficRate(Mbps)', 'Utilization_Pct']]
                st.dataframe(
                    bras_data.rename(columns={
                        'Month_Name': 'Month',
                        'MaxSendTrafficRate(Mbps)': 'Peak Utilization (Mbps)',
                        'Utilization_Pct': 'Utilization (%)'
                    }).style.format({
                        'Peak Utilization (Mbps)': '{:,.2f}',
                        'Utilization (%)': '{:.1f}%'
                    }),
                    height=400
                )
            
            with tab2:
                aaa_data = combined_df[
                    combined_df['Location'] == f"{region}_AAA"
                ][['Month_Name', 'AAA_Users']]
                st.dataframe(
                    aaa_data.rename(columns={
                        'Month_Name': 'Month',
                    }).style.format({
                        'AAA_Users': '{:,.0f}'
                    }),
                    height=400
                )
            
            # Footer
            st.markdown("---")
            st.markdown(f"**Data Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            st.markdown("**Note:** Utilization calculated based on 100G interface capacity per BRAS")

        else:
            st.warning("No data available to display. Please check your data files.")

    except Exception as e:
        st.error(f"Application error: {str(e)}")

if __name__ == "__main__":
    main()