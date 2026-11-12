"""v1.6.22 conservative, non-authorizing 2D reverse-path inspection.

The final remaining-stock envelope is optimistic for earlier passes. The model
cannot verify tool flank/holder, actual cutting engagement, or machine safety.
"""
import math


def review(moves, blocked_lines, stock_model, tool_width_mm, nose_radius_mm,
           axial_limit_z, stock_diameter_mm, sample_step_mm=0.25):
    if not all(math.isfinite(float(x)) for x in
               (tool_width_mm,nose_radius_mm,stock_diameter_mm,sample_step_mm)) or (
               axial_limit_z is not None and not math.isfinite(float(axial_limit_z))):
        raise ValueError('Non-finite sweep parameter')
    if tool_width_mm<=0 or nose_radius_mm<0 or stock_diameter_mm<=0 or sample_step_mm<=0:
        raise ValueError('Invalid sweep parameter')
    stations=stock_model['stations_z']; radii=stock_model['remaining_radius_mm']
    if len(stations)!=len(radii) or not stations:
        raise ValueError('Invalid stock model')
    by_line={m['line']:i for i,m in enumerate(moves)}
    candidates=[]
    for line in sorted(blocked_lines):
        idx=by_line.get(line)
        if idx is None or idx<1:continue
        rapid=moves[idx]; cut=moves[idx-1]
        if rapid['g']!=0 or cut['g']!=1:continue
        # Reverse the contiguous G1 chain, including a short chain of one or two.
        first=idx-1
        while first>0 and moves[first-1]['g']==1:first-=1
        chain=moves[first:idx]
        start= moves[first-1] if first>0 and moves[first-1]['g']==0 else None
        points=[(m['lathe_z'],m['machine_y']) for m in reversed(chain)]
        if start is not None:points.append((start['lathe_z'],start['machine_y']))
        # Remove duplicates and reject paths that move farther into the chuck.
        dedup=[]
        for p in points:
            if not dedup or math.dist(p,dedup[-1])>1e-7:dedup.append(p)
        issues=['FINAL_STOCK_ENVELOPE_NOT_CHRONOLOGICAL',
                'REVERSE_CUTTING_NOT_VERIFIED','TOOL_HOLDER_NOT_MODELED',
                'TAILSTOCK_AND_FIXTURES_NOT_MODELED','RADIAL_EXIT_NOT_VERIFIED']
        if len(dedup)<2:issues.append('NO_RETURN_PATH')
        if any(b[0]<a[0]-1e-6 for a,b in zip(dedup,dedup[1:])):
            issues.append('RETURN_MOVES_TOWARD_CHUCK')
        if axial_limit_z is not None and any(z>axial_limit_z+1e-6 for z,r in dedup):
            issues.append('AXIAL_TAILSTOCK_LIMIT')
        # Approximate rectangular axial width and radial nose extension.
        # Any point below the stock envelope is interference/engagement, NOT a safe exit.
        min_margin=float('inf'); min_where=None; unknown=0; sample_count=0
        segments=[]
        for (z0,r0),(z1,r1) in zip(dedup,dedup[1:]):
            segments.append({'start':[z0,r0],'end':[z1,r1],'mode':'G1_PREVIEW_ONLY'})
            steps=max(1,int(math.ceil(math.hypot(z1-z0,r1-r0)/sample_step_mm)))
            for i in range(steps+1):
                t=i/steps;z=z0+(z1-z0)*t;r=r0+(r1-r0)*t
                # Sampling stock stations in a tool axial footprint; include
                # nose radius conservatively on both axial and radial sides.
                half=tool_width_mm/2+nose_radius_mm
                nearby=[rv for zs,rv in zip(stations,radii) if abs(zs-z)<=half+sample_step_mm/2]
                sample_count+=1
                if not nearby:unknown+=1;continue
                margin=(r-nose_radius_mm)-max(nearby)
                if margin<min_margin:min_margin=margin;min_where=[z,r]
        if min_margin==float('inf'):issues.append('NO_STOCK_COVERAGE')
        elif min_margin<=0:issues.append('STOCK_ENVELOPE_CONTACT_OR_INTERFERENCE')
        if unknown:issues.append('STOCK_MODEL_OUTSIDE_COVERAGE')
        candidates.append({'source_line':line,'start':[cut['lathe_z'],cut['machine_y']],
            'return_end':list(dedup[-1]),'segments':segments,
            'segment_count':len(segments),'sample_count':sample_count,
            'minimum_estimated_margin_mm':None if min_margin==float('inf') else round(min_margin,4),
            'minimum_margin_at':min_where,'unknown_samples':unknown,
            'stock_model':'final 2D estimated remaining stock; not pass-by-pass',
            'tool_width_mm':tool_width_mm,'nose_radius_mm':nose_radius_mm,
            'status':'BLOCKED_2D_CONTACT' if min_margin<=0 else 'UNVERIFIED_2D_ONLY',
            'issues':issues,'original_g0_unchanged':True,'machine_approved':False})
    return {'version':'1.6.22','candidate_count':len(candidates),
        'blocked_original_g0_count':len(blocked_lines),'candidates':candidates,
        'original_g0_unchanged':True,'machine_approved':False,
        'warning':'Final-stock 2D sampling is not chronological and cannot certify reverse-cut or radial exit. Machine output blocked.'}
