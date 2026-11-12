"""v1.6.19: inspection-only guard for a Ø-stock continuation at Z-.

A radius-only 2D model cannot certify any retract or tool/holder sweep.
This module never creates a motion and never approves machine output.
"""
import math


def review_continuation(moves, endpoint_z, stock_diameter, tool_width_mm,
                        stock_rear_z, stock_front_z, tolerance=0.02):
    vals=(endpoint_z,stock_diameter,tool_width_mm,stock_rear_z,stock_front_z,tolerance)
    if not all(math.isfinite(float(v)) for v in vals):
        raise ValueError('Non-finite continuing-stock review input')
    if stock_diameter<=0 or tool_width_mm<=0 or stock_rear_z>=stock_front_z or tolerance<=0:
        raise ValueError('Invalid continuing-stock review dimensions')
    if not stock_rear_z+tolerance<endpoint_z<stock_front_z-tolerance:
        raise ValueError('Continuing-stock machining endpoint must lie within exposed stock')
    rows=[]
    for prev,cur in zip(moves,moves[1:]):
        if (cur['g']!=0 or abs(prev['lathe_z']-endpoint_z)>tolerance or
            abs(cur['lathe_z']-endpoint_z)>tolerance or
            cur['machine_y']<=prev['machine_y']+1e-7):
            continue
        r0=prev['machine_y']; r1=cur['machine_y']; stock_r=stock_diameter/2
        rows.append({
            'source_line':cur['line'], 'endpoint_z_mm':endpoint_z,
            'stock_diameter_mm':stock_diameter, 'continuing_stock_radius_mm':stock_r,
            'retract_start_radius_mm':r0, 'retract_end_radius_mm':r1,
            'start_below_continuation_radius':r0<stock_r,
            'nominal_radial_overlap_mm':max(0.0,stock_r-r0),
            'review_width_mm':tool_width_mm,
            'axial_footprint_crosses_continuation_boundary':True,
            'classification':'CONTINUING_STOCK_RETRACT_BLOCKED_UNVERIFIED',
            'g0_approved':False,'g1_substitution_approved':False,
            'safe_exit_computed':False,'machine_approved':False,
            'reason':'At machining endpoint, uncut Ø stock continues Z-. The finite-width tool footprint may overlap this stock. Neither G0 nor same-line G1 is approved.',
            'required_next_step':'CAM toolpath redesign using measured part, tool/holder geometry and verified remaining stock; independent simulation and machine checks required'
        })
    return {'model':'Declared continuing cylinder, conservative 2D endpoint guard',
            'stock_continuation_confirmed':True,'continuing_stock_diameter_mm':stock_diameter,
            'machining_limit_z_mm':endpoint_z,'blocked_retract_count':len(rows),
            'blocked_retracts':rows,'automatic_exit_available':False,
            'collision_verified':False,'machine_output_allowed':False}
