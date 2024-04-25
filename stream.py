
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import geopandas as gpd
import pydeck as pdk
from sqlalchemy import create_engine, MetaData, Table
import plotly.express as px
import psycopg2
import json



def format_indian_rupees(amount):
    amount_str = str(amount)[::-1]
    groups = [amount_str[i:i+3] for i in range(0, len(amount_str), 3)]
    formatted_amount = ','.join(groups)[::-1]
    return formatted_amount

engine = create_engine('postgresql://postgres:admin@localhost:5432/phonepe_pulse')
metadata = MetaData()

tables = [
    'aggregated_user',
    'aggregated_insurance',
    'aggregated_transaction',
    'map_insurance',
    'map_trans',
    'map_user',
    'top_insurance_district',
    'top_transaction_district',
    'top_user_district',
    'top_insurance_pincode',
    'top_transaction_pincode',
    'top_user_pincode'
]

dfs = {}

for table_name in tables:
    
    your_table = Table(table_name, metadata, autoload_with=engine)
    
    with engine.connect() as connection:
        query = your_table.select()
        result = connection.execute(query)
        data = result.fetchall()
        columns = result.keys()
    
    df = pd.DataFrame(data, columns=columns)
    
    dfs[f"df_{table_name}"] = df

sql_dataframe = tuple(dfs.keys())

st.set_page_config(page_title="Phonepe Data Visualisation",layout='wide')
st.subheader(":violet[Phonepe Pulse| The Beat of Progress]")



tab1, tab2, tab3 = st.tabs(["Insurance", "Transaction","User"])

