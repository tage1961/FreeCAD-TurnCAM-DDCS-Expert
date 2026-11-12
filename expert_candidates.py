"""Inspection-only shoulder-exit proposals. NEVER machine commands."""
import math

def _radius_at(points,z):
    matches=[]
    for (z0,r0),(z1,r1) in zip(points,points[1:]):
        lo,hi=sorted((z0,z1))
        if lo-1e-8<=z<=hi+1e-8:
            if abs(z1-z0)<1e-9: matches.extend([r0,r1])
            else: matches.append(r0+(r1-r0)*(z-z0)/(z1-z0))
    return max(matches) if matches else None

def propose_exits(moves,points,shoulder_z,stock_radius,nose_radius,axial_limit,axial_shift=1.5,radial_margin=0.5):
    """Build review-only G1-feed exit + G0 radial alternatives at shoulder.

    Reference-point path only. Sampling and nominal nose clearance are NOT
    insert/holder swept-volume verification, nor a safe cut guarantee.
    """
    if axial_shift<=nose_radius or radial_margin<=0: raise ValueError('Invalid proposal clearance')
    out=[]
    for prev,m in zip(moves,moves[1:]):
        if m['g']!=0 or abs(prev['lathe_z']-shoulder_z)>1e-3 or abs(m['lathe_z']-shoulder_z)>1e-3 or m['machine_y']<=prev['machine_y']:
            continue
        start_z=prev['lathe_z']; start_r=prev['machine_y']
        end_z=start_z+axial_shift
        reasons=[]
        if axial_limit is not None and end_z>axial_limit+1e-7: reasons.append('AXIAL_LIMIT_EXCEEDED')
        sampled=[_radius_at(points,start_z+(end_z-start_z)*i/40) for i in range(41)]
        if any(v is None for v in sampled): reasons.append('CONTOUR_OUTSIDE_DOMAIN')
        # Proposal stays outside the estimated part contour at its endpoint;
        # intervening motion can still be cutting and is not collision checked.
        end_r=max([start_r]+[v for v in sampled if v is not None])+nose_radius+radial_margin
        if end_r>=m['machine_y']: reasons.append('INSUFFICIENT_RADIAL_G0_CLEARANCE')
        out.append({'source_line':m['line'],'status':'REVIEW_ONLY_NOT_VALIDATED',
                    'original_rapid':[[start_z,start_r],[m['lathe_z'],m['machine_y']]],
                    'candidate_segments':[
                        {'g':'G1','start':[start_z,start_r],'end':[end_z,end_r], 'note':'proposed feed exit, stock cutting and nose contact NOT verified'},
                        {'g':'G0','start':[end_z,end_r],'end':[end_z,m['machine_y']], 'note':'proposed radial rapid, full tool envelope NOT verified'}],
                    'candidate_issues':reasons,
                    'nose_radius_mm':nose_radius,'nominal_stock_radius_mm':stock_radius,
                    'axial_shift_mm':axial_shift,'radial_margin_mm':radial_margin,
                    'holder_sweep_verified':False,'stock_sweep_verified':False,'machine_approved':False})
    return out
