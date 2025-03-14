from copy import deepcopy

from lib import seaf_drawio
from N2G import drawio_diagram
import sys
import argparse
from jsonschema import validate, ValidationError

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

def populate_json(json_schema, data):
    json_obj = deepcopy(json_schema)
    for key, value in data.items():
        if key in json_obj:
            if isinstance(value, dict) and isinstance(json_obj[key], dict):
                # Recursively populate nested objects
                populate_json(json_obj[key], value)
            else:
                # Assign values directly
                json_obj[key] = value

    return json_obj

def remove_empty_fields(data):
    """
    Рекурсивно удаляет пустые поля из словаря.
    Удаляются:
    - Пустые строки ('')
    - Пустые списки ([])
    - Пустые словари ({})
    - Значения None
    """
    if isinstance(data, dict):
        # Создаем новый словарь, исключая пустые значения
        return {
            key: remove_empty_fields(value)
            for key, value in data.items()
            if value or isinstance(value, bool)  # Оставляем только непустые значения
        }
    elif isinstance(data, list):
        # Если значение — список, рекурсивно очищаем каждый элемент
        return [remove_empty_fields(item) for item in data if item]
    else:
        # Возвращаем значение, если оно не является словарем или списком
        return data

def validate_json(json_obj, schema, i):
    try:
        validate(instance=json_obj, schema=schema)
    except ValidationError as e:
        print(f"Object {i} Validation error: {e}")



if __name__ == '__main__':

    if sys.version_info < (3, 9):
        print("Этот скрипт требует Python версии 3.9 или выше.")
        sys.exit(1)

    conf = __cli_vars(d.load_config("config.yaml")['drawio2seaf'])
    objects_data = d.get_data_from_diagram(conf['drawio_file'])
    json_schemas = d.get_json_schemas(schema_file)

    yaml_dict = {}
    for schema_key, schema in json_schemas.items():
        for d_key, d_val in objects_data[schema_key].items():
            #json_object = populate_json(schema, d_val)
            #validate_json(remove_empty_fields(json_object), schema, d_key)
            #yaml_dict.update({schema_key:{d_key:remove_empty_fields(json_object)}})
            yaml_dict.update({schema_key: {d_key: remove_empty_fields(populate_json(schema, d_val))}})

    #print(yaml_dict)
    d.write_to_yaml_file(conf['output_file'], yaml_dict)




