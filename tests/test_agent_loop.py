import os,threading,unittest
from unittest.mock import Mock,patch
from google.genai import types
from agent_core import AgentBrain
from request_router import RequestCancelled
from agent_tools import AgentToolExecutor

def response(text=None,calls=()):
    parts=[types.Part(function_call=types.FunctionCall(name=name,args=args)) for name,args in calls]
    if text: parts.append(types.Part(text=text))
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role='model',parts=parts))])

class AgentLoopTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{},clear=True);self.env.start()
        self.values=patch('agent_core.dotenv_values',return_value={'GEMINI_API_KEY':'test-key'});self.values.start()
        self.factory=patch('agent_core.genai.Client');self.create=self.factory.start()
        self.client=self.create.return_value.__enter__.return_value
        self.executor=Mock();self.executor.execute.return_value={'ok':True,'verified':True}
        self.brain=AgentBrain(trace_enabled=False)
    def tearDown(self):
        self.factory.stop();self.values.stop();self.env.stop()

    def test_missing_detail_pauses_before_other_actions_and_preserves_email(self):
        question='Tell me the recipient email address.'
        self.executor.execute.return_value={'ok':True,'input_request':{'question':question,'field':'email'}}
        self.client.models.generate_content.return_value=response(calls=[
            ('gmail_create_draft',{'to':'invented@example.org','subject':'Meeting','body':'Meet tomorrow.'}),
            ('request_input',{'question':question,'field':'email'})])
        reply=self.brain.run('Write an email saying meet tomorrow. Subject: Meeting.',self.executor)
        self.assertEqual(reply,question)
        self.executor.execute.assert_called_once_with('request_input',{'question':question,'field':'email'},None)
        self.assertIn('meet tomorrow',self.brain.history[0]['text'])
        self.client.models.generate_content.return_value=response('Ready to draft.')
        self.brain.run('The address is recipient@example.org',self.executor)
        contents=self.client.models.generate_content.call_args.kwargs['contents']
        self.assertIn('meet tomorrow',contents[0].parts[0].text)

    def test_observe_act_verify_loop(self):
        self.client.models.generate_content.side_effect=[
            response(calls=[('inspect_window',{'window_id':'returned-window'})]),
            response(calls=[('activate_control',{'control_id':'observed-play'})]),
            response(calls=[('media_status',{})]),
            response('Playing the selected song.')]
        reply=self.brain.run('Put that song on',self.executor)
        self.assertEqual([c.args[0] for c in self.executor.execute.call_args_list],
                         ['inspect_window','activate_control','media_status'])
        self.assertEqual(reply,'Playing the selected song.')
        final=self.client.models.generate_content.call_args.kwargs['contents']
        results=[p.function_response for c in final for p in c.parts if p.function_response]
        self.assertEqual(len(results),3)
        self.assertTrue(all(c.role=='user' for c in final if any(p.function_response for p in c.parts)))
        self.executor.close.assert_called_once()

    def test_tool_failure_is_returned_to_model_for_recovery(self):
        self.executor.execute.side_effect=[{'ok':False,'error':'stale control'},{'ok':True,'controls':[]}]
        self.client.models.generate_content.side_effect=[
            response(calls=[('activate_control',{'control_id':'old'})]),
            response(calls=[('inspect_window',{'window_id':'window'})]),
            response('The control is unavailable.')]
        self.brain.run('Play it',self.executor)
        self.assertFalse(self.executor.trace[0]['result']['ok'])
        self.assertEqual(self.executor.trace[1]['tool'],'inspect_window')

    def test_no_extra_ui_mutation_in_one_model_turn(self):
        self.client.models.generate_content.side_effect=[
            response(calls=[('activate_control',{'control_id':'one'}),('activate_control',{'control_id':'two'})]),
            response('Need to inspect again.')]
        self.brain.run('Do a task',self.executor)
        self.executor.execute.assert_called_once()
        self.assertFalse(self.executor.trace[1]['result']['ok'])

    def test_cancel_after_reasoning_prevents_tool_execution(self):
        cancel=threading.Event()
        def generated(**kwargs):
            cancel.set()
            return response(calls=[('spotify_play',{'query':'song'})])
        self.client.models.generate_content.side_effect=generated
        with self.assertRaises(RequestCancelled): self.brain.run('Play it',self.executor,cancel)
        self.executor.execute.assert_not_called();self.assertEqual(self.brain.history,[])

    def test_step_limit_stops_infinite_tool_loop(self):
        self.client.models.generate_content.return_value=response(calls=[('media_status',{})])
        reply=self.brain.run('Finish an impossible task',self.executor,max_rounds=2)
        self.assertIn('action limit',reply);self.assertEqual(self.executor.execute.call_count,2)

    def test_question_needs_no_desktop_action(self):
        self.client.models.generate_content.return_value=response('A website presents content.')
        self.brain.run('What is a website?',self.executor)
        self.executor.execute.assert_not_called()

    def test_uncertain_write_blocks_further_mutations(self):
        self.executor.execute.return_value={'ok':False,'outcome_uncertain':True,'error':'timeout'}
        self.client.models.generate_content.side_effect=[
            response(calls=[('gmail_create_draft',{'to':'test@example.org','subject':'Test','body':'body'})]),
            response(calls=[('notion_create_note',{'parent_id':'page','title':'Test','body':'body'})]),
            response('The write outcome is uncertain. Please check before retrying.')]
        self.brain.run('Create a draft and then a note',self.executor)
        self.executor.execute.assert_called_once()
        self.assertFalse(self.executor.trace[1]['result']['ok'])

    def test_current_request_and_date_context_are_explicit(self):
        self.brain.remember('Play jazz on Spotify','Playing jazz.')
        self.client.models.generate_content.return_value=response('Which app do you mean?')
        self.brain.run('So I want you to start on home.',self.executor)
        request=self.client.models.generate_content.call_args.kwargs
        self.assertEqual(request['contents'][-1].parts[0].text,'So I want you to start on home.')
        self.assertIn('Previous completed tasks are context',request['config'].system_instruction)
        self.assertIn('Current local date/time:',request['config'].system_instruction)
        self.assertIn('Tomorrow is ',request['config'].system_instruction)
        self.executor.execute.assert_not_called()

    def test_unknown_tools_and_extra_args_cannot_execute(self):
        desktop=Mock()
        tools=AgentToolExecutor(desktop=desktop)
        self.assertFalse(tools.execute('run_shell',{'command':'calc'})['ok'])
        self.assertFalse(tools.execute('launch_app',{'app_id':'app','command':'calc'})['ok'])
        desktop.call.assert_not_called()

if __name__=='__main__': unittest.main()
