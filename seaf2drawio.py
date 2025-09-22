from N2G import drawio_diagram
import sys
import json
import re
import os
import argparse
from copy import deepcopy
from lib import seaf_drawio
from lib.link_manager import remove_obsolete_links
import xml.etree.ElementTree as ET

patterns_dir = 'data/patterns/'
diagram = drawio_diagram()
node_xml_default = diagram.drawio_node_object_xml
root_object = 'seaf.ta.services.dc_region'
diagram_pages = {'main': ['Main Schema'], 'office': [], 'dc': []}
diagram_ids = {'Main Schema': []}
object_area = {}
conf = {}
pending_missing_links = set()
layout_counters = {}
expected_counts = {}
expected_data = {}
pattern_specs = {}
IGNORE_OBJECT_IDS = {"981", "991"}

# Переменные по умолчанию
DEFAULT_CONFIG = {
    "seaf2drawio": {
        "data_yaml_file": "data/example/test_seaf_ta_P41_v0.9.yaml",
        "drawio_pattern": "data/base.drawio",
        "output_file": "result/Sample_graph.drawio",
        "verify_generation": False
    }
}

d = seaf_drawio.SeafDrawio(DEFAULT_CONFIG)

def cli_vars(config):
    try:
        parser = argparse.ArgumentParser(description="Параметры командной строки.")

        src_validator = d.create_validator(r'^.+(\.yaml)$')
        dst_validator = d.create_validator(r'^.+(\.drawio)$')

        parser.add_argument("-s", "--src", type=src_validator, action=seaf_drawio.ValidateFile, help="файл данных SEAF",
                            required=False)
        parser.add_argument("-d", "--dst", type=dst_validator, help="путь и имя файла вывода результатов",
                            required=False)
        parser.add_argument("-p", "--pattern", type=dst_validator, action=seaf_drawio.ValidateFile, help="шаблон drawio",
                            required=False)
        args = parser.parse_args()
        if args.src:
            config['data_yaml_file'] = args.src
        if args.dst:
            config['output_file'] = args.dst
        if args.pattern:
            config['drawio_pattern'] = args.pattern
        return config

    except argparse.ArgumentTypeError as e:
        print(e)
        sys.exit(1)

def position_offset(pattern):

    match pattern['algo']:
        # По оси Y cверху вниз относительно родительского объекта
        case 'Y+':
            if return_ready(pattern):
                x_off = pattern.get('x_offset', pattern['offset'])
                y_off = pattern.get('y_offset', pattern['offset'])
                pattern['x'] = pattern['x'] + pattern['w'] + x_off
                pattern['y'] = pattern['y'] - (pattern['h'] + y_off) * pattern['deep']
            y_off = pattern.get('y_offset', pattern['offset'])
            pattern['y'] = pattern['y'] + pattern['h'] + y_off

        case 'Y-':
            if return_ready(pattern):
                x_off = pattern.get('x_offset', pattern['offset'])
                y_off = pattern.get('y_offset', pattern['offset'])
                pattern['x'] = pattern['x'] + pattern['w'] + x_off
                pattern['y'] = pattern['y'] + (pattern['h'] + y_off) * pattern['deep']
            y_off = pattern.get('y_offset', pattern['offset'])
            pattern['y'] = pattern['y'] - pattern['h'] - y_off

        case 'X-':

            if return_ready(pattern):
                y_off = pattern.get('y_offset', pattern['offset'])
                x_off = pattern.get('x_offset', pattern['offset'])
                pattern['y'] = pattern['y'] +  pattern['h'] + y_off
                pattern['x'] = pattern['x'] + (pattern['w'] + x_off) * pattern['deep']
            x_off = pattern.get('x_offset', pattern['offset'])
            pattern['x'] = pattern['x'] - pattern['w'] - x_off
        # По оси X слева направо
        case 'X+':
            if return_ready(pattern):
                y_off = pattern.get('y_offset', pattern['offset'])
                x_off = pattern.get('x_offset', pattern['offset'])
                pattern['y'] = pattern['y'] +  pattern['h'] + y_off
                pattern['x'] = pattern['x'] - (pattern['w'] + x_off) * pattern['deep']
            x_off = pattern.get('x_offset', pattern['offset'])
            pattern['x'] = pattern['x'] + pattern['w'] + x_off

def return_ready(pattern):
    pattern['count']+=1
    if pattern['count'] == pattern['deep']:
        pattern['count'] = 0

    return not bool(pattern['count'])

