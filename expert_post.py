"""Mach3 Turn diameter-mode G-code generator. Review and simulate before machining."""
import math
from expert_geometry import radius_at

class CAMError(ValueError):pass

def validate_rough_envelope(points, path, allowance, tolerance=1e-5):
    """Check every linear rough segment against the piecewise-linear finish envelope.

    Includes profile vertices between rough segment endpoints, not only sampled
    points; this prevents a simplified diagonal from cutting through a shoulder.
    """
    for (za,ra),(zb,rb) in zip(path,path[1:]):
        if zb < za-tolerance:
            raise CAMError('Roughing path reverses in Z.')
        zs=[z for z,r in points if za+tolerance<z<zb-tolerance]
        for z in zs:
            if abs(zb-za)<tolerance:
                rcheck=min(ra,rb)
            else:
                t=(z-za)/(zb-za)
                rcheck=ra+t*(rb-ra)
            # Multiple radii at a shoulder: the outside envelope is the maximum.
            nearby=[r for pz,r in points if abs(pz-z)<tolerance]
            if nearby:
                needed=max(nearby)
            else:
                needed=radius_at(points,z)
            if rcheck < needed+allowance-tolerance:
                raise CAMError('Roughing path intersects the profile/finishing allowance at Z%.4f.'%z)


