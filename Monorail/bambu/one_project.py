"""Merge finished single-plate Bambu projects -- all made with the same settings
by make_print_files.sh -- into one project with a plate for each.

    python3 one_project.py <out.3mf> "<plate name>=<project.3mf>" ...

Bambu lays plates out in a grid, as many columns as the square root of the
plate count rounded up, a bed and a fifth apart; each part moves to its plate's
place there and is listed on it. Every object gets a new number, since each
project numbers its own from 1, and every UUID a new value.

The projects' settings must match, but for the prime tower's place, which is
kept per plate, and these:
- the supports, which are on for the whole project as on the plates that have
  them: only painted faces are supported, so the others get none;
- flush_into_infill, which Bambu also keeps per object, so each part keeps its
  own plate's.
"""
import sys, re, json, math, uuid, zipfile
import xml.etree.ElementTree as ET

out, specs = sys.argv[1], [a.partition('=') for a in sys.argv[2:]]
plates = [(name, path) for name, _, path in specs]
BED, GAP = 256.0, 0.2
cols = math.ceil(math.sqrt(len(plates)))
SUPPORT_KEYS = {'enable_support', 'support_type', 'support_critical_regions_only',
                'support_on_build_plate_only', 'support_top_z_distance', 'support_filament',
                'support_interface_filament'}
PER_OBJECT_KEYS = {'flush_into_infill'}


def settings(z):
    return json.loads(z.read('Metadata/project_settings.config'))


zips = [zipfile.ZipFile(path) for _, path in plates]
all_ps = [settings(z) for z in zips]
ps = dict(all_ps[0])
supported = [p for p in all_ps if p.get('enable_support') == '1']
for key in set().union(*all_ps):
    values = [json.dumps(p.get(key)) for p in all_ps]
    if len(set(values)) == 1 or key in ('wipe_tower_x', 'wipe_tower_y') or key in PER_OBJECT_KEYS:
        continue
    assert key in SUPPORT_KEYS, 'the plates differ in {}: {}'.format(key, sorted(set(values)))
    ps[key] = supported[0][key]
for key in ('wipe_tower_x', 'wipe_tower_y'):
    ps[key] = [p[key][0] for p in all_ps]
ps['flush_into_infill'] = '1'

model_head, resources, build, rels, object_files = None, [], [], [], {}
config_objects, config_plates, cut = [], [], []
count = 0
for k, ((name, path), z, plate_ps) in enumerate(zip(plates, zips, all_ps)):
    dx, dy = (k % cols) * BED * (1 + GAP), -(k // cols) * BED * (1 + GAP)
    model = z.read('3D/3dmodel.model').decode()
    if model_head is None:
        model_head = model[:model.index('<resources>')]
    tops = re.findall(r'<object id="(\d+)"[^>]*type="model">\s*<components>\s*<component p:path="([^"]+)" objectid="(\d+)"', model)
    items = dict(re.findall(r'<item objectid="(\d+)"[^>]*transform="([^"]+)"', model))
    cfg = ET.fromstring(z.read('Metadata/model_settings.config'))
    cfg_objects = {o.get('id'): o for o in cfg.findall('object')}
    instances = []
    for top, part_path, mesh in tops:
        count += 1
        new_mesh, new_top, new_file = 2 * count - 1, 2 * count, '/3D/Objects/object_{}.model'.format(count)
        text = z.read(part_path.lstrip('/')).decode()
        text = re.sub(r'<object id="{}"'.format(mesh), '<object id="{}"'.format(new_mesh), text, count=1)
        object_files[new_file.lstrip('/')] = text
        resources.append(
            '  <object id="{}" p:UUID="{}" type="model">\n   <components>\n'
            '    <component p:path="{}" objectid="{}" p:UUID="{}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n'
            '   </components>\n  </object>\n'.format(new_top, uuid.uuid4(), new_file, new_mesh, uuid.uuid4()))
        t = items[top].split()
        t[9], t[10] = repr(float(t[9]) + dx), repr(float(t[10]) + dy)
        build.append('  <item objectid="{}" p:UUID="{}" transform="{}" printable="1"/>\n'.format(
            new_top, uuid.uuid4(), ' '.join(t)))
        rels.append(new_file)
        o = cfg_objects[top]
        o.set('id', str(new_top))
        for part in o.findall('part'):
            part.set('id', str(new_mesh))
        for key in PER_OBJECT_KEYS:
            if plate_ps.get(key) != ps[key]:
                ET.SubElement(o, 'metadata', {'key': key, 'value': plate_ps[key]})
        config_objects.append(o)
        instances.append(new_top)
        cut.append(' <object id="{}">\n  <cut_id id="0" check_sum="1" connectors_cnt="0"/>\n </object>\n'
                   .format(count))
    plate = ['  <plate>', '    <metadata key="plater_id" value="{}"/>'.format(k + 1),
             '    <metadata key="plater_name" value="{}"/>'.format(name),
             '    <metadata key="locked" value="false"/>',
             '    <metadata key="filament_map_mode" value="Auto For Flush"/>']
    for top in instances:
        plate += ['    <model_instance>', '      <metadata key="object_id" value="{}"/>'.format(top),
                  '      <metadata key="instance_id" value="0"/>',
                  '      <metadata key="identify_id" value="{}"/>'.format(1000 + top),
                  '    </model_instance>']
    config_plates.append('\n'.join(plate + ['  </plate>']))

files = {
    '[Content_Types].xml': zips[0].read('[Content_Types].xml'),
    '_rels/.rels': ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns='
                    '"http://schemas.openxmlformats.org/package/2006/relationships">\n'
                    ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" '
                    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
                    '</Relationships>\n'),
    '3D/3dmodel.model': model_head + ' <resources>\n' + ''.join(resources) + ' </resources>\n'
                        ' <build p:UUID="{}">\n'.format(uuid.uuid4()) + ''.join(build) +
                        ' </build>\n</model>\n',
    '3D/_rels/3dmodel.model.rels': '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns='
        '"http://schemas.openxmlformats.org/package/2006/relationships">\n' + ''.join(
            ' <Relationship Target="{}" Id="rel-{}" Type="http://schemas.microsoft.com/'
            '3dmanufacturing/2013/01/3dmodel"/>\n'.format(f, i + 1) for i, f in enumerate(rels)) +
        '</Relationships>\n',
    'Metadata/project_settings.config': json.dumps(ps, indent=4),
    'Metadata/model_settings.config': '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n' + ''.join(
        '  ' + ET.tostring(o, encoding='unicode').strip() + '\n' for o in config_objects) +
        '\n'.join(config_plates) + '\n  <assemble>\n  </assemble>\n</config>\n',
    'Metadata/cut_information.xml': '<?xml version="1.0" encoding="utf-8"?>\n<objects>\n' +
                                    ''.join(cut) + '</objects>\n',
    'Metadata/slice_info.config': zips[0].read('Metadata/slice_info.config'),
    'Metadata/filament_sequence.json': json.dumps({'plate_{}'.format(k + 1): {
        'nozzle_sequence': [], 'optimal_assignment': [], 'sequence': []} for k in range(len(plates))}),
}
files.update(object_files)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for name, data in files.items():
        z.writestr(name, data)
print('{}: {} plates, {} parts -- {}'.format(out, len(plates), count, ', '.join(n for n, _ in plates)))
