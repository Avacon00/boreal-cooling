"""Adaptive native application; all service calls and file I/O leave GTK's main loop."""
import copy
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
import gi
gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')
from gi.repository import Adw,Gtk,Gio,GLib,Gdk
from .core import PRESETS,profile,state_dir,atomic_json
from .diagnostics import configure
from .errors import BorealError
from .i18n import _, profile_label
from .transport import request
from .widgets import text,box,button,card,RoundPreview,CurveEditor,HistoryChart,ColorPicker

LOG=logging.getLogger('boreal.ui')
CSS=b'''
.lcd-control { min-width: 48px; }
.hero { font-size: 26px; font-weight: 700; }
.metric { font-size: 26px; font-weight: 700; }
.mint { color: #289b76; }
.sidebar-row { padding: 10px; }
.error-text { color: #c64646; }
'''


class App(Adw.Application):
    def __init__(self,demo=True,smoke=False,window_size=(1100,800)):
        super().__init__(application_id='io.boreal.Cooling.Demo' if demo else 'io.boreal.Cooling')
        self.window_size=window_size
        self.demo=demo; self.smoke=smoke; self.window=None; self.closed=False
        self.pool=ThreadPoolExecutor(max_workers=6,thread_name_prefix='ui-rpc')
        self.tray_busy=False
        self.refresh_ms=1000;self.poll_source=0;self.media_busy=False
        self.polling=False; self.pending=0; self.dialogs={}; self.snapshot={'devices':[],'host':{}}
        self.profiles=copy.deepcopy(PRESETS); self.media=[]; self.selected_media=None; self.media_source=None
        self.clean_profile=copy.deepcopy(PRESETS['Ausgewogen']); self.dirty=False; self.theme_loaded=False
        self.preview_key=None; self.last_fault=None; self.tray=None; self.loading=False; self.language_loaded=False
        self.connect('activate',self.activate); self.connect('shutdown',self.shutdown)

    def shutdown(self,*_args):
        self.closed=True
        if self.tray:self.tray.close()
        if self.poll_source:GLib.source_remove(self.poll_source);self.poll_source=0
        for _,cancel in self.dialogs.values(): cancel.cancel()
        self.dialogs.clear()
        for preview in (getattr(self,'lcd_preview',None),getattr(self,'overview_preview',None)):
            if preview: preview.stop()
        self.pool.shutdown(wait=False,cancel_futures=True)

    def activate(self,*_args):
        if self.window: self.window.present(); return
        self.window=Adw.ApplicationWindow(application=self,title='Boreal',default_width=self.window_size[0],default_height=self.window_size[1])
        self.window.set_size_request(640,480)
        Gtk.IconTheme.get_for_display(self.window.get_display()).add_search_path(str(Path(__file__).parent/'assets'))
        self.window.set_icon_name('io.boreal.Cooling')
        provider=Gtk.CssProvider(); provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(self.window.get_display(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.toasts=Adw.ToastOverlay(); self.window.set_content(self.toasts)
        root=box(spacing=0); self.toasts.set_child(root)
        self.split=Adw.OverlaySplitView(vexpand=True,sidebar_width_fraction=.23,min_sidebar_width=190,max_sidebar_width=250)
        breakpoint=Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 850sp'))
        breakpoint.add_setter(self.split,'collapsed',True); self.window.add_breakpoint(breakpoint)
        sidebar=box(spacing=8); sh=Adw.HeaderBar(); sh.set_title_widget(Adw.WindowTitle(title='BOREAL',subtitle=_('Demo') if self.demo else _('Kraken Control')))
        sidebar.append(sh)
        self.device_select=Gtk.DropDown.new_from_strings([_('Gerät wird gesucht …')])
        self.device_select.set_margin_start(10); self.device_select.set_margin_end(10)
        self.device_select.connect('notify::selected',self.device_changed); sidebar.append(self.device_select)
        nav=Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE);self.navigation=nav; nav.add_css_class('navigation-sidebar')
        self.pages=[('overview',_('Übersicht')),('cooling',_('Kühlung')),('display',_('Display')),('rgb',_('Beleuchtung')),('settings',_('Einstellungen'))]
        for key,name in self.pages:
            row=Gtk.ListBoxRow(); row.set_child(text(name)); row.add_css_class('sidebar-row'); row.page=key; nav.append(row)
        nav.connect('row-selected',self.navigate); sidebar.append(nav)
        spacer=box(); spacer.set_vexpand(True); sidebar.append(spacer)
        sidebar.append(button('Geräte aktualisieren',lambda:self.call('discover')))
        sidebar.append(text('SIMULIERTE GERÄTE' if self.demo else 'Lokal · ohne Cloud','dim-label'))
        self.split.set_sidebar(sidebar)
        main=box(spacing=0); header=Adw.HeaderBar()
        menu_button=Gtk.Button(icon_name='sidebar-show-symbolic')
        menu_button.connect('clicked',lambda *_:self.split.set_show_sidebar(not self.split.get_show_sidebar()))
        menu_button.set_tooltip_text(_('Navigation ein-/ausblenden')); header.pack_start(menu_button)
        self.title=Adw.WindowTitle(title=_('Übersicht'),subtitle='Boreal'); header.set_title_widget(self.title)
        self.to_tray=Gtk.Button(icon_name='go-down-symbolic',tooltip_text=_('In den Tray'));self.to_tray.set_sensitive(False)
        self.to_tray.connect('clicked',lambda *_:self.on_close());header.pack_end(self.to_tray)
        main.append(header)
        self.banner=Adw.Banner(title='',revealed=False); main.append(self.banner)
        self.stack=Gtk.Stack(vexpand=True,transition_type=Gtk.StackTransitionType.CROSSFADE); main.append(self.stack)
        self.split.set_content(main); root.append(self.split)
        bar=Gtk.ActionBar(); self.operation=text('Bereit','dim-label'); bar.pack_start(self.operation)
        self.emergency=button('Volle Kühlleistung',lambda:self.action('emergency'),'destructive-action'); bar.pack_end(self.emergency)
        root.append(bar)
        self.build_overview(); self.build_cooling(); self.build_display(); self.build_rgb(); self.build_settings()
        self.label_controls()
        nav.select_row(nav.get_row_at_index(0))
        self.window.connect('close-request',self.on_close)
        self.window.present()
        try:
            from .tray import Tray
            self.tray=Tray(self.tray_action,self.tray_available,self.demo)
        except Exception: LOG.info('Kein Tray verfügbar',exc_info=True)
        self.tray_note.set_text(_('Tray verfügbar') if self.tray and self.tray.active else _('Kein Tray-Host erkannt; Boreal bleibt über den Programmstarter erreichbar.'))
        self.call('snapshot',done=self.update)
        self.call('profiles',done=self.update_profiles)
        self.call('media',done=self.update_media)
        self.poll_source=GLib.timeout_add(self.refresh_ms,self.poll)
        if self.smoke: GLib.timeout_add_seconds(4,lambda:(self.quit(),False)[1])

    def label_controls(self):
        labels={'device_select':'Kraken-Gerät','refresh_select':'Messwerte aktualisieren',
                'profile_select':'Kühlprofil','profile_name':'Name des eigenen Profils',
                'library_select':'Medienbibliothek','fit':'Bilddarstellung','zoom':'Vergrößerung',
                'crop_x':'Position horizontal','crop_y':'Position vertikal','background_color':'Hintergrundfarbe',
                'rotation':'Display-Ausrichtung','brightness':'Display-Helligkeit in Prozent',
                'template':'Temperaturvorlage','accent':'Akzentfarbe','font_scale':'Schriftgröße',
                'unit':'Temperatureinheit','rgb_zone':'Beleuchtungszone','rgb_brightness':'Beleuchtungshelligkeit in Prozent',
                'theme':'Erscheinungsbild','language':'Oberflächensprache','restore_switch':'Automatische Gerätewiederherstellung'}
        for name,label in labels.items():
            widget=getattr(self,name,None)
            if widget:widget.update_property([Gtk.AccessibleProperty.LABEL],[_(label)])
        for index,widget in enumerate(self.sensor_widgets):
            widget.update_property([Gtk.AccessibleProperty.LABEL],[_('Sensor {number} der Temperaturvorlage').format(number=index+1)])

    def tray_available(self,active):
        if self.closed:return
        self.to_tray.set_sensitive(active)
        self.to_tray.set_tooltip_text(_('In den Tray') if active else _('Kein Tray-Bereich verfügbar'))
        self.tray_note.set_text(_('Tray verfügbar · X blendet Boreal aus') if active else _('Kein Tray verfügbar; Fenster bleibt über den Programmstarter erreichbar.'))
        if not active and not self.window.get_visible():self.window.present()
        self.refresh_tray()

    def refresh_tray(self):
        if not self.tray:return
        from .tray_model import menu
        self.tray.update(menu(self.snapshot,self.profiles,(self.selected() or {}).get('id'),self.tray_busy))

    def tray_action(self,command):
        if 'page' in command:
            self.show_page(command['page']);self.window.present();return
        if 'select' in command:
            ids=[d['id'] for d in self.snapshot['devices']]
            if command['select'] in ids:self.device_select.set_selected(ids.index(command['select']))
            return
        if command.get('quit'):self.quit();return
        if self.tray_busy and command['op']!='emergency':return
        self.tray_busy=True;self.refresh_tray()
        def run():
            try:return request(self.demo,**command)
            finally:GLib.idle_add(unlock)
        def unlock():
            self.tray_busy=False;self.refresh_tray();self.poll();return False
        self.background(run,lambda _:self.poll())

    def on_close(self,*_args):
        for _,cancel in self.dialogs.values(): cancel.cancel()
        if self.tray and self.tray.active:
            self.window.set_visible(False); return True
        return False

    def page(self,key,title,subtitle):
        layout=box(spacing=0)
        scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        clamp=Adw.Clamp(maximum_size=950,tightening_threshold=700)
        content=box(spacing=16)
        for side in ('top','bottom','start','end'): getattr(content,'set_margin_'+side)(20)
        content.append(text(title,'hero')); content.append(text(subtitle,'dim-label'))
        clamp.set_child(content); scroll.set_child(clamp); layout.append(scroll)
        self.stack.add_named(layout,key)
        return content,layout

    def build_overview(self):
        content,_layout=self.page('overview','Deine Kühlung im Blick','Temperaturen, aktives Profil und Display auf einen Blick.')
        refresh_group=Adw.PreferencesGroup()
        self.refresh_select=Gtk.DropDown.new_from_strings([_('0,5 Sekunden'),_('1 Sekunde'),_('2 Sekunden'),_('3 Sekunden'),_('5 Sekunden')])
        self.refresh_select.set_selected(1);self.refresh_select.connect('notify::selected',self.refresh_changed)
        refresh_row=Adw.ActionRow(title=_('Messwerte aktualisieren'));refresh_row.add_suffix(self.refresh_select);refresh_group.add(refresh_row);content.append(refresh_group)
        self.setup=Adw.PreferencesGroup(title=_('Einrichtung'))
        self.setup_row=Adw.ActionRow(title=_('Kraken verbinden'),subtitle=_('Mit einem Klick sichere Ausgangswerte setzen und das ausgewogene Profil übernehmen.'))
        self.connect_button=button('Einrichten',lambda:self.action('onboard'),'suggested-action')
        self.setup_row.add_suffix(self.connect_button); self.setup.add(self.setup_row); content.append(self.setup)
        grid=Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,homogeneous=True,min_children_per_line=1,max_children_per_line=3,column_spacing=8,row_spacing=8)
        self.metrics={}
        for key,name in (('Liquid temperature','Wasser'),('Pump speed','Pumpe'),('Fan speed','Lüfter'),('CPU','CPU (Maximum)'),('GPU','GPU (Maximum)')):
            outer,inner=card(name); value=text('—','metric'); inner.append(value); self.metrics[key]=value; grid.insert(outer,-1)
        content.append(grid)
        self.device_note=text('Gerät wird erkannt …','dim-label'); content.append(self.device_note)
        self.active_label=text('Kein Profil aktiv','title-3'); content.append(self.active_label)
        self.overview_preview=RoundPreview(200); content.append(self.overview_preview)
        self.history=HistoryChart(); content.append(self.history)
        self.sensor_note=text('Sensoren werden eingelesen …','dim-label'); content.append(self.sensor_note)

    def build_cooling(self):
        content,layout=self.page('cooling','Kühlung','Kurven laufen auf der Kraken weiter, auch wenn das Fenster geschlossen ist.')
        self.profile_select=Gtk.DropDown.new_from_strings([profile_label(name) for name in self.profiles]); self.profile_select.set_selected(1)
        self.profile_select.connect('notify::selected',lambda *_:self.load_profile())
        content.append(text('Kühlprofil'));content.append(self.profile_select)
        self.profile_name=Gtk.Entry(placeholder_text=_('Name für eigenes Profil'));content.append(text('Name des eigenen Profils'));content.append(self.profile_name)
        flow=Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,max_children_per_line=3,column_spacing=6,row_spacing=6)
        for title,callback in [('Speichern / Duplizieren',self.save_profile),('Umbenennen',self.rename_profile),('Löschen',self.delete_profile),('Importieren',self.import_profile),('Exportieren',self.export_profile)]:
            flow.insert(button(title,callback),-1)
        content.append(flow)
        self.editors={}
        for channel in ('pump','fan'):
            outer,inner=card(); editor=CurveEditor(channel,PRESETS['Ausgewogen'][channel],self.curve_changed)
            self.editors[channel]=editor; inner.append(editor); content.append(outer)
        self.curve_error=text('','error-text'); content.append(self.curve_error)
        content.append(text('Pumpe ≥60%, Lüfter ≥30%. Bei 50 °C immer 100%. Orange Linie: aktuelle Wassertemperatur.','dim-label'))
        footer=Gtk.ActionBar(); self.draft=text('Keine Änderungen','dim-label'); footer.pack_start(self.draft)
        footer.pack_end(button('Verwerfen',self.discard_profile))
        self.apply_button=button('Anwenden',self.apply_profile,'suggested-action'); footer.pack_end(self.apply_button)
        layout.append(footer)

    def build_display(self):
        content,layout=self.page('display','Dein Display','Medien und Vorlagen vorbereiten. Erst „Anzeigen“ überträgt den Inhalt.')
        content.append(text('Vorschau','title-3'));self.lcd_preview=RoundPreview(200);content.append(self.lcd_preview)
        self.lcd_state=text('Noch kein Inhalt','dim-label'); content.append(self.lcd_state)
        self.library_select=Gtk.DropDown.new_from_strings([_('Medienbibliothek leer')])
        self.library_select.connect('notify::selected',self.choose_library); content.append(self.library_select)
        row=box(False); row.append(button('Bild hinzufügen',lambda:self.choose_media('static'))); row.append(button('GIF hinzufügen',lambda:self.choose_media('gif'))); content.append(row)
        self.fit=Gtk.DropDown.new_from_strings([_('Einpassen'),_('Zuschneiden')])
        self.zoom=Gtk.SpinButton.new_with_range(1,3,.1); self.zoom.set_value(1)
        self.crop_x=Gtk.SpinButton.new_with_range(0,1,.05); self.crop_x.set_value(.5)
        self.crop_y=Gtk.SpinButton.new_with_range(0,1,.05); self.crop_y.set_value(.5)
        self.background_color=Gtk.Entry(text='#101d29')
        group=Adw.PreferencesGroup(title=_('Bildausschnitt'))
        for title,widget in [('Darstellung',self.fit),('Vergrößerung',self.zoom),('Position horizontal',self.crop_x),('Position vertikal',self.crop_y),('Hintergrundfarbe',self.background_color)]:
            row=Adw.ActionRow(title=_(title)); row.add_suffix(widget); group.add(row)
        content.append(group); content.append(button('Vorschau neu berechnen',self.reprocess))
        group=Adw.PreferencesGroup(title=_('Display-Einstellungen'))
        self.rotation=Gtk.DropDown.new_from_strings(['0°','90°','180°','270°'])
        row=Adw.ActionRow(title=_('Ausrichtung')); row.add_suffix(self.rotation)
        row.add_suffix(button('Drehen',self.rotate)); group.add(row)
        self.brightness=Gtk.SpinButton.new_with_range(0,100,5)
        row=Adw.ActionRow(title=_('Helligkeit')); row.add_suffix(self.brightness)
        row.add_suffix(button('Setzen',lambda:self.action('screen',mode='brightness',value=self.brightness.get_value_as_int()))); group.add(row)
        content.append(group)
        templates=Adw.PreferencesGroup(title=_('Temperaturvorlagen'))
        self.template=Gtk.DropDown.new_from_strings([_('Einzeltemperatur'),_('Zwei Sensoren'),_('Übersicht')])
        row=Adw.ActionRow(title=_('Vorlage')); row.add_suffix(self.template); templates.add(row)
        self.sensor_ids=['liquid','CPU','GPU']; self.sensor_widgets=[]
        for i in range(3):
            widget=Gtk.DropDown.new_from_strings([_('Wasser'),_('CPU (Maximum)'),_('GPU (Maximum)')]); widget.set_selected(i)
            row=Adw.ActionRow(title=_('Sensor {number}').format(number=i+1)); row.add_suffix(widget); templates.add(row); self.sensor_widgets.append(widget)
        self.accent=Gtk.Entry(text='#6ce5c0'); self.font_scale=Gtk.SpinButton.new_with_range(.7,1.5,.1); self.font_scale.set_value(1)
        self.unit=Gtk.DropDown.new_from_strings(['°C','°F'])
        for title,widget in [('Akzentfarbe',self.accent),('Schriftgröße',self.font_scale),('Einheit',self.unit)]:
            row=Adw.ActionRow(title=_(title)); row.add_suffix(widget); templates.add(row)
        content.append(templates)
        content.append(button('Vorlage auf LCD anzeigen',self.apply_template))
        content.append(button('Native Wassertemperatur anzeigen',lambda:self.action('screen',mode='liquid')))
        footer=Gtk.ActionBar(); self.media_label=text('Kein Medium ausgewählt','dim-label'); footer.pack_start(self.media_label)
        self.show_media=button('Bild auf Kraken anzeigen',self.apply_media,'suggested-action'); footer.pack_end(self.show_media); layout.append(footer)
        self.media_help=text('Überträgt das ausgewählte Bild auf das Display deiner Wasserkühlung.','dim-label');layout.append(self.media_help)

    def build_rgb(self):
        content,layout=self.page('rgb','Beleuchtung','Nur erkannte Zonen und geprüfte Funktionen werden angeboten.')
        self.rgb_note=text('Nach Verbindung verfügbar','dim-label'); content.append(self.rgb_note)
        self.rgb_group=Adw.PreferencesGroup()
        self.rgb_zone=Gtk.DropDown.new_from_strings([_('Keine Zone')])
        self.rgb_color=ColorPicker()
        self.rgb_brightness=Gtk.SpinButton.new_with_range(0,100,5); self.rgb_brightness.set_value(70)
        for title,widget in [('Zone',self.rgb_zone),('Helligkeit',self.rgb_brightness)]:
            row=Adw.ActionRow(title=_(title)); row.add_suffix(widget); self.rgb_group.add(row)
        content.append(self.rgb_group);content.append(self.rgb_color)
        self.rgb_apply=button('Farbe anwenden',lambda:self.apply_rgb('fixed'),'suggested-action'); footer=Gtk.ActionBar();footer.pack_end(self.rgb_apply)
        footer.pack_start(button('Beleuchtung ausschalten',lambda:self.apply_rgb('off')));layout.append(footer)

    def build_settings(self):
        content,_layout=self.page('settings','Einstellungen','Startverhalten, Erscheinungsbild und verständliche Diagnose.')
        group=Adw.PreferencesGroup(title=_('Alltag'))
        self.restore_switch=Gtk.Switch(valign=Gtk.Align.CENTER)
        self.restore_switch.connect('notify::active',self.restore_changed)
        row=Adw.ActionRow(title=_('Einstellungen automatisch wiederherstellen'),subtitle=_('Nur für dieses geprüfte Gerät. Nach kritischen Kühlfehlern ist eine Bestätigung nötig.'))
        row.add_suffix(self.restore_switch); group.add(row)
        content.append(group)
        content.append(button('Hintergrundstart beim Anmelden aktivieren',lambda:self.system_service(True)))
        content.append(button('Hintergrundstart deaktivieren',lambda:self.system_service(False)))
        self.theme=Gtk.DropDown.new_from_strings([_('System'),_('Hell'),_('Dunkel')]); self.theme.connect('notify::selected',self.theme_changed)
        group=Adw.PreferencesGroup(title=_('Erscheinungsbild')); row=Adw.ActionRow(title=_('Farbschema')); row.add_suffix(self.theme); group.add(row); content.append(group)
        self.language=Gtk.DropDown.new_from_strings([_('Systemsprache'),_('Deutsch'),_('English')])
        self.language.connect('notify::selected',self.language_changed)
        group=Adw.PreferencesGroup(title=_('Sprache'))
        row=Adw.ActionRow(title=_('Oberflächensprache'),subtitle=_('Die Systemsprache verwendet Deutsch auf einem deutschen Linux und sonst Englisch.'))
        row.add_suffix(self.language); group.add(row); content.append(group)
        self.tray_note=text('','dim-label'); content.append(self.tray_note)
        content.append(text('Fenster schließen lässt die Kühlung im Hintergrund aktiv. „Dienst beenden“ setzt nach Möglichkeit volle Kühlleistung.','dim-label'))
        content.append(button('Gerät freigeben',lambda:self.action('detach')))
        content.append(button('Diagnosebericht exportieren',lambda:self.call('diagnostics',done=self.save_diagnostics)))
        content.append(button('Log-Ordner öffnen',lambda:Gio.AppInfo.launch_default_for_uri(state_dir().as_uri(),None)))
        content.append(button('Dienst beenden',lambda:self.call('shutdown',done=lambda _:self.quit()),'destructive-action'))

    def show_page(self,page):
        keys=[key for key,_ in self.pages]
        if page not in keys:raise ValueError('Unbekannte Seite')
        self.navigation.select_row(self.navigation.get_row_at_index(keys.index(page)))
        self.stack.set_visible_child_name(page)
        self.title.set_title(dict(self.pages)[page])

    def navigate(self,listbox,row):
        if row:
            self.stack.set_visible_child_name(row.page)
            self.title.set_title(dict(self.pages)[row.page])
            if self.split.get_collapsed(): self.split.set_show_sidebar(False)

    def selected(self):
        i=self.device_select.get_selected() if hasattr(self,'device_select') else 0
        return self.snapshot['devices'][i] if i<len(self.snapshot['devices']) else None

    def device_changed(self,*_args):
        self.preview_key=None
        if hasattr(self,'metrics'): self.render()

    def notify(self,message):
        if not self.closed: self.toasts.add_toast(Adw.Toast.new(str(message)[:240]))

    def failure(self,exc):
        LOG.error('Bedienvorgang fehlgeschlagen: %s',exc)
        if self.window and not self.window.get_visible():
            note=Gio.Notification.new(_('Boreal: Aktion fehlgeschlagen'));note.set_body(str(exc)[:180]);self.send_notification('tray-error',note)
        self.banner.set_title(_('Fehler: {error}').format(error=str(exc)[:390])); self.banner.set_revealed(True)
        if isinstance(exc,(ConnectionError,FileNotFoundError,ConnectionRefusedError)) or getattr(exc,'code',None) in ('version','connection'):
            self.operation.set_text(_('Verbindung prüfen · letzte Messwerte können veraltet sein'))
        # Input/media errors NEVER falsify a healthy connection.

    def background(self,fn,done=None,quiet=False):
        if self.closed:return
        if not quiet:self.pending+=1;self.operation.set_text(_('{count} Vorgang/Vorgänge werden verarbeitet …').format(count=self.pending))
        future=self.pool.submit(fn)
        def finish(f):
            def deliver():
                if self.closed:return False
                if not quiet:self.pending-=1
                try:
                    result=f.result()
                    if done:done(result)
                    if not quiet:
                        self.operation.set_text(_('Übertragen / gespeichert') if not self.pending else _('{count} Vorgang/Vorgänge laufen …').format(count=self.pending))
                        fault=(self.selected() or {}).get('error')
                        self.banner.set_revealed(bool(fault))
                        if fault:self.banner.set_title(fault[:400])
                except Exception as exc:self.failure(exc)
                return False
            GLib.idle_add(deliver)
        future.add_done_callback(finish)

    def call(self,op,done=None,quiet=False,**args):
        self.background(lambda:request(self.demo,op,**args),done if done else lambda _:self.poll(),quiet)

    def action(self,op,**args):
        item=self.selected()
        if not item:self.notify(_('Zuerst ein Gerät auswählen'));return
        self.call(op,device=item['id'],**args)

    def poll(self):
        if self.closed:return False
        if self.polling:return True
        self.polling=True
        def fetch():
            try:return request(self.demo,'snapshot')
            finally:GLib.idle_add(lambda:(setattr(self,'polling',False),False)[1])
        self.background(fetch,self.update,quiet=True);return True

    def update(self,value):
        old=self.selected();old_id=old['id'] if old else None
        old_ids=[d['id'] for d in self.snapshot['devices']];self.snapshot=value
        ids=[d['id'] for d in value['devices']]
        if old_ids!=ids:
            self.device_select.set_model(Gtk.StringList.new([d['name'] for d in value['devices']] or [_('Kein Gerät gefunden')]))
            self.device_select.set_selected(ids.index(old_id) if old_id in ids else 0)
        if not self.theme_loaded:
            self.loading=True;self.theme.set_selected(['system','light','dark'].index(value.get('theme','system')))
            self.loading=False;self.theme_loaded=True;self.set_theme()
        if not self.language_loaded:
            self.loading=True; self.language.set_selected(['system','de','en'].index(value.get('language','system')))
            self.loading=False; self.language_loaded=True
        if value.get('refresh_notice'):
            self.banner.set_title(_(value['refresh_notice']));self.banner.set_revealed(True)
        interval=value.get('refresh_interval_ms',1000)
        if interval!=self.refresh_ms:
            self.refresh_ms=interval
            if self.poll_source:GLib.source_remove(self.poll_source)
            self.poll_source=GLib.timeout_add(interval,self.poll)
        self.loading=True;self.refresh_select.set_selected([500,1000,2000,3000,5000].index(interval));self.loading=False
        self.render()

    def refresh_changed(self,*_args):
        if not self.loading:self.call('set_refresh_interval',value=[500,1000,2000,3000,5000][self.refresh_select.get_selected()],done=self.update)

    def render(self):
        item=self.selected();connected=bool(item and item['connected'])
        self.connect_button.set_sensitive(bool(item and not connected and not item.get('blocked')))
        self.setup.set_visible(not connected)
        self.emergency.set_sensitive(connected);self.apply_button.set_sensitive(connected and not self.curve_error.get_text())
        self.show_media.set_sensitive(connected and bool(item.get('lcd')) and self.selected_media is not None and not self.media_busy)
        for key,widget in self.metrics.items():
            value=(item or {}).get('status',{}).get(key)
            if key in ('CPU','GPU'):
                host_value=self.snapshot.get('host',{}).get(key)
                value={'value':host_value,'unit':'°C'} if host_value is not None else None
            widget.set_text(f"{value['value']} {value['unit']}" if value else '—')
        if not item:
            self.device_note.set_text(_('Kraken nicht gefunden. USB-Verbindung und Gerätezugriffsrechte prüfen.'));return
        age=item.get('age'); stale=item.get('stale',False)
        self.title.set_subtitle(item['name']+(_(' · Demo') if self.demo else ''))
        state=_('Messwerte veraltet') if stale else _('Live')
        self.device_note.set_text(_('Firmware {firmware} · {state} · Vor {age} Sekunden gemessen').format(firmware=item['firmware'],state=state,age=age if age is not None else '—')+('\n'+_(item['error']) if item['error'] else ''))
        self.active_label.set_text(_('Aktiv: {profile}').format(profile=profile_label(item['active'])))
        if item['error'] and item['error']!=self.last_fault:
            self.last_fault=item['error'];self.banner.set_title(item['error'][:400]);self.banner.set_revealed(True)
            note=Gio.Notification.new(_('Boreal benötigt Aufmerksamkeit'));note.set_body(_(item['error'])[:180]);self.send_notification('hardware',note)
        self.history.values=item.get('history',[]);self.history.queue_draw()
        water=item.get('status',{}).get('Liquid temperature',{}).get('value')
        for editor in self.editors.values():editor.temperature=water;editor.chart.queue_draw()
        host=self.snapshot.get('host',{});self.sensor_note.set_text(' · '.join(_('{sensor} (Maximum): {value} °C').format(sensor=k,value=host.get(k,'—')) for k in ('CPU','GPU')))
        records=host.get('_sensors',[]);keys=['liquid','CPU','GPU']+[r['id'] for r in records]
        if keys!=self.sensor_ids:
            names=[_('Wasser'),_('CPU (Maximum)'),_('GPU (Maximum)')]+[r['label'] for r in records]
            for widget in self.sensor_widgets:
                old=widget.get_selected();key=self.sensor_ids[old] if old<len(self.sensor_ids) else 'liquid'
                widget.set_model(Gtk.StringList.new(names));widget.set_selected(keys.index(key) if key in keys else 0)
            self.sensor_ids=keys
        display=item.get('display',{});observed=display.get('observed',{})
        token=item['id']
        if self.preview_key!=token:
            self.preview_key=token
            self.rotation.set_selected(int(observed.get('orientation') or 0)//90)
            self.brightness.set_value(observed.get('brightness') if observed.get('brightness') is not None else 70)
        orientation=observed.get('orientation')
        display_mode={'stats':_('Live-Temperaturübersicht'),'static':_('Bild'),'gif':'GIF','liquid':_('Wassertemperatur')}.get(display.get('mode'),display.get('mode') or '—')
        self.lcd_state.set_text(_('Aktiv: {mode} · Ausrichtung bestätigt: {orientation}°').format(mode=display_mode,orientation=orientation if orientation is not None else '—')+('\n'+_(display['error']) if display.get('error') else ''))
        preview=display.get('path') if display.get('mode')=='gif' else display.get('preview')
        if preview:
            try:
                revision=(preview,item.get('last_screen'))
                if display.get('mode')=='stats' and getattr(self,'stats_preview_revision',None)!=revision:
                    self.overview_preview.path=None
                    self.stats_preview_revision=revision
                self.overview_preview.load(preview);self.overview_preview.orientation=orientation or 0
            except Exception:LOG.warning('Aktive Vorschau nicht verfügbar',exc_info=True)
        self.loading=True;self.restore_switch.set_active(bool(item.get('restore_enabled')));self.loading=False
        self.restore_switch.set_sensitive(connected and item.get('identity')=='Seriennummer' and item.get('tested',False))
        colors=item.get('colors',[]);model=self.rgb_zone.get_model()
        names=[model.get_string(i) for i in range(model.get_n_items())]
        labels=[{'ring':_('Pumpenring'),'fans':_('Lüfterbeleuchtung'),'external':_('Lüfterbeleuchtung')}.get(c,c) for c in colors]
        if names!=(labels or [_('Keine Zone')]):self.rgb_zone.set_model(Gtk.StringList.new(labels or [_('Keine Zone')]));self.rgb_zone.set_selected(0)
        self.rgb_color.set_sensitive(connected and bool(colors))
        self.rgb_group.set_sensitive(connected and bool(colors));self.rgb_apply.set_sensitive(connected and bool(colors))
        reason=item.get('rgb_error') or item.get('rgb_reason')
        self.rgb_note.set_text(_(reason) if reason else (_('Erkannte Zonen: {zones}').format(zones=', '.join(labels)) if colors else _('Kein unterstütztes RGB-Zubehör erkannt')))
        self.refresh_tray()

    def curve_changed(self):
        if not hasattr(self,'curve_error'):return
        try:
            value=self.read_profile();self.curve_error.set_text('');self.dirty=value!=self.clean_profile
        except Exception as exc:self.curve_error.set_text(str(exc));self.dirty=True
        self.draft.set_text(_('Ungespeicherte Änderungen') if self.dirty else _('Profil unverändert'))
        self.apply_button.set_sensitive(bool(self.selected() and self.selected()['connected'] and not self.curve_error.get_text()))

    def read_profile(self):return profile({c:e.value() for c,e in self.editors.items()})

    def load_profile(self):
        names=list(self.profiles);index=self.profile_select.get_selected()
        if self.loading or index>=len(names) or not hasattr(self,'editors'):return
        self.clean_profile=copy.deepcopy(self.profiles[names[index]])
        for channel,editor in self.editors.items():editor.set_points(self.clean_profile[channel])
        self.profile_name.set_text(names[index] if names[index] not in PRESETS else '')
        self.curve_changed()

    def discard_profile(self):
        for channel,editor in self.editors.items():editor.set_points(self.clean_profile[channel])
        self.curve_changed()

    def apply_profile(self):
        try:
            self.action('apply',profile=self.read_profile(),name=self.profile_name.get_text() or list(self.profiles)[self.profile_select.get_selected()])
        except Exception as exc:self.failure(exc)

    def update_profiles(self,values):
        old=self.profile_select.get_selected();old_name=list(self.profiles)[old] if old<len(self.profiles) else 'Ausgewogen'
        self.loading=True
        self.profiles=values;self.profile_select.set_model(Gtk.StringList.new([profile_label(name) for name in values]))
        self.profile_select.set_selected(list(values).index(old_name) if old_name in values else 1)
        self.loading=False
        self.refresh_tray()

    def save_profile(self):
        try:self.call('save_profile',name=self.profile_name.get_text(),profile=self.read_profile(),done=self.update_profiles)
        except Exception as exc:self.failure(exc)

    def rename_profile(self):
        old=list(self.profiles)[self.profile_select.get_selected()]
        self.call('rename_profile',old=old,name=self.profile_name.get_text(),done=self.update_profiles)

    def delete_profile(self):self.call('delete_profile',name=list(self.profiles)[self.profile_select.get_selected()],done=self.update_profiles)

    def file_dialog(self,title,callback,save=False,patterns=None):
        dialog=Gtk.FileDialog(title=_(title));cancel=Gio.Cancellable();key=uuid.uuid4().hex
        if patterns:
            filters=Gio.ListStore.new(Gtk.FileFilter);flt=Gtk.FileFilter();flt.set_name(_(title))
            for pattern in patterns:flt.add_pattern(pattern)
            filters.append(flt);dialog.set_filters(filters)
        self.dialogs[key]=(dialog,cancel)
        def selected(dialog,result,*_args):
            try:
                file=dialog.save_finish(result) if save else dialog.open_finish(result)
                if not self.closed and not cancel.is_cancelled():
                    path=file.get_path()
                    if not path:raise ValueError(_('Bitte eine lokale Datei wählen'))
                    callback(path)
            except GLib.Error as exc:
                if not cancel.is_cancelled() and exc.code not in (Gtk.DialogError.DISMISSED,Gtk.DialogError.CANCELLED):self.failure(exc)
            except Exception as exc:self.failure(exc)
            finally:self.dialogs.pop(key,None)
        (dialog.save if save else dialog.open)(self.window,cancel,selected,None)

    def import_profile(self):
        def selected(path):
            def read():
                p=Path(path)
                if p.stat().st_size>65536:raise ValueError(_('Profildatei zu groß'))
                data=json.loads(p.read_text());return data.get('name',p.stem),profile(data.get('profile',data))
            self.background(read,lambda pair:self.call('save_profile',name=pair[0],profile=pair[1],done=self.update_profiles))
        self.file_dialog('Profil importieren',selected,patterns=['*.json'])

    def export_profile(self):
        try:value=self.read_profile()
        except Exception as exc:self.failure(exc);return
        name=self.profile_name.get_text() or 'Boreal-Profil'
        self.file_dialog('Profil exportieren',lambda path:self.background(lambda:atomic_json(Path(path),{'schema':2,'name':name,'profile':value})),save=True)

    def crop_options(self):
        return dict(fit=['contain','cover'][self.fit.get_selected()],zoom=self.zoom.get_value(),x=self.crop_x.get_value(),y=self.crop_y.get_value(),background=self.background_color.get_text())

    def choose_media(self,mode):
        def selected(path):
            self.media_source=(path,mode)
            self.reprocess()
        self.file_dialog('GIF hinzufügen' if mode=='gif' else 'Bild hinzufügen',selected,patterns=['*.gif'] if mode=='gif' else ['*.png','*.jpg','*.jpeg','*.webp','*.gif'])

    def reprocess(self):
        if not self.media_source:self.notify(_('Zuerst ein Bild oder GIF auswählen'));return
        path,mode=self.media_source;item=self.selected()
        self.call('import_media',path=path,mode=mode,size=(item or {}).get('lcd',640) or 640,options=self.crop_options(),done=self.media_imported)

    def media_imported(self,record):
        self.selected_media=record
        self.call('media',done=self.update_media)
        self.preview_media(record)

    def update_media(self,records):
        selected_id=(self.selected_media or {}).get('id')
        self.media=records;self.library_select.set_model(Gtk.StringList.new([r['name'] for r in records] or [_('Medienbibliothek leer')]))
        if selected_id:
            ids=[r['id'] for r in records]
            self.library_select.set_selected(ids.index(selected_id) if selected_id in ids else 0)

    def choose_library(self,*_args):
        i=self.library_select.get_selected()
        if i<len(self.media):
            self.selected_media=self.media[i]
            record=self.selected_media
            self.media_source=(record.get('source',record['path']), 'gif' if record['format']=='gif' else 'static')
            self.preview_media(record)

    def preview_media(self,record):
        try:
            kind='GIF' if record['format']=='gif' else _('Bild')
            self.show_media.set_label(_('{kind} auf Kraken anzeigen').format(kind=kind))
            self.media_help.set_text(_('Überträgt {medium} auf das Display deiner Wasserkühlung.').format(medium=_('die ausgewählte Animation') if kind=='GIF' else _('das ausgewählte Bild')))
            self.lcd_preview.load(record['path']);self.lcd_preview.orientation=self.rotation.get_selected()*90;self.lcd_preview.queue_draw()
            self.media_label.set_text(_('{width} × {height} · {frames} Bild(er) · {size} KiB').format(width=record['width'],height=record['height'],frames=record['frames'],size=record['bytes']//1024))
            self.render()
        except Exception as exc:self.failure(exc)

    def apply_media(self):
        if not self.selected_media or self.media_busy:return
        record=self.selected_media;item=self.selected()
        if not item:return
        kind='GIF' if record['format']=='gif' else _('Bild')
        self.media_busy=True;self.show_media.set_label(_('{kind} wird übertragen …').format(kind=kind));self.render()
        def transfer():
            try:return request(self.demo,'screen',device=item['id'],mode='gif' if kind=='GIF' else 'static',media_id=record['id'])
            finally:GLib.idle_add(reset)
        def reset():
            self.media_busy=False;self.show_media.set_label(_('{kind} auf Kraken anzeigen').format(kind=kind));self.render();return False
        def done(value):
            self.media_help.set_text(_('{kind} erfolgreich auf Kraken übertragen.').format(kind=kind));self.poll()
        self.background(transfer,done)

    def rotate(self):
        value=int(self.rotation.get_selected())*90
        self.lcd_preview.orientation=value;self.lcd_preview.queue_draw()
        self.action('screen',mode='orientation',value=value)

    def apply_template(self):
        options=dict(template=['single','dual','overview'][self.template.get_selected()],accent=self.accent.get_text(),background=self.background_color.get_text(),font_scale=self.font_scale.get_value(),unit=['C','F'][self.unit.get_selected()],sensors=[self.sensor_ids[w.get_selected()] for w in self.sensor_widgets])
        self.action('screen',mode='stats',options=options)

    def apply_rgb(self,mode):
        item=self.selected();i=self.rgb_zone.get_selected()
        try:self.rgb_color.get_text()
        except ValueError as exc:self.failure(exc);return
        if item and i<len(item['colors']):self.action('color',channel=item['colors'][i],mode=mode,hex=self.rgb_color.get_text(),brightness=self.rgb_brightness.get_value_as_int())

    def restore_changed(self,*_args):
        if not self.loading:self.action('enable_restore',enabled=self.restore_switch.get_active())

    def set_theme(self):
        Adw.StyleManager.get_default().set_color_scheme([Adw.ColorScheme.DEFAULT,Adw.ColorScheme.FORCE_LIGHT,Adw.ColorScheme.FORCE_DARK][self.theme.get_selected()])

    def theme_changed(self,*_args):
        self.set_theme()
        if not self.loading and self.theme_loaded:self.call('theme',value=['system','light','dark'][self.theme.get_selected()])

    def language_changed(self,*_args):
        if self.loading or not self.language_loaded:return
        value=['system','de','en'][self.language.get_selected()]
        self.call('language',value=value,done=lambda _:
                  self.notify(_('Sprache gespeichert. Boreal beim nächsten Öffnen neu starten.')))

    def system_service(self,enabled):
        def run():
            from .autostart import set_ui_autostart
            unit='boreal-demo.service' if self.demo else 'boreal.service'
            result=subprocess.run(['systemctl','--user','enable' if enabled else 'disable',unit],capture_output=True,text=True,timeout=5)
            if result.returncode:raise ValueError(_('Boreal zuerst installieren. ')+result.stderr[:250])
            try:
                set_ui_autostart(enabled)
            except Exception:
                if enabled:
                    subprocess.run(['systemctl','--user','disable',unit],capture_output=True,text=True,timeout=5)
                raise
            return (_('Boreal und Tray starten künftig bei der Anmeldung') if enabled
                    else _('Autostart von Boreal und Tray deaktiviert'))
        self.background(run,self.notify)

    def save_diagnostics(self,path):
        import shutil
        self.file_dialog('Diagnosebericht speichern',lambda target:self.background(lambda:shutil.copyfile(path,target)),save=True)


def run(demo=True,smoke=False):
    configure('ui-demo' if demo else 'ui')
    return App(demo,smoke).run([])
