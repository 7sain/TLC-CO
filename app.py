import streamlit as st
import pandas as pd
import re

# --- Page Setup ---
st.set_page_config(page_title="Gauge Setup Pick List", layout="wide", initial_sidebar_state="expanded")

# --- Enterprise Modern High-Contrast CSS ---
st.markdown("""
    <style>
    /* Main App Background */
    .stApp { background-color: #eaeff4; font-family: 'Inter', -apple-system, sans-serif; }
    
    /* Force high contrast for Headings and Text */
    h1, h2, h3, h4, p, label { color: #0f172a !important; }
    
    /* ----------------------------------- */
    /* Pure White Input Boxes              */
    /* ----------------------------------- */
    
    div[data-baseweb="textarea"] > div {
        background-color: #ffffff !important;
        border: 2px solid #94a3b8 !important;
        border-radius: 8px !important;
    }
    textarea {
        color: #000000 !important;
        font-weight: 500 !important;
        font-size: 1.05em !important;
    }
    
    [data-testid="stFileUploadDropzone"] {
        background-color: #ffffff !important;
        border: 2px dashed #94a3b8 !important;
    }
    
    /* ----------------------------------- */
    /* Metric Cards & UI Elements          */
    /* ----------------------------------- */
    
    [data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 800 !important; color: #0f172a !important; }
    [data-testid="stMetricLabel"] { font-weight: 600 !important; color: #475569 !important; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* Sleek Flexbox List Rows */
    .list-row { 
        display: flex; justify-content: space-between; align-items: center; 
        background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; 
        padding: 12px 20px; margin-bottom: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        border-left: 6px solid #cbd5e1;
    }
    .row-green { border-left-color: #10b981; }
    .row-orange { border-left-color: #f59e0b; }
    .row-blue { border-left-color: #0ea5e9; }
    .row-red { border-left-color: #ef4444; }
    .row-gray { border-left-color: #64748b; background: #f8fafc; } /* Fleet Tracker Row */
    
    /* UI Badges & Tags */
    .badge { padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.5px; }
    .badge-ok { background: #d1fae5; color: #065f46; border: 1px solid #10b981; }
    .badge-warn { background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; }
    .badge-bad { background: #fee2e2; color: #991b1b; border: 1px solid #ef4444; }
    .badge-new { background: #e0f2fe; color: #075985; border: 1px solid #0ea5e9; }
    .badge-fleet { background: #e2e8f0; color: #334155; border: 1px solid #94a3b8; } 
    
    /* Clickable Instrument ID Tag */
    a.id-tag { 
        font-family: 'SFMono-Regular', Consolas, monospace; 
        background: #f8fafc; padding: 4px 8px; border-radius: 4px; 
        font-weight: 700; color: #0f172a; font-size: 0.95em; 
        border: 1px solid #cbd5e1; text-decoration: none; 
        transition: all 0.2s ease-in-out; 
    }
    a.id-tag:hover { background: #e2e8f0; color: #2563eb; border-color: #94a3b8; }
    
    .loc-tag { font-weight: 800; color: #2563eb; font-size: 1.1em; margin-right: 15px; }
    .fleet-tag { font-weight: 800; color: #475569; font-size: 1.1em; margin-right: 15px; }
    .spec-text { color: #64748b; font-size: 0.9em; font-style: italic; margin-left: 8px; }
    
    /* Master Box Recommender */
    .set-box { background: #ffffff; padding: 25px; border-radius: 12px; border-top: 6px solid #3b82f6; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; border-top: 6px solid #3b82f6; }
    .set-box h4 { margin-top: 0; color: #0f172a; font-size: 1.3em; }
    .set-list { list-style: none; padding-left: 0; margin-bottom: 15px; }
    .set-list li { padding: 8px 0; border-bottom: 1px solid #f1f5f9; font-size: 1.05em; color: #1e293b; font-weight: 500; }
    .set-list li:last-child { border-bottom: none; }
    </style>
""", unsafe_allow_html=True)

