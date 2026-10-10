"""User-driven account setup; not run by the model or unattended startup."""
import argparse,getpass,json
from pathlib import Path
from secret_store import save_secret
def main():
    parser=argparse.ArgumentParser();parser.add_argument('app',choices=['gmail','notion']);parser.add_argument('--client-json',type=Path)
    args=parser.parse_args()
    if args.app=='gmail':
        if not args.client_json or not args.client_json.is_file():parser.error('Provide your Google desktop OAuth client JSON using --client-json.')
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow=InstalledAppFlow.from_client_secrets_file(str(args.client_json),['https://www.googleapis.com/auth/gmail.compose','openid','https://www.googleapis.com/auth/userinfo.email'])
        credentials=flow.run_local_server(port=0,access_type='offline',prompt='consent')
        from google.auth.transport.requests import AuthorizedSession
        identity=AuthorizedSession(credentials).get('https://openidconnect.googleapis.com/v1/userinfo',timeout=15)
        identity.raise_for_status()
        email=identity.json().get('email')
        if not email:raise RuntimeError('Could not verify the connected Gmail account identity.')
        saved=json.loads(credentials.to_json());saved['bilal_account_email']=email
        save_secret('gmail',saved)
        print('Gmail connected for this Windows user. Sending still requires draft-specific approval.')
    else:
        token=getpass.getpass('Notion integration token (hidden): ').strip()
        if not token:parser.error('An integration token is required.')
        save_secret('notion',{'token':token})
        print('Notion token saved for this Windows user. Share the intended page with the integration.')
if __name__=='__main__':main()
