"""Native GTK components, no USB operations and no unvalidated source images."""
import copy
import math
import gi
gi.require_version('Gtk','4.0'); gi.require_version('GdkPixbuf','2.0'); gi.require_version('Graphene','1.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Graphene, Gsk
from .core import curve, interpolate
from .i18n import _


def text(value, css=None):
    w=Gtk.Label(label=_(value),xalign=0,wrap=True)
    if css: w.add_css_class(css)
    return w


def box(vertical=True,spacing=12):
    return Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL,spacing=spacing)


def button(label,callback,css=None):
    w=Gtk.Button(label=_(label))
    if css: w.add_css_class(css)
    w.connect('clicked',lambda _:callback())
    return w


def card(title=None,subtitle=None):
    w=box(); w.add_css_class('card')
    for side in ('top','bottom','start','end'): getattr(w,'set_margin_'+side)(4)
    inner=box()
    for side in ('top','bottom','start','end'): getattr(inner,'set_margin_'+side)(16)
    if title: inner.append(text(title,'title-3'))
    if subtitle: inner.append(text(subtitle,'dim-label'))
    w.append(inner)
    return w,inner


class RoundPreview(Gtk.Widget):
    def __init__(self,size=240):
        super().__init__()
        self.set_size_request(size,size); self.set_hexpand(False); self.set_halign(Gtk.Align.CENTER)
        self.set_tooltip_text(_('Runde LCD-Vorschau')); self.paintable=None; self.animation=None
        self.iterator=None; self.source=0; self.orientation=0; self.path=None
        self.connect('unrealize',lambda *_:self.stop())

    def stop(self):
        if self.source: GLib.source_remove(self.source); self.source=0

    def load(self,path,animate=True):
        if path==self.path: return
        self.stop(); self.path=path
        if not path:
            self.paintable=None; self.queue_draw(); return
        self.animation=GdkPixbuf.PixbufAnimation.new_from_file(path)
        self.iterator=self.animation.get_iter(None)
        self.paintable=Gdk.Texture.new_for_pixbuf(self.iterator.get_pixbuf())
        if animate and not self.animation.is_static_image(): self.source=GLib.timeout_add(80,self.frame)
        self.queue_draw()

    def frame(self):
        if not self.iterator: return False
        if self.iterator.advance(None):
            self.paintable=Gdk.Texture.new_for_pixbuf(self.iterator.get_pixbuf()); self.queue_draw()
        return True

    def do_snapshot(self,snapshot):
        size=min(self.get_width(),self.get_height())
        rect=Graphene.Rect().init((self.get_width()-size)/2,0,size,size)
        rounded=Gsk.RoundedRect(); rounded.init_from_rect(rect,size/2)
        snapshot.push_rounded_clip(rounded)
        color=Gdk.RGBA(); color.parse('#14242b'); snapshot.append_color(color,rect)
        if self.paintable:
            snapshot.save()
            snapshot.translate(Graphene.Point().init(self.get_width()/2,size/2))
            snapshot.rotate(self.orientation)
            snapshot.translate(Graphene.Point().init(-size/2,-size/2))
            self.paintable.snapshot(snapshot,size,size)
            snapshot.restore()
        snapshot.pop()


