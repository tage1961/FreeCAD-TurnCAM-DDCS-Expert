"""v1.6.21: read-only G1 backtrack proposals along prior G1 cuts.

A reversed tool-center trajectory is NOT proof of clearance: chip loading,
insert orientation, remaining stock, holder and tailstock are not modeled.
No original G0 is replaced; machine output remains blocked.
"""
import math


def review(moves, blocked_lines, shoulder_z, stock_d, tol=0.02):
    if not all(math.isfinite(float(x)) for x in (shoulder_z,stock_d,tol)) or stock_d<=0 or tol<=0:
        raise ValueError('Invalid backtrack review geometry')
    candidates=[]
    by_line={m['line']:i for i,m in enumerate(moves)}
    for line in sorted(blocked_lines):
        idx=by_line.get(line)
        if idx is None or idx<2:continue
        rapid=moves[idx]; endpoint=moves[idx-1]
        if not (rapid['g']==0 and endpoint['g']==1 and
                abs(endpoint['lathe_z']-shoulder_z)<=tol and
                abs(rapid['lathe_z']-shoulder_z)<=tol and
                rapid['machine_y']>endpoint['machine_y']):continue
        # Collect the entire contiguous G1 chain that finishes at the blocked G0.
        first=idx-1
        while first>0 and moves[first-1]['g']==1:
            first-=1
        # The preceding G0 establishes the feed chain start point.
        chain=moves[first:idx]
        if len(chain)<3:continue
        # Require a cut from the right (Z+) to the left endpoint (Z-), without
        # an intervening axial reversal. Otherwise suppress the preview.
        if chain[0]['lathe_z']<=shoulder_z+tol:continue
        if any(chain[j+1]['lathe_z']>chain[j]['lathe_z']+1e-6 for j in range(len(chain)-1)):
            continue
        reverse=list(reversed(chain))
        segments=[]
        for a,b in zip(reverse,reverse[1:]):
            if abs(a['lathe_z']-b['lathe_z'])<1e-7 and abs(a['machine_y']-b['machine_y'])<1e-7:continue
            segments.append({'g':'G1_PREVIEW','start':[a['lathe_z'],a['machine_y']],
                'end':[b['lathe_z'],b['machine_y']],
                'feed_mm_min':endpoint.get('feed_mm_min'),
                'status':'REVERSE_CUT_UNVERIFIED'})
        if not segments:continue
        candidates.append({'source_line':line,'cut_source_line':endpoint['line'],
            'start_z':endpoint['lathe_z'],'start_radius':endpoint['machine_y'],
            'return_z':reverse[-1]['lathe_z'],'return_radius':reverse[-1]['machine_y'],
            'segments':segments,'segment_count':len(segments),
            'original_g0_unchanged':True,'radial_exit_verified':False,
            'machine_approved':False,'status':'G1_BACKTRACK_PREVIEW_ONLY',
            'issues':['REVERSE_CUTTING_NOT_VERIFIED','STOCK_SWEEP_NOT_VERIFIED',
                'TOOL_HOLDER_NOT_MODELED','TAILSTOCK_NOT_MODELED',
                'RADIAL_EXIT_AT_RETURN_POINT_NOT_VERIFIED']})
    return {'version':'1.6.21','strategy':'reverse prior G1 centerline only',
        'candidate_count':len(candidates),'candidates':candidates,
        'blocked_original_g0_count':len(blocked_lines),
        'original_g0_unchanged':True,'machine_approved':False,
        'warning':'G1 reverse path is only a geometric proposal. It does not prove clearance, and no radial G0 at the return point is authorized.'}
