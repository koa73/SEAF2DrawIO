import sys
import yaml
import json
import re
import os
import argparse
from copy import deepcopy
from N2G import drawio_diagram
import html
from jsonschema import validate, ValidationError
import xml.etree.ElementTree as ET

class SeafDrawio:

    def __init__(self, default_config):
        """
        Инициализация загрузчика конфигурации.
        :param default_config: Словарь с конфигурацией по умолчанию.
        """
        self.default_config = default_config

    def load_config(self, config_file):
        """
        Загружает конфигурацию из YAML-файла и объединяет её с конфигурацией по умолчанию.
        :param config_file: Путь к YAML-файлу.
        :return: Итоговая конфигурация.
        """
        try:
            with open(config_file, 'r') as file:
                user_config = yaml.safe_load(file) or {}
        except FileNotFoundError:
            print(f"Файл {config_file} не найден. Используются значения по умолчанию.")
            user_config = {}

        return self._merge_configs(deepcopy(self.default_config), user_config)

    def _merge_configs(self, default, user):
        """
        Рекурсивно объединяет две конфигурации.
        :param default: Конфигурация по умолчанию.
        :param user: Пользовательская конфигурация.
        :return: Объединённая конфигурация.
        """
        for key, value in user.items():
            if isinstance(value, dict) and key in default:
                self._merge_configs(default[key], value)
            else:
                default[key] = value
        return default

    @staticmethod
    def read_object_file(file, **kwargs):
        try:
            with open(file, 'r') as file:
                try:
                    docs = yaml.safe_load_all(file)
                    for doc in docs:
                        return doc

                except yaml.YAMLError as e:
                    print("YAML error: {0}".format(e))

        except IOError as e:
            print("I/O error({0}): {1} : {2}".format(e.errno, e.strerror, file))
            sys.exit(1)

    @staticmethod
    def append_to_dict(d, key, value):
        try:
            if value not in d[key]:
                d[key].append(value)

        except KeyError:
            d[key] = []
            d[key].append(value)

    def find_key_value(self, data, target_key):
        """
        Recursively search for values associated with the given key in a nested JSON/dictionary.

        :param data: The JSON/dictionary to search through.
        :param target_key: The key to search for.
        :return: A list of values associated with the target key.
        """
        results = []

        # If the current data is a dictionary
        if isinstance(data, dict):
            for key, value in data.items():
                if key == target_key:
                    results.append(value)  # Add the value if the key matches
                if isinstance(value, (dict, list)):
                    results.extend(self.find_key_value(value, target_key))  # Recurse into nested structures

        # If the current data is a list
        elif isinstance(data, list):
            for item in data:
                results.extend(self.find_key_value(item, target_key))  # Recurse into each item in the list

        return results

    def find_value_by_key(self, data, target_key):
        """
        Recursively search for a value by key in a nested dictionary.

        :param data: The dictionary or list to search within
        :param target_key: The key to search for
        :return: The value associated with the target_key, or None if not found
        """
        if isinstance(data, dict):  # If the current item is a dictionary
            if target_key in data:  # Check if the target_key exists in this dictionary
                return data[target_key]
            for value in data.values():  # Recursively search in the values of the dictionary
                result = self.find_value_by_key(value, target_key)
                if result is not None:
                    return result
        elif isinstance(data, list):  # If the current item is a list
            for item in data:  # Recursively search in each item of the list
                result = self.find_value_by_key(item, target_key)
                if result is not None:
                    return result
        return None  # Return None if the key is not found

    @staticmethod
    def contains_object_tag(input_string, tag):
        """
                This function is useful when you need to quickly verify if a specific XML/HTML tag exists
                at the beginning of a string. Checks whether a given string starts with an XML-like opening tag
                that matches a specified tag name

                :param input_string:
                :param tag:
                :return: True/False
        """
        pattern = rf"^<{tag}\b[^>]*>"

        # Use re.search to check for the pattern
        match = re.search(pattern, input_string)
        return bool(match)

    @staticmethod
    def get_xml_pattern(xml, name):
        """
            Modify pattern to list of xml objects

            :param xml: objects patten .
            :param name: name of current pattern.
            :return: list of objects.
        """

        wrapped_xml_string = f"<root>{xml}</root>"
        result = []
        try:
            root = ET.fromstring(wrapped_xml_string)
            for item in root:
                result.append(ET.tostring(item, encoding='unicode'))
            return result
        except ET.ParseError as e:
            print(f"Ошибка парсинга XML шаблона {name} : {e} ")

            return result

    @staticmethod
    def list_contain(l, k):
        """
            Check if l (list) not empty and contain first value equal to string or in another lis

            :param l: list.
            :param k: string or list for comparing.
            :return: boolean True/False.
        """
        if isinstance(k, str):
            return True if len(l) > 0 and l[0] == k else False
        elif isinstance(k, list):
            return True if len(l) > 0 and l[0] in k else False

    def get_object(self, file, key, **kwargs):
        """
            Get JSON leave from file by key

            :param file: input file name.
            :param key: key for finding sub JSON.
            :param kwargs['type'] find json which contain value in key, kwargs['sort'] sorting by key
            :return: json object.
        """
        x = json.loads(json.dumps(self.read_object_file(file)[key]))
        if kwargs.get('type'):

            if kwargs['type'].find(":") != -1:
                k1, v1 = kwargs['type'].split(':')
            else:
                k1, v1 = 'type', kwargs['type']

            r = {k2: v2 for k2, v2 in x.items() if self.list_contain(self.find_key_value(v2, k1), v1)}

            if kwargs.get('sort'):
                return dict(sorted(r.items(), key=lambda item: self.find_value_by_key(item[1], kwargs["sort"])))

            return r
        else:
            return x

    @staticmethod
    def create_validator(pattern):
        def validate_file_format(value):
            # Проверяем, соответствует ли значение заданному шаблону
            if not re.match(pattern, value):
                raise argparse.ArgumentTypeError(
                    f'Неверный формат: {value}. Ожидается соответствие шаблону {pattern}.')

            return value

        return validate_file_format

    @staticmethod
    def _get_tag_attr(root):
        """
                    Извлекает атрибуты XML-тега <object>, исключая определённые атрибуты, и формирует структурированный словарь.
                    :param root: xml.etree.ElementTree.Element
                        XML-элемент (тег), из которого извлекаются атрибуты. Ожидается, что это тег <object>.

                    :return: dict
                        Вложенный словарь со структурой:
                            {
                                'schema_value': {
                                    'OID_value': {
                                        'attribute_key_1': 'decoded_attribute_value_1',
                                        'attribute_key_2': 'decoded_attribute_value_2'
                                    }
                                }
                            }

                    Примечания:
                        - Атрибуты 'id', 'label', 'OID' и 'schema' не включаются в результирующий словарь на третьем уровне.
                        - Значения атрибутов декодируются с помощью `html.unescape` для преобразования HTML-сущностей в читаемый текст.
        """
        # Извлечение всех атрибутов тега <object>
        attributes = root.attrib

        # Исключение атрибутов 'id' и 'label'
        return {
            attributes['schema']: {attributes['OID']: {key: html.unescape(value) for key, value in attributes.items()
                                                       if key not in ['id', 'label', 'OID', 'schema']}}}

    def get_data_from_diagram(self, file_name):
        """
            Извлекает данные из диаграммы, представленной в файле, и формирует словарь с атрибутами объектов.

            Функция выполняет следующие шаги:
            1. Загружает диаграмму из указанного файла.
            2. Проходит по всем объектам диаграммы (по каждому листу и каждому объекту на листе).
            3. Извлекает атрибуты объектов с помощью функции `get_tag_attr`.
            4. Возвращает словарь, содержащий все собранные данные.

            :param file_name: str
                Путь к файлу диаграммы (например, .drawio файл).

            :return: dict
                Словарь, где ключи — это идентификаторы объектов, а значения — их атрибуты.
                Пример структуры:
                    {
                        'object_id_1': {'attr1': 'value1', 'attr2': 'value2'},
                        'object_id_2': {'attr1': 'value3', 'attr2': 'value4'}
                    }

            Примечания:
                - Первый лист диаграммы обрабатывается с исключением объектов с ID "0101" и "0103".
                - Для каждого объекта используется функция `get_tag_attr`, которая извлекает атрибуты из XML-тега.
            """
        diagram = drawio_diagram()
        diagram.from_file(filename=file_name)
        objects_data = {}

        # Формируем dict из объектов диаграмм
        for i, (key, value) in enumerate(diagram.nodes_ids.items()):
            value = value if i > 0 else list(set(value) - {"0101", "0103"})
            diagram.go_to_diagram(diagram_index=i)
            for object_id in value:
                objects_data.update(self._get_tag_attr(diagram.current_root.find("./*[@id='{}']".format(object_id))))
        return objects_data

    def _create_json_from_schema(self, schema):
        """
        Создает JSON-объект на основе переданной JSON-схемы.

        Функция рекурсивно обрабатывает схему и формирует пустой JSON-объект,
        соответствующий структуре и типам данных, описанным в схеме.

        :param schema: dict
            JSON-схема, описывающая структуру объекта. Схема должна содержать ключ "properties",
            где каждый ключ соответствует имени поля, а значение — его типу и дополнительным свойствам.

        :return: dict

        Примечания:
            - Поддерживаются типы данных: string, integer, boolean, array, object.
            - Для вложенных объектов ("object") функция вызывается рекурсивно.
            - Если тип данных не указан или не поддерживается, используется пустая строка ("").
        """
        # Initialize an empty JSON object
        json_obj = {}

        # Populate the JSON object based on the schema's properties
        if "properties" in schema:
            for key, prop in schema["properties"].items():
                if prop.get("type") and prop["type"] == "object" and "properties" in prop:
                    # Recursively create nested objects
                    json_obj[key] = self._create_json_from_schema(prop)
                elif prop.get("type"):
                    # Initialize basic types (e.g., string, integer, etc.)
                    if prop["type"] == "string":
                        json_obj[key] = ""
                    elif prop["type"] == "integer":
                        json_obj[key] = 0
                    elif prop["type"] == "boolean":
                        json_obj[key] = False
                    elif prop["type"] == "array":
                        json_obj[key] = []
                    # elif prop["type"] == "object":
                    #    json_obj[key] = {}
                    # Add more types as needed
                else:
                    json_obj[key] = ""

        return json_obj

    def get_json_schemas(self, schema_file):
        """
            Извлекает и преобразует JSON-схемы объектов SEAF из файла схем.

            Функция выполняет следующие шаги:
            1. Загружает схемы объектов SEAF из указанного файла.
            2. Выделяет базовые компоненты для services/components из соответствующих схем.
            3. Обрабатывает каждую схему, заменяя ссылки ($ref) на соответствующие определения свойств.
            4. Формирует итоговый словарь JSON-схем объектов SEAF.

            :param schema_file: str
                Путь к файлу, содержащему схемы объектов SEAF (например, YAML или JSON).

            :return: dict
                Словарь JSON-схем объектов SEAF, где:
                - Ключи — это имена схем (например, 'seaf.ta.services.dc_region').
                - Значения — это JSON-схемы, преобразованные в формат Python-словаря.

            Примечания:
                - Базовые компоненты объединяются из схем 'seaf.ta.services.entity' и 'seaf.ta.components.entity'.
                - Ссылки ($ref) в схемах заменяются на соответствующие определения свойств.
                - Для создания JSON-схем используется функция `create_json_from_schema`.
            """

        # Извлекаем схемы объектов SEAF
        schemas = self.read_object_file(schema_file)
        # Выделить базовые компоненты для services/components
        entity = schemas.pop('seaf.ta.services.entity')['schema']['$defs'] | \
                 schemas.pop('seaf.ta.components.entity')['schema']['$defs']

        # Формируем JSON-схемы объектов SEAF
        result = {}
        for i, schema in schemas.items():
            target_schema = schema['schema']['patternProperties']
            pattern = ''
            for pattern, value in target_schema.items():
                if '$ref' in value:
                    value['properties'] = entity[value.pop("$ref").rsplit("/", 1)[-1]]['properties'] | value['properties']
                    #value['properties'].update(entity[value.pop("$ref").rsplit("/", 1)[-1]]['properties'])
            result.update({i: self._create_json_from_schema(target_schema[pattern])})

        return result

    @staticmethod
    def write_to_yaml_file(file_name, data):
        try:
            # Попытка записи словаря в YAML-файл
            with open(file_name, "w", encoding="utf-8") as file:
                for i, (key, value) in enumerate(data.items()):
                    if i > 0:
                        file.write("\n")  # Добавляем пустую строку перед каждым ключом, кроме первого
                    yaml.dump({key: value}, file, allow_unicode=True, sort_keys=False)

            print(f'Данные успешно записаны в файл {file_name}')

        except IOError as e:

            # Обработка ошибок ввода-вывода (например, отсутствие прав доступа к файлу)
            print(f"Ошибка записи в файл: {e}")

        except yaml.YAMLError as e:
            # Обработка ошибок, связанных с форматированием YAML
            print(f"Ошибка при сериализации данных в YAML: {e}")

        except Exception as e:
            # Обработка всех остальных исключений
            print(f"Произошла непредвиденная ошибка: {e}")

    def remove_empty_fields(self, data):
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
                key: self.remove_empty_fields(value)
                for key, value in data.items()
                if value or isinstance(value, bool)  # Оставляем только непустые значения
            }
        elif isinstance(data, list):
            # Если значение — список, рекурсивно очищаем каждый элемент
            return [self.remove_empty_fields(item) for item in data if item]
        else:
            # Возвращаем значение, если оно не является словарем или списком
            return data

    @staticmethod
    def validate_json(json_obj, schema, i):
        """
        Проверяет JSON-объект на соответствие заданной JSON-схеме.

        Эта функция использует метод `jsonschema.validate` для проверки, соответствует ли предоставленный
        JSON-объект указанной схеме. Если валидация не проходит, функция перехватывает исключение
        ValidationError и выводит сообщение об ошибке с деталями о проблеме.

        Параметры:
        ----------
        json_obj : dict
            JSON-объект, который нужно проверить. Должен быть представлен в виде словаря Python.

        schema : dict
            JSON-схема, по которой выполняется проверка. Должна быть представлена в виде словаря Python,
            описывающего структуру, типы данных и ограничения для JSON-объекта.

        i : int или str
            Идентификатор JSON-объекта, используемый для идентификации объекта в сообщениях об ошибках.
            Может быть числом (например, индексом) или строкой (например, именем).

        Примечания:
        ------------
        - Убедитесь, что библиотека `jsonschema` установлена (`pip install jsonschema`).
        - Схема должна соответствовать стандарту JSON Schema (https://json-schema.org/).
        """
        try:
            validate(instance=json_obj, schema=schema)
        except ValidationError as e:
            print(f"Object {i} Validation error: {e}")


class ValidateFile(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not os.path.isfile(values):
            raise argparse.ArgumentTypeError(f"Файл не найден: {values}")
        if not os.access(values, os.R_OK):
            raise argparse.ArgumentTypeError(f"Файл недоступен для чтения: {values}")
        setattr(namespace, self.dest, values)
