# TurnCAM DDCS Expert 1.6.31 — executable DDCS postprocessor

FreeCAD workbench for external turning using DDCS Expert V1.1.

**New:** `POSTPROCESS: Export executable DDCS .nc (UNVERIFIED)` writes actual G00/G01 and conservatively fitted G02/G03 (XY, incremental I/J), G21 G90 G94 G17, and M30. Axis mapping: lathe Z to machine X; lathe diameter/2 to machine Y. No A axis, no spindle commands, no machine Z movements. The existing review and inspection exports remain available.

**Safety:** This export does NOT check collisions or prove machine clearance. Original nine G00 retractions at X=-74.9543 remain unchanged and may collide with continuing Ø20 stock or the tool holder. The user must independently verify the toolpath, setup, work offsets, and machine behavior before running. There is no automatic safe start/park sequence.

Installation: unzip folder `FreeCAD_TurnCAM_DDCS_Expert` into `%APPDATA%\FreeCAD\Mod`, restart FreeCAD and select `TurnCAM DDCS Expert` workbench.

---

# TurnCAM DDCS Expert 1.6.29 — Full G-code risk review

New buttons: **Show FULL G-code + risk on each G00** and **Export full G-code risk listing (.txt, non-executable)**. The complete original motion sequence is displayed as recognizable G00/G01 commands with coordinates and G94 feed values, annotated with source line numbers and prominent warnings on stock-intersecting or boundary-unverified G00 retracts. This diagnostic listing is intentionally not a runnable CNC file. Existing inspection TXT/JSON/CSV, plots, strategy audit, and commented `.nc` review are preserved.

**Risk is not removed.** At the continuing Ø20 stock boundary X=-74.9543, nine rapid retracts remain unverified. No automatic safe exit, 3D insert/holder/chuck/tailstock collision verification, spindle interlock, or executable G-code export is implemented. Do not send the listing to the controller. Machine execution remains blocked even though the full G-code is now visible.

Install by replacing the `FreeCAD_TurnCAM_DDCS_Expert` folder in your FreeCAD Mod directory (back up first), then restart FreeCAD. Syntax and standalone formatter checks were performed; FreeCAD integration and machine behavior were not tested here.

---

# TurnCAM DDCS Expert 1.6.28 - INSPECTION ONLY

Built from the user-supplied 1.6.26 ZIP. The 9 endpoint G00 motions at Z=-74.9543 are intentionally unchanged, and remain BLOCKED/UNVERIFIED. Stock Ø20 continues toward chuck (Z-). No machine-ready output.

New: read-only **Inspection overview** button; TXT export now also writes a CSV with source lines, G0/G1 coordinates, feed and any rapid classification, alongside existing JSON. The `.nc` review remains fully commented and cannot be run. No toolpath or machining strategy changes.

FreeCAD integration not tested in this environment; pure Python module and syntax tests only. Keep a backup of the previous plugin folder.

# TurnCAM DDCS Expert 1.6.25 — INSPECTION ONLY

## New in 1.6.25

At the confirmed 90-degree shoulder Z -74.9543 (Ø12 finished, Ø20 stock continues toward chuck), an inspection-only preview of the user's requested exit is added:

- G1 X-74.9543 Y6.0000 (existing finish endpoint)
- G1 X-72.9543 Y8.0000 (diagonal concept)
- G0 Y12.0000 (same machine X; rapid concept, NOT VERIFIED)

The exact preview is only generated for the Ø12 finishing endpoint. Other roughing endpoints remain unmodified and are explicitly flagged as not applicable to the exact Ø12 sequence. The diagonal may cross remaining stock; the G0 starts inside the Ø20 original stock radius. No verified tool/holder or fixture clearance. Original G0 motions remain unchanged and blocked. The plugin exports ONLY commented inspection TXT and JSON, never machine-ready G-code.

The earlier v1.6.24 functionality remains included. Python syntax and logic were tested outside FreeCAD; UI integration has not been tested on Windows.

# TurnCAM DDCS Expert 1.6.24 — inspection only

