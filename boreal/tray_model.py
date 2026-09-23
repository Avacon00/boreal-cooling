"""Pure menu model. Each command captures its device and saved settings."""
import copy
from .core import TEST_PRESETS
from .i18n import _, profile_label


def menu(snapshot, profiles, selected, busy=False):
    devices=snapshot.get('devices',[])
    d=next((d for d in devices if d['id']==selected),{})
    key=d.get('id'); connected=bool(d.get('connected')); usable=connected and not busy
    def node(key,label,command=None,enabled=True,children=None,checked=None):
        return dict(key=key,label=label,command=command,enabled=enabled,children=children or [],checked=checked)
    nodes=[node('open',_('Boreal öffnen'),{'page':'overview'})]
    water=d.get('status',{}).get('Liquid temperature',{}).get('value')
    measured=_('Messwerte veraltet') if d.get('stale') else str(water)+' °C'
    active=profile_label(d.get('active',_('Nicht verbunden')))
    nodes.append(node('status',f"{d.get('name',_('Kein Gerät'))} · {measured} · {active}",enabled=False))
    if len(devices)>1:
        nodes.append(node('devices',_('Gerät'),children=[node('device:'+x['id'],x['name'],{'select':x['id']},checked=x['id']==key) for x in devices]))
    normal=[];tests=[]
    for name,value in profiles.items():
        n=node('profile:'+name,profile_label(name),dict(op='apply',device=key,profile=copy.deepcopy(value),name=name),usable,checked=connected and d.get('active_profile')==value)
        (tests if name in TEST_PRESETS else normal).append(n)
    if tests:normal.append(node('tests',_('Testprofile'),children=tests))
    nodes.append(node('profiles',_('Kühlprofil'),children=normal))
    nodes.append(node('emergency',_('Volle Kühlleistung'),dict(op='emergency',device=key),connected))
    display=d.get('display',{});lcd=usable and bool(d.get('lcd'))
    nodes.append(node('display',_('Display'),children=[
        node('liquid',_('Kühlmitteltemperatur anzeigen'),dict(op='screen',device=key,mode='liquid'),lcd),
        node('stats',_('Live-Stats pausieren') if d.get('stats') else _('Live-Stats fortsetzen'),dict(op='pause_stats' if d.get('stats') else 'resume_stats',device=key),lcd and display.get('mode')=='stats'),
        node('display-page',_('Display öffnen'),{'page':'display'})]))
    nodes.append(node('rgb',_('Beleuchtung'),children=[
        node('rgb-off',_('Beleuchtung ausschalten'),dict(op='lights_off',device=key),usable and bool(d.get('colors'))),
        node('rgb-restore',_('Letzte Beleuchtung wiederherstellen'),dict(op='restore_lights',device=key),usable and bool(d.get('rgb_last_on'))),
        node('rgb-page',_('Beleuchtung öffnen'),{'page':'rgb'})]))
    nodes.extend([node('settings',_('Einstellungen öffnen'),{'page':'settings'}),node('quit',_('Oberfläche beenden'),{'quit':True})])
    return nodes
