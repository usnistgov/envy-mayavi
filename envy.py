import sys, os, collections, itertools, numbers, math
if hasattr(sys,'frozen'):
    sys.path.insert(0, os.path.join(os.path.dirname(sys.executable), 'site-packages'))

from mayavi.core.ui.api import SceneEditor, MlabSceneModel
from traits.api import HasTraits, Instance
from traitsui.api import View, Item
from mayavi import mlab
from tvtk.api import tvtk
import mayavi.sources.api

import CoolProp

# Pure python to remove dependency on numpy
def linspace(start, end, n):
    l = []
    step = (end-start)/(n-1)
    for i in range(n):
        l.append(start + i*step)
    return l
    
# Pure python to remove dependency on numpy    
def logspace(start, end, n):
    l = []
    step = (end-start)/(n-1)
    for i in range(n):
        l.append(10**(start + i*step))
    return l
    
def argmax(x):
    return max(enumerate(x), key=lambda x:x[1])[0]
    
def log10(x):
    try:
        return [math.log10(_) for _ in x]
    except BaseException as BE:
        return math.log10(x)
    
def log(x):
    try:
        return [math.log(_) for _ in x]
    except:
        return math.log(x)
        
# Based on http://stackoverflow.com/a/17115473/1360263
from bisect import bisect_right
class Interpolate(object):
    def __init__(self, x_list, y_list):
        if any([y - x <= 0 for x, y in zip(x_list, x_list[1:])]):
            # x_list must be in strictly ascending order - swap order if opposite
            x_list,y_list = zip(*sorted(zip(x_list,y_list)))
            
        x_list = self.x_list = map(float, x_list)
        y_list = self.y_list = map(float, y_list)
        self.slopes = [(y2 - y1)/(x2 - x1) for x1, x2, y1, y2 in zip(x_list, x_list[1:], y_list, y_list[1:])]
    def __call__(self, x):
        o = []
        for _ in x:
            i = min(len(self.x_list)-2, bisect_right(self.x_list, _)-1)
            o.append(self.y_list[i] + self.slopes[i] * (_ - self.x_list[i]))
        return o

class MayaviView(HasTraits):

    scene = Instance(MlabSceneModel, ())

    # The layout of the panel created by Traits
    view = View(Item('scene', editor=SceneEditor(), resizable=True,
                    show_label=False),
                    resizable=True)

    def __init__(self, input_data):
        HasTraits.__init__(self)
        # Create some data, and plot it using the embedded scene's engine
        
        if input_data['backend'] == 'CoolProp':
            input_data['backend'] = 'HEOS'
        HEOS = CoolProp.AbstractState(input_data['backend'],input_data['fluid1'] + '&' + input_data['fluid2'])
        n = 200
        data = []
        X0 = linspace(0.0001, 0.9999, input_data['N'])
        for x0 in X0:

            HEOS.set_mole_fractions([x0, 1 - x0])
            try:
                HEOS.build_phase_envelope("dummy")
            except ValueError as VE:
                print(VE)
            
            PE = HEOS.get_phase_envelope_data()
            # Find maximum pressure location
            ipmax = argmax(PE.p)
            # Interpolate to find densities corresponding to cutoff pressure (if possible)
            if min(PE.p[0:ipmax-1]) < input_data['p_cutoff'] < max(PE.p[0:ipmax-1]):
                rhoymin = Interpolate(PE.p[0:ipmax-1], PE.rhomolar_vap[0:ipmax-1])([input_data['p_cutoff']])[0]
            else:
                rhoymin = min(PE.rhomolar_vap)
            if min(PE.p[ipmax+1::]) < input_data['p_cutoff'] < max(PE.p[ipmax+1::]):
                rhoymax = Interpolate(PE.p[ipmax+1::], PE.rhomolar_vap[ipmax+1::])([input_data['p_cutoff']])[0]
            else:
                rhoymax = max(PE.rhomolar_vap)
            rhoy = logspace(math.log10(rhoymin), math.log10(rhoymax), n)
            T = Interpolate(PE.rhomolar_vap, PE.T)(rhoy)
            logp = Interpolate(PE.rhomolar_vap, log(PE.p))(rhoy)
            data.append((list(T), list(logp), rhoy))
        
        for j in range(len(data)-1):
            triangles = [(0+i, 1+i, 0+n+i) for i in range(0, n-1)] + [(0+n+i, 1+i, 1+n+i) for i in range(0, n-1)]
            x = data[j][0] + data[j+1][0]
            y = data[j][1] + data[j+1][1]
            z = [X0[j]]*len(data[j][0]) + [X0[j+1]]*len(data[j][0])
            t = data[j][2] + data[j+1][2]
            
            # Apply scale factors
            y = [_*50 for _ in y]
            z = [_*100 for _ in z]
            
            lens = (len(x), len(y), len(z), len(t))
            assert(len(set(lens)) == 1)
            
            self.plot = self.scene.mlab.points3d(x, y, z, scale_factor = 0.5, figure = self.scene.mayavi_scene)
            self.plot = self.scene.mlab.triangular_mesh(x, y, z, triangles, scalars = t, figure = self.scene.mayavi_scene)
        
