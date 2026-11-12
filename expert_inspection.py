"""DDCS Expert V1.1: intentionally non-executable inspection translator."""
import re, json, math
from expert_post import generate
from expert_insert import TOOL, inspect_profile_nose, shoulder_rapid_review
from expert_stopshort20 import review as stopshort_review
from expert_backtrack21 import review as backtrack_review
from expert_sweep22 import review as sweep22_review
from expert_end_strategy23 import review as strategy23_review
from expert_exit_plan24 import review as exit24_review
from expert_diagonal25 import review as diagonal25_review
from expert_candidates import propose_exits
from expert_endface import propose_endface_exits
from expert_feed_retract import propose_feed_retracts
from expert_continuation19 import review_continuation

class InspectionError(ValueError): pass

def clip_outer_profile(points, limit, tol=1e-7):
    """Clip ordered (Z,radius) line segments at Z<=limit, without translation.

    No arcs are accepted here; caller must reject arc metadata when clipping.
    """
    if len(points) < 2:
        raise InspectionError('Profile needs at least two points')
    if any(not math.isfinite(z) or not math.isfinite(r) for z,r in points):
        raise InspectionError('Non-finite profile coordinate')
    if any(points[i+1][0] < points[i][0]-tol for i in range(len(points)-1)):
        raise InspectionError('Profile Z must increase from chuck toward right end')
    if points[0][0] >= limit-tol:
        raise InspectionError('No usable profile to left of tailstock axial limit')
    clipped=[]
    for i, (z,r) in enumerate(points):
        if z <= limit+tol:
            if z > limit: z=limit
            clipped.append((z,r))
            continue
        za,ra=points[i-1]
        if za < limit-tol:
            t=(limit-za)/(z-za)
            clipped.append((limit,ra+t*(r-ra)))
        break
    if len(clipped)<2 or clipped[-1][0] < clipped[0][0]+tol:
        raise InspectionError('No valid axial span after clipping')
    return clipped


def rapid_stock_intersection(z0, d0, z1, d1, stock_d, stock_left, stock_right, tol=1e-7):
    """Segment intersects the original cylindrical stock envelope in Z/diameter space.

    This deliberately ignores material already removed and tool/holder size.
    Diameter must be nonnegative (outer-turning representation).
    """
    if any(not math.isfinite(v) for v in (z0,d0,z1,d1,stock_d,stock_left,stock_right)):
        raise InspectionError('Non-finite rapid segment')
    if min(d0,d1)<-tol: raise InspectionError('Negative diameter in rapid move')
    if stock_d<=0 or stock_left>=stock_right: raise InspectionError('Invalid stock envelope')
    dz=z1-z0
    if abs(dz)<=tol:
        if not stock_left-tol<=z0<=stock_right+tol:return False
        return min(d0,d1)<stock_d-tol
    t0=max(0.0,min((stock_left-z0)/dz,(stock_right-z0)/dz))
    t1=min(1.0,max((stock_left-z0)/dz,(stock_right-z0)/dz))
    if t1<t0-tol:return False
    return min(d0+(d1-d0)*t0,d0+(d1-d0)*t1)<stock_d-tol




def _rapid_type(z0, r0, z1, r1, tol=1e-7):
    if abs(z1-z0)<=tol:
        return ('RADIAL_RETRACT' if r1>r0+tol else
                'RADIAL_APPROACH' if r1<r0-tol else 'ZERO_LENGTH')
    if abs(r1-r0)<=tol:
        return 'AXIAL_RAPID'
    return 'DIAGONAL_RAPID'