with tab1:

    
    
    col1, col2, col3 = st.columns([1.5,1.5,1.5],gap='medium')

    col2.subheader(':violet[Policy Details for Filtered Criteria]')

    col1.subheader("Filter for Policy Details")
    col1.write("Note: Select One year & One quarter for better visualization in map")
    year = col1.multiselect("Select the year:", options = dfs['df_aggregated_insurance']['year'].unique(),default = dfs['df_aggregated_insurance']['year'].unique())
    quarter = col1.multiselect("Select the Quarter:", options = dfs['df_aggregated_insurance']['quarter'].unique(),default = dfs['df_aggregated_insurance']['quarter'].unique())
    col1.write('Note: \n 1. Q1 - (Jan - Mar) \n 2. Q2 - (Apr - Jun) \n 3. Q3 - (Jul - Sep) \n 4. Q4 - (Oct - Dec)')
    state = col1.multiselect("Select the State:", options = dfs['df_aggregated_insurance']['state'].unique(), default = dfs['df_aggregated_insurance']['state'].unique())


    ### insurance map visualization

    mydb=psycopg2.connect(host="localhost",user="postgres",password="admin",dbname="phonepe_pulse",port="5432")
    cursor=mydb.cursor()
    cursor.execute('''select aggregated_insurance.state,aggregated_insurance.year,aggregated_insurance.quarter,aggregated_insurance.count,aggregated_insurance.amount,state_loc.latitude,state_loc.longitude from state_loc 
                INNER JOIN aggregated_insurance ON aggregated_insurance.state = state_loc.state ''')
    result = cursor.fetchall()
    columns = ['state', 'year', 'quarter', 'count', 'amount', 'latitude', 'longitude']
    ins_loc = pd.DataFrame(result, columns=columns)
    
    if year and quarter:
        
        map_ins =ins_loc[(ins_loc['year'].isin([i for i in year])) & (ins_loc['quarter'].isin([i for i in quarter])) & (ins_loc['state'].isin([i for i in state]))]
        
        # st.dataframe(map_ins)
        if map_ins.empty:
            st.subheader(":red[Data not available for selected Year / Quarter/ State..Try some other combination]")
        else:
            view = pdk.data_utils.compute_view(map_ins[["longitude", "latitude"]])
            view.pitch = 75
            view.bearing = 60
            view.zoom = 4

            column_layer = pdk.Layer('ColumnLayer',
                                    data=map_ins,
                                    get_position=['longitude', 'latitude'],
                                    get_elevation='count',
                                    elevation_scale=10,
                                    radius=40000,
                                    # get_fill_color=["quarter * 45", "quarter *15", "quarter * 25", 255],
                                    get_fill_color=[255,192,203,255],
                                    pickable=True,
                                    auto_highlight=True)
            tooltip = {
                "html": "State <b>{state}</b> </br> Year <b>{year}</b> </br> Quarter <b>{quarter}</b> </br> Policy Count <b>{count}</b> </br> Premium Amount <b>{amount}</b>",
                "style": {"background": "grey", "color": "white", "font-family": '"Helvetica Neue", Arial', "z-index": "10000"},
            }


            r = pdk.Deck(
                column_layer,
                initial_view_state=view,
                tooltip=tooltip,
                map_provider="mapbox",
                map_style=pdk.map_styles.MAPBOX_DARK,
            )

            st.pydeck_chart(r)

        



    ### Aggregated Insurance Details
    if year and quarter:
        ag_ins_total =dfs['df_aggregated_insurance'][(dfs['df_aggregated_insurance']['year'].isin([i for i in year])) & (dfs['df_aggregated_insurance']['quarter'].isin([i for i in quarter]))]
        ag_ins_state =dfs['df_aggregated_insurance'][(dfs['df_aggregated_insurance']['year'].isin([i for i in year])) & (dfs['df_aggregated_insurance']['quarter'].isin([i for i in quarter]))
                                                        & (dfs['df_aggregated_insurance']['state'].isin([i for i in state]))]
        
        
        col3.subheader(":red[Aggregated Policy Details]")
        col3.subheader(':violet[Total Policy Count :]')
        col3.header(format_indian_rupees(ag_ins_total['count'].sum()))
        col3.subheader(':violet[Total Policy Premium Amount in Rs:]')
        col3.subheader(format_indian_rupees(int(ag_ins_total['amount'].sum())))


        col3.subheader(":red[StateWise Policy Details]")
        col3.write(f"{i}, " for i in state)
        col3.subheader(':violet[StateWise Policy Count :]')
        col3.header(format_indian_rupees(ag_ins_state['count'].sum()))
        col3.subheader(':violet[StateWise Policy Premium Amount in Rs :]')
        col3.header(format_indian_rupees(int(ag_ins_state['amount'].sum())))


        with col2:
            top_10_state = st.checkbox(':green[ States]')
            if top_10_state:

                col2.subheader(':red[Selected Top 10 State ]')
                top_state = ag_ins_state.groupby('state')['amount'].sum().reset_index()
                top_state = top_state.sort_values(by='amount', ascending=False).head(10)
                top_state = top_state.reset_index(drop=True)
                top_state.columns = top_state.columns.str.title()
                top_state['S.No'] = range(1, len(top_state) + 1)
                col2.dataframe(top_state[['S.No', 'State','Amount']], hide_index=True)
              
    ### Aggregated Top District insurance Details
    
    

            if year and quarter:
                ag_ins_total =dfs['df_top_insurance_district'][(dfs['df_top_insurance_district']['year'].isin([i for i in year])) & (dfs['df_top_insurance_district']['quarter'].isin([i for i in quarter]))]
                ag_ins_state =dfs['df_top_insurance_district'][(dfs['df_top_insurance_district']['year'].isin([i for i in year])) & (dfs['df_top_insurance_district']['quarter'].isin([i for i in quarter]))
                                                                & (dfs['df_top_insurance_district']['state'].isin([i for i in state]))]

                top_10_diss = st.checkbox(':green[ District ]')
                if top_10_diss:
                    col2.subheader(':red[Selected Top 10 District ]')
                    state_top = ag_ins_state.groupby('district')['amount'].sum().reset_index()
                    top_10_by_state = state_top.sort_values(by='amount', ascending=False).head(10)
                    top_10_by_state = top_10_by_state.reset_index(drop=True)
                    top_10_by_state.columns = top_10_by_state.columns.str.title()
                    top_10_by_state['S.No'] = range(1, len(top_10_by_state) + 1)
                    col2.dataframe(top_10_by_state[['S.No', 'District','Amount']], hide_index=True)
            ### Aggregated Top pincode insurance Details
            if year and quarter:
                ag_ins_total =dfs['df_top_insurance_pincode'][(dfs['df_top_insurance_pincode']['year'].isin([i for i in year])) & (dfs['df_top_insurance_pincode']['quarter'].isin([i for i in quarter]))]
                ag_ins_state =dfs['df_top_insurance_pincode'][(dfs['df_top_insurance_pincode']['year'].isin([i for i in year])) & (dfs['df_top_insurance_pincode']['quarter'].isin([i for i in quarter]))
                                                            & (dfs['df_top_insurance_pincode']['state'].isin([i for i in state]))]

                pincodes = st.checkbox(':green[ Pincode ]')
                if pincodes:
                    col2.subheader(':red[Selected Top 10 Pincode ]')
                    state_top = ag_ins_state.groupby('pincode')['amount'].sum().reset_index()
                    top_10_by_state = state_top.sort_values(by='amount', ascending=False).head(10)
                    top_10_by_state = top_10_by_state.reset_index(drop=True)
                    top_10_by_state.columns = top_10_by_state.columns.str.title()
                    top_10_by_state['S.No'] = range(1, len(top_10_by_state) + 1)
                    col2.dataframe(top_10_by_state[['S.No', 'Pincode','Amount']],hide_index=True)