def generate(points, stock_d, depth, rpm, feed, allowance=.2, facing=True, roughing=True, finishing=True, clearance=2., face_feed=None, finish_arcs=None, finish_feed=None, finish_depth=None, stock_face_z=0., chuck_front_z=None, chuck_gap=2., stock_length=None, tailstock=True, start_offset=10., tailstock_d=30., entry_relief=False):
    if finish_feed is None:finish_feed=feed
    if finish_depth is None:finish_depth=allowance if allowance>0 else depth
    vals=(stock_d,depth,rpm,feed,finish_feed,allowance,clearance,finish_depth,stock_face_z,chuck_gap)
    if any(not math.isfinite(v) for v in vals):raise CAMError('All numeric values must be finite.')
    if stock_d<=0 or depth<=0 or rpm<=0 or feed<=0 or finish_feed<=0 or allowance<0 or clearance<=0 or finish_depth<=0:raise CAMError('Invalid cutting parameters.')
    if not 50<=rpm<=10000:raise CAMError('RPM outside the permitted validation range 50–10000.')
    if not (1<=feed<=20000 and 1<=finish_feed<=20000):raise CAMError('Feed outside the permitted range 1–20000 mm/min.')
    if tailstock:
        if not math.isfinite(start_offset) or start_offset <= 0:
            raise CAMError('Start offset from right end must be positive.')
        if not math.isfinite(tailstock_d) or tailstock_d <= 0:
            raise CAMError('Enter the tailstock exclusion diameter.')
        if facing:
            raise CAMError('Facing at Z0 is not allowed with tailstock enabled.')
        if (roughing or finishing) and not entry_relief:
            raise CAMError('Confirm that radial G1 entry at start Z has been checked for tool, tailstock, and actual stock.')
        # 1.6.1: never translate the original design contour. The caller must
        # clip the profile at the verified axial limit before generation.
        # Any contour crossing the limit is rejected here, not silently shifted.
        axial_limit = stock_face_z - start_offset
        if not points or max(z for z, r in points) > axial_limit + 1e-6:
            raise CAMError('Tailstock contour exceeds axial limit. Clip profile first; do not shift it.')
        if finish_arcs:
            raise CAMError('Tailstock arc paths are not verified for clipping; inspection blocked.')
    if not points or len(points)<2:raise CAMError('Ingen gyldig kontur.')
    # Refuse axis/end-face paths; those must be extracted before postprocessing.
    if points[0][1]<=1e-5 or points[-1][1]<=1e-5:
        raise CAMError('Konturen indeholder centerlinje eller endeflade. G-kode blokeret.')
    if any(points[i+1][0]<points[i][0]-1e-5 for i in range(len(points)-1)):
        raise CAMError('Z-tilbagegang i konturen. G-kode blokeret.')
    target=max(r for z,r in points)
    stock_r=stock_d/2
    if target>stock_r+1e-6:raise CAMError('Contour exceeds stock diameter.')
    if any(r<0 for z,r in points):raise CAMError('Negativ profilradius.')
    if not (facing or roughing or finishing):raise CAMError('Select at least one operation.')
    if not roughing and not finishing and not facing:raise CAMError('Ingen operation.')
    zmin=points[0][0]; zmax=points[-1][0]
    if zmax>1e-5 or zmin>=zmax:raise CAMError('Invalid Z range.')
    if stock_length is None:
        raise CAMError('Enter exposed stock length in mm before exporting.')
    if not math.isfinite(stock_length) or stock_length <= 0:
        raise CAMError('Stock length must be greater than 0 mm.')
    stock_back_z = stock_face_z - stock_length
    if zmin < stock_back_z - 1e-6:
        raise CAMError('Contour extends past the stock rear end Z%.4f. Increase stock length or correct Z0.' % stock_back_z)
    if chuck_front_z is not None and stock_back_z < chuck_front_z - 1e-6:
        raise CAMError('Stock rear end Z%.4f extends behind chuck front face Z%.4f. This model supports exposed stock only; enter the exposed length up to the chuck.' % (stock_back_z, chuck_front_z))
    if chuck_gap < 0:raise CAMError('Patronafstand skal vaere >= 0.')
    if stock_face_z > zmax+1e-6 and not tailstock:
        raise CAMError('Raamaterialets forside ligger foran Z0. Plan-/konturstart blokeret; ret Z0 eller plan fra sikkert udgangspunkt.')
    if chuck_front_z is None:
        raise CAMError('Patronens forside Z skal angives foer G-kode kan eksporteres.')
    if chuck_front_z is not None:
        if not math.isfinite(chuck_front_z):raise CAMError('Chuck Z must be finite.')
        if zmin < chuck_front_z+chuck_gap-1e-6:
            raise CAMError('Contour is too close to chuck front face. Increase chuck clearance or correct geometry.')
    safe_x=max(stock_d,tailstock_d if tailstock else stock_d)+2*clearance
    if chuck_front_z+chuck_gap >= zmin-1e-6:
        raise CAMError('Insufficient safety clearance at the left end of the contour.')
    def xfmt(r):return 'X%.4f'%(2*r)
    def zfmt(z):return 'Z%.4f'%z
    g=['(TurnCAM 1.5.13 - EXPERIMENTAL CODE)', '(SIMULATE AND VERIFY BEFORE RUNNING)',
       '(X DIAMETER; Z0 RIGHT END; Z- TOWARD CHUCK)',
       '(VERIFY MACH3 DIAMETER MODE, I RADIUS, WORK ZERO AND TOOL)',
       '(WARNING: NO COMPLETE COLLISION CHECK OF CHUCK, HOLDER OR STOCK)',
       '(STOCK FRONT Z%.4f; CHUCK FRONT %s; MIN CLEARANCE %.4f)'%(stock_face_z, 'UNKNOWN' if chuck_front_z is None else 'Z%.4f'%chuck_front_z, chuck_gap),
       '(STOCK LENGTH %.4f MM; STOCK REAR Z%.4f)'%(stock_length,stock_back_z),
       '(WARNING: NO VERIFIED REMAINING-STOCK / TOOL-CONTACT MODEL AT SHOULDERS)',
       '(TAILSTOCK %s; START Z%.4f; EXCLUSION DIAMETER %.4f; ENTRY CONFIRMED %s)'%('ON' if tailstock else 'OFF',-start_offset if tailstock else 0.,tailstock_d if tailstock else 0.,'YES' if entry_relief else 'NO'),
       '(ORIGINAL SKETCH COORDINATES PRESERVED; AXIAL LIMIT Z%.4f)'%(stock_face_z-start_offset if tailstock else stock_face_z),
       '(NO FACING TOWARD X0 WITH TAILSTOCK ENABLED)',
       'G21 G18 G40 G80 G90','G97 S%d M3'%round(rpm),'T0101','G94',
       'G0 X%.4f Z%.4f'%(safe_x,(stock_face_z-start_offset if tailstock else clearance))]
    if facing:
        g+=['(FACING - VERIFY CLEAR END FACE AND CENTER CLEARANCE)',
            'G0 X%.4f Z0.0000'%safe_x,
            'G1 X0.0000 F%.4f'%(face_feed or feed),
            'G0 X%.4f'%safe_x,
            'G0 Z%.4f'%clearance]
    if roughing:
        # Conservative: never command below the target profile + finishing allowance.
        min_rough=min(r for z,r in points)+allowance
        if min_rough > stock_r + 1e-6:
            raise CAMError('Finishing allowance exceeds stock.')
        # Build unique radial levels, including one exact final level.
        # Avoid an extra level caused by floating-point roundoff.
        levels=[]
        current=stock_r
        while current-min_rough>1e-7:
            current=max(min_rough,current-depth)
            if levels and abs(levels[-1]-current)<1e-7:break
            levels.append(current)
            if len(levels)>500:raise CAMError('Too many roughing passes (>500).')
        # Keep shoulders in the original profile, but suppress redundant
        # intermediate points on straight G1 segments (not arc finish data).
        def simplify(path):
            result=[]
            for z,r in path:
                if result and math.dist((z,r),result[-1])<1e-7:continue
                while len(result)>=2:
                    az,ar=result[-2];bz,br=result[-1]
                    cross=(bz-az)*(r-br)-(br-ar)*(z-bz)
                    dot=(bz-az)*(z-bz)+(br-ar)*(r-br)
                    if abs(cross)<1e-7 and dot>=-1e-8:result.pop()
                    else:break
                result.append((z,r))
            return result
        # Each axial region is roughed only where its local stock envelope
        # actually decreases. Regions separated by uncut shoulders are handled
        # independently; no cutting move crosses a non-active region.
        emitted=[]
        previous=[stock_r for _ in points]
        tol=1e-6
        for level in levels:
            radii=[max(level,r+allowance) for z,r in points]
            if any(a-b>depth+tol for a,b in zip(previous,radii)):
                raise CAMError('Roughing cut exceeds radial depth of cut.')
            active=[a-b>tol for a,b in zip(previous,radii)]
            if not any(active):continue
            # Adjacent active vertices form an axial cutting region. At a
            # shoulder the interval is bounded by its original vertices.
            regions=[];start=None
            for idx,on in enumerate(active):
                if on and start is None:start=idx
                if start is not None and (not on or idx==len(active)-1):
                    end=idx if on else idx-1
                    if end>start:regions.append((start,end))
                    else:
                        # A single vertex may be a real vertical shoulder.
                        # Include its adjacent edge and validate it below.
                        if start>0:regions.append((start-1,start))
                        elif start+1<len(points):regions.append((start,start+1))
                    start=None
            emitted.append((level,regions,radii,previous[:]))
            previous=radii
        g+=['(EXTERNAL ROUGHING - %d LEVELS; AP %.4f MM; ALLOWANCE %.4f MM; F %.2f MM/MIN)'%(len(emitted),depth,allowance,feed),
            '(LOCAL Z REGIONS; RADIAL G1 ENTRY; VERIFY SHOULDERS AND TOOL CLEARANCE)']
        for pass_index,(level,regions,radii,prior) in enumerate(emitted,1):
            g.append('(ROUGH PASS %d/%d; LEVEL X%.4f; %d REGIONS)'%(pass_index,len(emitted),2*level,len(regions)))
            for region_number,(left,right) in enumerate(reversed(regions),1):
                # A conservative per-region approach: stay outside the entire
                # raw cylinder for rapid Z positioning, then feed radially.
                # Never rapid to an inner diameter while inside raw stock.
                zr=points[right][0]
                zl=points[left][0]
                path=list(zip((points[k][0] for k in range(left,right+1)),radii[left:right+1]))
                validate_rough_envelope(points,path,allowance)
                g.append('(ROUGH REGION %d; Z%.4f TO Z%.4f)'%(region_number,zr,zl))
                # Warn at every radial entry: local radial depth does not
                # establish actual cutter contact at shoulders or grooves.
                g.append('(VERIFY RADIAL ENTRY AND SHOULDER CLEARANCE AT Z%.4f)'%zr)
                g.append('G0 X%.4f'%safe_x)
                g.append('G0 Z%.4f'%zr)
                # Start at the previous machined surface; radial depth <= AP.
                g.append('G1 X%.4f F%.4f'%(2*prior[right],feed))
                g.append('G1 X%.4f'% (2*radii[right]))
                last=(zr,radii[right])
                for z,r in reversed(path[:-1]):
                    if math.dist((z,r),last)>1e-6:
                        g.append('G1 %s %s'%(xfmt(r),zfmt(z)))
                        last=(z,r)
                g.append('G0 X%.4f'%safe_x)
            g.append('G0 Z%.4f'%(stock_face_z-start_offset if tailstock else clearance))
    if finishing and tailstock and not roughing and stock_r-points[-1][1]>finish_depth+1e-6:
        raise CAMError('Finishing without roughing at start Z would exceed the radial cut limit. Enable roughing or prepare the stock.')
    if finishing:
        # Intermediate finishing passes are radial offsets of the approved profile.
        # The final pass uses the exact approved geometry and verified G2/G3 arcs.
        finish_offsets=[]
        remaining=allowance
        while remaining>1e-7:
            remaining=max(0.,remaining-finish_depth)
            finish_offsets.append(remaining)
            if len(finish_offsets)>500:raise CAMError('Too many finishing passes (>500).')
        if not finish_offsets:finish_offsets=[0.]
        g.append('(FINISH PASSES %d; MAX RADIAL AP %.4f MM; ROUGHING ALLOWANCE %.4f MM)'%(len(finish_offsets),finish_depth,allowance))
        for pass_number,offset in enumerate(finish_offsets,1):
            pass_points=[(z,r+offset) for z,r in points]
            g.append('(FINISH PASS %d/%d; REMAINING ALLOWANCE %.4f MM)'%(pass_number,len(finish_offsets),offset))
            g.extend(_finish_pass(pass_points,finish_feed,clearance,safe_x,zmax,finish_arcs if offset<1e-7 else None,tailstock))
    g+=['M5','M30']
    program='\n'.join(g)+'\n'
    validate_motion_safety(program,stock_d,stock_face_z,chuck_front_z,chuck_gap,clearance,tailstock,start_offset,tailstock_d)
    return program