def remaining_stock_2d(moves, stock_d, stock_left, stock_right, cell_mm=0.25, tool_width_mm=2.0, nose_radius_mm=0.4, tool_orientation="center"):
    """Conservative sequential point-tool model, for inspection only.

    Interior G1 axial cuts update axial bins. At a cut endpoint the
    material state is unknown because tool width, stock shoulders and
    tool nose radius are not modeled. This routine never certifies a rapid.
    """
    if stock_right<=stock_left or stock_d<=0 or cell_mm<=0:
        raise InspectionError('Invalid stock model')
    n=int(math.ceil((stock_right-stock_left)/cell_mm))
    if n>100000:raise InspectionError('Stock model exceeds 100000 cells')
    step=(stock_right-stock_left)/n
    stations=[stock_left+(i+0.5)*step for i in range(n)]
    remaining=[stock_d/2.0]*n
    diagnostics=[]
    for a,b in zip(moves,moves[1:]):
        z0,z1=a['lathe_z'],b['lathe_z']
        r0,r1=a['machine_y'],b['machine_y']
        lo,hi=min(z0,z1),max(z0,z1)
        if b['g']==1:
            if hi-lo>1e-9:
                start=max(0,int(math.floor((lo-stock_left)/step)))
                stop=min(n,int(math.ceil((hi-stock_left)/step)))
                for i in range(start,stop):
                    z=stations[i]
                    if lo<=z<=hi:
                        t=(z-z0)/(z1-z0)
                        r=r0+(r1-r0)*t
                        if r>=0:remaining[i]=min(remaining[i],r)
        elif b['g']==0:
            direction=_rapid_type(z0,r0,z1,r1)
            if direction=='ZERO_LENGTH':continue
            if not rapid_stock_intersection(z0,2*r0,z1,2*r1,stock_d,stock_left,stock_right):
                continue
            # Material state must be captured BEFORE this rapid. Use both
            # interior stock and endpoint uncertainty, not just end position.
            hits=0;original_hits=0;uncertain=0;min_margin=None
            samples=max(2,int(math.ceil(max(abs(z1-z0),abs(r1-r0))/min(step/2,0.125))))
            if samples>100000:raise InspectionError('Rapid model exceeds sampling limit')
            for k in range(samples+1):
                t=k/samples;z=z0+(z1-z0)*t;r=r0+(r1-r0)*t
                if stock_left<=z<=stock_right and 0<=r<stock_d/2-1e-8:
                    original_hits+=1
                    i=min(n-1,max(0,int((z-stock_left)/step)))
                    neighborhood=remaining[max(0,i-1):min(n,i+2)]
                    max_radius=max(neighborhood)
                    margin=r-max_radius
                    min_margin=margin if min_margin is None else min(min_margin,margin)
                    # A rapid at the end of a longitudinal cut is a
                    # boundary condition, not a proven stock collision.
                    endpoint=(abs(z-z0)<step*1.1 or abs(z-z1)<step*1.1)
                    if margin<-1e-7:
                        if endpoint:uncertain+=1
                        else:hits+=1
                    elif abs(margin)<step+1e-7:
                        uncertain+=1
            if hits:
                status='POSSIBLE_REMAINING_STOCK'
            elif uncertain:
                status='BOUNDARY_UNVERIFIED'
            else:
                status='NO_REMAINING_STOCK_DETECTED_2D_UNVERIFIED'
            # v1.6.11: audit the axial end face separately. A radial rapid
            # at the exact end of a cut can cross an uncut shoulder even if
            # the centerline bin was cleared. No tool width is assumed.
            end_z=z0 if direction=='RADIAL_RETRACT' else z1
            end_index=min(n-1,max(0,int((end_z-stock_left)/step)))
            # A width-aware NEIGHBORHOOD, not a verified tool sweep. Include
            # stock samples spanning the entered axial cutter width around the
            # nominal endpoint. Never infer holder, nose, or orientation.
            half_width=tool_width_mm/2
            near_indices=[j for j in range(n) if abs(stations[j]-end_z)<=half_width+step]
            if not near_indices: near_indices=[end_index]
            # Bound JSON size for very wide entered tools; preserve extrema.
            if len(near_indices)>2000: raise InspectionError('Tool-width neighborhood too large')
            nearby=[{'z':round(stations[j],5),'remaining_radius_mm':round(remaining[j],5)} for j in near_indices]
            end_uncertainty=bool(direction in ('RADIAL_RETRACT','RADIAL_APPROACH') and
                                 stock_left<=end_z<=stock_right)
            if end_uncertainty and status=='NO_REMAINING_STOCK_DETECTED_2D_UNVERIFIED':
                status='BOUNDARY_UNVERIFIED'
            # Conservative 2D review footprint: axial interval + radial nose
            # inflation. This is NOT a real insert/holder shape, and the bin
            # model is not a certified material-removal or collision simulation.
            if tool_orientation=='center':
                axial_lo,axial_hi=end_z-tool_width_mm/2,end_z+tool_width_mm/2
            elif tool_orientation=='left':
                axial_lo,axial_hi=end_z-tool_width_mm,end_z
            else:
                axial_lo,axial_hi=end_z,end_z+tool_width_mm
            sweep_indices=[j for j in range(n) if axial_lo-step<=stations[j]<=axial_hi+step]
            sweep_radius=max((remaining[j] for j in sweep_indices),default=None)
            sweep_min_margin=(min(r0,r1)-nose_radius_mm-sweep_radius if sweep_radius is not None else None)
            sweep_flag=bool(sweep_min_margin is not None and sweep_min_margin<0)
            footprint={'axial_z_min':axial_lo,'axial_z_max':axial_hi,
                'nose_radius_mm':nose_radius_mm,'orientation':tool_orientation,
                'maximum_estimated_neighbor_radius_mm':sweep_radius,
                'minimum_estimated_footprint_margin_mm':sweep_min_margin,
                'estimated_overlap_or_uncertainty':sweep_flag,
                'verified_collision':False,'verified_clearance':False,
                'note':'2D conservative review footprint only; cutter geometry, approach, holder, actual stock and shoulder unverified'}
            diagnostics.append({'line':b['line'],'motion_type':direction,
                'classification':status,'possible_stock_samples':hits,
                'boundary_uncertain_samples':uncertain,
                'original_envelope_samples':original_hits,
                'minimum_radial_margin_mm':min_margin,
                'endpoint_stock_unverified':end_uncertainty,
                'endpoint_neighbor_bins':nearby,'tool_footprint_review':footprint,
                'endpoint_tool_width_mm':tool_width_mm,
                'axial_width_window_z':[end_z-half_width,end_z+half_width],
                'neighbor_stock_radius_max_mm':max(remaining[j] for j in near_indices),
                'width_window_has_higher_stock':any(remaining[j]>min(r0,r1)+1e-7 for j in near_indices),
                'start':{'z':z0,'radius':r0},'end':{'z':z1,'radius':r1},
                'reason':('Radial retraction at an axial cut endpoint; neighboring stock bins remain uncertain' if direction=='RADIAL_RETRACT' and uncertain else 'Estimated remaining stock intersects sampled rapid path' if hits else '2D model cannot establish physical clearance'),
                'review_required':True,'tool_width_verified':False,
                'endpoint_shoulder_verified':False,
                'note':'Entered axial width only expands review neighborhood; cutter orientation, nose and shoulder unverified; NOT collision clearance'})
    return {'model':'Sequential 2D axial bins, point tool; endpoint stock unverified',
            'cell_mm':step,'stock_left_z':stock_left,'stock_right_z':stock_right,
            'stations_z':stations,'remaining_radius_mm':remaining,
            'rapid_diagnostics':diagnostics}

