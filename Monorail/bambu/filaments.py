"""The monorail's filament list, built once and given to every plate, so that a
filament number means the same in every print file -- paint, supports and all
-- and a plate imported into another's project keeps its colours.

    python3 filaments.py <your four-filament project.3mf> <a one-filament project
        Bambu's command line wrote.3mf> <out.3mf> [<a project with a PETG filament>.3mf]

The out project has your four, then:

    5  grey PLA, for the beam and foot -- your filament 1, in grey
    6  PETG, for the supports' interface -- from the PETG project, if given

Bambu keeps several kinds of list that grow with the filament count. Lists of
a value per nozzle variant are as long as filament_self_index, and are matched
through it and filament_extruder_variant, since a filament can have fewer
variants than another. For the rest, the one-filament project shows which is
which: a list with k entries there has k per filament here. A few filament_
lists are missing there and go by their length; the machine's lists that are
as long only by coincidence are not filament_ lists. The purge volumes for a new filament are
those of the filament it looks most like, with a small purge between two that
look alike; Bambu Studio recalculates them when you change a swatch.
"""
import sys, json, zipfile

mine, ref_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
petg_path = sys.argv[4] if len(sys.argv) > 4 else None
GREY, PETG_SWATCH = '#8E9089', '#FFFFFF'
SAME_COLOUR_PURGE = '140'       # mm3, Bambu's default flush, between alike swatches
# Only that long by coincidence: points of the bed, and the prime tower's
# place on each plate.
NOT_PER_FILAMENT = {'bed_exclude_area', 'printable_area', 'print_compatible_printers',
                    'wipe_tower_x', 'wipe_tower_y', 'upward_compatible_machine'}


def settings(path):
    return json.loads(zipfile.ZipFile(path).read('Metadata/project_settings.config'))


ps, ref = settings(mine), settings(ref_path)
n = len(ps['filament_settings_id'])
assert len(ref['filament_settings_id']) == 1, ref_path + ' is not a one-filament project'
VARIANT_KEYS = ('filament_self_index', 'filament_extruder_variant')


def is_variant_list(key, settings_):
    return len(settings_.get(key, [])) == len(settings_['filament_self_index'])


def entries(settings_, index):
    """(position, variant) of filament `index`'s entries in the per-variant lists."""
    return [(i, v) for i, (f, v) in enumerate(zip(settings_['filament_self_index'],
                                                   settings_['filament_extruder_variant']))
            if int(f) == index + 1]


# Which lists are per filament, and how many entries each filament has.
per_filament, per_variant = {}, []
for key, value in ps.items():
    if key in NOT_PER_FILAMENT or key in VARIANT_KEYS or not isinstance(value, list):
        continue
    if key == 'flush_volumes_matrix' or len(value) == n + 2 and key in (
            'different_settings_to_system', 'inherits_group'):
        continue
    if is_variant_list(key, ps):
        per_variant.append(key)
    elif isinstance(ref.get(key), list) and ref[key] and len(value) == len(ref[key]) * n:
        per_filament[key] = len(ref[key])
    elif key.startswith('filament_') and value and len(value) % n == 0:
        per_filament[key] = len(value) // n     # not in Bambu's one-filament project


def add(source, s, colour, like):
    """Append filament s of the `source` settings, in `colour`; its purges are
    filament `like`'s."""
    global n
    t = n
    # Read everything from the source before appending: the source may be ps.
    ns = len(source['filament_settings_id'])
    taken = {key: (source[key][k * s:k * s + k]
                   if isinstance(source.get(key), list) and len(source[key]) == k * ns
                   else ps[key][k * like:k * like + k])
             for key, k in per_filament.items()}
    src_entries = entries(source, s)
    template = entries(ps, 0)                   # one entry per variant the printer has
    taken_variant = {}
    for _, variant in template:
        j = next((j for j, v in src_entries if v == variant), src_entries[0][0])
        for key in per_variant:
            taken_variant.setdefault(key, []).append(
                source[key][j] if is_variant_list(key, source) else ps[key][template[0][0]])
    for key, values in taken.items():
        ps[key] += values
    for _, variant in template:
        ps['filament_self_index'].append(str(t + 1))
        ps['filament_extruder_variant'].append(variant)
    for key, values in taken_variant.items():
        ps[key] += values
    for key in ('different_settings_to_system', 'inherits_group'):
        ps[key].insert(len(ps[key]) - 1, '')
    for key in ('filament_colour', 'filament_multi_colour', 'default_filament_colour'):
        if key in per_filament:
            ps[key][t] = colour
    m = ps['flush_volumes_matrix']
    old = [m[i * n:(i + 1) * n] for i in range(n)]
    looks = LOOKS_LIKE + [like]
    grid = [[None] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(n + 1):
            if i == j:
                grid[i][j] = '0'
            elif i < n and j < n:
                grid[i][j] = old[i][j]
            else:
                a, b = looks[i], looks[j]
                grid[i][j] = old[a][b] if a != b else SAME_COLOUR_PURGE
    ps['flush_volumes_matrix'] = [v for row in grid for v in row]
    LOOKS_LIKE.append(like)
    n += 1


LOOKS_LIKE = list(range(n))     # which original filament each one looks like
add(ps, 0, GREY, like=1)        # grey: your filament 1's profile, black's purges
if petg_path:
    petg = settings(petg_path)
    s = next((i for i, kind in enumerate(petg['filament_type']) if 'PETG' in kind.upper()), None)
    assert s is not None, petg_path + ' has no PETG filament'
    add(petg, s, PETG_SWATCH, like=0)

unsorted = [key for key, value in ps.items() if isinstance(value, list) and key not in per_filament
            and key not in per_variant and key not in NOT_PER_FILAMENT and key not in VARIANT_KEYS
            and key not in ('flush_volumes_matrix', 'different_settings_to_system', 'inherits_group')
            and len(value) % len(LOOKS_LIKE[:4]) == 0 and len(value) >= 4]
if unsorted:
    print('not grown, check these:', ', '.join('{} ({})'.format(k, len(ps[k])) for k in unsorted))
for key, k in per_filament.items():
    assert len(ps[key]) == k * n, key
for key in per_variant:
    assert len(ps[key]) == len(ps['filament_self_index']), key
assert len(ps['flush_volumes_matrix']) == n * n

zin = zipfile.ZipFile(mine)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for name in zin.namelist():
        data = zin.read(name)
        if name == 'Metadata/project_settings.config':
            data = json.dumps(ps, indent=4).encode()
        z.writestr(name, data)
print('{}: {} filaments -- {}'.format(out, n, ', '.join(
    '{} {} {}'.format(i + 1, kind, colour) for i, (kind, colour) in
    enumerate(zip(ps['filament_type'], ps['filament_colour'])))))
