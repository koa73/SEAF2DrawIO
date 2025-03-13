import sys
import yaml
import json
import re
import os
import argparse
from copy import deepcopy
from itertools import chain
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
    def dict_list_merging(nodes_ids):
        """
            Объединяет все элементы из словаря, содержащего списки, удаляет дубликаты и возвращает отсортированный список уникальных элементов.

            :param nodes_ids: dict
                Словарь, где ключи — строки (идентификаторы или названия), а значения — списки строк.
                Пример:
                    {
                        'group1': ['item1', 'item2'],
                        'group2': ['item2', 'item3']
                    }
            :return: list
                Отсортированный список уникальных элементов, объединённых из всех списков в словаре.
                Пример:
                    ['item1', 'item2', 'item3']
        """
        all_items = list(chain.from_iterable(nodes_ids.values()))
        unique_items = list(set(all_items) - {'0101', '0103'})
        sorted_unique_items = sorted(unique_items)
        return sorted_unique_items

class ValidateFile(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not os.path.isfile(values):
            raise argparse.ArgumentTypeError(f"Файл не найден: {values}")
        if not os.access(values, os.R_OK):
            raise argparse.ArgumentTypeError(f"Файл недоступен для чтения: {values}")
        setattr(namespace, self.dest, values)