import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta, date
import os

# --- Set konfigurasi halaman ---
st.set_page_config(page_title="DSS Waktu Tanam Padi", layout="wide")

# --- Judul utama ---
st.title("🌾 Sistem Rekomendasi Waktu Tanam Padi Sumatera Utara")
st.markdown("""
Sistem ini mengintegrasikan prediksi curah hujan menggunakan LSTM, 
Rule-Based System untuk rekomendasi waktu tanam, prediksi harga beras, 
dan informasi serangan hama sebagai pendukung keputusan.
""")

# --- Fungsi untuk memuat data ---
@st.cache_data
def load_data():
    try:
        # Coba load data aktual jika ada
        if os.path.exists('streamlit/hasil_dss_gabungan_label_streamlit.csv'):
            dss = pd.read_csv('streamlit/hasil_dss_gabungan_label_streamlit.csv')
            dss['Tanggal'] = pd.to_datetime(dss['Tanggal'])
            
            # Filter supaya hanya sampai 30 April 2025
            dss = dss[dss['Tanggal'] <= pd.to_datetime('2025-04-30')]
            
            # Rename kolom jika perlu (opsional)
            if 'Label RBS' in dss.columns and 'Label RBS' not in dss.columns:
                dss = dss.rename(columns={'Label RBS': 'Label RBS'})
        else:
            # Data sintetis jika file tidak ada
            date_range = pd.date_range(start='2024-05-01', end='2025-04-30')
            dss_data = []
            for date in date_range:
                month = date.month
                is_rainy = month >= 10 or month <= 3
                
                total_5 = np.random.normal(85 if is_rainy else 40, 20)
                max_dry = np.random.randint(2 if is_rainy else 5, 10 if is_rainy else 15)
                total_30 = np.random.normal(350 if is_rainy else 180, 50)
                
                score = 0
                if total_5 >= 38:
                    score += 2
                elif total_5 >= 30:
                    score += 1
                if max_dry <= 10:
                    score += 2
                elif max_dry <= 14:
                    score += 1
                if total_30 >= 300:
                    score += 1
                if total_30 >= 500:
                    score += 1
                
                if total_5 >= 35 and max_dry == 15 and total_30 >= 350:
                    label = 'Kuning'
                elif score >= 5:
                    label = 'Hijau'
                elif score >= 2:
                    label = 'Kuning'
                else:
                    label = 'Merah'
                
                dss_data.append({
                    'Tanggal': date,
                    'Total 5 Hari (mm)': total_5,
                    'Max Kering 15 Hari': max_dry,
                    'Total 30 Hari (mm)': total_30,
                    'Label RBS': label
                })
            dss = pd.DataFrame(dss_data)

        # Load data harga beras
        if os.path.exists('streamlit/harga_beras_forecast.xlsx'):
            harga = pd.read_excel('streamlit/harga_beras_forecast.xlsx')
            harga['Tanggal'] = pd.to_datetime(harga['Tanggal'])
            harga = harga[harga['Tanggal'] <= pd.to_datetime('2025-04-30')]  # Filter juga
        else:
            price_dates = pd.date_range(start='2024-05-01', end='2025-04-30')
            prices = []
            base_price = 13000
            for date in price_dates:
                price = base_price * (1 + np.random.normal(0, 0.02))
                prices.append({
                    'Tanggal': date,
                    'Prediksi Harga Beras (Rp/kg)': price
                })
            harga = pd.DataFrame(prices)

        # Load data serangan hama
        if os.path.exists('streamlit/dataset_hama.xlsx'):
            hama = pd.read_excel('streamlit/dataset_hama.xlsx')
        else:
            years = ['2020/2021', '2021/2022', '2022/2023', '2023/2024']
            pests = ['Penggerek Batang', 'Wereng Batang Cokelat', 'Tikus', 'Blas', 'Hawar Daun Bakteri', 'Tungro']
            
            hama_data = []
            for year in years:
                for pest in pests:
                    if pest == 'Penggerek Batang':
                        area = np.random.uniform(400, 1500)
                    elif pest == 'Wereng Batang Cokelat':
                        area = np.random.uniform(8, 25)
                    elif pest == 'Tikus':
                        area = np.random.uniform(300, 500)
                    elif pest == 'Blas':
                        area = np.random.uniform(900, 1700)
                    elif pest == 'Hawar Daun Bakteri':
                        area = np.random.uniform(700, 1300)
                    else:
                        area = np.random.uniform(2, 15)
                    
                    hama_data.append({
                        'Tahun': year,
                        'Jenis hama': pest,
                        'Luas serangan hama (HA)': area
                    })
            hama = pd.DataFrame(hama_data)
        
        return dss, harga, hama

    except Exception as e:
        st.error(f"Error saat memuat data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- Load data ---
dss, harga_beras, data_hama = load_data()
if dss.empty or 'Tanggal' not in dss.columns:
    st.error("Data DSS gagal dimuat. Cek kembali file CSV atau proses generasi data sintetis.")
    st.stop()

import datetime as dt
from dateutil.relativedelta import relativedelta

# --- Sidebar: Pilih Tanggal Tanam ---
st.sidebar.header("🗓️ Pilih Tanggal Tanam")

start_date = dss['Tanggal'].dt.date.min()
end_date = dss['Tanggal'].dt.date.max()

pilih_tanggal = st.sidebar.slider(
    '',
    min_value=start_date,
    max_value=end_date,
    value=start_date,
    format="YYYY-MM-DD"
)

st.sidebar.markdown(f"""
**Tanggal tersedia:**  
🟢 Mulai: `{start_date}`  
🔵 Akhir: `{end_date}`  
""")

# Informasi status rekomendasi
st.sidebar.markdown("---")
st.sidebar.subheader("📍 Status Rekomendasi:")
st.sidebar.markdown("""
- 🌱 **Hijau**: Sangat direkomendasikan untuk tanam
- ⚠️ **Kuning**: Direkomendasikan dengan catatan
- 🔥 **Merah**: Tidak direkomendasikan untuk tanam
""")

# Filter data DSS berdasarkan tanggal yang dipilih
data_pilihan = dss[dss['Tanggal'].dt.date == pilih_tanggal]

with st.container():
    st.subheader("📊 Rekomendasi Waktu Tanam")
    
    if not data_pilihan.empty:
        status = data_pilihan['Label RBS'].values[0]
        total_5 = data_pilihan['Total 5 Hari (mm)'].values[0]
        total_30 = data_pilihan['Total 30 Hari (mm)'].values[0]
        max_dry = data_pilihan['Max Kering 15 Hari'].values[0]

        emoji_status = {'Hijau': '🌱', 'Kuning': '⚠️', 'Merah': '🔥'}
        warna_status = {'hijau': '#e0f7e9', 'kuning': '#fff9e0', 'merah': '#ffe0e0'}

        st.markdown(f"""
            <div style="
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                background-color: {warna_status.get(status.lower(), '#f5f5f5')};
                margin-bottom: 20px;
            ">
                <h3 style="margin: 0;">{emoji_status.get(status, '')} Status: {status}</h3>
            </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Hujan 5 Hari", f"{total_5:.2f} mm")
        with col2:
            st.metric("Total Hujan 30 Hari", f"{total_30:.2f} mm")
        with col3:
            st.metric("Max Hari Kering", f"{max_dry} hari")
        
        if status.lower() == 'hijau':
            st.success("✅ Sangat direkomendasikan untuk tanam. Kondisi curah hujan optimal untuk pertumbuhan awal padi.")
        elif status.lower() == 'kuning':
            st.warning("⚠️ Direkomendasikan dengan catatan. Perhatikan ketersediaan air dan pastikan irigasi tambahan jika diperlukan.")
        else:
            st.error("❌ Tidak direkomendasikan untuk tanam. Kondisi curah hujan tidak mendukung untuk pertumbuhan optimal padi.")
    else:
        st.warning("Tanggal tersebut belum memiliki data rekomendasi DSS.")

# --- Prediksi Curah Hujan 3 Bulan Setelah Tanam ---
with st.container():
    st.subheader("🌧️ Prediksi Curah Hujan Harian (Selama 3 Bulan Setelah Tanam)")

    df_prediksi_cuaca = pd.read_csv('streamlit/hasil_rolling_forecast_2024_2025.csv')
    df_prediksi_cuaca['Tanggal'] = pd.to_datetime(df_prediksi_cuaca['Tanggal'])

    df_90hari = df_prediksi_cuaca[
        (df_prediksi_cuaca['Tanggal'] >= pd.to_datetime(pilih_tanggal)) &
        (df_prediksi_cuaca['Tanggal'] <= pd.to_datetime(pilih_tanggal) + pd.Timedelta(days=90))
    ]

    if not df_90hari.empty:
        import plotly.graph_objects as go
        fig_hujan = go.Figure()
        fig_hujan.add_trace(go.Scatter(
            x=df_90hari['Tanggal'],
            y=df_90hari['Rainfall'],
            mode='lines+markers',
            name='Curah Hujan (mm)'
        ))
        fig_hujan.update_layout(
            xaxis_title='Tanggal',
            yaxis_title='Curah Hujan (mm)',
            height=400
        )
        st.plotly_chart(fig_hujan, use_container_width=True)
    else:
        st.info("Belum tersedia data prediksi cuaca untuk periode ini.")

# --- Prediksi Harga Beras ---
with st.container():
    st.subheader("💰 Prediksi Harga Beras (3 Bulan Setelah Tanam)")
    
    tanggal_mulai_prediksi = pd.to_datetime(pilih_tanggal) + pd.Timedelta(days=90)
    mask_harga = (harga_beras['Tanggal'] >= tanggal_mulai_prediksi) & (harga_beras['Tanggal'] < tanggal_mulai_prediksi + pd.Timedelta(days=30))
    harga_tampil = harga_beras[mask_harga]
    
    if not harga_tampil.empty:
        tanggal_awal = tanggal_mulai_prediksi.strftime("%d %B %Y")
        tanggal_akhir = harga_tampil['Tanggal'].max().strftime("%d %B %Y")
        harga_panen = harga_tampil.iloc[0]['Prediksi Harga Beras (Rp/kg)']
        st.metric("Harga Prediksi Saat Panen", f"Rp {harga_panen:,.2f}")   
    else:
        st.info("Belum ada data prediksi harga beras untuk periode setelah panen.")

# --- Informasi Serangan Hama ---
with st.container():
    st.subheader("🐛 Informasi Serangan Hama")
    
    tab1, tab2 = st.tabs(["Tabel Serangan Hama", "Grafik Serangan Hama"])
    
    with tab1:
        tahun_list = sorted(data_hama['Tahun'].unique(), reverse=True)
        
        for tahun in tahun_list:
            st.markdown(f"### 📅 Musim Tanam {tahun}")
            data_per_tahun = data_hama[data_hama['Tahun'] == tahun][['Jenis hama', 'Luas serangan hama (HA)']]
            data_per_tahun = data_per_tahun.sort_values(by='Luas serangan hama (HA)', ascending=False)
            st.dataframe(data_per_tahun, use_container_width=True, hide_index=True)
    
    with tab2:
        fig = px.bar(
            data_hama, 
            x='Jenis hama', 
            y='Luas serangan hama (HA)', 
            color='Tahun',
            title='Luas Serangan Hama per Jenis',
            barmode='group',
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Total Serangan Hama per Tahun")
        total_per_tahun = data_hama.groupby('Tahun')['Luas serangan hama (HA)'].sum().reset_index()
        
        fig_total = px.bar(
            total_per_tahun,
            x='Tahun',
            y='Luas serangan hama (HA)',
            title='Total Luas Serangan Hama per Tahun',
            color='Tahun',
            height=400
        )
        st.plotly_chart(fig_total, use_container_width=True)

# --- Info untuk petani (accordion) ---
with st.expander("ℹ️ Informasi Tambahan untuk Petani"):
    st.markdown("""
    ### Cara Membaca Rekomendasi DSS
    
    Sistem DSS ini menggunakan model hybrid yang menggabungkan LSTM (Long Short-Term Memory) untuk prediksi curah hujan dengan Rule-Based System untuk menghasilkan rekomendasi waktu tanam.
    
    Rekomendasi dihasilkan berdasarkan sistem penilaian (skor) yang mempertimbangkan 3 parameter utama:
    
    #### Sistem Penilaian
    
    1. **Total Curah Hujan 5 Hari**
       - ≥ 38 mm: Sangat baik (2 poin)
       - 30-37 mm: Cukup baik (1 poin)
       - < 30 mm: Kurang ideal (0 poin)
    
    2. **Maksimum Hari Kering Berturut-turut**
       - ≤ 10 hari: Sangat baik (2 poin) 
       - 11-14 hari: Cukup baik (1 poin)
       - > 14 hari: Kurang ideal (0 poin)
    
    3. **Total Curah Hujan 30 Hari**
       - ≥ 500 mm: Sangat baik (2 poin)
       - 300-499 mm: Cukup baik (1 poin)
       - < 300 mm: Kurang ideal (0 poin)
    
    #### Kategori Rekomendasi
    
    Berdasarkan total skor dari ketiga parameter di atas:
    
    1. **Status Hijau 🌱 (Sangat Direkomendasikan)**
       - Total skor ≥ 5 poin
       - **Artinya:** Kondisi sangat baik untuk memulai tanam padi
    
    2. **Status Kuning ⚠️ (Direkomendasikan dengan Catatan)**
       - Total skor 2-4 poin
       - **Artinya:** Kondisi cukup baik, namun perhatikan ketersediaan air
    
    3. **Status Merah 🔥 (Tidak Direkomendasikan)**
       - Total skor 0-1 poin
       - **Artinya:** Sebaiknya tunda waktu tanam
    
    #### Kasus Khusus
    
    Sistem juga mempertimbangkan situasi khusus. Misalnya, kombinasi curah hujan 5 hari yang mencukupi (≥35 mm), periode maksimum 15 hari kering, dan total curah hujan 30 hari yang memadai (≥350 mm) akan menghasilkan status "Kuning" meskipun skor total mungkin di bawah 2.
    
    ### Informasi Pendukung
    
    - **Prediksi Harga Beras:** Menampilkan perkiraan harga beras 3 bulan setelah tanggal tanam (perkiraan masa panen)
    - **Data Serangan Hama:** Memberikan informasi tentang pola serangan hama berdasarkan data historis
    
    Semua informasi ini bertujuan membantu petani mengoptimalkan waktu tanam untuk meningkatkan hasil produksi padi.
    """)

# --- Footer ---
st.markdown("---")
st.markdown("""
<div style="text-align: center;">
    <p>🌾 Sistem Pendukung Keputusan Waktu Tanam Padi Sumatera Utara</p>
    <p>Dibuat oleh: Retha Novianty Sipayung (NRP: 5026211028)</p>
    <p>Institut Teknologi Sepuluh Nopember</p>
</div>
""", unsafe_allow_html=True)
