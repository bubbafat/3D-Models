#
# Run in Autodesk Fusion
# 1. Create a new part (empty)
# 2. Click on Utilities -> Add-ins -> Scripts and Add-ins    (Shift+S)
# 3. "+" -> Create Scripts or Add-in
# 4. Create new (name it, choose Python)
# 5. Save and then find it in the list to open the containing folder
# 6. Edit the pre-generated python file - replace with this file
# 7. Save python file and click the "Run" button in Fusion
# 8. wait ... it can take 30-90 seconds
#
# Monorail countdown, version 2: rebuilt toward the concept image -- a bullet
# nose with a wrap-around windshield, a black window band with raised black
# frames round the cubes, a red stripe that sweeps up at the tail, a narrow
# full-width lower body that straddles a straight concrete beam on two pylons, as the real Mark VI does, pinned
# and glued to the beam, and the spare cube stowed in the tail.
#
# Fourteen printable bodies:
#
#   Car_Bottom    the white belly, up to the red stripe -- print belly down
#   Car_Red_Display, Car_Red_Back
#                 the red stripe, cut down the middle -- print on the cut face
#   Car_Top       white, black band, white roof, with the cube slots -- print
#                 standing on its flat bottom
#   Pin_1..4      loose pins locating the top on the red -- print on end
#   Beam          the beam and its two pylons, one piece -- print on its side
#   Foot          the plate the pylons plug into -- print flat
#   Cube_1..3     the three countdown cubes
#   Cube_4_Spare  the fourth, stowed in a pocket in the car's tail face
#
# The cubes are the ship's cubes, unchanged -- same 20 mm size, same four-way
# digit assignment, so one set of four works in either model.
#
# COLOURS (every boundary below is a real geometric step for the fill tool).
# The car takes exactly the four AMS slots; the beam and foot print on their
# own plate in the fifth:
#
#   white       the car body
#   black       window band, cube frames, tail coupler, and the windshield --
#               recessed a step deeper than the band, so it still reads as glass
#   red         stripe and the two tail lights
#   gold        lettering
#   grey        beam and foot
#
# PRINT ORIENTATION, and why the car is cut along its colour lines:
#
#   Printed in one piece, or in halves, the car put several colours in nearly
#   every layer, and the colour changes cost more time and filament than the
#   car itself. So it is cut where the colours meet, like the ship's hull and
#   superstructure, and each part prints in one colour or close to it, in
#   batches:
#
#   - The bottom is all white and prints belly down. The beam channel is a
#     bridge; the nose's underside and the belly's rounded edges need support.
#     Its top carries a 0.4 mm recess, as the ship's deck does, that both red
#     halves seat in.
#   - The red stripe is cut down the middle and each half lies on its cut
#     face, so the gold lettering is only the last few layers. Over the spare
#     pocket the tail end needs support.
#   - The top prints standing on its flat bottom: the black band and frames are
#     upright walls, and the cube slots and the pocket's roof are bridges. Four
#     loose pins locate it on the red halves.
#
#   Set SPLIT_CAR = False below to get one body instead.
#

