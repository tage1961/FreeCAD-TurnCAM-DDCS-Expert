"""v1.6.26: DDCS G-code review export. Deliberately NON EXECUTABLE.

The nine radial G0 retracts at the continuing-stock endpoint are unverified.
Never emit live machine moves until an independent safe path is established.
"""
import math


def render_review_nc(report):
    if not report.get('inspection_only') or report.get('machine_code_allowed') is not False:
        raise ValueError('Refusing to export: expected blocked inspection report')
    if report.get('mapping') != {'mill_x':'lathe_z','mill_y':'lathe_diameter/2'}:
        raise ValueError('Unknown axis mapping')
    moves=report.get('moves',[])
    if not moves:
        raise ValueError('No toolpath moves')
    flagged={int(d['line']) for d in report.get('stock_2d',{}).get('rapid_diagnostics',[])
             if d.get('classification') in ('POSSIBLE_REMAINING_STOCK','BOUNDARY_UNVERIFIED')}
    lines=[
        '(DDCS EXPERT 1.6.28 - G-CODE REVIEW ONLY)',
        '(NOT EXECUTABLE - ALL MOTION BLOCKS COMMENTED OUT)',
        '(CONTINUING STOCK Z- AT FINISHED PROFILE END)',
        '(NO MACHINE-READY OUTPUT; VERIFY TOOL HOLDER CHUCK TAILSTOCK AND STOCK)',
        '(LATHE Z TO MILL X; LATHE DIAMETER / 2 TO MILL Y)',
        '(NO A AXIS; NO SPINDLE COMMANDS; G94 MM/MIN)',
        '(MODAL HEADER FOR REVIEW ONLY: G21 G90 G94 G17)',
        '(NO AUTOMATIC SAFE EXIT; BLOCKED G0 RETRACTS REMAIN UNCHANGED)',
    ]
    for move in moves:
        x=float(move['machine_x']); y=float(move['machine_y']); g=int(move['g'])
        if g not in (0,1) or not math.isfinite(x) or not math.isfinite(y):
            raise ValueError('Unsupported or nonfinite move')
        feed=move.get('feed_mm_min')
        block='G%d X%.4f Y%.4f'%(g,x,y)
        if g==1:
            if feed is None or not math.isfinite(float(feed)) or float(feed)<=0:
                raise ValueError('Invalid feed for G1')
            block+=' F%.3f'%float(feed)
        src=int(move['line'])
        label=' UNVERIFIED G00 STOCK-ENVELOPE' if src in flagged else ''
        lines.append('(SOURCE %d%s : %s)'%(src,label,block))
    lines.extend(['(END OF REVIEW - NO M30 OR EXECUTABLE MOVEMENTS)',
                  '(WARNING: DO NOT REMOVE PARENTHESES OR RUN ON CNC)'])
    return '\n'.join(lines)+'\n'
