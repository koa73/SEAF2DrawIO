import xml.etree.ElementTree as ET
from N2G import drawio_diagram

def find_parent(root, target):
    """Находит родительский элемент для target в дереве root"""
    for elem in root.iter():
        for child in list(elem):
            if child is target:
                return elem
    return None

def collect_data_links(object_data):
    """
    Собирает все связи из данных объекта.
    Проверяет различные возможные поля для связей.
    """
    data_links = set()
    
    for source_id, targets in object_data.items():
        # Проверяем разные возможные ключи для связей
        possible_keys = ['location', 'network_connection', 'connections', 'links']
        
        for key in possible_keys:
            if key in targets:
                connections = targets[key]
                # Убедимся, что это список
                if not isinstance(connections, list):
                    connections = [connections]
                
                for target_id in connections:
                    # Используем кортеж (source, target) как ключ
                    # Учитываем, что связи двунаправленные
                    link_key = tuple(sorted([source_id, target_id]))
                    data_links.add(link_key)
                    
    return data_links

def remove_obsolete_links(diagram, data_file, schema_key):
    """
    Удаляет связи из диаграммы, которые отсутствуют в новых данных.
    
    :param diagram: Экземпляр drawio_diagram
    :param data_file: Путь к YAML-файлу с данными
    :param schema_key: Ключ схемы для поиска связей в данных
    """
    # Получаем все связи из диаграммы
    existing_links = {}
    
    # Работаем напрямую с XML-деревом диаграммы
    root = diagram.drawing
    
    # Ищем все элементы object с атрибутом edge (связи)
    for obj in root.iter('object'):
        cell = obj.find('mxCell')
        if cell is not None and cell.get('edge') == '1':
            source = cell.get('source')
            target = cell.get('target')
            if source and target:
                # Используем кортеж (source, target) как ключ
                # Учитываем, что связи двунаправленные
                link_key = tuple(sorted([source, target]))
                existing_links[link_key] = obj.get('id')
    
    # Получаем связи из новых данных
    from lib import seaf_drawio
    
    # Загружаем данные
    d = seaf_drawio.SeafDrawio({})
    
    # Для компонентов используем другую схему
    if schema_key == 'seaf.ta.components.network':
        object_data = d.get_object(data_file, schema_key)
        # Собираем связи из данных
        data_links = collect_data_links(object_data)
    else:
        # Для других схем используем оригинальный подход
        object_data = d.get_object(data_file, schema_key)
        # Собираем связи из данных
        data_links = collect_data_links(object_data)
    
    # Определяем связи для удаления
    links_to_remove = set(existing_links.keys()) - data_links
    
    # Выводим информацию о связях, которые будут удалены
    if links_to_remove:
        print(f"Удаляем {len(links_to_remove)} устаревших связей:")
        for link_key in links_to_remove:
            print(f"  {link_key[0]} -> {link_key[1]}")
    else:
        print("Нет устаревших связей для удаления.")
    
    # Удаляем устаревшие связи напрямую из XML
    for link_key in links_to_remove:
        link_id = existing_links[link_key]
        # Находим и удаляем элемент object с соответствующим ID
        for obj in root.findall('.//object[@id="{}"]'.format(link_id)):
            # Находим родителя и удаляем из него
            parent = find_parent(root, obj)
            if parent is not None:
                parent.remove(obj)