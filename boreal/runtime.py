"""RPC v2: fast cached reads and per-device priority actors."""
import copy
import fcntl
import itertools
import json
import logging
import os
import queue
import signal
import socket
import socketserver
import struct
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from .core import PRESETS
from .diagnostics import configure, export
from .errors import BorealError, error_payload
from .hardware import catalog
from .library import media_call, records
from .service import Controller, device_state
from .settings import Settings, ProfileLibrary, restore_allowed
from .i18n import configure as configure_language
from .transport import Worker, socket_path, receive, open_lock
from .i18n import _

LOG=logging.getLogger('boreal.runtime')


class Actor:
    def __init__(self, descriptor, runtime):
        self.runtime=runtime; self.key=descriptor['id']; self.descriptor=descriptor
        self.controller=Controller(Worker(runtime.demo), runtime.profiles)
        self.controller.devices[self.key]=device_state(descriptor)
        self.controller.devices[self.key]['rgb_last_on']=copy.deepcopy(runtime.settings.read()['devices'].get(self.key,{}).get('rgb_last_on',{}))
        self.jobs=queue.PriorityQueue(maxsize=64); self.sequence=itertools.count()
        self.stop=threading.Event(); self.lock=threading.Lock(); self.cached=self.controller.snapshot()
        self.thread=threading.Thread(target=self.loop,daemon=True,name='device-'+self.key[:8]); self.thread.start()

    def publish(self):
        snapshot=self.controller.snapshot()
        with self.lock: self.cached=snapshot
        item=self.controller.devices[self.key]
        saved=self.runtime.settings.read()['devices'].get(self.key,{})
        if item['latched'] and not saved.get('latched'):
            self.runtime.settings.update_device(self.key,latched=True)

    def snapshot(self):
        with self.lock: snapshot=copy.deepcopy(self.cached)
        for item in snapshot['devices']:
            item['age']=round(time.monotonic()-item['updated'],1) if item['updated'] else None
            item['stale']=item['age'] is None or item['age']>12
            if item['stale']: item['status']={}
        return snapshot

    def submit(self, job, request):
        priority=0 if request['op'] in ('emergency','detach','_resume') else (1 if request['op'] in ('attach','onboard','apply','restore') else 3)
        try: self.jobs.put_nowait((priority,next(self.sequence),job,request))
        except queue.Full: raise BorealError(_('Zu viele ausstehende Geräteaufträge'),'busy')

    def ensure(self):
        if self.controller.worker.process is None:
            found=self.controller.worker.call('discover',self.descriptor.get('selector'))
            if not any(d['id']==self.key for d in found):
                self.controller.worker.close(); raise BorealError(_('Gerät nicht mehr erreichbar'),'connection')

    def persist(self):
        item=self.controller.devices[self.key]
        if not item['connected']: return
        changes=dict(firmware=item['firmware'],latched=item['latched'])
        if item['active_profile']:
            changes.update(profile=item['active_profile'],profile_name=item['active'])
        display=item['display']
        if not display['error'] and display['mode']:
            changes['display']={k:copy.deepcopy(display[k]) for k in ('mode','media_id','options','sent') if k in display}
        if not item['rgb_error']:
            changes['rgb']=item['rgb_settings'];changes['rgb_last_on']=item.get('rgb_last_on',{})
        self.runtime.settings.update_device(self.key,**changes)

    def restore(self):
        saved=self.runtime.settings.read()['devices'].get(self.key,{})
        if not saved.get('enabled') or saved.get('latched') or self.descriptor.get('identity')!='Seriennummer': return
        self.ensure()
        self.controller.dispatch(dict(v=2,op='attach',device=self.key))
        item=self.controller.devices[self.key]
        if not restore_allowed(saved,item):
            item['active']=_('Sicher · Firmware vor Wiederherstellung prüfen'); return
        self.controller.dispatch(dict(v=2,op='apply',device=self.key,profile=saved.get('profile',PRESETS['Ausgewogen']),name=saved.get('profile_name','Ausgewogen')))
        display=saved.get('display',{})
        try:
            for name,value in display.get('sent',{}).items():
                if name in ('orientation','brightness'):
                    self.controller.dispatch(dict(v=2,op='screen',device=self.key,mode=name,value=value))
            if display.get('mode'):
                self.controller.dispatch(dict(v=2,op='screen',device=self.key,mode=display['mode'],media_id=display.get('media_id'),options=display.get('options',{})))
            for zone,value in saved.get('rgb',{}).items():
                self.controller.dispatch(dict(v=2,op='color',device=self.key,channel=zone,**value))
        except Exception as exc:
            LOG.warning('Dekoration konnte nicht wiederhergestellt werden: %s',exc)

    def execute(self,req):
        op=req['op']
        if op=='_resume':
            self.controller.close(); self.restore(); return self.controller.snapshot()
        if op=='restore': self.restore(); return self.controller.snapshot()
        if op=='enable_restore':
            item=self.controller.devices[self.key]
            enabled=req.get('enabled')
            if type(enabled)!=bool: raise ValueError(_('Aktivierung muss ja/nein sein'))
            if enabled and (not item['connected'] or item['identity']!='Seriennummer' or not item.get('tested')):
                raise ValueError(_('Wiederherstellung benötigt ein verbundenes, geprüftes Gerät mit Seriennummer'))
            self.persist(); self.runtime.settings.update_device(self.key,enabled=enabled)
            return self.controller.snapshot()
        if op in ('attach','onboard'): self.ensure()
        if op=='onboard':
            self.controller.dispatch(dict(req,op='attach'))
            result=self.controller.dispatch(dict(req,op='apply',profile=PRESETS['Ausgewogen'],name='Ausgewogen'))
        else: result=self.controller.dispatch(req)
        if op in ('apply','screen','color','onboard','attach','pause_stats','resume_stats','lights_off','restore_lights'):
            self.persist()
        if op=='detach': self.runtime.settings.update_device(self.key,enabled=False)
        return result

    def loop(self):
        last=0
        while not self.stop.is_set():
            try:
                _,_,job,req=self.jobs.get(timeout=.05)
            except queue.Empty:
                job=req=None
            if req:
                self.runtime.job_update(job,state='running')
                try:
                    result=self.execute(req)
                    self.runtime.job_update(job,state='done',result=result)
                except Exception as exc:
                    LOG.exception('Auftrag %s (%s) fehlgeschlagen',job,req['op'])
                    self.runtime.job_update(job,state='failed',error=error_payload(exc))
                finally: self.publish()
            if time.monotonic()-last>=min(3,self.runtime.settings.read().get('refresh_interval_ms',1000)/1000):
                try:
                    self.controller.tick()
                    if self.runtime.settings.read().get('refresh_interval_ms',1000)==500 and any(d.get('telemetry_timeouts',0)>=2 for d in self.controller.devices.values()):
                        self.runtime.settings.refresh_interval(1000)
                        self.runtime.refresh_notice=_('Nach wiederholten USB-Zeitüberschreitungen auf 1 Sekunde zurückgestellt. Verbindung bitte prüfen.')
                    self.publish()
                except Exception: LOG.exception('Geräteüberwachung fehlgeschlagen')
                last=time.monotonic()
        self.controller.close(); self.publish()
        while not self.jobs.empty():
            _,_,job,_=self.jobs.get_nowait()
            self.runtime.job_update(job,state='failed',error=error_payload(BorealError(_('Dienst beendet'),'shutdown')))