class CurveEditor(Gtk.Box):
    def __init__(self,channel,points,on_change):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=10)
        self.channel=channel; self.points=copy.deepcopy(points); self.on_change=on_change
        self.temperature=None; self.drag_index=None; self.origin=None
        self.append(text('Pumpe' if channel=='pump' else 'Lüfter','title-3'))
        self.chart=Gtk.DrawingArea(content_height=160,hexpand=True)
        self.chart.set_draw_func(self.draw)
        self.chart.set_tooltip_text(_('Punkte ziehen; dieselben Werte können in der Tabelle bearbeitet werden'))
        drag=Gtk.GestureDrag.new(); drag.connect('drag-begin',self.begin); drag.connect('drag-update',self.drag)
        drag.connect('drag-end',lambda *_:self.rebuild())
        self.chart.add_controller(drag); self.append(self.chart)
        self.table=Gtk.Grid(column_spacing=8,row_spacing=6); self.append(self.table)
        self.append(button('Punkt hinzufügen',self.add))
        self.rebuild()

    def set_points(self,points):
        self.points=copy.deepcopy(points); self.rebuild(); self.chart.queue_draw()

    def value(self): return curve(self.points,self.channel)

    def rebuild(self):
        child=self.table.get_first_child()
        while child:
            next_child=child.get_next_sibling(); self.table.remove(child); child=next_child
        self.table.attach(text('Wasser °C'),0,0,1,1); self.table.attach(text('Leistung %'),1,0,1,1)
        for i,(t,d) in enumerate(self.points):
            ts=Gtk.SpinButton.new_with_range(20,50,1); ts.set_value(t)
            ds=Gtk.SpinButton.new_with_range(60 if self.channel=='pump' else 30,100,1); ds.set_value(d)
            ts.set_tooltip_text(_('Punkt {number}: Wassertemperatur').format(number=i+1)); ds.set_tooltip_text(_('Punkt {number}: Leistung').format(number=i+1))
            ts.set_sensitive(i not in (0,len(self.points)-1)); ds.set_sensitive(i!=len(self.points)-1)
            ts.connect('value-changed',self.edit,i,0); ds.connect('value-changed',self.edit,i,1)
            self.table.attach(ts,0,i+1,1,1); self.table.attach(ds,1,i+1,1,1)
            if i not in (0,len(self.points)-1): self.table.attach(button('Entfernen',lambda j=i:self.remove(j)),2,i+1,1,1)

    def edit(self,widget,index,column):
        self.points[index][column]=widget.get_value_as_int(); self.changed()

    def changed(self):
        self.chart.queue_draw(); self.on_change()

    def add(self):
        if len(self.points)>=12: return
        for i,(a,b) in enumerate(zip(self.points,self.points[1:])):
            if b[0]-a[0]>=2:
                t=(a[0]+b[0])//2; self.points.insert(i+1,[t,round((a[1]+b[1])/2)])
                self.rebuild(); self.changed(); return

    def remove(self,index):
        self.points.pop(index); self.rebuild(); self.changed()

    def coords(self,t,d):
        return (42+(t-20)/30*(self.chart.get_width()-60), 12+(100-d)/100*(self.chart.get_height()-38))

    def begin(self,gesture,x,y):
        candidates=[(math.dist((x,y),self.coords(*p)),i) for i,p in enumerate(self.points)]
        distance,index=min(candidates)
        self.drag_index=index if distance<24 else None; self.origin=(x,y)

    def drag(self,gesture,dx,dy):
        i=self.drag_index
        if i is None: return
        x,y=self.origin[0]+dx,self.origin[1]+dy
        t=round(20+(x-42)/max(1,self.chart.get_width()-60)*30)
        d=round(100-(y-12)/max(1,self.chart.get_height()-38)*100)
        if i in (0,len(self.points)-1): t=self.points[i][0]
        else: t=max(self.points[i-1][0]+1,min(self.points[i+1][0]-1,t))
        low=self.points[i-1][1] if i else (60 if self.channel=='pump' else 30)
        high=self.points[i+1][1] if i<len(self.points)-1 else 100
        d=100 if i==len(self.points)-1 else max(low,min(high,d))
        self.points[i]=[t,d]; self.changed()

    def draw(self,area,cr,width,height):
        rgba=self.get_style_context().get_color()
        cr.set_source_rgba(rgba.red,rgba.green,rgba.blue,.45); cr.set_line_width(1)
        for t in (20,30,40,50):
            x,_=self.coords(t,0); cr.move_to(x,12); cr.line_to(x,height-26); cr.stroke()
            cr.move_to(x-8,height-5); cr.show_text(str(t)+'°')
        for d in (30,60,100):
            _,y=self.coords(20,d); cr.move_to(2,y+3); cr.show_text(str(d)+'%')
        if self.temperature is not None:
            x,_=self.coords(max(20,min(50,self.temperature)),0)
            cr.set_source_rgba(.9,.65,.25,.7); cr.move_to(x,12); cr.line_to(x,height-26); cr.stroke()
        cr.set_source_rgb(*((.15,.65,.47) if self.channel=='pump' else (.3,.55,.9))); cr.set_line_width(3)
        for i,p in enumerate(self.points): (cr.move_to if i==0 else cr.line_to)(*self.coords(*p))
        cr.stroke()
        for p in self.points:
            cr.arc(*self.coords(*p),5,0,math.tau); cr.fill()


class HistoryChart(Gtk.DrawingArea):
    def __init__(self):
        super().__init__(content_height=110,hexpand=True)
        self.values=[]; self.set_draw_func(self.draw)
        self.set_tooltip_text(_('Wassertemperatur der letzten zwölf Minuten'))

    def draw(self,area,cr,w,h):
        if len(self.values)<2: return
        vals=[x[1] for x in self.values]; low=min(vals)-1; high=max(vals)+1
        cr.set_source_rgb(.2,.7,.5); cr.set_line_width(2)
        for i,v in enumerate(vals):
            x=10+(self.values[i][0]-self.values[0][0])/max(.001,self.values[-1][0]-self.values[0][0])*(w-20); y=10+(high-v)/(high-low)*(h-30)
            (cr.move_to if i==0 else cr.line_to)(x,y)
        cr.stroke(); cr.move_to(10,h-4); cr.show_text(_('{value:.1f} °C · Wasserverlauf').format(value=vals[-1]))