def get_parent_value(pattern, current_parent):
    r = ''
    if pattern.get('parent_key'):
        r = d.find_value_by_key(d.find_value_by_key(json.loads(json.dumps(d.read_and_merge_yaml(conf['data_yaml_file']))),
                                                    current_parent), pattern['parent_key'])
    return r

def add_pages(pattern):

    if pattern.get('ext_page'):
        page_data = d.get_object(conf['data_yaml_file'], pattern['schema'])
        diagram_xml_default = diagram.drawio_diagram_xml

        for key_id in list( page_data.keys() ):

            diagram.drawio_diagram_xml = pattern['ext_page']
            try:
                diagram.add_diagram(key_id + '_page', page_data[key_id]['title'])
                diagram_pages[k].append(page_data[key_id]['title'])
                d.append_to_dict(diagram_ids, page_data[key_id]['title'], key_id)
            except ET.ParseError:
                print(f'WARNING ! Не используйте XML зарезервированные символы <>&\'\" в поле title для объектов dc/office')
                pass


        diagram.drawio_diagram_xml = diagram_xml_default
        diagram.go_to_diagram(page_name)

def update_object_area(area,  key, algo, offset, **kwargs ):
    try:
        if key not in area:
            area[key] = {'X+': 0, 'Y+': 0, 'X-': 0, 'Y-': 0, 'none':0}
        if kwargs.get('parent'):
            area[kwargs['parent']][algo] += offset
            #print(f">>>>{page_name}::  {key} --> {kwargs['parent']} :: {area[kwargs['parent']][algo]}")
    except KeyError as e:
        area[kwargs.get('parent')] = {'X+': 0, 'Y+': 0, 'X-': 0, 'Y-': 0, 'none': 0}
        update_object_area(area,  key, algo, offset, **kwargs )

def add_object(pattern, data, key_id):

    pattern_count, current_parent = 0, ''
    for xml_pattern in d.get_xml_pattern(pattern['xml'], key_id):

        diagram.drawio_node_object_xml = xml_pattern

        # Если у элемента есть родитель, получаем ID родителя и проверяем связан ли родитель с текущей диаграммой (страницей)
        # добавляем в справочник ID элемента
        if pattern.get('parent_id') and d.find_common_element(d.find_key_value(data, pattern['parent_id']),
                                                     diagram_ids[page_name]) and pattern_count == 0:

            d.append_to_dict(diagram_ids, page_name, key_id)
            current_parent = d.find_common_element(d.find_key_value(data, pattern['parent_id']),diagram_ids[page_name])

            # If parent_id field is a list (e.g., WAN.segment), normalize it to the selected current_parent
            try:
                if isinstance(data.get(pattern['parent_id']), list):
                    data['parent_tmp'] = data.get(pattern['parent_id'])
                    data[pattern['parent_id']] = current_parent
            except Exception:
                pass

            if current_parent != pattern['last_parent']:   # reset to default pattern
                default_pattern['parent'] = get_parent_value(pattern, current_parent)
                pattern.update(default_pattern)
                pattern['last_parent'] = current_parent

        try:
            diagram.drawio_node_object_xml = diagram.drawio_node_object_xml.format_map(
                data | {'Group_ID': f'{key_id}_0', 'parent_id' : current_parent, 'parent_type' : default_pattern['parent'],
                        'description' : data.get('description','') })  # замена в xml шаблоне переменных в одинарных {}, добавление ID группы
            data['OID'] = key_id

        except KeyError as e:

            #print("Error: Can't add object: {id} to page: {page}. Key: {key} out of dictionary. Data: {data}"
            #      .format(key=str(e), id=i, page=page_name, data=data))
            return


        if key_id in diagram_ids[page_name]:

            #if pattern.get('parent_id') == 'dc':
            #    print(f'==={i} == {current_parent} === {key_id}_{pattern_count}')
            """
                Заменяет ключ 'id' на 'sid' в словаре, если он существует.
            """
            if 'id' in data:
                data['sid'] = data.pop('id')

            data['schema'] = pattern['schema']

            # Удаляем техническое поле если оно присутствует в данных
            if 'parent_tmp' in data:
                del data['parent_tmp']

            # Если не содержит конструкции <object></object>, то изменять ID добавляя порядковый номер
            diagram.add_node(
                id=f"{key_id}_{pattern_count}" if not d.contains_object_tag(xml_pattern, 'object') else key_id,
                label=data['title'],
                x_pos=pattern['x'],
                y_pos=pattern['y'],
                width=pattern['w'],
                height=pattern['h'],
                data=data if d.contains_object_tag(xml_pattern, 'object') else {},
                url=pattern.get('ext_page') and data['title']
            )
            d.append_to_dict(diagram_ids, page_name, key_id)  # Добавляет ID root элементов

            #if d.contains_object_tag(xml_pattern, 'object'): ## ---- ToDo ----
            #    update_object_area(object_area[page_name], key_id, pattern.get('algo'), 1, parent=current_parent)

            if pattern_count == 0:  # Change position of element
                position_offset(object_pattern)
            pattern_count += 1

        diagram.drawio_node_object_xml = node_xml_default

