"""Owned Chrome DOM session. JSON-only worker; no personal profile attachment."""
import json,re,sys,uuid
from pathlib import Path
from urllib.parse import urlparse
from literal_slots import looks_secret

BLOCKED=re.compile(r'\b(send|submit|delete|remove|purchase|buy|pay|publish|post|confirm|authorize|approve|password|sign.?in|log.?in|install|download|upload)\b',re.I)


class DOMSession:
    def __init__(self):self.playwright=None;self.context=None;self.tabs={};self.elements={}
    def start(self):
        if self.context:return
        from playwright.sync_api import sync_playwright
        self.playwright=sync_playwright().start();profile=Path(__file__).resolve().parent/'data/browser-profile'
        self.context=self.playwright.chromium.launch_persistent_context(str(profile),channel='chrome',headless=False,accept_downloads=False,no_viewport=True)
        self.context.set_default_timeout(6000);self.context.set_default_navigation_timeout(15000)
        # No automatic downloads and no routes to local/private services.
        self.context.route('**/*',self.guard_route)
    def guard_route(self,route):
        try:
            self.check(route.request.url)
            route.continue_()
        except Exception:route.abort()
    def page(self,tab_id):
        page=self.tabs.get(tab_id)
        if page is None or page.is_closed():raise ValueError('Unknown tab. List tabs again.')
        self.check(page.url);return page
    def check(self,url):
        from task_store import TaskStore
        from web_reader import validate_url
        host=urlparse(url).hostname
        allowed=TaskStore().setting('allowed_domains',[])
        if not host or host.casefold() not in {x.casefold() for x in allowed}:raise ValueError('Domain is not in Settings → allowed browser domains.')
        validate_url(url)
    def execute(self,name,args):
        if name=='browser_open':self.check(args['url'])
        if name=='browser_tabs' and not self.context:return {'ok':True,'verified':True,'tabs':[]}
        self.start()
        if name=='browser_tabs':
            self.tabs={uuid.uuid4().hex[:12]:page for page in self.context.pages if not page.is_closed()}
            self.elements.clear()
            return {'ok':True,'verified':True,'tabs':[{'tab_id':key,'url':page.url,'title':page.title()} for key,page in self.tabs.items() if page.url!='about:blank']}
        if name=='browser_open':
            self.check(args['url']);page=self.context.new_page();page.goto(args['url'],wait_until='domcontentloaded');self.check(page.url)
            token=uuid.uuid4().hex[:12];self.tabs[token]=page;self.elements.clear()
            return {'ok':True,'verified':True,'tab_id':token,'url':page.url,'title':page.title()}
        page=self.page(args['tab_id'])
        if name=='browser_read':
            self.elements.clear();fields=[]
            for locator in page.locator('input,textarea,button,a,[role="button"],[contenteditable="true"]').all()[:120]:
                if not locator.is_visible():continue
                kind=locator.get_attribute('type') or '';label=locator.get_attribute('aria-label') or locator.get_attribute('placeholder') or locator.inner_text()[:100] or locator.get_attribute('name') or ''
                if kind.casefold() in {'password','file','hidden','submit'} or BLOCKED.search(label):continue
                handle=locator.element_handle()
                if handle is None:continue
                token=uuid.uuid4().hex[:12];self.elements[token]=(page,handle,kind,label,page.url);fields.append({'element_id':token,'label':label,'type':kind})
            text=page.locator('body').inner_text()[:30000]
            if looks_secret(text):raise ValueError('Page appears to contain credentials and cannot enter model context.')
            return {'ok':True,'verified':True,'url':page.url,'text':text,'elements':fields,'untrusted_content':True}
        entry=self.elements.get(args.get('element_id'))
        if not entry or entry[0]!=page:raise ValueError('Stale DOM element. Read the tab again.')
        locator=entry[1];kind=locator.get_attribute('type') or '';label=locator.get_attribute('aria-label') or locator.get_attribute('placeholder') or locator.inner_text()[:100] or locator.get_attribute('name') or ''
        if (kind,label,page.url)!=(entry[2],entry[3],entry[4]):raise ValueError('The observed element changed. Read the tab again.')
        if kind.casefold() in {'password','file','hidden','submit'} or BLOCKED.search(label):raise ValueError('Authentication, submission and destructive DOM actions need dedicated tools.')
        self.elements.clear()
        if name=='browser_fill':
            locator.fill(args['text']);verified=locator.input_value()==args['text']
            return {'ok':verified,'verified':verified,'reply':'Field filled and read back.'}
        if name=='browser_click':
            locator.click();self.check(page.url)
            return {'ok':True,'verified':False,'reply':'Control clicked. Read the page to verify its effect.'}
        raise ValueError('Unknown browser tool.')


def main():
    sys.stdout.reconfigure(encoding='utf-8');session=DOMSession()
    for line in sys.stdin:
        try:
            call=json.loads(line);result=session.execute(call['tool'],call.get('args',{}))
        except Exception as exc:result={'ok':False,'error':str(exc) if isinstance(exc,ValueError) else 'DOM operation failed ('+type(exc).__name__+'). No success was verified.'}
        print(json.dumps(result,ensure_ascii=True),flush=True)


if __name__=='__main__':main()
