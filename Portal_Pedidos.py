import streamlit as st
import pandas as pd
import numpy as np
import pymysql
import logging
import sshtunnel
from sshtunnel import SSHTunnelForwarder

st.title("Primeiro App")

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
    """Open an SSH tunnel and connect using a username and password.
    
    :param verbose: Set to True to show logging
    :return tunnel: Global SSH tunnel connection
    """
    
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
    """Connect to a MySQL server using the SSH tunnel connection
    
    :return connection: Global MySQL database connection
    """
    
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
    return pd.read_sql_query(sql, connection)

#Disconnect
def mysql_disconnect():
    connection.close()
def close_ssh_tunnel():
    tunnel.close

#Execute
open_ssh_tunnel()
mysql_connect()
df = run_query("SELECT * FROM tb_orders_out")
df.head()


###############################################

# Initialize connection.
#conn = st.connection('mysql', type='sql')

# Perform query.
#df = conn.query('SELECT * from mytable;', ttl=600)

# Print results.
for row in df.itertuples():
    st.write(f"{row.marca}")

################################################


mysql_disconnect()
close_ssh_tunnel()  
