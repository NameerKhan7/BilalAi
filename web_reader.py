"""Bounded public webpage retrieval. No cookies or private/local-network targets."""
import ipaddress,socket,time
from urllib.parse import urlparse,urljoin
import requests
from bs4 import BeautifulSoup

def validate_url(url):
    parsed=urlparse(url)
    if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use a public HTTP(S) page without embedded credentials.')
    if parsed.port not in {None,80,443}:raise ValueError('Only public web ports are supported.')
    addresses=socket.getaddrinfo(parsed.hostname,parsed.port or (443 if parsed.scheme=='https' else 80),type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError('Private, loopback and local-network pages are not available through this tool.')
    return url
def read_webpage(url,session=None,start=0):
    start=int(start or 0)
    if not 0<=start<=500000:raise ValueError('Invalid page offset.')
    deadline=time.monotonic()+25
    session=session or requests.Session()
    for _ in range(6):
        if time.monotonic()>deadline:raise RuntimeError('Page reading timed out.')
        validate_url(url)
        response=session.get(url,headers={'User-Agent':'BilalAI/0.1'},timeout=12,allow_redirects=False,stream=True)
        if response.status_code in {301,302,303,307,308}:
            location=response.headers.get('Location')
            response.close()
            if not location:raise ValueError('Redirect without a destination.')
            url=urljoin(url,location);continue
        if response.status_code>=400:response.close();raise RuntimeError(f'Page could not be read (HTTP {response.status_code}).')
        kind=response.headers.get('Content-Type','').lower()
        if kind and not any(t in kind for t in ['text/','html','json']):
            response.close();raise ValueError('That resource is not a text webpage.')
        parts=[];size=0
        for chunk in response.iter_content(16384):
            if time.monotonic()>deadline:response.close();raise RuntimeError('Page reading timed out.')
            size+=len(chunk)
            if size>768000:break
            parts.append(chunk)
        response.close()
        soup=BeautifulSoup(b''.join(parts),'html.parser')
        for node in soup(['script','style','noscript','nav','footer','header']):node.decompose()
        title=soup.title.get_text(' ',strip=True) if soup.title else ''
        region=soup.find('main') or soup.find('article') or soup
        text=region.get_text(' ',strip=True)
        lowered=text.casefold()
        if (len(text)<200 and any(hint in lowered for hint in ['trouble accessing google search','enable javascript','unusual traffic','verify you are human'])) or not text:
            return {'ok':False,'url':url,'error':'The source returned a blocked/empty page, not readable evidence. Use another source; do not repeat this page.','untrusted_content':True}
        return {'ok':True,'url':url,'title':title,'text':text[start:start+14000],'start':start,'next_start':str(start+14000) if len(text)>start+14000 else None,
                'truncated':size>768000 or len(text)>start+14000,'untrusted_content':True}
    raise ValueError('Too many redirects.')
