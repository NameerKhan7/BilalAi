"""Offline cancellation phrases during processing; no audio goes to a provider."""
import re,subprocess,threading
CANCEL_PHRASES={'never mind','nevermind','cancel that','cancel the request','stop bilal','forget it'}
def is_cancel_request(text):
    text=re.sub(r'[^\w\s]',' ',text.casefold())
    text=re.sub(r'\s+',' ',text).strip()
    for _ in range(3):text=re.sub(r'^(?:hey bilal|bilal|actually|okay|ok)\s+','',text)
    return text in CANCEL_PHRASES

SCRIPT=r'''
Add-Type -AssemblyName System.Speech
$recognizer=[System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() | Where-Object { $_.Culture.Name -eq 'en-US' } | Select-Object -First 1
if (-not $recognizer) { exit 2 }
$engine=New-Object System.Speech.Recognition.SpeechRecognitionEngine($recognizer.Id)
$choices=New-Object System.Speech.Recognition.Choices
$choices.Add([string[]]@('never mind','cancel that','stop Bilal'))
$builder=New-Object System.Speech.Recognition.GrammarBuilder
$builder.Culture=$recognizer.Culture
$builder.Append($choices)
$engine.LoadGrammar((New-Object System.Speech.Recognition.Grammar($builder)))
$engine.SetInputToDefaultAudioDevice()
[Console]::Out.WriteLine('READY')
[Console]::Out.Flush()
try {
    while ($true) {
        $result=$engine.Recognize([TimeSpan]::FromSeconds(2))
        if ($result -and $result.Confidence -ge 0.75) {
            [Console]::Out.WriteLine('CANCEL')
            [Console]::Out.Flush()
        }
    }
} finally { $engine.Dispose() }
'''
class CancelListener:
    def __init__(self,callback):self.callback=callback;self.process=None
    def start(self):
        if self.process is not None:return
        self.process=subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-Command',SCRIPT],
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        threading.Thread(target=self._read,args=(self.process,),daemon=True).start()
    def _read(self,process):
        for line in process.stdout:
            if line.strip()=='CANCEL' and process is self.process:self.callback()
    def stop(self):
        process=self.process;self.process=None
        if process is not None:
            if process.poll() is None:process.kill()
            process.wait(timeout=3)

def strip_wake_prefix(text):
    return re.sub(r'^\s*(?:hey|hi)\s*[, ]*bilal[\s,.!?]*','',text,flags=re.I).strip()