class ColorPicker(Gtk.Box):
    """Local HSV draft; selecting colors never sends hardware commands."""
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        import colorsys
        from .colors import parse_hex
        self.h,self.s,self.v=colorsys.rgb_to_hsv(*parse_hex('6CE5C0')); self.syncing=False
        self.wheel=Gtk.DrawingArea(content_width=200,content_height=200,halign=Gtk.Align.CENTER)
        self.wheel.set_draw_func(self.draw);self.append(self.wheel)
        click=Gtk.GestureClick();click.connect('pressed',lambda g,n,x,y:self.pick(x,y));self.wheel.add_controller(click)
        drag=Gtk.GestureDrag();drag.connect('drag-begin',self.begin);drag.connect('drag-update',lambda g,x,y:self.pick(self.origin[0]+x,self.origin[1]+y));self.wheel.add_controller(drag)
        self.hue=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,360,1)
        self.saturation=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,100,1)
        for label,widget in [('Farbton (Grad)',self.hue),('Sättigung (%)',self.saturation)]:
            self.append(text(label));self.append(widget);widget.update_property([Gtk.AccessibleProperty.LABEL],[_(label)]);widget.connect('value-changed',self.sliders)
        self.append(text('Farbcode (HEX)'));self.entry=Gtk.Entry();self.entry.update_property([Gtk.AccessibleProperty.LABEL],[_('Farbcode HEX')]);self.append(self.entry)
        self.entry.connect('changed',self.entered);self.error=text('','error-text');self.append(self.error)
        swatches=Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,max_children_per_line=4)
        for name,value in [('Weiß','FFFFFF'),('Rot','FF0000'),('Orange','FF8000'),('Gelb','FFFF00'),('Grün','00FF00'),('Cyan','00FFFF'),('Blau','0000FF'),('Violett','8000FF')]:
            swatch=button(name,lambda v=value:self.entry.set_text(v))
            row=box(False,8);chip=Gtk.DrawingArea(content_width=16,content_height=16)
            rgb=parse_hex(value)
            def draw_chip(area,cr,w,h,rgb=rgb):
                cr.set_source_rgb(*rgb);cr.arc(w/2,h/2,7,0,math.tau);cr.fill()
            chip.set_draw_func(draw_chip);row.append(chip);row.append(text(name));swatch.set_child(row)
            swatches.insert(swatch,-1)
        self.append(swatches);self.sync()

    def begin(self,g,x,y):self.origin=(x,y);self.pick(x,y)

    def pick(self,x,y):
        radius=min(self.wheel.get_width(),self.wheel.get_height())/2-8
        dx=x-self.wheel.get_width()/2;dy=y-self.wheel.get_height()/2
        self.h=(math.atan2(dy,dx)/math.tau)%1;self.s=min(1,math.hypot(dx,dy)/radius);self.v=1;self.sync()

    def sliders(self,*_):
        if self.syncing:return
        self.h=self.hue.get_value()/360;self.s=self.saturation.get_value()/100;self.v=1;self.sync()

    def entered(self,*_):
        if self.syncing:return
        import colorsys
        from .colors import parse_hex
        try:self.h,self.s,self.v=colorsys.rgb_to_hsv(*parse_hex(self.entry.get_text()))
        except ValueError as exc:self.error.set_text(str(exc));return
        self.sync()

    def sync(self):
        from .colors import hsv_hex
        self.syncing=True;self.entry.set_text(hsv_hex(self.h,self.s,self.v))
        self.hue.set_value(self.h*360);self.saturation.set_value(self.s*100)
        self.syncing=False;self.error.set_text('');self.wheel.queue_draw()

    def get_text(self):
        from .colors import parse_hex
        parse_hex(self.entry.get_text());return self.entry.get_text().removeprefix('#')

    def draw(self,area,cr,w,h):
        import colorsys
        r=min(w,h)/2-8;cx=w/2;cy=h/2
        for ring in range(20,0,-1):
            for angle in range(120):
                a=angle*math.tau/120;b=(angle+1)*math.tau/120
                cr.set_source_rgb(*colorsys.hsv_to_rgb(angle/120,ring/20,1))
                cr.move_to(cx,cy);cr.arc(cx,cy,r*ring/20,a,b);cr.close_path();cr.fill()
        x=cx+math.cos(self.h*math.tau)*self.s*r;y=cy+math.sin(self.h*math.tau)*self.s*r
        cr.set_source_rgb(*colorsys.hsv_to_rgb(self.h,self.s,self.v));cr.arc(x,y,7,0,math.tau);cr.fill_preserve()
        cr.set_source_rgb(0,0,0);cr.set_line_width(3);cr.stroke_preserve()
        cr.set_source_rgb(1,1,1);cr.set_line_width(1);cr.stroke()
