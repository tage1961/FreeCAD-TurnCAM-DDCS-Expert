"""Read sketch edges directly from FreeCAD, or inspect DXF geometry without inventing arcs."""
import math

def sketch_paths(obj, step=0.10):
    if obj is None or not obj.isDerivedFrom('Sketcher::SketchObject'):
        raise ValueError('Select a Sketch in the model tree (or select one from the list).')
    # Sketch.Shape contains FreeCAD's actual topological edges, unlike DXF exports
    # which may contain circles used as construction geometry.
    edges=obj.Shape.Edges
    if not edges:raise ValueError('Sketch indeholder ingen synlige kanter.')
    paths=[]
    for edge in edges:
        pts=edge.discretize(Deflection=step)
        if len(pts)<2:continue
        paths.append([(float(p.x),float(p.z)) for p in pts])
    return paths

def dxf_paths(path):
    # Prefer ezdxf when installed in FreeCAD's Python environment.
    try:
        import ezdxf
    except ImportError:
        raise ValueError('DXF import requires ezdxf in the FreeCAD Python environment. Use direct Sketch import or install ezdxf in FreeCAD Python.')
    doc=ezdxf.readfile(path)
    paths=[];warnings=[];kinds={}
    for e in doc.modelspace():
        kind=e.dxftype();kinds[kind]=kinds.get(kind,0)+1
        if kind=='LINE':
            a=e.dxf.start;b=e.dxf.end
            paths.append([(a.x,a.z),(b.x,b.z)])
        elif kind=='ARC':
            a=float(e.dxf.start_angle);b=float(e.dxf.end_angle)
            if abs((b-a)%360)<1e-7:
                warnings.append('ARC med ens start/slutvinkel: ikke rekonstrueret')
                continue
            # DXF ARC is OCS; use its OCS transformation, not XY assumptions.
            span=(b-a)%360
            coords=[]
            for i in range(max(12,math.ceil(span/3))+1):
                angle=math.radians(a+span*i/max(12,math.ceil(span/3)))
                c=e.dxf.center;r=e.dxf.radius
                p=e.ocs().to_wcs((c.x+r*math.cos(angle),c.y+r*math.sin(angle),c.z))
                coords.append((p.x,p.z))
            paths.append(coords)
        elif kind=='CIRCLE':
            # Construction circles in FreeCAD exports must not be mistaken for profile arcs.
            warnings.append('CIRCLE omitted: may be construction geometry')
        elif kind in ('LWPOLYLINE','POLYLINE'):
            try:
                pts=list(e.get_points()) if kind=='LWPOLYLINE' else [v.dxf.location for v in e.vertices]
                if kind=='LWPOLYLINE':
                    if any(len(p)>4 and abs(p[4])>1e-9 for p in pts):
                        warnings.append('Polyline with bulge requires separate arc interpretation');continue
                    paths.append([(float(p[0]),float(e.dxf.elevation if isinstance(e.dxf.elevation,(int,float)) else 0)) for p in pts])
                else:paths.append([(float(p.x),float(p.z)) for p in pts])
            except Exception as exc:warnings.append('Polyline ikke vist: '+str(exc))
        else:warnings.append('Ikke vist: '+kind)
    if not paths:raise ValueError('No unambiguous profile entities found. Select the original Sketch instead.')
    return paths,warnings,kinds

def segments_from_paths(paths):
    return [('line',(a[1],a[0]),(b[1],b[0]),None) for p in paths for a,b in zip(p,p[1:]) if math.dist(a,b)>1e-7]


def sketch_arc_candidates(obj, paths):
    """Return sampled Sketch circle arcs with centers in internal (Z, radius) coordinates.

    These are only candidates: post-processing matches all points against the
    validated contour before emitting G2/G3.
    """
    out=[]
    for edge,path in zip(obj.Shape.Edges,paths):
        curve=edge.Curve
        if type(curve).__name__ not in ('Circle','ArcOfCircle'):
            continue
        try:
            c=curve.Center
            if abs(float(c.y))>0.02:continue
            r=float(curve.Radius)
            if r<=0 or len(path)<3:continue
            if abs((edge.Length/r)-2*math.pi)<0.01:continue
            out.append((path,(float(c.z),float(c.x))))
        except (AttributeError,TypeError,ValueError):continue
    return out
