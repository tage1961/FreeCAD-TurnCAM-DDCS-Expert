"""SDJCR 1212 + DCMT070204: conservative 2D inspection geometry.

Reference point is a nominal programmed contact point, NOT a calibrated tool
nose centre. Offset points are diagnostic only and never used for CNC output.
"""
import math

TOOL = {'holder':'SDJCR 1212', 'holder_hand':'R', 'shank_mm':[12.0,12.0],
        'insert':'DCMT070204', 'included_angle_deg':55.0,
        'clearance_angle_deg':7.0, 'nominal_nose_radius_mm':0.4,
        'tip_facing':'Z-', 'holder_mounting_verified':False}


def inspect_profile_nose(points, radius=0.4):
    """Calculate signed normal offsets for linear contour segments.

    The outer contour is assumed to be ordered in increasing Z. A right-side
    normal (-dr,dz) is radially outward for increasing Z; its magnitude is r.
    Corners are NOT joined: they need cutter-contact and holder checks.
    """
    if not (math.isfinite(radius) and radius > 0):
        raise ValueError('Insert nose radius must be positive')
    segments=[]
    for (z0,r0),(z1,r1) in zip(points,points[1:]):
        dz=z1-z0; dr=r1-r0; length=math.hypot(dz,dr)
        if length < 1e-8:
            continue
        # Positive radial component of the normal for increasing Z.
        nz=-dr/length; nr=dz/length
        segments.append({'profile_start':[z0,r0], 'profile_end':[z1,r1],
                         'normal_z':nz, 'normal_r':nr,
                         'nose_center_offset_start':[z0+radius*nz,r0+radius*nr],
                         'nose_center_offset_end':[z1+radius*nz,r1+radius*nr],
                         'slope_deg':math.degrees(math.atan2(dr,dz)),
                         'requires_corner_join_review':True})
    return {'reference':'2D segment normal-offset illustration only; NOT a validated cutter-compensated path',
            'nose_radius_mm':radius,'segments':segments,
            'corner_join_implemented':False,'gouge_check_implemented':False,
            'holder_orientation_verified':False,'machine_path_compensated':False}


def shoulder_rapid_review(moves, shoulder_z, stock_radius, nose_radius):
    """Flag radial G0 at the end of a cut adjoining larger stock at Z<shoulder.

    In a conservative circular-nose model, a tip reference at shoulder Z can
    have a disk footprint extending into Z<shoulder. This does not prove a
    collision, but it cannot be certified as free space either.
    """
    out=[]
    for a,b in zip(moves,moves[1:]):
        if b['g']!=0 or abs(a['lathe_z']-b['lathe_z'])>1e-5:
            continue
        if b['machine_y'] <= a['machine_y']+1e-7:
            continue
        if abs(a['lathe_z']-shoulder_z)>1e-3:
            continue
        out.append({'source_line':b['line'], 'z':a['lathe_z'],
                    'radial_start_mm':a['machine_y'], 'radial_end_mm':b['machine_y'],
                    'stock_radius_mm':stock_radius, 'nose_radius_mm':nose_radius,
                    'nose_extends_toward_uncut_stock':True,
                    'status':'BLOCKED_UNVERIFIED_SHOULDER',
                    'reason':'Uncut larger-diameter stock continues toward chuck (Z-); insert nose/holder may overlap shoulder during G0'})
    return out
