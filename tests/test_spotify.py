import asyncio
import json
import unittest
from unittest.mock import Mock, patch
from spotify_worker import matches_title, result_buttons, execute, PlaybackFailure
from spotify_tools import play_spotify, SpotifyActionError
from request_router import RequestProcessor, spotify_command

class SpotifyTests(unittest.TestCase):
    def test_recognizes_compound_and_playback_requests(self):
        self.assertEqual(spotify_command('Hey Bilal, open up Spotify and play jazz.'),'jazz')
        self.assertEqual(spotify_command('Please play Nog 2 on Spotify'),'Nog 2')
        self.assertIsNone(spotify_command('How do I play jazz on Spotify?'))
        self.assertIsNone(spotify_command("Don't play jazz on Spotify"))
        self.assertIsNone(spotify_command('Open Notion and play jazz'))

    def test_result_selection_excludes_global_transport(self):
        controls=[]
        for name in ['Play','Pause','Play Next','Play Blinding Lights']:
            button=Mock();button.window_text.return_value=name
            button.is_visible.return_value=True;button.is_enabled.return_value=True
            controls.append(button)
        window=Mock();window.descendants.return_value=controls
        self.assertEqual([name for _,name in result_buttons(window)],['Blinding Lights'])

    def test_wrong_current_track_cannot_pass_verification(self):
        self.assertFalse(matches_title('Blinding Lights','Jazz in Paris'))
        self.assertTrue(matches_title('Blinding Lights','Blinding Lights (Remastered)'))
        self.assertFalse(matches_title('','Any song'))

    def test_failure_is_not_remembered_as_a_success(self):
        brain=Mock();brain.history=[]
        player=Mock(side_effect=SpotifyActionError('Could not verify playback'))
        processor=RequestProcessor(brain,spotify_player=player)
        with self.assertRaises(SpotifyActionError): processor.handle('Play jazz on Spotify')
        brain.ask.assert_not_called();brain.remember.assert_not_called()

    def test_worker_failure_does_not_become_a_playing_reply(self):
        worker=Mock();worker.poll.return_value=1
        worker.stdout.read.return_value=json.dumps({'ok':False,'error':'No named playable result'})
        worker.__enter__=Mock(return_value=worker);worker.__exit__=Mock(return_value=False)
        with patch('spotify_tools.subprocess.Popen',return_value=worker):
            with self.assertRaisesRegex(SpotifyActionError,'No named'):
                play_spotify('jazz')

    def test_missing_search_verification_never_invokes_play(self):
        window=Mock();window.descendants.return_value=[]
        desktop=Mock()
        # Time jumps past the search deadline after finding the window.
        with patch('pywinauto.Desktop',return_value=desktop), patch('spotify_worker.os.startfile'), \
             patch('spotify_worker.spotify_window',return_value=window), \
             patch('spotify_worker.media_snapshot',new=Mock(return_value=None)), \
             patch('spotify_worker.asyncio.run',return_value=None), \
             patch('spotify_worker.time.monotonic',side_effect=[0,1,20]):
            with self.assertRaisesRegex(PlaybackFailure,'verify the search field'):
                execute('jazz')
        window.descendants.assert_not_called()

if __name__=='__main__': unittest.main()
