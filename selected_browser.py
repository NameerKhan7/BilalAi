"""Accessibility control of the exact browser window handed over by the user.

This uses its existing tab and login. No CDP, cookie extraction, new profile,
model-generated keystrokes, password entry, email sending or deletion.
"""
import re,time
from urllib.parse import urlparse,quote,unquote
from web_reader import validate_url

BROWSERS={'chrome.exe','msedge.exe','brave.exe','firefox.exe','vivaldi.exe','opera.exe','browser.exe'}


class SelectedBrowser:
    def __init__(self,session):self.session=session
    def window(self):
        from window_grants import validate_identity
        identity=getattr(self.session,'bound_target',None)
        if not identity:raise ValueError('Ask the user to hand over the intended browser window first.')
        validate_identity(identity)
        if identity['process'] not in BROWSERS:raise ValueError('This handed-off app is not a supported browser. Select its browser window.')
        return self.session.desktop.window(handle=identity['handle'])
    def focus(self,window,activate=False):
        import win32gui
        self.window()
        if activate:window.set_focus()
        if win32gui.GetForegroundWindow()!=window.handle:raise ValueError('The selected browser is not in focus. No input was sent.')
    def address(self,window):
        self.focus(window,activate=True);window.type_keys('^l',set_foreground=False)
        deadline=time.monotonic()+1
        while time.monotonic()<deadline:
            self.focus(window)
            for field in window.descendants(control_type='Edit'):
                try:
                    if field.element_info.element.CurrentHasKeyboardFocus and not field.element_info.element.CurrentIsPassword:
                        value=field.iface_value.CurrentValue
                        if urlparse(value if '://' in value else 'https://'+value).hostname:
                            return field,value if '://' in value else 'https://'+value
                except Exception:continue
            time.sleep(.05)
        # Never type a URL when the address field cannot be identified.
        window.type_keys('{ESC}',set_foreground=False)
        raise ValueError('The browser address bar is not accessible. Open the intended Gmail tab and select the window again.')
    def navigate(self,url):
        validate_url(url)
        if urlparse(url).hostname!='mail.google.com':raise ValueError('This tool can navigate only to Gmail, not arbitrary destinations.')
        window=self.window();field,_=self.address(window);self.focus(window)
        if not field.element_info.element.CurrentHasKeyboardFocus:raise ValueError('Address-bar focus changed. Navigation was stopped.')
        field.iface_value.SetValue(url)
        if field.iface_value.CurrentValue!=url:raise ValueError('Address-bar readback failed. Navigation was not submitted.')
        self.focus(window)
        if not field.element_info.element.CurrentHasKeyboardFocus:raise ValueError('Address-bar focus changed. Navigation was not submitted.')
        window.type_keys('{ENTER}',set_foreground=False);self.session.invalidate();time.sleep(.4)
    def state(self):
        window=self.window();field,url=self.address(window);self.focus(window);window.type_keys('{ESC}',set_foreground=False)
        items=[];deadline=time.monotonic()+6
        for control in window.descendants():
            if time.monotonic()>deadline or len(items)>=240:break
            try:
                if not control.is_visible() or control.element_info.element.CurrentIsPassword:continue
                name=control.window_text();kind=control.element_info.control_type;value=None
                if kind in {'Edit','ComboBox'}:
                    try:value=control.iface_value.CurrentValue
                    except Exception:pass
                if name or value:items.append({'type':kind,'name':name[:500],'value':value[:1000] if isinstance(value,str) else None})
            except Exception:continue
        return {'ok':True,'verified':True,'url':url,'title':window.window_text(),'items':items,'untrusted_content':True,'scope':'User-selected existing window and current tab; login remains in that browser.'}
    def open_gmail(self):
        before=self.state()
        if urlparse(before['url']).hostname=='mail.google.com':return before
        self.navigate('https://mail.google.com/');after=self.state()
        if urlparse(after['url']).hostname!='mail.google.com':return {'ok':False,'verified':False,'window_request':{'question':'Please sign in to the intended Gmail account yourself, then hand this browser window back to Bilal.'},'reply':'Gmail needs your sign-in. I have not searched your inbox.'}
        return after
    def search_gmail(self,query):
        if not query.strip() or len(query)>400:raise ValueError('Use a mail search query under 400 characters.')
        current=self.state();parsed=urlparse(current['url'])
        # Preserve the observed account index/address; never substitute /u/0.
        account=re.fullmatch(r'/mail/u/([^/]+)/?',parsed.path)
        if parsed.hostname!='mail.google.com' or not account:
            return {'ok':False,'verified':False,'window_request':{'question':'Open Gmail with the correct account in your browser, then hand that window to Bilal.'},'reply':'I need the intended Gmail account open before searching.'}
        target='https://mail.google.com'+parsed.path.rstrip('/')+'/#search/'+quote(query,safe='')
        self.navigate(target);observed=None
        for _ in range(4):
            observed=self.state();actual=urlparse(observed['url'])
            same_account=actual.hostname=='mail.google.com' and actual.path.rstrip('/')==parsed.path.rstrip('/')
            query_visible=any(item['type'] in {'Edit','ComboBox'} and (item.get('value') or '').strip()==query.strip() for item in observed['items'] if 'address' not in item['name'].casefold())
            no_results=any('no conversations found' in item['name'].casefold() or 'no results found' in item['name'].casefold() for item in observed['items'])
            words=set(re.findall(r'\w+',query.casefold()));rows=[item['name'] for item in observed['items'] if item['type'] in {'DataItem','ListItem','Hyperlink','Text'} and words & set(re.findall(r'\w+',item['name'].casefold())) and not item['name'].startswith('http')]
            route_matches=unquote(actual.fragment)=='search/'+query
            if same_account and route_matches and query_visible and (rows or no_results):
                return {'ok':True,'verified':True,'url':observed['url'],'title':observed['title'],'query':query,'visible_matches':rows[:30],'no_results':no_results,'untrusted_content':True,'reply':'Searched the selected Gmail account and observed its results.','note':'These are visible result labels, not full email bodies. Do not claim messages were read in full.'}
            time.sleep(.3)
        return {'ok':False,'verified':False,'url':observed['url'] if observed else target,'error':'Search navigation occurred, but the query and results were not both observable. No email result was claimed.'}
