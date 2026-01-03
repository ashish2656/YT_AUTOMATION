"""
Check which Google account is authenticated and test Drive folder access
"""
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/youtube.upload"
]

def check_account(account_num):
    """Check which Google account is authenticated for a given account number"""
    token_file = f"token_account{account_num}.json"
    
    try:
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        
        # Get Drive service
        drive_service = build("drive", "v3", credentials=creds)
        
        # Get user info
        about = drive_service.about().get(fields="user").execute()
        user_email = about['user'].get('emailAddress', 'Unknown')
        user_name = about['user'].get('displayName', 'Unknown')
        
        print(f"\n{'='*60}")
        print(f"Account {account_num}:")
        print(f"  Email: {user_email}")
        print(f"  Name: {user_name}")
        
        return drive_service, user_email
        
    except Exception as e:
        print(f"\nAccount {account_num}: Error - {e}")
        return None, None

def test_folder_access(drive_service, folder_id, account_num):
    """Test if a folder is accessible"""
    try:
        folder = drive_service.files().get(
            fileId=folder_id,
            fields="id, name, owners, permissions"
        ).execute()
        
        print(f"  ✅ Can access folder: {folder.get('name')}")
        print(f"     Folder ID: {folder_id}")
        
        # Try to list files
        results = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            pageSize=5,
            fields="files(id, name, mimeType)"
        ).execute()
        
        files = results.get('files', [])
        print(f"     Files found: {len(files)}")
        if files:
            print(f"     First file: {files[0].get('name')}")
        
        return True
    except Exception as e:
        print(f"  ❌ Cannot access folder {folder_id}")
        print(f"     Error: {e}")
        return False

if __name__ == "__main__":
    # Check all accounts
    for i in range(1, 6):
        drive_service, email = check_account(i)
        
        # Test folder access for specific accounts
        if i == 2 and drive_service:
            # Test channel_1 folder (should use account2)
            print(f"\n  Testing channel_1 folder access:")
            test_folder_access(drive_service, "1FOhRmS1YCRTLeWJeJtOoet8gcxE_EuGL", i)
    
    print(f"\n{'='*60}")
