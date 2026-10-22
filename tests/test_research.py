import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from research_tools import ResearchGuard,web_search,prayer_times
from web_reader import read_webpage
from diagnose_task import summarize


def response(body):
    value=Mock(status_code=200,headers={'Content-Type':'text/html'})
    value.iter_content.return_value=[body if isinstance(body,bytes) else json.dumps(body).encode()]
    return value


class ResearchTests(unittest.TestCase):
    def test_search_returns_links_without_a_browser(self):
        session=Mock();session.get.return_value=response(b'<rss><channel><item><title>Example</title><link>https://example.org/source</link><description>Evidence</description></item></channel></rss>')
        with patch('research_tools.validate_url'),patch('subprocess.Popen') as launch:
            result=web_search('example question',session)
        self.assertEqual(result['results'][0]['url'],'https://example.org/source');launch.assert_not_called()
    def test_unreadable_search_is_not_reported_as_success(self):
        session=Mock();session.get.return_value=response(b'<html>access denied</html>')
        with patch('research_tools.validate_url'):
            with self.assertRaisesRegex(RuntimeError,'blocked or unreadable'):web_search('example',session)
    def test_google_access_page_is_not_usable_evidence(self):
        session=Mock();session.get.return_value=response(b'<title>Google Search</title>Google Search If you are having trouble accessing Google Search, please click here.')
        with patch('web_reader.validate_url'):result=read_webpage('https://www.google.com/search?q=test',session)
        self.assertFalse(result['ok']);self.assertIn('blocked',result['error'])
    def prayer_fixture(self,date='23-10-2026',latitude=33.7708):
        places=[{'name':'Wah Cantonment','display_name':'Wah Cantonment, Pakistan','lat':'33.7708','lon':'72.7519',
            'addresstype':'town','address':{'country':'Pakistan','country_code':'pk'},'osm_type':'node','osm_id':1}]
        timings={'code':200,'data':{'date':{'gregorian':{'date':date}},'timings':{'Fajr':'04:57'},
            'meta':{'latitude':latitude,'longitude':72.7519,'timezone':'Asia/Karachi','method':{'id':1,'name':'Karachi'}}}}
        session=Mock();session.get.side_effect=[response(places),response(timings)]
        return session
    def test_prayer_verifies_date_place_method_and_source(self):
        session=self.prayer_fixture()
        with patch('research_tools.validate_url'):result=prayer_times('Wah Cantt','Pakistan','2026-10-23',session=session)
        self.assertTrue(result['verified']);self.assertEqual(result['timings']['Fajr'],'04:57')
        self.assertEqual(result['resolved_location']['name'],'Wah Cantonment')
        self.assertIn('latitude=',result['url']);self.assertIn('not a mosque',result['note'])
    def test_prayer_rejects_wrong_date_or_coordinates(self):
        for session in [self.prayer_fixture(date='22-10-2026'),self.prayer_fixture(latitude=8.8888)]:
            with patch('research_tools.validate_url'):
                with self.assertRaises(RuntimeError):prayer_times('Wah Cantt','Pakistan','2026-10-23',session=session)
    def test_unresolved_city_does_not_fall_back_to_another_city(self):
        session=Mock();session.get.return_value=response([])
        with patch('research_tools.validate_url'):
            with self.assertRaisesRegex(ValueError,'full city'):prayer_times('Wakand','Pakistan','2026-10-23',session=session)
        self.assertEqual(session.get.call_count,1)
    def test_guard_stops_repeats_and_limits_tabs_across_tool_names(self):
        guard=ResearchGuard()
        self.assertIsNone(guard.check('web_search',{'query':'Fajr Wah Cantt'}))
        self.assertIn('Repeated',guard.check('web_search',{'query':' FAJR   WAH CANTT '}))
        for name in ['open_url','browser_search']:self.assertIsNone(guard.check(name,{'query':name}))
        self.assertIn('budget',guard.check('open_site',{'site':'wikipedia'}))
    def test_guard_limits_different_searches_and_page_reads(self):
        guard=ResearchGuard()
        for index in range(2):self.assertIsNone(guard.check('web_search',{'query':str(index)}))
        self.assertIn('budget',guard.check('web_search',{'query':'third query'}))
        for index in range(3):self.assertIsNone(guard.check('read_webpage',{'url':str(index)}))
        self.assertIn('budget',guard.check('read_webpage',{'url':'fourth page'}))
    def test_diagnostic_detects_old_access_page_and_repeated_calls(self):
        step={'tool':'read_webpage','arguments':{'url':'https://example.org'},'result':{'ok':True,'text':'Trouble accessing Google Search'}}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'trace.json';path.write_text(json.dumps({'steps':[step,step],'provider_http_code':429}),encoding='utf-8')
            result=summarize(path)
        self.assertEqual(result['repeated_calls'],1);self.assertEqual(result['unreadable_pages'],2);self.assertEqual(result['provider_http_code'],429)
