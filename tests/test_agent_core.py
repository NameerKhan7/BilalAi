import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from google.genai import errors
from agent_core import AgentBrain,AgentError,DEFAULT_MODEL

class AgentBrainTests(unittest.TestCase):
    def setUp(self):
        credentials=patch('agent_core.credential_key',return_value=None);credentials.start();self.addCleanup(credentials.stop)
        self.environment=patch.dict(os.environ,{},clear=True)
        self.values=patch('agent_core.dotenv_values',return_value={'GEMINI_API_KEY':'test-key-without-prefix'})
        self.factory=patch('agent_core.genai.Client')
        self.environment.start();self.values.start()
        self.create=self.factory.start()
        self.client=self.create.return_value.__enter__.return_value
        self.client.models.generate_content.return_value=SimpleNamespace(text=' A short answer. ')

    def tearDown(self):
        self.factory.stop();self.values.stop();self.environment.stop()

    def test_key_has_no_local_prefix_restriction(self):
        brain=AgentBrain()
        self.assertEqual(brain.ask('What is 2 plus 2?'),'A short answer.')
        self.create.assert_called_once_with(api_key='test-key-without-prefix',http_options={'timeout':20000})
        request=self.client.models.generate_content.call_args.kwargs
        self.assertEqual(request['model'],DEFAULT_MODEL)
        self.assertEqual(request['contents'][0].parts[0].text,'What is 2 plus 2?')
        self.assertTrue(request['config'].automatic_function_calling.disable)

    def test_follow_up_includes_prior_question_and_answer(self):
        brain=AgentBrain()
        brain.ask('Remember the word mango.')
        brain.ask('What word did I mention?')
        content=self.client.models.generate_content.call_args.kwargs['contents']
        self.assertEqual([(c.role,c.parts[0].text) for c in content],
                         [('user','Remember the word mango.'),('model','A short answer.'),('user','What word did I mention?')])

    def test_history_is_bounded_in_complete_turns(self):
        brain=AgentBrain(history_pairs=2)
        for question in ['first','second','third']:
            brain.ask(question)
        self.assertEqual([h['text'] for h in brain.history],['second','A short answer.','third','A short answer.'])
        self.assertEqual([h['role'] for h in brain.history],['user','model','user','model'])

    def test_quota_failure_does_not_poison_history_or_expose_raw_error(self):
        brain=AgentBrain()
        brain.ask('first')
        history=list(brain.history)
        self.client.models.generate_content.side_effect=errors.ClientError(429,{'error':{'message':'private-provider-detail','status':'RESOURCE_EXHAUSTED'}})
        with self.assertRaises(AgentError) as error: brain.ask('second')
        self.assertIn('quota',str(error.exception))
        self.assertNotIn('private-provider-detail',str(error.exception))
        self.assertEqual(brain.history,history)

    def test_missing_key_makes_no_request(self):
        self.values.stop()
        with patch('agent_core.dotenv_values',return_value={}),patch('agent_core.credential_key',return_value=None):
            with self.assertRaisesRegex(AgentError,'GEMINI_API_KEY'): AgentBrain().ask('hello')
        self.create.assert_not_called()

    def test_empty_or_oversized_question_makes_no_request(self):
        brain=AgentBrain()
        with self.assertRaises(AgentError): brain.ask('  ')
        with self.assertRaises(AgentError): brain.ask('x'*4001)
        self.create.assert_not_called()

    def test_empty_reply_is_not_saved_as_a_successful_turn(self):
        self.client.models.generate_content.return_value=SimpleNamespace(text=None)
        brain=AgentBrain()
        with self.assertRaisesRegex(AgentError,'no answer'): brain.ask('hello')
        self.assertEqual(brain.history,[])

    def test_clear_starts_a_fresh_conversation(self):
        brain=AgentBrain();brain.ask('hello');brain.clear();brain.ask('new topic')
        content=self.client.models.generate_content.call_args.kwargs['contents']
        self.assertEqual(len(content),1)
        self.assertEqual(content[0].parts[0].text,'new topic')

if __name__=='__main__': unittest.main()
