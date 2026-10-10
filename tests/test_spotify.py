import asyncio
import json
import unittest
from unittest.mock import Mock, patch
from spotify_worker import matches_title, result_buttons, search_matches, execute, PlaybackFailure
from spotify_tools import play_spotify, SpotifyActionError
from agent_tools import AgentToolExecutor

class SpotifyTests(unittest.TestCase):
    def test_combobox_and_encoded_spaces_are_verified(self):
        field=Mock();field.is_visible.return_value=True
        field.iface_value.CurrentValue='Blinding+Lights'
        window=Mock();window.descendants.side_effect=lambda **kw: [field] if kw['control_type']=='ComboBox' else []
        self.assertTrue(search_matches(window,'Blinding Lights'))
        self.assertFalse(search_matches(window,'Different Song'))

    def test_result_selection_uses_song_row_and_generic_play(self):
        button=Mock();button.window_text.return_value='Play'
        button.is_visible.return_value=True;button.is_enabled.return_value=True
        cell=Mock();cell.window_text.return_value='Song\u00a0\u2022\u00a0The Weeknd'
        link=Mock();link.window_text.return_value='Blinding Lights'
        row=Mock();row.element_info.control_type='DataItem';row.is_visible.return_value=True
        row.descendants.side_effect=lambda **kw: {'Button':[button],'DataItem':[cell],'Hyperlink':[link]}[kw['control_type']]
        grid=Mock();grid.window_text.return_value='Search results';grid.is_visible.return_value=True
        grid.children.return_value=[row]
        transport=Mock();transport.window_text.return_value='Player controls'
        window=Mock();window.descendants.return_value=[transport,grid]
        self.assertEqual(result_buttons(window),[(button,'Blinding Lights')])
        cell.window_text.return_value='Single\u00a0\u2022\u00a0The Weeknd'
        self.assertEqual(result_buttons(window),[])

    def test_wrong_current_track_cannot_pass_verification(self):
        self.assertFalse(matches_title('Blinding Lights','Jazz in Paris'))
        self.assertTrue(matches_title('Blinding Lights','Blinding Lights (Remastered)'))
        self.assertFalse(matches_title('','Any song'))

    def test_playback_failure_reaches_the_agent(self):
        player=Mock(side_effect=SpotifyActionError('Could not verify playback'))
        executor=AgentToolExecutor(spotify_player=player,desktop=Mock())
        with self.assertRaises(SpotifyActionError): executor.execute('spotify_play',{'query':'jazz'})

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