def add_links(pattern,  **kwargs):

    diagram.drawio_link_object_xml = pattern['xml']
    source_id = 'Unknown'

    for source_id, targets in d.get_object(conf['data_yaml_file'], pattern['schema'],
                                           type=object_pattern.get('type')).items():  # source_id - ID объекта

        if kwargs.get('logical_link'):
            targets['OID'] = source_id
            source_id = targets['source']
            targets['schema'] = pattern['schema']

        try:
            if source_id in diagram_ids[page_name]:  # Объект присутствует на текущей диаграмме
                if pattern.get('parent_id'):
                    # parent_id may be a list (e.g., WAN.segment). Derive targets for each parent entry.
                    parent_val = targets.get(pattern['parent_id'])
                    parent_ids = parent_val if isinstance(parent_val, list) else ([parent_val] if parent_val else [])
                    derived_targets = []
                    for pid in parent_ids:
                        val = get_parent_value(pattern, pid)
                        if isinstance(val, list):
                            derived_targets.extend(val)
                        elif val is not None:
                            derived_targets.append(val)
                    targets = {pattern['targets']: derived_targets}
                for target_id in targets[pattern['targets']]:
                    if target_id in diagram_ids[page_name]:  # Объект для связи присутствует на диаграмме
                        if kwargs.get('logical_link'):
                            style = 'style'+ str(targets['direction']) # Выбор стиля стрелки
                            diagram.add_link(source=source_id, target=target_id, style=pattern[style], data=targets)
                        else:
                            diagram.add_link(source=source_id, target=target_id, style=pattern['style'])
                    else:
                        # Defer logging: cross-page targets are expected; warn later only if missing everywhere
                        pending_missing_links.add((page_name, source_id, target_id))
        except KeyError as e:
            pass
            print(f" INFO : Не найден параметр {e} для объекта '{pattern['schema']}/{source_id}' при добавлении связей на диаграмму '{page_name}'.")
        except TypeError as e:
            pass
            print(
                f"Error: у объекта '{source_id}' отсутствует данные для создания линка в параметре {pattern['targets']} ")



