import threading, unittest
from unittest.mock import Mock,patch
from request_router import RequestProcessor,RequestCancelled
from app_tools import open_app,AppLaunchError
from browser_tools import search_url

class AgentRequestTests(unittest.TestCase):
    def test_all_wording_is_forwarded_to_the_agent(self):
        brain=Mock();brain.run.return_value='Done'
        executor=Mock();executor.trace=[{'tool':'spotify_play'}]
        processor=RequestProcessor(brain,executor_factory=lambda:executor)
        for query in ['Play blind Lights on Spotify by The Weeknd',
                      'Find that Weeknd track and put it on',
                      'Open my newly installed app',
                      'Explain websites versus web apps']:
            result=processor.handle(query)
            self.assertEqual(brain.run.call_args.args[0],query)
            self.assertEqual(result.kind,'agent')

    def test_question_without_tools_is_an_answer(self):
        brain=Mock();brain.run.return_value='An explanation.'
        executor=Mock();executor.trace=[]
        result=RequestProcessor(brain,executor_factory=lambda:executor).handle('What is a website?')
        self.assertEqual(result.kind,'answer')

    def test_store_launch_uses_app_id_without_shell(self):
        with patch('app_tools.Path.is_file',return_value=False),patch('app_tools.store_catalog',return_value={'spotify':'SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify'}),patch('app_tools.subprocess.Popen') as launch:
            open_app('spotify')
        self.assertTrue(launch.call_args.args[0][1].startswith('shell:AppsFolder\\SpotifyAB.'))
        self.assertFalse(launch.call_args.kwargs['shell'])

    def test_missing_app_is_not_reported_opened(self):
        with patch('app_tools.Path.is_file',return_value=False),patch('app_tools.store_catalog',return_value={}):
            with self.assertRaises(AppLaunchError): open_app('notion')

    def test_search_query_cannot_become_a_shell_command(self):
        self.assertIn('search_query=food+%26+calc.exe',search_url('youtube','food & calc.exe'))

if __name__=='__main__': unittest.main()