def inspect(points, *, stock_d, stock_length, depth, rpm, feed, finish_feed,
            allowance, finish_depth, clearance, stock_face, chuck_z, chuck_gap,
            tailstock, tailstock_tip_z, tip_clearance, tailstock_d, facing,
            roughing, finishing, entry_relief, finish_arcs=None, tool_width_mm=2.0,
            nose_radius_mm=0.4, tool_orientation="left", shoulder_z=None, exit_shift_mm=1.5, exit_margin_mm=0.5, physical_end_confirmed=False, free_space_declared=False, stock_continues_zminus=True, finished_shoulder_d=12.0, shoulder_axial_margin=0.6):
    values=[stock_d,stock_length,depth,rpm,feed,finish_feed,allowance,finish_depth,exit_shift_mm,exit_margin_mm,
            clearance,stock_face,chuck_z,chuck_gap,tailstock_tip_z,tip_clearance,tailstock_d,tool_width_mm,nose_radius_mm,finished_shoulder_d,shoulder_axial_margin]
    if any(not math.isfinite(x) for x in values): raise InspectionError('Non-finite numeric parameter')
    if tool_width_mm<=0 or tool_width_mm>100: raise InspectionError('Tool axial width must be >0 and <=100 mm')
    if nose_radius_mm<0 or nose_radius_mm>20: raise InspectionError('Nose radius must be between 0 and 20 mm')
    if tool_orientation not in ('center','left','right'): raise InspectionError('Invalid tool orientation')
    if abs(nose_radius_mm-0.4)>1e-6:
        raise InspectionError('DCMT070204 requires nominal nose radius 0.4 mm')
    if shoulder_z is not None and not math.isfinite(shoulder_z):
        raise InspectionError('Invalid shoulder Z')
    if stock_continues_zminus and physical_end_confirmed:
        raise InspectionError('Conflicting declarations: stock continues toward Z- but profile endpoint is marked physical end')
    if stock_continues_zminus and free_space_declared:
        raise InspectionError('Free space beyond profile end cannot be declared while stock continues toward Z-')
    if tip_clearance <= 0: raise InspectionError('Tip clearance must be positive')
    if tailstock and tailstock_tip_z >= stock_face:
        # Tip can be at or inside the workpiece only; positive Z beyond face is a separate case.
        raise InspectionError('Tailstock tip Z must be less than stock face Z')
    limit=tailstock_tip_z-tip_clearance if tailstock else None
    start_offset=stock_face-limit if tailstock else 0.0
    if tailstock and start_offset<=0:raise InspectionError('Invalid axial start offset')
    if not (facing or roughing or finishing):raise InspectionError('Select an operation')
    # Source generator cannot face with tailstock. Never misrepresent that as generated facing.
    facing_pending=bool(tailstock and facing)
    if facing_pending and not (roughing or finishing):
        raise InspectionError('Tailstock-facing path is not implemented; no motion can be generated')
    original_points=list(points)
    clipping_required=bool(tailstock and any(z>limit+1e-7 for z,r in points))
    if tailstock:
        if finish_arcs:
            # Even if an arc is wholly behind the limit, source generator's
            # tailstock arc convention is unverified. Fail closed.
            raise InspectionError('Tailstock arcs are not supported in 1.6.1 inspection')
        points=clip_outer_profile(points,limit)
    source=generate(points,stock_d,depth,rpm,feed,allowance,
        facing=bool(facing and not tailstock),roughing=roughing,finishing=finishing,
        clearance=clearance,finish_arcs=finish_arcs or {},finish_feed=finish_feed,
        finish_depth=finish_depth,stock_face_z=stock_face,chuck_front_z=chuck_z,
        chuck_gap=chuck_gap,stock_length=stock_length,tailstock=tailstock,
        start_offset=start_offset,tailstock_d=tailstock_d,entry_relief=entry_relief)
    # Parse source in diameter mode; no unrecognized motion may be silently omitted.
    motion=None; z=None; diameter=None; feed_now=None; moves=[]; warnings=[]; removed_zero_g1=[]
    for n,line in enumerate(source.splitlines(),1):
        stripped=line.strip()
        m=re.match(r'^(G0?[0123])(?:\s|$)',stripped,re.I)
        if not m:continue
        g=int(m.group(1)[1:]); params={k:float(v) for k,v in re.findall(r'([XZFIJK])\s*([-+]?\d+(?:\.\d+)?)',stripped,re.I)}
        if g in (2,3):
            raise InspectionError('Unsupported G02/G03 at source line %d; no partial inspection exported'%n)
        old_z=z;old_d=diameter
        z=params.get('Z',z);diameter=params.get('X',diameter)
        if 'F' in params:feed_now=params['F']
        if z is None or diameter is None:raise InspectionError('Incomplete motion at source line '+str(n))
        if g==1 and (feed_now is None or feed_now<=0):raise InspectionError('Missing G94 feed')
        move={'line':n,'g':g,'lathe_z':z,'diameter':diameter,'machine_x':z,
              'machine_y':diameter/2,'feed_mm_min':feed_now if g==1 else None}
        # Remove only redundant zero-length G01 records from the inspection
        # trajectory; preserve original source-line references for audit.
        if g==1 and old_z is not None and old_d is not None and abs(z-old_z)<1e-7 and abs(diameter-old_d)<1e-7:
            removed_zero_g1.append(n)
            continue
        moves.append(move)
        if tailstock and max(z,old_z if old_z is not None else z)>limit+1e-7:
            warnings.append({'line':n,'kind':'AXIAL_LIMIT','detail':'Tool tip crosses Z limit %.4f'%limit})
        if g==0 and old_d is not None and old_z is not None:
            if rapid_stock_intersection(old_z,old_d,z,diameter,stock_d,stock_face-stock_length,stock_face):
                warnings.append({'line':n,'kind':'RAPID_STOCK_ENVELOPE','detail':'G0 segment intersects original stock envelope; may be cleared by previous cutting but not verified'})
    nose_preview=inspect_profile_nose(points,nose_radius_mm)
    # Shoulder location is user-defined: larger stock persists toward Z-.
    # Never treat the profile endpoint as free space.
    shoulder=shoulder_z if shoulder_z is not None else min(z for z,r in points)
    # A confirmed physical end is NOT a shoulder. Never suggest a Z+ shoulder
    # escape at this location. Do not change source moves or infer free stock.
    if physical_end_confirmed:
        if abs(shoulder-min(z for z,r in points))>0.02:
            raise InspectionError('Physical end Z must match leftmost used profile Z within 0.02 mm')
        shoulder_checks=[]
        exit_candidates=[]
    else:
        shoulder_checks=shoulder_rapid_review(moves,shoulder,stock_d/2,nose_radius_mm)
        exit_candidates=[] if stock_continues_zminus else propose_exits(moves,points,shoulder,stock_d/2,nose_radius_mm,limit,exit_shift_mm,exit_margin_mm)
    # v1.6.16: endface preview is gated by explicit declaration of free space,
    # matching physical end / stock rear and a nominal chuck axial check.
    endface_candidates, endface_candidate_issues=propose_endface_exits(
        moves,shoulder,stock_face-stock_length,chuck_z,chuck_gap,
        tool_width_mm,nose_radius_mm,exit_margin_mm,
        free_space_declared,physical_end_confirmed)
    # Read-only motion-mode substitution proposal. The original G0 remains in
    # moves, warnings, stock analysis, and inspection-only TXT output.
    feed_retract_candidates=propose_feed_retracts(moves,shoulder,stock_continues_zminus,feed,finish_feed)
    continuation_guard=(review_continuation(moves,shoulder,stock_d,tool_width_mm,
                        stock_face-stock_length,stock_face) if stock_continues_zminus else None)
    blocked_lines={r['source_line'] for r in continuation_guard['blocked_retracts']} if continuation_guard else set()
    # A same-line G1 preview is misleading when the tool may sweep through
    # the Ø20 continuation. Suppress it; never modify the original G0 moves.
    feed_retract_candidates=[c for c in feed_retract_candidates if c['source_line'] not in blocked_lines]
    stopshort=stopshort_review(moves,shoulder,stock_d,finished_shoulder_d,
        tool_width_mm,nose_radius_mm,shoulder_axial_margin,stock_continues_zminus)
    backtrack=backtrack_review(moves,blocked_lines,shoulder,stock_d)
    stock_model=remaining_stock_2d(moves,stock_d,stock_face-stock_length,stock_face,tool_width_mm=tool_width_mm, nose_radius_mm=nose_radius_mm, tool_orientation=tool_orientation)
    sweep22=sweep22_review(moves,blocked_lines,stock_model,tool_width_mm,nose_radius_mm,limit,stock_d)
    strategy23=strategy23_review(moves,blocked_lines,shoulder,stock_d,finished_shoulder_d,
        approach_z=shoulder+0.1543,exit_z=shoulder+0.9543,
        nose_radius=nose_radius_mm,tool_width=tool_width_mm) if stock_continues_zminus else {'candidates':[],'candidate_count':0}
    exit24=exit24_review(moves,blocked_lines,shoulder,stock_d,finished_shoulder_d,
        depth,finish_depth,tool_width_mm,nose_radius_mm,stock_continues_zminus)
    diagonal25=diagonal25_review(moves,blocked_lines,shoulder,stock_d,finished_shoulder_d,
        nose_radius=nose_radius_mm,tool_width=tool_width_mm) if stock_continues_zminus else {'entries':[],'reviewed_endpoint_count':0,'exact_finished_diameter_preview_count':0,'verified_exit_count':0}
    diagnostic_by_line={d['line']:d for d in stock_model['rapid_diagnostics']}
    for alert in warnings:
        if alert['kind']=='RAPID_STOCK_ENVELOPE' and alert['line'] in diagnostic_by_line:
            diag=diagnostic_by_line[alert['line']]
            alert['stock_2d_classification']=diag['classification']
            alert['motion_type']=diag['motion_type']
            alert['detail']+='; 2D estimate: '+diag['classification']
    continuation_checks=[]
    if stock_continues_zminus:
        for d in stock_model['rapid_diagnostics']:
            if d.get('motion_type')=='RADIAL_RETRACT' and abs(d['start']['z']-shoulder)<0.02:
                d['endpoint_material_status']='CONTINUING_STOCK_Z_MINUS_UNVERIFIED'
                continuation_checks.append({'source_line':d['line'], 'z':shoulder,
                    'classification':'CONTINUING_STOCK_RETRACT_UNVERIFIED',
                    'note':'Raw stock extends toward chuck (Z-). Radial rapid at axial cut end is NOT cleared; no replacement motion generated.'})
        if continuation_checks:
            warnings.append({'line':None,'kind':'CONTINUING_STOCK_RETRACTIONS_BLOCKED',
                'detail':'%d G0 radial retracts at Z %.4f require verified clearance: stock continues toward chuck; no free end or automatic exit assumed'%(len(continuation_checks),shoulder)})
    if exit24['reviewed_endpoint_count']:
        warnings.append({'line':None,'kind':'EXIT24_NO_VERIFIED_PATH',
            'detail':'%d continuing-stock exits reviewed; zero verified, original G0 retained'%exit24['reviewed_endpoint_count']})
    if sweep22['candidate_count']:
        warnings.append({'line':None,'kind':'SWEEP22_REVIEW_UNVERIFIED',
            'detail':'%d reverse-path 2D footprint reviews, all unverified; original G0 remains blocked'%sweep22['candidate_count']})
    if backtrack['candidate_count']:
        warnings.append({'line':None,'kind':'G1_BACKTRACK_PREVIEW_UNVERIFIED',
            'detail':'%d reverse-cut G1 paths suggested for review only; no radial exit certified, original G0 retained'%backtrack['candidate_count']})
    if stopshort['candidate_count']:
        warnings.append({'line':None,'kind':'STOP_SHORT_PREVIEW_ONLY',
            'detail':'%d early-stop markers are NOT retract paths; machining allowance remains at shoulder'%stopshort['candidate_count']})
    if blocked_lines:
        warnings.append({'line':None,'kind':'CONTINUATION_G1_PREVIEW_SUPPRESSED',
            'detail':'%d G1-on-original-G0 previews suppressed: changing feed mode cannot clear Ø%.3f continuing stock; redesign required'%(len(blocked_lines),stock_d)})
    endface_checks=[]
    if physical_end_confirmed:
        for d in stock_model['rapid_diagnostics']:
            if (d.get('motion_type')=='RADIAL_RETRACT' and
                abs(d['start']['z']-shoulder)<0.02):
                endface_checks.append({'source_line':d['line'],'end_z':shoulder,
                    'classification':'PHYSICAL_END_DECLARED_CLEARANCE_UNVERIFIED',
                    'note':'No shoulder assumed; original radial G0 unchanged. Endface, remaining stock and tool/fixture clearance not verified.'})
        if endface_checks:
            warnings.append({'line':None,'kind':'PHYSICAL_ENDFACE_RETRACTIONS_UNVERIFIED',
                'detail':'%d radial G0 retracts at declared physical end remain unverified; no replacement paths generated'%len(endface_checks)})
        # Physical end and exposed stock rear are distinct user inputs; if
        # inconsistent, the original-stock model still assumes stock exists.
        stock_rear=stock_face-stock_length
        if abs(stock_rear-shoulder)>0.02:
            warnings.append({'line':None,'kind':'PHYSICAL_END_STOCK_EXTENT_MISMATCH',
                'detail':'Declared physical end Z %.4f differs from exposed-stock rear Z %.4f; verify stock geometry and chuck before interpreting 2D diagnostics'%(shoulder,stock_rear)})
    for check in shoulder_checks:
        warnings.append({'line':check['source_line'],'kind':'DCMT_SHOULDER_RETRACT',
                         'detail':check['reason']})
    if physical_end_confirmed and endface_candidate_issues:
        warnings.append({'line':None,'kind':'ENDFACE_PREVIEW_GATED',
            'detail':'No physical-end exit preview: '+', '.join(endface_candidate_issues)})
    if endface_candidates:
        warnings.append({'line':None,'kind':'ENDFACE_PREVIEW_UNVERIFIED',
            'detail':'%d endface exit concepts; no source moves changed; not collision verified'%len(endface_candidates)})
    if exit_candidates:
        warnings.append({'line':None,'kind':'CANDIDATE_EXITS_UNVERIFIED', 'detail':'%d proposed shoulder exits generated for inspection ONLY; no candidate replaces source motions'%len(exit_candidates)})
    if feed_retract_candidates:
        warnings.append({'line':None,'kind':'G1_RETRACT_PREVIEW_NOT_VALIDATED',
            'detail':'%d radial G0-to-G1 preview substitutions; G1 does NOT establish collision clearance; original G0 unchanged'%len(feed_retract_candidates)})
    if removed_zero_g1:
        warnings.append({'line':None,'kind':'REDUNDANT_G1_REMOVED',
            'detail':'%d zero-length G1 moves omitted from inspection path (source unchanged)'%len(removed_zero_g1)})
    warnings.extend([
        {'line':None,'kind':'FIXTURE_UNVERIFIED','detail':'Chuck, holder, tailstock geometry and offsets unverified'},
        {'line':None,'kind':'INDEPENDENT_SPINDLE','detail':'No spindle-ready interlock for separately driven motor'},
        {'line':None,'kind':'STOCK_UNVERIFIED','detail':'2D stock estimate with DCMT nose-offset preview; no physical tool/holder clearance verification'},
        {'line':None,'kind':'MACHINE_OUTPUT_BLOCKED','detail':'Inspection output only; not executable G-code'}])
    if facing_pending:
        warnings.append({'line':None,'kind':'FACING_NOT_GENERATED','detail':'Facing requested with tailstock: source generator cannot produce it; implement in future CAM revision'})
    lines=['; DDCS Expert 1.6.26 - INSPECTION ONLY - NOT EXECUTABLE',
           '; NO A AXIS, NO SPINDLE CONTROL, NO MACHINE-READY OUTPUT',
           '; Lathe Z -> mill X; lathe diameter X / 2 -> mill Y',
           '; Tailstock %s, axial limit %s'%('ON' if tailstock else 'OFF',str(limit)),
           '; Facing with tailstock: %s'%('NOT GENERATED' if facing_pending else 'not pending'),
           '; ORIGINAL Z PRESERVED; profile clipped at axial limit (no translation)',
           '; LEFT END: %s; Z %.4f; G0 clearance NOT VERIFIED'%('PHYSICAL END DECLARED' if physical_end_confirmed else ('STOCK CONTINUES Z- / MACHINING LIMIT' if stock_continues_zminus else 'SHOULDER/UNKNOWN'),shoulder)]
    lines.append('; G1 radial retract previews at continuing-stock endpoint SUPPRESSED; original G0 unchanged; NOT COLLISION VERIFIED')
    if continuation_guard:
        lines.append('; CONTINUING STOCK DIAMETER %.4f mm toward chuck; %d endpoint retracts BLOCKED / UNVERIFIED'%(stock_d,len(blocked_lines)))
        lines.append('; v1.6.22 2D REVERSE SWEEP REVIEW ONLY; original G0 unchanged; no collision verified')
    lines.append('; v1.6.23 USER END-STRATEGY IS PREVIEW ONLY; ORIGINAL G0 UNCHANGED; 4mm RADIAL PLUNGE NOT VALIDATED')
    lines.append('; v1.6.24 CONTINUING-STOCK EXIT REVIEW: %d blocked endpoints; 0 verified; NO EXIT PATH GENERATED'%exit24['reviewed_endpoint_count'])
    lines.append('; v1.6.25 DIAGONAL G1 + G0 PREVIEW ONLY: %d finish-end candidates; %d verified; original G0 unchanged'%(diagonal25['exact_finished_diameter_preview_count'],diagonal25['verified_exit_count']))
    for m in moves:
        lines.append('; SOURCE %d G%d X%.4f Y%.4f%s'%(m['line'],m['g'],m['machine_x'],m['machine_y'],
                  ' F%.3f'%m['feed_mm_min'] if m['feed_mm_min'] is not None else ''))
    report={'version':'1.6.28','inspection_only':True,'machine_code_allowed':False,
            'tool_specification':dict(TOOL), 'nose_offset_preview':nose_preview,
            'shoulder_z':shoulder, 'uncut_stock_toward':'UNKNOWN_AT_DECLARED_PHYSICAL_END' if physical_end_confirmed else ('Z-_CONFIRMED_BY_USER' if stock_continues_zminus else 'UNKNOWN'),
            'endpoint_type':'PHYSICAL_END_DECLARED' if physical_end_confirmed else ('MACHINING_LIMIT_WITH_CONTINUING_STOCK' if stock_continues_zminus else 'SHOULDER_OR_UNKNOWN'),
            'physical_end_confirmed':bool(physical_end_confirmed),
            'stock_continues_zminus':bool(stock_continues_zminus),
            'continuation_guard_1619':continuation_guard,
            'stopshort_review_1620':stopshort,
            'backtrack_review_1621':backtrack,
            'sweep_review_1622':sweep22,
            'end_strategy_review_1623':strategy23,
            'exit_feasibility_review_1624':exit24,
            'diagonal_exit_review_1625':diagonal25,
            'continuation_g1_previews_suppressed':sorted(blocked_lines),
            'continuation_retract_checks':continuation_checks,
            'continuation_retract_count':len(continuation_checks),
            'endface_retract_checks':endface_checks, 'endface_retract_count':len(endface_checks),
            'free_space_declared':bool(free_space_declared),
            'candidate_endface_exits':endface_candidates,
            'endface_candidate_count':len(endface_candidates),
            'endface_candidate_issues':endface_candidate_issues,
            'physical_end_stock_rear_consistent':abs((stock_face-stock_length)-shoulder)<=0.02 if physical_end_confirmed else None,
            'insert_shoulder_rapid_checks':shoulder_checks,
            'insert_shoulder_rapid_count':len(shoulder_checks),
            'toolpath_nose_compensation_applied':False, 'candidate_shoulder_exits':exit_candidates,
            'candidate_g1_retracts':feed_retract_candidates,'candidate_g1_retract_count':len(feed_retract_candidates),
            'original_g0_retained':True,'g1_retract_preview_only':True,
            'candidate_exit_count':len(exit_candidates)+len(endface_candidates),'candidate_paths_machine_approved':False,
            'candidate_shoulder_review_linked':not physical_end_confirmed,
            'tailstock':'on' if tailstock else 'off','axial_limit_z':limit,
            'facing_requested':bool(facing),'facing_generated':bool(facing and not facing_pending),
            'facing_pending':facing_pending,'profile_clipped':clipping_required,
            'original_z_range':[min(z for z,r in original_points),max(z for z,r in original_points)],
            'used_z_range':[min(z for z,r in points),max(z for z,r in points)],
            'moves':moves,'alerts':warnings,'rapid_stock_alerts':sum(a['kind']=='RAPID_STOCK_ENVELOPE' for a in warnings),
            'rapid_check':'Original envelope + approximate sequential 2D remaining stock; all flagged rapids still require review',
            'rapid_review_required':True,'rapid_review_count':len(stock_model['rapid_diagnostics']),
            'endpoint_shoulder_review_count':sum(bool(d['endpoint_stock_unverified']) for d in stock_model['rapid_diagnostics']),
            'physical_collision_verification':False,'tool_axial_width_mm':tool_width_mm,'tool_nose_radius_mm':nose_radius_mm,
            'tool_orientation':tool_orientation,'holder_hand':'R','tip_facing':'Z-', 'tool_footprint_verified':False,
            'tool_width_model':'Conservative 2D review footprint, NOT physical collision or clearance verification',
            'stock_2d':stock_model,'removed_zero_length_g1_source_lines':removed_zero_g1,
            'rapid_classification_counts':{kind:sum(d['classification']==kind for d in stock_model['rapid_diagnostics']) for kind in ('POSSIBLE_REMAINING_STOCK','BOUNDARY_UNVERIFIED','NO_REMAINING_STOCK_DETECTED_2D_UNVERIFIED')},
            'rapid_motion_counts':{kind:sum(d['motion_type']==kind for d in stock_model['rapid_diagnostics']) for kind in ('RADIAL_RETRACT','RADIAL_APPROACH','AXIAL_RAPID','DIAGONAL_RAPID')},
            'mapping':{'mill_x':'lathe_z','mill_y':'lathe_diameter/2'},
            'unsupported':['machine-ready G-code','G02/G03 arc conversion','3D collision check','spindle interlock']}
    from expert_shoulder import review as shoulder_review
    report['shoulder_analysis']=shoulder_review(report)
    report['shoulder_analysis']['physical_end_confirmed']=bool(physical_end_confirmed)
    return '\n'.join(lines)+'\n',report
