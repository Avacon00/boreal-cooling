from pathlib import Path
from boreal.ui import App
from gi.repository import GLib,Gtk
from PIL import Image
app=App(demo=True,window_size=(800,600));app.set_application_id('io.boreal.Cooling.MatrixQA')
errors=[]; steps=[]
path=Path('/tmp/boreal-qa-preview.gif').resolve()
a=Image.new('RGB',(160,160),'#6ce5c0');b=Image.new('RGB',(160,160),'#387aaa');a.save(path,save_all=True,append_images=[b],duration=800,loop=0)
def setup():
    app.window.set_default_size(800,600)
    app.split.set_show_sidebar(False)
    for page,_ in app.pages:
        for rotation in ([0,90,180,270] if page=='display' else [0]):
            steps.append((page,rotation))
    GLib.timeout_add(500,step);return False
def step():
    try:
        if not steps:
            app.file_dialog('Boreal QA – Abbruchtest',lambda _:errors.append('unexpected file callback'))
            GLib.timeout_add(300,cancel);return False
        page,rotation=steps.pop(0)
        app.stack.set_visible_child_name(page)
        app.lcd_preview.load(str(path));app.lcd_preview.orientation=rotation;app.lcd_preview.queue_draw()
        GLib.timeout_add(250,lambda:capture(page,rotation))
    except Exception as exc: errors.append(repr(exc));app.quit()
    return False
def capture(page,rotation):
    try:
        assert app.window.get_width()==800 and app.window.get_height()==600, (app.window.get_width(),app.window.get_height())
        paint=Gtk.WidgetPaintable.new(app.window);snap=Gtk.Snapshot()
        paint.snapshot(snap,app.window.get_width(),app.window.get_height())
        app.window.get_renderer().render_texture(snap.to_node(),None).save_to_png(str(Path(f'/tmp/boreal-qa-{page}-{rotation}-800.png').resolve()))
        GLib.timeout_add(200,step)
    except Exception as exc:errors.append(repr(exc));app.quit()
    return False
def cancel():
    for _,c in list(app.dialogs.values()):c.cancel()
    GLib.timeout_add(500,done);return False
def done():
    if app.dialogs:errors.append('dialog references not released')
    app.quit();return False
GLib.timeout_add_seconds(2,setup);app.run([])
if errors:raise RuntimeError(errors)
print('PASS: pages at 800x600, animated preview in four orientations, dialog cancellation')