if __name__ == '__main__':

    if sys.version_info < (3, 9):
        print("Этот скрипт требует Python версии 3.9 или выше.")
        sys.exit(1)

    conf = cli_vars(d.load_config("config.yaml")['seaf2drawio'])

    diagram.from_xml(d.read_file_with_utf8(conf['drawio_pattern']))
    
    # Удаляем устаревшие связи перед добавлением новых
    remove_obsolete_links(diagram, conf['data_yaml_file'], 'seaf.ta.components.network')
    
    diagram_ids['Main Schema'] = list(d.get_object(conf['data_yaml_file'], root_object).keys())
    for file_name, pages in diagram_pages.items():

        for page_name in pages:

            object_area[page_name] = {} # Создаем поле объектов страницы

            diagram.go_to_diagram(page_name)
            for k, object_pattern in d.read_yaml_file(patterns_dir + file_name + '.yaml').items():

                try:
                    object_data = d.get_object(conf['data_yaml_file'], object_pattern['schema'], type=object_pattern.get('type'),
                        sort=object_pattern['parent_id'] if object_pattern.get('parent_id') else None)

                    add_pages(object_pattern)
                    object_pattern.update({
                                'count': 0,               # Счетчик объектов
                                'last_parent': '',        # Триггер для отслеживания изменения родительского объекта
                                'parent': ''              # Родительский объект
                    })
                    default_pattern = deepcopy(object_pattern)

                    # Collect expected IDs and data per schema (for verification)
                    try:
                        schema_key = object_pattern['schema']
                        expected_counts.setdefault(schema_key, set()).update(list(object_data.keys()))
                        expected_data.setdefault(schema_key, {}).update(object_data)
                        # Record pattern spec for diagnostics
                        type_key, type_val = None, None
                        if object_pattern.get('type'):
                            if ':' in object_pattern['type']:
                                type_key, type_val = object_pattern['type'].split(':', 1)
                            else:
                                type_key, type_val = 'type', object_pattern['type']
                        pattern_specs.setdefault(schema_key, []).append({
                            'pattern_name': k,
                            'parent_id': object_pattern.get('parent_id'),
                            'type_key': type_key,
                            'type_val': type_val,
                        })
                    except Exception:
                        pass

                    for i in list(object_data.keys()):
                        if i in diagram.nodes_ids[diagram.current_diagram_id]:
                            diagram.update_node(id=i, data=object_data[i])
                            d.append_to_dict(diagram_ids, page_name, i)
                        else:
                            add_object(object_pattern, object_data[i], i)

                except KeyError as e:
                    pass
                    print(f' INFO : В файле данных отсутствуют объекты {object_pattern["schema"]} для добавления на диаграмму {page_name}')

                if bool(re.match(r'^network_links(_\d+)*',k)):
                    add_links(object_pattern, pattern_name=k)  # Связывание объектов на текущей диаграмме

                if bool(re.match(r'^logical_links(_\d+)*', k)):
                    add_links(object_pattern, logical_link=True)  # Связывание объектов на текущей диаграмме

    # After constructing all pages, log only truly missing targets (not present on any page)
    try:
        present_ids = set()
        for ids in diagram_ids.values():
            present_ids.update(ids)
        real_missing = sorted({(p, s, t) for (p, s, t) in pending_missing_links if t not in present_ids})
        if real_missing:
            print(f"INFO: skipped {len(real_missing)} links due to targets missing on all pages:")
            for page_name, source_id, target_id in real_missing:
                print(f"  {page_name}: {source_id} -> {target_id}")
    except Exception:
        pass

    # Post-process: distribute KB services vertically per x column (parent=101) to avoid overlaps
    try:
        root_xml = diagram.drawing
        for diag in root_xml.findall('.//diagram'):
            kb_cells = []
            for cell in diag.iter('mxCell'):
                if cell.get('vertex') == '1' and cell.get('parent') == '101':
                    geo = cell.find('mxGeometry')
                    if geo is not None and geo.get('x') is not None and geo.get('y') is not None:
                        try:
                            x = int(float(geo.get('x')))
                            y = int(float(geo.get('y')))
                        except ValueError:
                            continue
                        kb_cells.append((cell, x, y))
            from collections import defaultdict
            groups = defaultdict(list)
            for cell, x, y in kb_cells:
                groups[x].append((cell, y))
            for x, items in groups.items():
                items.sort(key=lambda t: (t[1], t[0].get('id')))
                if not items:
                    continue
                y0 = min(y for _, y in items)
                step = 70  # height 40 + offset 30 from KB patterns
                for idx, (cell, _) in enumerate(items):
                    geo = cell.find('mxGeometry')
                    if geo is not None:
                        geo.set('y', str(y0 + idx * step))
    except Exception:
        pass

    d.dump_file(filename=os.path.basename(conf['output_file']), folder=os.path.dirname(conf['output_file']),
                content=diagram.drawing if os.path.dirname(conf['output_file']) else './')

    #print(object_area)

    # Optional verification summary against final generated file
    try:
        if conf.get('verify_generation'):
            final_path = conf['output_file']
            tree = ET.parse(final_path)
            root_xml = tree.getroot()

            # Gather drawn counts per schema (global and per page)
            drawn_unique = {}
            drawn_total = {}
            per_page_unique = {}
            per_page_total = {}
            # per-page (iterate diagrams)
            for diag in root_xml.findall('.//diagram'):
                page = diag.get('name') or 'Unknown'
                per_page_unique.setdefault(page, {})
                per_page_total.setdefault(page, {})
                for obj in diag.iter('object'):
                    schema = obj.get('schema')
                    oid = obj.get('id')
                    if not schema or not oid:
                        continue
                    if oid in IGNORE_OBJECT_IDS:
                        continue
                    # Logical links: use OID (semantic id) if available, skip non-edge objects
                    if schema == 'seaf.ta.services.logical_link':
                        cell = obj.find('mxCell')
                        if cell is None or cell.get('edge') != '1':
                            continue
                        oid = obj.get('OID') or oid
                    per_page_total[page][schema] = per_page_total[page].get(schema, 0) + 1
                    per_page_unique[page].setdefault(schema, set()).add(oid)
            for obj in root_xml.findall('.//object'):
                schema = obj.get('schema')
                oid = obj.get('id')
                if not schema or not oid:
                    continue
                if oid in IGNORE_OBJECT_IDS:
                    continue
                if schema == 'seaf.ta.services.logical_link':
                    cell = obj.find('mxCell')
                    if cell is None or cell.get('edge') != '1':
                        continue
                    oid = obj.get('OID') or oid
                drawn_total[schema] = drawn_total.get(schema, 0) + 1
                drawn_unique.setdefault(schema, set()).add(oid)

            # Print summary per schema based on expected_counts gathered from patterns
            schemas = sorted(set(list(expected_counts.keys()) + list(drawn_unique.keys())))
            all_match = True
            print("Verification summary (by schema):")
            for schema in schemas:
                exp = len(expected_counts.get(schema, set()))
                drw_u = len(drawn_unique.get(schema, set()))
                drw_t = drawn_total.get(schema, 0)
                match = (exp == drw_u)
                all_match = all_match and match
                print(f"  - {schema}: expected={exp}, drawn_unique={drw_u}, drawn_total={drw_t} -> {'OK' if match else 'MISMATCH'}")

            if not all_match:
                # Show a small diff preview
                for schema in schemas:
                    exp_set = expected_counts.get(schema, set())
                    drw_set = drawn_unique.get(schema, set())
                    missing = list(exp_set - drw_set)[:5]
                    extra = list(drw_set - exp_set)[:5]
                    if missing or extra:
                        if missing:
                            print(f"    missing in diagram ({schema}): {missing}...")
                        if extra:
                            print(f"    extra in diagram ({schema}): {extra}...")

                # Detailed diagnostics for missing items
                all_oids = set()
                for obj in root_xml.findall('.//object'):
                    if obj.get('id'):
                        all_oids.add(obj.get('id'))
                print("Diagnostics for missing items:")
                # Pre-compute expected values per schema/type_key for concise messages
                schema_expected = {}
                for schema in schemas:
                    specs = pattern_specs.get(schema, [])
                    if not specs:
                        continue
                    # choose most common type_key, collect all its expected values
                    key_counts = {}
                    values_by_key = {}
                    for spec in specs:
                        tk, tv = spec.get('type_key'), spec.get('type_val')
                        if not tk or not tv:
                            continue
                        key_counts[tk] = key_counts.get(tk, 0) + 1
                        values_by_key.setdefault(tk, set()).add(tv)
                    if values_by_key:
                        best_key = max(key_counts.items(), key=lambda x: x[1])[0]
                        schema_expected[schema] = (best_key, values_by_key.get(best_key, set()))

                for schema in schemas:
                    exp_set = expected_counts.get(schema, set())
                    drw_set = drawn_unique.get(schema, set())
                    missing_ids = list(exp_set - drw_set)
                    if not missing_ids:
                        continue
                    print(f"  {schema}:")
                    tkey, tvals = schema_expected.get(schema, (None, set()))
                    for mid in missing_ids[:10]:
                        data = expected_data.get(schema, {}).get(mid, {})
                        msg_parts = []
                        if tkey:
                            vals = d.find_key_value(data, tkey)
                            actual = vals[0] if isinstance(vals, list) and vals else None
                            # Prepare expected list (limited)
                            ev = sorted(v for v in tvals)
                            ev_out = ", ".join(ev[:6]) + (" ..." if len(ev) > 6 else "")
                            msg_parts.append(f"{tkey}='{actual}' | expected: {ev_out}")
                        # parent_id hint (first parent spec)
                        pid = None
                        for spec in pattern_specs.get(schema, []):
                            if spec.get('parent_id'):
                                pid = spec.get('parent_id')
                                break
                        if pid:
                            parents = d.find_key_value(data, pid)
                            present = any(p in all_oids for p in (parents if isinstance(parents, list) else [parents]))
                            if not present:
                                msg_parts.append(f"parent '{pid}' not present on pages")
                        print(f"    - {mid}: " + ("; ".join(msg_parts) if msg_parts else "no rule matched"))

            # Per-page breakdown (drawn counts)
            print("Per-page summary (drawn, by schema):")
            for page in sorted(per_page_total.keys()):
                print(f"  Page: {page}")
                schemas_p = sorted(set(list(per_page_total[page].keys()) + list(per_page_unique[page].keys())))
                for schema in schemas_p:
                    du = len(per_page_unique[page].get(schema, set()))
                    dt = per_page_total[page].get(schema, 0)
                    print(f"    - {schema}: drawn_unique={du}, drawn_total={dt}")

            print("Result:", "GENERATION MATCHES YAML (by schema)" if all_match else "GENERATION DIFFERS FROM YAML (by schema)")
    except Exception as e:
        print(f"Verification step failed: {e}")
