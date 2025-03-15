from copy import deepcopy
import ast
from lib import seaf_drawio
from N2G import drawio_diagram
import sys
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

def populate_json(json_schema, data):
    json_obj = deepcopy(json_schema)
    for key, value in data.items():
        if key in json_obj:
            if isinstance(value, dict) and isinstance(json_obj[key], dict):
                # Recursively populate nested objects
                populate_json(json_obj[key], value)

            else:
                if isinstance(json_obj[key], list):
                    json_obj[key] = ast.literal_eval(value)
                else:
                    # Assign values directly
                    json_obj[key] = value

    return json_obj

if __name__ == '__main__':

    if sys.version_info < (3, 9):
        print("Этот скрипт требует Python версии 3.9 или выше.")
        sys.exit(1)

    conf = __cli_vars(d.load_config("config.yaml")['drawio2seaf'])
    objects_data = d.get_data_from_diagram(conf['drawio_file'])
    json_schemas = d.get_json_schemas(schema_file)

    yaml_dict = {}
    for schema_key, schema in json_schemas.items():
        if schema_key == 'seaf.ta.components.network':
            print(schema_key)
            print(objects_data[schema_key])
        for d_key, d_val in objects_data[schema_key].items():
            #json_object = populate_json(schema, d_val)
            #d.validate_json(d.remove_empty_fields(json_object), schema, d_key)
            #yaml_dict.update({schema_key:{d_key:remove_empty_fields(json_object)}})
            yaml_dict = d.merge_dicts(yaml_dict,{schema_key: {d_key: d.remove_empty_fields(populate_json(schema, d_val))}})

    #print(yaml_dict)
    d.write_to_yaml_file(conf['output_file'], yaml_dict)




