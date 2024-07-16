import streamlit as st
import pandas as pd
import io
from datetime import datetime
import dropbox
import os

# Configuración de la página
st.set_page_config(page_title="Fichajes-Atlantic Cobalt", layout="wide")

# Definir usuarios y contraseñas válidos
valid_users = {"pedro": "pedro123", "user": "user123"}

# Función para verificar el inicio de sesión
def check_login(username, password):
    if username in valid_users and valid_users[username] == password:
        return True
    return False

# Función para mostrar la pantalla de inicio de sesión
def login_screen():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if check_login(username, password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
        else:
            st.error("Incorrect username or password")

# Función para mostrar la aplicación principal
def main_app():
    # Título de la aplicación
    
    st.sidebar.image('data/logoACAG.png', use_column_width=True)
    st.sidebar.header('Gestiones')
    # Obtener el token de acceso desde los secretos de Streamlit

    menu = st.sidebar.radio("Ir a", ["Resumen", "Cambiar día","Boarding-pass"])

    path = 'data/bbdd.xlsx'
    df = pd.read_excel(path)

    # Contenido para Opción 1
    if menu == "Resumen":
        # Crear la tabla dinámica (pivot table)
        pivot = pd.pivot_table(df, index=['Pais Real','Estado'], columns='Jornada en Suiza', values='Ciudad Real', aggfunc='count')
        pivot['Festivo'].fillna(0,inplace=True)
        pivot['Laborable'].fillna(0,inplace=True)
        pivot["Total_general"] = pivot['Festivo'] + pivot['Laborable']

        # Calcular la suma por país
        suma_por_pais = pivot.groupby('Pais Real').sum().reset_index()
        suma_por_pais['Estado'] = suma_por_pais['Pais Real']
        suma_por_pais.set_index(['Pais Real', 'Estado'], inplace=True)

        # Concatenar las filas originales con las sumas por país
        df_final = pd.concat([pivot, suma_por_pais]).sort_index(level=['Pais Real', 'Estado'], ascending=[True, False])

        # Reemplazar los valores NaN en la columna 'Estado' por cadenas vacías
        df_final.reset_index(inplace=True)
        df_final['Estado'].fillna('', inplace=True)

        # Reordenar la columna 'Pais Real'
        order = ['España', 'Suiza', 'Pendiente']
        df_final['Pais Real'] = pd.Categorical(df_final['Pais Real'], categories=order, ordered=True)
        df_final.sort_values(by=['Pais Real', 'Estado'], inplace=True)

        # Eliminar la columna 'Pais Real'
        #df_final = df_final.drop(columns=['Pais Real'])

        # Reordenar las columnas
        #df_final = df_final[['Estado', 'Festivo', 'Laborable', 'Total_general']]
        

        sorted_df = pd.concat([
            df_final[(df_final['Estado'] == 'España') & (df_final['Pais Real'] == 'España')],
            df_final[((df_final['Estado'] == 'Programado') | (df_final['Estado'] == 'Real igual programado')| (df_final['Estado'] == 'Real distinto programado')) & (df_final['Pais Real'] == 'España')],
            df_final[df_final['Estado'] == 'Suiza'],
            df_final[((df_final['Estado'] == 'Programado') | (df_final['Estado'] == 'Real igual programado')| (df_final['Estado'] == 'Real distinto programado')) & (df_final['Pais Real'] != 'España')]
        ])
        
        sorted_df.loc[sorted_df['Pais Real'] == 'Pendiente', 'Estado'] = 'Pendiente'
        
        # Función para aplicar estilos
        def highlight_rows(s):
            if s.Estado in ['España', 'Suiza','Pendiente']:
                return ['background-color: lightblue; font-weight: bold']*len(s)
            else:
                return ['']*len(s)

        # Aplicar estilos al dataframe
        styled_df=sorted_df.round(0)
        styled_df = sorted_df.style.format({"Festivo": "{:.0f}", "Laborable": "{:.0f}", "Total_general": "{:.0f}"}).apply(highlight_rows, axis=1)
        
        
        
        st.title("Resumen días")
        st.table(styled_df)
    
    # Contenido para Opción 2
    elif menu == "Cambiar día":

        # Leer el archivo Excel
        file_path = path
        df = pd.read_excel(file_path)
        df.set_index('Fecha', inplace=True)

        st.title('Modificar DataFrame por Fecha')

        # Mostrar el DataFrame
        st.write('DataFrame original:')
        st.dataframe(df)

        # Seleccionar la fecha para modificar
        fecha_seleccionada = st.date_input('Seleccione una fecha para modificar:', value=pd.to_datetime('2024-01-01'))

        # Convertir la fecha seleccionada a tipo datetime
        fecha_seleccionada = pd.to_datetime(fecha_seleccionada)

        # Encontrar la fila con la fecha seleccionada
        if fecha_seleccionada in df.index:
            fila_a_modificar = df.loc[fecha_seleccionada]

            st.write('Fila seleccionada para modificar:')
            st.write(fila_a_modificar)

            # Input para nuevos valores
            nuevo_jornada = st.selectbox('Nuevo Jornada en Suiza', ['Laborable', 'Festivo'], index=0 if fila_a_modificar['Jornada en Suiza'] == 'Laborable' else 1)
            nueva_ciudad_prog = st.text_input('Nueva Ciudad Prog', value=fila_a_modificar['Ciudad Prog'])
            nuevo_pais_prog = st.text_input('Nuevo Pais Prog', value=fila_a_modificar['Pais Prog'])
            nuevo_estado = st.selectbox('Nuevo Estado', ['Real igual programado', 'Programado', 'Real distinto programado'], 
                                index=['Real igual programado', 'Programado', 'Real distinto programado'].index(fila_a_modificar['Estado']))
            nueva_ciudad_real = st.text_input('Nueva Ciudad Real', value=fila_a_modificar['Ciudad Real'])
            nuevo_pais_real = st.text_input('Nuevo Pais Real', value=fila_a_modificar['Pais Real'])

            if st.button('Actualizar'):
                # Actualizar los valores en el DataFrame directamente
                df.at[fecha_seleccionada, 'Jornada en Suiza'] = nuevo_jornada
                df.at[fecha_seleccionada, 'Ciudad Prog'] = nueva_ciudad_prog
                df.at[fecha_seleccionada, 'Pais Prog'] = nuevo_pais_prog
                df.at[fecha_seleccionada, 'Estado'] = nuevo_estado
                df.at[fecha_seleccionada, 'Ciudad Real'] = nueva_ciudad_real
                df.at[fecha_seleccionada, 'Pais Real'] = nuevo_pais_real

                # Guardar los cambios en el archivo Excel
                df.to_excel(file_path, engine='openpyxl')

                st.write('DataFrame actualizado y guardado en el archivo Excel:')
                st.dataframe(df)
        else:
            st.write('No se encontró ninguna fila con la fecha seleccionada.')
            



    elif menu == "Boarding-pass":
        
        if "DROPBOX_ACCESS_TOKEN" in st.secrets:
            ACCESS_TOKEN = st.secrets["DROPBOX_ACCESS_TOKEN"]
        else:
            st.error("El token de acceso de Dropbox no está configurado.")
            st.stop()

        # Función para autenticar en Dropbox

        # Función para obtener un enlace compartido existente o crear uno nuevo
        def get_shared_link(dbx, file_path):
            try:
                # Verificar si ya existe un enlace compartido
                shared_links = dbx.sharing_list_shared_links(path=file_path, direct_only=True)
                if shared_links.links:
                    return shared_links.links[0].url
                else:
                    # Crear un nuevo enlace compartido
                    shared_link_metadata = dbx.sharing_create_shared_link_with_settings(file_path)
                    return shared_link_metadata.url
            except dropbox.exceptions.ApiError as err:
                st.error(f"Error al obtener/crear el enlace compartido: {err}")
                return None

        # Función para subir archivo a Dropbox
        def upload_to_dropbox(dbx, file_content, filename, folder_path):
            dropbox_path = f"{folder_path}/{filename}"
            dbx.files_upload(file_content, dropbox_path, mode=dropbox.files.WriteMode("overwrite"))
            return get_shared_link(dbx, dropbox_path)

        # Función para descargar archivo de Dropbox
        def download_from_dropbox(dbx, filename, folder_path):
            dropbox_path = f"{folder_path}/{filename}"
            _, res = dbx.files_download(dropbox_path)
            return res.content

        # Función para generar enlace de descarga
        def generar_link_de_descarga(shared_url, filename):
            return f'<a href="{shared_url}" download="{filename}">Descargar {filename}</a>'

        # Carpeta de Dropbox donde se guardarán los archivos
        folder_path = "/AM56_B839DeJ0UxF27XT3RQ"  # Esta es la parte final de tu carpeta compartida
        excel_file = "registro_archivos.xlsx"

        # Inicializa o carga el dataframe
        dbx = dropbox.Dropbox(ACCESS_TOKEN)
        try:
            excel_content = download_from_dropbox(dbx, excel_file, folder_path)
            dataframe = pd.read_excel(io.BytesIO(excel_content))
        except dropbox.exceptions.ApiError as e:
            dataframe = pd.DataFrame(columns=['Fecha de Subida', 'Fecha del Viaje', 'Nombre del Archivo', 'Enlace de Descarga'])

        st.session_state['dataframe'] = dataframe

        st.title("Visor y Registro de PDFs en Streamlit")


        st.write("Registro de archivos subidos:")
        st.write(st.session_state['dataframe'].to_html(escape=False, index=False), unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Cargar un archivo PDF", type="pdf")
        fecha_viaje = st.date_input("Fecha del Viaje")
       # Mostrar el dataframe con enlaces de descarga
        
        if uploaded_file is not None and fecha_viaje is not None:
            # Registrar información del archivo subido
            fecha_subida = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            nombre_archivo = uploaded_file.name
            fecha_viaje_str = fecha_viaje.strftime("%Y-%m-%d")
            
            # Convertir el archivo subido a un formato manejable
            pdf_file_content = uploaded_file.getvalue()

            # Subir el archivo a Dropbox
            shared_url = upload_to_dropbox(dbx, pdf_file_content, nombre_archivo, folder_path)

            if shared_url:
                # Generar enlace de descarga
                link_descarga = generar_link_de_descarga(shared_url, nombre_archivo)

                # Añadir la información al dataframe
                nuevo_registro = pd.DataFrame([[fecha_subida, fecha_viaje_str, nombre_archivo, link_descarga]], 
                                            columns=['Fecha de Subida', 'Fecha del Viaje', 'Nombre del Archivo', 'Enlace de Descarga'])
                st.session_state['dataframe'] = pd.concat([st.session_state['dataframe'], nuevo_registro], ignore_index=True)

                # Guardar el dataframe en un archivo Excel en Dropbox
                with io.BytesIO() as output:
                    st.session_state['dataframe'].to_excel(output, index=False)
                    output.seek(0)
                    upload_to_dropbox(dbx, output.read(), excel_file, folder_path)

 

    
    if st.button("Logout"):
        st.session_state["logged_in"] = False

# Configurar la página inicial de Streamlit
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state["logged_in"]:
    main_app()
else:
    login_screen()




