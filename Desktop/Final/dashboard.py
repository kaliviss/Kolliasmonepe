# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from datetime import timedelta
import os
import base64
import io

st.set_page_config(
    page_title="Logistics BI Dashboard",
    layout="wide"
)

# ------------------------------------------------
# TITLE + LOGO
# ------------------------------------------------

logo_path = os.path.join(os.path.dirname(__file__), "logo.png")

if os.path.exists(logo_path):

    with open(logo_path, "rb") as f:
        logo_bytes = f.read()

    logo_base64 = base64.b64encode(logo_bytes).decode()

    st.markdown(
        f"""
        <div style="text-align: center;">
            <h1>Logistics Business Intelligence Dashboard</h1>
            <img src="data:image/png;base64,{logo_base64}" width="500">
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.title("Logistics Business Intelligence Dashboard")

# ------------------------------------------------
# LOAD DATA
# ------------------------------------------------

def load_data(file):

    df = pd.read_excel(file, sheet_name="Συγκεντρωτικό")

    df.columns = df.columns.str.strip()

    df["ΗΜΕΡΟΜΗΝΙΑ"] = pd.to_datetime(
        df["ΗΜΕΡΟΜΗΝΙΑ"],
        dayfirst=True,
        errors="coerce"
    )

    numeric_cols = [
        "ΣΗΜΕΙΑ",
        "ΚΟΣΤΟΣ",
        "Extra Cost"  
        "Km",
        "EXTRA ΠΑΡΑΔΟΣΕΙΣ",
        "ΚΟΜΙΣΤΡΟ ΣΥΝΕΡΓΑΤΗ",
        "ΚΟΜΙΣΤΡΟ ΣΥΝΟΛΙΚΟ"
    ]

    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["ΜΗΝΑΣ"] = df["ΗΜΕΡΟΜΗΝΙΑ"].dt.month
    df["ΕΤΟΣ"] = df["ΗΜΕΡΟΜΗΝΙΑ"].dt.year

    return df

# ------------------------------------------------
# FILE UPLOAD
# ------------------------------------------------

uploaded_file = st.file_uploader(
    "Ανεβάστε Excel αρχείο",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Ανεβάστε το Excel αρχείο για να ξεκινήσει το dashboard.")
    st.stop()

df = load_data(uploaded_file)

# ------------------------------------------------
# FILTERS
# ------------------------------------------------

st.sidebar.title("Φίλτρα")

companies = st.sidebar.multiselect(
    "Μεταφορική Εταιρεία",
    sorted(df["Μεταφορική Εταιρεία"].dropna().unique())
)

partners = st.sidebar.multiselect(
    "Συνεργάτης",
    sorted(df["ΣΥΝΕΡΓΑΤΗΣ"].dropna().unique())
)

vehicles = st.sidebar.multiselect(
    "Πινακίδα",
    sorted(df["ΑΡ. ΠΙΝΑΚΙΔΑΣ"].dropna().unique())
)

vehicle_types = st.sidebar.multiselect(
    "Τύπος Οχήματος",
    sorted(df["ΤΥΠΟΣ ΟΧΗΜΑΤΟΣ"].dropna().unique())
)

regions = st.sidebar.multiselect(
    "Περιοχή",
    sorted(df["ΠΕΡΙΟΧΗ"].dropna().unique())
)

date_range = st.sidebar.date_input(
    "Ημερομηνίες",
    [df["ΗΜΕΡΟΜΗΝΙΑ"].min(), df["ΗΜΕΡΟΜΗΝΙΑ"].max()]
)

if len(date_range) != 2:
    start_date = df["ΗΜΕΡΟΜΗΝΙΑ"].min()
    end_date = df["ΗΜΕΡΟΜΗΝΙΑ"].max()
else:
    start_date, end_date = date_range

mask = pd.Series(True,index=df.index)

if companies:
    mask &= df["Μεταφορική Εταιρεία"].isin(companies)

if partners:
    mask &= df["ΣΥΝΕΡΓΑΤΗΣ"].isin(partners)

if vehicles:
    mask &= df["ΑΡ. ΠΙΝΑΚΙΔΑΣ"].isin(vehicles)

if vehicle_types:
    mask &= df["ΤΥΠΟΣ ΟΧΗΜΑΤΟΣ"].isin(vehicle_types)

if regions:
    mask &= df["ΠΕΡΙΟΧΗ"].isin(regions)

# FIX
if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = date_range[0]
    end_date = date_range[0]

mask &= (
    (df["ΗΜΕΡΟΜΗΝΙΑ"]>=pd.to_datetime(start_date)) &
    (df["ΗΜΕΡΟΜΗΝΙΑ"]<=pd.to_datetime(end_date))
)

data = df[mask].copy()

# ------------------------------------------------
# RENAME
# ------------------------------------------------

data = data.drop(columns=["ΚΟΜΙΣΤΡΟ ΣΥΝΕΡΓΑΤΗ"],errors="ignore")

data.rename(
    columns={
        "ΚΟΜΙΣΤΡΟ ΣΥΝΟΛΙΚΟ":"ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ",
        "ΚΟΣΤΟΣ":"ΚΟΜΙΣΤΡΟ_ΑΒ"
    },
    inplace=True
)
# ------------------------------------------------
# EXTRA COST CALCULATIONS
# ------------------------------------------------

if "Extra Cost" not in data.columns:
    data["Extra Cost"] = 0

data["ΣΥΝΟΛΙΚΟ_ΚΟΜΙΣΤΡΟ"] = data["ΚΟΜΙΣΤΡΟ_ΑΒ"] + data["Extra Cost"]

# ------------------------------------------------
# KPI
# ------------------------------------------------

total_orders = data["ΑΡ ΕΝΤΟΛΗΣ"].nunique()
total_km = data["Km"].sum()
total_stops = data["ΣΗΜΕΙΑ"].sum()

total_commission_ab = data["ΚΟΜΙΣΤΡΟ_ΑΒ"].sum()
total_extra_cost = data["Extra Cost"].sum()

total_revenue = data["ΣΥΝΟΛΙΚΟ_ΚΟΜΙΣΤΡΟ"].sum()

total_commission_partner = data["ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ"].sum()

profit_est = total_revenue - total_commission_partner

cols = st.columns(7)

cols[0].metric("Εντολές",f"{total_orders:,}")
cols[1].metric("Κόμιστρο Συνεργατών",f"{total_commission_partner:,.0f} €")
cols[2].metric("Κόμιστρο AB",f"{total_commission_ab:,.0f} €")
cols[3].metric("Extra Cost",f"{total_extra_cost:,.0f} €")
cols[4].metric("Συνολικό Κόμιστρο",f"{total_revenue:,.0f} €")
cols[5].metric("Συνολικά Χλμ",f"{total_km:,.0f}")
cols[6].metric("Εκτίμηση Κέρδους",f"{profit_est:,.0f} €")

# ------------------------------------------------
# HELPERS
# ------------------------------------------------

def compute_metrics(df_tab):
    df_tab = df_tab.copy()
    
    # Κέρδος
    if "ΚΟΜΙΣΤΡΟ_ΑΒ" in df_tab.columns and "ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ" in df_tab.columns:
        df_tab["Κέρδος"] = df_tab["ΚΟΜΙΣΤΡΟ_ΑΒ"] - df_tab["ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ"]
    
    # €/Χλμ
    if "Κέρδος" in df_tab.columns and "Km" in df_tab.columns:
        df_tab["€/Χλμ"] = df_tab["Κέρδος"] / df_tab["Km"].replace(0,np.nan)
    
    # €/Σημείο
    if "Κέρδος" in df_tab.columns and "ΣΗΜΕΙΑ" in df_tab.columns:
        df_tab["€/Σημείο"] = df_tab["Κέρδος"] / df_tab["ΣΗΜΕΙΑ"].replace(0,np.nan)
    
    return df_tab

def euro_format(df):

    euro_cols = [
        "ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ",
        "ΚΟΜΙΣΤΡΟ_ΑΒ",
        "€/Χλμ",
        "€/Σημείο",
        "Κέρδος"
    ]

    df = df.copy()

    for c in euro_cols:
        if c in df.columns:
            df[c] = df[c].apply(lambda x: f"{x:,.2f} €" if pd.notnull(x) else "")

    return df

# ------------------------------------------------
# TABS
# ------------------------------------------------

tab_overview, tab_tariff, tab_partners, tab_vehicles, tab_financial, tab_extra, tab_predictive, tab_ai, tab_avg, tab_comparison = st.tabs(
[
    "Επισκόπηση",
    "Tariff Engine",
    "Συνεργάτες",
    "Οχήματα",
    "Οικονομικά",
    "Extra Cost",
    "Predictive AI",
    "AI Έλεγχοι",
    "Μέσοι Όροι",
    "Σύγκριση"
]
)

# ------------------------------------------------
# OVERVIEW
# ------------------------------------------------

with tab_overview:

    st.header("Τάσεις Δραστηριότητας")

    daily = data.groupby("ΗΜΕΡΟΜΗΝΙΑ").agg(
        Εντολές=("ΑΡ ΕΝΤΟΛΗΣ","nunique"),
        Km=("Km","sum"),
        ΣΗΜΕΙΑ=("ΣΗΜΕΙΑ","sum"),
        ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ=("ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ","sum"),
        ΚΟΜΙΣΤΡΟ_ΑΒ=("ΚΟΜΙΣΤΡΟ_ΑΒ","sum")
    ).reset_index()

    daily = compute_metrics(daily)

    c1,c2=st.columns(2)

    with c1:
        st.plotly_chart(px.line(daily,x="ΗΜΕΡΟΜΗΝΙΑ",y="Εντολές"),use_container_width=True)

    with c2:
        st.plotly_chart(px.line(daily,x="ΗΜΕΡΟΜΗΝΙΑ",y="Km"),use_container_width=True)

    c3,c4=st.columns(2)

    with c3:
        st.plotly_chart(px.line(daily,x="ΗΜΕΡΟΜΗΝΙΑ",y="ΣΗΜΕΙΑ"),use_container_width=True)

    with c4:
        st.plotly_chart(px.line(daily,x="ΗΜΕΡΟΜΗΝΙΑ",y="Κέρδος"),use_container_width=True)


    # ------------------------------------------------
    # ADVANCED ANALYTICS (ΝΕΑ ΓΡΑΦΗΜΑΤΑ)
    # ------------------------------------------------

    st.markdown("### Advanced Analytics")

    daily["Stops_per_Order"] = daily["ΣΗΜΕΙΑ"] / daily["Εντολές"].replace(0,np.nan)
    daily["Km_per_Order"] = daily["Km"] / daily["Εντολές"].replace(0,np.nan)

    c5,c6 = st.columns(2)

    with c5:
        fig = px.line(daily,x="ΗΜΕΡΟΜΗΝΙΑ",y="Stops_per_Order",
        title="Stops ανά Εντολή")
        st.plotly_chart(fig,use_container_width=True)

    with c6:
        fig = px.line(daily,x="ΗΜΕΡΟΜΗΝΙΑ",y="Km_per_Order",
        title="Km ανά Εντολή")
        st.plotly_chart(fig,use_container_width=True)

    c7,c8 = st.columns(2)

    with c7:
        fig = px.line(daily,x="ΗΜΕΡΟΜΗΝΙΑ",y="€/Χλμ",
        title="Κέρδος ανά Km")
        st.plotly_chart(fig,use_container_width=True)

    with c8:
        fig = px.line(daily,x="ΗΜΕΡΟΜΗΝΙΑ",y="€/Σημείο",
        title="Κέρδος ανά Σημείο")
        st.plotly_chart(fig,use_container_width=True)

    daily["Cumulative_Profit"] = daily["Κέρδος"].cumsum()

    fig = px.area(
        daily,
        x="ΗΜΕΡΟΜΗΝΙΑ",
        y="Cumulative_Profit",
        title="Συσσωρευμένο Κέρδος"
    )

    st.plotly_chart(fig,use_container_width=True)


    partner_orders = data.groupby("ΣΥΝΕΡΓΑΤΗΣ")["ΑΡ ΕΝΤΟΛΗΣ"].nunique().reset_index()

    fig = px.bar(
        partner_orders,
        x="ΣΥΝΕΡΓΑΤΗΣ",
        y="ΑΡ ΕΝΤΟΛΗΣ",
        title="Εντολές ανά Συνεργάτη"
    )

    st.plotly_chart(fig,use_container_width=True)


    vehicle_orders = data.groupby("ΑΡ. ΠΙΝΑΚΙΔΑΣ")["ΑΡ ΕΝΤΟΛΗΣ"].nunique().reset_index()

    fig = px.bar(
        vehicle_orders,
        x="ΑΡ. ΠΙΝΑΚΙΔΑΣ",
        y="ΑΡ ΕΝΤΟΛΗΣ",
        title="Εντολές ανά Όχημα"
    )

    st.plotly_chart(fig,use_container_width=True)


    vehicle_type = data.groupby("ΤΥΠΟΣ ΟΧΗΜΑΤΟΣ")["ΑΡ ΕΝΤΟΛΗΣ"].nunique().reset_index()

    fig = px.pie(
        vehicle_type,
        names="ΤΥΠΟΣ ΟΧΗΜΑΤΟΣ",
        values="ΑΡ ΕΝΤΟΛΗΣ",
        title="Κατανομή Εντολών ανά Τύπο Οχήματος"
    )

    st.plotly_chart(fig,use_container_width=True)


    monthly = data.groupby(["ΕΤΟΣ","ΜΗΝΑΣ"])["ΑΡ ΕΝΤΟΛΗΣ"].nunique().reset_index()

    monthly["date"] = pd.to_datetime(
        monthly["ΕΤΟΣ"].astype(str)+"-"+monthly["ΜΗΝΑΣ"].astype(str)+"-01"
    )

    fig = px.line(
        monthly,
        x="date",
        y="ΑΡ ΕΝΤΟΛΗΣ",
        title="Μηνιαία Τάση Εντολών"
    )

    st.plotly_chart(fig,use_container_width=True)

# ------------------------------------------------
# PARTNERS
# ------------------------------------------------

with tab_partners:
    partner_stats = data.groupby("ΣΥΝΕΡΓΑΤΗΣ").agg(
        Εντολές=("ΑΡ ΕΝΤΟΛΗΣ","nunique"),
        Km=("Km","sum"),
        ΣΗΜΕΙΑ=("ΣΗΜΕΙΑ","sum"),
        ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ=("ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ","sum"),
        ΚΟΜΙΣΤΡΟ_ΑΒ=("ΚΟΜΙΣΤΡΟ_ΑΒ","sum")
    ).reset_index()

    partner_stats = compute_metrics(partner_stats)

    # Υπολογισμός Συμμετοχής %
    total_profit = partner_stats["Κέρδος"].sum()
    partner_stats["Συμμετοχή %"] = partner_stats["Κέρδος"] / total_profit * 100
    partner_stats["Συμμετοχή %"] = partner_stats["Συμμετοχή %"].apply(lambda x: f"{x:.2f}%")

    # Υπολογισμός Efficiency Οχήματος
    partner_stats["Efficiency Οχήματος"] = partner_stats["Km"] / partner_stats["ΣΗΜΕΙΑ"].replace(0, np.nan)
    partner_stats["Efficiency Οχήματος"] = partner_stats["Efficiency Οχήματος"].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")

    # Εμφάνιση
    st.dataframe(euro_format(partner_stats))    
    st.info("""
### 📊 % Συμμετοχή στο Κέρδος
- **Τι είναι:** Το ποσοστό του συνολικού κέρδους που δημιουργεί κάθε συνεργάτης  
- **Πώς ορίζεται:** Κέρδος συνεργάτη ÷ Συνολικό κέρδος εταιρείας  
- **Γιατί είναι χρήσιμο:** Δείχνει ποιοι συνεργάτες φέρνουν μεγαλύτερη αξία, αποκαλύπτει εξάρτηση από λίγους συνεργάτες, βοηθά στη διαπραγμάτευση συμβολαίων
""")
    st.info("""
### 💰 Δείκτες Κερδοφορίας
- **€/Χλμ:** Κέρδος ανά χιλιόμετρο  
- **€/Σημείο:** Κέρδος ανά σημείο παράδοσης  
- **Γιατί είναι χρήσιμο:** Βοηθά στην τιμολόγηση, δείχνει τις πιο κερδοφόρες περιοχές, υποστηρίζει στρατηγικό σχεδιασμό
""")
    st.info("""
### 🚚 Efficiency Οχήματος
- **Τι είναι:** Πόσα χιλιόμετρα κάνει το όχημα ανά σημείο παράδοσης  
- **Πώς ορίζεται:** Χιλιόμετρα ÷ Σημεία  
- **Γιατί είναι χρήσιμο:** Εντοπίζει κακό routing, μειώνει κόστος καυσίμων, βελτιστοποιεί δρομολόγια
""")

# ------------------------------------------------
# VEHICLES
# ------------------------------------------------

with tab_vehicles:

    vehicle_stats = data.groupby("ΑΡ. ΠΙΝΑΚΙΔΑΣ").agg(
        Εντολές=("ΑΡ ΕΝΤΟΛΗΣ","nunique"),
        Km=("Km","sum"),
        ΣΗΜΕΙΑ=("ΣΗΜΕΙΑ","sum"),
        ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ=("ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ","sum"),
        ΚΟΜΙΣΤΡΟ_ΑΒ=("ΚΟΜΙΣΤΡΟ_ΑΒ","sum")
    ).reset_index()

    vehicle_stats = compute_metrics(vehicle_stats)

    st.dataframe(euro_format(vehicle_stats))

# ------------------------------------------------
# FINANCIAL
# ------------------------------------------------

with tab_financial:

    region_stats = data.groupby("ΠΕΡΙΟΧΗ").agg(
        Εντολές=("ΑΡ ΕΝΤΟΛΗΣ","nunique"),
        ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ=("ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ","sum"),
        ΚΟΜΙΣΤΡΟ_ΑΒ=("ΚΟΜΙΣΤΡΟ_ΑΒ","sum")
    ).reset_index()

    region_stats = compute_metrics(region_stats)

    st.dataframe(euro_format(region_stats))
# ------------------------------------------------
# TARIFF ENGINE
# ------------------------------------------------

with tab_tariff:

    st.header("Tariff Lookup")

    col1,col2,col3 = st.columns(3)

    region = col1.selectbox(
        "Περιοχή",
        sorted(data["ΠΕΡΙΟΧΗ"].dropna().unique())
    )

    warehouse = col2.selectbox(
        "Αποθήκη",
        sorted(data["ΑΠΟΘΗΚΗ"].dropna().unique())
    )

    vehicle = col3.selectbox(
        "Τύπος Οχήματος",
        sorted(data["ΤΥΠΟΣ ΟΧΗΜΑΤΟΣ"].dropna().unique())
    )

    result = data[
        (data["ΠΕΡΙΟΧΗ"]==region) &
        (data["ΑΠΟΘΗΚΗ"]==warehouse) &
        (data["ΤΥΠΟΣ ΟΧΗΜΑΤΟΣ"]==vehicle)
    ]

    if len(result)>0:

        row = result.iloc[0]

        c1,c2,c3,c4 = st.columns(4)

        c1.metric("Κόστος AB",f"{row['ΚΟΜΙΣΤΡΟ_ΑΒ']:,.2f} €")
        c2.metric("Extra Cost",f"{row['Extra Cost']:,.2f} €")
        c3.metric("Κόμιστρο Συνεργάτη",f"{row['ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ']:,.2f} €")
        c4.metric("Συνολικό Κόμιστρο", f"{row['ΣΥΝΟΛΙΚΟ_ΚΟΜΙΣΤΡΟ']:,.2f} €")

    else:

        st.warning("Δεν βρέθηκε δρομολόγιο")

    st.markdown("---")

    st.header("Tariff Matrix")

    matrix = data.pivot_table(
        values="ΣΥΝΟΛΙΚΟ_ΚΟΜΙΣΤΡΟ",
        index="ΑΠΟΘΗΚΗ",
        columns="ΠΕΡΙΟΧΗ",
        aggfunc="first"
    )

    st.dataframe(matrix)

# ------------------------------------------------
# EXTRA COST ANALYTICS
# ------------------------------------------------

with tab_extra:

    st.header("Extra Cost Analysis")

    total_extra = data["Extra Cost"].sum()
    avg_extra_route = data["Extra Cost"].mean()

    c1,c2 = st.columns(2)

    c1.metric("Συνολικό Extra Cost", f"{total_extra:,.2f} €")
    c2.metric("Μέσο Extra Cost / Δρομολόγιο", f"{avg_extra_route:,.2f} €")

    st.markdown("### Extra Cost ανά Περιοχή")

    region_extra = data.groupby("ΠΕΡΙΟΧΗ").agg(
        Δρομολόγια=("ΑΡ ΕΝΤΟΛΗΣ","nunique"),
        Extra_Cost=("Extra Cost","sum"),
        ΚΟΜΙΣΤΡΟ_ΑΒ=("ΚΟΜΙΣΤΡΟ_ΑΒ","sum")
    ).reset_index()

    region_extra["Συνολικό Κόμιστρο"] = region_extra["Extra_Cost"] + region_extra["ΚΟΜΙΣΤΡΟ_ΑΒ"]
    region_extra["% Extra Cost"] = (region_extra["Extra_Cost"] / region_extra["Συνολικό Κόμιστρο"]) * 100

    st.dataframe(region_extra)

    fig = px.bar(
        region_extra,
        x="ΠΕΡΙΟΧΗ",
        y="Extra_Cost",
        title="Extra Cost ανά Περιοχή"
    )

    st.plotly_chart(fig,use_container_width=True)

    st.markdown("### Extra Cost ανά Τύπο Οχήματος")

    vehicle_extra = data.groupby("ΤΥΠΟΣ ΟΧΗΜΑΤΟΣ").agg(
        Δρομολόγια=("ΑΡ ΕΝΤΟΛΗΣ","nunique"),
        Extra_Cost=("Extra Cost","sum"),
        Km=("Km","sum")
    ).reset_index()

    vehicle_extra["Extra Cost / Km"] = vehicle_extra["Extra_Cost"] / vehicle_extra["Km"].replace(0,np.nan)

    st.dataframe(vehicle_extra)

    fig = px.pie(
        vehicle_extra,
        names="ΤΥΠΟΣ ΟΧΗΜΑΤΟΣ",
        values="Extra_Cost",
        title="Κατανομή Extra Cost ανά Τύπο Οχήματος"
    )

    st.plotly_chart(fig,use_container_width=True)

    st.markdown("### Extra Cost ανά Συνεργάτη")

    partner_extra = data.groupby("ΣΥΝΕΡΓΑΤΗΣ").agg(
        Δρομολόγια=("ΑΡ ΕΝΤΟΛΗΣ","nunique"),
        Extra_Cost=("Extra Cost","sum"),
        ΚΟΜΙΣΤΡΟ_ΑΒ=("ΚΟΜΙΣΤΡΟ_ΑΒ","sum")
    ).reset_index()

    partner_extra["Συνολικό Κόμιστρο"] = partner_extra["Extra_Cost"] + partner_extra["ΚΟΜΙΣΤΡΟ_ΑΒ"]

    st.dataframe(partner_extra)

    fig = px.bar(
        partner_extra,
        x="ΣΥΝΕΡΓΑΤΗΣ",
        y="Extra_Cost",
        title="Extra Cost ανά Συνεργάτη"
    )

    st.plotly_chart(fig,use_container_width=True)

# ------------------------------------------------
# Σύγκριση Tab
# ------------------------------------------------

with tab_comparison:
    st.header("Σύγκριση Οχημάτων")
    selected_vehicles = st.multiselect(
        "Επιλέξτε αριθμούς κυκλοφορίας για σύγκριση",
        options=sorted(data["ΑΡ. ΠΙΝΑΚΙΔΑΣ"].dropna().unique())
    )
    
    if selected_vehicles:
        comparison_data = data[data["ΑΡ. ΠΙΝΑΚΙΔΑΣ"].isin(selected_vehicles)]
        metrics = comparison_data.groupby("ΑΡ. ΠΙΝΑΚΙΔΑΣ").agg(
            Εντολές=("ΑΡ ΕΝΤΟΛΗΣ", "nunique"),
            Km=("Km", "sum"),
            ΣΗΜΕΙΑ=("ΣΗΜΕΙΑ", "sum"),
            ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ=("ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ", "sum"),
            ΚΟΜΙΣΤΡΟ_ΑΒ=("ΚΟΜΙΣΤΡΟ_ΑΒ", "sum")
        ).reset_index()
        metrics = compute_metrics(metrics)
        st.dataframe(euro_format(metrics))

# ------------------------------------------------
# PREDICTIVE AI
# ------------------------------------------------

with tab_predictive:

    if len(data)>10:

        daily=data.groupby("ΗΜΕΡΟΜΗΝΙΑ").agg(
            ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ=("ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ","sum"),
            ΚΟΜΙΣΤΡΟ_ΑΒ=("ΚΟΜΙΣΤΡΟ_ΑΒ","sum")
        ).reset_index()

        daily["Κέρδος"]=daily["ΚΟΜΙΣΤΡΟ_ΑΒ"]-daily["ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ"]
        daily["t"]=np.arange(len(daily))

        model=RandomForestRegressor(n_estimators=200,random_state=42)
        model.fit(daily[["t"]],daily["Κέρδος"])

        future_days=30

        future_X=pd.DataFrame({
            "t":np.arange(len(daily),len(daily)+future_days)
        })

        forecast=model.predict(future_X)

        future_dates=pd.date_range(
            daily["ΗΜΕΡΟΜΗΝΙΑ"].max()+timedelta(days=1),
            periods=future_days
        )

        fig=go.Figure()

        fig.add_scatter(x=daily["ΗΜΕΡΟΜΗΝΙΑ"],y=daily["Κέρδος"],name="Πραγματικά")
        fig.add_scatter(x=future_dates,y=forecast,name="AI Πρόβλεψη")

        st.plotly_chart(fig,use_container_width=True)

# ------------------------------------------------
# AI CHECKS
# ------------------------------------------------

with tab_ai:

    data["route_efficiency"]=data["Km"]/data["ΣΗΜΕΙΑ"].replace(0,np.nan)

    inefficient=data.sort_values("route_efficiency").head(20)

    st.subheader("Πιθανά μη αποδοτικά δρομολόγια")
    st.dataframe(inefficient)
    st.info("""
**Τι είναι:** Δρομολόγια με πολύ λίγα σημεία για τα διανυθέντα χιλιόμετρα  
**Πώς ορίζεται:** Χιλιόμετρα ÷ Σημεία  
**Γιατί είναι χρήσιμο:** Εντοπίζει κακό routing, μειώνει κόστος καυσίμων, βελτιώνει προγραμματισμό
""")

    features=data[["Km","ΣΗΜΕΙΑ","ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ"]]

    model=IsolationForest(contamination=0.02,random_state=42)

    data["anomaly"]=model.fit_predict(features)

    anomalies=data[data["anomaly"]==-1]

    st.subheader("Περίεργες χρεώσεις συνεργατών")
    st.dataframe(anomalies)
    st.info("""
**Τι είναι:** Δρομολόγια με ασυνήθιστες τιμές κόστους  
**Πώς εντοπίζονται:** AI αλγόριθμος Isolation Forest  
**Γιατί είναι χρήσιμο:** Εντοπίζει λάθη τιμολόγησης, αποκαλύπτει υπερβολικές χρεώσεις, βοηθά στον οικονομικό έλεγχο
""")

# ------------------------------------------------
# AVERAGES TAB
# ------------------------------------------------

with tab_avg:

    st.header("Μέσοι Όροι Δραστηριότητας")

    avg_orders_day = data.groupby("ΗΜΕΡΟΜΗΝΙΑ")["ΑΡ ΕΝΤΟΛΗΣ"].nunique().mean()
    avg_km_day = data.groupby("ΗΜΕΡΟΜΗΝΙΑ")["Km"].sum().mean()
    avg_stops_day = data.groupby("ΗΜΕΡΟΜΗΝΙΑ")["ΣΗΜΕΙΑ"].sum().mean()

    avg_profit_order = (data["ΚΟΜΙΣΤΡΟ_ΑΒ"] - data["ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ"]).mean()

    avg_km_order = data["Km"].sum() / data["ΑΡ ΕΝΤΟΛΗΣ"].nunique()
    avg_stops_order = data["ΣΗΜΕΙΑ"].sum() / data["ΑΡ ΕΝΤΟΛΗΣ"].nunique()

    avg_profit_km = (data["ΚΟΜΙΣΤΡΟ_ΑΒ"].sum() - data["ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ"].sum()) / data["Km"].sum()
    avg_profit_stop = (data["ΚΟΜΙΣΤΡΟ_ΑΒ"].sum() - data["ΚΟΜΙΣΤΡΟ_ΣΥΝΕΡΓΑΤΗ"].sum()) / data["ΣΗΜΕΙΑ"].sum()

    col1,col2,col3,col4 = st.columns(4)

    col1.metric("Μέσες Εντολές / Ημέρα", f"{avg_orders_day:,.2f}")
    col2.metric("Μέσα Χλμ / Ημέρα", f"{avg_km_day:,.2f}")
    col3.metric("Μέσα Σημεία / Ημέρα", f"{avg_stops_day:,.2f}")
    col4.metric("Μέσο Κέρδος / Εντολή", f"{avg_profit_order:,.2f} €")

    col5,col6,col7,col8 = st.columns(4)

    col5.metric("Μέσα Χλμ / Εντολή", f"{avg_km_order:,.2f}")
    col6.metric("Μέσα Σημεία / Εντολή", f"{avg_stops_order:,.2f}")
    col7.metric("Μέσο Κέρδος / Χλμ", f"{avg_profit_km:,.2f} €")
    col8.metric("Μέσο Κέρδος / Σημείο", f"{avg_profit_stop:,.2f} €")

# ------------------------------------------------
# EXPORT
# ------------------------------------------------

st.markdown("---")
st.subheader("Εξαγωγή σε Excel")

excel_buffer = io.BytesIO()

with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
    data.to_excel(writer, index=False, sheet_name='Data')

st.download_button(
    label="💾 Εξαγωγή σε Excel",
    data=excel_buffer.getvalue(),
    file_name="logistics_data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)