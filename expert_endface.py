"""Review-only, fail-closed physical-end exit geometry (not CNC instructions)."""
import math

def propose_endface_exits(moves, end_z, stock_rear_z, chuck_z, chuck_gap,
                          tool_width_mm, nose_radius_mm, exit_margin_mm,
                          free_space_declared, physical_end_confirmed):
    """Only preview when user declares free space AND geometry is consistent.

    Z- candidate: move axially beyond the declared free end by at least
    entered tool review width + nose radius + clearance. It is not a
    collision-free swept-volume path; tool/holder geometry is unknown.
    """
    issues=[]
    if not physical_end_confirmed: issues.append('PHYSICAL_END_NOT_DECLARED')
    if not free_space_declared: issues.append('FREE_SPACE_NOT_DECLARED')
    if abs(stock_rear_z-end_z)>0.02: issues.append('STOCK_REAR_END_MISMATCH')
    if not all(math.isfinite(v) for v in (end_z,stock_rear_z,chuck_z,chuck_gap,tool_width_mm,nose_radius_mm,exit_margin_mm)):
        issues.append('NONFINITE_PARAMETER')
    if tool_width_mm<=0 or nose_radius_mm<0 or exit_margin_mm<=0:issues.append('INVALID_CLEARANCE')
    if issues:return [],issues
    axial_distance=tool_width_mm+nose_radius_mm+exit_margin_mm
    exit_z=end_z-axial_distance
    # Stop if even the nominal axial point is too close to the chuck.
    if exit_z<=chuck_z+chuck_gap:
        return [],['CHUCK_AXIAL_CLEARANCE_NOT_MET']
    candidates=[]
    for prev,move in zip(moves,moves[1:]):
        if move['g']!=0:continue
        if abs(prev['lathe_z']-end_z)>0.02 or abs(move['lathe_z']-end_z)>0.02:continue
        if move['machine_y']<=prev['machine_y']+1e-7:continue
        radius=prev['machine_y']
        candidates.append({'source_line':move['line'],'status':'GEOMETRY_PREVIEW_UNVERIFIED',
            'candidate_issues':['TOOL_HOLDER_SWEEP_NOT_VERIFIED','ACTUAL_FREE_SPACE_NOT_MEASURED',
                                'CHUCK_FIXTURE_NOT_3D_VERIFIED','NO_MACHINE_APPROVAL'],
            'candidate_segments':[
              {'g':'G1 REVIEW ONLY','start':[end_z,radius],'end':[exit_z,radius],
               'note':'Axial extension toward Z- into user-declared free space; cutting feed not generated'},
              {'g':'G0 REVIEW ONLY','start':[exit_z,radius],'end':[exit_z,move['machine_y']],
               'note':'Radial retract at the proposed free-space point; clearance NOT verified'}],
            'exit_z':exit_z,'axial_distance_mm':axial_distance,
            'original_g0_unchanged':True,'machine_approved':False})
    return candidates,[]
