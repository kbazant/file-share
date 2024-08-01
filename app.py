from flask import Flask, request, render_template, abort
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta

app = Flask(__name__)

# Set the maximum file size to 10 MB (10 * 1024 * 1024 bytes)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# Key Vault and Blob Storage configuration
key_vault_name = "filesharekey"
secret_name = "filesharesecret"
kv_uri = f"https://{key_vault_name}.vault.azure.net"

# Retrieve the connection string from Azure Key Vault
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=kv_uri, credential=credential)
connection_string = secret_client.get_secret(secret_name).value

# Initialize the BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

@app.route('/')
def home():
  return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
  file = request.files['file']
  if file:
      container_name = "fileshare"
      blob_client = blob_service_client.get_blob_client(container=container_name, blob=file.filename)
      blob_client.upload_blob(file)
      
      # Set the expiry time for the SAS token
      expiry_time = datetime.utcnow() + timedelta(hours=1)
      
      sas_token = generate_blob_sas(
          account_name=blob_service_client.account_name,
          container_name=container_name,
          blob_name=file.filename,
          account_key=blob_service_client.credential.account_key,
          permission=BlobSasPermissions(read=True),
          expiry=expiry_time
      )
      sas_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{file.filename}?{sas_token}"
      
      # Format the expiry time for display
      expiry_time_str = expiry_time.strftime('%Y-%m-%d %H:%M:%S UTC')
      
      return render_template('index.html', link=sas_url, expiry_time=expiry_time_str)
  else:
      return render_template('index.html', error="No file selected")

@app.errorhandler(413)
def request_entity_too_large(error):
  return render_template('index.html', error="File is too large. Maximum file size is 10 MB."), 413

if __name__ == '__main__':
  app.run(debug=True)