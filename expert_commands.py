import FreeCADGui as Gui
class OpenExpert:
    def GetResources(self):
        return {'MenuText':'Open DDCS Expert', 'ToolTip':'Sketch/DXF turning inspection - no machine output'}
    def Activated(self):
        from expert_panel import ExpertPanel
        Gui.Control.showDialog(ExpertPanel())
    def IsActive(self): return True
Gui.addCommand('DDCSExpert_Open', OpenExpert())
