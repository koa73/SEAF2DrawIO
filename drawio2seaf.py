from lib import seaf_drawio
from N2G import drawio_diagram
import sys
import json
import html
import argparse

# Переменные по умолчанию
DEFAULT_CONFIG = {
    "drawio2seaf": {
        "drawio_file": "result/Sample_graph.drawio",
        "output_file": "result/seaf.yaml"
    }
}
d = seaf_drawio.SeafDrawio(DEFAULT_CONFIG)
diagram = drawio_diagram()
schema_file = 'data/seaf.schema'

def __cli_vars(config):
    try:
        parser = argparse.ArgumentParser(description="Параметры командной строки.")

        dst_validator = d.create_validator(r'^.+(\.yaml)$')
        src_validator = d.create_validator(r'^.+(\.drawio)$')

        parser.add_argument("-s", "--src", type=src_validator, action=seaf_drawio.ValidateFile, help="файл DrawIO",
                            required=False)
        parser.add_argument("-d", "--dst", type=dst_validator, help="путь и имя файла вывода результатов",
                            required=False)
        args = parser.parse_args()
        if args.src:
            config['drawio_file'] = args.src
        if args.dst:
            config['output_file'] = args.dst
        return config

    except argparse.ArgumentTypeError as e:
        print(e)
        sys.exit(1)

def get_tag_attr(root):
    # Извлечение всех атрибутов тега <object>
    attributes = root.attrib

    # Исключение атрибутов 'id' и 'label'
    return {attributes['schema']:{attributes['OID']:{key: html.unescape(value) for key, value in attributes.items()
                               if key not in ['id', 'label', 'OID', 'schema']}}}


if __name__ == '__main__':

    if sys.version_info < (3, 9):
        print("Этот скрипт требует Python версии 3.9 или выше.")
        sys.exit(1)

    conf = __cli_vars(d.load_config("config.yaml")['drawio2seaf'])
    diagram.from_file(filename=conf['drawio_file'])
    objects_data = {}

    # Формируем dict из объектов диаграмм
    for i, (key, value) in enumerate(diagram.nodes_ids.items()):
        #value = value if i > 0 else list(set(value) - {"0101", "0103"})
        diagram.go_to_diagram(diagram_index=i)
        for object_id in list(set(value) - {'0101', '0103'}):
            objects_data.update(get_tag_attr(diagram.current_root.find("./*[@id='{}']".format(object_id))))
    #print(f' -------\n {json.dumps(objects_data)} --------------\n')

    # Извлекаем схемы объектов SEAF
    schemas = d.read_object_file(schema_file)
    # Выделить базовые компоненты для services/components
    entity = schemas.pop('seaf.ta.services.entity')['schema']['$defs'] | schemas.pop('seaf.ta.components.entity')['schema']['$defs']

    # Формируем JSON-схемы объектов SEAF
    for i, schema in schemas.items():
        target_schema = schema['schema']
        for pattern, value in target_schema['patternProperties'].items():
            if '$ref' in value:
                value.update(entity[value.pop("$ref").rsplit('/', 1)[-1]])
                print(f'==== >>>> {value}')
        print(json.dumps({i:target_schema}, ensure_ascii=False, indent=4))