class Runtime:
    def __init__(self,demo=False):
        self.demo=demo; self.settings=Settings(); configure_language(self.settings.read().get('language','system')); self.profiles=ProfileLibrary()
        self.actors={}; self.jobs={}; self.lock=threading.RLock()
        self.general=ThreadPoolExecutor(max_workers=2,thread_name_prefix='media-config')
        self.stopping=False;self.refresh_notice=""

    def job_update(self,key,**changes):
        with self.lock:
            if key in self.jobs:
                self.jobs[key].update(changes,updated=time.time())

    def snapshot(self):
        with self.lock: actors=list(self.actors.values())
        devices=[]; host={}
        for actor in actors:
            state=actor.snapshot(); devices.extend(state['devices']); host=state['host'] or host
        settings=self.settings.read()
        for device in devices:
            device['restore_enabled']=settings['devices'].get(device['id'],{}).get('enabled',False)
        return dict(v=2,devices=devices,host=host,theme=settings['theme'],language=settings.get('language','system'),refresh_interval_ms=settings.get('refresh_interval_ms',1000),refresh_notice=self.refresh_notice)

    def discover(self):
        for info in catalog(self.demo):
            with self.lock:
                if info['id'] in self.actors: continue
                if len(self.actors)>=8: raise ValueError(_('Maximal acht Geräte pro Sitzung'))
                actor=Actor(info,self); self.actors[info['id']]=actor
            saved=self.settings.read()['devices'].get(info['id'],{})
            if saved.get('enabled') and not saved.get('latched'):
                self.submit(dict(v=2,op='restore',device=info['id']))
        return self.snapshot()

    def general_job(self,key,req):
        self.job_update(key,state='running')
        try:
            op=req['op']
            if op=='discover': result=self.discover()
            elif op=='save_profile': self.profiles.save(req['name'],req['profile']); result=self.profiles.read()
            elif op=='delete_profile': self.profiles.delete(req['name']); result=self.profiles.read()
            elif op=='rename_profile': self.profiles.rename(req['old'],req['name']); result=self.profiles.read()
            elif op=='import_media': result=media_call('import',path=req['path'],mode=req['mode'],size=req.get('size',640),options=req.get('options',{}))
            elif op=='set_refresh_interval': self.settings.refresh_interval(req['value']); result=self.snapshot()
            elif op=='theme': self.settings.theme(req['value']); result=self.snapshot()
            elif op=='language':
                self.settings.language(req['value']); configure_language(req['value']); result=self.snapshot()
            elif op=='diagnostics': result=export(self.snapshot())
            else: raise ValueError(_('Unbekannte Aktion'))
            self.job_update(key,state='done',result=result)
        except Exception as exc:
            LOG.exception('Auftrag %s fehlgeschlagen',key)
            self.job_update(key,state='failed',error=error_payload(exc))

    def submit(self,req):
        if self.stopping: raise BorealError(_('Dienst wird beendet'),'shutdown')
        op=req['op']
        general=op in ('discover','save_profile','delete_profile','rename_profile','import_media','theme','language','diagnostics','set_refresh_interval')
        allowed=('attach','onboard','detach','apply','screen','color','emergency','enable_restore','restore','_resume','pause_stats','resume_stats','lights_off','restore_lights')
        if not general and op not in allowed: raise ValueError(_('Unbekannte Aktion'))
        with self.lock:
            if not general and req.get('device') not in self.actors: raise ValueError(_('Gerät nicht gefunden'))
            pending=sum(j['state'] in ('queued','running') for j in self.jobs.values())
            if pending>=60 and op!='emergency': raise BorealError('Auftragsliste voll','busy')
            if len(self.jobs)>=128:
                for key in list(self.jobs):
                    if self.jobs[key]['state'] in ('done','failed'): del self.jobs[key]; break
            key=uuid.uuid4().hex
            req=dict(req,request_id=key)
            self.jobs[key]=dict(id=key,op=op,state='queued',updated=time.time())
            try:
                if general: self.general.submit(self.general_job,key,req)
                else: self.actors[req['device']].submit(key,req)
            except Exception:
                del self.jobs[key]; raise
        return dict(job_id=key)

    def handle(self,req):
        if not isinstance(req,dict) or req.get('v')!=2:
            raise BorealError(_('UI und Dienst haben unterschiedliche Versionen. Boreal gemeinsam aktualisieren und Dienst neu starten.'),'version')
        op=req.get('op')
        if op=='snapshot': return self.snapshot()
        if op=='profiles': return self.profiles.read()
        if op=='media': return records()
        if op=='job':
            with self.lock:
                if req.get('job_id') not in self.jobs: raise ValueError(_('Auftrag nicht mehr verfügbar'))
                return copy.deepcopy(self.jobs[req['job_id']])
        if op=='shutdown': self.stopping=True; return {'stopping':True}
        if op=='_resume': raise ValueError(_('Interne Aktion'))
        return self.submit(req)

    def close(self):
        self.stopping=True
        for actor in self.actors.values(): actor.stop.set()
        for actor in self.actors.values(): actor.thread.join(timeout=45)
        self.general.shutdown(wait=True,cancel_futures=True)


class Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
    daemon_threads=True
    request_queue_size=16


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(1)
        try:
            _,uid,_=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid!=os.getuid(): raise PermissionError(_('Fremder Benutzer'))
            answer=dict(ok=True,result=self.server.runtime.handle(receive(self.request)))
        except Exception as exc: answer=dict(ok=False,error=error_payload(exc))
        try: self.request.sendall(json.dumps(answer,allow_nan=False).encode()+b'\n')
        except OSError: pass


def run(demo=False):
    configure('demo' if demo else 'hardware')
    path=socket_path(demo)
    lock=open_lock(path.with_suffix('.lock'))
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    path.unlink(missing_ok=True)
    runtime=Runtime(demo)
    def stop(*_): runtime.stopping=True
    signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
    with Server(str(path),Handler) as server:
        os.chmod(path,0o600); server.runtime=runtime; server.timeout=.3
        runtime.discover()
        previous=time.clock_gettime(time.CLOCK_BOOTTIME)-time.monotonic()
        last_scan=time.monotonic()
        try:
            while not runtime.stopping:
                server.handle_request()
                delta=time.clock_gettime(time.CLOCK_BOOTTIME)-time.monotonic()
                if delta-previous>3:
                    for key in list(runtime.actors): runtime.submit(dict(v=2,op='_resume',device=key))
                previous=delta
                if time.monotonic()-last_scan>15:
                    runtime.discover()
                    for key,actor in list(runtime.actors.items()):
                        item=actor.snapshot()['devices'][0]
                        saved=runtime.settings.read()['devices'].get(key,{})
                        if not item['connected'] and not item['latched'] and saved.get('enabled') and actor.jobs.empty():
                            runtime.submit(dict(v=2,op='restore',device=key))
                    last_scan=time.monotonic()
        finally:
            runtime.close(); path.unlink(missing_ok=True); lock.close()
