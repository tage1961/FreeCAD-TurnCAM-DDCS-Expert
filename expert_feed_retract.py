"""v1.6.18 read-only feed-retract proposals; never machine instructions."""
import math

def propose_feed_retracts(moves, machining_limit_z, stock_continues_zminus, feed_mm_min, finish_feed_mm_min, tolerance=0.02):
    """Suggest replacing endpoint G0 radial retract with G1 at controlled feed.

    Changing motion mode does not establish clearance. Do not alter source moves.
    """
    if not all(math.isfinite(float(x)) for x in (machining_limit_z, feed_mm_min, finish_feed_mm_min)):
        raise ValueError('Non-finite feed-retract input')
    if feed_mm_min <= 0 or finish_feed_mm_min <= 0:
        raise ValueError('Feed-retract feed must be positive')
    proposals=[]
    for prev, move in zip(moves,moves[1:]):
        if (move['g']!=0 or abs(prev['lathe_z']-machining_limit_z)>tolerance or
            abs(move['lathe_z']-prev['lathe_z'])>1e-6 or
            move['machine_y']<=prev['machine_y']+1e-7):
            continue
        # Finishing passes are identified by the immediately preceding feed.
        prior_feed=prev.get('feed_mm_min')
        target_feed=finish_feed_mm_min if prior_feed is not None and abs(prior_feed-finish_feed_mm_min)<1e-5 else feed_mm_min
        proposals.append({
            'source_line':move['line'], 'replaces_source_g0_in_preview_only':True,
            'status':'FEED_RETRACT_PREVIEW_UNVERIFIED',
            'candidate_segments':[{'g':'G1','start':[prev['lathe_z'],prev['machine_y']],
                                   'end':[move['lathe_z'],move['machine_y']],
                                   'feed_mm_min':target_feed,
                                   'note':'Radial G1 instead of G0; tool/stock intersection NOT verified'}],
            'candidate_issues':['CONTINUING_STOCK_Z_MINUS' if stock_continues_zminus else 'STOCK_BOUNDARY_UNKNOWN',
                                'NO_INSERT_OR_HOLDER_SWEPT_VOLUME_CHECK',
                                'G1_DOES_NOT_PREVENT_COLLISION'],
            'stock_sweep_verified':False,'holder_sweep_verified':False,'machine_approved':False
        })
    return proposals
