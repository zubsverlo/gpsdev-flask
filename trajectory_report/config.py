import os
import dotenv


dotenv.load_dotenv()

if os.getenv("ENV") == "production":
    DB = os.getenv("DATABASE_PRODUCTION")
    ASYNC_DB = os.getenv("ASYNC_DATABASE_PRODUCTION")
    REDIS = os.getenv("REDIS")
else:
    DB = os.getenv("DATABASE_DEVELOPMENT")
    ASYNC_DB = os.getenv("ASYNC_DATABASE_DEVELOPMENT")
    REDIS = os.getenv("REDIS_DEVELOPMENT")


TOKENS_MTS = {
    "ГССП": os.getenv("TOKEN_MTS_GSSP"),
    "Вера": os.getenv("TOKEN_MTS_VERA"),
    "Линия Жизни": os.getenv("TOKEN_MTS_LZH"),
}

TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")

# Параметры для генерации кластеров (ClusterGenerator.py)
# STAY_LOCATIONS - параметры формирования остановок
# CLUSTERS - параметры формирования кластеров
CLUSTERS_MTS = dict()

# Кол-во минут на одном месте, чтобы сформировать остановку.
# Стандарт: 2
CLUSTERS_MTS["minutes_for_a_stop"] = 2
# После какого кол-ва минут отсутствия данных считать остановку прерванной.
# Стандарт: 360
CLUSTERS_MTS["no_data_for_minutes"] = 360
# Радиус в км, по которому объединять локации в одну остановку
# Стандарт: 0.8
CLUSTERS_MTS["spatial_radius_km"] = 0.3
# В каком радиусе объединять остановки в кластер
# Стандарт: 0.3
CLUSTERS_MTS["cluster_radius_km"] = 0.3


# Параметры генерации кластеров и остановок для owntracks
CLUSTERS_OWNTRACKS = dict()

CLUSTERS_OWNTRACKS["minutes_for_a_stop"] = 2
CLUSTERS_OWNTRACKS["no_data_for_minutes"] = 60
CLUSTERS_OWNTRACKS["spatial_radius_km"] = 0.10
CLUSTERS_OWNTRACKS["cluster_radius_km"] = 0.10


# Основные параметры для формирования отчета:
REPORT_BASE = dict()
# Радиус, который считается приемлемым между координатами кластера
# и координатами объекта, чтобы считать это посещением.
REPORT_BASE["RADIUS_MTS"] = 500
REPORT_BASE["RADIUS_OWNTRACKS"] = 160

# Длительность в минутах между посещениями, чтобы считать их отдельными.
# Например, если сотрудник пришел, затем ушёл и вернулся.
# Сколько он должен отсутствовать у подопечного, что разорвать его посещение
# На 2 отдельных? Если перерыв меньше указанного числа - перерыв учитывается в
# длительности посещения.
REPORT_BASE["MINS_BETWEEN_ATTENDS"] = 40


# Параметры, определяющие, есть ли у сотрудника проблемы с локациями.
# Эти параметры применяются при формировании анализа локаций сотрудника
# в report.Report.OneEmployeeReport.
# На основании таблицы stats принимается решение, нужно ли направить
# сотрудника для решения проблем с локациями.
# На проблемы указывает любой из двух вариантов:
#  1. Период неактивности в процентом соотношении больше, чем активности
#  и количество переходов между состояниями больше COUNT.
#  2. Средняя длительность активности телефона меньше MINUTES.
STATS_CHECKOUT = dict()
STATS_CHECKOUT["MINUTES"] = 60
STATS_CHECKOUT["COUNT"] = 4


# Количество минут, которое считается достаточным, чтобы посчитать перерыв
# между локациями длинным и отобразить его в анализе локаций как бездействующий
LONG_PERIOD = 25
