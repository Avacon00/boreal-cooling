from gi.repository import Gio, GLib
import copy
from .i18n import _
XML = '''<node><interface name="org.kde.StatusNotifierItem">
<method name="Activate"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
<method name="SecondaryActivate"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
<method name="ContextMenu"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
<property name="Category" type="s" access="read"/>
<property name="Id" type="s" access="read"/>
<property name="Title" type="s" access="read"/>
<property name="Status" type="s" access="read"/>
<property name="IconPixmap" type="a(iiay)" access="read"/>
<property name="IconName" type="s" access="read"/>
<property name="ItemIsMenu" type="b" access="read"/>
<property name="Menu" type="o" access="read"/>
</interface></node>'''

MENU_XML = """<node><interface name="com.canonical.dbusmenu">
<property name="Version" type="u" access="read"/><property name="TextDirection" type="s" access="read"/><property name="Status" type="s" access="read"/>
<method name="GetLayout"><arg type="i" direction="in"/><arg type="i" direction="in"/><arg type="as" direction="in"/><arg type="u" direction="out"/><arg type="(ia{sv}av)" direction="out"/></method>
<method name="GetGroupProperties"><arg type="ai" direction="in"/><arg type="as" direction="in"/><arg type="a(ia{sv})" direction="out"/></method>
<method name="AboutToShow"><arg type="i" direction="in"/><arg type="b" direction="out"/></method>
<method name="Event"><arg type="i" direction="in"/><arg type="s" direction="in"/><arg type="v" direction="in"/><arg type="u" direction="in"/></method>
<signal name="LayoutUpdated"><arg type="u"/><arg type="i"/></signal></interface></node>"""


