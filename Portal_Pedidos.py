import streamlit as st
import pandas as pd
import io
import numpy as np
import pymysql
import logging
from datetime import datetime
import time
import sshtunnel
from sshtunnel import SSHTunnelForwarder
import hmac

##################CONFIGURACAO DE PAGINA##################
st.set_page_config(
    page_title="Portal Pedidos VMSTARK",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded"
)
########################################################

##########VARIAVEIS e FUNCOES SESSION STATE#########
st.subheader("Portal Compras VM")

if 'txtin_pedido_fornecedor' not in st.session_state:
    st.session_state.txtin_pedido_fornecedor = ""
if 'tmp_txtin_pedido' not in st.session_state:
    st.session_state.tmp_txtin_pedido = ""

def clear_text():
    st.session_state.txtin_pedido_fornecedor = st.session_state.tmp_txtin_pedido
    st.session_state.tmp_txtin_pedido = ""

#########################################


###########################START AUTENTICACAO USUARIO######################
def check_password():
    def login_form():
        with st.form("Credentials"):
            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)     
        usuario=st.session_state["username"]     #teste
    def password_entered():
        if st.session_state["username"] in st.secrets[
            "passwords"
        ] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]],
        ):
            st.session_state["password_correct"] = True
            usuario=st.session_state["username"]     
            st.experimental_set_query_params(usuario=usuario) 
            del st.session_state["password"]  # Don't store the username or password.
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False
    if st.session_state.get("password_correct", False):
        return True 
    login_form()
    if "password_correct" in st.session_state:
        st.error("😕 Usuário ou Senha Incorreto")
    return False
if not check_password():
    st.stop()
###########################END AUTENTICACAO USUARIO######################


###########################START MYSQL|SSH FUNCTIONS##################################

#credentials
ssh_host = 'ssh.pythonanywhere.com'
ssh_username = 'vmstark'
ssh_password = 'vmstark10!'
database_username = 'vmstark'
database_password = 'mandrake10!'
database_name = 'vmstark$default'
localhost = '127.0.0.1'

#open ssh tunnel
def open_ssh_tunnel(verbose=False):
    if verbose:
        sshtunnel.DEFAULT_LOGLEVEL = logging.DEBUG
    global tunnel
    tunnel = SSHTunnelForwarder(
        (ssh_host, 22),
        ssh_username = ssh_username,
        ssh_password = ssh_password,
        remote_bind_address = ('vmstark.mysql.pythonanywhere-services.com', 3306)
    )
    tunnel.start()

#connect mysql via ssh
def mysql_connect():
    global connection
    connection = pymysql.connect(
        host='127.0.0.1',
        user=database_username,
        passwd=database_password,
        db=database_name,
        port=tunnel.local_bind_port
    )

#Run QUERY
def run_query(sql):
    return pd.read_sql_query(sql, connection, index_col=None)
#Disconnect
def mysql_disconnect():
    connection.close()
def close_ssh_tunnel():
    tunnel.close
######################END MYSQL|SSH FUNCTIONS##################################


#########################EXECUTE#######################################
open_ssh_tunnel()
mysql_connect()

parametro=st.experimental_get_query_params()
user=parametro.get("usuario")

###FILTRO DATA
datafull_server=run_query(f'SELECT SUBTIME(current_timestamp, "3:0:0")')
datafull_server=datafull_server.iat[0,0]
data_server=datafull_server.date()
qr_filtro_data= run_query(f'SELECT DISTINCT data FROM tb_orders_out WHERE data <> "{data_server}" ORDER BY data DESC')  
option_data = st.selectbox('Data', (qr_filtro_data),on_change=clear_text)
####

###TABELA DADOS
df = run_query(f'SELECT codigo as SKU, produto as Produto, sum(qty) as Quantidade,indisponivel FROM tb_orders_out where Marca="{user[0]}" and Data="{option_data}" group by data,marca,codigo,produto,indisponivel order by Quantidade DESC')
edited_data_df=st.data_editor(df,width=1000,height=1000,hide_index=True,column_config={"indisponivel": st.column_config.CheckboxColumn("Indisponível?",help="Marcar caso produto esteja indisponível",default=False)})
###


############## REGISTRAR PRODUTOS INDISPONIVEIS
df2=edited_data_df.query(f'indisponivel == "True"')
df3=df2[['SKU']]
cod_list=df3.values.tolist()
cod_clean2=','.join(','.join(l) for l in cod_list)
cod_clean3=" OR ".join(map(lambda x: "({})".format(x), cod_clean2.split(" OR ")))
if len(df3) != 0:
    with connection:
        with connection.cursor() as cursor:
            try:
                sql2=f"UPDATE tb_orders_out SET indisponivel = 'False' WHERE Marca='{user[0]}' and Data='{option_data}'"
                cursor.execute(sql2)
                connection.commit() 
                sql2=f"UPDATE tb_orders_out SET indisponivel = 'True' WHERE Marca='{user[0]}' and Data='{option_data}' and codigo in {cod_clean3}"
                cursor.execute(sql2)
                connection.commit()
            except:
                print("nada")


####DOWNLOAD XLS
            
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    # Write each dataframe to a different worksheet.
    df.to_excel(writer, sheet_name='Sheet1')
    # Close the Pandas Excel writer and output the Excel file to the buffer
    writer.close()
    st.download_button(
        label="Download ⬇️",
        data=buffer,
        file_name=f"pandas_multiple_{option_data}.xlsx",
        mime="application/vnd.ms-excel"
    )
##########

#####INPUT Pedido Fornecedor###
mysql_connect()
qr_pedido_forncedor= run_query(f"SELECT DISTINCT pedido_fornecedor FROM tb_orders_out WHERE Marca='{user[0]}' and Data='{option_data}'")
pedido_registrado=qr_pedido_forncedor.iat[0,0]
if(pedido_registrado!="" and pedido_registrado!="None" and pedido_registrado is not None):
    st.subheader(f'✅:green[Pedido já registrado: {pedido_registrado}]')
st.text_input('Pedido Fornecedor:', key='tmp_txtin_pedido', on_change=clear_text,placeholder="Digite o número do pedido interno e aperte <ENTER>")
txtin_pedido_fornecedor = st.session_state.get('txtin_pedido_fornecedor', '')
if (txtin_pedido_fornecedor !=""):
    with connection:
        with connection.cursor() as cursor:
            sql=f"UPDATE tb_orders_out SET pedido_fornecedor = '{txtin_pedido_fornecedor}' WHERE Marca='{user[0]}' and Data='{option_data}'"
            cursor.execute(sql)
            connection.commit() 
            st.caption(f':green[Pedido Registrado e Enviado: {txtin_pedido_fornecedor}]')
            st.write(user[0])
            st.write(option_data)