def _finish_pass(points,finish_feed,clearance,safe_x,zmax,finish_arcs,tailstock=False):
    g=[]
    def xfmt(r):return 'X%.4f'%(2*r)
    def zfmt(z):return 'Z%.4f'%z
    # Approach in front of the workpiece; intermediate contours are radially offset.
    if True:
        g+=['(EXTERNAL FINISH - G2/G3 ONLY FOR VERIFIED SKETCH ARCS; F %.2f MM/MIN)'%finish_feed,
            'G0 X%.4f Z%.4f'%(safe_x,zmax if tailstock else clearance)]
        if tailstock:
            g.append('(TAILSTOCK: RADIAL ENTRY REQUIRES VERIFIED CLEARANCE AT Z%.4f)'%zmax)
            g.append('G1 %s F%.4f'%(xfmt(points[-1][1]),finish_feed))
        else:
            g.extend(['G0 %s'%xfmt(points[-1][1]),'G1 %s F%.4f'%(zfmt(zmax),finish_feed)])
        # finish_arcs maps a validated path index to (end_index, center_z, center_r).
        # I and K are incremental center offsets in radius-space; verify Mach3 convention.
        i=len(points)-1
        while i>0:
            arc=(finish_arcs or {}).get(i)
            if arc is not None:
                j,cz,cr=arc
                if not (0<=j<i):raise CAMError('Invalid arc index.')
                start=points[i];end=points[j]
                radius=math.hypot(start[0]-cz,start[1]-cr)
                if radius<=1e-7 or math.dist(start,end)<=1e-7:raise CAMError('Invalid circular arc.')
                if abs(math.hypot(end[0]-cz,end[1]-cr)-radius)>0.02:raise CAMError('Arc endpoint does not match radius.')
                # G18 signed rotation in (X-radius, Z) coordinates.
                angles=[math.atan2(points[k][0]-cz,points[k][1]-cr) for k in range(i,j-1,-1)]
                turns=[(b-a+math.pi)%(2*math.pi)-math.pi for a,b in zip(angles,angles[1:])]
                sweep=sum(turns)
                if abs(sweep)<1e-5 or abs(sweep)>=2*math.pi-1e-5:raise CAMError('Ambiguous arc direction.')
                if abs(sweep)>math.pi+1e-5:
                    raise CAMError('Arc exceeding 180 degrees must be split before export.')
                if any(abs(math.hypot(points[k][0]-cz,points[k][1]-cr)-radius)>0.02 for k in range(j,i+1)):
                    raise CAMError('Arc points are not on the same circle.')
                gcode='G3' if sweep>0 else 'G2'
                i_offset=cr-start[1]
                k_offset=cz-start[0]
                g.append('%s %s %s I%.4f K%.4f'%(gcode,xfmt(end[1]),zfmt(end[0]),i_offset,k_offset))
                i=j
            else:
                i-=1
                z,r=points[i]
                if math.dist((z,r),points[i+1])>1e-6:
                    g.append('G1 %s %s'%(xfmt(r),zfmt(z)))
        g+=['G0 X%.4f'%safe_x,'G0 Z%.4f'%(zmax if tailstock else clearance)]
    return g


