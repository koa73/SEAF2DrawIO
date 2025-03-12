# Скрипт для конвертации объектов SEAF TA в объекты DrawIO 

 - seaf2drawio.py  - скрипт для конвертации yaml объектов метамодели SEAF в объекты DrawIO для автоматизации процесса 
                     формирования диаграммы технической архитектуры ( схема Р41 )

### Для начала работы необходимо 

 1. Наличие Python версии 3.9 и выше
 2. Установить следующие пакеты : 
     ###### pip install N2G
     ###### pip install pyaml
 
### Конфигурация работы скрипта  
  Конфигурация скрипта осуществляется путем изменения переменных в файле config.yaml
  
| Переменная           | Назначение                                                                                     |
|----------------------|------------------------------------------------------------------------------------------------|
| ***data_yaml_file*** | Файл описания объектов SEAF <br/>(default: .data/example/test_seaf_ta_P41_v0.5.yaml)           |
| ***drawio_pattern*** | Шаблон Draw IO  файла используемый для постраения диаграммы.<br/>(default: .data/base.drawio)  | 
| ***output_file***    | Файл Draw IO диаграммы сформированной скриптом.<br/>(default: .result/Sample_graph.drawio)     |

###### * Если переменные в файле не заполнены, то по умолчанию используются default значения.
###### * Еслм вместо входного шаблона Draw IO (.data/base.drawio) использовать файл с ранее сформированной скриптом диаграммы Р41,то скрипт не изменит ранее сделанную разметку объекто, а только обноовит данные существующих объектов и дополнит новыми объектами из yaml файла.

#### Переменные конфигурации скрипта можно установить в командной строке в следующем виде:

###### usage: seaf2drawio.py [-h] [-s SRC] [-d DST] [-p PATTERN]

###### Параметры командной строки.

###### options:
######  -h, --help            show this help message and exit
######  -s SRC, --src SRC     файл данных SEAF
######  -d DST, --dst DST     путь и имя файла вывода результатов
######  -p PATTERN, --pattern PATTERN шаблон drawio

#### Переменные командной строки имеют приоритет перед переменными файла конфигурации.

### Порядок описания объекто SEAF для корректной работы скрипта

###### Описание объектов необходимо осуществлять в следующей последовательности, сначало создается родительский (parent) объект, затем дочерние (child) ссылающийся на родителя
    -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    |- Регион                                   - seaf.ta.services.dc_region
    |  |- Зона домтупности                      - seaf.ta.services.dc_az
    |  |  |- Офис/ЦОД                           - seaf.ta.services.office / seaf.ta.services.dc
    |  |  |  |- Зоны безопасности               - seaf.ta.services.network_segment (type : см. модель SEAF)
    |  |  |  |  |- Сети                         - seaf.ta.services.network (type: 'LAN')
    |  |  |  |  |- Провыйдеры услуг связи (ISP) - seaf.ta.services.network (type: 'WAN')
    |  |  |  |  |- Сетевые устройства           - seaf.ta.components.network (type : см. модель SEAF)

######  * Типы зон безопасности и сетевых устройст описываются в модели SEAF, описание объектов можно посмотреть в файле примере (.data/example/test_seaf_ta_P41_v0.5.yaml)

###### * Связывание объекто осуществляется через атрибут ***network_connection*** объекта описания сетевого устройства ***seaf.ta.components.network***

##### * Внимание ! На диаграмме "Main Schema" объекты ISP  перекрывают друг друга, необходимо это учитывать