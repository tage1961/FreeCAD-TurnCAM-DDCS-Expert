"""v1.6.29: complete, numbered G-code syntax for visual review, NOT an NC program.

All original moves are preserved. Source-number prefixes and warning annotations
intentionally make this listing unsuitable for direct CNC execution.
"""
import math

BLOCKING = ('POSSIBLE_REMAINING_STOCK', 'BOUNDARY_UNVERIFIED')


def render_full_review(report):
    if report.get('inspection_only') is not True or report.get('machine_code_allowed') is not False:
        raise ValueError('Expected inspection-only report; refusing to mislabel machine output')
    if report.get('mapping') != {'mill_x': 'lathe_z', 'mill_y': 'lathe_diameter/2'}:
        raise ValueError('Unexpected machine axis mapping')
    moves = report.get('moves', [])
    if not moves:
        raise ValueError('No G-code moves to display')
    diagnostics = report.get('stock_2d', {}).get('rapid_diagnostics', [])
    flagged = {int(d['line']): d for d in diagnostics if d.get('classification') in BLOCKING}
    continuing = {int(d['source_line']) for d in report.get('continuation_retract_checks', [])}
    # The continuation guard is independent of the 2D classification.
    for m in moves:
        if int(m['g']) == 0 and report.get('stock_continues_zminus'):
            if abs(float(m['machine_x']) - float(report.get('shoulder_z', float('inf')))) < 0.02:
                if int(m['line']) in flagged:
                    continuing.add(int(m['line']))
    header = [
        'DDCS EXPERT 1.6.29 - COMPLETE G-CODE LISTING FOR RISK REVIEW',
        'NOT MACHINE-READY. THIS IS A NUMBERED DIAGNOSTIC LISTING, NOT A CNC FILE.',
        'Original toolpath is unchanged; no exit paths are verified.',
        'Axes: lathe Z -> machine X; lathe diameter / 2 -> machine Y.',
        'G21 G90 G94 are ASSUMED for interpreting coordinates and feeds; not a validated setup.',
        'No spindle/A-axis commands; no startup, homing, interlocks, or safe parking.',
        'WARNING: flagged G00 retracts may intersect continuing stock and/or tool holder.',
        'Source line | G-code command | Risk annotation',
        '-' * 94,
    ]
    for m in moves:
        g = int(m['g']); x = float(m['machine_x']); y = float(m['machine_y'])
        if g not in (0, 1) or not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError('Unsupported/nonfinite motion')
        command = 'G%02d X%.4f Y%.4f' % (g, x, y)
        if g == 1:
            feed = m.get('feed_mm_min')
            if feed is None or not math.isfinite(float(feed)) or float(feed) <= 0:
                raise ValueError('Invalid G01 feed')
            command += ' F%.3f' % float(feed)
        src = int(m['line'])
        note = ''
        if src in flagged or src in continuing:
            note = '  <<< DANGER / UNVERIFIED G00: possible remaining stock; DO NOT RUN'
        header.append('SOURCE %3d | %-34s%s' % (src, command, note))
    header.extend([
        '-' * 94,
        'FLAGGED G00: %d. Verified safe exits: 0.' % len(set(flagged) | continuing),
        'A 2D model cannot prove clearance for insert, holder, chuck, or tailstock.',
        'No executable .nc file is generated. This listing is for identifying and fixing risk.',
    ])
    return '\n'.join(header) + '\n'
