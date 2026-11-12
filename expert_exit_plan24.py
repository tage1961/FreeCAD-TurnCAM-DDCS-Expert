"""v1.6.24: fail-closed exit feasibility assessment for continuing Ø stock.

Read-only inspection: no generated G-code, no path certification.
Coordinates: lathe Z = mill X; lathe radius = mill Y.
"""
import math


def review(moves, blocked_lines, boundary_z, stock_diameter, finished_diameter,
           rough_radial_doc, finish_radial_doc, tool_width, nose_radius,
           stock_continues_zminus=True):
    vals = (boundary_z, stock_diameter, finished_diameter, rough_radial_doc,
            finish_radial_doc, tool_width, nose_radius)
    if not all(math.isfinite(float(x)) for x in vals):
        raise ValueError('Non-finite exit feasibility parameter')
    if not (stock_diameter > 0 and 0 < finished_diameter <= stock_diameter
            and rough_radial_doc > 0 and finish_radial_doc > 0
            and tool_width > 0 and nose_radius >= 0):
        raise ValueError('Invalid exit feasibility parameter')
    by_line = {m['line']: i for i, m in enumerate(moves)}
    radius_stock = stock_diameter / 2.0
    radius_final = finished_diameter / 2.0
    total_radial = max(0.0, radius_stock-radius_final)
    rough_pass_lower_bound = int(math.ceil(max(0.0, total_radial - 1e-9)/rough_radial_doc))
    entries = []
    for line in sorted(set(blocked_lines)):
        i = by_line.get(line)
        if i is None or i < 1:
            continue
        rapid = moves[i]
        prev = moves[i-1]
        if rapid['g'] != 0 or prev['g'] != 1:
            continue
        z = float(prev['lathe_z'])
        r = float(prev['machine_y'])
        if abs(z-boundary_z) > 0.03:
            continue
        radial_gap = max(0.0, radius_stock-r)
        issues = [
            'CONTINUING_STOCK_Z_MINUS',
            'RADIAL_G0_CROSSES_ORIGINAL_STOCK_ENVELOPE',
            'REMAINING_STOCK_PER_PASS_NOT_VERIFIED',
            'AXIAL_SHOULDER_FACE_NOT_PLANNED',
            'TOOL_HOLDER_TAILSTOCK_CHUCK_NOT_VERIFIED',
            'NO_MEASURED_EXIT_GROOVE_OR_FREE_SPACE',
        ]
        entries.append({
            'source_line':line, 'endpoint_z_mm':z, 'start_radius_mm':r,
            'stock_radius_mm':radius_stock,
            'radial_material_to_stock_surface_mm':round(radial_gap,6),
            'minimum_rough_passes_for_full_diameter_change':rough_pass_lower_bound,
            'max_rough_radial_doc_mm':rough_radial_doc,
            'max_finish_radial_doc_mm':finish_radial_doc,
            'tool_axial_review_width_mm':tool_width,
            'tool_nose_radius_mm':nose_radius,
            'classification':'NO_VERIFIED_EXIT_CONTINUING_STOCK',
            'issues':issues, 'suggested_next_design':
                'Specify measured relief-groove geometry and tool access, or redesign pass/exit strategy; re-check complete stock, tool and fixtures.',
            'candidate_path_generated':False, 'original_g0_unchanged':True,
            'machine_approved':False,
        })
    return {
        'version':'1.6.24',
        'continuing_stock_confirmed':bool(stock_continues_zminus),
        'stock_diameter_mm':stock_diameter,
        'finished_diameter_mm':finished_diameter,
        'total_radial_removal_mm':round(total_radial,6),
        'rough_pass_lower_bound_for_total_radial_removal':rough_pass_lower_bound,
        'blocked_original_g0_count':len(set(blocked_lines)),
        'reviewed_endpoint_count':len(entries),
        'verified_exit_count':0,
        'candidate_path_generated':False,
        'original_g0_unchanged':True,
        'machine_approved':False,
        'required_before_machine_output':[
            'Verified remaining-stock model at every operation',
            'Defined shoulder relief or verified alternative exit geometry',
            'Tool and holder geometry plus cutting direction',
            'Chuck and tailstock clearances including real setup',
            'Independent machine simulation and dry run',
        ],
        'entries':entries,
        'warning':'No safe radial exit can be inferred at the Z- continuing-stock boundary. Inspection only.',
    }
