import os, json
import FreeCAD as App
import FreeCADGui as Gui
try:
    from PySide import QtGui as W
except ImportError:
    from PySide6 import QtWidgets as W
from expert_reader10 import sketch_paths, dxf_paths
from expert_profile15 import extract_outer
from expert_inspection import inspect
from expert_plot import show_plot
from expert_gcode26 import render_review_nc
from expert_full_review29 import render_full_review
from expert_machine_post30 import render_machine_nc
from expert_review27 import overview_text, diagnostics_csv, summarize
from expert_strategy28 import strategy_audit, audit_text

class ExpertPanel:
    def __init__(self):
        self.form=W.QWidget();self.form.setWindowTitle('TurnCAM DDCS Expert 1.6.35 (En) - DDCS POSTPROCESSOR')
        layout=W.QVBoxLayout(self.form)
        label=W.QLabel('DDCS Expert V1.1 | X=lathe Z; Y=lathe diameter/2 | Post output NOT collision verified')
        label.setWordWrap(True);layout.addWidget(label)
        self.sketches=W.QComboBox();layout.addWidget(self.sketches)
        b=W.QPushButton('Refresh Sketch list');b.clicked.connect(self.refresh);layout.addWidget(b)
        b=W.QPushButton('Load selected Sketch');b.clicked.connect(self.load_sketch);layout.addWidget(b)
        b=W.QPushButton('Load DXF');b.clicked.connect(self.load_dxf);layout.addWidget(b)
        form=W.QFormLayout();layout.addLayout(form);self.fields={}
        for key,label,default in [
            ('stock','Stock diameter (mm)','20'),('stock_length','Exposed stock length (mm)','150'),
            ('depth','Roughing radial depth (mm)','0.5'),('rpm','Reference RPM (not output)','1200'),
            ('feed','Rough feed G94 (mm/min)','180'),('finish_feed','Finish feed G94 (mm/min)','100'),
            ('allow','Finishing allowance radial (mm)','0.5'),('finish_depth','Finishing depth radial (mm)','0.25'),
            ('clear','Radial clearance (mm)','2'),('stock_face','Stock front face Z','0'),
            ('chuck_z','Chuck front Z','-160'),('chuck_gap','Chuck clearance Z (mm)','3'),
            ('tip_z','Tailstock tip Z (mm)','-4'),('tip_clearance','Axial tool-tip clearance (mm)','10'),
            ('tailstock_d','Tailstock exclusion diameter (mm)','30'),
            ('tool_width','Axial tool review width (mm; not holder envelope)','2.0'),
            ('shoulder_axial_margin','Additional axial review margin (mm)','0.6'),
            ('exit_shift','Proposed shoulder exit Z+ distance (mm; shoulders only)','1.5'),
            ('exit_margin','Proposed exit radial margin (mm)','0.5'),
            ('nose_radius','DCMT070204 nose radius (mm; fixed 0.4)','0.4')]:
            e=W.QLineEdit(default);self.fields[key]=e;form.addRow(label,e)
        self.orientation=W.QComboBox();self.orientation.addItems(['left','center','right'])
        form.addRow('Tool review width direction (not calibrated)',self.orientation)
        self.fields['nose_radius'].setReadOnly(True)
        layout.addWidget(W.QLabel('SDJCR 1212 (right-hand) + DCMT070204 (55 deg, R0.4); tip toward chuck Z-. Tool mounting NOT verified.'))
        self.tailstock=W.QCheckBox('Tailstock active');self.tailstock.setChecked(True);layout.addWidget(self.tailstock)
        self.continuation=W.QCheckBox('Raw stock CONTINUES at stock diameter toward chuck (Z-) beyond left profile endpoint');self.continuation.setChecked(True);layout.addWidget(self.continuation)
        self.physical_end=W.QCheckBox('Left profile endpoint is the PHYSICAL END of the workpiece (not a shoulder)');self.physical_end.setChecked(False);layout.addWidget(self.physical_end)
        self.continuation.toggled.connect(self.update_endpoint_controls)
        self.physical_end.toggled.connect(self.update_endpoint_controls)
        self.free_space=W.QCheckBox('I confirm measured FREE SPACE toward Z- beyond the physical left end (preview ONLY)');self.free_space.setChecked(False);layout.addWidget(self.free_space)
        self.update_endpoint_controls()
        layout.addWidget(W.QLabel('v1.6.35: G02/G03 arc fitting and 3-decimal DDCS export available. Collision validation is NOT performed by the postprocessor.'))
        self.entry=W.QCheckBox('I have inspected radial entry (does not approve machine output)');layout.addWidget(self.entry)
        self.facing=W.QCheckBox('Facing requested (tailstock ON: not generated in this release)');layout.addWidget(self.facing)
        self.rough=W.QCheckBox('External roughing');self.rough.setChecked(True);layout.addWidget(self.rough)
        self.finish=W.QCheckBox('External finishing');self.finish.setChecked(True);layout.addWidget(self.finish)
        self.status=W.QLabel('Load a Sketch or DXF to generate DDCS G-code.');self.status.setWordWrap(True);layout.addWidget(self.status)
        b=W.QPushButton('Plot toolpaths (2D inspection)');b.clicked.connect(self.plot);layout.addWidget(b)
        b=W.QPushButton('SAVE .nc FILE');b.clicked.connect(self.export_machine_nc);layout.addWidget(b)
        b=W.QPushButton('Close');b.clicked.connect(self.reject);layout.addWidget(b)
        self.points=None;self.refresh()
    def update_endpoint_controls(self,*args):
        continuing=self.continuation.isChecked()
        if continuing:
            self.physical_end.setChecked(False)
            self.free_space.setChecked(False) if hasattr(self,'free_space') else None
        self.physical_end.setEnabled(not continuing)
        if hasattr(self,'free_space'):
            if not self.physical_end.isChecked(): self.free_space.setChecked(False)
            self.free_space.setEnabled(not continuing and self.physical_end.isChecked())
    def getStandardButtons(self):return 0
    def reject(self):Gui.Control.closeDialog()
    def accept(self):self.reject()
    def refresh(self):
        self.sketches.clear();doc=App.ActiveDocument
        if doc:
            for obj in doc.Objects:
                if obj.isDerivedFrom('Sketcher::SketchObject'):self.sketches.addItem(obj.Label,obj.Name)
    def load_sketch(self):
        try:
            doc=App.ActiveDocument
            if doc is None:raise ValueError('Open a FreeCAD document first')
            obj=doc.getObject(self.sketches.currentData())
            self.points=extract_outer(sketch_paths(obj));self.status.setText('Sketch profile loaded')
        except Exception as exc:self.error(exc)
    def load_dxf(self):
        path=W.QFileDialog.getOpenFileName(self.form,'Load DXF','','DXF (*.dxf)')[0]
        if not path:return
        try:
            paths,warnings,kinds=dxf_paths(path)
            if warnings:raise ValueError('Ambiguous DXF entities: '+'; '.join(warnings))
            self.points=extract_outer(paths);self.status.setText('DXF profile loaded: '+str(kinds))
        except Exception as exc:self.error(exc)
    def error(self,exc):
        self.points=None;self.status.setText(str(exc));W.QMessageBox.warning(self.form,'DDCS Expert',str(exc))
    def run(self):
        if self.points is None:raise ValueError('Load and validate a profile first')
        def v(k):
            if k == 'shoulder_z': return min(z for z, radius in self.points)  # actual profile end, never previous part's hardcoded Z
            if k == 'finished_shoulder_d': return min(v('stock') - 0.001, max(0.001, 2.0 * self.points[0][1]))  # review-only geometry from loaded profile
            return float(self.fields[k].text().replace(',','.'))
        txt, report = inspect(self.points,stock_d=v('stock'),stock_length=v('stock_length'),depth=v('depth'),
            rpm=v('rpm'),feed=v('feed'),finish_feed=v('finish_feed'),allowance=v('allow'),
            finish_depth=v('finish_depth'),clearance=v('clear'),stock_face=v('stock_face'),
            chuck_z=v('chuck_z'),chuck_gap=v('chuck_gap'),tailstock=self.tailstock.isChecked(),
            tailstock_tip_z=v('tip_z'),tip_clearance=v('tip_clearance'),tailstock_d=v('tailstock_d'),
            facing=self.facing.isChecked(),roughing=self.rough.isChecked(),
            finishing=self.finish.isChecked(),entry_relief=self.entry.isChecked(),
            tool_width_mm=v('tool_width'),nose_radius_mm=v('nose_radius'),
            tool_orientation=self.orientation.currentText(),shoulder_z=v('shoulder_z'),
            exit_shift_mm=v('exit_shift'),exit_margin_mm=v('exit_margin'),
            physical_end_confirmed=self.physical_end.isChecked(),
            free_space_declared=self.free_space.isChecked(),
            stock_continues_zminus=self.continuation.isChecked(),
            finished_shoulder_d=v('finished_shoulder_d'),
            shoulder_axial_margin=v('shoulder_axial_margin'))
        report['strategy_safety_audit_1628'] = strategy_audit(report, v('feed'), v('finish_feed'))
        return txt, report
    def overview(self):
        try:
            txt,report=self.run()
            dlg=W.QDialog(self.form);dlg.setWindowTitle('DDCS Expert 1.6.28 - inspection overview')
            dlg.resize(720,420);lay=W.QVBoxLayout(dlg)
            view=W.QPlainTextEdit();view.setReadOnly(True);view.setPlainText(overview_text(report));lay.addWidget(view)
            b=W.QPushButton('Close');b.clicked.connect(dlg.accept);lay.addWidget(b)
            dlg.exec_() if hasattr(dlg,'exec_') else dlg.exec()
        except Exception as exc:W.QMessageBox.warning(self.form,'DDCS Expert',str(exc))
    def strategy_review(self):
        try:
            _, report = self.run()
            audit = report['strategy_safety_audit_1628']
            dlg = W.QDialog(self.form)
            dlg.setWindowTitle('DDCS Expert 1.6.28 - strategy / safety audit')
            dlg.resize(800, 500)
            lay = W.QVBoxLayout(dlg)
            view = W.QPlainTextEdit()
            view.setReadOnly(True)
            view.setPlainText(audit_text(audit))
            lay.addWidget(view)
            b = W.QPushButton('Close')
            b.clicked.connect(dlg.accept)
            lay.addWidget(b)
            dlg.exec_() if hasattr(dlg, 'exec_') else dlg.exec()
        except Exception as exc:
            W.QMessageBox.warning(self.form, 'DDCS Expert', str(exc))
    def preview(self):
        try:
            txt,report=self.run();dlg=W.QDialog(self.form);dlg.setWindowTitle('DDCS Expert inspection only');dlg.resize(800,600)
            lay=W.QVBoxLayout(dlg);info=W.QLabel('%d moves; %d alerts. Machine output BLOCKED.'%(len(report['moves']),len(report['alerts'])))
            lay.addWidget(info);view=W.QPlainTextEdit();view.setReadOnly(True);view.setPlainText(txt);lay.addWidget(view)
            b=W.QPushButton('Close');b.clicked.connect(dlg.accept);lay.addWidget(b)
            dlg.exec_() if hasattr(dlg,'exec_') else dlg.exec()
        except Exception as exc:W.QMessageBox.warning(self.form,'DDCS Expert',str(exc))
    def full_gcode_review(self):
        try:
            _, report = self.run()
            listing = render_full_review(report)
            dlg = W.QDialog(self.form)
            dlg.setWindowTitle('DDCS Expert 1.6.29 - FULL G-code / risk review')
            dlg.resize(1050, 680)
            lay = W.QVBoxLayout(dlg)
            warning = W.QLabel('FULL G-code visible. Flagged G00 exits are NOT verified; do NOT execute this listing.')
            warning.setWordWrap(True)
            lay.addWidget(warning)
            view = W.QPlainTextEdit()
            view.setReadOnly(True)
            view.setPlainText(listing)
            lay.addWidget(view)
            b = W.QPushButton('Close')
            b.clicked.connect(dlg.accept)
            lay.addWidget(b)
            dlg.exec_() if hasattr(dlg, 'exec_') else dlg.exec()
        except Exception as exc:
            W.QMessageBox.warning(self.form, 'DDCS Expert', str(exc))

    def export_full_review(self):
        try:
            _, report = self.run()
            listing = render_full_review(report)
            path = W.QFileDialog.getSaveFileName(self.form,
                'Save numbered G-code risk listing (NOT machine code)', '', 'Text (*.txt)')[0]
            if not path:
                return
            if not path.lower().endswith('.txt'):
                path += '.txt'
            with open(path, 'w', encoding='utf-8') as f:
                f.write(listing)
            self.status.setText('Saved complete numbered G-code risk review: ' + path)
        except Exception as exc:
            W.QMessageBox.warning(self.form, 'DDCS Expert', str(exc))

    def plot(self):
        try:
            txt,report=self.run()
            def v(k):return float(self.fields[k].text().replace(',','.'))
            show_plot(self.form,report,v('stock'),v('stock_length'),v('stock_face'),v('chuck_z'),v('tip_z'))
        except Exception as exc:W.QMessageBox.warning(self.form,'DDCS Expert',str(exc))
    def export(self):
        try:
            txt,report=self.run();path=W.QFileDialog.getSaveFileName(self.form,'Save inspection only','','Text (*.txt)')[0]
            if not path:return
            if not path.lower().endswith('.txt'):path+='.txt'
            with open(path,'w',encoding='utf-8') as f:f.write(txt)
            with open(os.path.splitext(path)[0]+'.json','w',encoding='utf-8') as f:json.dump(report,f,indent=2)
            with open(os.path.splitext(path)[0]+'.csv','w',encoding='utf-8',newline='') as f:f.write(diagnostics_csv(report))
            with open(os.path.splitext(path)[0]+'_strategy_safety.txt','w',encoding='utf-8') as f:f.write(audit_text(report['strategy_safety_audit_1628']))
            self.status.setText('Saved INSPECTION only: '+path+' (NOT machine code)')
        except Exception as exc:W.QMessageBox.warning(self.form,'DDCS Expert',str(exc))

    def export_nc(self):
        try:
            txt,report=self.run()
            nc=render_review_nc(report)
            path=W.QFileDialog.getSaveFileName(self.form,'Save DDCS G-code review (NOT executable)','','G-code review (*.nc)')[0]
            if not path:return
            if not path.lower().endswith('.nc'):path+='.nc'
            with open(path,'w',encoding='ascii') as f:f.write(nc)
            with open(os.path.splitext(path)[0]+'.json','w',encoding='utf-8') as f:json.dump(report,f,indent=2)
            self.status.setText('G-code REVIEW saved (NOT executable): '+path)
        except Exception as exc:W.QMessageBox.warning(self.form,'DDCS Expert',str(exc))

    def export_machine_nc(self):
        try:
            _, report = self.run()
            nc = render_machine_nc(report)
            path = W.QFileDialog.getSaveFileName(self.form, 'SAVE .nc FILE', '', 'G-code (*.nc)')[0]
            if not path:
                return
            if not path.lower().endswith('.nc'):
                path += '.nc'
            with open(path, 'w', encoding='ascii') as f:
                f.write(nc)
            self.status.setText('UNVERIFIED executable DDCS G-code exported: ' + path)
        except Exception as exc:
            W.QMessageBox.warning(self.form, 'DDCS Expert', str(exc))
