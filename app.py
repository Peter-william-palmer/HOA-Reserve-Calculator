# --- TAB 2: COMPONENTS (Editable & Upload) ---
with tab2:
    st.subheader("Manage Component Inventory")
    
    # --- FILE UPLOADER SECTION ---
    st.markdown("#### 📂 Upload Existing Study")
    uploaded_file = st.file_uploader("Upload a CSV file to automatically populate this table", type=['csv'])
    
    if uploaded_file is not None:
        try:
            # Read CSV
            new_data = pd.read_csv(uploaded_file)
            
            # Simple column mapping to standardize inputs
            col_map = {
                'Component': 'Component Name', 'Item': 'Component Name', 'Name': 'Component Name',
                'Cost': 'Current Cost', 'Replacement Cost': 'Current Cost',
                'UL': 'Useful Life', 'Life': 'Useful Life',
                'RUL': 'Remaining Useful Life', 'Remaining': 'Remaining Useful Life'
            }
            new_data.rename(columns=col_map, inplace=True)
            
            # Check for required columns
            required = ['Component Name', 'Current Cost', 'Useful Life', 'Remaining Useful Life']
            if all(col in new_data.columns for col in required):
                # Ensure numeric types
                new_data['Current Cost'] = pd.to_numeric(new_data['Current Cost'], errors='coerce').fillna(0)
                new_data['Useful Life'] = pd.to_numeric(new_data['Useful Life'], errors='coerce').fillna(0)
                new_data['Remaining Useful Life'] = pd.to_numeric(new_data['Remaining Useful Life'], errors='coerce').fillna(0)
                
                # Update Session State
                st.session_state.component_df = new_data
                st.success("✅ Reserve Study Loaded Successfully! Reloading component list...")
                st.rerun()
            else:
                st.error(f"❌ CSV is missing required columns. It needs: {required}")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.divider()
    
    # --- MANUAL EDIT SECTION ---
    st.markdown("#### ✏️ Manual Edit")
    st.info("Add, edit, or delete rows below. Data saves automatically.")
    
    # Presets Logic (FIXED LINE 186 HERE)
    BOSTON_PRESETS = {
        "Asphalt Roof (Large)": {'Component Name': 'New Asphalt Roof', 'Current Cost': 120000.0, 'Useful Life': 25, 'Remaining Useful Life': 25, 'Notes': 'Boston Avg'},
        "Rubber Roof (Flat)": {'Component Name': 'EPDM Rubber Roof', 'Current Cost': 80000.0, 'Useful Life': 20, 'Remaining Useful Life': 20, 'Notes': 'Boston Avg'},
        "Boiler System": {'Component Name': 'Commercial Boiler', 'Current Cost': 45000.0, 'Useful Life': 25, 'Remaining Useful Life': 15, 'Notes': 'Boston Avg'},
        "Elevator Modernization": {'Component Name': 'Elevator Mod', 'Current Cost': 100000.0, 'Useful Life': 25, 'Remaining Useful Life': 10, 'Notes': 'Hydraulic'},
        "Ext. Painting (Wood)": {'Component Name': 'Full Ext Paint', 'Current Cost': 25000.0, 'Useful Life': 6, 'Remaining Useful Life': 3, 'Notes': 'Cycles fast in NE'},
        "Paving Overlay": {'Component Name': 'Pavement Overlay', 'Current Cost': 35000.0, 'Useful Life': 20, 'Remaining Useful Life': 5, 'Notes': '2 inch overlay'}
    }
    
    col_preset, col_btn = st.columns([3, 1])
    with col_preset:
        preset_option = st.selectbox("Quick Add (2025 Greater Boston Averages)", ["Select..."] + list(BOSTON_PRESETS.keys()))
    with col_btn:
        st.write("") 
        st.write("") 
        if st.button("Add Preset"):
            if preset_option != "Select...":
                new_row = BOSTON_PRESETS[preset_option]
                st.session_state.component_df = pd.concat([st.session_state.component_df, pd.DataFrame([new_row])], ignore_index=True)
                st.rerun()

    # The Editor
    edited_df = st.data_editor(st.session_state.component_df, num_rows="dynamic", use_container_width=True)
    st.session_state.component_df = edited_df
