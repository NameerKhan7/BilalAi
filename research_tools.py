"""Read-only research services. Searches return data, never browser windows."""
from datetime import date,time as clock_time
import re,json,time,threading,math
from functools import lru_cache
from urllib.parse import urlencode,urlparse
from xml.etree import ElementTree
import requests
from web_reader import validate_url


def public_response(url,params,session=None):
    try:validate_url(url)
    except OSError as exc:raise RuntimeError('Could not resolve the research source. Check the network and retry later.') from exc
    session=session or requests
    deadline=time.monotonic()+25
    response=session.get(url,params=params,timeout=12,allow_redirects=False,stream=True,
        headers={'User-Agent':'BilalAI/0.1 (https://github.com/NameerKhan7/BilalAi)'})
    try:
        if response.status_code!=200:raise RuntimeError(f'Research source returned HTTP {response.status_code}.')
        chunks=[];size=0
        for chunk in response.iter_content(16384):
            if time.monotonic()>deadline:raise RuntimeError('Research request timed out.')
            size+=len(chunk)
            if size>256000:raise RuntimeError('Research response exceeded its size limit.')
            chunks.append(chunk)
        return b''.join(chunks)
    finally:response.close()


def web_search(query,session=None):
    query=query.strip()
    if not query or len(query)>400:raise ValueError('Use a short search query.')
    source='https://www.bing.com/search'
    body=public_response(source,{'q':query,'format':'rss'},session)
    try:root=ElementTree.fromstring(body)
    except ElementTree.ParseError:raise RuntimeError('Search returned a blocked or unreadable page; do not repeat the same query.')
    if root.tag!='rss':raise RuntimeError('Search returned a blocked or unreadable page; do not repeat the same query.')
    results=[]
    for item in root.findall('./channel/item')[:5]:
        url=item.findtext('link','')
        if urlparse(url).scheme not in {'http','https'}:continue
        results.append({'title':item.findtext('title','')[:250],'url':url,'snippet':item.findtext('description','')[:1500]})
    if not results:raise RuntimeError('Search returned no usable results. Do not keep opening browser tabs.')
    return {'ok':True,'query':query,'results':results,'url':source+'?'+urlencode({'q':query,'format':'rss'}),
        'untrusted_content':True,'verified':False,'step_verified':True,'note':'Search retrieval was verified, but snippets are leads, not proof of a date-sensitive fact. Read a relevant source.'}


GEOCODE_LOCK=threading.Lock()
LAST_GEOCODE=0.


def resolve_city(city,country,session=None):
    global LAST_GEOCODE
    params={'city':city,'country':country,'format':'jsonv2','limit':'3','addressdetails':'1','accept-language':'en'}
    with GEOCODE_LOCK:
        if session is None:time.sleep(max(0,1.-(time.monotonic()-LAST_GEOCODE)))
        try:places=json.loads(public_response('https://nominatim.openstreetmap.org/search',params,session))
        finally:LAST_GEOCODE=time.monotonic()
    candidates=[]
    for place in places if isinstance(places,list) else []:
        address=place.get('address',{})
        if country.casefold() not in {address.get('country','').casefold(),address.get('country_code','').casefold()}:continue
        if place.get('addresstype') not in {'city','town','village','municipality','suburb','borough','hamlet'}:continue
        lat=float(place['lat']);lon=float(place['lon'])
        if -90<=lat<=90 and -180<=lon<=180:candidates.append((place,lat,lon))
    if not candidates:raise ValueError('That city/country could not be resolved confidently. Ask for the full city name and country.')
    place,lat,lon=candidates[0]
    if any(abs(other_lat-lat)>.1 or abs(other_lon-lon)>.1 for _,other_lat,other_lon in candidates[1:]):raise ValueError('Several different places match. Ask for the region before giving a time.')
    return {'name':place.get('name',city),'display_name':place.get('display_name',city),'latitude':lat,'longitude':lon,
        'source':'https://www.openstreetmap.org/'+str(place.get('osm_type','node'))+'/'+str(place.get('osm_id','')),
        'attribution':'OpenStreetMap contributors, ODbL'}


@lru_cache(maxsize=64)
def cached_city(city,country):return resolve_city(city,country)


def prayer_times(city,country,day,method='1',session=None):
    city=city.strip();country=country.strip()
    if not city or not country or max(len(city),len(country))>120:raise ValueError('Provide the confirmed city and country.')
    requested=date.fromisoformat(day)
    if not method.isdigit() or not 0<=int(method)<=23:raise ValueError('Use a supported prayer calculation method ID.')
    location=resolve_city(city,country,session) if session is not None else cached_city(city,country)
    source='https://api.aladhan.com/v1/timings/'+requested.strftime('%d-%m-%Y')
    params={'latitude':str(location['latitude']),'longitude':str(location['longitude']),'method':method}
    payload=json.loads(public_response(source,params,session))
    if payload.get('code')!=200 or not isinstance(payload.get('data'),dict):raise RuntimeError('Prayer source could not resolve that city/date.')
    data=payload['data'];actual=data.get('date',{}).get('gregorian',{}).get('date')
    if actual!=requested.strftime('%d-%m-%Y'):raise RuntimeError('Prayer source returned a different date; no time was verified.')
    meta=data.get('meta',{});timings=data.get('timings',{})
    returned_lat=float(meta.get('latitude',999));returned_lon=float(meta.get('longitude',999))
    if not math.isfinite(returned_lat) or not math.isfinite(returned_lon) or abs(returned_lat-location['latitude'])>.02 or abs(returned_lon-location['longitude'])>.02:
        raise RuntimeError('Prayer source returned coordinates for a different place; no time was verified.')
    if str(meta.get('method',{}).get('id'))!=method:raise RuntimeError('Prayer source returned a different calculation method.')
    if not meta.get('timezone') or not re.fullmatch(r'\d{2}:\d{2}(?:\s+.*)?',str(timings.get('Fajr',''))):raise RuntimeError('Prayer source returned incomplete timing data.')
    clock_time.fromisoformat(str(timings['Fajr']).split()[0])
    return {'ok':True,'verified':True,'city_query':city,'country_query':country,'date':day,'timezone':meta['timezone'],
        'method':meta.get('method',{}).get('name',method),'method_id':meta.get('method',{}).get('id'),
        'resolved_location':location,
        'timings':{key:timings.get(key) for key in ['Fajr','Sunrise','Dhuhr','Asr','Maghrib','Isha']},
        'url':source+'?'+urlencode(params),
        'note':'Calculated prayer start times for the resolved city, not a mosque congregation schedule. State the method; confirm an ambiguous city.'}


class ResearchGuard:
    """Bound repeat/research/browser work in code, independent of prompt compliance."""
    def __init__(self):self.seen=set();self.counts={'search':0,'page':0,'browser':0,'prayer':0}
    def check(self,name,args):
        import json
        group={'web_search':'search','read_webpage':'page','browser_search':'browser','open_url':'browser','open_site':'browser','prayer_times':'prayer'}.get(name)
        if not group:return None
        key=(name,json.dumps({k:' '.join(v.casefold().split()) if isinstance(v,str) else v for k,v in args.items()},sort_keys=True))
        if key in self.seen:return 'Repeated lookup/action with no new evidence.'
        self.seen.add(key);self.counts[group]+=1
        if self.counts[group]>{'search':2,'page':3,'browser':2,'prayer':2}[group]:return 'Research/browser budget reached; stop and report the result or blocker.'
        return None