def validate_motion_safety(program, stock_d, stock_face_z, chuck_front_z, chuck_gap, clearance, tailstock=False, start_offset=10., tailstock_d=30.):
    """Fail-closed static check of rapid motion in the assumed cylindrical stock envelope.

    This is NOT a holder, chuck-jaw, or material-removal collision simulator.
    """
    import re
    pos=None
    stock_r=stock_d/2.
    safe_z=stock_face_z+clearance
    for number,line in enumerate(program.splitlines(),1):
        m=re.match(r'^(G0|G1|G2|G3)\s',line)
        if not m:continue
        params={k:float(v) for k,v in re.findall(r'([XZ])(-?\d+(?:\.\d+)?)',line)}
        if not params:continue
        target=(params.get('Z',pos[0] if pos else 0.),params.get('X',pos[1] if pos else stock_d+2*clearance))
        if not all(math.isfinite(v) for v in target):raise CAMError('Non-finite coordinate in G-code.')
        if tailstock and target[0]>-start_offset+1e-5:
            raise CAMError('Tailstock exclusion zone violated at line %d.'%number)
        if m.group(1)=='G0' and pos is not None:
            za,xa=pos;zb,xb=target
            # Conservative linear interpolation of a rapid segment.
            for j in range(21):
                t=j/20.;z=za+(zb-za)*t;x=xa+(xb-xa)*t
                if z < stock_face_z-1e-6 and x < stock_d-1e-5 and not (abs(zb-za)<1e-7 and xb>=xa-1e-7):
                    raise CAMError('G0 enters raw stock at line %d (X%.3f Z%.3f).'%(number,x,z))
                if z <= chuck_front_z+chuck_gap-1e-6:
                    raise CAMError('G0 enters chuck safety zone at line %d.'%number)
        pos=target
    return True
