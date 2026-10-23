"""Opt-in real Windows check against a temporary public Chrome window only."""
import json,tempfile,time
from pathlib import Path


def main():
    import win32gui,win32process,psutil
    from playwright.sync_api import sync_playwright
    from window_grants import WindowGrants
    from agent_tools import DesktopBridge
    report={'test':'owned public Chrome window; no Gmail/account access'};grants=WindowGrants();worker=DesktopBridge()
    def windows():
        found=[]
        win32gui.EnumWindows(lambda handle,_:found.append(handle) if win32gui.IsWindowVisible(handle) else None,None)
        return set(found)
    before=windows()
    try:
        with tempfile.TemporaryDirectory(prefix='bilal-handoff-') as profile:
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch_persistent_context(profile,channel='chrome',headless=False,no_viewport=True)
                try:
                    page=browser.new_page();page.goto('https://example.com/',wait_until='domcontentloaded');time.sleep(1)
                    targets=[h for h in windows()-before if 'Example Domain' in win32gui.GetWindowText(h) and psutil.Process(win32process.GetWindowThreadProcessId(h)[1]).name().lower()=='chrome.exe']
                    if len(targets)!=1:raise RuntimeError('Could not uniquely identify the owned test browser.')
                    token=grants.issue(targets[0]);identity=grants.bind(token,'owned-acceptance')
                    bound=worker.call('_bind_user_window',{'identity':identity});report['bound']=bound.get('verified')
                    state=worker.call('selected_browser_state',{});report.update(state_ok=state.get('ok'),observed_url=state.get('url'),observed_title=state.get('title'),visible_item_count=len(state.get('items',[])),error=state.get('error'))
                    report['public_page_verified']=bool(state.get('ok') and 'example.com' in state.get('url',''))
                    grants.revoke(token);revoked=worker.call('selected_browser_state',{});report['revocation_enforced']=not revoked.get('ok')
                finally:worker.close();grants.revoke_all();browser.close()
    except Exception as exc:report['error']=str(exc)
    finally:worker.close();grants.revoke_all()
    path=Path(__file__).resolve().parent/'logs/window_handoff_acceptance.json';path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
    return 0 if report.get('public_page_verified') and report.get('revocation_enforced') else 1


if __name__=='__main__':raise SystemExit(main())
