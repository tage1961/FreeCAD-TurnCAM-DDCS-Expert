import FreeCADGui as Gui
class DDCSExpertWorkbench(Gui.Workbench):
    MenuText = 'TurnCAM DDCS Expert'
    ToolTip = 'DDCS Expert V1.1 turning postprocessor (unverified machine G-code)'
    def Initialize(self):
        import expert_commands
        self.appendToolbar('DDCS Expert', ['DDCSExpert_Open'])
        self.appendMenu('DDCS Expert', ['DDCSExpert_Open'])
    def GetClassName(self):
        return 'Gui::PythonWorkbench'
Gui.addWorkbench(DDCSExpertWorkbench())