#-----------------------------------------------------------------------------
# Wx Code
import wx

class InputsPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        RPnames = sorted([CoolProp.CoolProp.get_fluid_param_string(fluid, 'REFPROPname') for fluid in CoolProp.__fluids__])
            
        sizer = wx.FlexGridSizer(cols = 2)
        
        self.backend_label = wx.StaticText(self, label = 'Backend:')
        self.fluid1_label = wx.StaticText(self, label = 'Fluid1:')
        self.fluid2_label = wx.StaticText(self, label = 'Fluid2:')
        self.N_label = wx.StaticText(self, label = 'N fractions:')
        self.N = wx.TextCtrl(self, value = '10')
        self.backend = wx.ComboBox(self)
        self.backend.AppendItems(['REFPROP','HEOS'])
        self.backend.SetSelection(0)
        self.fluid1 = wx.ComboBox(self)
        self.fluid1.AppendItems(RPnames)
        self.fluid1.SetValue('METHANE')
        self.fluid2 = wx.ComboBox(self)
        self.fluid2.AppendItems(RPnames)
        self.fluid2.SetValue('ETHANE')
        self.p_cutoff_label = wx.StaticText(self, label = 'Cutoff pressure [Pa]:')
        self.p_cutoff = wx.TextCtrl(self, value = '1e6')
        self.btn = wx.Button(self, label = 'Go!')
        sizer.AddMany([(self.backend_label,0), (self.backend,1),
                      (self.fluid1_label,0), (self.fluid1,1),
                      (self.fluid2_label,0), (self.fluid2,1),
                      (self.N_label,0), (self.N,1),
                      (self.p_cutoff_label,0), (self.p_cutoff,1),
                      (self.btn)])
        self.SetSizer(sizer)
        sizer.Layout()
        self.Fit()
        
        #Bind a key-press event to all objects to get Enter key press
        children = self.GetChildren()
        for child in children:
            child.Bind(wx.EVT_KEY_UP,  self.OnKeyPress)
        
    def OnKeyPress(self,event=None):
        """ Accept if Return key is pressed """
        event.Skip()
        if event.GetKeyCode() == wx.WXK_RETURN:
            self.EndModal(wx.ID_OK)
        
class MainWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, wx.ID_ANY, 'Fluid selection')
        
        self.notebook = wx.aui.AuiNotebook(self, style=wx.aui.AUI_NB_TAB_SPLIT | wx.aui.AUI_NB_CLOSE_ON_ALL_TABS | wx.aui.AUI_NB_LEFT)
        
        self.inputs = InputsPanel(self)
        self.notebook.AddPage(page=self.inputs, caption='Inputs')
        
        self.inputs.btn.Bind(wx.EVT_BUTTON, self.OnGo)
        self.mayavi_views = []
        self.mayavi_controls = []
        
    def OnGo(self, event):
        data = dict(backend = self.inputs.backend.GetValue(),
                    fluid1 = self.inputs.fluid1.GetValue(),
                    fluid2 = self.inputs.fluid2.GetValue(),
                    N = int(self.inputs.N.GetValue()),
                    p_cutoff = float(self.inputs.p_cutoff.GetValue())
                    )
        HEOS = CoolProp.AbstractState(data['backend'],data['fluid1'] + '&' + data['fluid2'])
        
        v = MayaviView(data)
        self.mayavi_views.append(v)
        # Use traits to create a panel, and use it as the content of this
        # wx frame.
        c = v.edit_traits(parent=self, kind='subpanel').control
        self.mayavi_controls.append(c)
        
        self.notebook.AddPage(page=c, caption=data['fluid1']+'-'+data['fluid2'])

if __name__=='__main__':
    app = wx.App(0)
    
    frame = MainWindow(None)
    frame.Show()
    
    app.MainLoop()