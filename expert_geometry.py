"""Contour conversion and restrictive envelope validation."""
import math
class DXFError(ValueError):
    """Fejl i konturfortolkning eller geometri."""
    pass

def sampled_segments(segments, tolerance=.05):
    paths=[]
    for kind,a,b,center in segments:
        if kind=='line': paths.append([a,b]);continue
        cx,cy,ccw=center
        r=math.hypot(a[0]-cx,a[1]-cy)
        if r<1e-8: raise DXFError('ARC med nulradius.')
        aa=math.atan2(a[1]-cy,a[0]-cx);bb=math.atan2(b[1]-cy,b[0]-cx)
        sweep=(bb-aa)%(2*math.pi) if ccw else -((aa-bb)%(2*math.pi))
        # Identical start/end angles in a DXF ARC represent a full circle
        # for display purposes. This geometry is NOT automatically approved
        # for turning: profile validation below still rejects closed loops.
        if abs(sweep)<1e-9:
            # Identical endpoints are ambiguous: never silently invent a full
            # circle from an ARC, which may actually be a zero-length arc.
            # True circles must be represented by DXF CIRCLE entities.
            # A zero-angle ARC cannot be reconstructed reliably; preview a marker only.
            # Machining validation rejects this degenerate path.
            paths.append([a, a])
            continue
        step=2*math.acos(max(-1.,min(1.,1-tolerance/r))) if tolerance<r else math.pi/4
        n=max(2,min(2000,math.ceil(abs(sweep)/max(step,1e-4))))
        paths.append([(cx+r*math.cos(aa+sweep*i/n),cy+r*math.sin(aa+sweep*i/n)) for i in range(n+1)])
    return paths

def profile_from_segments(segments, tolerance=.05):
    """Extract an open outer path from a single DXF outline.

    Closed outlines, duplicate edges and radial end walls are accepted for
    *preview*, but ambiguous machining geometry remains blocked.
    """
    paths=sampled_segments(segments,tolerance)
    eps=.02
    def same(a,b):return math.dist(a,b)<eps
    # Remove exact duplicate edges, including reversed duplicates.
    unique=[]
    for path in paths:
        if same(path[0],path[-1]):continue
        if not any((same(path[0],q[0]) and same(path[-1],q[-1])) or
                   (same(path[0],q[-1]) and same(path[-1],q[0])) for q in unique):
            unique.append(path)
    if not unique:raise DXFError('Ingen brugbare segmenter.')
    if len(unique)==1 and len(paths)>1:
        raise DXFError('Kun en dobbelt linje; ingen komplet kontur.')
    # A closing axis line connects both ends of a turning outline.
    # Remove it only when it lies on Y=0 and spans the full axial range.
    xmin=min(pt[0] for path in unique for pt in path)
    xmax=max(pt[0] for path in unique for pt in path)
    closing=[]
    for i,path in enumerate(unique):
        if (all(abs(y)<eps for x,y in path) and
            abs(min(path[0][0],path[-1][0])-xmin)<eps and
            abs(max(path[0][0],path[-1][0])-xmax)<eps):closing.append(i)
    if len(closing)==1:unique.pop(closing[0])
    unused=list(unique);chain=unused.pop(0)
    while unused:
        match=None
        for i,p in enumerate(unused):
            if same(chain[-1],p[0]):match=(i,p[1:],False);break
            if same(chain[-1],p[-1]):match=(i,list(reversed(p[:-1])),False);break
            if same(chain[0],p[-1]):match=(i,p[:-1],True);break
            if same(chain[0],p[0]):match=(i,list(reversed(p[1:])),True);break
        if match is None:raise DXFError('Multiple disconnected contours; select one profile.')
        i,add,front=match
        chain=add+chain if front else chain+add
        unused.pop(i)
    if same(chain[0],chain[-1]):raise DXFError('Closeket kontur uden entydig akselinje; vælg profil manuelt.')
    if any(not(math.isfinite(x) and math.isfinite(y)) for x,y in chain):
        raise DXFError('Invalid coordinates.')
    # DXF sketches may be drawn below the X axis. Mirror the entire
    # contour only if all its nonzero radial values are negative.
    ys=[y for x,y in chain]
    if max(ys)<=eps and min(ys)<-eps:chain=[(x,-y) for x,y in chain]
    elif min(ys)<-eps:raise DXFError('Profile crosses the centerline; select the correct radial axis.')
    if chain[0][0]>chain[-1][0]:chain.reverse()
    # Radial end walls share Z. Preserve their outermost radial value.
    # Internal vertical walls are not safe to flatten into an envelope.
    result=[]
    for x,y in chain:
        z=x-xmax
        if result and abs(z-result[-1][0])<1e-5:
            if abs(x-xmin)>eps and abs(x-xmax)>eps:
                raise DXFError('Internal vertical shoulder requires a separate toolpath strategy.')
            result[-1]=(result[-1][0],max(result[-1][1],y))
        elif result and z<result[-1][0]-1e-5:
            raise DXFError('Contour reverses in Z and requires manual profile selection.')
        else:result.append((z,y))
    if len(result)<2 or max(y for z,y in result)<=0:
        raise DXFError('Ingen entydig udvendig profil.')
    return [(round(z,5),round(y,5)) for z,y in result]

def radius_at(pts,z):
    if z<=pts[0][0]:return pts[0][1]
    if z>=pts[-1][0]:return pts[-1][1]
    lo=0;hi=len(pts)-1
    while hi-lo>1:
        mid=(lo+hi)//2
        if pts[mid][0]<=z:lo=mid
        else:hi=mid
    a=pts[lo];b=pts[hi]
    return a[1]+(b[1]-a[1])*(z-a[0])/(b[0]-a[0])


def profile_from_vertical_dxf(segments, tolerance=.05):
    """DXF X = radius; DXF Y = axial coordinate (vertical Z in drawing).

    Re-map to internal (axial, radial) representation. The sampled arcs
    remain polylines for conservative machining validation.
    """
    paths=sampled_segments(segments,tolerance)
    converted=[]
    for path in paths:
        for a,b in zip(path,path[1:]):
            if math.dist(a,b)>1e-9:
                converted.append(('line',(a[1],a[0]),(b[1],b[0]),None))
    return profile_from_segments(converted,tolerance)
