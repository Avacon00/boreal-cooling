"""Device state machine. One actor serializes every call for a physical device."""
import copy
import hashlib
import logging
import time
from pathlib import Path
from .core import PRESETS, Profiles, profile, number
from .errors import BorealError
from .library import media_call, asset
from .media import sensors, sensor_records
from .transport import runtime_dir
from .i18n import _

LOG = logging.getLogger('boreal.device')


def device_state(info):
    return dict(info, connected=False, status={}, updated=0, error='', active=_('Nicht verbunden'),
                stats=False, latched=False, cooling_error='', rgb_error='', history=[],
                display={'mode': None, 'desired': {}, 'sent': {}, 'observed': {}, 'error': '', 'options': {}},
                rgb_settings={}, active_profile=None, last_screen=0)


class Controller:
    def __init__(self, worker, profiles=None):
        self.worker = worker
        self.profiles = profiles or Profiles()
        self.devices = {}
        self.host = {}

    def snapshot(self):
        now = time.monotonic()
        devices = []
        for item in self.devices.values():
            data = copy.deepcopy(item)
            data.pop('selector', None)
            data['age'] = round(now-item['updated'], 1) if item['updated'] else None
            data['stale'] = data['age'] is None or data['age'] > 12
            if data['stale']: data['status'] = {}
            devices.append(data)
        return dict(devices=devices, host=copy.deepcopy(self.host))

    def discover(self):
        if any(x['connected'] for x in self.devices.values()):
            return self.snapshot()
        self.worker.close()
        found = self.worker.call('discover')
        self.devices = {d['id']: device_state(d) for d in found}
        return self.snapshot()

    def fault(self, item, reason, latched=True):
        item.update(error=str(reason), stats=False, status={}, updated=0, connected=False,
                    active=_('Fehler · Verbindung prüfen'), latched=latched, cooling_error=str(reason))
        try:
            if self.worker.process is None:
                raise RuntimeError(_('USB-Sitzung verloren; Fallback nicht bestätigt'))
            self.worker.call('fallback', item['id'])
            item['error'] += _(' · 100%-Fallback gesendet')
        except Exception as exc:
            item['error'] += _(' · Fallback unbestätigt: {error}').format(error=exc)
        try:
            if self.worker.process is not None:
                self.worker.call('detach', item['id'])
        except Exception:
            pass
        LOG.error('Gerätefehler %s: %s', item['id'], item['error'])

    @staticmethod
    def check_status(status):
        for key, low, high in (('Liquid temperature', 1, 80), ('Pump speed', 1, 20000)):
            try:
                number(status[key]['value'], low, high)
                expected = '°C' if key == 'Liquid temperature' else 'rpm'
                if status[key]['unit'] != expected: raise ValueError(_('Einheit'))
            except (KeyError, ValueError, TypeError):
                raise RuntimeError(_('Fehlender oder ungültiger Sensor: {sensor}').format(sensor=key)) from None
        if status['Liquid temperature']['value'] >= 50:
            raise RuntimeError(_('Wassertemperatur ≥50°C'))
        return status

    def sample(self, item):
        value = self.check_status(self.worker.call('status', item['id']))
        item.update(status=value, updated=time.monotonic(), measured_at=time.time())
        item['history'].append([time.time(), value['Liquid temperature']['value'], value['Pump speed']['value'],
                                value.get('Fan speed', {}).get('value')])
        cutoff=time.time()-720
        item['history'][:]=[row for row in item['history'] if row[0]>=cutoff][-1441:]

    def cosmetic_fault(self, item, exc, component):
        if component == 'display':
            item['stats'] = False
            item['display']['error'] = str(exc)
        else:
            item['rgb_error'] = str(exc)
        # A failed decoration is isolated only if the same USB session still has valid cooling telemetry.
        try:
            if self.worker.process is None: raise ConnectionError(_('USB-Prozess beendet'))
            self.sample(item)
        except Exception as sensor_error:
            self.fault(item, sensor_error, latched=not isinstance(sensor_error, (ConnectionError, TimeoutError)))
            raise BorealError(item['error'], 'connection', 'cooling') from exc
        raise BorealError(str(exc), 'display' if component == 'display' else 'rgb', component, True) from exc

    def render_stats(self, item):
        path = runtime_dir() / f"stats-{item['id']}.png"
        media_call('stats', size=item['lcd'], status=item['status'], host=self.host,
                   destination=str(path), options=item['display']['options'])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item.get('screen_hash'):
            self.worker.call('screen', item['id'], 'static', str(path))
            item['screen_hash'] = digest
        item['display'].update(mode='stats', preview=str(path), error='')
        item['last_screen'] = time.monotonic()

    def tick(self):
        self.host = sensors()
        self.host['_sensors'] = sensor_records()
        for item in self.devices.values():
            if not item['connected']: continue
            try:
                self.sample(item)
            except Exception as exc:
                if isinstance(exc,TimeoutError):item['telemetry_timeouts']=item.get('telemetry_timeouts',0)+1
                self.fault(item, exc, latched=not isinstance(exc, (ConnectionError, TimeoutError)))
                continue
            if item['stats'] and time.monotonic()-item['last_screen'] >= 10:
                try: self.render_stats(item)
                except Exception as exc:
                    try: self.cosmetic_fault(item, exc, 'display')
                    except BorealError: LOG.warning('Stats gestoppt: %s', exc)

    def dispatch(self, req):
        if not isinstance(req, dict) or req.get('v') not in (1, 2):
            raise ValueError(_('Protokollversion 2 erforderlich'))
        op = req.get('op')
        if op == 'snapshot': return self.snapshot()
        if op == 'discover': return self.discover()
        if op == 'profiles': return self.profiles.read()
        if op == 'save_profile':
            self.profiles.save(req['name'], req['profile']); return self.profiles.read()
        if op == 'delete_profile':
            self.profiles.delete(req['name']); return self.profiles.read()
        if op not in {'attach','detach','apply','screen','color','emergency','pause_stats','resume_stats','lights_off','restore_lights'}:
            raise ValueError(_('Unbekannte Aktion'))
        key = req.get('device')
        if key not in self.devices: raise ValueError(_('Gerät nicht gefunden'))
        item = self.devices[key]
        if op == 'attach':
            if item['blocked']: raise ValueError(item['blocked'])
            if item['connected']: return self.snapshot()
            try:
                item.update(self.worker.call('attach', key))
                self.worker.call('fallback', key)
                self.sample(item)
                item.update(connected=True, error='', cooling_error='', latched=False, active=_('Sicher · 100%'), stats=False)
                item['display']['observed'] = {k:item.get(k) for k in ('brightness','orientation')}
            except Exception as exc:
                self.fault(item, exc); raise BorealError(item['error'], 'cooling', 'cooling') from exc
            return self.snapshot()
        if not item['connected']: raise BorealError(_('Gerät zuerst verbinden'), 'connection', 'connection', True)
        if op in ('pause_stats','resume_stats'):
            if item['display']['mode']!='stats': raise ValueError(_('Keine Statistikvorlage eingerichtet'))
            if op=='pause_stats': item['stats']=False; return self.snapshot()
            return self.dispatch(dict(req,op='screen',mode='stats',options=item['display']['options']))
        if op in ('lights_off','restore_lights'):
            values=item.get('rgb_last_on',{})
            if op=='restore_lights' and not values: raise ValueError(_('Keine Beleuchtung gespeichert'))
            for zone in list(item['colors']):
                if op=='lights_off': self.dispatch(dict(req,op='color',channel=zone,mode='off',hex='000000',brightness=0))
                elif zone in values: self.dispatch(dict(req,op='color',channel=zone,**values[zone]))
            return self.snapshot()
        value = None
        if op == 'apply': value = profile(req['profile'])
        if op == 'color':
            modes = ('fixed','off') if item['pid']=='3012' else ('fixed','off','breathing')
            if req.get('channel') not in item['colors'] or req.get('mode') not in modes:
                raise ValueError(_('RGB-Kanal oder Effekt wird nicht unterstützt'))
            color = req.get('hex','')
            if not isinstance(color,str) or len(color)!=6 or any(c not in '0123456789abcdefABCDEF' for c in color):
                raise ValueError(_('RGB-Farbe benötigt sechs Hex-Zeichen'))
            number(req.get('brightness',100),0,100)
            value = [[int(color[i:i+2],16) for i in (0,2,4)]] if req['mode']!='off' else []
        if op == 'screen':
            if not item['lcd']: raise ValueError(_('Dieses Gerät hat kein unterstütztes LCD'))
            mode, value = req.get('mode'), req.get('value')
            if mode not in ('liquid','static','gif','stats','brightness','orientation'):
                raise ValueError(_('Unbekannter LCD-Modus'))
            if mode=='gif' and not item['gif']: raise ValueError(_('GIF für diese Firmware nicht freigegeben'))
            if mode=='brightness': number(value,0,100)
            if mode=='orientation' and (type(value)!=int or value not in (0,90,180,270)):
                raise ValueError(_('Rotation: 0, 90, 180 oder 270'))
            if mode in ('static','gif'):
                if req.get('media_id'):
                    value, record = asset(req['media_id']); value = str(value)
                    if (record['format']=='gif') != (mode=='gif'): raise ValueError(_('Medientyp stimmt nicht überein'))
                else:
                    record = media_call('import', path=value, mode=mode, size=item['lcd'], options=req.get('options',{}))
                    value = record['path']
        # Cooling sample failure is never treated as a merely cosmetic error.
        if op in ('apply','screen','color'):
            try: self.sample(item)
            except Exception as exc:
                self.fault(item, exc); raise BorealError(item['error'], 'cooling', 'cooling') from exc
        try:
            if op == 'apply':
                self.worker.call('curves',key,value)
                item.update(active=req.get('name',_('Eigene Kurve angewandt'))[:64], active_profile=value, cooling_error='')
            elif op in ('emergency','detach'):
                self.worker.call('fallback',key)
                item.update(active=_('Sicher · 100%'),stats=False,active_profile=None)
                if op=='detach':
                    self.worker.call('detach',key); item.update(connected=False,status={},updated=0)
            elif op=='color':
                args=[key,req['channel'],req['mode'],value]
                if 'brightness' in req: args.append(req['brightness'])
                self.worker.call('color',*args)
                item['rgb_settings'][req['channel']]={k:req.get(k,100 if k=='brightness' else None) for k in ('mode','hex','brightness')}
                if req['mode']!='off' and req.get('brightness',100)>0:
                    item.setdefault('rgb_last_on',{})[req['channel']]=dict(item['rgb_settings'][req['channel']])
                item['rgb_error']=''
            elif op=='screen':
                display=item['display']; old_stats=item['stats']; item['stats']=False
                if mode in ('orientation','brightness'):
                    display['desired'][mode]=value
                    self.worker.call('screen',key,mode,value)
                    display['sent'][mode]=value
                    observed=self.worker.call('display_info',key)
                    display['observed']=observed
                    if observed.get(mode)!=value: raise RuntimeError(_('LCD-Einstellung wurde nicht bestätigt'))
                    if mode=='orientation':
                        item.pop('screen_hash',None)
                        if display['mode'] in ('static','gif'):
                            self.worker.call('screen',key,display['mode'],display['path'])
                    item['stats']=old_stats
                    item['last_screen']=0
                elif mode=='stats':
                    # Validate and render immediately before committing the template.
                    previous=display['options']; display['options']=req.get('options', previous)
                    item.pop('screen_hash',None)
                    try: self.render_stats(item)
                    except Exception:
                        display['options']=previous; raise
                    item['stats']=True
                else:
                    self.worker.call('screen',key,mode,value)
                    display.update(mode=mode)
                    if mode in ('static','gif'):
                        display.update(path=value,media_id=record['id'],preview=record['preview'])
                    else:
                        for field in ('path','media_id','preview'): display.pop(field,None)
                display['error']=''
            LOG.info('Aktion %s erfolgreich request=%s device=%s',op,req.get('request_id','internal'),key)
        except Exception as exc:
            if op in ('screen','color'):
                self.cosmetic_fault(item,exc,'display' if op=='screen' else 'rgb')
            self.fault(item,exc)
            raise BorealError(item['error'],'cooling','cooling') from exc
        return self.snapshot()

    def close(self):
        for item in self.devices.values():
            if item['connected']:
                try: self.worker.call('fallback',item['id'])
                except Exception: LOG.exception('Fallback beim Dienstende unbestätigt')
                try: self.worker.call('detach',item['id'])
                except Exception: pass
                item.update(connected=False,stats=False,status={})
        self.worker.close()


def run(demo=False):
    from .runtime import run as serve
    serve(demo)
