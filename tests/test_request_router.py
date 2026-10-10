import threading
import unittest
from unittest.mock import Mock,patch
from pathlib import Path
from request_router import RequestProcessor,app_command,browser_command,RequestCancelled
from app_tools import open_app,AppLaunchError
from browser_tools import search_url
from command_types import RequestResult

class LocalRequestTests(unittest.TestCase):
    def setUp(self):
        self.brain=Mock();self.brain.history=[];self.brain.ask.return_value='A website presents content; a web app supports interactive tasks.'
        self.opener=Mock(return_value='Opened Notion.')
        self.browser=Mock()
        self.processor=RequestProcessor(self.brain,self.browser,self.opener)

    def test_notion_opens_locally_without_gemini(self):
        result=self.processor.handle('Hey Bilal, open the Notion app.')
        self.opener.assert_called_once_with('notion');self.brain.ask.assert_not_called()
        self.assertEqual(result.kind,'app')

    def test_exact_screenshot_sentence_opens_spotify_without_gemini(self):
        result=self.processor.handle('Okay, so I want you to open up Spotify and play jazz.')
        self.opener.assert_called_once_with('spotify')
        self.brain.ask.assert_not_called()
        self.assertEqual(result.kind,'app')

    def test_conversational_fillers_can_precede_a_wake_phrase(self):
        self.processor.handle('Well, okay, hey Bilal, could you please open Notion?')
        self.opener.assert_called_once_with('notion')
        self.brain.ask.assert_not_called()

    def test_unmatched_command_does_not_get_fake_gemini_execution(self):
        result=self.processor.handle('Do me a favor and open Spotify while deleting files')
        self.assertEqual(result.kind,'unsupported')
        self.brain.ask.assert_not_called()
        self.opener.assert_not_called()

    def test_negative_instruction_does_not_launch(self):
        self.processor.handle("Okay, I don't want you to open Spotify")
        self.opener.assert_not_called()

    def test_actual_spotify_failure_routes_locally(self):
        self.opener.return_value='Opened Spotify.'
        result=self.processor.handle('I said I want you to open up the Spotify and play Nog 2.')
        self.opener.assert_called_once_with('spotify')
        self.brain.ask.assert_not_called()
        self.assertEqual(result.kind,'app')
        self.assertIn('playback are not connected',result.reply)

    def test_polite_wrappers_do_not_send_app_commands_to_gemini(self):
        self.processor.handle('Could you please open up the Notion app?')
        self.opener.assert_called_once_with('notion')
        self.brain.ask.assert_not_called()

    def test_playback_request_does_not_get_fake_gemini_tool_reply(self):
        result=self.processor.handle('Play some jazz on the Spotify')
        self.opener.assert_called_once_with('spotify')
        self.brain.ask.assert_not_called()
        self.assertIn('not connected',result.reply)

    def test_spotify_and_chrome_names_are_recognized(self):
        self.assertEqual(app_command('Please open Spotify'),'spotify')
        self.assertEqual(app_command('Chrome kholo'),'chrome')
        self.assertEqual(app_command('Open Google Chrome browser'),'chrome')

    def test_information_question_does_not_launch_an_app(self):
        result=self.processor.handle('What is the difference between a website and a web app?')
        self.brain.ask.assert_called_once();self.opener.assert_not_called();self.browser.execute.assert_not_called()
        self.assertEqual(result.kind,'answer')

    def test_how_to_question_is_not_an_open_command(self):
        self.processor.handle('How do I open Notion?')
        self.opener.assert_not_called();self.brain.ask.assert_called_once()

    def test_unsupported_app_is_not_silently_changed(self):
        result=self.processor.handle('Open Prom')
        self.assertEqual(result.kind,'unsupported');self.opener.assert_not_called();self.brain.ask.assert_not_called()

    def test_website_search_extracts_site_and_terms(self):
        command=browser_command('Open YouTube and search for Pakistani food in Chrome')
        self.assertEqual((command.action,command.site,command.query),('web_search','youtube','Pakistani food'))
        url=search_url('youtube','food & calc.exe')
        self.assertIn('search_query=food+%26+calc.exe',url)

    def test_cancelled_request_does_not_open_apps(self):
        cancel=threading.Event();cancel.set()
        with self.assertRaises(RequestCancelled): self.processor.handle('Open Spotify',cancel)
        self.opener.assert_not_called()

    def test_store_launch_uses_app_id_and_never_a_shell(self):
        with patch('app_tools.Path.is_file',return_value=False),patch('app_tools.store_catalog',return_value={'spotify':'SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify'}),patch('app_tools.subprocess.Popen') as launch:
            open_app('spotify')
        args=launch.call_args.args[0]
        self.assertTrue(args[1].startswith('shell:AppsFolder\\SpotifyAB.'))
        self.assertFalse(launch.call_args.kwargs['shell'])

    def test_missing_store_app_is_not_reported_opened(self):
        with patch('app_tools.Path.is_file',return_value=False),patch('app_tools.store_catalog',return_value={}),patch('app_tools.subprocess.Popen') as launch:
            with self.assertRaises(AppLaunchError): open_app('notion')
            launch.assert_not_called()

if __name__=='__main__': unittest.main()
