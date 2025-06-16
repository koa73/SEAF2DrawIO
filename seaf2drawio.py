from N2G import drawio_diagram
import sys
import json
import re
import os
import argparse
from copy import deepcopy
from lib import seaf_drawio
import xml.etree.ElementTree as ET

patterns_dir = 'data/patterns/'
diagram = drawio_diagram()
node_xml_default = diagram.drawio_node_object_xml
root_object = 'seaf.ta.services.dc_region'
diagram_pages = {'main': ['Main Schema'], 'office': [], 'dc': []}
diagram_ids = {'Main Schema': []}
conf = {}

# Переменные по умолчанию
DEFAULT_CONFIG = {
    "seaf2drawio": {
        "data_yaml_file": "data/example/test_seaf_ta_P41_v0.5.yaml",
        "drawio_pattern": "data/base.drawio",
        "output_file": "result/Sample_graph.drawio"
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
                pattern['x'] = pattern['x'] + pattern['w'] + pattern['offset']
                pattern['y'] = pattern['y'] - (pattern['h'] + pattern['offset']) * pattern['deep']
            pattern['y'] = pattern['y'] + pattern['h'] + pattern['offset']

        case 'Y-':
            if return_ready(pattern):
                pattern['x'] = pattern['x'] + pattern['w'] + pattern['offset']
                pattern['y'] = pattern['y'] + (pattern['h'] + pattern['offset']) * pattern['deep']
            pattern['y'] = pattern['y'] - pattern['h'] - pattern['offset']

        case 'X-':

            if return_ready(pattern):
                pattern['y'] = pattern['y'] +  pattern['h'] + pattern['offset']
                pattern['x'] = pattern['x'] + (pattern['w'] + pattern['offset']) * pattern['deep']
            pattern['x'] = pattern['x'] - pattern['w'] - pattern['offset']
        # По оси X слева направо
        case 'X+':
            if return_ready(pattern):
                pattern['y'] = pattern['y'] +  pattern['h'] + pattern['offset']
                pattern['x'] = pattern['x'] - (pattern['w'] + pattern['offset']) * pattern['deep']
            pattern['x'] = pattern['x'] + pattern['w'] + pattern['offset']


def return_ready(pattern):
    pattern['count']+=1
    if pattern['count'] == pattern['deep']:
        pattern['count'] = 0

    return not bool(pattern['count'])


def get_parent_value(pattern, current_parent):
    r = ''
    if pattern.get('parent_key'):
        r = d.find_value_by_key(d.find_value_by_key(json.loads(json.dumps(d.read_yaml_file(conf['data_yaml_file']))),
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

            """
                Заменяет ключ 'id' на 'sid' в словаре, если он существует.
            """
            if 'id' in data:
                data['sid'] = data.pop('id')

            data['schema'] = pattern['schema']

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

            if pattern_count == 0:  # Change position of element
                position_offset(object_pattern)

            pattern_count += 1

        diagram.drawio_node_object_xml = node_xml_default


def add_links(pattern):

    diagram.drawio_link_object_xml = pattern['xml']
    source_id = 'Unknown'

    for source_id, targets in d.get_object(conf['data_yaml_file'], pattern['schema'],
                                           type=object_pattern.get('type')).items():  # source_id - ID объекта

        try:
            if source_id in diagram_ids[page_name]:  # Объект присутствует на текущей диаграмме
                if pattern.get('parent_id'):
                    targets = {pattern['targets']: [get_parent_value(pattern, targets[pattern['parent_id']])]}
                for target_id in targets[pattern['targets']]:
                    if target_id in diagram_ids[page_name]:  # Объект для связи присутствует на диаграмме
                        diagram.add_link(source=source_id, target=target_id, style=pattern['style'])

                    else:
                        print(f' Can\'t link  {source_id} <---> {target_id}, object {target_id} not found at the page '
                              f'{page_name}')
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
    diagram_ids['Main Schema'] = list(d.get_object(conf['data_yaml_file'], root_object).keys())
    for file_name, pages in diagram_pages.items():

        for page_name in pages:

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
                    add_links(object_pattern)  # Связывание объектов на текущей диаграмме

    d.dump_file(filename=os.path.basename(conf['output_file']), folder=os.path.dirname(conf['output_file']),
                content=diagram.drawing if os.path.dirname(conf['output_file']) else './')