class Tray:
    def __init__(self, action, availability, demo=False):
        self.action=action;self.availability=availability;self.demo=demo
        self.active=False;self.closed=False;self.connection=None;self.registrations=[];self.signals=[]
        self.ids={};self.nodes={};self.roots=[];self.revision=1;self.previous=None;self.generation=0
        self.watch=Gio.bus_watch_name(Gio.BusType.SESSION,'org.kde.StatusNotifierWatcher',Gio.BusNameWatcherFlags.NONE,self.appeared,self.vanished)

    def appeared(self,connection,name,owner):
        if self.closed:return
        self.connection=connection;self.generation+=1;generation=self.generation
        if not self.signals:
            for signal in ('StatusNotifierHostRegistered','StatusNotifierHostUnregistered'):
                self.signals.append(connection.signal_subscribe(name,name,signal,'/StatusNotifierWatcher',None,Gio.DBusSignalFlags.NONE,self.host_changed))
        if not self.registrations:
            self.registrations.append(connection.register_object('/Menu',Gio.DBusNodeInfo.new_for_xml(MENU_XML).interfaces[0],self.menu_method,lambda c,s,p,i,n: GLib.Variant('u',3) if n=='Version' else GLib.Variant('s','ltr' if n=='TextDirection' else 'normal'),None))
            self.registrations.append(connection.register_object('/StatusNotifierItem',Gio.DBusNodeInfo.new_for_xml(XML).interfaces[0],self.method,self.prop,None))
        def checked(conn,result):
            if self.closed or generation!=self.generation:return
            try:
                present=conn.call_finish(result).unpack()[0]
                if not present:self.set_active(False);return
                conn.call(name,'/StatusNotifierWatcher',name,'RegisterStatusNotifierItem',GLib.Variant('(s)',(conn.get_unique_name(),)),None,Gio.DBusCallFlags.NONE,2000,None,registered)
            except GLib.Error:self.set_active(False)
        def registered(conn,result):
            if self.closed or generation!=self.generation:return
            try:conn.call_finish(result);self.set_active(True)
            except GLib.Error:self.set_active(False)
        connection.call(name,'/StatusNotifierWatcher','org.freedesktop.DBus.Properties','Get',GLib.Variant('(ss)',(name,'IsStatusNotifierHostRegistered')),None,Gio.DBusCallFlags.NONE,2000,None,checked)

    def host_changed(self,c,s,p,i,name,args):
        if name=='StatusNotifierHostUnregistered':self.vanished()
        else:self.appeared(c,'org.kde.StatusNotifierWatcher',s)

    def set_active(self,value):
        if self.active!=value:self.active=value;self.availability(value)

    def vanished(self,*_):
        self.generation+=1;self.set_active(False)

    def close(self):
        self.closed=True;Gio.bus_unwatch_name(self.watch)
        if self.connection:
            for registration in self.registrations:self.connection.unregister_object(registration)
            for subscription in self.signals:self.connection.signal_unsubscribe(subscription)
        self.registrations=[];self.active=False

    def update(self,roots):
        if roots==self.previous:return
        self.previous=copy.deepcopy(roots);self.roots=roots;self.nodes={}
        def visit(nodes):
            for n in nodes:
                self.ids.setdefault(n['key'],len(self.ids)+1);self.nodes[self.ids[n['key']]]=n;visit(n['children'])
        visit(roots);self.revision+=1
        if self.connection:
            self.connection.emit_signal(None,'/Menu','com.canonical.dbusmenu','LayoutUpdated',GLib.Variant('(ui)',(self.revision,0)))

    def prop(self,c,s,p,i,name):
        values={'Category':'Hardware','Id':'boreal-demo' if self.demo else 'boreal','Title':_('Boreal Demo') if self.demo else 'Boreal','Status':'Active','IconName':'io.boreal.Cooling'}
        if name in values:return GLib.Variant('s',values[name])
        if name=='IconPixmap':
            pixels=bytearray()
            for y in range(32):
                for x in range(32):
                    inside=(x-16)**2+(y-16)**2<225
                    drop=(x-16)**2+(y-20)**2<64 or (10<=y<=20 and abs(x-16)<(y-7)*.55)
                    pixels.extend((255,108,229,192) if inside and drop else ((255,21,44,48) if inside else (0,0,0,0)))
            return GLib.Variant('a(iiay)',[(32,32,bytes(pixels))])
        if name=='ItemIsMenu':return GLib.Variant('b',True)
        if name=='Menu':return GLib.Variant('o','/Menu')

    def method(self,c,s,p,i,name,parameters,invocation):
        # Menu hosts consume /Menu. Activation must never open the main window.
        invocation.return_value(None)

    def properties(self,n):
        props={'label':GLib.Variant('s',n['label']),'enabled':GLib.Variant('b',n['enabled']),'visible':GLib.Variant('b',True)}
        if n['children']:props['children-display']=GLib.Variant('s','submenu')
        if n['checked'] is not None:
            props['toggle-type']=GLib.Variant('s','radio');props['toggle-state']=GLib.Variant('i',int(n['checked']))
        return props

    def menu_method(self,c,s,p,i,name,parameters,invocation):
        args=parameters.unpack()
        def layout(index,depth):
            n=self.nodes.get(index);children=self.roots if index==0 else n['children']
            return (index,{} if n is None else self.properties(n),[GLib.Variant('(ia{sv}av)',layout(self.ids[x['key']],depth-1)) for x in children] if depth!=0 else [])
        try:
            if name=='GetLayout':invocation.return_value(GLib.Variant('(u(ia{sv}av))',(self.revision,layout(args[0],args[1]))))
            elif name=='GetGroupProperties':invocation.return_value(GLib.Variant('(a(ia{sv}))',([(k,self.properties(n)) for k,n in self.nodes.items() if not args[0] or k in args[0]],)))
            elif name=='AboutToShow':invocation.return_value(GLib.Variant('(b)',(False,)))
            elif name=='Event':
                node=self.nodes.get(args[0])
                if args[1]=='clicked' and node and node['enabled'] and node['command']:self.action(copy.deepcopy(node['command']))
                invocation.return_value(None)
            else:invocation.return_dbus_error('org.freedesktop.DBus.Error.UnknownMethod','Unknown menu method')
        except Exception as exc:invocation.return_dbus_error('org.freedesktop.DBus.Error.Failed',str(exc))
