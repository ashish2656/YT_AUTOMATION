import json
from google_auth_oauthlib.flow import InstalledAppFlow

with open('config.json') as f:
    config = json.load(f)

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/drive.readonly'
]

client_config = {
    'installed': {
        'client_id': config['client_id'],
        'client_secret': config['client_secret'],
        'redirect_uris': ['http://localhost:8080/'],
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token'
    }
}

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

print('\n🔐 Generating token for Account 5: ashishdodiya269697@gmail.com')
print('⏳ Browser will open - sign in with ashishdodiya269697@gmail.com...\n')

creds = flow.run_local_server(port=8080)

token_data = {
    'token': creds.token,
    'refresh_token': creds.refresh_token,
    'token_uri': creds.token_uri,
    'client_id': creds.client_id,
    'client_secret': creds.client_secret,
    'scopes': creds.scopes
}

with open('token_account5.json', 'w') as f:
    json.dump(token_data, f, indent=2)

print('✅ Token saved to token_account5.json')
