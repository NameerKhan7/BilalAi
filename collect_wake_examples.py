"""Record labelled phrases locally. No transcription, cloud upload or agent action."""
import argparse,threading,uuid
from wake_learning import WakeExamples
from audio_capture import CaptureConfig,capture_command
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',choices=['positive','negative','both'],required=True);parser.add_argument('--count',type=int,default=10)
    args=parser.parse_args()
    if not 1<=args.count<=50:parser.error('Use 1 to 50 examples per session.')
    store=WakeExamples();store.session=uuid.uuid4().hex
    labels=['positive','negative'] if args.label=='both' else [args.label]
    for label in labels:
      for i in range(args.count):
          input(f'Example {i+1}/{args.count}: press Enter, then '+('say Hey Bilal.' if label=='positive' else 'say a confusable phrase, ordinary speech, or hey alone.'))
          config=CaptureConfig(initial_wait_seconds=4,max_seconds=7,silence_seconds=1.5)
          result=capture_command(config,on_event=lambda name,data:print('SPEAK NOW',flush=True) if name=='ready' else None)
          if not result.speech_detected:print('No speech captured; skipped.');continue
          sample=store.record(result.audio,None,source='manual')
          if input('Confirm the recording matches that requested label? [y/N] ').strip().casefold()=='y':
              store.label(sample,label);print('Saved reviewed example locally.')
          else:print('Kept unlabelled; it will not be used for training.')
if __name__=='__main__':main()
