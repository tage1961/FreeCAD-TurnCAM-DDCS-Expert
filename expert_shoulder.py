"""Read-only shoulder review for DDCS Expert 1.6.21.

This is NOT a swept-volume, collision or clearance solver. Suggested routes
are conceptual inspection alternatives, never machine instructions.
"""
import math


def review(report):
    if not report.get('inspection_only') or report.get('machine_code_allowed') is not False:
        raise ValueError('Shoulder review requires blocked inspection-only report')
    rows=[]
    candidates={c['source_line']:c for c in report.get('candidate_shoulder_exits',[])+report.get('candidate_endface_exits',[])+report.get('candidate_g1_retracts',[])}
    for d in report.get('stock_2d',{}).get('rapid_diagnostics',[]):
        if d.get('motion_type') != 'RADIAL_RETRACT':
            continue
        if report.get('physical_end_confirmed') and abs(d.get('start',{}).get('z',float('inf'))-report['shoulder_z'])>0.02:
            continue
        fp=d.get('tool_footprint_review') or {}
        start=d.get('start') or {}
        end=d.get('end') or {}
        neighbors=d.get('endpoint_neighbor_bins') or []
        margin=fp.get('minimum_estimated_footprint_margin_mm')
        if margin is not None and not math.isfinite(float(margin)):
            raise ValueError('Non-finite margin')
        z=start.get('z')
        r=start.get('radius')
        max_neighbor=max((v['remaining_radius_mm'] for v in neighbors),default=None)
        candidate=candidates.get(d['line'])
        rows.append({
            'line':d['line'], 'z':z, 'start_radius':r,
            'end_radius':end.get('radius'),
            'neighbor_max_radius':max_neighbor,
            'estimated_margin_mm':margin,
            'classification':('END_FACE_UNVERIFIED' if report.get('physical_end_confirmed') else ('CONTINUING_STOCK_UNVERIFIED' if report.get('stock_continues_zminus') and abs(z-report['shoulder_z'])<0.02 else d.get('classification','UNKNOWN'))),
            'tool_window_z':d.get('axial_width_window_z'),
            'review_required':True,
            'candidate':candidate,
            'candidate_status':candidate['status'] if candidate else 'NO_CANDIDATE',
            'candidate_issues':candidate.get('candidate_issues',[]) if candidate else ['NO_CANDIDATE'],
            'options':(['Verify physical stock rear, chuck/fixture and available clearance; original G0 is not approved',
                        'Physical-end Z- preview requires stock rear to equal physical end and explicit free-space declaration; it remains unverified'] if report.get('physical_end_confirmed') else [
                'Review an earlier axial stopping point, subject to the actual part contour and remaining stock',
                'Review a cutting-feed exit strategy instead of rapid radial retract, subject to tool geometry',
                'Review a different pass order or a shoulder relief operation in CAM before retract'
            ]),
            'warning':'Physical end declared, but toolpath is NOT cleared or approved. No 3D collision, holder, tailstock or machine verification.' if report.get('physical_end_confirmed') else 'Hypotheses only. No 3D collision, tool holder, tailstock or machine verification.'
        })
    return {'version':'1.6.21','inspection_only':True,
            'machine_code_allowed':False,'physical_collision_verification':False,
            'shoulder_review_count':len(rows),'shoulder_reviews':rows,
            'route_generation':False, 'candidate_preview_linked':True}