# --- Core Search Logic (Updated for Fleet Tracking) ---
def find_available_gauges(required_string, search_df, is_local_stock=True):
    if not required_string: return pd.DataFrame()
    req_str = str(required_string)
    rev, pos = None, None
    
    if "Rev " in req_str:
        parts = req_str.split("Rev ")
        rev = parts[1].strip()
        req_str = parts[0].strip() 
    if "Pos " in req_str:
        parts = req_str.split("Pos ")
        pos = parts[1].strip()
        req_str = parts[0].strip()
        
    base_drawing = req_str.strip("- ").strip()
    
    # Base Mask - Drawing must match
    mask = (search_df['Drawing Nº'].astype(str).str.strip() == base_drawing)
    
    # If checking Local Stock, MUST be "Stored". (Owner Fleet ignores this)
    if is_local_stock and 'Logistics Status' in search_df.columns:
        mask = mask & (search_df['Logistics Status'].astype(str).str.strip().str.lower() == 'stored')
    
    if pos is not None and 'Position' in search_df.columns:
        safe_position = search_df['Position'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        mask = mask & (safe_position == str(pos))
        
    if rev is not None and 'Revision Nº' in search_df.columns:
        safe_revision = search_df['Revision Nº'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        if "-" in rev:
            try:
                min_r, max_r = map(int, rev.split("-"))
                numeric_revs = pd.to_numeric(search_df['Revision Nº'], errors='coerce')
                mask = mask & (numeric_revs >= min_r) & (numeric_revs <= max_r)
            except ValueError:
                mask = mask & (safe_revision.str.upper() == rev.upper())
        else:
            if rev.isdigit():
                numeric_revs = pd.to_numeric(search_df['Revision Nº'], errors='coerce')
                mask = mask & (numeric_revs == int(rev))
            else:
                mask = mask & (safe_revision.str.upper() == rev.upper())
                
    return search_df[mask]

# --- Sidebar: Global Settings ---
with st.sidebar:
    st.title("⚙️ QC Settings")
    st.markdown("Set parameters for this specific shipment/setup.")
    job_duration = st.number_input("Expected Job Duration (Days)", min_value=1, value=7, step=1)
    safety_buffer = st.number_input("Required Safety Buffer (Days)", min_value=0, value=3, step=1)
    required_safe_days = job_duration + safety_buffer
    
    st.success(f"**Target QC Limit:** {required_safe_days} Days")

# --- Top Area: The Control Panel ---
st.title("🏭 TLN Confirmed Order Dashboard")

with st.container(border=True):
    c1, c2, c3 = st.columns([1, 1, 1.5])
    
    with c1:
        st.subheader("1. Current Location (xlsx)")
        stock_file = st.file_uploader("Upload Local Stock", type=['xlsx'], label_visibility="collapsed")
        
    with c2:
        st.subheader("2. Owner (xlsx) (Optional)")
        owner_file = st.file_uploader("Upload Owner Excel", type=['xlsx'], label_visibility="collapsed")
    
    with c3:
        st.subheader("3. Catalog Requirements")
        pasted_data = st.text_area("Paste generated report here:", height=120, label_visibility="collapsed")
        
    run_check = st.button("🚀 Analyze Setup Readiness", type="primary", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True) 

# --- Main Logic & Dashboard UI ---
if stock_file and pasted_data and run_check:
    stock_df = pd.read_excel(stock_file)
    owner_df = pd.read_excel(owner_file) if owner_file else None
    
    # Smart Parser
    grouped_requirements = {}
    current_category = "General Setup Requirements"
    for line in pasted_data.split('\n'):
        line = line.strip('\r')
        if not line.strip(): continue 
        columns = [col.strip() for col in line.split('\t') if col.strip()]
        
        if len(columns) == 1 and (":" in columns[0] and "Alternative" not in columns[0]):
            current_category = columns[0].replace(':', '').strip()
            if current_category not in grouped_requirements:
                grouped_requirements[current_category] = []
        elif len(columns) >= 2:
            if current_category not in grouped_requirements:
                grouped_requirements[current_category] = []
            grouped_requirements[current_category].append({"Gauge Name": columns[0], "Required Specs": columns[-1]})
    
    all_required_categories = set(grouped_requirements.keys())
    total_categories = len(all_required_categories)
    
    location_tracker = {} 
    categories_found = 0
    missing_categories_list = []
    
    # Background Mapping Pass (LOCAL SEARCH ONLY)
    for category, items in grouped_requirements.items():
        cat_is_satisfied = False
        for item in items:
            matches = find_available_gauges(item['Required Specs'], stock_df, is_local_stock=True)
            if not matches.empty:
                days_col = pd.to_numeric(matches['Remaining Calendar Days'], errors='coerce').fillna(-1)
                ready_matches = matches[
                    (matches['Calibration Status'].str.strip().str.title() == 'Calibrated') & 
                    ((days_col >= required_safe_days) | (days_col == 0))
                ]
                
                if not ready_matches.empty:
                    cat_is_satisfied = True
                    for _, match_row in ready_matches.iterrows():
                        loc = str(match_row.get('Warehouse Location', 'N/A')).strip()
                        inst_id = str(match_row.get('Instrument ID', 'N/A')).strip()
                        if loc and loc != 'N/A' and loc != 'nan':
                            if loc not in location_tracker:
                                location_tracker[loc] = {'found_gauges': set(), 'satisfied_categories': set()}
                            
                            display_name = f"<strong>{category}:</strong> {item['Gauge Name']} <a href='http://icc.tenaris.net/ICC/Instrument/Details/{inst_id}' target='_blank' class='id-tag'>{inst_id}</a> <span class='spec-text'>({item['Required Specs']})</span>"
                            
                            location_tracker[loc]['found_gauges'].add(display_name)
                            location_tracker[loc]['satisfied_categories'].add(category)
        
        if cat_is_satisfied:
            categories_found += 1
        else:
            missing_categories_list.append(category)

    # --- Readiness Metrics & Progress ---
    readiness_percentage = int((categories_found / total_categories) * 100) if total_categories > 0 else 0
    st.progress(readiness_percentage / 100.0, text=f"Setup Readiness: {readiness_percentage}%")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Required Categories", str(total_categories))
    m2.metric("Categories Ready", str(categories_found))
    m3.metric("Blocked / Missing", str(total_categories - categories_found))
    st.markdown("---")
    
    # --- Tabbed Interface ---
    tab1, tab2, tab3 = st.tabs(["🧰 Master Sets (Fast Track)", "📋 Full Pick List", "⚠️ Blocked & Fleet Tracking"])
    
    with tab1:
        st.subheader("Recommended Master Boxes")
        best_locations = sorted(location_tracker.items(), key=lambda x: len(x[1]['satisfied_categories']), reverse=True)
        found_sets = False
        
        for loc, loc_data in best_locations:
            satisfied_cats = loc_data['satisfied_categories']
            found_gauges = loc_data['found_gauges']
            missing_cats = all_required_categories - satisfied_cats
            
            if len(satisfied_cats) > 1:
                found_sets = True
                gauge_list_html = "".join([f"<li>✅ {g}</li>" for g in found_gauges])
                
                if not missing_cats:
                    missing_html = f"<div style='color:#059669; font-weight:700; margin-top:10px;'>🌟 Complete Set! 100% of requirements inside.</div>"
                else:
                    missing_html = f"<div style='color:#dc2626; font-weight:600; margin-top:10px;'>⚠️ Grab elsewhere: {', '.join(missing_cats)}</div>"

                st.markdown(f"""
                <div class="set-box">
                    <h4>📍 Location: {loc}</h4>
                    <ul class="set-list">{gauge_list_html}</ul>
                    {missing_html}
                </div>
                """, unsafe_allow_html=True)
                
        if not found_sets:
            st.info("No master boxes found containing multiple setup requirements.")
            
    with tab2:
        st.subheader("Detailed Pick List")
        for category, items in grouped_requirements.items():
            st.markdown(f"#### 🎯 {category}")
            for item in items:
                gauge_name = item['Gauge Name']
                matches = find_available_gauges(item['Required Specs'], stock_df, is_local_stock=True)
                
                if not matches.empty:
                    # LOCAL MATCH FOUND
                    for _, match_row in matches.iterrows():
                        loc = str(match_row.get('Warehouse Location', 'N/A'))
                        inst_id = str(match_row.get('Instrument ID', 'N/A'))
                        rev_no = str(match_row.get('Revision Nº', 'N/A'))
                        cal_status = str(match_row.get('Calibration Status', '')).strip().title()
                        
                        try: days_left = int(float(match_row.get('Remaining Calendar Days', -1)))
                        except ValueError: days_left = -1
                        
                        if cal_status == 'Calibrated':
                            if days_left == 0:
                                b_class, r_class, qc_msg = "badge-new", "row-blue", "🆕 Brand New"
                            elif days_left >= required_safe_days:
                                b_class, r_class, qc_msg = "badge-ok", "row-green", f"✅ {days_left} Days"
                            else:
                                b_class, r_class, qc_msg = "badge-warn", "row-orange", f"⚠️ {days_left} Days"
                        else:
                            b_class, r_class, qc_msg = "badge-bad", "row-red", f"❌ {cal_status}"
                        
                        st.markdown(f"""
                        <div class="list-row {r_class}">
                            <div style="flex: 1;">
                                <span class="loc-tag">{loc}</span> 
                                <a href="http://icc.tenaris.net/ICC/Instrument/Details/{inst_id}" target="_blank" class="id-tag">{inst_id}</a>
                            </div>
                            <div style="flex: 2; color: #334155; font-weight: 500;">{gauge_name} (Rev {rev_no})</div>
                            <div style="flex: 1; text-align: right;"><span class="badge {b_class}">{qc_msg}</span></div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    # NOT FOUND LOCALLY - FALLBACK TO Owner SEARCH
                    fleet_match_found = False
                    
                    if owner_df is not None:
                        owner_matches = find_available_gauges(item['Required Specs'], owner_df, is_local_stock=False)
                        if not owner_matches.empty:
                            fleet_match_found = True
                            
                            # THE FIX: Iterate through all fleet matches and display their Instrument IDs
                            for _, fleet_row in owner_matches.iterrows():
                                inst_id = str(fleet_row.get('Instrument ID', 'N/A'))
                                loc = str(fleet_row.get('Workplace Name', 'Unknown Location'))
                                rev_no = str(fleet_row.get('Revision Nº', 'N/A'))
                                
                                st.markdown(f"""
                                <div class="list-row row-gray">
                                    <div style="flex: 1;">
                                        <span class="fleet-tag">🌍 Fleet Match</span>
                                        <a href="http://icc.tenaris.net/ICC/Instrument/Details/{inst_id}" target="_blank" class="id-tag">{inst_id}</a>
                                    </div>
                                    <div style="flex: 2; color: #334155; font-weight: 500;">{gauge_name} (Rev {rev_no})</div>
                                    <div style="flex: 1; text-align: right;"><span class="badge badge-fleet">📍 At: {loc}</span></div>
                                </div>
                                """, unsafe_allow_html=True)

                    if not fleet_match_found:
                        # NOT FOUND ANYWHERE
                        st.markdown(f"""
                        <div class="list-row row-red" style="background: #fff5f5;">
                            <div style="flex: 1;"><span class="loc-tag" style="color:#ef4444;">--</span></div>
                            <div style="flex: 2; color: #ef4444; font-weight: 500;">{gauge_name}</div>
                            <div style="flex: 1; text-align: right;"><span class="badge badge-bad">❌ Not Found</span></div>
                        </div>
                        """, unsafe_allow_html=True)
            st.write("") 

    with tab3:
        st.subheader("Blocked Requirements Investigation")
        if not missing_categories_list:
            st.success("🎉 No blocked items! Your setup is 100% ready to pick locally.")
        else:
            st.error("The following categories are completely missing from your Local Inventory. Global tracking results are below:")
            for cat in missing_categories_list:
                st.markdown(f"#### 🛑 {cat}")
                
                for item in grouped_requirements[cat]:
                    gauge_name = item['Gauge Name']
                    req_specs = item['Required Specs']
                    
                    if owner_df is not None:
                        owner_matches = find_available_gauges(req_specs, owner_df, is_local_stock=False)
                        if not owner_matches.empty:
                            st.markdown(f"**🔍 {gauge_name} is out of the room. Global locations:**")
                            # THE FIX: Iterate to show IDs in Tab 3 as well
                            for _, match_row in owner_matches.iterrows():
                                inst_id = str(match_row.get('Instrument ID', 'N/A'))
                                loc = str(match_row.get('Workplace Name', 'Unknown Location'))
                                st.markdown(f"- 📍 **{loc}** | ID: <a href='http://icc.tenaris.net/ICC/Instrument/Details/{inst_id}' target='_blank' class='id-tag'>{inst_id}</a>", unsafe_allow_html=True)
                        else:
                            st.warning(f"❌ **{gauge_name}** — Not found in Owner.")
                    else:
                        st.markdown(f"**— {gauge_name}** *(Upload Owner Excel in Step 2 to track location)*")
                st.markdown("---")