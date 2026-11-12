import math
"""2D inspection plot: lathe Z horizontally, tool radius vertically (FreeCAD Qt)."""
try:
    from PySide import QtGui as G, QtCore as C
    W=G
except ImportError:
    from PySide6 import QtGui as G, QtWidgets as W, QtCore as C


def show_plot(parent, report, stock_d, stock_length, stock_face, chuck_z, tailstock_tip_z):
    moves=report['moves']
    if not moves:raise ValueError('No moves to plot')
    dlg=W.QDialog(parent);dlg.setWindowTitle('DDCS Expert 1.6.26 - toolpath inspection (NOT CNC SAFE)');dlg.resize(1050,680)
    layout=W.QVBoxLayout(dlg)
    info=W.QLabel('BLUE: G1 | ORANGE: G0 | RED: original-stock G0 warning | GREEN: estimated remaining stock | DASHED GREEN: axial limit. PURPLE DASHED: unverified candidate exits | CYAN DASHED: G1 previews only where not suppressed. At confirmed continuing stock, same-line G1 is suppressed. MAGENTA DASHED: stop-short markers, not motions. CYAN DASHED: reverse G1 backtrack previews (unverified). NOT collision verification.')
    info.setWordWrap(True);layout.addWidget(info)
    scene=W.QGraphicsScene(dlg)
    class InspectionView(W.QGraphicsView):
        def __init__(self, graphics_scene):
            super().__init__(graphics_scene)
            self.auto_fit=True
        def resizeEvent(self, event):
            super().resizeEvent(event)
            if self.auto_fit and self.scene() is not None:
                self.fitInView(self.scene().sceneRect(),C.Qt.KeepAspectRatio)
    view=InspectionView(scene);layout.addWidget(view)
    view.setRenderHint(G.QPainter.Antialiasing)
    view.setHorizontalScrollBarPolicy(C.Qt.ScrollBarAsNeeded)
    view.setVerticalScrollBarPolicy(C.Qt.ScrollBarAsNeeded)
    zz=[m['lathe_z'] for m in moves]+[stock_face,stock_face-stock_length,chuck_z,tailstock_tip_z]
    rr=[m['machine_y'] for m in moves]+[0,stock_d/2]
    minz=min(zz)-5;maxz=max(zz)+5;minr=min(0,min(rr))-3;maxr=max(rr)+3
    # World x is lathe Z (increasing right); world y is radius (increasing up).
    scale=9.0
    def xy(z,r):return (z-minz)*scale,(maxr-r)*scale
    def line(z0,r0,z1,r1,color,width=1.4,dash=False):
        x0,y0=xy(z0,r0);x1,y1=xy(z1,r1)
        pen=G.QPen(G.QColor(color));pen.setWidthF(width)
        if dash:pen.setStyle(C.Qt.DashLine)
        scene.addLine(x0,y0,x1,y1,pen)
    left=stock_face-stock_length
    x0,y0=xy(left,stock_d/2);x1,y1=xy(stock_face,0)
    scene.addRect(x0,y0,x1-x0,y1-y0,G.QPen(G.QColor('#888888')),G.QBrush(G.QColor(224,224,224,120)))
    line(chuck_z,minr,chuck_z,maxr,'#7c3aed',2,True)
    if report.get('axial_limit_z') is not None:
        lim=report['axial_limit_z'];line(lim,minr,lim,maxr,'#14804a',2.2,True)
    if report.get('tailstock')=='on':
        line(tailstock_tip_z,minr,tailstock_tip_z,maxr,'#9b59b6',1.4,True)
        # Vis den aksiale forbudszone som en transparent baggrund.
        lim=report.get('axial_limit_z')
        if lim is not None:
            sx,sy=xy(lim,maxr); ex,ey=xy(stock_face,minr)
            scene.addRect(sx,sy,max(0,ex-sx),max(0,ey-sy),
                G.QPen(C.Qt.NoPen),G.QBrush(G.QColor(160,60,180,25)))
            line(lim,minr,lim,maxr,'#14804a',2.2,True)

    model=report.get('stock_2d',{})
    stations=model.get('stations_z',[]); radii=model.get('remaining_radius_mm',[])
    for z0,z1,r0,r1 in zip(stations,stations[1:],radii,radii[1:]):
        line(z0,r0,z1,r1,'#138a55',1.8)
    flagged={a['line'] for a in report['alerts'] if a['kind']=='RAPID_STOCK_ENVELOPE'}
    selected_items={}
    for prev,m in zip(moves,moves[1:]):
        color=('#d23c34' if m['line'] in flagged else '#ed8a17') if m['g']==0 else '#1767bf'
        line(prev['lathe_z'],prev['machine_y'],m['lathe_z'],m['machine_y'],color,2.2 if m['line'] in flagged else 1.5)
        selected_items[m['line']] = (prev,m)
    # Purple dashed candidate segments are independent overlays, never replacements.
    for proposal in report.get('candidate_shoulder_exits',[])+report.get('candidate_endface_exits',[]):
        for segment in proposal['candidate_segments']:
            (z0,r0),(z1,r1)=segment['start'],segment['end']
            line(z0,r0,z1,r1,'#8b35d5',2.3,True)
    # Cyan dashed: proposed G1 motion mode only, NOT a safe or executable route.
    for proposal in report.get('candidate_g1_retracts',[]):
        for segment in proposal['candidate_segments']:
            (z0,r0),(z1,r1)=segment['start'],segment['end']
            line(z0,r0,z1,r1,'#00b8c8',3.0,True)
    # v1.6.23: draw a short magenta axial marker at the proposed earlier stop.
    # No connecting line is drawn: this is NOT a new feed or retract path.
    stopshort=report.get('stopshort_review_1620',{})
    for marker in stopshort.get('candidates',[]):
        z=marker['review_stop_z'];r=marker['original_radius']
        line(z,r-0.22,z,r+0.22,'#cc248b',2.5,True)
    # v1.6.23: dashed cyan previews are reverse traversal of original G1.
    # They are NOT inserted into machine instructions or the stock model.
    for candidate in report.get('backtrack_review_1621',{}).get('candidates',[]):
        for segment in candidate['segments']:
            z0,r0=segment['start'];z1,r1=segment['end']
            line(z0,r0,z1,r1,'#009fb7',2,True)
    # v1.6.23 user-specified facing sequence: violet dash-dot concept, not G-code.
    for candidate in report.get('end_strategy_review_1623',{}).get('candidates',[]):
        for segment in candidate['segments']:
            z0,r0=segment['start'];z1,r1=segment['end']
            line(z0,r0,z1,r1,'#a050dd',1.7,True)
    # v1.6.25 exact user sequence is drawn ONLY for Ø12 finish endpoint.
    # This overlay is NOT an executable motion or approved G0 clearance.
    for candidate in report.get('diagonal_exit_review_1625',{}).get('entries',[]):
        for seg in candidate.get('segments',[]):
            z0,r0=seg['start'];z1,r1=seg['end']
            line(z0,r0,z1,r1,'#d12d8b' if seg['mode']=='G1_PREVIEW' else '#d94130',3,True)
    # Axes and scale ticks (lathe Z / radius), plus interactive zoom.
    for ztick in range(int(math.ceil(minz/10)*10),int(maxz)+1,10):
        x,y=xy(ztick,0)
        scene.addText(str(ztick)).setPos(x-12,(maxr-minr)*scale+2)
        line(ztick,minr,ztick,maxr,'#dddddd',0.5,True)
    for rtick in range(int(math.ceil(minr/5)*5),int(maxr)+1,5):
        x,y=xy(minz,rtick)
        scene.addText('R'+str(rtick)).setPos(-38,y-10)
    scene.setSceneRect(-45,-10,(maxz-minz)*scale+90,(maxr-minr)*scale+40)
    summary=W.QLabel('Moves: %d | Alerts: %d | Rapid stock-envelope intersections: %d | Machine output BLOCKED'%(len(moves),len(report['alerts']),report.get('rapid_stock_alerts',0)))
    layout.addWidget(summary)
    guard=report.get('continuation_guard_1619')
    if guard:
        layout.addWidget(W.QLabel('CONFIRMED Ø%.3f continuing stock toward chuck: %d endpoint G0 retracts BLOCKED/UNVERIFIED; same-line G1 previews suppressed. No automatic safe exit.'%(guard['continuing_stock_diameter_mm'],guard['blocked_retract_count'])))
    if report.get('stopshort_review_1620',{}).get('candidate_count'):
        ss=report['stopshort_review_1620']
        layout.addWidget(W.QLabel('v1.6.23: %d MAGENTA early-stop markers at Z%.4f (reserve %.3f mm); NOT toolpaths, leaves unmachined stock. Original 9 G0 unchanged.'%(ss['candidate_count'],ss['review_stop_z'],ss['review_reserve_mm'])))
    bt=report.get('backtrack_review_1621',{})
    if bt.get('candidate_count'):
        layout.addWidget(W.QLabel('v1.6.23: %d CYAN reverse-G1 preview paths. NOT collision-checked; no radial exit certified; original G0 remains BLOCKED.'%bt['candidate_count']))
    sweep22=report.get('sweep_review_1622',{})
    layout.addWidget(W.QLabel('v1.6.23: %d/%d blocked G0 reviewed with 2D reverse-path footprint sampling; NONE verified safe. Original G0 unchanged.'%(sweep22.get('candidate_count',0),sweep22.get('blocked_original_g0_count',0))))
    strat=report.get('end_strategy_review_1623',{})
    layout.addWidget(W.QLabel('v1.6.23: %d VIOLET user-proposed shoulder-face sequences (3 G1 segments each); 4mm radial plunge and diagonal exit UNVERIFIED. NOT machine code.'%strat.get('candidate_count',0)))
    e24=report.get('exit_feasibility_review_1624',{})
    layout.addWidget(W.QLabel('v1.6.24: %d continuing-stock endpoint exits assessed; %d VERIFIED. No exit path generated; G0 blocked. Requires verified relief geometry / per-pass stock model.'%(e24.get('reviewed_endpoint_count',0),e24.get('verified_exit_count',0))))
    d25=report.get('diagonal_exit_review_1625',{})
    layout.addWidget(W.QLabel('v1.6.25: %d exact Ø12 diagonal G1 + radial G0 previews, %d verified. Other rough-pass endpoints not substituted. G0 from Y8 to Y12 remains UNVERIFIED/BLOCKED.'%(d25.get('exact_finished_diameter_preview_count',0),d25.get('verified_exit_count',0))))
    diag=report.get('stock_2d',{}).get('rapid_diagnostics',[])
    possible=sum(d['classification']=='POSSIBLE_REMAINING_STOCK' for d in diag)
    boundary=sum(d['classification']=='BOUNDARY_UNVERIFIED' for d in diag)
    layout.addWidget(W.QLabel('2D estimate: %d possible-stock / %d boundary-unverified / %d original-envelope G0. Removed %d zero-length G1. NOT COLLISION SAFE.'%(possible,boundary,len(diag),len(report.get('removed_zero_length_g1_source_lines',[])))))
    # Select a motion and inspect its endpoints, type and associated warning.
    diagnostics={d['line']:d for d in diag}
    picker=W.QComboBox()
    picker_row=W.QHBoxLayout()
    picker_row.addWidget(picker,1)
    flagged_only=W.QCheckBox('Only flagged G0')
    picker_row.addWidget(flagged_only)
    layout.addLayout(picker_row)
    def repopulate_picker(only_flagged=False):
        picker.blockSignals(True)
        picker.clear()
        picker.addItem('Select movement for details',None)
        for prev,m in zip(moves,moves[1:]):
            if only_flagged and m['line'] not in flagged:continue
            direction=diagnostics.get(m['line'],{}).get('motion_type','')
            picker.addItem('Source %d: G%d %s'%(m['line'],m['g'],direction),m['line'])
        picker.blockSignals(False)
        on_select(0)
    flagged_only.toggled.connect(repopulate_picker)
    review_row=W.QHBoxLayout()
    prev_btn=W.QPushButton('Previous flagged G0')
    next_btn=W.QPushButton('Next flagged G0')
    review_row.addWidget(prev_btn);review_row.addWidget(next_btn)
    layout.addLayout(review_row)
    def cycle_flagged(delta):
        lines=sorted(k for k in diagnostics if k in selected_items)
        if not lines:return
        current=picker.currentData()
        if current not in lines:target=lines[0 if delta>0 else -1]
        else:target=lines[(lines.index(current)+delta)%len(lines)]
        if picker.findData(target)<0:flagged_only.setChecked(False)
        index=picker.findData(target)
        if index>=0:picker.setCurrentIndex(index)
    prev_btn.clicked.connect(lambda checked=False:cycle_flagged(-1))
    next_btn.clicked.connect(lambda checked=False:cycle_flagged(1))
    detail=W.QLabel('Select a movement above. All positions are tool-tip coordinates, not full cutter geometry.')
    detail.setWordWrap(True);layout.addWidget(detail)
    endpoint=W.QLabel('Endpoint stock estimate: select a flagged G0 to see neighboring 0.25 mm stock bins.')
    endpoint.setWordWrap(True);layout.addWidget(endpoint)

    highlight=[None]
    focus_items=[]
    marker_items=[]
    tool_overlay=[]
    def clear_focus():
        for item in focus_items+marker_items+tool_overlay:scene.removeItem(item)
        focus_items.clear();marker_items.clear();tool_overlay.clear()

    def on_select(index):
        clear_focus()
        if highlight[0] is not None:
            scene.removeItem(highlight[0]);highlight[0]=None
        line_number=picker.itemData(index)
        if line_number is None:
            focus_rect[0]=None
            endpoint.setText('Endpoint stock estimate: select a flagged G0 to see neighboring 0.25 mm stock bins.')
            detail.setText('Select a movement. No cutter or holder clearance is certified.')
            return
        a,b=selected_items[line_number]
        x0,y0=xy(a['lathe_z'],a['machine_y']);x1,y1=xy(b['lathe_z'],b['machine_y'])
        pen=G.QPen(G.QColor('#b000d0'));pen.setWidthF(4)
        highlight[0]=scene.addLine(x0,y0,x1,y1,pen)
        # Start/end markers and direction arrow, visible when inspecting a move.
        for x,y,color in ((x0,y0,'#0c8a45'),(x1,y1,'#b000d0')):
            marker_items.append(scene.addEllipse(x-4,y-4,8,8,G.QPen(G.QColor(color)),G.QBrush(G.QColor(color))))
        dx=x1-x0;dy=y1-y0;length=math.hypot(dx,dy)
        if length>1e-7:
            ux,uy=dx/length,dy/length
            mx,my=(x0+x1)/2,(y0+y1)/2
            arrow_pen=G.QPen(G.QColor('#b000d0'));arrow_pen.setWidthF(2.5)
            marker_items.append(scene.addLine(mx-ux*10-uy*5,my-uy*10+ux*5,mx,my,arrow_pen))
            marker_items.append(scene.addLine(mx-ux*10+uy*5,my-uy*10-ux*5,mx,my,arrow_pen))
        diag_item=diagnostics.get(line_number,{})
        status=diag_item.get('classification','NOT CLASSIFIED')
        direction=diag_item.get('motion_type','CUTTING OR OTHER')
        margin=diag_item.get('minimum_radial_margin_mm')
        margin_text=' | min 2D radial margin %.3f mm'%margin if margin is not None else ''
        reason=diag_item.get('reason','Movement requires visual review')
        if diag_item.get('endpoint_stock_unverified'):reason+='; endface/width NOT verified' if report.get('physical_end_confirmed') else '; endpoint shoulder/width NOT verified'
        neighbor=diag_item.get('endpoint_neighbor_bins',[])
        width=report.get('tool_axial_width_mm',0)
        footprint=diag_item.get('tool_footprint_review',{})
        if width>0 and diag_item:
            # Display an axial-width strip at the selected radial retract.
            # It is NOT a physical cutter shape or a swept-volume clearance.
            endpoint_z=a['lathe_z'] if direction=='RADIAL_RETRACT' else b['lathe_z']
            leftx,top_y=xy(footprint.get('axial_z_min',endpoint_z-width/2),max(a['machine_y'],b['machine_y'])+report.get('tool_nose_radius_mm',0))
            rightx,bottom_y=xy(footprint.get('axial_z_max',endpoint_z+width/2),min(a['machine_y'],b['machine_y'])-report.get('tool_nose_radius_mm',0))
            rect=scene.addRect(leftx,top_y,max(1,rightx-leftx),max(1,bottom_y-top_y),
                G.QPen(G.QColor('#8b5cf6')),G.QBrush(G.QColor(139,92,246,45)))
            tool_overlay.append(rect)
        if neighbor:
            endpoint.setText('ENDPOINT NEIGHBORS (estimated, not measured): '+
                ' | '.join('Z %.3f: R %.3f'%(v['z'],v['remaining_radius_mm']) for v in neighbor)+
                ' mm. Footprint model: width %.3f mm, nose %.3f mm, direction %s. Estimated footprint margin %s mm. NOT collision/clearance verified.'%(report.get('tool_axial_width_mm',0),report.get('tool_nose_radius_mm',0),report.get('tool_orientation','center'),str(round(footprint['minimum_estimated_footprint_margin_mm'],3)) if footprint.get('minimum_estimated_footprint_margin_mm') is not None else 'unknown'))
            for v in neighbor:
                px,py=xy(v['z'],v['remaining_radius_mm'])
                pen2=G.QPen(G.QColor('#a000bf'));pen2.setWidthF(1.5)
                focus_items.append(scene.addEllipse(px-3,py-3,6,6,pen2,G.QBrush(G.QColor('#f4a7ff'))))
        else:
            endpoint.setText('No endpoint stock samples for this movement; physical clearance remains unverified.')
        detail.setText('Source %d | G%d | %s | X %.4f -> %.4f mm | Y %.4f -> %.4f mm | %s%s | %s | NOT COLLISION VERIFIED'%(line_number,b['g'],direction,a['machine_x'],b['machine_x'],a['machine_y'],b['machine_y'],status,margin_text,reason))
        # Magnified local context: original stock boundary and estimated
        # remaining surface at the selected segment's axial station.
        model=report.get('stock_2d',{})
        zs=model.get('stations_z',[]);rs=model.get('remaining_radius_mm',[])
        zlo=min(a['lathe_z'],b['lathe_z'])-2
        zhi=max(a['lathe_z'],b['lathe_z'])+2
        for i in range(1,len(zs)):
            if zlo<=zs[i]<=zhi:
                x0,y0=xy(zs[i-1],rs[i-1]);x1,y1=xy(zs[i],rs[i])
                pen=G.QPen(G.QColor('#008c58'));pen.setWidthF(3)
                focus_items.append(scene.addLine(x0,y0,x1,y1,pen))
        # Zoom around the selected movement without losing fit-view option.
        lowr=min(a['machine_y'],b['machine_y'],stock_d/2)-2
        highr=max(a['machine_y'],b['machine_y'],stock_d/2)+2
        xx0,yy0=xy(zlo,highr);xx1,yy1=xy(zhi,lowr)
        focus_rect[0]=C.QRectF(xx0,yy0,max(50,xx1-xx0),max(50,yy1-yy0))
        # Selection highlights only; do not force zoom.
    focus_rect=[None]
    picker.currentIndexChanged.connect(on_select)
    repopulate_picker(False)
    controls=W.QHBoxLayout()
    def zoom_by(factor):
        view.auto_fit=False
        view.scale(factor,factor)
    for title,factor in [('Zoom +',1.25),('Zoom -',0.8)]:
        btn=W.QPushButton(title);btn.clicked.connect(lambda checked=False,f=factor:zoom_by(f));controls.addWidget(btn)
    focus=W.QPushButton('Zoom to selected')
    def zoom_selected():
        if focus_rect[0] is not None:
            view.auto_fit=False
            view.fitInView(focus_rect[0],C.Qt.KeepAspectRatio)
    focus.clicked.connect(lambda checked=False:zoom_selected())
    controls.addWidget(focus)
    def fit_all():
        view.auto_fit=True
        view.fitInView(scene.sceneRect(),C.Qt.KeepAspectRatio)
    fit=W.QPushButton('Fit view');fit.clicked.connect(lambda checked=False:fit_all());controls.addWidget(fit)
    # Read-only shoulder review. Never changes the generated inspection moves.
    shoulder_btn=W.QPushButton(('Endface review (%d G0 checks)' % report.get('endface_retract_count',0)) if report.get('physical_end_confirmed') else (('Continuing-stock review (%d G0)' % report.get('continuation_retract_count',0)) if report.get('stock_continues_zminus') else ('Shoulder review (%d G0 checks)' % report.get('insert_shoulder_rapid_count',0))))
    def show_shoulder_review():
        from expert_shoulder import review
        data=review(report)
        popup=W.QDialog(dlg)
        popup.setWindowTitle('DDCS Expert 1.6.26 - endpoint review (NOT CNC SAFE)')
        popup.resize(900,500)
        outer=W.QVBoxLayout(popup)
        outer.addWidget(W.QLabel('Conservative 2D estimates. Negative margin is NOT proof of collision. No proposed path is machine-approved.'))
        table=W.QTableWidget(len(data['shoulder_reviews']),6)
        table.setHorizontalHeaderLabels(['Source','Z (mm)','Start R','Neighbor max R','Margin (mm)','Classification'])
        for i,item in enumerate(data['shoulder_reviews']):
            values=[item['line'],item['z'],item['start_radius'],item['neighbor_max_radius'],item['estimated_margin_mm'],item['classification']]
            for j,val in enumerate(values):
                table.setItem(i,j,W.QTableWidgetItem('—' if val is None else ('%.3f'%val if isinstance(val,float) else str(val))))
        table.setSelectionBehavior(W.QAbstractItemView.SelectRows)
        table.setEditTriggers(W.QAbstractItemView.NoEditTriggers)
        table.resizeColumnsToContents()
        outer.addWidget(table)
        detail_box=W.QTextEdit();detail_box.setReadOnly(True)
        outer.addWidget(detail_box)
        def update_detail():
            i=table.currentRow()
            if i<0:return
            item=data['shoulder_reviews'][i]
            candidate=item.get('candidate')
            if candidate:
                segments='\n'.join('%s: Z%.4f R%.4f -> Z%.4f R%.4f (%s)' % (
                    seg['g'],seg['start'][0],seg['start'][1],seg['end'][0],seg['end'][1],seg['note'])
                    for seg in candidate['candidate_segments'])
                candidate_text=('PURPLE CANDIDATE PREVIEW (NOT EXECUTABLE):\n%s\nStatus: %s\nIssues: %s\n'
                    % (segments,candidate['status'],', '.join(candidate['candidate_issues']) or 'No simple geometry flags; still unverified'))
            else:
                candidate_text='NO GENERATED CANDIDATE FOR THIS SOURCE LINE.\n'
            ss=next((x for x in report.get('stopshort_review_1620',{}).get('candidates',[]) if x['source_line']==item['line']),None)
            if ss:
                candidate_text+='\nv1.6.23 STOP-SHORT MARKER (NOT A PATH): Z%.4f; leaves material; retract still blocked.\n'%ss['review_stop_z']
            bt=next((x for x in report.get('backtrack_review_1621',{}).get('candidates',[]) if x['source_line']==item['line']),None)
            if bt:
                candidate_text+='\nv1.6.23 REVERSE G1 PREVIEW (NOT EXECUTABLE): %d segments, return to Z%.4f R%.4f. No verified radial exit; G0 remains blocked.\n'%(bt['segment_count'],bt['return_z'],bt['return_radius'])
            sw=next((x for x in report.get('sweep_review_1622',{}).get('candidates',[]) if x['source_line']==item['line']),None)
            if sw:
                candidate_text+='\nv1.6.23 2D SWEEP (NOT EXECUTABLE): %d segments, %d samples; minimum estimated margin %s mm; %s. Issues: %s\n'%(sw['segment_count'],sw['sample_count'],sw['minimum_estimated_margin_mm'],sw['status'],', '.join(sw['issues']))
            st=next((x for x in report.get('end_strategy_review_1623',{}).get('candidates',[]) if x['source_line']==item['line']),None)
            if st:
                candidate_text+='\nv1.6.23 USER END STRATEGY (NOT EXECUTABLE):\n'
                for seg in st['segments']:
                    candidate_text+='  G1 X%.4f Y%.4f -> X%.4f Y%.4f\n'%(seg['start'][0],seg['start'][1],seg['end'][0],seg['end'][1])
                candidate_text+='Status: %s. Issues: %s\n'%(st['status'],', '.join(st['issues']))
            ex24=next((x for x in report.get('exit_feasibility_review_1624',{}).get('entries',[]) if x['source_line']==item['line']),None)
            if ex24:
                candidate_text+='\nv1.6.24 EXIT FEASIBILITY: %s; radial stock gap %.3f mm; no exit generated.\nIssues: %s\nNext: %s\n'%(ex24['classification'],ex24['radial_material_to_stock_surface_mm'],', '.join(ex24['issues']),ex24['suggested_next_design'])
            d25item=next((x for x in report.get('diagonal_exit_review_1625',{}).get('entries',[]) if x['source_line']==item['line']),None)
            if d25item:
                candidate_text+='\nv1.6.25 DIAGONAL EXIT: %s. Issues: %s\n'%(d25item['status'],', '.join(d25item['issues']))
                for seg in d25item['segments']:
                    candidate_text+='  %s X%.4f Y%.4f -> X%.4f Y%.4f (PREVIEW ONLY)\n'%(seg['mode'],seg['start'][0],seg['start'][1],seg['end'][0],seg['end'][1])
            detail_box.setPlainText('Source %s, Z %s mm\nAxial review window: %s\nEstimated margin: %s mm\n\n%s\nCONCEPTUAL ALTERNATIVES:\n- %s\n\n%s'%(
                item['line'],item['z'],item['tool_window_z'],item['estimated_margin_mm'],candidate_text,'\n- '.join(item['options']),item['warning']))
        table.itemSelectionChanged.connect(update_detail)
        if data['shoulder_reviews']:table.selectRow(0)
        btn=W.QPushButton('Close');btn.clicked.connect(popup.accept);outer.addWidget(btn)
        popup.exec_() if hasattr(popup,'exec_') else popup.exec()
    shoulder_btn.clicked.connect(lambda checked=False:show_shoulder_review())
    controls.addWidget(shoulder_btn)
    layout.addLayout(controls)
    close=W.QPushButton('Close');close.clicked.connect(dlg.accept);layout.addWidget(close)
    # Fit after the dialog is laid out so the first view shows the entire stock.
    # Schedule after Qt has allocated a real viewport, not before dialog layout.
    C.QTimer.singleShot(0,fit_all)
    dlg.exec_() if hasattr(dlg,'exec_') else dlg.exec()
