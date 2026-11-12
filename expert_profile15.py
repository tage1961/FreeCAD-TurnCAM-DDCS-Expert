"""Extract a single exterior turning path from open/closed XZ Sketch edges.
Coordinates of input paths: (radius X, axial Z). No FreeCAD dependency.
"""
import math

class ProfileError(ValueError): pass

def extract_outer(paths, eps=0.025):
    edges=[]; nodes=[]
    def node(p):
        for i,q in enumerate(nodes):
            if math.dist(p,q)<=eps:return i
        nodes.append(tuple(p));return len(nodes)-1
    for path in paths:
        if len(path)<2:continue
        a=node(path[0]);b=node(path[-1])
        if a==b:raise ProfileError('Closeket enkeltkant/cirkel kan ikke anvendes som udvendig profil.')
        if any({a,b}=={e[0],e[1]} for e in edges):continue
        edges.append((a,b,path))
    if not edges:raise ProfileError('Ingen brugbare kanter.')
    # Remove center-axis closing edges, but retain radial end walls.
    axis=[e for e in edges if all(abs(p[0])<=eps for p in e[2])]
    if axis:
        edges=[e for e in edges if e not in axis]
    adjacency={}
    for idx,(a,b,_) in enumerate(edges):
        adjacency.setdefault(a,[]).append(idx);adjacency.setdefault(b,[]).append(idx)
    ends=[v for v,adj in adjacency.items() if len(adj)==1]
    if len(ends)!=2 or any(len(adj)>2 for adj in adjacency.values()):
        raise ProfileError('Cannot identify a unique external chain; check for branches or extra construction geometry.')
    start=min(ends,key=lambda n:nodes[n][1]);cur=start;used=set();chain=[]
    while True:
        opts=[i for i in adjacency[cur] if i not in used]
        if not opts:break
        i=opts[0];used.add(i);a,b,path=edges[i]
        if cur==b:path=list(reversed(path));cur=a
        else:cur=b
        chain.extend(path if not chain else path[1:])
    if len(used)!=len(edges):raise ProfileError('Multiple disconnected contours; select one Sketch with one profile.')
    if max(x for x,z in chain)<=eps:raise ProfileError('Ingen udvendig radius fundet.')
    if min(x for x,z in chain)<-eps:raise ProfileError('Profilen krydser centeraksen X=0.')
    if chain[0][1]>chain[-1][1]:chain.reverse()
    for (x0,z0),(x1,z1) in zip(chain,chain[1:]):
        if z1<z0-eps:raise ProfileError('External contour reverses in Z; a separate strategy is required.')
    zref=max(z for x,z in chain)
    pts=[(round(z-zref,6),round(max(0.,x),6)) for x,z in chain]
    if pts[-1][0]-pts[0][0]<eps:raise ProfileError('Profile has no Z length.')
    # The input is often a closed solid cross-section. The axial closing
    # edge is removed above; trim only the two radial END FACES, never
    # intermediate shoulders. Toolpaths must not follow the center axis.
    lo,hi=pts[0][0],pts[-1][0]
    a=0
    while a+1<len(pts) and abs(pts[a+1][0]-lo)<=eps:a+=1
    b=len(pts)-1
    while b-1>=0 and abs(pts[b-1][0]-hi)<=eps:b-=1
    # At each end face choose the OUTERMOST radius, then keep the exterior.
    left=max(range(a+1),key=lambda k:pts[k][1])
    right=max(range(b,len(pts)),key=lambda k:pts[k][1])
    pts=pts[left:right+1]
    if len(pts)<2 or pts[0][1]<=eps or pts[-1][1]<=eps:
        raise ProfileError('Kan ikke isolere udvendig profil fra endeflader.')
    if any(pts[i+1][0]<pts[i][0]-eps for i in range(len(pts)-1)):
        raise ProfileError('Udvendig profil har Z-tilbagegang.')
    return pts