## New in 1.6.24

Confirmed scenario: Ø20 stock continues toward chuck beyond left profile endpoint Z−74.9543; finished diameter Ø12.

The new `expert_exit_plan24.py` produces a read-only, per-G00 feasibility report. It explicitly refuses to infer a safe radial exit through continuing stock, records the remaining radial material and lower bound on roughing passes, and lists missing conditions (relief groove, per-pass stock model, tool/holder/fixture geometry). No replacement toolpath is emitted. Original G00 is preserved and machine output remains blocked. The prior v1.6.23 conceptual previews are retained as unverified illustrations.

Install: extract the `FreeCAD_TurnCAM_DDCS_Expert` folder to the same FreeCAD Mod location as the previous version, replacing the old folder after backup; restart FreeCAD. This package has only been Python syntax/logic tested outside FreeCAD.

## v1.6.23 - User-proposed shoulder facing, inspection only

Adds violet 3-segment G1 *concept* at machining boundary, based on Ø20 to Ø12 and Z+ approach/exit. All original moves are unchanged. The proposed 4 mm radial plunge and diagonal exit are NOT collision-checked or machine approved. Tool DCMT070204 / SDJCR 1212 orientation, stock chronology and holder clearance remain unverified. Do not run the preview as CNC code.

## v1.6.22: reverse-path 2D sweep inspection

All blocked continuing-stock radial G00 source lines receive a proposed reverse G01 path and conservative sampled 2D tool-width/nose-radius stock-envelope review. The final-stock estimate is **not chronological** and cannot prove cutting clearance. Every original G00 is preserved, all proposals are non-executable, and machine-ready output remains blocked. FreeCAD physical testing is required.

# v1.6.21 — G1 reverse-cut backtrack inspection previews

**Confirmed:** Ø20 stock continues toward chuck beyond the left profile endpoint Z−74.9543. The 9 original endpoint radial G00 moves remain BLOCKED / UNVERIFIED. A new `expert_backtrack21.py` proposes retracing the immediately preceding contiguous G01 cutting chain in reverse, displayed as cyan dashed segments and recorded in JSON as `backtrack_review_1621`. No replacement G-code is generated. This is NOT an approved exit: reverse-cutting, remaining stock, holder/insert sweep, tailstock and the eventual radial withdrawal at the return point are unverified. Machine output remains disabled. The v1.6.20 magenta stop-short markers are retained separately. Do not run the inspection TXT as CNC code.

# v1.6.20 inspection-only update

Confirmed Ø12 finished shoulder at Z-74.9543; Ø20 stock continues toward chuck. New magenta axial stop-short markers are review-only and **not** replacement paths. The original nine radial G0 moves remain, and machine-ready output remains blocked. Axial reserve estimate = tool review width/2 + insert nose radius + additional review margin. It does not validate insert contact, 12x12 holder clearance, pinol, chuck, or residual stock. A stop-short leaves an unmachined axial band and does not solve the retract.

# TurnCAM DDCS Expert 1.6.19 (En) — inspection only

**IMPORTANT:** This is not machine-ready CNC software. No executable G-code is exported. Original G0 motions are not modified, and no exit is certified safe.

## 1.6.19 — confirmed continuing Ø20 stock toward chuck

- When **Raw stock CONTINUES at stock diameter toward chuck (Z-)** is checked, the left profile endpoint is treated as a machining limit, not a physical end or free space.
- Added `expert_continuation19.py`: an independent conservative guard that identifies endpoint radial G0 retractions against the continuing cylindrical stock envelope. The diameter is taken from the Stock diameter field (Ø20 mm in the supplied test), not hard-coded.
- The guard reports nominal radial overlap and marks each retraction `CONTINUING_STOCK_RETRACT_BLOCKED_UNVERIFIED` in JSON. It does not claim a physical collision; holder and cutting insert swept volumes are not modeled.
- G1-on-the-same-line previews are **suppressed** for these blocked retracts. Changing from G0 to G1 does not establish clearance.
- The inspection plot displays the count of blocked retracts; machine output remains blocked.
- Continuing-stock endpoint must lie inside the declared exposed stock interval; contradictory geometry is rejected.
- The user must redesign the toolpath based on actual stock, contour, tool geometry, fixture and verified clearance. This release does **not** automatically generate a safe alternative.

