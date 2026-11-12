"""v1.6.28: read-only inspection overview and CSV, no path modifications."""
import csv
import io

BLOCKED = 'NOT CNC SAFE - MACHINE OUTPUT BLOCKED'

def summarize(report):
    if report.get('inspection_only') is not True or report.get('machine_code_allowed') is not False:
        raise ValueError('A blocked inspection report is required')
    moves = report.get('moves', [])
    alerts = report.get('alerts', [])
    diagnostics = report.get('stock_2d', {}).get('rapid_diagnostics', [])
    flagged = [d for d in diagnostics if d.get('classification') in
               ('POSSIBLE_REMAINING_STOCK', 'BOUNDARY_UNVERIFIED')]
    return {
        'version': '1.6.28', 'status': BLOCKED,
        'moves': len(moves), 'alerts': len(alerts),
        'flagged_rapids': len(flagged),
        'flagged_source_lines': sorted(set(int(d['line']) for d in flagged)),
        'stock_continues_zminus': bool(report.get('stock_continues_zminus')),
        'profile_end_z': report.get('shoulder_z'),
        'tailstock': report.get('tailstock'),
        'tool': 'SDJCR 1212 / DCMT070204 R0.4',
        'mapping': 'Lathe Z -> machine X; diameter / 2 -> machine Y',
        'physical_collision_verified': False,
        'original_moves_modified': False,
    }

def overview_text(report):
    s = summarize(report)
    lines = [
        'TURN CAM DDCS EXPERT 1.6.28 - INSPECTION OVERVIEW',
        s['status'],
        'Moves: %d | Alerts: %d | Flagged G00: %d' % (s['moves'],s['alerts'],s['flagged_rapids']),
        'Flagged source lines: ' + (', '.join(map(str,s['flagged_source_lines'])) or 'none'),
        'Left profile end Z: %s mm' % s['profile_end_z'],
        'Stock continues toward chuck Z-: %s' % ('YES' if s['stock_continues_zminus'] else 'NOT CONFIRMED'),
        'Tailstock: %s' % s['tailstock'],
        'Tool: %s' % s['tool'],
        s['mapping'],
        'Original motions unchanged. 2D review does not certify tool/holder/stock clearance.',
        'No executable machine code is produced.',
    ]
    return '\n'.join(lines) + '\n'

def diagnostics_csv(report):
    summarize(report)
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['source_line','motion_type','classification','machine_x_mm','machine_y_mm','feed_mm_min','warning'])
    diag_by_line = {}
    for d in report.get('stock_2d', {}).get('rapid_diagnostics', []):
        diag_by_line[int(d['line'])] = d
    for m in report.get('moves', []):
        line = int(m['line']); d = diag_by_line.get(line, {})
        writer.writerow([line,'G%d' % int(m['g']),d.get('classification',''),
                         '%.4f' % float(m['machine_x']), '%.4f' % float(m['machine_y']),
                         '' if m.get('feed_mm_min') is None else '%.3f' % float(m['feed_mm_min']),
                         'REVIEW REQUIRED' if d.get('classification') in ('POSSIBLE_REMAINING_STOCK','BOUNDARY_UNVERIFIED') else ''])
    return output.getvalue()