#### Transaction Tab
with tab2:
    col1, col2,col3 = st.columns([1.5,1.5,1.5],gap='medium')


    

    col1.subheader('Filter for Transaction Details')
    col1.write("Note: Select One year & One quarter for better visualization in map")
    year = col1.multiselect("Select the year:", options = dfs['df_aggregated_transaction']['year'].unique(),default = dfs['df_aggregated_transaction']['year'].unique())
    quarter = col1.multiselect("Select the Quarter:", options = dfs['df_aggregated_transaction']['quarter'].unique(),default = dfs['df_aggregated_transaction']['quarter'].unique())
    col1.write('Note: \n 1. Q1 - (Jan - Mar) \n 2. Q2 - (Apr - Jun) \n 3. Q3 - (Jul - Sep) \n 4. Q4 - (Oct - Dec)')
    state = col1.multiselect("Select the State:", options = dfs['df_top_transaction_district']['state'].unique(), default = dfs['df_top_transaction_district']['state'].unique())




    if year and quarter:
        ag_trans_total =dfs['df_aggregated_transaction'][(dfs['df_aggregated_transaction']['year'].isin([i for i in year])) & (dfs['df_aggregated_transaction']['quarter'].isin([i for i in quarter]))]
        ag_trans_state =dfs['df_aggregated_transaction'][(dfs['df_aggregated_transaction']['year'].isin([i for i in year])) & (dfs['df_aggregated_transaction']['quarter'].isin([i for i in quarter]))
                                                     & (dfs['df_aggregated_transaction']['state'].isin([i for i in state]))]
        
        
        col2.subheader(':violet[Transaction Categories]')
        trans_cat = ag_trans_total.groupby('transaction_type')['transaction_amount'].sum().reset_index()
        trans_cat = trans_cat.sort_values(by='transaction_amount', ascending=False).head(10)
        trans_cat = trans_cat.reset_index(drop=True)
        trans_cat.columns = trans_cat.columns.str.title()
        col2.dataframe(trans_cat,hide_index=True)
        with col3:
            col3.subheader(':violet[Transaction Details for Filtered Criteria]')
            top_10_state = st.checkbox(':green[State]')
            if top_10_state:
                col3.subheader(':red[Selected Top 10 State]')
                trans_state = ag_trans_state.groupby('state')['transaction_amount'].sum().reset_index()
                trans_state = trans_state.sort_values(by='transaction_amount', ascending=False).head(10)
                trans_state = trans_state.reset_index(drop=True)
                trans_state.columns = trans_state.columns.str.title()
                trans_state['S.No'] = range(1, len(trans_state) + 1)
                col3.dataframe(trans_state[['S.No', 'State','Transaction_Amount']],hide_index=True)

            
        
            if year and quarter:
                trans_dis =dfs['df_top_transaction_district'][(dfs['df_top_transaction_district']['year'].isin([i for i in year])) & (dfs['df_top_transaction_district']['quarter'].isin([i for i in quarter]))]
                trans_state =dfs['df_top_transaction_district'][(dfs['df_top_transaction_district']['year'].isin([i for i in year])) & (dfs['df_top_transaction_district']['quarter'].isin([i for i in quarter]))
                                                        & (dfs['df_top_transaction_district']['state'].isin([i for i in state]))]
                
                top_10_district = st.checkbox(':green[District]')
                if top_10_district:
                    col3.subheader(':red[Selected Top 10 District]')
                    top_dis = trans_state.groupby('district')['amount'].sum().reset_index()
                    top_dis = top_dis.sort_values(by='amount', ascending=False).head(10)
                    top_dis = top_dis.reset_index(drop=True)
                    top_dis.columns = top_dis.columns.str.title()
                    top_dis['S.No'] = range(1, len(top_dis) + 1)
                    col3.dataframe(top_dis[['S.No', 'District', 'Amount']], hide_index=True)

                if year and quarter:
                    if year and quarter:
                        trans_pin =dfs['df_top_transaction_pincode'][(dfs['df_top_transaction_pincode']['year'].isin([i for i in year])) & (dfs['df_top_transaction_pincode']['quarter'].isin([i for i in quarter]))]
                        pin_state =dfs['df_top_transaction_pincode'][(dfs['df_top_transaction_pincode']['year'].isin([i for i in year])) & (dfs['df_top_transaction_pincode']['quarter'].isin([i for i in quarter]))
                                                     & (dfs['df_top_transaction_pincode']['state'].isin([i for i in state]))]
                    
                    top_10_pincode = st.checkbox(':green[Pincode]')
                    if top_10_pincode:                                         
                        col3.subheader(':red[Selected Top 10 Pincode]')
                        
                        top_pin = pin_state.groupby('pincode')['amount'].sum().reset_index()
                        top_pin = top_pin.sort_values(by='amount', ascending=False).head(10)
                        top_pin = top_pin.reset_index(drop=True)
                        top_pin.columns = top_pin.columns.str.title()
                        top_pin['S.No'] = range(1, len(top_pin) + 1)
                        col3.dataframe(top_pin[['S.No', 'Pincode', 'Amount']],hide_index=True)

        ### Transaction map visualization

    mydb=psycopg2.connect(host="localhost",user="postgres",password="admin",dbname="phonepe_pulse",port="5432")
    cursor=mydb.cursor()
    cursor.execute('''select map_trans.state,map_trans.year,map_trans.quarter,map_trans.name,map_trans.count,map_trans.amount,map_insurance.lat,map_insurance.lng from map_insurance 
                INNER JOIN map_trans ON map_trans.new_label = map_insurance.new_label ''')
    result = cursor.fetchall()
    columns = ['state', 'year', 'quarter','district', 'count', 'amount', 'latitude', 'longitude']
    trans_loc = pd.DataFrame(result, columns=columns)


    
    
    if year and quarter:
        
        trans_loc1 =trans_loc[(trans_loc['year'].isin([i for i in year])) & (trans_loc['quarter'].isin([i for i in quarter])) & (trans_loc['state'].isin([i for i in state]))] 
                              
        
        
        if trans_loc1.empty:
            st.subheader(":red[Data not available for selected Year / Quarter / State..Try some other combination]")
        else:
            view = pdk.data_utils.compute_view(trans_loc1[["longitude", "latitude"]])
            view.pitch = 75
            view.bearing = 60
            view.zoom = 4

            column_layer = pdk.Layer('ColumnLayer',
                                    data=trans_loc1,
                                    get_position=['longitude', 'latitude'],
                                    get_elevation='count/10000',
                                    elevation_scale=10,
                                    radius=7000,
                                    # get_fill_color=["quarter * 45", "quarter *15", "quarter * 25", 255],
                                    get_fill_color=[255,192,203,245],
                                    pickable=True,
                                    auto_highlight=True)
            tooltip = {
                "html": "State <b>{state}</b> </br> District <b>{district}</b> </br> Year <b>{year}</b> </br> Quarter <b>{quarter}</b> </br> Transaction Count <b>{count}</b> </br> Transaction Amount <b>{amount}</b>",
                "style": {"background": "grey", "color": "white", "font-family": '"Helvetica Neue", Arial', "z-index": "10000"},
            }


            r = pdk.Deck(
                column_layer,
                initial_view_state=view,
                tooltip=tooltip,
                map_provider="mapbox",
                map_style=pdk.map_styles.MAPBOX_DARK,
            )

            st.pydeck_chart(r)