import adsk.core, adsk.fusion, adsk.cam, math, os, time, traceback
from itertools import permutations


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('No active Fusion design. Start a new design first, then run this script.')
            return

        root = design.rootComponent
        userParams = design.userParameters

        # The 3MF exporter follows the document's units. Left on cm or inch it
        # writes a file the slicer reads at the wrong scale.
        design.fusionUnitsManager.distanceDisplayUnits = \
            adsk.fusion.DistanceUnits.MillimeterDistanceUnits

        def require(condition, message):
            if not condition:
                raise RuntimeError(message)

        def drop(entity, what):
            """deleteMe() returns False rather than raising when Fusion declines.
            Unchecked, scratch geometry silently survives into the export.

            Only ever handed a FEATURE or a sketch. On a body still referenced by
            an earlier combine it returns True and removes nothing, which is how
            the livery tools once survived -- so tools are consumed by a combine
            instead of deleted."""
            require(entity.deleteMe(),
                    'Fusion would not delete {} -- it would have been left in the '
                    'model and exported as a stray part.'.format(what))

        def mm(v):
            """Fusion's internal unit is cm; every number in this script is mm."""
            return v / 10.0

        def P(x, y):
            return adsk.core.Point3D.create(mm(x), mm(y), 0)

        # ---------------------------------------------------------------- cleanup
        for s in list(root.sketches):
            if s.name.startswith(('Car_', 'Beam_', 'Base_', 'Cut_', 'Cube_', 'Text_',
                                  'Tool_', 'Probe_', 'Pin_')):
                s.deleteMe()
        for b in list(root.bRepBodies):
            if b.name.startswith(('Car', 'Beam', 'Base', 'Foot', 'Cube', 'Tool', 'Inner',
                                  'Probe', 'Pin')):
                b.deleteMe()
        for p in list(root.constructionPlanes):
            if p.name.startswith(('Deck_P', 'Cut_P', 'Car_P', 'Tool_P', 'Base_P')):
                p.deleteMe()

        def set_param(name, expr, units, comment=''):
            existing = userParams.itemByName(name)
            if existing:
                # deleteMe() returns False rather than raising when another
                # parameter's expression still references this one.
                if not existing.deleteMe():
                    try:
                        existing.unit = units
                    except:
                        pass
                    existing.expression = expr
                    if comment:
                        existing.comment = comment
                    return existing
            return userParams.add(name, adsk.core.ValueInput.createByString(expr), units, comment)

        extrudes = root.features.extrudeFeatures
        lofts = root.features.loftFeatures
        combines = root.features.combineFeatures
        moves = root.features.moveFeatures

        # ------------------------------------------------ symmetric-extrude probe
        # setDistanceExtent(True, d) may apply d per side or as the total, and
        # getting it wrong doubles every symmetric cut in this file. Measure it
        # rather than assume.
        probeSk = root.sketches.add(root.xYConstructionPlane)
        probeSk.name = 'Probe_Symmetric'
        probeLines = probeSk.sketchCurves.sketchLines
        pp = probeSk.sketchPoints
        pa = pp.add(P(300.0, 0.0))
        pb = pp.add(P(302.0, 0.0))
        pc = pp.add(P(302.0, 2.0))
        pd = pp.add(P(300.0, 2.0))
        probeLines.addByTwoPoints(pa, pb)
        probeLines.addByTwoPoints(pb, pc)
        probeLines.addByTwoPoints(pc, pd)
        probeLines.addByTwoPoints(pd, pa)
        require(probeSk.profiles.count == 1, 'Symmetric-extrude probe sketch did not close.')
        probeIn = extrudes.createInput(probeSk.profiles.item(0),
                                       adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        probeIn.setDistanceExtent(True, adsk.core.ValueInput.createByString('10 mm'))
        probeBody = extrudes.add(probeIn).bodies.item(0)
        probeBody.name = 'Probe_Body'
        probeSpan = (probeBody.boundingBox.maxPoint.z - probeBody.boundingBox.minPoint.z) * 10.0
        SYMMETRIC_PER_SIDE = probeSpan > 15.0
        drop(probeBody, 'the symmetric-extrude probe body')
        drop(probeSk, 'the symmetric-extrude probe sketch')

        def symmetric_value(totalDepth):
            """What to hand setDistanceExtent so the cut is totalDepth overall."""
            return totalDepth / 2.0 if SYMMETRIC_PER_SIDE else totalDepth

        # ============================================================ parameters
        SPLIT_CAR = True              # see the note at the top of the file
        PREVIEW_COLOURS = True        # paint the model in Fusion the way it prints

        set_param('totalLength', '177 mm', 'mm', 'Overall footprint -- the car plus its tail coupler')
        set_param('totalHeight', '76 mm', 'mm', 'Desk to roof')
        set_param('carLength', '174 mm', 'mm', 'Car nose to tail face')
        set_param('carWidth', '42 mm', 'mm', 'Car width across the flanks')
        set_param('carHeight', '51 mm', 'mm', 'Belly to roof crown')
        set_param('roofRadius', '10 mm', 'mm', 'Cross-section round at the roof')
        set_param('bellyRadius', '6 mm', 'mm', 'Cross-section round where the body turns under')
        set_param('noseLength', '48 mm', 'mm', 'How far back the bullet nose starts')
        set_param('beamWidth', '10 mm', 'mm', 'Track beam width -- real Mark VI proportion to the car')
        set_param('beamDepth', '15 mm', 'mm', 'Track beam depth -- about 10 mm of it shows below the car')
        set_param('beamLength', '168 mm', 'mm', 'Track beam length')
        set_param('beamFit', '0.8 mm', 'mm', 'Slack across the belly channel over the beam, total')
        set_param('footSize', '130 mm', 'mm', 'Length of the plate the two pylons plug into')
        set_param('cubeSize', '20 mm', 'mm', 'Countdown cube edge length')
        set_param('cubeCount', '3', '', 'Number of cubes displayed at once')
        set_param('cubeClearance', '0.6 mm', 'mm', 'Slack so a cube slides in and out freely')
        set_param('slotDepth', '16 mm', 'mm', 'Display slot depth from the frame face -- cube stands cubeSize minus this proud')
        set_param('frameProud', '1.5 mm', 'mm', 'How far the black cube frames stand off the flank')
        set_param('cubeEdgeFillet', '1 mm', 'mm', 'Cube edge break')
        set_param('spareClearance', '1.7 mm', 'mm', 'Spare pocket slack, total across the cube')
        set_param('stripeDepth', '0.8 mm', 'mm', 'Red stripe recess -- 2 walls at 0.42')
        set_param('bandDepth', '0.6 mm', 'mm', 'Black window band recess')
        set_param('glassDepth', '1.2 mm', 'mm', 'Windshield glass recess, a further step inside the band')
        set_param('digitRecessDepth', '0.84 mm', 'mm', 'Engraved digit depth -- 2 walls at 0.42')
        set_param('digitInkHeight', '11 mm', 'mm', 'Height of the digit you actually see -- calibrated per font')
        set_param('textRise', '1.2 mm', 'mm', 'How far the lettering stands off the stripe floor')
        set_param('pinDiameter', '4 mm', 'mm', 'Pin locating the car top on the red stripe')
        set_param('seatDepth', '0.4 mm', 'mm', 'Recess in the car bottom that the red stripe seats in')
        set_param('seatGap', '0.1 mm', 'mm', 'Clearance per side round the red stripe in its recess')
        set_param('pinFit', '0.4 mm', 'mm', 'Socket oversize on the pin, total')
        set_param('mickeyHeadDia', '6 mm', 'mm', 'Mickey head diameter, reference size')
        set_param('mickeyEarDia', '3.4 mm', 'mm', 'Mickey ear diameter')
        set_param('cubeMarkScale', '0.45', '', 'Mickey emblem size on a cube, relative to reference')

        # ------------------------------------------------- numeric seeds (all mm)
        # Proportions come from the concept image, scaled so its cubes are the
        # real 20 mm cubes. The width is not visible there; 42 mm is what a
        # 16 mm slot plus a frame and a back wall need in each half.
        carLen, carHalfW = 174.0, 21.0
        carX0, carX1 = -carLen / 2.0, carLen / 2.0
        # The lower body is full width right down to the beam, as on the real
        # Mark VI -- not stepped in to a narrow skirt, which made the car look
        # perched on a pedestal.
        bodyZ0, bodyZ1 = 0.0, 51.0    # belly, roof crown
        bodyRBot, bodyRTop = 6.0, 10.0
        minRound = 0.6                # floor on any corner round after insetting

        noseLen = 48.0
        noseStartX = carX1 - noseLen
        noseTipHalfW, noseTipZ0, noseTipZ1 = 5.0, 12.5, 22.5
        noseTipRBot, noseTipRTop = 2.5, 3.5
        nosePower = 2.2               # the side view's taper: >1 meets the body
                                      # tangentially; the higher, the blunter the bullet
        noseWidthPower = 1.4          # the width's taper. Lying on the split face,
                                      # the width is each half's print height, and
                                      # at 2.2 the nose left the flank so slowly
                                      # that its first layers stepped 5-7 mm wide
        NOSE_T = (0.0, 0.1, 0.2, 0.3, 0.55, 0.75, 0.9, 1.0)

        tailLen, tailRound = 5.0, 2.5  # the tail face is flat, its edge rolled over
        tailStartX = carX0 + tailLen
        TAIL_T = (0.0, 0.5, 1.0)


        # The track beam, in real Mark VI proportion to the car: narrow, showing
        # about a fifth of the car's height below the belly, and straight. Its
        # flat top runs up inside a straight channel in the belly, so the car
        # sits on the whole run. The bottom prints belly down, so the channel's
        # roof is a bridge. Three pins locate the car on the beam, and the
        # channel's sides are deep enough to glue to.
        beamHalfW, beamDepth = 5.0, 15.0
        beamHalfLen = 84.0            # ends inside the car: never past nose or tail
        beamCrestZ = 5.0              # beam top, up inside the belly
        beamFit = 0.8                 # total, across the channel
        channelHalfW = beamHalfW + beamFit / 2.0

        def beam_top(x):
            return beamCrestZ

        def beam_bottom(x):
            return beamCrestZ - beamDepth


        # Two pylons, spaced out under the beam, the same width as the beam,
        # so beam and pylons are a single flat profile that prints on its side
        # with nothing overhanging. They plug into one foot that gives the
        # stance -- wide and long, because the model gets picked up and handled.
        pylonX, pylonHalfX = 45.0, 6.0
        pylonShow = 9.0               # column visible below the beam at mid-span
        footTopZ = beam_bottom(0.0) - pylonShow
        footH = 6.0
        footZ0 = footTopZ - footH
        footHalfX, footHalfY, footTopHalfY = 65.0, 28.0, 25.0
        socketDepth, socketFit = 4.0, 0.6
        pylonZ0 = footTopZ - socketDepth  # each column stands on its socket floor

        TOTAL_HEIGHT = bodyZ1 - footZ0

        # Livery. Every colour region is a real geometric step, never a split
        # face: the slicer's fill tool floods across coplanar triangles, so a
        # Fusion face split gives it nothing to stop on. A 0.6-0.8 mm step does.
        liveryOver = 8.0              # how far the side-view tools run past the ends
        stripeZ0, stripeZ1, stripeDepth = 12.0, 23.0, 0.8
        sweepX0, sweepZ = carX0 + 30.0, 19.0   # the red's lower edge lifts over the
                                               # last 30 mm to this height at the tail
        bandZ0, bandZ1, bandDepth = 29.0, 42.0, 0.6
        bandTailTopX, bandTailBotX = carX0 + 3.5, carX0 + 6.5   # slanted end
        glassZ0, glassZ1, glassDepth = 30.5, 40.0, 1.2
        glassTopRearX = carX1 - 32.0  # the raked rear edge of the windshield:
        glassPointX, glassPointZ = carX1 - 35.0, 38.7   # a small point near the top,
        glassBotRearX = carX1 - 26.5  # then a long rake down and forward

        # The tail face carries the spare cube's pocket, the coupler block above
        # it, and a red tail light either side at stripe height.
        couplerHalfW, couplerZ0, couplerZ1, couplerProud = 7.0, 36.5, 45.5, 3.0
        lightY, lightHalfW, lightZ0, lightZ1, lightProud = 16.0, 1.2, 19.5, 22.5, 2.0

        cube, clearance = 20.0, 0.6
        cubeN = 3
        cubeEdgeFillet = 1.0
        slotW = cube + 2 * clearance
        frameWall, frameGap, frameProud = 1.5, 1.4, 1.5
        frameW = slotW + 2 * frameWall
        pitch = frameW + frameGap
        slotDepth = 16.0              # from the frame face
        arrayCentreX = -9.0
        frameZ0 = stripeZ1            # frames stand on the red's top edge
        slotZ0 = frameZ0 + frameWall
        slotZ1 = slotZ0 + slotW
        frameZ1 = slotZ1 + frameWall
        frameFaceY = carHalfW + frameProud
        slotFloorY = frameFaceY - slotDepth
        cubeProud = cube - slotDepth  # beyond the frame face

        spareClearance = 1.7          # total, so 0.85 a side. 1.2 printed snug: lying
                                      # on the split face, each half prints the
                                      # pocket's side wall as a supported roof, whose
                                      # support scars likely ate the slack. 0.6 total
                                      # seized on the ship
        spareDepth = cube + 1.2       # the cube sits 1.2 mm in from the tail face
        sparePocketSize = cube + spareClearance
        spareZ0 = lightZ0 + (lightZ1 - lightZ0 - sparePocketSize) / 2.0
                                      # centred on the tail lights, which leaves
                                      # room for the top notch under the coupler
        spareZ1 = spareZ0 + sparePocketSize
        spareCentreZ = (spareZ0 + spareZ1) / 2.0
        spareGripR = 3.0              # finger notch in the pocket's top and bottom
        spareGripDepth = 8.0          # walls: they stand upright in print. Notches
                                      # in the side walls were holes in the roof
                                      # bridge, and fell apart unsupported
        spareGripHalfW = spareGripR * math.sqrt(2.0)   # 45-degree flanks off the round

        # Where the parts meet. The red stripe is set stripeDepth into the body,
        # so the bottom's top face has a ledge round it, like the ship's deck
        # round its superstructure, with room for the ship's locating recess:
        # the red halves stand seatDepth down into it, along the flat run from
        # seatX0 to the nose. Behind that the red's lower edge sweeps up, and
        # the curve itself locates them.
        # The top gets the same white lip over the red, seatDepth deep. It
        # prints standing on its underside, where a recess the width of the red
        # would be a bridge just off the bed, so the red carries a rib, lipRib
        # wide, along its edge, and the top a groove behind the lip for it.
        seatDepth, seatGap = 0.4, 0.1
        seatX0 = sweepX0 + 3.0
        lipRib = 1.2
        # Every joint is pinned: loose pins in sockets in both parts, so every
        # part lies flat on the bed. Standing on end at these (x, y) across the
        # red-top joint and the seat, lying across the cut between the red
        # halves at (x, z), and standing in the beam's top at x, beamPinH into
        # each part there.
        pinDia, pinH, pinFit, socketExtra = 4.0, 3.0, 0.4, 0.5
        TOP_PIN_XY = [(-75.0, 15.0), (-75.0, -15.0), (50.0, 10.0), (50.0, -10.0)]
        SEAT_PIN_XY = [(-40.0, 12.0), (-40.0, -12.0), (30.0, 12.0), (30.0, -12.0)]
        RED_PIN_XZ = [(-45.0, 17.5), (40.0, 17.5)]
        beamPinH = 5.0
        BEAM_PIN_X = [-55.0, 0.0, 55.0]

        mickHead, mickEar = 6.0, 3.4
        mickEarGap = -0.7             # negative: how far the ear laps over the head
        mickEarAngle = 48.0           # degrees from vertical

        earOffset = (mickHead + mickEar) / 2.0 + mickEarGap
        EAR_SIN = math.sin(math.radians(mickEarAngle))
        EAR_COS = math.cos(math.radians(mickEarAngle))
        require(earOffset < (mickHead + mickEar) / 2.0 - 0.3,
                'Ears sit {:.2f} mm from the head centre against {:.2f} mm of combined '
                'radius. They need real overlap or they read as three loose blobs.'
                .format(earOffset, (mickHead + mickEar) / 2.0))

        # ------------------------------------------------------------- fonts
        # Fusion matches the family name exactly and rejects anything else. Each
        # list is tried in turn and the report says which name was used. The
        # Countdown fonts are this repository's own, built in Font/; Waltograph,
        # in its various spellings, is the fallback.
        WALTOGRAPH = ['Waltograph UI', 'Waltograph', 'waltograph UI', 'WaltographUI',
                      'Waltograph 42', 'Waltograph42']
        DIGIT_FONTS = ['Countdown Digits'] + WALTOGRAPH
        TEXT_FONTS = ['Countdown Lettering'] + WALTOGRAPH

        # ----------------------------------------------------- digit engraving
        digitRecess = 0.84            # 2 outer walls at 0.42 -- 0.6 is 1.43 walls,
                                      # which Arachne resolves differently layer to
                                      # layer and prints ragged
        digitInkHeight = 11.0         # visible glyph height -- calibrated, not guessed
        digitEmSeed = 15.0            # starting em size for the calibration pass
        digitBold = False             # neither digit font has a real bold weight
        digitShiftMark = 2.0          # lift the digit on faces that carry the mark
        digitMarkGap = 0.8            # clear space demanded between digit and mark
        toolOvershoot = 0.5           # how far the cut tool pokes past the face

        MARK_6_AND_9 = False          # Mickey doubles as the 6/9 orientation mark.
                                      # Off: Countdown Digits' 9 is its 6 upside
                                      # down, so the two need not be told apart
        markScale = 0.45
        markCentreY = -6.6            # below the face centre

        # ------------------------------------------------------ car lettering
        CAR_TEXT = {'D': "DAYS 'TIL VACATION",
                    'B': "VACATION IS CALLING!"}
        textSides = ('D', 'B')        # D is the display side (+y), B the back
        textSharedScale = True
        textRise = 1.2                # above the stripe floor; 0.4 proud of the flank
        textBite = 1.0                # into the stripe floor, so the join is solid
        textSeedEm = 20.0
        textX0, textX1 = arrayCentreX - 46.0, arrayCentreX + 46.0   # centred under the cubes
        textEndMargin = 2.0
        textBandMargin = 1.0          # clear of the stripe edges -- kept small, as
                                      # big lettering is the point
        textMinGlyphs = 4             # a fully joined script would defeat the fit
        textMinStroke = 0.45          # mm; about one extrusion width -- a hard floor
        textWarnStroke = 0.84         # two Bambu outer walls at 0.42, not 2 x 0.40

        textRun = (textX1 - textX0) - 2.0 * textEndMargin
        textMaxH = (stripeZ1 - stripeZ0) - 2.0 * textBandMargin
        textCentreX = (textX0 + textX1) / 2.0
        textCentreZ = (stripeZ0 + stripeZ1) / 2.0

        AXIS_NAMES = ('x', 'y', 'z')
        DIAG = math.sqrt(0.5)

        # -------------------------------------------------- section geometry
        # The car's cross-section at any station, as pure arithmetic. The solids
        # are built from exactly these numbers, and the guards below use them
        # to check things before a single feature exists.
        def ramp(t, power):
            """Fraction of a taper reached at t in [0, 1], and its slope d/dt."""
            if t <= 0.0:
                return 0.0, 0.0
            return t ** power, power * t ** (power - 1.0)

        def slope_factor(dg, drop, length):
            """How much further in, measured in a section's own plane, a face
            sloping by drop/length must move to end up `shrink` deep along its
            normal. Without it the livery recesses go shallow on the nose."""
            return math.sqrt(1.0 + (dg * drop / length) ** 2)

        def nose_section(t, shrink):
            """One nose cross-section, inset by `shrink` all round.

            Insetting every dimension and dropping every round by the same
            amount is a true offset of a rounded rectangle, which is what lets
            the livery recesses be cut as (side-view tool minus inset solid)."""
            g, dg = ramp(t, nosePower)
            gW, dgW = ramp(t, noseWidthPower)
            x = noseStartX + t * (carX1 - shrink - noseStartX)
            halfW = (carHalfW - (carHalfW - noseTipHalfW) * gW
                     - shrink * slope_factor(dgW, carHalfW - noseTipHalfW, noseLen))
            z0 = (bodyZ0 + (noseTipZ0 - bodyZ0) * g
                  + shrink * slope_factor(dg, noseTipZ0 - bodyZ0, noseLen))
            z1 = (bodyZ1 - (bodyZ1 - noseTipZ1) * g
                  - shrink * slope_factor(dg, bodyZ1 - noseTipZ1, noseLen))
            rB = max(minRound, bodyRBot - (bodyRBot - noseTipRBot) * g - shrink)
            rT = max(minRound, bodyRTop - (bodyRTop - noseTipRTop) * g - shrink)
            return x, halfW, z0, z1, rB, rT

        def tail_section(t, shrink):
            """One tail cross-section: the flat tail face with its edge rolled over."""
            g, dg = ramp(t, 2.0)
            inset = tailRound * g + shrink * slope_factor(dg, tailRound, tailLen)
            x = tailStartX - t * (tailStartX - (carX0 + shrink))
            return (x, carHalfW - inset, bodyZ0 + inset, bodyZ1 - inset,
                    max(minRound, bodyRBot - tailRound * g - shrink),
                    max(minRound, bodyRTop - tailRound * g - shrink))

        def section_at(x):
            """(halfW, z0, z1, rBot, rTop) of the finished body at station x."""
            if x >= noseStartX:
                return nose_section(min(1.0, (x - noseStartX) / noseLen), 0.0)[1:]
            if x <= tailStartX:
                return tail_section(min(1.0, (tailStartX - x) / tailLen), 0.0)[1:]
            return carHalfW, bodyZ0, bodyZ1, bodyRBot, bodyRTop

        def inside_section(y, z, sec, margin=0.0):
            """Is (y, z) inside that rounded-rectangle section, with margin to spare?"""
            halfW, z0, z1, rB, rT = sec
            ay = abs(y)
            if ay > halfW - margin or z < z0 + margin or z > z1 - margin:
                return False
            for r, cz, below in ((rB, z0 + rB, True), (rT, z1 - rT, False)):
                cy = halfW - r
                if ay > cy and ((below and z < cz) or (not below and z > cz)):
                    if math.hypot(ay - cy, z - cz) > r - margin:
                        return False
            return True

        # -------------------------------------------------------- layout guards
        flatZ0, flatZ1 = bodyZ0 + bodyRBot, bodyZ1 - bodyRTop
        require(bodyRBot + bodyRTop < bodyZ1 - bodyZ0 - 1.0 and 2.0 * bodyRTop < 2.0 * carHalfW - 1.0,
                'The section rounds do not fit a {:.0f} x {:.0f} mm body.'
                .format(2.0 * carHalfW, bodyZ1 - bodyZ0))
        require(stripeZ0 > flatZ0 + 0.3 and stripeZ1 < flatZ1,
                'The red stripe runs {:.1f} to {:.1f} mm, off the flat flank ({:.1f} to '
                '{:.1f} mm) -- the lettering has to sit on a flat floor.'
                .format(stripeZ0, stripeZ1, flatZ0, flatZ1))
        require(bandZ0 - stripeZ1 >= 3.0,
                'Stripe top {:.1f} mm and band bottom {:.1f} mm leave no white '
                'pinstripe between them.'.format(stripeZ1, bandZ0))
        require(bandZ1 < bodyZ1 - 2.0,
                'The window band runs over the roof crown.')
        require(bandZ0 + 1.0 < glassZ0 < glassPointZ < glassZ1 < bandZ1 - 1.0,
                'The windshield glass needs a black border inside the band on both sides.')
        require(glassPointX < glassTopRearX < glassBotRearX and glassPointX > noseStartX,
                'The windshield outline is inside out, or starts behind the nose.')
        require(sweepZ < stripeZ1 - 2.0 and sweepX0 > tailStartX + 10.0,
                'The red sweep at the tail leaves no red at the tail face.')

        arrayWidth = cubeN * frameW + (cubeN - 1) * frameGap
        arrayX0 = arrayCentreX - arrayWidth / 2.0
        arrayX1 = arrayCentreX + arrayWidth / 2.0
        displayCentres = [arrayCentreX + (i - (cubeN - 1) / 2.0) * pitch
                          for i in range(cubeN)]
        require(arrayX0 > tailStartX + 1.0 and arrayX1 < noseStartX - 1.0,
                'The cube frames run x {:.1f} to {:.1f}, off the parallel body '
                '({:.1f} to {:.1f}).'.format(arrayX0, arrayX1, tailStartX, noseStartX))
        require(bandTailBotX < arrayX0 - 1.0 and glassPointX > arrayX1 + 2.0,
                'The window band does not reach round the cube frames.')
        require(frameZ1 < bodyZ1 - 1.0,
                'The cube frames reach z {:.1f}, over the {:.1f} mm roof.'
                .format(frameZ1, bodyZ1))
        require(slotDepth > cube / 2.0,
                'Slot depth {:.1f} mm is under half the cube -- it would tip out.'
                .format(slotDepth))

        # The beam, and the belly straddling it along its flat run.
        flatX0, flatX1 = tailStartX, noseStartX
        straddleEnds = min(beam_top(flatX0), beam_top(flatX1))
        require(straddleEnds > 0.5,
                'The belly only covers {:.1f} mm of the beam at '
                'the ends of its flat run. Raise the beam top.'
                .format(straddleEnds))
        require(channelHalfW < carHalfW - bodyRBot - 3.0,
                'The beam channel is wider than the flat of the belly.')
        require(beamHalfLen <= min(carX1, -carX0) - 2.0,
                'The beam runs to x +/-{:.0f}, past the car\'s nose or tail.'
                .format(beamHalfLen))
        require(beamHalfLen > max(flatX1, -flatX0),
                'The beam stops short of the flat belly it has to carry.')
        require(pylonX - pylonHalfX > 10.0 and pylonX + pylonHalfX < beamHalfLen - 10.0,
                'The pylons at x +/-{:.0f} do not sit well under the beam.'.format(pylonX))
        require(footTopZ < beam_bottom(pylonX + pylonHalfX) - 5.0 and pylonZ0 - footZ0 >= 1.5,
                'The pylons and foot do not fit under the beam.')
        require(footTopHalfY > beamHalfW + socketFit / 2.0 + 5.0
                and footHalfX > pylonX + pylonHalfX + socketFit / 2.0 + 8.0,
                'The foot is too small round the pylon sockets.')

        # The spare cube's pocket in the tail face.
        tailCap = tail_section(1.0, 0.0)
        require(spareZ0 > tailCap[2] + 2.0 and spareZ1 < couplerZ0 - 2.0,
                'The spare pocket runs z {:.1f} to {:.1f}; the tail face is {:.1f} to '
                '{:.1f} with the coupler from {:.1f}.'
                .format(spareZ0, spareZ1, tailCap[2], tailCap[3], couplerZ0))
        require(carX0 + spareDepth < arrayX0 - 2.0,
                'The spare pocket reaches the display slots.')
        require(spareZ0 - spareGripR > beamCrestZ + 2.0
                and spareZ1 + spareGripR < couplerZ0 - 1.0,
                'Finger notches run z {:.1f} to {:.1f}, too close to the beam channel '
                '({:.1f}) or the coupler ({:.1f}).'.format(
                    spareZ0 - spareGripR, spareZ1 + spareGripR, beamCrestZ, couplerZ0))
        require(spareGripHalfW < sparePocketSize / 2.0 - 3.0,
                'The finger notches reach the pocket\'s side walls.')
        require(couplerZ1 < tailCap[3] - 1.0 and couplerHalfW < tailCap[1] - 2.0
                and couplerZ0 + couplerProud < couplerZ1 - 3.0,
                'The tail coupler does not fit on the tail face.')
        require(lightY - lightHalfW > sparePocketSize / 2.0 + 2.0
                and lightY + lightHalfW < tailCap[1] - 1.0,
                'The tail lights do not fit between the spare pocket and the edge.')
        require(sweepZ <= lightZ0 and lightZ1 <= stripeZ1,
                'The tail lights are not inside the red at the tail face.')
        # Where the parts meet: the seat, and the pins between the red and the top.
        def red_floor(x):
            """The red's lower edge at station x: flat, then sweeping up to the tail."""
            if x >= sweepX0:
                return stripeZ0
            u = min(1.0, (sweepX0 - x) / (sweepX0 - carX0))
            return stripeZ0 + (sweepZ - stripeZ0) * u * u * (3.0 - 2.0 * u)

        require(seatX0 > carX0 + spareDepth + 2.0 and seatX0 < arrayX0,
                'The seat for the red halves starts at x {:.1f}, in the spare pocket or '
                'past the cubes.'.format(seatX0))
        require(stripeDepth - seatGap >= 0.6,
                'The rim round the red halves\' seat is {:.2f} mm wide -- too thin to '
                'print.'.format(stripeDepth - seatGap))
        require(stripeZ0 - seatDepth > beamCrestZ + beamPinH + socketExtra + 0.8,
                'The beam pins\' sockets come within 0.8 mm of the seat for the red halves.')
        socketR = (pinDia + pinFit) / 2.0
        for (px, py) in TOP_PIN_XY:
            sec = section_at(px)
            zLo, zHi = stripeZ1 - pinH - socketExtra, stripeZ1 + pinH + socketExtra
            require(all(inside_section(abs(py) + sgn * socketR, z, sec, 1.5)
                        for sgn in (-1.0, 1.0) for z in (zLo, zHi)),
                    'The pin at x {:.0f}, y {:.0f} is too near the skin.'.format(px, py))
            require(abs(py) + socketR < carHalfW - stripeDepth - textBite - 1.5,
                    'The pin at x {:.0f}, y {:.0f} runs into the lettering.'.format(px, py))
            require(zLo > red_floor(px) + 1.5,
                    'The pin socket at x {:.0f} goes through the red, whose lower edge '
                    'is at z {:.1f} there.'.format(px, red_floor(px)))
            require(not (py > 0.0 and arrayX0 - socketR - 1.5 < px < arrayX1 + socketR + 1.5
                         and py + socketR > slotFloorY - 1.5),
                    'The pin at x {:.0f}, y {:.0f} runs into a cube slot.'.format(px, py))
            require(px - socketR > carX0 + spareDepth + 1.5
                    or abs(py) - socketR > sparePocketSize / 2.0 + 1.5,
                    'The pin at x {:.0f}, y {:.0f} runs into the spare pocket.'.format(px, py))
            require(abs(py) + socketR < carHalfW - stripeDepth - lipRib - seatGap - 1.0,
                    'The pin at x {:.0f}, y {:.0f} runs into the groove behind the top\'s '
                    'lip.'.format(px, py))
        seatJoint = stripeZ0 - seatDepth
        for (px, py) in SEAT_PIN_XY:
            sec = section_at(px)
            zLo, zHi = seatJoint - pinH - socketExtra, seatJoint + pinH + socketExtra
            require(all(inside_section(abs(py) + sgn * socketR, z, sec, 1.5)
                        for sgn in (-1.0, 1.0) for z in (zLo, zHi)),
                    'The seat pin at x {:.0f}, y {:.0f} is too near the skin.'.format(px, py))
            require(abs(py) + socketR < carHalfW - stripeDepth - textBite - 1.5
                    and abs(py) - socketR > channelHalfW + 1.5,
                    'The seat pin at x {:.0f}, y {:.0f} runs into the lettering or the beam '
                    'channel.'.format(px, py))
            require(px - socketR > seatX0 + seatGap and zHi < stripeZ1 - pinH - socketExtra - 1.0,
                    'The seat pin at x {:.0f} is off the seat, or meets the top\'s pins.'
                    .format(px))
        for (px, pz) in RED_PIN_XZ:
            sec = section_at(px)
            require(pz - socketR > max(stripeZ0, red_floor(px)) + 1.0
                    and pz + socketR < stripeZ1 - 1.0
                    and px - socketR > carX0 + spareDepth + 1.5
                    and inside_section(pinH + socketExtra, pz, sec, 1.5),
                    'The pin between the red halves at x {:.0f}, z {:.1f} does not fit in the '
                    'red.'.format(px, pz))
            require(min(abs(py) for _, py in TOP_PIN_XY + SEAT_PIN_XY) - socketR
                    > pinH + socketExtra + 1.0,
                    'The pins between the red halves run into the other pins.')
        beamSocketTop = beamCrestZ + beamPinH + socketExtra
        require(socketR < beamHalfW - 1.5
                and beamCrestZ - beamPinH - socketExtra > beam_bottom(0.0) + 2.0,
                'The beam is too slim or too shallow for its pins.')
        for px in BEAM_PIN_X:
            sec = section_at(px)
            require(abs(px) + socketR < beamHalfLen - 2.0
                    and px - socketR > carX0 + spareGripDepth + 1.5
                    and sec[1] < beamCrestZ - 1.0
                    and inside_section(socketR, beamSocketTop, sec, 1.0),
                    'The beam pin at x {:.0f} does not sit inside the belly.'.format(px))

        require(textX1 < noseStartX - 1.0,
                'The lettering runs to x {:.1f}, onto the nose at {:.1f}. Flat glyphs '
                'bury at one end and float at the other there.'.format(textX1, noseStartX))
        require(textX0 > sweepX0 + 1.0,
                'The lettering starts at x {:.1f}, where the red is already sweeping up.'
                .format(textX0))
        require(textRun > 20.0 and textMaxH > 3.0,
                'No usable room left for the lettering.')

        # ===================================================== generic helpers
        def axis_component(point, axis):
            return {'x': point.x, 'y': point.y, 'z': point.z}[axis]

        planeSerial = [0]

        def plane_through(name, basePlane, axis, coord):
            """An offset plane that really does lie at `coord` on `axis`.

            Which way an offset goes depends on the base plane's normal, which
            is not worth assuming. Measure where it landed and go the other way
            if it went the wrong way. A wrong guess is left hidden, not deleted:
            a stray plane never exports."""
            for sign in (1.0, -1.0):
                planeSerial[0] += 1
                pi = root.constructionPlanes.createInput()
                pi.setByOffset(basePlane, adsk.core.ValueInput.createByString(
                    '{} mm'.format(sign * coord)))
                plane = root.constructionPlanes.add(pi)
                plane.name = '{}_{}'.format(name, planeSerial[0])
                plane.isLightBulbOn = False
                got = axis_component(plane.geometry.origin, axis) * 10.0
                if abs(got - coord) < 0.01:
                    return plane
            raise RuntimeError('Could not place a plane at {} = {:.2f} mm.'.format(axis, coord))

        planeCache = {}

        def plane_at(z):
            key = round(z, 4)
            if key not in planeCache:
                planeCache[key] = plane_through(
                    'Deck_P_{}'.format(key).replace('.', '_').replace('-', 'n'),
                    root.xYConstructionPlane, 'z', z)
            return planeCache[key]

        def sketch_axis_map(sk):
            """Measure which global axes this sketch's local X and Y actually track.

            Fusion's construction-plane orientations are not worth assuming: getting
            the YZ plane's mapping backwards silently rotates a pocket 90 degrees."""
            o = sk.sketchToModelSpace(adsk.core.Point3D.create(0.0, 0.0, 0.0))
            pu = sk.sketchToModelSpace(adsk.core.Point3D.create(1.0, 0.0, 0.0))
            pv = sk.sketchToModelSpace(adsk.core.Point3D.create(0.0, 1.0, 0.0))
            uVec = (pu.x - o.x, pu.y - o.y, pu.z - o.z)
            vVec = (pv.x - o.x, pv.y - o.y, pv.z - o.z)

            def dominant(vec):
                i = max(range(3), key=lambda k: abs(vec[k]))
                return AXIS_NAMES[i], (1.0 if vec[i] >= 0 else -1.0)

            return (o,) + dominant(uVec) + dominant(vVec)

        def local_mapper(sk, axes):
            o, uAxis, uSign, vAxis, vSign = sketch_axis_map(sk)
            require(set([uAxis, vAxis]) == set(axes),
                    'Sketch "{}" lies along global {}/{}, but its geometry is given '
                    'in {}/{}.'.format(sk.name, uAxis, vAxis, axes[0], axes[1]))

            def to_local(gA, gB):
                vals = {axes[0]: mm(gA), axes[1]: mm(gB)}
                u = (vals[uAxis] - axis_component(o, uAxis)) / uSign
                v = (vals[vAxis] - axis_component(o, vAxis)) / vSign
                return adsk.core.Point3D.create(u, v, 0)
            return to_local

        def all_profiles(sk):
            coll = adsk.core.ObjectCollection.create()
            for i in range(sk.profiles.count):
                coll.add(sk.profiles.item(i))
            return coll

        def body_named(name):
            b = root.bRepBodies.itemByName(name)
            require(b is not None, 'Body "{}" is missing.'.format(name))
            return b

        def volume_mm3(name):
            return body_named(name).physicalProperties.volume * 1000.0

        def is_outside(name, x, y, z):
            """Is that point outside the body? The honest check that a pocket is
            where it was meant to be: a volume check passes on either side."""
            c = body_named(name).pointContainment(
                adsk.core.Point3D.create(mm(x), mm(y), mm(z)))
            return c == adsk.fusion.PointContainment.PointOutsidePointContainment

        def is_inside(name, x, y, z):
            c = body_named(name).pointContainment(
                adsk.core.Point3D.create(mm(x), mm(y), mm(z)))
            return c == adsk.fusion.PointContainment.PointInsidePointContainment

        toolSerial = [0]

        def label_tool_bodies(feature):
            """Tag the cut tools so a failed run leaves identifiable debris that
            the cleanup at the top of the script sweeps up.

            The tools are tracked by FEATURE, never by name. Renaming a body is
            not a timeline operation, so the name does not survive a recompute."""
            for i in range(feature.bodies.count):
                toolSerial[0] += 1
                feature.bodies.item(i).name = 'Tool_Text_{}'.format(toolSerial[0])
            return feature

        def tool_bodies(feats):
            """Live bodies of the given features, re-read on every call."""
            out = []
            for f in feats:
                require(f.bodies.count > 0, 'A cut tool feature produced no bodies.')
                for i in range(f.bodies.count):
                    out.append(f.bodies.item(i))
            return out

        def bodies_extent(feats):
            """Combined bounding box of those features' bodies, in mm."""
            return extent_of(tool_bodies(feats))

        def extent_of(bodies):
            lo = [1.0e9, 1.0e9, 1.0e9]
            hi = [-1.0e9, -1.0e9, -1.0e9]
            require(len(bodies) > 0, 'Nothing to measure.')
            for b in bodies:
                bb = b.boundingBox
                spans = ((bb.minPoint.x, bb.maxPoint.x),
                         (bb.minPoint.y, bb.maxPoint.y),
                         (bb.minPoint.z, bb.maxPoint.z))
                for i, (mn, mx) in enumerate(spans):
                    lo[i] = min(lo[i], mn * 10.0)
                    hi[i] = max(hi[i], mx * 10.0)
            return lo, hi

        def collect(feats):
            coll = adsk.core.ObjectCollection.create()
            for b in tool_bodies(feats):
                coll.add(b)
            return coll

        def move_solids(bodies, matrix):
            coll = adsk.core.ObjectCollection.create()
            for b in bodies:
                coll.add(b)
            if hasattr(moves, 'createInput2'):
                mi = moves.createInput2(coll)
                mi.defineAsFreeMove(matrix)
            else:
                mi = moves.createInput(coll, matrix)
            moves.add(mi)

        def move_by_matrix(feats, matrix):
            move_solids(tool_bodies(feats), matrix)

        def translate(feats, dx, dy):
            if abs(dx) < 1.0e-6 and abs(dy) < 1.0e-6:
                return
            matrix = adsk.core.Matrix3D.create()
            matrix.translation = adsk.core.Vector3D.create(mm(dx), mm(dy), 0.0)
            move_by_matrix(feats, matrix)

        lastFeature = [None]          # the most recent combine, for painting its faces

        def combine_bodies(targetName, toolBodies, op, keepTools=False):
            """Combine, and hand back EVERY body the feature produced.

            A cut that disconnects its target yields several bodies and only one
            keeps the plain name -- the rest become "Name (1)", "Name (2)".
            Reading the feature instead of the name is what stops those
            surviving into the export, and what stops a follow-up cut reaching
            only whichever piece happened to keep the name."""
            target = body_named(targetName)
            coll = adsk.core.ObjectCollection.create()
            for b in toolBodies:
                coll.add(b)
            require(coll.count > 0, 'Combine on "{}" was handed no tools.'.format(targetName))
            ci = combines.createInput(target, coll)
            ci.operation = op
            ci.isKeepToolBodies = keepTools
            feat = combines.add(ci)
            lastFeature[0] = feat
            # Both sources, unioned: the feature's own list, and every body
            # still carrying the target's name. Fusion names are unique, so the
            # names dedupe. Trusting either one alone has been wrong before.
            out, seen = [], set()
            for i in range(feat.bodies.count):
                b = feat.bodies.item(i)
                if b.name not in seen:
                    seen.add(b.name)
                    out.append(b)
            for b in root.bRepBodies:
                if b.name in seen:
                    continue
                if b.name == targetName or b.name.startswith(targetName + ' ('):
                    seen.add(b.name)
                    out.append(b)
            require(len(out) > 0,
                    'Combine on "{}" left nothing behind -- the tool swallowed it '
                    'whole.'.format(targetName))
            return out

        def cut_from(targetName, tools, keepTools=False):
            return combine_bodies(targetName, tools,
                                  adsk.fusion.FeatureOperations.CutFeatureOperation, keepTools)

        def join_into(targetName, tools):
            return combine_bodies(targetName, tools,
                                  adsk.fusion.FeatureOperations.JoinFeatureOperation, False)

        # ------------------------------------------------- preview colours
        # Paints faces as they are created, while the feature can still say
        # exactly which faces it made -- by the end of the timeline most have
        # been reworked by later features and the lists come back short.
        # Cosmetic: a failure here is reported, never fatal, and the slicer
        # still gets painted by hand on the steps these faces sit on.
        # The windshield prints black like the band; its paint here is a shade
        # off black only so its outline still shows in Fusion.
        PAINT_RGB = {'white': (238, 238, 232), 'black': (28, 28, 32),
                     'glass': (48, 52, 58), 'red': (190, 28, 34),
                     'gold': (238, 178, 40), 'grey': (150, 152, 158)}
        paints = {}
        paintTrouble = []

        def paint(name):
            if name not in paints:
                existing = design.appearances.itemByName('Livery ' + name)
                if existing is None:
                    lib = app.materialLibraries.itemByName('Fusion Appearance Library')
                    base = lib.appearances.itemByName('Plastic - Matte (White)')
                    existing = design.appearances.addByCopy(base, 'Livery ' + name)
                    r, g, b = PAINT_RGB[name]
                    for i in range(existing.appearanceProperties.count):
                        prop = existing.appearanceProperties.item(i)
                        if prop.objectType == adsk.core.ColorProperty.classType():
                            try:
                                prop.value = adsk.core.Color.create(r, g, b, 255)
                            except:
                                pass
                paints[name] = existing
            return paints[name]

        def paint_faces(feature, colour, pick=None):
            """Give the faces `feature` created the colour; pick(face) may
            return another colour name for some of them, or None to skip."""
            if not PREVIEW_COLOURS:
                return
            try:
                for i in range(feature.faces.count):
                    face = feature.faces.item(i)
                    c = pick(face) if pick else colour
                    if c:
                        face.appearance = paint(c)
            except Exception as ex:
                paintTrouble.append('{}: {}'.format(colour, ex))

        def paint_body(name, colour):
            if not PREVIEW_COLOURS:
                return
            try:
                body_named(name).appearance = paint(colour)
            except Exception as ex:
                paintTrouble.append('{}: {}'.format(name, ex))

        def face_point(face):
            p = face.pointOnFace
            return p.x * 10.0, p.y * 10.0, p.z * 10.0

        fillets = root.features.filletFeatures

        def fillet_edges(edgeList, expression, label):
            require(len(edgeList) > 0, 'Found no {} edges to fillet.'.format(label))
            coll = adsk.core.ObjectCollection.create()
            for e in edgeList:
                coll.add(e)
            fi = fillets.createInput()
            fi.edgeSetInputs.addConstantRadiusEdgeSet(
                coll, adsk.core.ValueInput.createByString(expression), False)
            fillets.add(fi)

        def extrude_symmetric(sk, totalDepth, name):
            """The sketch's single profile, pushed out equally both ways, as a new body."""
            require(sk.profiles.count == 1,
                    'Sketch "{}" closed into {} profiles, expected 1.'
                    .format(sk.name, sk.profiles.count))
            ei = extrudes.createInput(sk.profiles.item(0),
                                      adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            ei.setDistanceExtent(True, adsk.core.ValueInput.createByString(
                '{} mm'.format(symmetric_value(totalDepth))))
            feat = extrudes.add(ei)
            require(feat.bodies.count == 1,
                    'Sketch "{}" extruded into {} bodies.'.format(sk.name, feat.bodies.count))
            body = feat.bodies.item(0)
            body.name = name
            return body

        def box_body(name, x0, x1, y0, y1, z0, z1):
            """An axis-aligned block, used as a cut tool or a raised detail."""
            require(x1 > x0 and y1 > y0 and z1 > z0,
                    'Box "{}" has a non-positive span.'.format(name))
            sk = root.sketches.add(plane_at(z0))
            sk.name = 'Tool_Sk_' + name
            to_local = local_mapper(sk, ('x', 'y'))
            sp = sk.sketchPoints
            bl = sp.add(to_local(x0, y0))
            br = sp.add(to_local(x1, y0))
            tr = sp.add(to_local(x1, y1))
            tl = sp.add(to_local(x0, y1))
            lines = sk.sketchCurves.sketchLines
            lines.addByTwoPoints(bl, br)
            lines.addByTwoPoints(br, tr)
            lines.addByTwoPoints(tr, tl)
            lines.addByTwoPoints(tl, bl)
            require(sk.profiles.count == 1, 'Box sketch "{}" did not close.'.format(name))
            ei = extrudes.createInput(sk.profiles.item(0),
                                      adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            ei.setDistanceExtent(False, adsk.core.ValueInput.createByString(
                '{} mm'.format(z1 - z0)))
            body = extrudes.add(ei).bodies.item(0)
            body.name = 'Tool_' + name
            lo, hi = extent_of([body])
            require(abs(lo[2] - z0) < 0.05 and abs(hi[2] - z1) < 0.05,
                    'Box "{}" came out at z {:.2f} to {:.2f}, asked for {:.2f} to {:.2f} '
                    '-- the extrude went the wrong way.'.format(name, lo[2], hi[2], z0, z1))
            return body

        def side_prism(name, corners, halfSpan, curved=None, arcs=None, bodyName=None):
            """A solid drawn in side view and pushed straight through in y.

            corners is a closed outline in global (x, z). curved maps a corner
            index i to fit points (x, z) for a spline from corner i to corner
            i + 1; arcs maps i to one point (x, z) the arc from i to i + 1
            passes through; every other edge is a straight line. Corner points
            are made once and handed to both curves that meet there -- never
            read an endpoint back off a curve."""
            curved = curved or {}
            arcs = arcs or {}
            sk = root.sketches.add(root.xZConstructionPlane)
            sk.name = 'Tool_Sk_' + name
            to_local = local_mapper(sk, ('x', 'z'))
            sp = sk.sketchPoints
            pts = [sp.add(to_local(a, b)) for a, b in corners]
            lines = sk.sketchCurves.sketchLines
            splines = sk.sketchCurves.sketchFittedSplines
            arcCurves = sk.sketchCurves.sketchArcs
            for i in range(len(pts)):
                j = (i + 1) % len(pts)
                if i in arcs:
                    arcCurves.addByThreePoints(pts[i], to_local(*arcs[i]), pts[j])
                elif i in curved:
                    coll = adsk.core.ObjectCollection.create()
                    coll.add(pts[i])
                    for a, b in curved[i]:
                        coll.add(sp.add(to_local(a, b)))
                    coll.add(pts[j])
                    splines.add(coll)
                else:
                    lines.addByTwoPoints(pts[i], pts[j])
            return extrude_symmetric(sk, 2.0 * halfSpan, bodyName or ('Tool_' + name))

        def end_prism(name, corners, x0, x1, bodyName=None):
            """A solid drawn in end view, closed straight lines through global
            (y, z) corners, pushed along x from x0 to x1."""
            sk = root.sketches.add(plane_through(
                'Tool_P_' + name, root.yZConstructionPlane, 'x', (x0 + x1) / 2.0))
            sk.name = 'Tool_Sk_' + name
            to_local = local_mapper(sk, ('y', 'z'))
            sp = sk.sketchPoints
            pts = [sp.add(to_local(a, b)) for a, b in corners]
            lines = sk.sketchCurves.sketchLines
            for i in range(len(pts)):
                lines.addByTwoPoints(pts[i], pts[(i + 1) % len(pts)])
            return extrude_symmetric(sk, x1 - x0, bodyName or ('Tool_' + name))

        # ------------------------------------------------------- text machinery
        def text_tool(sketchName, text, emHeight, depth, font):
            """Text prism standing on the world XY plane.

            Fusion's MiddleVerticalAlignment anchors a single line near the
            bottom of its box rather than centring it. So the box is used only
            to stop wrapping; the glyph gets centred afterwards by measuring
            where the ink actually landed."""
            sk = root.sketches.add(root.xYConstructionPlane)
            sk.name = sketchName
            boxW = emHeight * len(text) * 1.6 + 10.0
            boxH = emHeight * 3.0
            inp = sk.sketchTexts.createInput2(text, mm(emHeight))
            inp.fontName = font
            if digitBold and font == digitFont:
                inp.textStyle = adsk.fusion.TextStyles.TextStyleBold
            inp.setAsMultiLine(
                P(-boxW / 2.0, -boxH / 2.0), P(boxW / 2.0, boxH / 2.0),
                adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                adsk.core.VerticalAlignments.MiddleVerticalAlignment,
                0.0)
            try:
                txt = sk.sketchTexts.add(inp)
            except:
                raise RuntimeError(
                    'Fusion would not create text in the font "{}", although the '
                    'resolver accepted that name earlier in this run.'.format(font))
            op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
            try:
                ei = extrudes.createInput(txt, op)
            except:
                coll = adsk.core.ObjectCollection.create()
                coll.add(txt)
                ei = extrudes.createInput(coll, op)
            ei.setDistanceExtent(False, adsk.core.ValueInput.createByString(
                '{} mm'.format(depth)))
            feat = extrudes.add(ei)
            require(feat.bodies.count > 0,
                    'Text "{}" produced no solid -- the glyph outlines in "{}" are '
                    'probably self-intersecting.'.format(text, font))
            return label_tool_bodies(feat), sk

        def font_files_on_disk(needle):
            """Where the font actually lives, which says whether Fusion could
            ever see it. A file only under ~/Library/Fonts is installed for this
            user; Fusion does not always pick those up."""
            hits = []
            for folder in (os.path.expanduser('~/Library/Fonts'),
                           '/Library/Fonts', '/System/Library/Fonts',
                           os.path.join(os.environ.get('WINDIR', ''), 'Fonts')):
                try:
                    for f in sorted(os.listdir(folder)):
                        if needle.lower() in f.lower():
                            hits.append(os.path.join(folder, f))
                except:
                    pass
            return hits

        def resolve_font(candidates, sample, what):
            """The first family name Fusion will actually build text in, found
            before a thousand features depend on it. Fusion raises on add(), not
            on setting fontName, so the only honest test is to create some and
            throw it away."""
            tried = []
            for name in candidates:
                if name in tried:
                    continue
                tried.append(name)
                sk = root.sketches.add(root.xYConstructionPlane)
                sk.name = 'Probe_Font'
                try:
                    inp = sk.sketchTexts.createInput2(sample, mm(10.0))
                    inp.fontName = name
                    inp.setAsMultiLine(
                        P(-40.0, -20.0), P(40.0, 20.0),
                        adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                        adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0.0)
                    sk.sketchTexts.add(inp)
                    sk.deleteMe()
                    return name
                except:
                    try:
                        sk.deleteMe()
                    except:
                        pass
            found = font_files_on_disk('countdown') + font_files_on_disk('walto')
            raise RuntimeError(
                'Fusion rejected every font name tried for the {}: {}.\n\n'
                'Matching font files on this machine:\n  {}\n\n'
                'Open Sketch > Create > Text in Fusion and read the exact family '
                'name out of the Font dropdown, then put it first in the list. If it '
                'is not in that dropdown at all, Fusion cannot see the font: install '
                'the TrueType (.ttf) file in Font Book -- Fusion refuses '
                'OpenType-PostScript (.otf) fonts -- then restart Fusion, which '
                'reads its font list only at launch.'
                .format(what, ', '.join('"{}"'.format(t) for t in tried),
                        '\n  '.join(found) if found else
                        '(none found -- the font is not installed)'))

        digitFont = resolve_font(DIGIT_FONTS, '0', 'cube digits')
        textFont = resolve_font(TEXT_FONTS, 'D', 'car lettering')

        # ============================================================== the car
        def rounded_rect(sk, to_local, halfW, z0, z1, rB, rT):
            """Rounded rectangle given in global (y, z), drawn in sketch space,
            with one round at the two belly corners and another at the roof.

            The eight tangent points are created once and shared by the line and
            the arc that meet there. Never read an endpoint back off a curve:
            addByThreePoints stores arcs counter-clockwise, so a clockwise arc
            returns start and end swapped and the chain joins the wrong corners."""
            require(min(rB, rT) > 0.3, 'A corner round collapsed to {:.2f} mm.'.format(min(rB, rT)))
            require(2.0 * max(rB, rT) < 2.0 * halfW - 0.2 and rB + rT < (z1 - z0) - 0.2,
                    'Rounds of {:.2f} and {:.2f} mm will not fit a {:.2f} x {:.2f} mm '
                    'section.'.format(rB, rT, 2.0 * halfW, z1 - z0))
            sp = sk.sketchPoints
            lines = sk.sketchCurves.sketchLines
            arcs = sk.sketchCurves.sketchArcs

            A = sp.add(to_local(halfW, z0 + rB))
            Bp = sp.add(to_local(halfW, z1 - rT))
            C = sp.add(to_local(halfW - rT, z1))
            D = sp.add(to_local(-halfW + rT, z1))
            E = sp.add(to_local(-halfW, z1 - rT))
            F = sp.add(to_local(-halfW, z0 + rB))
            G = sp.add(to_local(-halfW + rB, z0))
            H = sp.add(to_local(halfW - rB, z0))

            lines.addByTwoPoints(A, Bp)     # display flank
            lines.addByTwoPoints(C, D)      # roof
            lines.addByTwoPoints(E, F)      # back flank
            lines.addByTwoPoints(G, H)      # belly

            dT, dB = rT * DIAG, rB * DIAG
            arcs.addByThreePoints(Bp, to_local(halfW - rT + dT, z1 - rT + dT), C)
            arcs.addByThreePoints(D, to_local(-halfW + rT - dT, z1 - rT + dT), E)
            arcs.addByThreePoints(F, to_local(-halfW + rB - dB, z0 + rB - dB), G)
            arcs.addByThreePoints(H, to_local(halfW - rB + dB, z0 + rB - dB), A)

            require(sk.profiles.count == 1,
                    'Rounded-rect sketch "{}" closed into {} profiles, expected 1.'
                    .format(sk.name, sk.profiles.count))

        def bottom_rounded(sk, to_local, a0, a1, z0, z1, r):
            """A rectangle in global (a, z) with only its two bottom corners
            rounded. The top sits buried inside the body, so it stays square."""
            require(2.0 * r < (a1 - a0) - 0.2 and r < (z1 - z0) - 0.2,
                    'A {:.1f} mm round will not fit the {} outline.'.format(r, sk.name))
            sp = sk.sketchPoints
            lines = sk.sketchCurves.sketchLines
            arcs = sk.sketchCurves.sketchArcs
            TR = sp.add(to_local(a1, z1))
            TL = sp.add(to_local(a0, z1))
            L = sp.add(to_local(a0, z0 + r))
            BL = sp.add(to_local(a0 + r, z0))
            BR = sp.add(to_local(a1 - r, z0))
            R = sp.add(to_local(a1, z0 + r))
            lines.addByTwoPoints(TR, TL)
            lines.addByTwoPoints(TL, L)
            lines.addByTwoPoints(BL, BR)
            lines.addByTwoPoints(R, TR)
            d = r * DIAG
            arcs.addByThreePoints(L, to_local(a0 + r - d, z0 + r - d), BL)
            arcs.addByThreePoints(BR, to_local(a1 - r + d, z0 + r - d), R)
            require(sk.profiles.count == 1,
                    'Sketch "{}" closed into {} profiles, expected 1.'
                    .format(sk.name, sk.profiles.count))

        def loft_sections(tag, label, sections):
            """Loft through (x, halfW, z0, z1, rB, rT) sections into a new body."""
            li = lofts.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            for i, (sx, sHalfW, sz0, sz1, srB, srT) in enumerate(sections):
                sk = root.sketches.add(plane_through(
                    'Car_P_{}_{}_{}'.format(label, tag, i), root.yZConstructionPlane, 'x', sx))
                sk.name = 'Car_{}_{}_{}'.format(label, tag, i)
                rounded_rect(sk, local_mapper(sk, ('y', 'z')), sHalfW, sz0, sz1, srB, srT)
                li.loftSections.add(sk.profiles.item(0))
            li.isSolid = True
            feat = lofts.add(li)
            require(feat.bodies.count == 1,
                    'The {} loft for "{}" produced {} bodies.'
                    .format(label, tag, feat.bodies.count))
            body = feat.bodies.item(0)
            body.name = 'Tool_{}_{}'.format(label, tag)
            return body

        def build_car(tag, shrink):
            """The main body as one solid: a parallel midbody, a lofted bullet
            nose and a rolled-over tail, joined.

            Called once for the car itself and once per livery band. The inset
            copies are cut tools, never parts, and each is consumed by the
            combine that uses it."""
            halfW = carHalfW - shrink
            z0, z1 = bodyZ0 + shrink, bodyZ1 - shrink
            rB = max(minRound, bodyRBot - shrink)
            rT = max(minRound, bodyRTop - shrink)
            midLen = noseStartX - tailStartX
            midMid = (tailStartX + noseStartX) / 2.0

            sk = root.sketches.add(plane_through(
                'Car_P_Mid_' + tag, root.yZConstructionPlane, 'x', midMid))
            sk.name = 'Car_Mid_' + tag
            rounded_rect(sk, local_mapper(sk, ('y', 'z')), halfW, z0, z1, rB, rT)
            extrude_symmetric(sk, midLen, tag)

            noseBody = loft_sections(tag, 'Nose', [nose_section(t, shrink) for t in NOSE_T])
            tailBody = loft_sections(tag, 'Tail', [tail_section(t, shrink) for t in TAIL_T])
            join_into(tag, [noseBody, tailBody])

            out = body_named(tag)
            lo, hi = extent_of([out])
            spanX = hi[0] - lo[0]
            require(abs(spanX - (carLen - 2.0 * shrink)) < 0.5,
                    'Car "{}" came out {:.1f} mm long, expected {:.1f}.'
                    .format(tag, spanX, carLen - 2.0 * shrink))
            require(hi[0] > lo[0] and abs(hi[0] - (carX1 - shrink)) < 0.5,
                    'Car "{}" has its nose at x {:.1f}, expected {:.1f} -- it was built '
                    'back to front.'.format(tag, hi[0], carX1 - shrink))
            return out

        carBody = build_car('Car', 0.0)
        paint_body('Car', 'white')

        # --------------------------------------------------------- the livery
        def livery_cut(name, depth, colour, corners, curved=None):
            """Recess the car's skin inside a side-view outline, following the
            real surface.

            The tool is (side-view prism AND NOT inset solid), which tracks the
            flank, the nose, the tail roll and the corner rounds alike -- a
            planar tool cannot.

            Two rules learned the hard way. Every tool is CONSUMED by a combine
            rather than deleted afterwards: deleteMe() returns True on a body an
            earlier combine still references and then does not remove it, so the
            tools survived into the export. And all of a band's tools go into ONE
            combine, because a cut can disconnect its target and a second
            combine would reach only whichever piece kept the name."""
            before = volume_mm3('Car')
            innerName = 'Inner_' + name
            build_car(innerName, depth)
            side_prism(name, corners, carHalfW + liveryOver, curved)
            pieces = cut_from('Tool_' + name, [body_named(innerName)])
            cut_from('Car', pieces)
            paint_faces(lastFeature[0], colour)
            removed = before - volume_mm3('Car')
            require(removed > 1.0,
                    'The {} recess removed {:.2f} mm3 -- the tool missed the car '
                    'entirely.'.format(name, removed))
            return removed, len(pieces)

        frontX = carX1 + liveryOver
        backX = carX0 - liveryOver

        bandCut, bandPieces = livery_cut('Band', bandDepth, 'black', [
            (bandTailTopX, bandZ1), (frontX, bandZ1),
            (frontX, bandZ0), (bandTailBotX, bandZ0)])

        glassCut, glassPieces = livery_cut('Glass', glassDepth, 'glass', [
            (frontX, glassZ1), (glassTopRearX, glassZ1),
            (glassPointX, glassPointZ), (glassBotRearX, glassZ0),
            (frontX, glassZ0)])

        # The red's lower edge lifts toward the tail on an S-curve: flat where it
        # leaves the straight run, flat again where it reaches the tail face.
        def smoothstep(u):
            return u * u * (3.0 - 2.0 * u)
        sweepFit = [(sweepX0 + (carX0 - sweepX0) * u,
                     stripeZ0 + (sweepZ - stripeZ0) * smoothstep(u))
                    for u in (0.75, 0.5, 0.25)]
        stripeCut, stripePieces = livery_cut('Stripe', stripeDepth, 'red', [
            (frontX, stripeZ0), (frontX, stripeZ1),
            (backX, stripeZ1), (backX, sweepZ),
            (carX0, sweepZ), (sweepX0, stripeZ0)],
            {4: sweepFit})

        # Measured, not assumed: the recess floors are where they should be.
        require(is_outside('Car', textCentreX, carHalfW - stripeDepth / 2.0, textCentreZ)
                and is_inside('Car', textCentreX, carHalfW - stripeDepth - 0.3, textCentreZ),
                'The red stripe recess is not {:.1f} mm deep on the display flank.'
                .format(stripeDepth))
        require(is_outside('Car', arrayX0 - 10.0, -(carHalfW - bandDepth / 2.0),
                           (bandZ0 + bandZ1) / 2.0),
                'The window band did not reach the back flank.')

        # ------------------------------------------ raised details: frames etc.
        # The cube frames, the coupler block on the tail and the two red tail
        # lights. All raised, so each is its own colour region with real edges,
        # and all joined in one combine.
        raised = []
        for k, xc in enumerate(displayCentres):
            raised.append(box_body('Frame_{}'.format(k),
                                   xc - frameW / 2.0, xc + frameW / 2.0,
                                   slotFloorY - 1.0, frameFaceY,
                                   frameZ0, frameZ1))
        # The coupler's underside slopes at 45 degrees: the top prints standing
        # up, and a square block would be a 3 mm ledge over air.
        raised.append(side_prism('Coupler', [
            (carX0 + 2.0, couplerZ0), (carX0, couplerZ0),
            (carX0 - couplerProud, couplerZ0 + couplerProud),
            (carX0 - couplerProud, couplerZ1), (carX0 + 2.0, couplerZ1)],
            couplerHalfW))
        for k, sgn in enumerate((-1.0, 1.0)):
            raised.append(box_body('Light_{}'.format(k), carX0 - lightProud, carX0 + 1.5,
                                   sgn * lightY - lightHalfW, sgn * lightY + lightHalfW,
                                   lightZ0, lightZ1))

        raisedBefore = volume_mm3('Car')
        join_into('Car', raised)
        # The lights are the only raised faces below the coupler on the tail.
        paint_faces(lastFeature[0], 'black',
                    lambda f: 'red' if (face_point(f)[0] < carX0 + 1.5
                                        and face_point(f)[2] < couplerZ0 - 0.5) else 'black')
        raisedAdded = volume_mm3('Car') - raisedBefore
        require(raisedAdded > 50.0,
                'The frames, coupler and tail lights added only {:.0f} mm3.'.format(raisedAdded))
        require(is_inside('Car', displayCentres[0], frameFaceY - 0.3, frameZ1 - 0.5),
                'The cube frames are not standing on the display flank.')

        # ----------------------------------------------- pockets (slots etc.)
        def cut_pockets(sketchName, planeName, basePlane, axis, coord, depth, rects,
                        targetName, axes):
            """rects in GLOBAL mm along axes[0]/axes[1], on a plane at `coord` on
            `axis`. Cut symmetrically about that mid-depth plane so the direction
            cannot come out backwards; the probed symmetric_value keeps the total
            depth right either way."""
            plane = plane_through(planeName, basePlane, axis, coord)
            sk = root.sketches.add(plane)
            sk.name = sketchName
            to_local = local_mapper(sk, axes)
            sp = sk.sketchPoints
            lines = sk.sketchCurves.sketchLines
            for a0, a1, b0, b1 in rects:
                bl = sp.add(to_local(a0, b0))
                br = sp.add(to_local(a1, b0))
                tr = sp.add(to_local(a1, b1))
                tl = sp.add(to_local(a0, b1))
                lines.addByTwoPoints(bl, br)
                lines.addByTwoPoints(br, tr)
                lines.addByTwoPoints(tr, tl)
                lines.addByTwoPoints(tl, bl)
            require(sk.profiles.count == len(rects),
                    'Sketch "{}" produced {} profiles, expected {}.'
                    .format(sketchName, sk.profiles.count, len(rects)))
            ei = extrudes.createInput(all_profiles(sk),
                                      adsk.fusion.FeatureOperations.CutFeatureOperation)
            ei.participantBodies = [body_named(targetName)]
            ei.setDistanceExtent(True, adsk.core.ValueInput.createByString(
                '{} mm'.format(symmetric_value(depth))))
            return extrudes.add(ei)

        # Display slots, cut through the frames. One pocket per cube rather than
        # one wide cavity, so a cube cannot drift sideways.
        slotsBefore = volume_mm3('Car')
        slotFeat = cut_pockets('Cut_Slots', 'Cut_P_Slots', root.xZConstructionPlane,
                               'y', frameFaceY - slotDepth / 2.0, slotDepth,
                               [(xc - slotW / 2.0, xc + slotW / 2.0, slotZ0, slotZ1)
                                for xc in displayCentres],
                               'Car', ('x', 'z'))
        paint_faces(slotFeat, 'black')
        slotsCut = slotsBefore - volume_mm3('Car')
        slotsWant = cubeN * slotW * slotW * slotDepth
        require(0.9 * slotsWant < slotsCut < 1.02 * slotsWant,
                'The display slots took out {:.0f} mm3 against {:.0f} expected -- '
                'they are the wrong depth or off the frames.'.format(slotsCut, slotsWant))
        for xc in displayCentres:
            require(is_outside('Car', xc, slotFloorY + 1.0, (slotZ0 + slotZ1) / 2.0)
                    and is_inside('Car', xc, slotFloorY - 1.0, (slotZ0 + slotZ1) / 2.0),
                    'The slot at x {:.1f} is not on the display side with its floor at '
                    'y {:.1f}.'.format(xc, slotFloorY))

        # ------------------------------------------------- the beam channel
        # Under the belly, straight like the beam, so the car sits on the
        # beam along its whole length. Run past both ends of the car.
        channelX = carX1 + 5.0
        channelBefore = volume_mm3('Car')
        channelTool = side_prism('Channel', [
            (-channelX, beam_top(-channelX)), (channelX, beam_top(channelX)),
            (channelX, -3.0), (-channelX, -3.0)],
            channelHalfW)
        cut_from('Car', [channelTool])
        crestOff = 10.0               # on the flat run, clear of the pins
        require(volume_mm3('Car') < channelBefore - 100.0
                and is_outside('Car', crestOff, 0.0, beam_top(crestOff) - 0.4)
                and is_inside('Car', crestOff, 0.0, beam_top(crestOff) + 0.4)
                and is_outside('Car', crestOff, channelHalfW - 0.2, 1.0)
                and is_inside('Car', 0.0, channelHalfW + 1.0, 1.0),
                'The beam channel is not {:.1f} mm up into the belly.'
                .format(beamCrestZ))

        # ---------------------------------------------- spare cube, tail pocket
        cut_pockets('Cut_Spare', 'Cut_P_Spare', root.yZConstructionPlane,
                    'x', carX0 + spareDepth / 2.0, spareDepth,
                    [(-sparePocketSize / 2.0, sparePocketSize / 2.0, spareZ0, spareZ1)],
                    'Car', ('y', 'z'))
        require(is_outside('Car', carX0 + spareDepth - 1.0, 0.0, spareCentreZ)
                and is_inside('Car', carX0 + spareDepth + 1.0, 0.0, spareCentreZ),
                'The spare pocket is not {:.1f} mm deep in the tail face.'.format(spareDepth))

        # Finger notches in the pocket's top and bottom walls. Clearance lets
        # the cube fall out, but it sits 1.2 mm in, so there is nothing to grip
        # without them. A round where the finger goes, then 45-degree flanks to
        # the pocket wall. The bottom one is in the car bottom and opens upward
        # in print; the top one is in the car top, where the round is a small
        # arch over the 45-degree flanks.
        gripSk = root.sketches.add(plane_through(
            'Cut_P_SpareGrip', root.yZConstructionPlane, 'x', carX0 + spareGripDepth / 2.0))
        gripSk.name = 'Cut_SpareGrip'
        gripLocal = local_mapper(gripSk, ('y', 'z'))
        gripLines = gripSk.sketchCurves.sketchLines
        gripTan = spareGripR / math.sqrt(2.0)
        for wallZ, into in ((spareZ0, -1.0), (spareZ1, 1.0)):
            pts = [gripSk.sketchPoints.add(gripLocal(y, wallZ + into * dz)) for y, dz in (
                (-spareGripHalfW, -1.0), (-spareGripHalfW, 0.0), (-gripTan, gripTan),
                (gripTan, gripTan), (spareGripHalfW, 0.0), (spareGripHalfW, -1.0))]
            for i in (0, 1, 3, 4, 5):
                gripLines.addByTwoPoints(pts[i], pts[(i + 1) % 6])
            gripSk.sketchCurves.sketchArcs.addByThreePoints(
                pts[2], gripLocal(0.0, wallZ + into * spareGripR), pts[3])
        require(gripSk.profiles.count == 2,
                'Finger notch sketch produced {} profiles, expected 2.'
                .format(gripSk.profiles.count))
        gripIn = extrudes.createInput(all_profiles(gripSk),
                                      adsk.fusion.FeatureOperations.CutFeatureOperation)
        gripIn.participantBodies = [body_named('Car')]
        gripIn.setDistanceExtent(True, adsk.core.ValueInput.createByString(
            '{} mm'.format(symmetric_value(spareGripDepth))))
        extrudes.add(gripIn)
        for wallZ, into in ((spareZ0, -1.0), (spareZ1, 1.0)):
            require(is_outside('Car', carX0 + 1.0, 0.0, wallZ + into * (spareGripR - 0.3))
                    and is_inside('Car', carX0 + 1.0, 0.0, wallZ + into * (spareGripR + 0.3))
                    and is_inside('Car', carX0 + spareGripDepth + 0.5, 0.0, wallZ + into * 1.0)
                    and is_inside('Car', carX0 + 1.0, spareGripHalfW + 0.3, wallZ + into * 0.3),
                    'The finger notch at z {:.1f} is not {:.0f} mm deep and {:.0f} mm long.'
                    .format(wallZ, spareGripR, spareGripDepth))

        # ========================================================== lettering
        # Raised, and joined into the car as one body. A flush inlay is
        # invisible in Fusion and exports as a loose body per glyph that the
        # slicer scatters across the plate.
        #
        # The flank is flat here, so the whole line moves as one rigid block
        # on one frame. The reading direction comes out of r = up x n, which is
        # always right-handed -- so the line cannot come out mirrored on one
        # side, which is exactly how the ship's reverse side went wrong.
        textThick = textBite + textRise
        stripeFloor = carHalfW - stripeDepth

        for sideTag in textSides:
            require(sideTag in CAR_TEXT and CAR_TEXT[sideTag].strip(),
                    'CAR_TEXT has nothing for side {}.'.format(sideTag))

        seedSize = {}
        for sideTag in textSides:
            f, sk = text_tool('Text_Fit_{}'.format(sideTag),
                              CAR_TEXT[sideTag], textSeedEm, 1.0, textFont)
            lo, hi = bodies_extent([f])
            seedSize[sideTag] = (hi[0] - lo[0], hi[1] - lo[1])
            drop(f, 'lettering fit extrude for side ' + sideTag)
            drop(sk, 'lettering fit sketch for side ' + sideTag)

        sideScale = {}
        for sideTag, (w, h) in seedSize.items():
            require(w > 0.1 and h > 0.1,
                    'Lettering fit measured nothing for side {}.'.format(sideTag))
            sideScale[sideTag] = min(textRun / w, textMaxH / h)
        if textSharedScale:
            common = min(sideScale.values())
            sideScale = dict((k, common) for k in sideScale)
        textEm = dict((k, textSeedEm * v) for k, v in sideScale.items())
        for sideTag, em in textEm.items():
            require(em > 1.0,
                    'Lettering fit produced a degenerate size on side {}.'.format(sideTag))
        textInk = dict((k, (seedSize[k][0] * sideScale[k], seedSize[k][1] * sideScale[k]))
                       for k in sideScale)

        textStrokes, textGlyphCounts, textFitRatios = [], [], []
        for sideTag in textSides:
            sideSign = 1.0 if sideTag == 'D' else -1.0

            feat, _ = text_tool('Text_{}'.format(sideTag),
                                CAR_TEXT[sideTag], textEm[sideTag], textThick, textFont)
            require(feat.bodies.count >= textMinGlyphs,
                    'The lettering on side {} came out as {} solid(s). A script that '
                    'joins into one piece gives the fit nothing to measure.'
                    .format(sideTag, feat.bodies.count))
            textGlyphCounts.append(feat.bodies.count)

            # Stroke width, measured before the join consumes the glyphs. For a
            # thin prism of thickness t, volume/t is the ink area and
            # (surface - 2*ink)/t is the outline, about twice the stroke run.
            glyphBodies = tool_bodies([feat])
            volMM = sum(b.physicalProperties.volume for b in glyphBodies) * 1000.0
            areaMM = sum(b.physicalProperties.area for b in glyphBodies) * 100.0
            inkArea = volMM / textThick
            outline = (areaMM - 2.0 * inkArea) / textThick
            require(inkArea > 1.0 and outline > 1.0,
                    'Lettering on side {} measured as nonsense.'.format(sideTag))
            strokeW = 2.0 * inkArea / outline
            require(strokeW > textMinStroke,
                    'Lettering strokes average about {:.2f} mm, under the {:.2f} mm a '
                    '0.4 mm nozzle can lay down at all. Shorten the text or raise '
                    'the stripe band.'.format(strokeW, textMinStroke))
            textStrokes.append(strokeW)

            # Centre the block on the ink, not on the text box, then move the
            # whole thing onto the flank in one go.
            lo, hi = bodies_extent([feat])
            translate([feat], -(lo[0] + hi[0]) / 2.0, -(lo[1] + hi[1]) / 2.0)

            nvec = (0.0, sideSign, 0.0)            # outward normal
            uvec = (0.0, 0.0, 1.0)                 # up
            rvec = (uvec[1] * nvec[2] - uvec[2] * nvec[1],
                    uvec[2] * nvec[0] - uvec[0] * nvec[2],
                    uvec[0] * nvec[1] - uvec[1] * nvec[0])   # up x n, right-handed
            origin = (textCentreX,
                      sideSign * (stripeFloor - textBite),
                      textCentreZ)
            matrix = adsk.core.Matrix3D.create()
            require(matrix.setWithCoordinateSystem(
                        adsk.core.Point3D.create(mm(origin[0]), mm(origin[1]), mm(origin[2])),
                        adsk.core.Vector3D.create(rvec[0], rvec[1], rvec[2]),
                        adsk.core.Vector3D.create(uvec[0], uvec[1], uvec[2]),
                        adsk.core.Vector3D.create(nvec[0], nvec[1], nvec[2])),
                    'Could not build the lettering frame for side {}.'.format(sideTag))
            move_by_matrix([feat], matrix)

            before = volume_mm3('Car')
            join_into('Car', tool_bodies([feat]))
            added = volume_mm3('Car') - before
            # Only the part above the stripe floor is new material; the bite was
            # already car. The ratio is reported rather than pinned -- it also
            # carries how well the inset-solid model matched the real surface.
            expect = inkArea * textRise
            ratio = added / expect if expect > 1.0e-9 else 0.0
            textFitRatios.append(ratio)
            require(0.25 < ratio < 2.2,
                    'Lettering on side {} added {:.0f} mm3 against {:.0f} expected '
                    '(x{:.2f}) -- the glyphs are not sitting on the flank.'
                    .format(sideTag, added, expect, ratio))

        textStrokeMin = min(textStrokes) if textStrokes else 0.0

        # ====================================================== split the car
        PIN_BODIES = []

        def exact_mm3(body):
            """Volume to within a few mm3: the default estimate wanders by tens."""
            return body.getPhysicalProperties(
                adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume * 1000.0

        def pin_joint(tag, basePlane, axis, coord, axes, points, depth, parts):
            """Pins across a joint: a socket depth + socketExtra deep on either side
            of the joint plane, at `coord` on `axis`, through every part named,
            and a loose pin 2 * depth long in each, so every part still lies flat
            on the bed. Cut symmetric about the joint, so the direction cannot
            come out backwards. points are global (a, b) along axes."""
            plane = plane_through('Cut_P_Pins_' + tag, basePlane, axis, coord)
            for what, radius, length in (('Cut_Sockets_', socketR, depth + socketExtra),
                                         ('Pin_Sketch_', pinDia / 2.0, depth)):
                sk = root.sketches.add(plane)
                sk.name = what + tag
                to_local = local_mapper(sk, axes)
                for a, b in points:
                    sk.sketchCurves.sketchCircles.addByCenterRadius(to_local(a, b), mm(radius))
                require(sk.profiles.count == len(points),
                        'Sketch "{}" produced {} profiles, expected {}.'
                        .format(sk.name, sk.profiles.count, len(points)))
                cutting = what.startswith('Cut')
                ei = extrudes.createInput(all_profiles(sk), (
                    adsk.fusion.FeatureOperations.CutFeatureOperation if cutting else
                    adsk.fusion.FeatureOperations.NewBodyFeatureOperation))
                if cutting:
                    ei.participantBodies = [body_named(n) for n in parts]
                    before = sum(exact_mm3(body_named(n)) for n in parts)
                ei.setDistanceExtent(True, adsk.core.ValueInput.createByString(
                    '{} mm'.format(symmetric_value(2.0 * length))))
                feat = extrudes.add(ei)
                if cutting:
                    removed = before - sum(exact_mm3(body_named(n)) for n in parts)
                    want = len(points) * math.pi * socketR ** 2 * 2.0 * length
                    require(abs(removed - want) < 0.1 * want,
                            'The {} pin sockets took out {:.0f} mm3 against {:.0f} expected.'
                            .format(tag, removed, want))
                else:
                    require(feat.bodies.count == len(points),
                            'The {} pins came out as {} bodies.'.format(tag, feat.bodies.count))
                    for i in range(feat.bodies.count):
                        PIN_BODIES.append('Pin_{}_{}'.format(tag, i + 1))
                        feat.bodies.item(i).name = PIN_BODIES[-1]
                        paint_body(PIN_BODIES[-1], 'white')

        if SPLIT_CAR:
            # Cut where the colours meet (see the note at the top of the file):
            # across the red stripe's top edge, then along its lower edge -- flat,
            # then the sweep up to the tail, drawn through the very points the
            # stripe's own recess was, so each cut lands on the stripe's step.
            def exact(name):
                return exact_mm3(body_named(name))

            carVolume = exact('Car')
            sbf = root.features.splitBodyFeatures

            def split_in_two(bodyName, plane, axis, lowName, highName):
                """Split a body by a plane into exactly two pieces, named by which
                side of the plane each lies along `axis`."""
                feat = sbf.add(sbf.createInput(body_named(bodyName), plane, True))
                require(feat.bodies.count == 2,
                        'Splitting {} gave {} pieces, expected 2.'
                        .format(bodyName, feat.bodies.count))
                k = AXIS_NAMES.index(axis)
                pieces = []
                for i in range(feat.bodies.count):
                    lo, hi = extent_of([feat.bodies.item(i)])
                    pieces.append(((lo[k] + hi[k]) / 2.0, feat.bodies.item(i)))
                pieces.sort(key=lambda p: p[0])
                pieces[0][1].name = lowName
                pieces[1][1].name = highName

            split_in_two('Car', plane_at(stripeZ1), 'z', 'Car_Lower', 'Car_Top')
            lowerVolume = exact('Car_Lower')
            require(abs(lowerVolume + exact('Car_Top') - carVolume) < 1.0e-4 * carVolume,
                    'Cutting the top off changed the car\'s volume.')

            # The red is what of the lower piece lies above its lower edge: a copy
            # keeps what the tool holds, and the original keeps the rest.
            redTool = side_prism('RedCut', [
                (carX0, sweepZ), (sweepX0, stripeZ0), (frontX, stripeZ0),
                (frontX, stripeZ1 + 5.0), (backX, stripeZ1 + 5.0), (backX, sweepZ)],
                carHalfW + liveryOver, {0: sweepFit})
            copyFeat = root.features.copyPasteBodies.add(body_named('Car_Lower'))
            require(copyFeat.bodies.count == 1,
                    'Copying the lower car gave {} bodies.'.format(copyFeat.bodies.count))
            copyFeat.bodies.item(0).name = 'Car_Red'
            combine_bodies('Car_Red', [redTool],
                           adsk.fusion.FeatureOperations.IntersectFeatureOperation, True)
            # Kept, the tool is listed among the feature's bodies, so count by name.
            red = [b for b in root.bRepBodies
                   if b.name == 'Car_Red' or b.name.startswith('Car_Red (')]
            bottom = cut_from('Car_Lower', [body_named(redTool.name)])
            require(len(red) == 1 and len(bottom) == 1,
                    'Cutting the red from the bottom left {} red and {} bottom pieces.'
                    .format(len(red), len(bottom)))
            bottom[0].name = 'Car_Bottom'
            require(abs(exact('Car_Red') + exact('Car_Bottom') - lowerVolume) < 1.0e-4 * lowerVolume,
                    'Cutting the red from the bottom changed their volume.')

            # The seat: the red halves stand seatDepth down into a recess in the
            # bottom's top face. Both are the car rebuilt inset -- by the stripe
            # depth for the red's own floor, and by seatGap less for the recess --
            # so they follow the flank, the nose and the rounds alike.
            build_car('Inner_Tongue', stripeDepth)
            tongue = combine_bodies('Inner_Tongue', [box_body(
                'TongueSlab', seatX0 + seatGap, frontX, -carHalfW - 2.0, carHalfW + 2.0,
                stripeZ0 - seatDepth, stripeZ0)],
                adsk.fusion.FeatureOperations.IntersectFeatureOperation)
            tongueVolume = sum(exact_mm3(b) for b in tongue)
            before = exact('Car_Red')
            join_into('Car_Red', tongue)
            require(abs(exact('Car_Red') - before - tongueVolume) < 0.01 * tongueVolume
                    and tongueVolume > 1000.0,
                    'The red\'s {:.0f} mm3 tongue did not join on cleanly.'.format(tongueVolume))
            build_car('Inner_Seat', stripeDepth - seatGap)
            seat = combine_bodies('Inner_Seat', [box_body(
                'SeatSlab', seatX0, frontX, -carHalfW - 2.0, carHalfW + 2.0,
                stripeZ0 - seatDepth, stripeZ0 + 1.0)],
                adsk.fusion.FeatureOperations.IntersectFeatureOperation)
            before = exact('Car_Bottom')
            cut_from('Car_Bottom', seat)
            seatVolume = before - exact('Car_Bottom')
            require(0.99 * tongueVolume < seatVolume < 1.05 * tongueVolume,
                    'The recess took {:.0f} mm3 out of the bottom against a {:.0f} mm3 '
                    'tongue.'.format(seatVolume, tongueVolume))

            # The lip at the top joint: a rib along the red's top edge, lipRib wide
            # and seatDepth tall, flush with the red's face, and a groove for it in
            # the top's underside, seatGap clear all round, behind a white lip as
            # wide as the bottom's rim. Each is the space between two of the car's
            # insets, cut to height -- and the rib stops at the spare pocket.
            def inset_ring(tag, outer, inner, z0, z1):
                build_car('Inner_' + tag, outer)
                build_car('Inner_' + tag + '_In', inner)
                cut_from('Inner_' + tag, [body_named('Inner_' + tag + '_In')])
                return combine_bodies('Inner_' + tag, [box_body(
                    tag + 'Slab', carX0 - liveryOver, carX1 + liveryOver,
                    -carHalfW - 2.0, carHalfW + 2.0, z0, z1)],
                    adsk.fusion.FeatureOperations.IntersectFeatureOperation)

            rib = inset_ring('Rib', stripeDepth, stripeDepth + lipRib,
                             stripeZ1, stripeZ1 + seatDepth)
            require(len(rib) == 1, 'The rib came out in {} pieces.'.format(len(rib)))
            rib = cut_from(rib[0].name, [box_body(
                'RibPocket', carX0 - liveryOver, carX0 + spareDepth,
                -sparePocketSize / 2.0, sparePocketSize / 2.0,
                stripeZ1 - 1.0, stripeZ1 + seatDepth + 1.0)])
            ribVolume = sum(exact_mm3(b) for b in rib)
            before = exact('Car_Red')
            join_into('Car_Red', rib)
            require(abs(exact('Car_Red') - before - ribVolume) < 0.02 * ribVolume
                    and ribVolume > 50.0,
                    'The red\'s {:.0f} mm3 rib did not join on cleanly.'.format(ribVolume))
            groove = inset_ring('Groove', stripeDepth - seatGap, stripeDepth + lipRib + seatGap,
                                stripeZ1 - 1.0, stripeZ1 + seatDepth)
            before = exact('Car_Top')
            cut_from('Car_Top', groove)
            grooveVolume = before - exact('Car_Top')
            require(ribVolume < grooveVolume < 1.6 * ribVolume,
                    'The groove took {:.0f} mm3 out of the top against a {:.0f} mm3 rib.'
                    .format(grooveVolume, ribVolume))
            ribY = carHalfW - stripeDepth - lipRib / 2.0
            lipY = carHalfW - (stripeDepth - seatGap) / 2.0
            require(is_inside('Car_Red', 0.0, -ribY, stripeZ1 + seatDepth / 2.0)
                    and is_outside('Car_Top', 0.0, -ribY, stripeZ1 + seatDepth / 2.0)
                    and is_inside('Car_Top', 0.0, -lipY, stripeZ1 + seatDepth / 2.0)
                    and is_inside('Car_Top', 0.0, -(ribY - lipRib), stripeZ1 + seatDepth / 2.0),
                    'The red\'s rib does not sit in a groove behind a white lip.')

            split_in_two('Car_Red', root.xZConstructionPlane, 'y', 'Car_Red_Back', 'Car_Red_Display')

            # Every joint pinned: the red halves to each other, to the bottom and
            # to the top.
            redHalves = ['Car_Red_Display', 'Car_Red_Back']
            pin_joint('Red', root.xZConstructionPlane, 'y', 0.0, ('x', 'z'),
                      RED_PIN_XZ, pinH, redHalves)
            pin_joint('Seat', root.xYConstructionPlane, 'z', seatJoint, ('x', 'y'),
                      SEAT_PIN_XY, pinH, redHalves + ['Car_Bottom'])
            pin_joint('Top', root.xYConstructionPlane, 'z', stripeZ1, ('x', 'y'),
                      TOP_PIN_XY, pinH, redHalves + ['Car_Top'])
            for px, pz in RED_PIN_XZ:
                require(all(is_outside(n, px, sgn * pinH, pz) and
                            is_inside(n, px, sgn * (pinH + socketExtra + 0.5), pz)
                            for n, sgn in (('Car_Red_Display', 1.0), ('Car_Red_Back', -1.0))),
                        'The pin socket at x {:.0f} is not in both red halves.'.format(px))
            for pins, z, other in ((SEAT_PIN_XY, seatJoint, 'Car_Bottom'),
                                   (TOP_PIN_XY, stripeZ1, 'Car_Top')):
                up = 1.0 if other == 'Car_Top' else -1.0
                for (px, py) in pins:
                    redHalf = 'Car_Red_Display' if py > 0.0 else 'Car_Red_Back'
                    require(is_outside(redHalf, px, py, z - up * pinH)
                            and is_inside(redHalf, px, py, z - up * (pinH + socketExtra + 0.5))
                            and is_outside(other, px, py, z + up * pinH)
                            and is_inside(other, px, py, z + up * (pinH + socketExtra + 0.5)),
                            'The pin socket at x {:.0f}, y {:.0f} is not in both the red and '
                            '{}.'.format(px, py, other))

            # Each part is where it should be: the bottom under the red's lower
            # edge, the red's tongue in the recess inside a white rim, the red
            # halves either side of the middle, the top above the stripe.
            tailX = carX0 + 2.0
            require(is_inside('Car_Bottom', 0.0, 15.0, stripeZ0 - seatDepth - 0.2)
                    and is_outside('Car_Bottom', 0.0, 15.0, stripeZ0 - seatDepth / 2.0)
                    and is_inside('Car_Red_Display', 0.0, 15.0, stripeZ0 - seatDepth / 2.0)
                    and is_inside('Car_Red_Back', 0.0, -15.0, stripeZ0 - seatDepth / 2.0)
                    and is_inside('Car_Bottom', 0.0, carHalfW - 0.3, stripeZ0 - seatDepth / 2.0)
                    and is_inside('Car_Bottom', 0.0, -(carHalfW - 0.3), stripeZ0 - seatDepth / 2.0),
                    'The red halves do not stand in a recess inside a white rim.')
            require(is_inside('Car_Bottom', tailX, 15.0, red_floor(tailX) - 0.5)
                    and is_inside('Car_Red_Display', tailX, 15.0, red_floor(tailX) + 0.5)
                    and is_inside('Car_Red_Display', 0.0, 3.0, (stripeZ0 + stripeZ1) / 2.0)
                    and is_inside('Car_Red_Back', 0.0, -3.0, (stripeZ0 + stripeZ1) / 2.0)
                    and is_inside('Car_Top', 0.0, -15.0, stripeZ1 + 0.5)
                    and is_inside('Car_Top', 0.0, -15.0, bodyZ1 - 2.0),
                    'The car did not come apart along the red stripe as it should.')

            # Colours per part. The bottom is white throughout: its top took the
            # stripe's steps, painted red, with it. A red half is red all over but
            # the letter tops, which go gold at the end. The top's underside is
            # white, and black under the frames: in print the first layer takes
            # the colour of the face on the bed, whatever the walls above it are.
            if PREVIEW_COLOURS:
                try:
                    bottomBody = body_named('Car_Bottom')
                    bottomBody.appearance = paint('white')
                    for i in range(bottomBody.faces.count):
                        bottomBody.faces.item(i).appearance = paint('white')
                    for n in ('Car_Red_Display', 'Car_Red_Back'):
                        b = body_named(n)
                        b.appearance = paint('red')
                        for i in range(b.faces.count):
                            f = b.faces.item(i)
                            if (f.appearanceSourceType ==
                                    adsk.core.AppearanceSourceTypes.OverrideAppearanceSource
                                    and f.appearance.name != paint('red').name):
                                f.appearance = paint('red')

                    def top_underside():
                        top = body_named('Car_Top')
                        out = []
                        for i in range(top.faces.count):
                            f = top.faces.item(i)
                            bb = f.boundingBox
                            if max(abs(bb.minPoint.z * 10.0 - stripeZ1),
                                   abs(bb.maxPoint.z * 10.0 - stripeZ1)) < 0.01:
                                out.append(f)
                        return out
                    feet = adsk.core.ObjectCollection.create()
                    for f in top_underside():
                        feet.add(f)
                    sfi = root.features.splitFaceFeatures.createInput(
                        feet, plane_through('Cut_P_FrameFeet', root.xZConstructionPlane,
                                            'y', carHalfW + 0.1), True)
                    root.features.splitFaceFeatures.add(sfi)
                    for f in top_underside():
                        f.appearance = paint('black' if face_point(f)[1] > carHalfW else 'white')
                except Exception as ex:
                    paintTrouble.append('parts: {}'.format(ex))
            CAR_BODIES = ['Car_Bottom', 'Car_Red_Display', 'Car_Red_Back', 'Car_Top']
        else:
            CAR_BODIES = ['Car']

        # ========================================================== the cubes
        cubeBodies = []
        cubeCentres = {}

        def make_cube(name, x0, y0, zBase):
            sk = root.sketches.add(plane_at(zBase))
            sk.name = 'Cube_Sk_{}'.format(name)
            to_local = local_mapper(sk, ('x', 'y'))
            sp = sk.sketchPoints
            bl = sp.add(to_local(x0, y0))
            br = sp.add(to_local(x0 + cube, y0))
            tr = sp.add(to_local(x0 + cube, y0 + cube))
            tl = sp.add(to_local(x0, y0 + cube))
            lines = sk.sketchCurves.sketchLines
            lines.addByTwoPoints(bl, br)
            lines.addByTwoPoints(br, tr)
            lines.addByTwoPoints(tr, tl)
            lines.addByTwoPoints(tl, bl)
            require(sk.profiles.count == 1, 'Cube sketch "{}" did not close.'.format(sk.name))
            ei = extrudes.createInput(
                sk.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            ei.setDistanceExtent(False, adsk.core.ValueInput.createByString('cubeSize'))
            body = extrudes.add(ei).bodies.item(0)
            body.name = 'Cube_{}'.format(name)
            cubeBodies.append(body)
            cubeCentres[body.name] = (x0 + cube / 2.0, y0 + cube / 2.0, zBase + cube / 2.0)
            lo, hi = extent_of([body])
            require(abs(lo[2] - zBase) < 0.05 and abs(hi[2] - (zBase + cube)) < 0.05,
                    'Cube "{}" extruded the wrong way.'.format(name))
            return body

        for i, xc in enumerate(displayCentres):
            make_cube(str(i + 1), xc - cube / 2.0, slotFloorY, slotZ0 + clearance)
        make_cube('4_Spare', carX0 + spareDepth - cube, -cube / 2.0,
                  spareZ0 + spareClearance / 2.0)

        for body in cubeBodies:
            fillet_edges(list(body.edges), 'cubeEdgeFillet', 'cube edge')

        # ------------------------------------------------- digits on every face
        # Every one of the 24 faces carries a digit, and that is forced rather
        # than chosen: 000/111/222/333 are all under 365, so 0-3 each need three
        # cubes; 344/355/266/277/288/299 are too, so 4-9 each need two. That is
        # 4*3 + 6*2 = 24 faces against 24 available. No face can be left blank --
        # and three cubes could not do it at all, which is why there are four.
        CUBE_DIGITS = [
            ('Cube_1',       'A', ['1', '2', '3', '4', '5', '6']),
            ('Cube_2',       'B', ['0', '2', '3', '4', '7', '8']),
            ('Cube_3',       'C', ['0', '1', '3', '5', '7', '9']),
            ('Cube_4_Spare', 'D', ['0', '1', '2', '6', '8', '9']),
        ]

        # digits[i] lands on FACE_ORDER[i]. The in-plane right vector is derived
        # as up x normal, which is always right-handed, so no face can come out
        # mirrored -- that failure mode is designed out rather than tested for.
        FACE_ORDER = ['-Y', '+Y', '+X', '-X', '+Z', '-Z']
        FACE_FRAME = {
            '+X': ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
            '-X': ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
            '+Y': ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            '-Y': ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
            '+Z': ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
            '-Z': ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
        }

        def validate_digit_sets():
            """Prove the digit sets can still render every value 0-365."""
            sets = {}
            for bodyName, label, digits in CUBE_DIGITS:
                require(len(digits) == 6,
                        'Cube {} has {} faces, needs 6.'.format(label, len(digits)))
                require(len(set(digits)) == 6, 'Cube {} repeats a digit.'.format(label))
                sets[label] = set(digits)
            require(len(sets) == 4, 'Expected four distinctly labelled cubes.')
            labels = list(sets.keys())
            worstN, worstCount = None, None
            for n in range(0, 366):
                want = list('{:03d}'.format(n))
                count = 0
                for combo in permutations(labels, 3):
                    if all(want[i] in sets[combo[i]] for i in range(3)):
                        count += 1
                require(count > 0, 'These digit sets cannot display {:d}.'.format(n))
                if worstCount is None or count < worstCount:
                    worstN, worstCount = n, count
            return worstN, worstCount

        worstN, worstCount = validate_digit_sets()

        markHead = mickHead * markScale
        markEar = mickEar * markScale
        markOffset = earOffset * markScale
        markTop = markCentreY + markOffset * EAR_COS + markEar / 2.0
        markBot = markCentreY - markHead / 2.0
        faceSafe = cube / 2.0 - cubeEdgeFillet
        require(markBot > -faceSafe,
                'Cube Mickey reaches {:.2f} mm, past the {:.2f} mm safe face area.'
                .format(markBot, faceSafe))

        cubeToolHeight = digitRecess + toolOvershoot

        # Calibration. Ask the font how tall it actually draws instead of
        # assuming some fraction of the em size -- a script face like Waltograph
        # has nothing like text-face metrics.
        calFeat, calSk = text_tool('Cube_Digit_Calibration', '0123456789',
                                   digitEmSeed, cubeToolHeight, digitFont)
        calLo, calHi = bodies_extent([calFeat])
        calH = calHi[1] - calLo[1]
        calW = calHi[0] - calLo[0]
        require(calH > 0.1, 'Calibration text measured no height.')
        require(calW > 4.0 * calH,
                'Calibration text wrapped onto more than one line, so its height '
                'is meaningless. Widen the box in text_tool.')
        digitEmHeight = digitEmSeed * digitInkHeight / calH
        require(0.2 * digitEmSeed < digitEmHeight < 5.0 * digitEmSeed,
                'Calibration wants a {:.1f} mm em to draw {:.1f} mm of ink, which '
                'is not credible -- check the font actually has numerals.'
                .format(digitEmHeight, digitInkHeight))
        drop(calFeat, 'the digit calibration extrude')
        drop(calSk, 'the digit calibration sketch')

        def mark_tool(sketchName):
            """Mickey, used as the 6/9 orientation mark. Straight prisms, no
            taper: on overlapping circles a taper shrinks the visible face until
            the ears only graze the head and it reads as three loose blobs."""
            sk = root.sketches.add(root.xYConstructionPlane)
            sk.name = sketchName
            circles = sk.sketchCurves.sketchCircles
            circles.addByCenterRadius(P(0.0, markCentreY), mm(markHead / 2.0))
            for sgn in (-1.0, 1.0):
                circles.addByCenterRadius(
                    P(sgn * markOffset * EAR_SIN, markCentreY + markOffset * EAR_COS),
                    mm(markEar / 2.0))
            require(sk.profiles.count > 0, 'Cube Mickey produced no profiles.')
            ei = extrudes.createInput(all_profiles(sk),
                                      adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            ei.setDistanceExtent(False, adsk.core.ValueInput.createByString(
                '{} mm'.format(cubeToolHeight)))
            return label_tool_bodies(extrudes.add(ei))

        inkSizes = []

        def engrave_face(bodyName, centre, faceKey, digit, withMark):
            anchorY = digitShiftMark if withMark else 0.0
            toolFeats = [text_tool('Cube_Digit_{}_{}'.format(bodyName, faceKey),
                                   digit, digitEmHeight, cubeToolHeight, digitFont)[0]]

            # Centre on the ink, not on the text box.
            lo, hi = bodies_extent(toolFeats)
            inkW, inkH = hi[0] - lo[0], hi[1] - lo[1]
            translate(toolFeats,
                      -(lo[0] + hi[0]) / 2.0,
                      anchorY - (lo[1] + hi[1]) / 2.0)
            inkSizes.append((inkW, inkH))

            top = anchorY + inkH / 2.0
            bot = anchorY - inkH / 2.0
            require(inkW / 2.0 < faceSafe and top < faceSafe and bot > -faceSafe,
                    'Digit "{}" measures {:.1f} x {:.1f} mm and spans y {:.1f} to '
                    '{:.1f}, outside the {:.1f} mm safe face area. Lower '
                    'digitInkHeight.'.format(digit, inkW, inkH, bot, top, faceSafe))
            if withMark:
                require(bot - markTop > digitMarkGap,
                        'Digit "{}" bottoms out at {:.2f} mm, only {:.2f} mm clear '
                        'of the Mickey at {:.2f} mm. Raise digitShiftMark or lower '
                        'markCentreY.'.format(digit, bot, bot - markTop, markTop))
                toolFeats.append(mark_tool(
                    'Cube_Mick_{}_{}'.format(bodyName, faceKey)))

            n, u = FACE_FRAME[faceKey]
            r = (u[1] * n[2] - u[2] * n[1],
                 u[2] * n[0] - u[0] * n[2],
                 u[0] * n[1] - u[1] * n[0])
            inset = cube / 2.0 - digitRecess
            matrix = adsk.core.Matrix3D.create()
            require(matrix.setWithCoordinateSystem(
                        adsk.core.Point3D.create(mm(centre[0] + n[0] * inset),
                                                 mm(centre[1] + n[1] * inset),
                                                 mm(centre[2] + n[2] * inset)),
                        adsk.core.Vector3D.create(r[0], r[1], r[2]),
                        adsk.core.Vector3D.create(u[0], u[1], u[2]),
                        adsk.core.Vector3D.create(n[0], n[1], n[2])),
                    'Could not build the placement frame for face ' + faceKey)
            move_by_matrix(toolFeats, matrix)

            target = body_named(bodyName)
            volBefore = target.physicalProperties.volume

            ci = combines.createInput(target, collect(toolFeats))
            ci.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
            ci.isKeepToolBodies = False
            combines.add(ci)

            target = root.bRepBodies.itemByName(bodyName)
            require(target is not None,
                    'Cube "{}" vanished while engraving {}.'.format(bodyName, digit))
            removed = volBefore - target.physicalProperties.volume
            # ~0.4% expected per face. Zero means the tool landed off the cube;
            # a large bite means the placement frame is wrong.
            require(removed > 1.0e-5,
                    'Engraving "{}" on face {} of {} removed nothing -- the tool '
                    'landed off the cube.'.format(digit, faceKey, bodyName))
            require(removed < 0.08 * volBefore,
                    'Engraving "{}" on face {} of {} removed {:.1f}% of the cube -- '
                    'the tool is mis-oriented.'
                    .format(digit, faceKey, bodyName, 100.0 * removed / volBefore))

        marked = []
        for bodyName, label, digits in CUBE_DIGITS:
            require(bodyName in cubeCentres,
                    'No cube named "{}" was built.'.format(bodyName))
            for faceKey, digit in zip(FACE_ORDER, digits):
                withMark = MARK_6_AND_9 and digit in ('6', '9')
                if withMark:
                    marked.append('{}:{}'.format(label, digit))
                engrave_face(bodyName, cubeCentres[bodyName], faceKey, digit, withMark)

        inkHiMin = min(h for w, h in inkSizes)
        inkHiMax = max(h for w, h in inkSizes)
        inkWidest = max(w for w, h in inkSizes)

        # ======================================================= beam and foot
        # The beam and its two pylons are one flat side profile -- the
        # straight beam and the two columns -- pushed out to the beam's width.
        # Printed lying on that side it has no overhang at all, and the colour
        # is a single grey.
        bL = beamHalfLen
        oX, iX = pylonX + pylonHalfX, pylonX - pylonHalfX   # column outer and inner edges
        side_prism('Beam', [
            (-bL, beam_top(-bL)), (bL, beam_top(bL)),
            (bL, beam_bottom(bL)), (oX, beam_bottom(oX)),
            (oX, pylonZ0), (iX, pylonZ0), (iX, beam_bottom(iX)),
            (-iX, beam_bottom(-iX)), (-iX, pylonZ0), (-oX, pylonZ0),
            (-oX, beam_bottom(-oX)), (-bL, beam_bottom(-bL))],
            beamHalfW, bodyName='Beam')
        paint_body('Beam', 'grey')
        beamLo, beamHi = extent_of([body_named('Beam')])
        require(abs((beamHi[0] - beamLo[0]) - 2.0 * bL) < 0.5
                and abs(beamHi[2] - beamCrestZ) < 0.05
                and abs(beamLo[2] - pylonZ0) < 0.05,
                'The beam came out {:.1f} long, z {:.2f} to {:.2f}; expected {:.1f} long, '
                'z {:.2f} to {:.2f}.'.format(beamHi[0] - beamLo[0], beamLo[2], beamHi[2],
                                             2.0 * bL, pylonZ0, beamCrestZ))
        require(is_outside('Beam', bL - 1.0, 0.0, beam_top(bL) + 0.5)
                and is_inside('Beam', bL - 1.0, 0.0, beam_top(bL) - 0.5),
                'The beam top is not straight.')
        # The car sits on the beam's top; across the channel it has beamFit of
        # slack, and nowhere does it run into the beam.
        tbm = adsk.fusion.TemporaryBRepManager.get()
        for carBody in CAR_BODIES:
            hit = tbm.copy(body_named('Beam'))
            tbm.booleanOperation(hit, tbm.copy(body_named(carBody)),
                                 adsk.fusion.BooleanTypes.IntersectionBooleanType)
            require(hit.volume * 1000.0 < 0.01,
                    'The beam runs {:.2f} mm3 into {}.'.format(hit.volume * 1000.0, carBody))
        require(is_outside(CAR_BODIES[0], crestOff, beamHalfW + 0.2, beamCrestZ - 1.0)
                and is_inside(CAR_BODIES[0], crestOff, channelHalfW + 0.2, beamCrestZ - 1.0),
                'The channel does not leave {:.1f} mm of slack round the beam.'.format(beamFit))
        require(all(is_inside('Beam', sgn * pylonX, 0.0, footTopZ - 1.0) for sgn in (-1.0, 1.0))
                and is_outside('Beam', 0.0, 0.0, footTopZ - 1.0),
                'The pylons are not standing at x +/-{:.0f}.'.format(pylonX))

        # Pins standing in the beam's top, beamPinH into the car's belly and
        # beamPinH into the beam, so the car goes on straight and stays there.
        pin_joint('Beam', root.xYConstructionPlane, 'z', beamCrestZ, ('x', 'y'),
                  [(px, 0.0) for px in BEAM_PIN_X], beamPinH, ['Beam', CAR_BODIES[0]])
        for px in BEAM_PIN_X:
            require(is_outside('Beam', px, 0.0, beamCrestZ - beamPinH)
                    and is_inside('Beam', px, 0.0, beamCrestZ - beamPinH - socketExtra - 0.5)
                    and is_outside(CAR_BODIES[0], px, 0.0, beamCrestZ + beamPinH)
                    and is_inside(CAR_BODIES[0], px, 0.0, beamSocketTop + 0.5),
                    'The beam pin socket at x {:.0f} is not in both the beam and the car.'
                    .format(px))

        # The foot: a plate with sloped sides, and a socket each column drops
        # into. Prints flat.
        footSk = root.sketches.add(plane_through(
            'Base_P_Foot', root.yZConstructionPlane, 'x', 0.0))
        footSk.name = 'Base_Foot'
        footLocal = local_mapper(footSk, ('y', 'z'))
        fsp = footSk.sketchPoints
        footPts = [fsp.add(footLocal(a, b)) for a, b in
                   [(-footHalfY, footZ0), (footHalfY, footZ0),
                    (footTopHalfY, footTopZ), (-footTopHalfY, footTopZ)]]
        for i in range(len(footPts)):
            footSk.sketchCurves.sketchLines.addByTwoPoints(
                footPts[i], footPts[(i + 1) % len(footPts)])
        extrude_symmetric(footSk, 2.0 * footHalfX, 'Foot')
        paint_body('Foot', 'grey')
        cut_pockets('Cut_Socket', 'Cut_P_Socket', root.xYConstructionPlane,
                    'z', footTopZ - socketDepth / 2.0, socketDepth,
                    [(sgn * pylonX - pylonHalfX - socketFit / 2.0,
                      sgn * pylonX + pylonHalfX + socketFit / 2.0,
                      -beamHalfW - socketFit / 2.0, beamHalfW + socketFit / 2.0)
                     for sgn in (-1.0, 1.0)],
                    'Foot', ('x', 'y'))
        for sgn in (-1.0, 1.0):
            require(is_outside('Foot', sgn * pylonX, 0.0, pylonZ0 + 0.3)
                    and is_inside('Foot', sgn * pylonX, 0.0, pylonZ0 - 0.3),
                    'The pylon socket at x {:.0f} is not {:.1f} mm deep in the foot.'
                    .format(sgn * pylonX, socketDepth))

        # ------------------------------------------- preview colours, finishing
        # The digits and the lettering run to thousands of faces, and every
        # face painted costs Fusion about 20 ms. So: each cube goes black as a
        # body and only its ~26 outer faces go back to white, and only the
        # letters' top faces go gold. Done last, when no later feature can
        # rework the faces.
        paintStarted = time.time()
        if PREVIEW_COLOURS:
            try:
                for bodyName in cubeCentres:
                    body = body_named(bodyName)
                    c = cubeCentres[bodyName]
                    body.appearance = paint('black')
                    for i in range(body.faces.count):
                        face = body.faces.item(i)
                        off = sorted((abs(v - w) for v, w in zip(face_point(face), c)), reverse=True)
                        # A face of the cube's skin reaches its outer plane, or
                        # is a round with two offsets past the flat. A digit
                        # face sits inside the plane, within the flat area.
                        if off[0] > cube / 2.0 - 0.05 or off[1] > faceSafe - 0.01:
                            face.appearance = paint('white')
                # Only the letters' tops. Their sides matter for printing --
                # lying on the split face, a letter's 1.2 mm of height IS its
                # sides -- but the glyph outlines run to thousands of faces and
                # painting them here took eleven minutes. The export converter
                # (to_bambu.py) paints the sides on the mesh instead, finding
                # the letters from these gold tops.
                letterTop = stripeFloor + textRise
                for bodyName in CAR_BODIES:
                    body = body_named(bodyName)
                    for i in range(body.faces.count):
                        face = body.faces.item(i)
                        x, y, z = face_point(face)
                        if abs(abs(y) - letterTop) < 0.02 and stripeZ0 < z < stripeZ1:
                            face.appearance = paint('gold')
            except Exception as ex:
                paintTrouble.append('finishing: {}'.format(ex))
        paintSeconds = time.time() - paintStarted

        # -------------------------------------------------------- body manifest
        # Anything beyond these is scratch geometry that survived, and it would
        # export as a stray part. Name it rather than ship it.
        EXPECTED_BODIES = CAR_BODIES + PIN_BODIES + ['Beam', 'Foot', 'Cube_1', 'Cube_2',
                                                     'Cube_3', 'Cube_4_Spare']
        actualBodies = sorted(b.name for b in root.bRepBodies)
        strays = [nm for nm in actualBodies if nm not in EXPECTED_BODIES]
        missing = [nm for nm in EXPECTED_BODIES if nm not in actualBodies]
        require(not missing,
                'These parts were never built: {}.'.format(', '.join(missing)))
        require(not strays,
                '{} stray bodies survived and would export as extra parts: {}{}'
                .format(len(strays), ', '.join(strays[:15]),
                        ' ...' if len(strays) > 15 else ''))

        allLo, allHi = extent_of([body_named(nm) for nm in EXPECTED_BODIES])

        # ------------------------------------------------------------------ tidy
        for s in root.sketches:
            try:
                s.isVisible = False
            except:
                pass

        if SPLIT_CAR:
            partsLine = ('Car in four parts along the red stripe: bottom {:.1f}, red halves '
                         '{:.1f} and {:.1f}, top {:.1f} cm3. The red stands {:.1f} mm down '
                         'into the bottom with {:.1f} mm a side, and its {:.1f} mm rib {:.1f} mm '
                         'up into a groove behind the top\'s lip.\n'
                         'Pins on every joint: {} between the red halves, {} to the bottom, {} to '
                         'the top, {} to the beam; {} in all.\n'
                         .format(*([volume_mm3(n) / 1000.0 for n in CAR_BODIES]
                                   + [seatDepth, seatGap, lipRib, seatDepth,
                                      len(RED_PIN_XZ), len(SEAT_PIN_XY), len(TOP_PIN_XY),
                                      len(BEAM_PIN_X), len(PIN_BODIES)])))
        else:
            partsLine = 'Car in one piece.\n'
        ui.messageBox('Built.\n\n'
                      'Symmetric extrude probed as {}.\n'
                      'Overall {:.1f} x {:.1f} x {:.1f} mm, measured. Car {:.0f} mm long, '
                      '{:.0f} wide, {:.0f} tall.\n'
                      '{}'
                      'Beam {:.0f} x {:.0f} x {:.1f} mm, straight; the belly straddles '
                      'it {:.1f} mm deep all along its flat, {:.1f} mm slack across.\n'
                      'Two pylons {:.0f} mm apart, {:.0f} mm showing, into a {:.0f} x '
                      '{:.0f} mm foot.\n'
                      '{} pins {:.0f} mm long locate the car on the beam; the channel is '
                      '{:.1f} mm deep, to glue its sides.\n'
                      'Bullet nose {:.0f} mm long; tail edge rolled {:.1f} mm.\n'
                      'Slots {:.0f} mm deep from the frame face, cubes {:.0f} mm proud of '
                      'the frames, {:.1f} mm of back wall.\n'
                      'Frames {:.1f} mm proud, z {:.1f} to {:.1f}.\n'
                      'Spare pocket in the tail face: {:.1f} mm slack, z {:.1f} to {:.1f}, '
                      'finger notches top and bottom, {:.0f} mm deep and {:.1f} mm wide.\n'
                      'Livery as real steps, not split faces: band {:.1f} mm, windshield '
                      '{:.1f} mm, stripe {:.1f} mm; tools came apart into {}/{}/{} pieces.\n\n'
                      'Fonts: digits in "{}"{}, lettering in "{}"{}.\n'
                      'Digits: 24 faces, recessed {:.2f} mm ({:.1f} walls at 0.42).\n'
                      'Calibrated to a {:.1f} mm em; measured ink {:.1f}-{:.1f} mm tall, '
                      'widest {:.1f} mm, centred on the ink.\n'
                      'Mickey mark on {}.\n'
                      'Hardest countdown value is {:03d}, with {} valid arrangements.\n\n'
                      'Lettering over a {:.1f} mm run, {} scale:\n{}\n'
                      'Raised {:.2f} mm off the stripe floor, {} glyphs a side. '
                      'Measured stroke about {:.2f} mm{}.\n'
                      'Join volume came out x{:.2f} of expected.\n\n'
                      'Bodies in the model: {} -- {}.\n'
                      'Preview colours: {}.\n\n'
                      'Print the car bottom belly down, all white, with support under '
                      'the nose; the red halves on their cut faces, red with gold '
                      'lettering, with support at the tail; the top standing on its '
                      'flat bottom, white and black; the pins on end; the beam on its '
                      'side; the foot flat. Beam and foot grey. Glue every joint, the car '
                      'to the beam too.'
                      .format('PER SIDE' if SYMMETRIC_PER_SIDE else 'TOTAL',
                              allHi[0] - allLo[0], allHi[1] - allLo[1], allHi[2] - allLo[2],
                              carLen, 2.0 * carHalfW, bodyZ1,
                              partsLine,
                              2.0 * beamHalfLen, 2.0 * beamHalfW, beamDepth,
                              straddleEnds, beamFit,
                              2.0 * pylonX, pylonShow, 2.0 * footHalfX, 2.0 * footHalfY,
                              len(BEAM_PIN_X), 2.0 * beamPinH, beamCrestZ,
                              noseLen, tailRound,
                              slotDepth, cubeProud, slotFloorY,
                              frameProud, frameZ0, frameZ1,
                              spareClearance, spareZ0, spareZ1, spareGripR, 2.0 * spareGripHalfW,
                              bandDepth, glassDepth, stripeDepth,
                              bandPieces, glassPieces, stripePieces,
                              digitFont,
                              '' if digitFont == DIGIT_FONTS[0]
                              else ' (NOT your first choice, "{}")'.format(DIGIT_FONTS[0]),
                              textFont,
                              '' if textFont == TEXT_FONTS[0]
                              else ' (NOT your first choice, "{}")'.format(TEXT_FONTS[0]),
                              digitRecess, digitRecess / 0.42,
                              digitEmHeight, inkHiMin, inkHiMax, inkWidest,
                              ', '.join(marked) if marked else 'off',
                              worstN, worstCount,
                              textRun,
                              'shared' if textSharedScale else 'per-side',
                              '\n'.join('  {}: "{}"  {:.1f} x {:.1f} mm at a {:.1f} mm em'
                                        .format(s, CAR_TEXT[s], textInk[s][0],
                                                textInk[s][1], textEm[s])
                                        for s in textSides),
                              textRise,
                              '/'.join(str(n) for n in textGlyphCounts),
                              textStrokeMin,
                              '' if textStrokeMin >= textWarnStroke else
                              ' -- thin for a colour change, look at it before printing',
                              min(textFitRatios) if textFitRatios else 0.0,
                              len(actualBodies), ', '.join(actualBodies),
                              'off' if not PREVIEW_COLOURS else
                              ('applied, finishing took {:.0f} s'.format(paintSeconds)
                               if not paintTrouble else
                               'PARTLY FAILED -- ' + '; '.join(paintTrouble[:3]))))

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
