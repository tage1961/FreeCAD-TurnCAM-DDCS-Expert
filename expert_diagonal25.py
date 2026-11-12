"""v1.6.25 read-only exact user-proposed diagonal exit inspection.

Never emits CNC G-code or modifies existing moves. Machine X = lathe Z;
machine Y = radius, not diameter. Conservative envelope checks only.
"""
import math


def review(moves, blocked_lines, boundary_z, stock_diameter, finished_diameter,
           axial_plus=2.0, radial_plus=2.0, clearance_radius=12.0,
           nose_radius=0.4, tool_width=2.0, stock_continues_zminus=True):
    values = (boundary_z, stock_diameter, finished_diameter, axial_plus,
              radial_plus, clearance_radius, nose_radius, tool_width)
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError('Nonfinite diagonal exit parameter')
    if not (stock_continues_zminus and stock_diameter > finished_diameter > 0
            and axial_plus > 0 and radial_plus > 0 and tool_width > 0
            and nose_radius >= 0 and clearance_radius > stock_diameter/2):
        raise ValueError('Invalid diagonal exit inspection geometry')
    r_final = finished_diameter/2.0
    r_stock = stock_diameter/2.0
    indexed = {m['line']:i for i,m in enumerate(moves)}
    entries=[]
    for source in sorted(set(blocked_lines)):
        idx=indexed.get(source)
        if idx is None or idx < 1: continue
        rapid, cut = moves[idx], moves[idx-1]
        if rapid['g'] != 0 or cut['g'] != 1 or abs(cut['lathe_z']-boundary_z)>0.03:
            continue
        r_start=float(cut['machine_y'])
        # User's exact request applies to Ø12 finish endpoint only. Never
        # silently substitute Ø12 for intermediate rough-pass radii.
        matches_final=abs(r_start-r_final)<0.015
        segments=[]
        if matches_final:
            p0=[float(boundary_z),r_final]
            p1=[float(boundary_z+axial_plus),r_final+radial_plus]
            p2=[float(boundary_z+axial_plus),clearance_radius]
            segments=[{'mode':'G1_PREVIEW','start':p0,'end':p1},
                      {'mode':'G0_PREVIEW_BLOCKED','start':p1,'end':p2}]
        issues=['CONTINUING_STOCK_AT_Z_MINUS',
                'DIAGONAL_MAY_CROSS_UNCUT_STOCK_OR_FINISHED_CONTOUR',
                'G0_STARTS_INSIDE_ORIGINAL_STOCK_RADIUS' if r_final+radial_plus<r_stock else 'G0_CLEARANCE_NOT_VERIFIED',
                'CHRONOLOGICAL_REMAINING_STOCK_NOT_MODELED',
                'DCMT_NOSE_AND_SDJCR_HOLDER_SWEEP_NOT_VERIFIED',
                'CHUCK_TAILSTOCK_AND_TOOL_HEIGHT_NOT_VERIFIED']
        if not matches_final:
            issues.insert(0,'INTERMEDIATE_PASS_NOT_AT_FINISHED_DIAMETER')
        entries.append({'source_line':source,'start_radius_mm':r_start,
            'matches_finished_diameter':matches_final,
            'segments':segments,'issues':issues,
            'status':'UNVERIFIED_BLOCKED' if matches_final else 'NOT_APPLICABLE_TO_INTERMEDIATE_PASS',
            'original_g0_unchanged':True,'machine_approved':False})
    return {'version':'1.6.25','entries':entries,
        'reviewed_endpoint_count':len(entries),
        'exact_finished_diameter_preview_count':sum(bool(e['segments']) for e in entries),
        'verified_exit_count':0,'machine_approved':False,'original_g0_unchanged':True,
        'coordinates':'machine X = lathe Z, machine Y = diameter / 2',
        'requested_sequence_machine_coordinates':[
            ['G1',round(boundary_z,4),round(r_final,4)],
            ['G1',round(boundary_z+axial_plus,4),round(r_final+radial_plus,4)],
            ['G0',None,round(clearance_radius,4)]],
        'warning':'G0 from Y8 to Y12 crosses the Ø20 original stock envelope; diagonal G1 and tool/holder clearance not verified. Not CNC code.'}