## Test against supplied v1.6.18 JSON

At Z=-74.9543, stock Ø20, tool review width 2 mm, stock from Z=-150 to 0, the guard flags 9 retracts: source 27, 37, 47, 57, 67, 77, 87, 96, 104. Nominal radius overlaps are 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 3.75, 4.0 mm. These are geometric warning indicators, not measured collisions.

# TurnCAM DDCS Expert 1.6.7 (En) — inspection-only prototype

This is a **separate FreeCAD workbench**, based on the user-supplied TurnCAM 1.5.13 EN sources. Original `FreeCAD_TurnCAM` remains unchanged. This release is **NOT CNC-SAFE** and **DOES NOT EXPORT EXECUTABLE MACHINE CODE**.

## Windows installation
1. Close FreeCAD.
2. Unzip the package. Copy the `FreeCAD_TurnCAM_DDCS_Expert` folder to your FreeCAD user `Mod` folder (typically `%APPDATA%\FreeCAD\Mod`). **Do not overwrite `FreeCAD_TurnCAM`.**
3. Restart FreeCAD. Select `TurnCAM DDCS Expert` workbench.
4. Open a FreeCAD document with a Sketch or import DXF (DXF requires `ezdxf` in FreeCAD's Python environment).
5. Inspect with `Preview inspection`, or export `.txt` and `.json` for review.

## Current functionality
- Sketch/DXF profile extraction inherited from TurnCAM 1.5.13 (separate namespaced module copies).
- Existing external roughing and finishing path generation reused for **inspection only**.
- Tailstock ON: axial machining limit = tailstock tip Z minus axial clearance (defaults -4 - 10 = -14 mm). The profile is **clipped** at the axial boundary. Original Z coordinates remain unchanged; the rightmost portion is left unmachined. Linear segments are interpolated at the boundary; arc-containing profiles with tailstock ON are rejected (fail closed).
- Tailstock OFF: source Sketch remains referenced to Z0.
- DDCS inspection mapping: lathe Z -> mill X, lathe diameter X / 2 -> mill Y. G94 feeds retained in mm/min.
- No A-axis output; no M3/M5/S/T executable output. All inspection moves start with semicolons.
- Facing checkbox independent. With tailstock OFF, source facing is inspected. **With tailstock ON, facing is requested but NOT generated**, explicitly reported as `FACING_NOT_GENERATED` (not silently simulated).
- Source G02/G03 arcs are **not translated** and produce blocking warnings.

## Known limitations
- No machine-ready output; no collision-proofing of holder, chuck, pinol geometry, or remaining stock.
- No verified spindle-ready interlock for separate workpiece motor.
- No proven mapping of G02/G03 arc plane/direction to DDCS Expert.
- Tailstock diameter and axial tip clearance are NOT a complete collision model.
- 2D Qt graphical toolpath inspection added; this is NOT a physical collision simulation.
- Some source profiles may fail original TurnCAM geometry checks.
- RPM is accepted as a reference value for the original generator but not output to the machine.

**Do not remove comment prefixes and run the result on the machine.**

## Changes in 1.6.2
- Fixed the v1.6.0 error that shifted all geometry toward the chuck.
- Tailstock ON: clip original linear contour at the axial limit instead. No repositioning.
- Report includes `original_z_range`, `used_z_range`, and `profile_clipped`.
- Arc metadata with tailstock ON is blocked, not silently linearized.
- The contour's rightmost 14 mm is **not** machined when the tip is at Z-4 and clearance 10 mm.
- Existing 1.5.13 workbench is untouched.

**Important:** This does not verify tool-holder or pinol collision. Radial entry and rapid retract warnings still require engineering review.

## Changes in 1.6.2
- New **Plot toolpaths (2D inspection)** button. Displays stock, chuck-front marker, tailstock tip and axial-limit markers, G1 cutting, G0 rapids, and highlighted rapid-envelope intersections.
- G00 check evaluates the **entire linear segment** against the original stock cylinder, rather than checking only endpoints. This does not model stock already removed, the tool, chuck jaws, or tailstock body.
- `rapid_stock_alerts` and `rapid_check` added to JSON.
- Unsupported G02/G03 now stops export instead of silently skipping motion.
- Existing TurnCAM 1.5.13 is unchanged. Machine output remains blocked.

**Plot caveat:** paths are displayed in radius vs axial coordinates. They do not account for real cutter/holder dimensions. A rapid inside the original stock envelope is flagged even if a previous pass may have removed the material.

## Changes in 1.6.3
- Adds sequential **approximate 2D remaining-stock model** (0.25 mm axial bins, zero-width point tool). This is a diagnostic, NOT validated material simulation. Radial-only G1 plunges cannot certify cleared axial widths.
- Every G00 originally intersecting the stock envelope **remains flagged**, with additional `stock_2d_classification` explaining whether the estimate still detects stock. No collision warning is cleared based on this estimate.
- Green estimated remaining-stock profile added to plot, plus 10 mm Z ticks, radius ticks, zoom buttons and Fit view.
- Output remains commented inspection only. No G02/G03, physical tailstock/chuck/holder collision validation, spindle interlock or executable machine output.
- Older TurnCAM 1.5.13 is NOT modified.


## Version 1.6.5
- Rapid warnings now report direction (radial retract, radial approach, axial or diagonal).
- Select any move in the 2D plot to highlight it and inspect start/end positions and warning classification.
- Original-stock and possible-remaining-stock warnings remain conservative, including radial retracts.
- This remains an inspection-only prototype; no collision approval and no machine-ready G-code.

## Version 1.6.5 changes
- Suppresses zero-length G01 records from the inspection trajectory; original source is not modified. Source line numbers remain traceable.
- Sequential remaining-stock model distinguishes boundary uncertainty from interior possible remaining stock. Neither state is a safety approval.
- Movement selection zooms to local region, highlights stock profile, and reports minimum estimated radial margin.
- Exports removed source lines and rapid classification counts to JSON.
- All output is comments; NOT CNC G-code. Do not run on machinery.

## Changes in 1.6.7
- Selection highlights a movement without automatically zooming; new **Zoom to selected** button and **Fit view**.
- Tailstock ON axial restricted zone shaded in inspection plot (axial tip proxy only).
- G00 diagnostics now include an explicit `reason`, `review_required`, and report-level `rapid_review_count`.
- Sequential 2D point-tool stock estimate retained; it cannot prove endpoint clearance, cutter/holder clearance, or 3D collision safety.
- No automatic G00 rerouting is generated because cutter geometry and physical clearance are unverified. Machine output remains blocked.
- Original TurnCAM 1.5.13 and DDCS V3.3 installation unchanged.

## Changes in 1.6.7
- Responsive fit-to-entire-stock view on dialog opening and resizing; manual zoom stays manual until Fit view.
- Movement selection shows green start marker, purple end marker, direction arrow and explicit coordinates.
- Diagnostic JSON records neighboring stock bins and endpoint uncertainty for each flagged radial rapid.
- No change to executable output: all motion lines are commented inspection data. No physical collision certification.
- Installation: close FreeCAD, back up only the FreeCAD_TurnCAM_DDCS_Expert directory, replace that directory under %APPDATA%\FreeCAD\Mod, restart FreeCAD. Keep the original TurnCAM DDCS V3.3 installation untouched.

## Version 1.6.10
- Adds **Only flagged G0** filter to the inspection movement selector. All original warnings remain present and no G0 is silently removed.
- Selecting a flagged G0 displays the five neighboring stock bins (Z and estimated radius), and magenta endpoint markers on the 2D plot. This highlights the unresolved end-of-cut shoulder.
- Explicit report flags: `endpoint_shoulder_review_count`, `physical_collision_verification: false`, and per-rapid `tool_width_verified: false`, `endpoint_shoulder_verified: false`.
- Resets selection details when filtering. **Fit view** displays the full stock; **Zoom to selected** is optional and no longer forced.
- The negative estimated 2D radial margin is not a measured tool clearance. This release does not automatically reroute G0, and does not provide executable G-code.


## Version 1.6.10 additions
- Axial tool-width input (mm), used ONLY to widen the inspection neighborhood at a rapid endpoint. It does not model a real tool or prove clearance.
- Transparent purple axial-width strip in the 2D plot for selected flagged G0. Not a swept volume.
- Previous/Next flagged G0 buttons for systematic review.
- JSON adds tool_axial_width_mm, axial_width_window_z, neighbor_stock_radius_max_mm and width_window_has_higher_stock.
- Inspection-only export remains fully commented; no executable CNC code.
- This release has not been run inside FreeCAD on the user's machine.


## v1.6.10 - tool footprint review (inspection only)

Added editable tool nose radius (default 0.4 mm) and axial tool width
orientation: center / left / right. Selected flagged G0 shows a 2D
footprint strip and the JSON includes `tool_footprint_review` with an
estimated radial margin against nearby stock bins. Negative margins are
**not proven collisions** and positive margins are **not safe clearance**.
The model omits actual cutter outline, holder, insert orientation, actual
stock, and 3D fixtures. Every G0 warning remains review-required.
No machine-ready G-code is generated. A axis and spindle control remain
absent from the commented inspection output.


## Version 1.6.11 - shoulder review (inspection only)
- New **Shoulder review** button in the 2D inspection plot. Lists radial G0 retracts with source line, axial endpoint, estimated neighboring stock radius and conservative tool-footprint margin.
- Selecting a row shows the review window and three **conceptual** CAM alternatives. None is generated or approved as a CNC path.
- JSON inspection report now contains `shoulder_analysis` with all reviews and explicit `route_generation: false`.
- The existing path generation, axis mapping and machine-output blocking are unchanged.
- These estimates do not verify physical collision clearance.

### Installation
Unzip and copy `FreeCAD_TurnCAM_DDCS_Expert` to the FreeCAD user Mod directory, replacing the prior version after making a backup. Restart FreeCAD. Do not install alongside a second copy of the same workbench.

## Version 1.6.12 — SDJCR 1212 / DCMT070204
- Fixed tool specification: right-hand SDJCR 1212 (12 x 12 mm) with DCMT070204, 55-degree diamond, nominal R0.4 nose, tip facing chuck (Z-). Actual installation and tool offset remain unverified.
- New editable **finished contour end / shoulder Z** (default -74.9543 mm for the supplied example). The material to the left (Z-) remains larger raw stock. Set this field to the actual contour end for each new part.
- New `expert_insert.py` calculates **per-linear-segment nose-center normal-offset preview** in Z/radius coordinates, and records its points in `nose_offset_preview` in JSON. This is a geometric diagnostic, NOT a complete compensated cutting path: intersections, inside corners, arc transitions, contact point calibration, gouging, holder geometry, and 3D collisions remain unresolved.
- New conservative shoulder review flags radial G00 retracts at the specified end position; `insert_shoulder_rapid_checks` in JSON. The original inspection moves are retained unchanged. It does not certify any G00 safe.
- Nose radius is fixed at 0.4 mm for this tool. Tool axial review width is still a user-supplied conservative proxy, NOT a calibrated SDJCR insert/holder swept envelope.
- **No executable G-code.** All exported moves are comments. Do not remove comment prefixes or execute the file. No verified FreeCAD runtime test was performed in this build environment.

## v1.6.13 - inspection-only shoulder exit candidates

- SDJCR 1212 right-hand, DCMT070204 R0.4, tip toward chuck Z-.
- Two editable *proposal* parameters: axial exit Z+ distance (default 1.5 mm) and radial review margin (default 0.5 mm).
- For radial G0 retracts at the shoulder, propose a G1 diagonal Z+/radial-out feed exit followed by a G0 radial retract at the new Z. The proposed route is shown PURPLE DASHED in the 2D inspection plot and included in JSON `candidate_shoulder_exits`.
- Proposed routes are **NOT** substituted into the source moves or exported as executable G-code. Neither actual insert nose contact nor holder swept volume, remaining stock swept volume, cutting suitability, or tailstock clearance are verified. This is a diagnostic geometry hypothesis, not a safe strategy.
- 2D nose normal-offset preview is unchanged and is NOT cutter compensation. The original toolpath remains uncompensated. Machine output remains BLOCKED.


## v1.6.14 — linked shoulder review and purple preview
- The shoulder-review dialog now shows the exact candidate G1/G0 segments corresponding to each source G0 and their candidate issues. Previously the dialog showed only conceptual alternatives even when purple paths were plotted.
- The G0 check count in the button is dynamic. JSON `shoulder_analysis.shoulder_reviews[*].candidate` links to the purple overlay data by `source_line`.
- **No automatic path replacement, no physical collision validation, no machine-ready G-code.** The candidate is a geometric illustration and is not proven to clear remaining stock, tool insert, holder, chuck or tailstock.
- Existing sequential 2D remaining-stock model is only an estimate; this version does not claim it can verify a candidate's swept volume.
- Tested with Python compilation and standalone report review, not inside FreeCAD.


## v1.6.16 — physical end versus shoulder
- New **Left profile endpoint is the PHYSICAL END** checkbox (off by default). Check it only when the leftmost used contour Z is the actual free workpiece end, not a shoulder or an intermediate turning limit.
- When checked, the nine radial retracts at that Z are labeled **END_FACE_UNVERIFIED** rather than shoulder candidates. No misleading Z+ shoulder-exit purple previews are generated. The endface review is inspection-only.
- Exposed stock length and declared physical end are independently compared. A mismatch is reported; **the model is NOT silently altered**. For example, stock front Z0, length 150 gives stock rear Z-150, which conflicts with a declared physical end at Z-74.9543.
- The original source toolpath, all G00s, and fail-closed machine output BLOCKED are preserved. There is NO claim that an endface radial retract is collision-safe. The chuck, insert, holder, tailstock and remaining stock are not physically checked.
- Tested with Python compilation and standalone inspection runs, NOT inside FreeCAD.


## v1.6.16 — guarded physical-end exit previews
- Added a separate **measured FREE SPACE toward Z-** confirmation, OFF by default.
- Physical-end exit previews appear ONLY when physical end is declared, free space is explicitly confirmed, the exposed stock rear matches the profile end within 0.02 mm, and the proposed nominal Z- point is farther than the configured axial chuck gap from chuck face.
- Proposed Z- extension distance = entered axial tool review width + nominal insert nose radius + proposed radial margin. It is a geometric *concept*, NOT a physical swept-volume or holder/insert collision check. The proposed radial G0 remains unverified. No proposed motion is included in the output toolpath.
- With the supplied v1.6.15 example (stock rear Z-150, physical end Z-74.9543), previews are **blocked** by STOCK_REAR_END_MISMATCH even if free space is checked. Do not simply change stock length unless it reflects actual stock geometry.
- Original rapid warnings remain; machine-ready output stays blocked. Pinol/chuck warnings and no spindle/A commands preserved.


## v1.6.17 — raw stock continues toward chuck

- New **Raw stock CONTINUES toward chuck (Z-)** checkbox, enabled by default for the confirmed test geometry. When selected, physical-end and free-space declarations are disabled and contradictory API declarations raise an error.
- Profile left Z (e.g. -74.9543 mm) is the **machining limit**, not the physical workpiece end. Original stock continues toward the chuck; the 2D model still uses declared exposed stock length (e.g. rear -150 mm).
- Radial G0 retracts at the machining limit are explicitly flagged `CONTINUING_STOCK_RETRACT_UNVERIFIED`. No automatic shoulder/endface exit is proposed in this mode. All source motions remain unchanged and machine output is **BLOCKED**.
- Do NOT infer that a G01 axial exit into continuing stock is safe. A safe solution requires actual stock and finished-part geometry, insert/holder envelope, chuck/fixture, and verified motion planning.
- Export TXT and JSON remain **inspection-only**; not machine code.


## v1.6.18 — G1 radial retract review (NOT CNC SAFE)

- The original axial cut to Z=-74.9543 is **already G1**. The following radial withdrawal is G0 in the source.
- Adds read-only `candidate_g1_retracts` proposing **G1 instead of G0** for radial withdrawal at the machining limit. Uses rough/finish G94 feed values (180/100 mm/min with the default inputs).
- Cyan dashed overlay in 2D inspection and per-line details in continuing-stock review.
- Original G0 motions are deliberately preserved; no executable output is created. Switching G0 to G1 only reduces speed and **does not make a stock-intersecting path safe**.
- SDJCR 1212/DCMT070204 R0.4 nose preview, continuing raw stock Z-, pinol axial limit, and blocked machine output remain unchanged.
- No swept-volume, nose-radius toolpath compensation, or holder collision verification.


## v1.6.26 - DDCS G-code review .nc

- Adds **Export G-code REVIEW .nc (NOT executable)** to the FreeCAD panel.
- Emits DDCS-oriented G0/G1, X/Y, and G94 feed blocks in parentheses as comments. No executable motion is present.
- Preserves the Z-74.9543 mm finished contour endpoint with raw Ø20 stock continuing toward Z-.
- Nine radial G0 exits remain unverified and are **not** silently replaced by G1 or diagonal exits.
- Exports a matching JSON inspection report. This is NOT a machine-ready postprocessor.
- Machine release requires verified stock/tool/holder/fixture geometry and safe exit planning.


## v1.6.28: strategy / safety separation

- New read-only **Strategy / safety audit** button groups G1 moves by uniquely matching G94 rough and finish feeds. When feeds match or cannot be identified, the operation is UNCLASSIFIED.
- Flagged G0 retracts are associated with the last cutting stage only for diagnostics. This is not an independent geometric operation identification. Facing remains separately reported but cannot be identified per G1.
- Safety gate remains BLOCKED regardless of stage. No original G0/G1 moves are modified.
- TXT + JSON + CSV export now also writes `_strategy_safety.txt`; JSON contains `strategy_safety_audit_1628`.
- No machine-ready output, no certified tool/holder/tailstock/chuck collision model.

## v1.6.31 arc export
Finishing G01 polyline samples are replaced by G02/G03 only when at least four points fit a circular arc within 0.015 mm, with consistent rotation, <=180 degree sweep, and rounded 3-decimal endpoints/center offsets passing the same tolerance. Roughing G01 moves and G00 retracts are unchanged apart from 3-decimal output. G17 XY plane; I/J offsets are incremental from arc start (verify controller interpretation). F remains mm/min. Arcs are inferred from sampled points, not guaranteed exact CAD arcs. This does not check machine collisions.


## v1.6.32 - UI cleanup
Removed five obsolete read-only inspection/review buttons from the main panel, and hid the two legacy shoulder review fields (left profile end Z and finished shoulder diameter). Their former defaults remain internally for compatibility with inspection calculations. Plot, TXT/JSON/CSV inspection, review NC and G02/G03 3-decimal executable NC export are unchanged.


## 1.6.34: endpoint toggle fixes
- Hidden endpoint Z now follows the loaded sketch/DXF leftmost profile point, rather than a hardcoded Z from another part.
- Non-continuing stock stop-short review now always returns candidate_count=0 (prevents KeyError).
- Measured free-space checkbox is enabled only when physical end is explicitly selected.
- Declaring a physical end does not change stock length: exposed stock rear must still be entered consistently for endface preview.
- Machine post and G02/G03 arc-fitting implementation are unchanged.

Version 1.6.35: Removed inspection/review export buttons; SAVE .nc FILE exports without confirmation prompt. Save-file location dialog remains.
