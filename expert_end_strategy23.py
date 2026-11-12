"""v1.6.23: user-specified shoulder-facing concept, inspection only.

Coordinates: lathe Z -> machine X; lathe diameter -> machine Y radius.
No cutting paths or CNC instructions are authorized by this module.
"""
import math


def review(moves, blocked_lines, boundary_z, stock_diameter, finished_diameter,
           approach_z=-74.8, exit_z=-74.0, nose_radius=0.4, tool_width=2.0):
    vals=(boundary_z,stock_diameter,finished_diameter,approach_z,exit_z,nose_radius,tool_width)
    if not all(math.isfinite(float(v)) for v in vals):
        raise ValueError('Non-finite end-strategy parameter')
    if not (0 < finished_diameter < stock_diameter and nose_radius >= 0 and tool_width > 0):
        raise ValueError('Invalid end-strategy diameter/tool geometry')
    if not (boundary_z < approach_z and boundary_z < exit_z):
        raise ValueError('Approach and exit must be on Z+ side of boundary')
    by_line={m['line']:i for i,m in enumerate(moves)}
    candidates=[]
    for source_line in sorted(blocked_lines):
        idx=by_line.get(source_line)
        if idx is None or idx<1 or moves[idx]['g']!=0:
            continue
        cut=moves[idx-1]
        if cut['g']!=1 or abs(cut['lathe_z']-boundary_z)>0.03:
            continue
        # The requested Ø20 -> Ø12 radial cut is 4 mm deep; the preview
        # deliberately does not pretend this can be cut in one pass.
        r_stock=stock_diameter/2.0
        r_finished=finished_diameter/2.0
        waypoints=[(approach_z,r_stock),(boundary_z,r_stock),
                   (boundary_z,r_finished),(exit_z,r_stock)]
        segments=[]
        for (z0,r0),(z1,r1) in zip(waypoints,waypoints[1:]):
            segments.append({'mode':'G1_CONCEPT_ONLY','start':[z0,r0],
                             'end':[z1,r1], 'start_diameter':2*r0,
                             'end_diameter':2*r1})
        issues=['APPROACH_AT_STOCK_SURFACE_NOT_CLEARANCE',
                'RADIAL_PLUNGE_4MM_REQUIRES_PASS_PLANNING',
                'DCMT_INSERT_CUTTING_DIRECTION_NOT_VERIFIED',
                'DIAGONAL_EXIT_MAY_CROSS_STOCK',
                'TOOL_HOLDER_ENVELOPE_NOT_MODELED',
                'PASS_BY_PASS_STOCK_NOT_MODELED',
                'NO_COLLISION_CLEARANCE_VERIFICATION']
        candidates.append({'source_line':source_line,
            'reference_cut_radius':cut['machine_y'],
            'waypoints_z_radius':[list(p) for p in waypoints],
            'segments':segments,'radial_depth_mm':r_stock-r_finished,
            'tool_nose_radius_mm':nose_radius,'tool_width_mm':tool_width,
            'status':'CONCEPT_ONLY_BLOCKED','issues':issues,
            'original_g0_unchanged':True,'machine_approved':False})
    return {'version':'1.6.23','candidate_count':len(candidates),
            'blocked_original_g0_count':len(blocked_lines),
            'coordinate_mapping':'lathe Z -> mill X, diameter / 2 -> mill Y',
            'concept_parameters':{'approach_z':approach_z,'boundary_z':boundary_z,
                'exit_z':exit_z,'stock_diameter':stock_diameter,
                'finished_diameter':finished_diameter},
            'candidates':candidates,'original_g0_unchanged':True,
            'machine_approved':False,
            'warning':'Conceptual G1 path only; Ø20->Ø12 is 4 mm radial engagement; no pass-by-pass tool or collision validation.'}
