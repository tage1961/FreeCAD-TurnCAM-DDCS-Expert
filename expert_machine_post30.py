"""DDCS Expert 2-axis post: optional conservative G02/G03 fit for finish cuts.

Arc fitting is restricted to uninterrupted finishing-feed G01 blocks; a fit is
accepted only if every input point matches the circle and the quantized arc.
No collision checking is performed by this module.
"""
import math

DECIMALS = 3
ARC_TOLERANCE_MM = 0.015


def _circle(a, b, c):
    ax, ay = a; bx, by = b; cx, cy = c
    d = 2*((ax-cx)*(by-cy)-(ay-cy)*(bx-cx))
    if abs(d) < 1e-7:
        return None
    u = ax*ax+ay*ay-cx*cx-cy*cy
    v = bx*bx+by*by-cx*cx-cy*cy
    ox = (u*(by-cy)-v*(ay-cy))/d
    oy = ((ax-cx)*v-(bx-cx)*u)/d
    r = math.hypot(ax-ox,ay-oy)
    return (ox,oy,r) if math.isfinite(r) and 0.05 < r < 10000 else None


def _fit_arc(points, tol=ARC_TOLERANCE_MM):
    if len(points) < 4:
        return None
    fit = _circle(points[0], points[len(points)//2], points[-1])
    if fit is None:
        return None
    cx,cy,r = fit
    if any(abs(math.hypot(x-cx,y-cy)-r)>tol for x,y in points):
        return None
    angles = [math.atan2(y-cy,x-cx) for x,y in points]
    increments = [((b-a+math.pi)%(2*math.pi)-math.pi) for a,b in zip(angles,angles[1:])]
    if not increments or any(abs(v)<1e-7 for v in increments):
        return None
    if not (all(v>0 for v in increments) or all(v<0 for v in increments)):
        return None
    sweep = sum(increments)
    if not 0.10 < abs(sweep) <= math.pi+1e-7:
        return None
    # Verify rounding of endpoint and relative center offsets to three decimals.
    start = tuple(round(v,3) for v in points[0])
    end = tuple(round(v,3) for v in points[-1])
    i,j = round(cx-start[0],3), round(cy-start[1],3)
    qc = (start[0]+i,start[1]+j)
    qr = math.hypot(i,j)
    if qr < 0.05 or abs(math.hypot(end[0]-qc[0],end[1]-qc[1])-qr)>tol:
        return None
    if any(abs(math.hypot(round(x,3)-qc[0],round(y,3)-qc[1])-qr)>tol for x,y in points):
        return None
    return (3 if sweep>0 else 2,i,j)


def render_machine_nc(report):
    if report.get('mapping') != {'mill_x':'lathe_z','mill_y':'lathe_diameter/2'}:
        raise ValueError('Unexpected lathe-to-machine axis mapping')
    moves = report.get('moves') or []
    if not moves:
        raise ValueError('No toolpath to export')
    prepared=[]
    for n,m in enumerate(moves,1):
        g=int(m['g'])
        if g not in (0,1):
            raise ValueError('Unsupported motion at move %d'%n)
        x,y=float(m['machine_x']),float(m['machine_y'])
        if not all(math.isfinite(v) for v in (x,y)):
            raise ValueError('Nonfinite coordinate at move %d'%n)
        f=None
        if g==1:
            f=float(m['feed_mm_min'])
            if not math.isfinite(f) or f<=0:
                raise ValueError('Invalid feed at move %d'%n)
        if prepared and (x,y)==prepared[-1][1]:
            continue
        prepared.append((g,(x,y),f))
    lines=[
        '(TURN CAM DDCS EXPERT V1.6.33)',
        '(UNVERIFIED TOOLPATH - COLLISION CHECK NOT PERFORMED BY POST)',
        '(LATHE Z = MACHINE X; LATHE DIAMETER / 2 = MACHINE Y)',
        '(G02/G03: XY PLANE; I/J RELATIVE TO ARC START)',
        '(THREE DECIMAL COORDINATES AND ARC CENTER OFFSETS)',
        '(ORIGINAL G00 RETRACTS PRESERVED - CHECK BEFORE RUNNING)',
        '(NO A AXIS; NO SPINDLE COMMANDS; MACHINE Z NOT COMMANDED)',
        'G21 G90 G94 G17',
    ]
    # Only finish-feed runs: choose minimum G01 feed (usually 100 vs rough 180).
    feeds=[f for g,p,f in prepared if g==1]
    finish_feed=min(feeds) if feeds else None
    idx=0
    while idx<len(prepared):
        g,pt,f=prepared[idx]
        if g==1 and idx>0 and f==finish_feed:
            # Collect successive same-feed G01s, with the previous position as start.
            end=idx
            while end+1<len(prepared) and prepared[end+1][0]==1 and prepared[end+1][2]==f:
                end+=1
            points=[prepared[idx-1][1]]+[prepared[k][1] for k in range(idx,end+1)]
            pos=0
            while pos<len(points)-1:
                chosen=None
                # Longest acceptable arc; do not cross >180 degree sweep.
                for stop in range(min(len(points)-1,pos+60),pos+2,-1):
                    arc=_fit_arc(points[pos:stop+1])
                    if arc is not None:
                        chosen=(stop,arc)
                        break
                if chosen:
                    stop,(ag,i,j)=chosen
                    x,y=points[stop]
                    lines.append('G%02d X%.3f Y%.3f I%.3f J%.3f F%.3f'%(ag,x,y,i,j,f))
                    pos=stop
                else:
                    x,y=points[pos+1]
                    lines.append('G01 X%.3f Y%.3f F%.3f'%(x,y,f))
                    pos+=1
            idx=end+1
            continue
        x,y=pt
        line='G%02d X%.3f Y%.3f'%(g,x,y)
        if g==1: line+=' F%.3f'%f
        lines.append(line)
        idx+=1
    lines.append('M30')
    return '\n'.join(lines)+'\n'
