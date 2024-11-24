from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from django.shortcuts import render
from .forms import DocumentForm
from django.http import HttpResponse
from datetime import datetime, timedelta, timezone


# Azure Key Vault details
KEY_VAULT_URL = "https://agrostoragekeys.vault.azure.net/"

def get_azure_credentials():
    """Retrieve Azure Blob Storage credentials from Key Vault."""
    try:
        # Authenticate using DefaultAzureCredential
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
        
        # Retrieve secrets
        account_name = secret_client.get_secret("AZUREACCOUNTNAME").value
        account_key = secret_client.get_secret("AZUREACCOUNTKEY").value
        container_name = secret_client.get_secret("AZURECONTAINER").value
        
        return account_name, account_key, container_name
    except Exception as e:
        raise RuntimeError(f"Error retrieving secrets from Key Vault: {str(e)}")

def upload_file(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            
            try:
                # Fetch credentials from Key Vault
                account_name, account_key, container_name = get_azure_credentials()
                
                # Build connection string dynamically
                connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
                blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                
                # Upload file to Azure Blob Storage
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=file.name)
                blob_client.upload_blob(file, overwrite=True)  # Use `overwrite=True` to allow re-uploads

                 # Generate SAS URL for the uploaded file
                sas_url = generate_sas_link(account_name, account_key, container_name, file.name)
                
                # On success, render a success page
                return render(request, 'upload/success.html', {'file_name': file.name, 'sas_url': sas_url})
            except Exception as e:
                # Handle Azure errors (e.g., network issues, invalid credentials)
                return HttpResponse(f"An error occurred: {str(e)}", status=500)
    else:
        form = DocumentForm()

    return render(request, 'upload/upload.html', {'form': form})


def generate_sas_link(account_name, account_key, container_name, blob_name):
    """Generate a SAS link for a given blob."""
    try:
       
        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry = datetime.now(timezone.utc) + timedelta(hours=1)  # Link valid for 1 hour
        )
        
        # Construct the full SAS URL
        sas_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
        
        return sas_url
    except Exception as e:
        raise RuntimeError(f"Error generating SAS token: {str(e)}")