#### User Tab
with tab3:
    col1,col2,col3,col4= st.columns([1.75,1,1.5,1.7],gap='small')


    col1.subheader('Filter for User Details')
    col1.write("Note: Select One year & One quarter for better visualization in map")
    year = col1.multiselect("Select the year:", options = dfs['df_aggregated_user']['year'].unique(),default = dfs['df_aggregated_user']['year'].unique(),key="year_select")
    quarter = col1.multiselect("Select the Quarter:", options=[1, 2, 3, 4], default=[1, 2, 3, 4], key="quarter_select")
    col1.write('Note: \n 1. Q1 - (Jan - Mar) \n 2. Q2 - (Apr - Jun) \n 3. Q3 - (Jul - Sep) \n 4. Q4 - (Oct - Dec)')
    state = col1.multiselect("Select the State:", options=dfs['df_aggregated_user']['state'].unique(), default=dfs['df_aggregated_user']['state'].unique(), key="state_select")


 ### User map visualization

    mydb=psycopg2.connect(host="localhost",user="postgres",password="admin",dbname="phonepe_pulse",port="5432")
    cursor=mydb.cursor()
    cursor.execute('''select map_user.state, map_user.year, map_user.quarter, map_user.name, map_user.registeredusers,map_user.appopens, map_insurance.lat, map_insurance.lng from map_insurance 
                INNER JOIN map_user ON map_user.new_label = map_insurance.new_label''')
    result = cursor.fetchall()
    columns = ['state', 'year', 'quarter','district', 'users','appopens', 'latitude', 'longitude']
    user_loc = pd.DataFrame(result, columns=columns)
    
    
    if year and quarter:
        
        map_user =user_loc[(user_loc['year'].isin([i for i in year])) & (user_loc['quarter'].isin([i for i in quarter])) & (user_loc['state'].isin([i for i in state]))]

        if map_user.empty:
            st.subheader(":red[Data not available for selected Year / Quarter / State..Try some other combination]")
        else:
            view = pdk.data_utils.compute_view(map_user[["longitude", "latitude"]])
            view.pitch = 75
            view.bearing = 60
            view.zoom = 4

            column_layer = pdk.Layer('ColumnLayer',
                                    data=map_user,
                                    get_position=['longitude', 'latitude'],
                                    get_elevation='users/100',
                                    elevation_scale=10,
                                    radius=7000,
                                    # get_fill_color=["quarter * 45", "quarter *15", "quarter * 25", 255],
                                    get_fill_color=[206, 147, 216,255],
                                    pickable=True,
                                    auto_highlight=True)
            tooltip = {
                "html": "State <b>{state}</b> </br> District <b>{district}</b> </br> Year <b>{year}</b> </br> Quarter <b>{quarter}</b> </br> Registered Users <b>{users}</b></br> App Opens <b>{appopens}</b>",
                "style": {"background": "grey", "color": "white", "font-family": '"Helvetica Neue", Arial', "z-index": "10000"},
            }


            r = pdk.Deck(
                column_layer,
                initial_view_state=view,
                tooltip=tooltip,
                map_provider="mapbox",
                map_style=pdk.map_styles.MAPBOX_DARK,
            )

            st.pydeck_chart(r)

        




    if year and quarter:
        ag_user_total =dfs['df_aggregated_user'][(dfs['df_aggregated_user']['year'].isin([i for i in year])) & (dfs['df_aggregated_user']['quarter'].isin([i for i in quarter]))]
        ag_user_state =dfs['df_aggregated_user'][(dfs['df_aggregated_user']['year'].isin([i for i in year])) & (dfs['df_aggregated_user']['quarter'].isin([i for i in quarter]))
                                                     & (dfs['df_aggregated_user']['state'].isin([i for i in state]))]
        
        

        col2.subheader(':violet[User Device]')
        user_cat = ag_user_state.groupby('brand')['devicecount'].sum().reset_index()
        user_cat = user_cat.sort_values(by='devicecount', ascending=False)
        user_cat = user_cat.reset_index(drop=True)
        user_cat.columns = user_cat.columns.str.title()
        col2.dataframe(user_cat,hide_index=True,height=738)



        with col4:

            col4.subheader(':violet[User Details for Filtered Criteria]')
            state_10 = st.checkbox(':green[States]')
            if year and quarter:
                map_user_total =dfs['df_map_user'][(dfs['df_map_user']['year'].isin([i for i in year])) & (dfs['df_map_user']['quarter'].isin([i for i in quarter]))]
                map_user_state =dfs['df_map_user'][(dfs['df_map_user']['year'].isin([i for i in year])) & (dfs['df_map_user']['quarter'].isin([i for i in quarter]))
                                                     & (dfs['df_map_user']['state'].isin([i for i in state]))]
        

                col3.subheader(':violet[App Opens]')
                user_app = map_user_state.groupby('name')['appopens'].sum().reset_index()
                user_app = user_app.sort_values(by='appopens', ascending=False)
                user_app = user_app.reset_index(drop=True)
                user_app.columns = user_app.columns.str.title()
                col3.dataframe(user_app,hide_index=True,height=738)


                if state_10:
                    col4.subheader(':violet[Selected Top 10 State]')
                    map_state = map_user_state.groupby('state')['registeredusers'].sum().reset_index()
                    map_state = map_state.sort_values(by='registeredusers', ascending=False).head(10)
                    map_state = map_state.reset_index(drop=True)
                    map_state.columns = map_state.columns.str.title()
                    map_state['S.No'] = range(1, len(map_state) + 1)
                    col4.dataframe(map_state[['S.No','State','Registeredusers']],hide_index=True)
            
        
            if year and quarter:
                map_user_total =dfs['df_top_user_district'][(dfs['df_top_user_district']['year'].isin([i for i in year])) & (dfs['df_top_user_district']['quarter'].isin([i for i in quarter]))]
                map_user_state =dfs['df_top_user_district'][(dfs['df_top_user_district']['year'].isin([i for i in year])) & (dfs['df_top_user_district']['quarter'].isin([i for i in quarter]))
                                                     & (dfs['df_top_user_district']['state'].isin([i for i in state]))]
                district_10 = st.checkbox(':green[Districts]')
                if district_10:
                    col4.subheader(':violet[Selected Top 10 Districts]')
                    top_dis = map_user_state.groupby('name')['registeredusers'].sum().reset_index()
                    top_dis = top_dis.sort_values(by='registeredusers', ascending=False).head(10)
                    top_dis = top_dis.reset_index(drop=True)
                    top_dis.columns = top_dis.columns.str.title()
                    top_dis['S.No'] = range(1, len(top_dis) + 1)
                    col4.dataframe(top_dis[['S.No','Name','Registeredusers']], hide_index=True)

                if year and quarter:
                    if year and quarter:
                        trans_pin =dfs['df_top_user_pincode'][(dfs['df_top_user_pincode']['year'].isin([i for i in year])) & (dfs['df_top_user_pincode']['quarter'].isin([i for i in quarter]))]
                        pin_state =dfs['df_top_user_pincode'][(dfs['df_top_user_pincode']['year'].isin([i for i in year])) & (dfs['df_top_user_pincode']['quarter'].isin([i for i in quarter]))
                                                     & (dfs['df_top_user_pincode']['state'].isin([i for i in state]))]
                    
                    top_10_pincode = st.checkbox(':green[Pincodes]')
                    if top_10_pincode:                                         
                        col4.subheader(':violet[Selected Top 10 Pincode]')
                        top_pin = pin_state.groupby('pincode')['registeredusers'].sum().reset_index()
                        top_pin = top_pin.sort_values(by='registeredusers', ascending=False).head(10)
                        top_pin = top_pin.reset_index(drop=True)
                        top_pin.columns = top_pin.columns.str.title()
                        top_pin['S.No'] = range(1, len(top_pin) + 1)
                        col4.dataframe(top_pin[['S.No','Pincode','Registeredusers']], hide_index=True)

