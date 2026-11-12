"""v1.6.20: conservative, NON-EXECUTABLE axial stop-short review.

No physical clearance is inferred from this offset. Tool holder mounting,
actual insert contact, shoulder transition and remaining stock are unverified.
"""
import math


def review(moves, shoulder_z, stock_d, finished_d, tool_width, nose_radius,
           extra_clearance, stock_continues=True):
    vals=(shoulder_z,stock_d,finished_d,tool_width,nose_radius,extra_clearance)
    if not all(math.isfinite(v) for v in vals):
        raise ValueError('Non-finite shoulder geometry')
    if not (0 < finished_d < stock_d):
        raise ValueError('Finished diameter must be positive and smaller than continuing stock')
    if tool_width <= 0 or nose_radius < 0 or extra_clearance <= 0:
        raise ValueError('Tool width, nose radius or shoulder clearance invalid')
    if not stock_continues:
        return {'status':'DISABLED_NO_CONFIRMED_CONTINUING_STOCK','candidates':[],
                'candidate_count':0,'machine_approved':False}
    # Review-only *upper-bound* axial keep-out estimate. The 12x12 shank and
    # insert mounting are not modeled; this is not a verified offset.
    reserve=tool_width/2.0+nose_radius+extra_clearance
    stop_z=shoulder_z+reserve  # Z+ means away from the chuck
    rows=[]
    for a,b in zip(moves,moves[1:]):
        if (a['g']==1 and b['g']==0 and
            abs(a['lathe_z']-shoulder_z)<0.02 and
            abs(b['lathe_z']-shoulder_z)<0.02 and
            b['machine_y']>a['machine_y']+1e-6):
            rows.append({'source_line':b['line'],'cut_source_line':a['line'],
                'original_end_z':a['lathe_z'],'original_radius':a['machine_y'],
                'review_stop_z':stop_z,'axial_reserve_mm':reserve,
                'original_retract_g':0,
                'candidate_segments':[{'g':'G1','start':[a['lathe_z'],a['machine_y']],
                    'end':[stop_z,a['machine_y']],
                    'note':'DIRECTIONAL ANNOTATION ONLY: segment drawn from old endpoint back to proposed earlier stop; NOT a tool motion'}],
                'status':'STOP_SHORT_PREVIEW_ONLY_NOT_A_PATH',
                'issues':['UNMACHINED_AXIAL_BAND', 'UNVERIFIED_NOSE_CONTACT',
                          'HOLDER_ENVELOPE_NOT_MODELED', 'NO_RETRACT_ROUTE_VERIFIED'],
                'machine_approved':False})
    return {'status':'REVIEW_ONLY','shoulder_z':shoulder_z,
            'finished_diameter_mm':finished_d,'continuing_stock_diameter_mm':stock_d,
            'radial_shoulder_height_mm':(stock_d-finished_d)/2.0,
            'review_reserve_mm':reserve,'review_stop_z':stop_z,
            'candidates':rows,'candidate_count':len(rows),
            'machine_approved':False,
            'warning':'Stop-short leaves an unmachined axial band and does not solve radial retraction; no tool/holder swept-volume verification.'}
