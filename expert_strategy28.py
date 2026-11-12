"""v1.6.28 read-only separation of process stages and independent safety gate.

No motion generation, approval, or machine export is implemented here.
"""
import json

BLOCKING = ('POSSIBLE_REMAINING_STOCK', 'BOUNDARY_UNVERIFIED')


def strategy_audit(report, rough_feed, finish_feed):
    if report.get('inspection_only') is not True or report.get('machine_code_allowed') is not False:
        raise ValueError('Strategy audit requires a blocked inspection report')
    moves = report.get('moves', [])
    diagnostics = report.get('stock_2d', {}).get('rapid_diagnostics', [])
    flagged = {int(d['line']): d for d in diagnostics if d.get('classification') in BLOCKING}
    # Classification is based on a G1 feed matching a unique user-selected feed.
    # Identical feeds, or unmatched feeds, must remain UNCLASSIFIED.
    def feed_stage(feed):
        if feed is None:
            return 'UNCLASSIFIED'
        r = abs(float(feed) - float(rough_feed)) < 0.0005
        f = abs(float(feed) - float(finish_feed)) < 0.0005
        return 'ROUGHING' if r and not f else ('FINISHING' if f and not r else 'UNCLASSIFIED')
    stages = {k: {'cut_moves': 0, 'blocked_retracts': [], 'source_lines': []}
              for k in ('ROUGHING', 'FINISHING', 'UNCLASSIFIED')}
    last_cut_stage = 'UNCLASSIFIED'
    for m in moves:
        line = int(m['line'])
        if int(m['g']) == 1:
            stage = feed_stage(m.get('feed_mm_min'))
            last_cut_stage = stage
            stages[stage]['cut_moves'] += 1
            stages[stage]['source_lines'].append(line)
        elif int(m['g']) == 0 and line in flagged:
            stages[last_cut_stage]['blocked_retracts'].append(line)
    facing = {
        'requested': bool(report.get('facing_requested')),
        'reported_generated': bool(report.get('facing_generated')),
        'pending': bool(report.get('facing_pending')),
        'independent_motion_classification_verified': False,
        'status': 'PENDING_OR_DISABLED' if not report.get('facing_generated') else 'GENERATED_NOT_INDEPENDENTLY_VERIFIED',
    }
    blocked = sorted(flagged)
    return {
        'version': '1.6.28',
        'purpose': 'Read-only separation of machining strategy from safety inspection',
        'inspection_only': True,
        'machine_code_allowed': False,
        'strategy': {'facing': facing, 'stages': stages,
                     'classification_method': 'G1 feed comparison; G0 assigned to immediately preceding cutting stage',
                     'classification_limit': 'Same or unknown feeds produce UNCLASSIFIED; no facing-specific G1 identification'},
        'safety_gate': {'status': 'BLOCKED', 'flagged_g0_count': len(blocked),
                        'flagged_source_lines': blocked,
                        'original_moves_unchanged': True,
                        'verified_exit_paths': 0,
                        'collision_verified': False,
                        'note': 'Stage grouping never overrides the original inspection safety gate'},
    }


def audit_text(audit):
    s = audit['strategy']['stages']
    lines = ['DDCS EXPERT 1.6.28 - STRATEGY / SAFETY SEPARATION',
             'INSPECTION ONLY - NOT CNC SAFE - MACHINE OUTPUT BLOCKED',
             'Facing: ' + audit['strategy']['facing']['status']]
    for name in ('ROUGHING', 'FINISHING', 'UNCLASSIFIED'):
        part = s[name]
        lines.append('%s: %d G1 cut moves; %d flagged G0 after stage; lines %s' %
                     (name, part['cut_moves'], len(part['blocked_retracts']),
                      ', '.join(map(str, part['blocked_retracts'])) or 'none'))
    lines += ['Safety gate: BLOCKED; flagged G0: %d' % audit['safety_gate']['flagged_g0_count'],
              'No G0 replaced, no automatic G1 exit, no 3D/tool-holder verification.',
              'Feed-based grouping is diagnostic, NOT proof of machining operation.',
              'No executable G-code generated.']
    return '\n'.join(lines) + '\n'
