import base64,json,tempfile,threading,unittest
from pathlib import Path
from email.message import EmailMessage
from unittest.mock import Mock,patch
from memory import LocalState,digest
from business_tools import BusinessWorkflows,GmailClient,NotionClient,canonical_email
from agent_tools import TOOL_DECLARATIONS
from secret_store import save_secret,load_secret

class BusinessLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.state=LocalState(Path(self.temp.name)/'state.sqlite3')
        self.message={'to':'test@example.org','cc':'','bcc':'','from':'owner@example.org','subject':'Test','body':'Test body'}
        self.gmail=Mock();self.gmail.create.return_value={'draft_id':'draft-test','message':self.message}
        self.gmail.get.return_value=self.message;self.gmail.send.return_value={'verified':True,'reply':'Email sent.'}
        self.work=BusinessWorkflows(self.state,self.gmail)
    def tearDown(self):self.temp.cleanup()
    def test_draft_is_unsent_and_approval_survives_restart(self):
        result=self.work.draft('test@example.org','Test','Test body')
        self.gmail.send.assert_not_called()
        pending=LocalState(self.state.path).pending()
        self.assertEqual(pending[0]['id'],result['approval_id'])
        self.assertEqual(pending[0]['payload']['message'],self.message)
    def test_send_requires_exact_approval_and_is_one_shot(self):
        action=self.state.propose('gmail_send',{'draft_id':'draft-test','message':self.message})
        self.work.resolve(action['id'],action['digest'],True)
        self.gmail.send.assert_called_once_with('draft-test',self.message)
        with self.assertRaises(ValueError):self.work.resolve(action['id'],action['digest'],True)
        self.assertEqual(self.gmail.send.call_count,1)
    def test_wrong_digest_cannot_send(self):
        row=self.state.propose('gmail_send',{'draft_id':'draft-test','message':self.message})
        with self.assertRaises(ValueError):self.work.resolve(row['id'],'different',True)
        self.gmail.send.assert_not_called()
    def test_changed_local_payload_cannot_reuse_old_digest(self):
        row=self.state.propose('gmail_send',{'draft_id':'draft-test','message':self.message})
        changed={'draft_id':'draft-test','message':{**self.message,'to':'changed@example.org'}}
        with self.state.db() as db:db.execute('UPDATE pending SET payload=? WHERE id=?',(json.dumps(changed),row['id']))
        with self.assertRaises(ValueError):self.work.resolve(row['id'],row['digest'],True)
        self.gmail.send.assert_not_called()

    def test_changed_recipient_requires_new_review(self):
        row=self.state.propose('gmail_send',{'draft_id':'draft-test','message':self.message})
        self.gmail.get.return_value={**self.message,'to':'changed@example.org'}
        result=self.work.resolve(row['id'],row['digest'],True)
        self.assertFalse(result['ok']);self.gmail.send.assert_not_called()
        self.assertNotEqual(result['approval_id'],row['id'])
    def test_rejection_and_cancel_do_not_send(self):
        for approval,cancel in [(False,None),(True,threading.Event())]:
            if cancel:cancel.set()
            row=self.state.propose('gmail_send',{'draft_id':'draft-test','message':self.message})
            self.work.resolve(row['id'],row['digest'],approval,cancel)
        self.gmail.send.assert_not_called()
    def test_crashed_inflight_action_is_not_replayed_on_restart(self):
        row=self.state.propose('gmail_send',{'draft_id':'draft-test','message':self.message})
        self.state.claim(row['id'],row['digest'])
        recovered=LocalState(self.state.path,recover_inflight=True)
        self.assertEqual(recovered.get(row['id'])['status'],'uncertain')
        with self.assertRaises(ValueError):recovered.claim(row['id'],row['digest'])

    def test_timeout_is_uncertain_and_cannot_auto_retry(self):
        row=self.state.propose('gmail_send',{'draft_id':'draft-test','message':self.message})
        self.gmail.send.side_effect=TimeoutError()
        with self.assertRaises(RuntimeError):self.work.resolve(row['id'],row['digest'],True)
        self.assertEqual(self.state.get(row['id'])['status'],'uncertain')
        with self.assertRaises(ValueError):self.work.resolve(row['id'],row['digest'],True)
    def test_memory_is_not_learned_until_confirmed(self):
        result=self.work.propose_memory('preferred_city','Karachi')
        self.assertEqual(self.state.memories(),{})
        row=self.state.get(result['approval_id']);self.work.resolve(row['id'],row['digest'],True)
        self.assertEqual(LocalState(self.state.path).memories()['preferred_city'],'Karachi')
    def test_credentials_are_not_proposed_as_memory(self):
        with self.assertRaises(ValueError):self.work.propose_memory('api_key','dummy')
    def test_model_has_no_send_or_approve_tool(self):
        names={tool.name for tool in TOOL_DECLARATIONS}
        self.assertNotIn('gmail_send',names);self.assertNotIn('approve_action',names)
    def test_email_headers_reject_injection(self):
        client=GmailClient(session=Mock())
        with self.assertRaises(ValueError):client.create('a@example.org\nBcc: b@example.org','test','body')
    def test_send_payload_is_bound_to_reviewed_content(self):
        client=GmailClient();client.api=Mock(side_effect=[{'id':'sent-test'},{'labelIds':['SENT']}])
        result=client.send('draft-test',self.message)
        sent=client.api.call_args_list[0].args[2]
        self.assertEqual(canonical_email(sent['message']['raw']),self.message)
        self.assertTrue(result['verified'])
    def test_notion_search_paginates_and_returns_actual_page_ids(self):
        client=NotionClient(token='fixture-token');client.api=Mock(side_effect=[
            {'results':[{'id':'page-one','properties':{'Name':{'type':'title','title':[{'plain_text':'Bilal AI'}]}}}],'has_more':True,'next_cursor':'cursor'},
            {'results':[{'id':'page-two','properties':{'Name':{'type':'title','title':[{'plain_text':'Notes'}]}}}],'has_more':False}])
        result=client.search('Bilal')
        self.assertEqual([p['id'] for p in result['pages']],['page-one','page-two'])
        self.assertFalse(result['truncated'])
        self.assertEqual(client.api.call_args_list[1].args[2]['start_cursor'],'cursor')
    def test_notion_note_verifies_roundtrip_and_preserves_long_body(self):
        client=NotionClient(token='fixture-token');body='x'*3600
        client.api=Mock(side_effect=[{'id':'new-page','url':'https://notion.so/new-page'},
            {'properties':{'title':{'type':'title','title':[{'plain_text':'Test note'}]}}}])
        client.read=Mock(return_value={'text':body,'truncated':False})
        result=client.create_note('parent-page','Test note',body)
        self.assertTrue(result['verified'])
        blocks=client.api.call_args_list[0].args[2]['children']
        self.assertEqual(''.join(t['text']['content'] for t in blocks[0]['paragraph']['rich_text']),body)

    def test_creation_network_and_readback_failures_are_uncertain(self):
        import requests
        from agent_tools import AgentToolExecutor
        business=Mock()
        executor=AgentToolExecutor(state=self.state,business=business)
        for error in [requests.ConnectionError('fixture'),RuntimeError('Readback failed')]:
            business.notion.create_note.side_effect=error
            result=executor.execute('notion_create_note',{'parent_id':'fixture','title':'Test','body':'Body'})
            self.assertFalse(result['ok'])
            self.assertTrue(result['outcome_uncertain'])

    def test_dpapi_roundtrip_uses_temporary_storage(self):
        with patch('secret_store.path_for',return_value=Path(self.temp.name)/'secret.bin'):
            save_secret('gmail',{'test':'dummy noncredential'})
            self.assertEqual(load_secret('gmail'),{'test':'dummy noncredential'})
            self.assertNotIn(b'dummy noncredential',(Path(self.temp.name)/'secret.bin').read_bytes())

if __name__=='__main__':unittest.main()
