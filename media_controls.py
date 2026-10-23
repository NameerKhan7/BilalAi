"""Observed WinRT playback and Core Audio volume, never synthetic media keys."""
import asyncio,math


async def media_control(action):
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status
    methods={'play':'try_play_async','pause':'try_pause_async','next':'try_skip_next_async','previous':'try_skip_previous_async'}
    if action not in methods:raise ValueError('Choose play, pause, next or previous.')
    manager=await Manager.request_async();sessions=[s for s in manager.get_sessions() if 'spotify' in s.source_app_user_model_id.casefold()]
    if len(sessions)!=1:raise ValueError('Exactly one Spotify media session must be open.')
    session=sessions[0];before=await session.try_get_media_properties_async();previous=(before.title,before.artist)
    accepted=await getattr(session,methods[action])()
    if not accepted:return {'ok':False,'verified':False,'error':'Spotify did not accept the playback request.'}
    for _ in range(12):
        await asyncio.sleep(.15);after=await session.try_get_media_properties_async();playing=session.get_playback_info().playback_status==Status.PLAYING
        verified=playing if action=='play' else not playing if action=='pause' else (after.title,after.artist)!=previous
        if verified:return {'ok':True,'verified':True,'title':after.title,'artist':after.artist,'playing':playing,'reply':'Playback '+action+' verified.'}
    return {'ok':False,'verified':False,'error':'The media change was not observed. No automatic retry was attempted.'}


def volume(percent):
    from pycaw.pycaw import AudioUtilities
    level=float(percent)
    if not math.isfinite(level) or not 0<=level<=100:raise ValueError('Volume must be between 0 and 100.')
    speakers=AudioUtilities.GetSpeakers()
    if speakers is None:raise ValueError('No default speaker device is available.')
    before=speakers.volume_percent;speakers.volume_percent=level;actual=speakers.volume_percent;verified=abs(actual-level)<.6
    return {'ok':verified,'verified':verified,'previous_percent':round(before,1),'percent':round(actual,1),'reply':'Volume set to '+str(round(actual))+' percent.'}
