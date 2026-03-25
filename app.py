from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import logging
import random
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from io import BytesIO
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
PAGES_FILE = os.path.join(DATA_DIR, 'pages.json')
LOGS_FILE = os.path.join(DATA_DIR, 'logs.json')
STATS_FILE = os.path.join(DATA_DIR, 'stats.json')
QURAN_FILE = os.path.join(DATA_DIR, 'quran_progress.json')
CALENDAR_FILE = os.path.join(DATA_DIR, 'content_calendar.json')
WEEKLY_FILE = os.path.join(DATA_DIR, 'weekly_stats.json')

os.makedirs(DATA_DIR, exist_ok=True)
scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Riyadh'))

UNSPLASH_KEY = 'gZrefpx0NIcCATHYfGXq873vRehUuDMWEdZw0JH-rOY'

POST_TYPES = {
    # 📖 القرآن الكريم
    'quran_ayah':        'آية اليوم',
    'quran_tafseer':     'تفسير القرآن بالترتيب',
    'quran_recitation':  'تلاوة وتفسير',
    'quran_khatma':      'ختمة قرآنية',
    'quran_ijaz':        'إعجاز القرآن العلمي',
    # 🕌 السيرة النبوية
    'seerah_birth':      'مولد النبي وطفولته',
    'seerah_manners':    'أخلاق النبي وصفاته',
    'seerah_miracles':   'معجزات النبي',
    'seerah_battles':    'غزوات النبي وبطولاته',
    'seerah_companions': 'النبي مع أصحابه',
    'seerah_love':       'حب النبي والشوق إليه',
    # ⚔️ فتوحات ومعارك الإسلام
    'battles_badr':      'غزوة بدر الكبرى',
    'battles_uhud':      'غزوة أحد والثبات',
    'battles_khandaq':   'غزوة الخندق والتخطيط',
    'battles_mecca':     'فتح مكة المكرمة',
    'battles_history':   'فتوحات إسلامية تاريخية',
    'battles_heroism':   'بطولات إسلامية خالدة',
    # 👳 قصص الأنبياء
    'prophet_adam':      'قصة سيدنا آدم',
    'prophet_ibrahim':   'قصة سيدنا إبراهيم',
    'prophet_musa':      'قصة سيدنا موسى',
    'prophet_yusuf':     'قصة سيدنا يوسف',
    'prophet_isa':       'قصة سيدنا عيسى',
    'prophet_miracles':  'معجزات الأنبياء',
    'prophet_lessons':   'عبر ودروس الأنبياء',
    # 🌟 قصص الصحابة
    'sahabi_abubakr':    'سيدنا أبو بكر الصديق',
    'sahabi_umar':       'سيدنا عمر بن الخطاب',
    'sahabi_uthman':     'سيدنا عثمان بن عفان',
    'sahabi_ali':        'سيدنا علي بن أبي طالب',
    'sahabi_heroism':    'بطولات الصحابة',
    'sahabi_islam':      'قصص إسلام الصحابة',
    'sahabi_sahabiyat':  'قصص الصحابيات الكريمات',
    # 🌹 نساء الإسلام
    'women_khadijah':    'السيدة خديجة أم المؤمنين',
    'women_aisha':       'السيدة عائشة الصديقة',
    'women_fatima':      'السيدة فاطمة الزهراء',
    'women_maryam':      'السيدة مريم العذراء',
    'women_heroes':      'بطلات وعالمات الإسلام',
    # 🛡️ الإسلام وحفظ الإنسان
    'islam_dignity':     'الإسلام وكرامة الإنسان',
    'islam_family':      'الإسلام وحفظ الأسرة',
    'islam_mind':        'الإسلام وحفظ العقل',
    'islam_honor':       'الإسلام وصون العرض والعفاف',
    'islam_wealth':      'الإسلام وحفظ المال',
    'islam_rights':      'حقوق الإنسان في الإسلام',
    'islam_justice':     'العدل في الإسلام',
    'islam_mercy':       'الرحمة في الإسلام',
    # 🧠 العلم والحضارة الإسلامية
    'civilization_science': 'علماء الإسلام وإنجازاتهم',
    'civilization_golden':  'الحضارة الإسلامية الذهبية',
    'civilization_medicine':'الطب الإسلامي عبر التاريخ',
    'civilization_andalus': 'الأندلس ومجد الإسلام',
    # 💎 الأخلاق والتزكية
    'akhlaq_patience':   'الصبر والثبات في الإسلام',
    'akhlaq_shukr':      'الشكر والقناعة',
    'akhlaq_tawakkul':   'التوكل على الله',
    'akhlaq_ikhlas':     'الإخلاص والصدق',
    'akhlaq_rehma':      'الرحمة والتراحم',
    # 🤲 الأذكار والأدعية
    'adhkar_morning':    'أذكار الصباح',
    'adhkar_evening':    'أذكار المساء',
    'adhkar_sleep':      'أذكار النوم',
    'adhkar_home':       'أذكار البيت',
    'duaa_hardship':     'دعاء الكرب والضيقة',
    'duaa_rizq':         'دعاء الرزق والفرج',
    'duaa_healing':      'دعاء الشفاء',
    'duaa_parents':      'دعاء الوالدين',
    'duaa_short':        'دعاء قصير مؤثر',
    # 📚 الفقه والعلم
    'friday_khutba':     'خطبة الجمعة',
    'fiqh_lesson':       'درس فقهي',
    'fatwa':             'فتوى شرعية',
    'ibadah_ruling':     'أحكام العبادات',
    'hadith_sahih':      'حديث نبوي صحيح',
    'islamic_fact':      'معلومة إسلامية مثيرة',
    # 😢 قصص إيمانية مؤثرة
    'story_tawba':       'قصة توبة مؤثرة',
    'story_good_end':    'قصة حسن الخاتمة',
    'story_karama':      'قصة كرامات الصالحين',
    'story_duaa_answered':'قصة استجابة الدعاء',
    'story_hidaya':      'قصة هداية مؤثرة',
    # 🌙 المناسبات الدينية
    'ramadan':           'محتوى رمضان',
    'eid':               'محتوى العيدين',
    'hajj_umrah':        'الحج والعمرة',
    'islamic_wisdom':    'حكمة إسلامية',
}

# الفئات الرئيسية - الموقع يختار تلقائياً
POST_CATEGORIES = {
    '📖 القرآن الكريم':          ['quran_ayah','quran_tafseer','quran_recitation','quran_khatma','quran_ijaz'],
    '🕌 السيرة النبوية':          ['seerah_birth','seerah_manners','seerah_miracles','seerah_battles','seerah_companions','seerah_love'],
    '⚔️ فتوحات ومعارك الإسلام':  ['battles_badr','battles_uhud','battles_khandaq','battles_mecca','battles_history','battles_heroism'],
    '👳 قصص الأنبياء':            ['prophet_adam','prophet_ibrahim','prophet_musa','prophet_yusuf','prophet_isa','prophet_miracles','prophet_lessons'],
    '🌟 قصص الصحابة':             ['sahabi_abubakr','sahabi_umar','sahabi_uthman','sahabi_ali','sahabi_heroism','sahabi_islam','sahabi_sahabiyat'],
    '🌹 نساء الإسلام':            ['women_khadijah','women_aisha','women_fatima','women_maryam','women_heroes'],
    '🛡️ الإسلام وحفظ الإنسان':   ['islam_dignity','islam_family','islam_mind','islam_honor','islam_wealth','islam_rights','islam_justice','islam_mercy'],
    '🧠 الحضارة الإسلامية':       ['civilization_science','civilization_golden','civilization_medicine','civilization_andalus'],
    '💎 الأخلاق والتزكية':        ['akhlaq_patience','akhlaq_shukr','akhlaq_tawakkul','akhlaq_ikhlas','akhlaq_rehma'],
    '🤲 الأذكار والأدعية':        ['adhkar_morning','adhkar_evening','adhkar_sleep','adhkar_home','duaa_hardship','duaa_rizq','duaa_healing','duaa_parents','duaa_short'],
    '📚 الفقه والعلم الشرعي':     ['friday_khutba','fiqh_lesson','fatwa','ibadah_ruling','hadith_sahih','islamic_fact'],
    '😢 قصص إيمانية مؤثرة':      ['story_tawba','story_good_end','story_karama','story_duaa_answered','story_hidaya'],
    '🌙 المناسبات الدينية':        ['ramadan','eid','hajj_umrah','islamic_wisdom'],
    '🔢 سلاسل يومية':             ['allah_name','aya_taammul','hadith_daily'],
    '💬 تفاعلي وجذاب':            ['dini_question','complete_aya','who_is_sahabi','islamic_did_you_know'],
    '🌙 محتوى وقت محدد':          ['fajr_duaa','night_reminder','salah_reminder'],
    '📚 تعليمي متسلسل':           ['islam_pillars','jannah_description','judgment_signs'],
    '🤲 روحاني عميق':             ['creation_reflection','islam_answers','if_prophet_era'],
    '📿 سلاسل قرآنية':            ['quran_numeric_ijaz','surah_story','quran_word_deep'],
    '⚡ محتوى صادم ومثير':        ['islam_before_science','non_muslims_about_islam','shocking_islam_facts'],
    '🌍 الإسلام في العالم':        ['muslims_worldwide','revert_story','islam_in_numbers'],
    '💪 الإسلام وتحديات الحياة':  ['islam_depression','islam_success','islam_health'],
    '🌺 الأسرة والمجتمع':          ['parents_rights','islamic_parenting','marriage_islam'],
    '✈️ رحلات إسلامية':            ['journey_mecca','journey_madina','journey_mosque'],
    '💌 رسائل إيمانية':            ['letter_hardship','letter_away_from_allah','letter_youth'],
    '🔥 تحفيز وإلهام':             ['muslim_success','daily_word','daily_challenge','dont_give_up'],
    '📜 شعر وأدب إسلامي':          ['islamic_poetry','shafii_poetry','prophet_love_poetry','zuhd_poetry'],
    '💬 كلمات معبرة':              ['heart_sentence','scholar_quote','wise_men_words'],
    '⚖️ حكم وأمثال':              ['arabic_proverb','ancestors_wisdom','daily_wisdom'],
}

# ===== جداول النشر الجاهزة =====
# كل جدول = 24 موعد (كل ساعة) مع فئة مخصصة
SCHEDULE_TEMPLATES = {
    "📖 جدول القرآن": {
        "desc": "يركز على القرآن والتفسير والإعجاز",
        "hours": [
            (0,  "🤲 أدعية قصيرة مؤثرة"),
            (1,  "📖 القرآن الكريم"),
            (2,  "📖 القرآن الكريم"),
            (3,  "🤲 الأذكار والأدعية"),
            (4,  "🤲 الأذكار والأدعية"),
            (5,  "🤲 الأذكار والأدعية"),
            (6,  "📖 القرآن الكريم"),
            (7,  "📖 القرآن الكريم"),
            (8,  "📖 القرآن الكريم"),
            (9,  "📚 الفقه والعلم الشرعي"),
            (10, "📖 القرآن الكريم"),
            (11, "💬 تفاعلي وجذاب"),
            (12, "📖 القرآن الكريم"),
            (13, "📚 الفقه والعلم الشرعي"),
            (14, "📖 القرآن الكريم"),
            (15, "😢 قصص إيمانية مؤثرة"),
            (16, "📖 القرآن الكريم"),
            (17, "✈️ رحلات إسلامية"),
            (18, "📖 القرآن الكريم"),
            (19, "💎 الأخلاق والتزكية"),
            (20, "📖 القرآن الكريم"),
            (21, "💌 رسائل إيمانية"),
            (22, "⚖️ حكم وأمثال"),
            (23, "🤲 الأذكار والأدعية"),
        ]
    },
    "⚔️ جدول البطولات": {
        "desc": "يركز على الفتوحات والسيرة والبطولات",
        "hours": [
            (0,  "🤲 أدعية قصيرة مؤثرة"),
            (1,  "⚖️ حكم وأمثال"),
            (2,  "💬 كلمات معبرة"),
            (3,  "🤲 الأذكار والأدعية"),
            (4,  "🤲 الأذكار والأدعية"),
            (5,  "🤲 الأذكار والأدعية"),
            (6,  "🔢 سلاسل يومية"),
            (7,  "📖 القرآن الكريم"),
            (8,  "👳 قصص الأنبياء"),
            (9,  "🕌 السيرة النبوية"),
            (10, "⚔️ فتوحات ومعارك الإسلام"),
            (11, "🌟 قصص الصحابة"),
            (12, "💬 تفاعلي وجذاب"),
            (13, "⚔️ فتوحات ومعارك الإسلام"),
            (14, "🧠 الحضارة الإسلامية"),
            (15, "🕌 السيرة النبوية"),
            (16, "⚔️ فتوحات ومعارك الإسلام"),
            (17, "🌹 نساء الإسلام"),
            (18, "👳 قصص الأنبياء"),
            (19, "📜 شعر وأدب إسلامي"),
            (20, "🌟 قصص الصحابة"),
            (21, "💌 رسائل إيمانية"),
            (22, "🔥 تحفيز وإلهام"),
            (23, "🤲 الأذكار والأدعية"),
        ]
    },
    "🤲 جدول الروحانيات": {
        "desc": "يركز على الأذكار والأدعية والقصص المؤثرة",
        "hours": [
            (0,  "🤲 الأذكار والأدعية"),
            (1,  "💌 رسائل إيمانية"),
            (2,  "🤲 أدعية قصيرة مؤثرة"),
            (3,  "🤲 الأذكار والأدعية"),
            (4,  "🤲 الأذكار والأدعية"),
            (5,  "🤲 الأذكار والأدعية"),
            (6,  "📖 القرآن الكريم"),
            (7,  "🤲 الأذكار والأدعية"),
            (8,  "😢 قصص إيمانية مؤثرة"),
            (9,  "💫 قصص من الحياة اليومية"),
            (10, "🤲 الأذكار والأدعية"),
            (11, "📖 القرآن الكريم"),
            (12, "💬 تفاعلي وجذاب"),
            (13, "🤲 الأذكار والأدعية"),
            (14, "😢 قصص إيمانية مؤثرة"),
            (15, "💎 الأخلاق والتزكية"),
            (16, "🤲 الأذكار والأدعية"),
            (17, "✈️ رحلات إسلامية"),
            (18, "🤲 الأذكار والأدعية"),
            (19, "💌 رسائل إيمانية"),
            (20, "🤲 الأذكار والأدعية"),
            (21, "⚖️ حكم وأمثال"),
            (22, "💬 كلمات معبرة"),
            (23, "🤲 الأذكار والأدعية"),
        ]
    },
    "💡 جدول التحفيز": {
        "desc": "يركز على التحفيز والنجاح والشباب",
        "hours": [
            (0,  "🤲 أدعية قصيرة مؤثرة"),
            (1,  "⚖️ حكم وأمثال"),
            (2,  "💬 كلمات معبرة"),
            (3,  "🤲 الأذكار والأدعية"),
            (4,  "🤲 الأذكار والأدعية"),
            (5,  "🤲 الأذكار والأدعية"),
            (6,  "🔥 تحفيز وإلهام"),
            (7,  "📖 القرآن الكريم"),
            (8,  "🔥 تحفيز وإلهام"),
            (9,  "🕌 السيرة النبوية"),
            (10, "💡 المحتوى التحفيزي الديني"),
            (11, "💬 تفاعلي وجذاب"),
            (12, "🔥 تحفيز وإلهام"),
            (13, "💪 الإسلام وتحديات الحياة"),
            (14, "🔥 تحفيز وإلهام"),
            (15, "😢 قصص إيمانية مؤثرة"),
            (16, "💡 المحتوى التحفيزي الديني"),
            (17, "🔥 تحفيز وإلهام"),
            (18, "📜 شعر وأدب إسلامي"),
            (19, "💬 كلمات معبرة"),
            (20, "🔥 تحفيز وإلهام"),
            (21, "💌 رسائل إيمانية"),
            (22, "⚖️ حكم وأمثال"),
            (23, "🤲 الأذكار والأدعية"),
        ]
    },
    "📚 جدول العلم": {
        "desc": "يركز على الفقه والحديث والعلم الشرعي",
        "hours": [
            (0,  "🤲 أدعية قصيرة مؤثرة"),
            (1,  "⚖️ حكم وأمثال"),
            (2,  "📖 القرآن الكريم"),
            (3,  "🤲 الأذكار والأدعية"),
            (4,  "🤲 الأذكار والأدعية"),
            (5,  "🤲 الأذكار والأدعية"),
            (6,  "🔢 سلاسل يومية"),
            (7,  "📖 القرآن الكريم"),
            (8,  "📚 الفقه والعلم الشرعي"),
            (9,  "📚 الفقه والعلم الشرعي"),
            (10, "🧠 الحضارة الإسلامية"),
            (11, "💬 تفاعلي وجذاب"),
            (12, "📚 الفقه والعلم الشرعي"),
            (13, "📚 الفقه والعلم الشرعي"),
            (14, "🧠 الحضارة الإسلامية"),
            (15, "📚 الفقه والعلم الشرعي"),
            (16, "⚡ محتوى صادم ومثير"),
            (17, "🌍 الإسلام في العالم"),
            (18, "📚 الفقه والعلم الشرعي"),
            (19, "💎 الأخلاق والتزكية"),
            (20, "📚 الفقه والعلم الشرعي"),
            (21, "💌 رسائل إيمانية"),
            (22, "⚖️ حكم وأمثال"),
            (23, "🤲 الأذكار والأدعية"),
        ]
    },
    "🌙 جدول المتنوع": {
        "desc": "يشمل جميع الفئات بتوازن",
        "hours": [
            (0,  "🤲 أدعية قصيرة مؤثرة"),
            (1,  "⚖️ حكم وأمثال"),
            (2,  "💬 كلمات معبرة"),
            (3,  "🤲 الأذكار والأدعية"),
            (4,  "🤲 الأذكار والأدعية"),
            (5,  "🤲 الأذكار والأدعية"),
            (6,  "🔢 سلاسل يومية"),
            (7,  "📖 القرآن الكريم"),
            (8,  "👳 قصص الأنبياء"),
            (9,  "🕌 السيرة النبوية"),
            (10, "⚔️ فتوحات ومعارك الإسلام"),
            (11, "🌟 قصص الصحابة"),
            (12, "💬 تفاعلي وجذاب"),
            (13, "💪 الإسلام وتحديات الحياة"),
            (14, "🧠 الحضارة الإسلامية"),
            (15, "📚 الفقه والعلم الشرعي"),
            (16, "😢 قصص إيمانية مؤثرة"),
            (17, "✈️ رحلات إسلامية"),
            (18, "🔥 تحفيز وإلهام"),
            (19, "📜 شعر وأدب إسلامي"),
            (20, "🌺 الأسرة والمجتمع"),
            (21, "💌 رسائل إيمانية"),
            (22, "💬 كلمات معبرة"),
            (23, "🤲 الأذكار والأدعية"),
        ]
    },
}

# أيام الأسبوع للتنويع التلقائي بين الصفحات
ROTATION_DAYS = ["sun","mon","tue","wed","thu","fri","sat"]

PAGE_PERSONALITIES = {
    'spiritual': 'روحاني هادئ',
    'motivational': 'تحفيزي قوي',
    'educational': 'علمي تعليمي',
    'friendly': 'ودي مرح',
    'commercial': 'تجاري احترافي',
    'mixed': 'متنوع'
}

QURAN_SURAHS = [
    (1,'الفاتحة',7),(2,'البقرة',286),(3,'آل عمران',200),(4,'النساء',176),
    (5,'المائدة',120),(6,'الأنعام',165),(7,'الأعراف',206),(8,'الأنفال',75),
    (9,'التوبة',129),(10,'يونس',109),(11,'هود',123),(12,'يوسف',111),
    (13,'الرعد',43),(14,'إبراهيم',52),(15,'الحجر',99),(16,'النحل',128),
    (17,'الإسراء',111),(18,'الكهف',110),(19,'مريم',98),(20,'طه',135),
    (21,'الأنبياء',112),(22,'الحج',78),(23,'المؤمنون',118),(24,'النور',64),
    (25,'الفرقان',77),(26,'الشعراء',227),(27,'النمل',93),(28,'القصص',88),
    (29,'العنكبوت',69),(30,'الروم',60),(31,'لقمان',34),(32,'السجدة',30),
    (33,'الأحزاب',73),(34,'سبأ',54),(35,'فاطر',45),(36,'يس',83),
    (37,'الصافات',182),(38,'ص',88),(39,'الزمر',75),(40,'غافر',85),
    (41,'فصلت',54),(42,'الشورى',53),(43,'الزخرف',89),(44,'الدخان',59),
    (45,'الجاثية',37),(46,'الأحقاف',35),(47,'محمد',38),(48,'الفتح',29),
    (49,'الحجرات',18),(50,'ق',45),(51,'الذاريات',60),(52,'الطور',49),
    (53,'النجم',62),(54,'القمر',55),(55,'الرحمن',78),(56,'الواقعة',96),
    (57,'الحديد',29),(58,'المجادلة',22),(59,'الحشر',24),(60,'الممتحنة',13),
    (61,'الصف',14),(62,'الجمعة',11),(63,'المنافقون',11),(64,'التغابن',18),
    (65,'الطلاق',12),(66,'التحريم',12),(67,'الملك',30),(68,'القلم',52),
    (69,'الحاقة',52),(70,'المعارج',44),(71,'نوح',28),(72,'الجن',28),
    (73,'المزمل',20),(74,'المدثر',56),(75,'القيامة',40),(76,'الإنسان',31),
    (77,'المرسلات',50),(78,'النبأ',40),(79,'النازعات',46),(80,'عبس',42),
    (81,'التكوير',29),(82,'الانفطار',19),(83,'المطففين',36),(84,'الانشقاق',25),
    (85,'البروج',22),(86,'الطارق',17),(87,'الأعلى',19),(88,'الغاشية',26),
    (89,'الفجر',30),(90,'البلد',20),(91,'الشمس',15),(92,'الليل',21),
    (93,'الضحى',11),(94,'الشرح',8),(95,'التين',8),(96,'العلق',19),
    (97,'القدر',5),(98,'البينة',8),(99,'الزلزلة',8),(100,'العاديات',11),
    (101,'القارعة',11),(102,'التكاثر',8),(103,'العصر',3),(104,'الهمزة',9),
    (105,'الفيل',5),(106,'قريش',4),(107,'الماعون',7),(108,'الكوثر',3),
    (109,'الكافرون',6),(110,'النصر',3),(111,'المسد',5),(112,'الإخلاص',4),
    (113,'الفلق',5),(114,'الناس',6)
]

HASHTAGS = {
    'islamic': ['#إسلاميات','#ذكر_الله','#اللهم_صل_على_محمد','#الإسلام','#مسلمون','#ديننا_حياتنا'],
    'quran': ['#القرآن_الكريم','#تفسير_القرآن','#آيات_قرآنية','#نور_القرآن','#كلام_الله'],
    'hadith': ['#حديث_نبوي','#السنة_النبوية','#نبينا_محمد','#اللهم_صل_على_محمد'],
    'motivation': ['#تحفيز','#تطوير_الذات','#نجاح','#إيجابية','#همة'],
    'tips': ['#نصائح','#فائدة_اليوم','#معلومة','#تعلم_كل_يوم'],
    'offer': ['#عروض','#تسوق','#خصومات','#منتجات_مميزة'],
    'wisdom': ['#حكمة','#اقتباسات','#ثقافة','#أدب_عربي','#تأمل'],
    'general': ['#عربي','#محتوى_عربي'],
    'story': ['#قصص','#حكايات','#قصة','#روايات','#اقرأ'],
    'comedy': ['#كوميدي','#ضحك','#فكاهة','#نكت','#مضحك'],
    'drama': ['#دراما','#تشويق','#غرائب','#عجائب','#مثير'],
    'documentary': ['#معلومات','#ثقافة','#تاريخ','#حقائق','#اكتشف'],
    'success': ['#نجاح','#تحفيز','#قصص_نجاح','#الإصرار','#احلم_وحقق']
}

IMAGE_QUERIES = {
    'quran':        ['quran book open light','mosque architecture empty','flowers nature peaceful green'],
    'quran_tafseer':['quran pages light','mosque dome sky','nature light rays green'],
    'hadith':       ['roses red beautiful','white flowers nature','garden flowers colorful'],
    'prophet_story':['desert sunset landscape','golden sky clouds','sand dunes sunset'],
    'sahabi_story': ['desert landscape sunset','old stone architecture','golden nature landscape'],
    'islamic_fact': ['flowers bloom colorful','nature geometric','butterfly flowers macro'],
    'duaa':         ['sky sunrise clouds','morning light nature','clouds blue sky peaceful'],
    'friday':       ['green nature peaceful','morning sky light','forest green sunlight'],
    'seasonal':     ['spring flowers bloom','cherry blossom tree','colorful flowers garden'],
    'motivation':   ['mountain peak clouds','sunrise nature landscape','waterfall forest nature'],
    'tips':         ['green leaves nature','garden peaceful flowers','nature close up leaf'],
    'fact':         ['nature macro flower','colorful butterfly','ocean waves peaceful'],
    'question':     ['nature path forest','river reflection trees','colorful autumn leaves'],
    'wisdom':       ['rose single beautiful','white lily flower','nature calm water reflection'],
    'poet_quote':   ['roses bouquet beautiful','flowers field colorful','garden roses pink'],
    'offer':        ['flowers arrangement beautiful','nature colorful bright','garden flowers sunshine'],
    'default':      ['flowers nature beautiful','sky clouds peaceful','garden colorful bloom'],
    'story_suspense': ['dark forest mysterious','night city lights','dramatic sky clouds'],
    'story_romance':  ['roses romantic beautiful','sunset couple silhouette nature','flowers love red'],
    'story_horror':   ['dark abandoned building','foggy night forest','mysterious dark landscape'],
    'story_personal': ['journal notebook coffee','morning light peaceful','nature reflection calm'],
    'story_today':    ['city street life','coffee morning sunshine','everyday life colorful'],
    'story_serial':   ['open book pages','dramatic sky sunset','mystery dark atmosphere'],
    'meme':           ['colorful funny balloon','bright colorful abstract','playful colors nature'],
    'comedy_sketch':  ['colorful abstract art','bright cheerful flowers','sunny day nature'],
    'drama_mystery':  ['mysterious fog forest','dramatic dark clouds','ancient ruins landscape'],
    'truth_or_lie':   ['question mark abstract','colorful puzzle pieces','geometric pattern bright'],
    'weird_facts':    ['galaxy stars space','colorful butterfly macro','exotic nature animals'],
    'country_culture':['world map colorful','exotic landscape travel','colorful architecture'],
    'history_simple': ['ancient ruins architecture','old stone walls','vintage landscape nature'],
    'success_story':  ['mountain summit sunrise','achievement peak clouds','bright sunrise landscape'],
    'life_change':    ['butterfly transformation','sunrise new day','path forward nature'],
    'inspiration_quote':['sunrise motivational','mountain landscape inspiring','nature peaceful morning']
}

DAYS_AR = {
    'mon':'الإثنين','tue':'الثلاثاء','wed':'الأربعاء',
    'thu':'الخميس','fri':'الجمعة','sat':'السبت','sun':'الأحد'
}

def load_json(filepath, default):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return default

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_log(page_name, status, message):
    logs = load_json(LOGS_FILE, [])
    logs.insert(0, {'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'page': page_name, 'status': status, 'message': message})
    save_json(LOGS_FILE, logs[:200])

def update_stats(success=True, post_type=''):
    stats = load_json(STATS_FILE, {'total':0,'today':0,'errors':0,'last_reset':'','by_type':{}})
    today = datetime.now().strftime('%Y-%m-%d')
    if stats.get('last_reset') != today:
        stats['today'] = 0
        stats['last_reset'] = today
    stats['total'] += 1
    if success:
        stats['today'] += 1
        if post_type:
            stats.setdefault('by_type',{})[post_type] = stats.get('by_type',{}).get(post_type,0)+1
    else:
        stats['errors'] = stats.get('errors',0)+1
    save_json(STATS_FILE, stats)

def update_weekly_stats(page_name, post_type, success):
    week = datetime.now().strftime('%Y-W%W')
    stats = load_json(WEEKLY_FILE, {})
    if week not in stats:
        stats[week] = {'total':0,'success':0,'by_page':{},'by_type':{}}
    stats[week]['total'] += 1
    if success: stats[week]['success'] += 1
    stats[week]['by_page'][page_name] = stats[week]['by_page'].get(page_name,0)+1
    stats[week]['by_type'][post_type] = stats[week]['by_type'].get(post_type,0)+1
    save_json(WEEKLY_FILE, stats)

def get_islamic_events():
    """تواريخ المناسبات الاسلامية الميلادية"""
    from datetime import date
    events = [
        # رمضان 2025
        {"name": "شهر رمضان المبارك",       "start": date(2025,3,1),  "end": date(2025,3,29), "ptype": "ramadan"},
        {"name": "العشر الأواخر من رمضان",  "start": date(2025,3,20), "end": date(2025,3,29), "ptype": "ramadan"},
        {"name": "ليلة القدر المباركة",      "start": date(2025,3,26), "end": date(2025,3,27), "ptype": "ramadan"},
        {"name": "عيد الفطر المبارك",        "start": date(2025,3,30), "end": date(2025,4,2),  "ptype": "eid"},
        # ذو الحجة 2025
        {"name": "أيام ذو الحجة العشر",     "start": date(2025,5,29), "end": date(2025,6,6),  "ptype": "hajj_umrah"},
        {"name": "يوم عرفة المبارك",         "start": date(2025,6,5),  "end": date(2025,6,6),  "ptype": "hajj_umrah"},
        {"name": "عيد الأضحى المبارك",       "start": date(2025,6,6),  "end": date(2025,6,10), "ptype": "eid"},
        {"name": "رأس السنة الهجرية",        "start": date(2025,6,26), "end": date(2025,6,27), "ptype": "islamic_wisdom"},
        {"name": "ذكرى عاشوراء المباركة",   "start": date(2025,7,4),  "end": date(2025,7,6),  "ptype": "islamic_wisdom"},
        {"name": "ذكرى المولد النبوي الشريف","start": date(2025,9,4),  "end": date(2025,9,6),  "ptype": "prophet_story"},
        # رمضان 2026
        {"name": "شهر رمضان المبارك",       "start": date(2026,2,18), "end": date(2026,3,19), "ptype": "ramadan"},
        {"name": "العشر الأواخر من رمضان",  "start": date(2026,3,9),  "end": date(2026,3,19), "ptype": "ramadan"},
        {"name": "ليلة القدر المباركة",      "start": date(2026,3,15), "end": date(2026,3,16), "ptype": "ramadan"},
        {"name": "عيد الفطر المبارك",        "start": date(2026,3,20), "end": date(2026,3,23), "ptype": "eid"},
        # ذو الحجة 2026
        {"name": "أيام ذو الحجة العشر",     "start": date(2026,5,18), "end": date(2026,5,26), "ptype": "hajj_umrah"},
        {"name": "يوم عرفة المبارك",         "start": date(2026,5,25), "end": date(2026,5,26), "ptype": "hajj_umrah"},
        {"name": "عيد الأضحى المبارك",       "start": date(2026,5,26), "end": date(2026,5,30), "ptype": "eid"},
        {"name": "رأس السنة الهجرية",        "start": date(2026,6,16), "end": date(2026,6,17), "ptype": "islamic_wisdom"},
        {"name": "ذكرى المولد النبوي الشريف","start": date(2026,8,24), "end": date(2026,8,26), "ptype": "prophet_story"},
    ]
    return events

def get_seasonal_context():
    from datetime import date as ddate
    now = datetime.now(pytz.timezone('Asia/Riyadh'))
    today = now.date()
    weekday = now.weekday()
    contexts = []
    if weekday == 4:
        contexts.append({"name": "يوم الجمعة المبارك", "ptype": "friday_khutba"})
    for ev in get_islamic_events():
        pre = ev["start"] - timedelta(days=2)
        if pre <= today <= ev["end"]:
            contexts.append({"name": ev["name"], "ptype": ev["ptype"]})
    return contexts

def get_upcoming_event():
    from datetime import date as ddate
    today = datetime.now(pytz.timezone('Asia/Riyadh')).date()
    upcoming = []
    for ev in get_islamic_events():
        d = (ev["start"] - today).days
        if 1 <= d <= 10:
            upcoming.append({**ev, "days_until": d})
    return sorted(upcoming, key=lambda x: x["days_until"])

def get_smart_post_type(page_id, requested_type):
    # لو الطلب هو فئة رئيسية — اختر من أنواعها بذكاء بدون تكرار
    if requested_type in POST_CATEGORIES:
        available_types = POST_CATEGORIES[requested_type]
        calendar = load_json(CALENDAR_FILE, {})
        history = calendar.get(page_id, [])
        last_5 = history[-5:]
        # تجنب الأنواع المتكررة في آخر 5 بوستات
        fresh = [t for t in available_types if t not in last_5]
        if not fresh:
            fresh = available_types  # لو كلها متكررة ابدأ من جديد
        return random.choice(fresh)
    # لو نوع محدد — تحقق من التكرار
    calendar = load_json(CALENDAR_FILE, {})
    history = calendar.get(page_id, [])
    last_3 = history[-3:]
    if requested_type in last_3:
        all_types = [t for t in POST_TYPES.keys()]
        available = [t for t in all_types if t not in last_3]
        if available: return random.choice(available)
    return requested_type

def record_post_type(page_id, post_type):
    calendar = load_json(CALENDAR_FILE, {})
    if page_id not in calendar: calendar[page_id] = []
    calendar[page_id].append(post_type)
    calendar[page_id] = calendar[page_id][-20:]
    save_json(CALENDAR_FILE, calendar)

def get_quran_progress():
    return load_json(QURAN_FILE, {'surah':1,'ayah':1})

def get_next_ayah():
    p = get_quran_progress()
    s, a = p['surah'], p['ayah']
    si = next((x for x in QURAN_SURAHS if x[0]==s), QURAN_SURAHS[0])
    next_a = a+1; next_s = s
    if next_a > si[2]:
        next_a = 1; next_s = s+1
        if next_s > 114: next_s = 1
    save_json(QURAN_FILE, {'surah':next_s,'ayah':next_a})
    return s, a, si[1]

def get_hashtags(post_type, topic=''):
    base = ['#إسلاميات', '#محتوى_إسلامي', '#الإسلام_ديننا']
    quran_tags   = ['#القرآن_الكريم','#تفسير_القرآن','#آيات_قرآنية','#نور_القرآن','#كلام_الله','#ختمة_قرآنية']
    seerah_tags  = ['#السيرة_النبوية','#نبينا_محمد','#اللهم_صل_على_محمد','#حب_النبي','#سيرة_عطرة']
    battles_tags = ['#فتوحات_إسلامية','#بطولات_إسلامية','#تاريخ_الإسلام','#مجد_الإسلام','#عز_الإسلام']
    prophets_tags= ['#قصص_الأنبياء','#الأنبياء_والرسل','#قصص_قرآنية','#سير_الأنبياء']
    sahaba_tags  = ['#قصص_الصحابة','#الصحابة_الكرام','#رضي_الله_عنهم','#جيل_الصحابة']
    women_tags   = ['#نساء_الإسلام','#أمهات_المؤمنين','#مجد_المرأة_المسلمة']
    protect_tags = ['#الإسلام_يحفظك','#الإسلام_والكرامة','#الإسلام_والعفاف','#الإسلام_والعدل']
    civili_tags  = ['#الحضارة_الإسلامية','#علماء_الإسلام','#مجد_الإسلام','#تراث_إسلامي']
    akhlaq_tags  = ['#أخلاق_إسلامية','#تزكية_النفس','#تهذيب_الأخلاق','#الإسلام_والأخلاق']
    adhkar_tags  = ['#أذكار','#ذكر_الله','#اللهم','#حصن_المسلم','#أذكار_الصباح','#أذكار_المساء']
    duaa_tags    = ['#دعاء','#اللهم','#دعاء_مستجاب','#ادعوني_أستجب_لكم']
    fiqh_tags    = ['#فقه_إسلامي','#علم_نافع','#أحكام_شرعية','#تعلم_دينك']
    stories_tags = ['#قصص_إسلامية','#قصص_مؤثرة','#رحمة_الله','#توبة','#هداية']
    season_tags  = ['#مناسبات_إسلامية','#رمضان_كريم','#عيد_مبارك','#الحج_المبرور']

    if post_type in ['quran_ayah','quran_tafseer','quran_recitation','quran_khatma','quran_ijaz']:
        return ' '.join(random.sample(quran_tags,4) + random.sample(base,2))
    elif 'seerah' in post_type:
        return ' '.join(random.sample(seerah_tags,4) + random.sample(base,2))
    elif 'battles' in post_type:
        return ' '.join(random.sample(battles_tags,4) + random.sample(base,2))
    elif 'prophet' in post_type:
        return ' '.join(random.sample(prophets_tags,4) + random.sample(base,2))
    elif 'sahabi' in post_type:
        return ' '.join(random.sample(sahaba_tags,4) + random.sample(base,2))
    elif 'women' in post_type:
        return ' '.join(random.sample(women_tags,3) + random.sample(base,2))
    elif 'islam_' in post_type:
        return ' '.join(random.sample(protect_tags,3) + random.sample(base,2))
    elif 'civilization' in post_type:
        return ' '.join(random.sample(civili_tags,3) + random.sample(base,2))
    elif 'akhlaq' in post_type:
        return ' '.join(random.sample(akhlaq_tags,3) + random.sample(base,2))
    elif 'adhkar' in post_type:
        return ' '.join(random.sample(adhkar_tags,4) + random.sample(base,1))
    elif 'duaa' in post_type:
        return ' '.join(random.sample(duaa_tags,4) + random.sample(base,1))
    elif post_type in ['friday_khutba','fiqh_lesson','fatwa','ibadah_ruling','hadith_sahih','islamic_fact']:
        return ' '.join(random.sample(fiqh_tags,4) + random.sample(base,2))
    elif 'story' in post_type:
        return ' '.join(random.sample(stories_tags,4) + random.sample(base,2))
    elif post_type in ['ramadan','eid','hajj_umrah']:
        return ' '.join(random.sample(season_tags,3) + random.sample(base,2))
    elif post_type in ['quran_numeric_ijaz','surah_story','quran_word_deep']:
        return ' '.join(random.sample(quran_tags,3) + ['#إعجاز_قرآني','#القرآن_يعجز_البشر'] + random.sample(base,1))
    elif post_type in ['islam_before_science','non_muslims_about_islam','shocking_islam_facts']:
        return ' '.join(['#الإسلام_دين_العلم','#إعجاز_علمي','#الإسلام_يسبق_العلم','#فخور_بإسلامي'] + random.sample(base,2))
    elif post_type in ['muslims_worldwide','revert_story','islam_in_numbers']:
        return ' '.join(['#الإسلام_ينتشر','#أسلمت','#الإسلام_في_العالم','#الهداية_نعمة'] + random.sample(base,1))
    elif post_type in ['islam_depression','islam_success','islam_health']:
        return ' '.join(['#الإسلام_حل','#الإسلام_والصحة','#الإسلام_والحياة','#طريق_السعادة'] + random.sample(base,1))
    elif post_type in ['parents_rights','islamic_parenting','marriage_islam']:
        return ' '.join(['#الأسرة_المسلمة','#بر_الوالدين','#التربية_الإسلامية','#الزواج_الإسلامي'] + random.sample(base,1))
    elif post_type in ['journey_mecca','journey_madina','journey_mosque']:
        return ' '.join(['#مكة_المكرمة','#المدينة_المنورة','#الحرمين','#مساجد_إسلامية','#رحلة_إيمانية'] + random.sample(base,1))
    elif post_type in ['letter_hardship','letter_away_from_allah','letter_youth']:
        return ' '.join(['#رسالة_إيمانية','#الله_معك','#لا_تيأس','#عودة_إلى_الله','#شباب_مسلم'] + random.sample(base,1))
    elif post_type in ['muslim_success','daily_word','daily_challenge','dont_give_up']:
        return ' '.join(['#تحفيز','#همة','#المسلم_متميز','#لا_تستسلم','#نجاح_إسلامي'] + random.sample(base,1))
    elif post_type in ['islamic_poetry','shafii_poetry','prophet_love_poetry','zuhd_poetry']:
        return ' '.join(['#شعر_إسلامي','#أدب_عربي','#حب_النبي','#شعر_الزهد','#الشافعي'] + random.sample(base,1))
    elif post_type in ['heart_sentence','scholar_quote','wise_men_words']:
        return ' '.join(['#كلمات_معبرة','#اقتباسات_إسلامية','#حكمة','#كلام_العارفين'] + random.sample(base,2))
    elif post_type in ['arabic_proverb','ancestors_wisdom','daily_wisdom']:
        return ' '.join(['#حكمة_اليوم','#أمثال_عربية','#حكم_وأمثال','#تراث_عربي'] + random.sample(base,2))
    else:
        return ' '.join(random.sample(base,3) + ['#إسلام','#دين'])

def has_foreign_words(text):
    import re
    foreign = re.findall(r'[a-zA-Z\u0400-\u04FF\u4e00-\u9fff]+', text)
    real_foreign = [w for w in foreign if len(w) > 1]
    if real_foreign:
        logger.warning(f"Foreign words: {real_foreign[:5]}")
        return True
    return False

def clean_foreign_words(text):
    import re
    cleaned = re.sub(r'[a-zA-Z\u0400-\u04FF\u4e00-\u9fff]+', '', text)
    cleaned = re.sub(r'  +', ' ', cleaned)
    return cleaned.strip()

def fetch_unsplash_image(post_type):
    try:
        queries = IMAGE_QUERIES.get(post_type, IMAGE_QUERIES['default'])
        for _ in range(3):
            query = random.choice(queries)
            r = requests.get('https://api.unsplash.com/photos/random', params={
                'query': query, 'orientation': 'squarish', 'content_filter': 'high'
            }, headers={'Authorization': f'Client-ID {UNSPLASH_KEY}'}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                desc = (data.get('description') or data.get('alt_description') or '').lower()
                tags = [t.get('title','').lower() for t in data.get('tags',[])]
                has_people = any(w in desc or any(w in t for t in tags)
                    for w in ['person','people','man','woman','girl','boy','human','face','portrait'])
                if has_people: continue
                img_r = requests.get(data['urls']['regular'], timeout=20)
                if img_r.status_code == 200:
                    return Image.open(BytesIO(img_r.content)).convert('RGB')
    except Exception as e:
        logger.error(f"Unsplash error: {e}")
    return None

def create_post_image(text, post_type):
    if not PIL_AVAILABLE: return None
    try:
        SIZE = (1080, 1080)
        img = fetch_unsplash_image(post_type)
        if img:
            img = img.resize(SIZE, Image.LANCZOS)
        else:
            img = Image.new('RGB', SIZE)
            nature_colors = [
                [(20,83,45),(5,150,105)],
                [(12,74,110),(3,105,161)],
                [(124,45,18),(180,83,9)],
                [(6,78,59),(4,120,87)],
            ]
            c = random.choice(nature_colors)
            draw_bg = ImageDraw.Draw(img)
            for y in range(SIZE[1]):
                t = y/SIZE[1]
                draw_bg.line([(0,y),(SIZE[0],y)], fill=(
                    int(c[0][0]*(1-t)+c[1][0]*t),
                    int(c[0][1]*(1-t)+c[1][1]*t),
                    int(c[0][2]*(1-t)+c[1][2]*t)
                ))
        output = BytesIO()
        img.save(output, format='JPEG', quality=95)
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Image error: {e}")
        return None

def post_image_to_facebook(page_id, access_token, content, post_type):
    last_error = ''
    for attempt in range(1, 4):  # 3 محاولات
        try:
            img_data = create_post_image(content[:200], post_type)
            if img_data:
                url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
                r = requests.post(url, data={'caption': content, 'access_token': access_token},
                    files={'source': ('image.jpg', img_data, 'image/jpeg')}, timeout=60)
                result = r.json()
                if 'id' in result or 'post_id' in result:
                    return True, result.get('post_id', result.get('id',''))
                if 'error' in result:
                    last_error = result['error'].get('message','خطأ')
                    return False, last_error
            # لو فشل إنشاء الصورة جرب بدون صورة
            return post_to_facebook(page_id, access_token, content)
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Image post attempt {attempt} failed: {last_error[:80]}")
            if attempt < 3:
                import time; time.sleep(3 * attempt)
    return post_to_facebook(page_id, access_token, content)

def post_to_facebook(page_id, access_token, content):
    url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
    last_error = ''
    for attempt in range(1, 4):  # 3 محاولات
        try:
            logger.info(f"FB post attempt {attempt} — page:{page_id}")
            r = requests.post(url, data={'message': content, 'access_token': access_token}, timeout=45)
            result = r.json()
            if 'id' in result:
                logger.info(f"FB post OK: {result['id']}")
                return True, result['id']
            last_error = result.get('error',{}).get('message','خطأ غير معروف')
            # لو الخطأ من فيسبوك مش شبكة — لا تعيد المحاولة
            if 'error' in result:
                logger.error(f"FB API error: {last_error}")
                return False, last_error
        except Exception as e:
            last_error = str(e)
            logger.warning(f"FB attempt {attempt} failed: {last_error[:80]}")
            if attempt < 3:
                import time; time.sleep(3 * attempt)  # انتظر 3 ثم 6 ثواني
    return False, last_error

def enforce_arabic(text):
    """تحقق من ان النص عربي بنسبة 80% على الاقل"""
    import re
    if not text: return False
    arabic_chars = len(re.findall(r'[؀-ۿ]', text))
    total_letters = len(re.findall(r'[a-zA-Z؀-ۿ]', text))
    if total_letters == 0: return True
    return (arabic_chars / total_letters) >= 0.80

def get_prompt_for_type(post_type, topic, personality='mixed', seasonal_ctx=None):
    p = PAGE_PERSONALITIES.get(personality, PAGE_PERSONALITIES['mixed'])
    t = topic

    # تفسير القرآن بالترتيب - معالجة خاصة
    if post_type == 'quran_tafseer':
        s, a, sname = get_next_ayah()
        return (f'اكتب منشور فيسبوك إسلامي عن الآية رقم {a} من سورة {sname}\n'
                f'📖 عنوان: تفسير سورة {sname} - الآية {a}\n'
                f'اكتب: نص الآية كاملاً - تفسيرها بأسلوب بسيط - الفوائد - دعاء\n'
                f'الأسلوب: {p} - باللغة العربية الفصحى فقط')

    # مناسبة دينية حالية
    if post_type in ['ramadan','eid','hajj_umrah'] and seasonal_ctx:
        ev = random.choice(seasonal_ctx)
        ev_name = ev['name'] if isinstance(ev, dict) else ev
        return (f'اكتب منشور فيسبوك إسلامي خاص بـ: {ev_name}\n'
                f'الموضوع: {t}\n'
                f'ابدأ بتهنئة مؤثرة + فضل هذه المناسبة + دعاء مناسب + تشجيع على العمل الصالح\n'
                f'الأسلوب: {p}')

    prompts = {
        # 📖 القرآن الكريم
        'quran_ayah':       f'📖 اكتب منشور "آية اليوم"\nاختر آية قرآنية مؤثرة - نصها + اسم السورة + تفسير مبسط + فائدة عملية + دعاء\nالأسلوب: {p}',
        'quran_recitation': f'🎙️ اكتب منشور تلاوة وتفسير آية عن موضوع: {t}\nالآية + معناها + كيف نطبقها + دعاء\nالأسلوب: {p}',
        'quran_khatma':     f'📿 اكتب منشور يشجع على ختم القرآن\nفضل القراءة + خطة مقترحة + تحدٍّ للمتابعين + اختم بـ: من معنا في الختمة؟ اكتب 📖\nالأسلوب: {p}',
        'quran_ijaz':       f'🔬 اكتب منشور إعجاز علمي قرآني مذهل عن: {t}\nالآية الكريمة + الاكتشاف العلمي الحديث المرتبط بها + كيف سبق القرآن العلم\nاختم بـ: سبحان الله 🤍\nالأسلوب: {p}',
        # 🕌 السيرة النبوية
        'seerah_birth':     f'🌹 اكتب منشور عن مولد النبي محمد صلى الله عليه وسلم أو طفولته\nأحداث مضيئة + معجزات مصاحبة + ما يدل على نبوته منذ الصغر\nاختم بالصلاة على النبي\nالأسلوب: {p}',
        'seerah_manners':   f'✨ اكتب منشور عن خلق أو صفة من صفات النبي محمد صلى الله عليه وسلم\nاختر صفة محددة + موقف حقيقي من حياته يجسدها + كيف نقتدي به\nاختم بـ: اللهم صلِّ على محمد\nالأسلوب: {p}',
        'seerah_miracles':  f'✨ اكتب منشور عن معجزة من معجزات النبي محمد صلى الله عليه وسلم\nاختر معجزة محددة + اذكرها بأسلوب قصصي شيق + دلالتها + الحديث الشريف\nالأسلوب: {p}',
        'seerah_battles':   f'⚔️ اكتب منشور عن غزوة من غزوات النبي صلى الله عليه وسلم\nاختر غزوة + أحداثها البطولية + الدرس الاستراتيجي والإيماني\nاختم بسؤال تفاعلي\nالأسلوب: {p}',
        'seerah_companions':f'🌟 اكتب منشور عن موقف إنساني بين النبي وأصحابه صلى الله عليه وسلم\nموقف محدد + ما يكشفه عن شخصيته الكريمة + الدرس\nالأسلوب: {p}',
        'seerah_love':      f'💖 اكتب منشور يثير حب النبي محمد صلى الله عليه وسلم في القلوب\nصفة أو موقف يجعل القلب يشتاق إليه + الصلاة عليه + سؤال: كيف تحب نبيك؟\nالأسلوب: {p}',
        # ⚔️ الفتوحات والمعارك
        'battles_badr':     f'⚔️ اكتب منشور عن غزوة بدر الكبرى\nسياقها + أحداثها البطولية + الأثر الإيماني + درس يلهم المسلم اليوم\nالأسلوب: {p}',
        'battles_uhud':     f'⚔️ اكتب منشور عن غزوة أحد والثبات\nما حدث + التضحيات + درس الثبات بعد المحنة + كيف نطبقه اليوم\nالأسلوب: {p}',
        'battles_khandaq':  f'🏰 اكتب منشور عن غزوة الخندق والتخطيط الإسلامي\nعبقرية الخطة + الصمود + الإيمان بنصر الله + الدرس\nالأسلوب: {p}',
        'battles_mecca':    f'🕌 اكتب منشور عن فتح مكة المكرمة\nكيف فتح النبي مكة بلا إراقة دماء + العفو العظيم + الدرس الخالد\nالأسلوب: {p}',
        'battles_history':  f'🌍 اكتب منشور عن فتح إسلامي تاريخي عظيم\nاختر فتحاً مشهوراً + أحداثه + أثره على نشر الإسلام + الدرس\nالأسلوب: {p}',
        'battles_heroism':  f'🦁 اكتب منشور عن بطولة إسلامية خالدة\nاختر بطلاً مسلماً + موقفه الملحمي + ما دفعه لهذه البطولة + الدرس\nالأسلوب: {p}',
        # 👳 قصص الأنبياء
        'prophet_adam':     f'🌿 اكتب قصة مؤثرة من قصة سيدنا آدم عليه السلام\nاختر موقفاً محدداً + الآيات القرآنية + الدرس + دعاء\nالأسلوب: {p}',
        'prophet_ibrahim':  f'🔥 اكتب قصة مؤثرة من قصة سيدنا إبراهيم عليه السلام\nاختر موقفاً كالنار أو الذبح + الآيات + العبرة العظيمة + دعاء\nالأسلوب: {p}',
        'prophet_musa':     f'🌊 اكتب قصة مؤثرة من قصة سيدنا موسى عليه السلام\nاختر موقفاً كفلق البحر + الآيات + الدرس + دعاء\nالأسلوب: {p}',
        'prophet_yusuf':    f'⭐ اكتب قصة مؤثرة من قصة سيدنا يوسف عليه السلام\nاختر موقفاً كالجب أو العزيز + الآيات + درس الصبر والعفو + دعاء\nالأسلوب: {p}',
        'prophet_isa':      f'✨ اكتب قصة مؤثرة من قصة سيدنا عيسى عليه السلام\nاختر موقفاً + المعجزات + ما يؤمن به المسلمون + دعاء\nالأسلوب: {p}',
        'prophet_miracles': f'🌟 اكتب منشور عن معجزة عظيمة لأحد الأنبياء\nاختر نبياً ومعجزة محددة + اشرحها بأسلوب شيق + الحكمة منها\nاختم بـ: سبحان الله 🤍\nالأسلوب: {p}',
        'prophet_lessons':  f'📖 اكتب درس وعبرة من قصص الأنبياء عن موضوع: {t}\nالقصة باختصار + العبرة + كيف نطبقها اليوم + سؤال\nالأسلوب: {p}',
        # 🌟 الصحابة
        'sahabi_abubakr':   f'🌟 اكتب منشور عن سيدنا أبو بكر الصديق رضي الله عنه\nاختر موقفاً أو صفة محددة + أسلوب قصصي مؤثر + الدرس\nالأسلوب: {p}',
        'sahabi_umar':      f'⚡ اكتب منشور عن سيدنا عمر بن الخطاب رضي الله عنه\nاختر موقفاً من عدله أو شجاعته + أسلوب ملحمي + الدرس\nالأسلوب: {p}',
        'sahabi_uthman':    f'📖 اكتب منشور عن سيدنا عثمان بن عفان رضي الله عنه\nاختر موقفاً من كرمه أو تقواه + أسلوب مؤثر + الدرس\nالأسلوب: {p}',
        'sahabi_ali':       f'🦁 اكتب منشور عن سيدنا علي بن أبي طالب رضي الله عنه\nاختر موقفاً من شجاعته أو حكمته + أسلوب ملحمي + الدرس\nالأسلوب: {p}',
        'sahabi_heroism':   f'⚔️ اكتب قصة بطولة صحابي كريم\nاختر صحابياً وموقفاً بطولياً محدداً + أسلوب ملحمي مشوق + الدرس\nالأسلوب: {p}',
        'sahabi_islam':     f'🌙 اكتب قصة إسلام أحد الصحابة الكرام\nاختر صحابياً مشهوراً + قصة إسلامه المؤثرة + التحول + دعاء\nالأسلوب: {p}',
        'sahabi_sahabiyat': f'🌹 اكتب منشور عن صحابية كريمة\nاختر صحابية + موقفها البطولي أو الإيماني + دورها في الإسلام\nالأسلوب: {p}',
        # 🌹 نساء الإسلام
        'women_khadijah':   f'💎 اكتب منشور عن السيدة خديجة أم المؤمنين رضي الله عنها\nوقوفها مع النبي + كرمها + قصة مؤثرة من حياتها + الدرس\nالأسلوب: {p}',
        'women_aisha':      f'📚 اكتب منشور عن السيدة عائشة أم المؤمنين رضي الله عنها\nعلمها الواسع + موقف من حياتها + إسهامها في الفقه الإسلامي\nالأسلوب: {p}',
        'women_fatima':     f'🌹 اكتب منشور عن السيدة فاطمة الزهراء رضي الله عنها\nفضلها + موقف مؤثر من حياتها + محبة النبي لها\nالأسلوب: {p}',
        'women_maryam':     f'✨ اكتب منشور عن السيدة مريم العذراء عليها السلام\nما ذكره القرآن عنها + معجزة ولادة عيسى + درس التقوى والصبر\nالأسلوب: {p}',
        'women_heroes':     f'🦅 اكتب منشور عن بطلة أو عالمة مسلمة عظيمة\nاختر شخصية نسائية إسلامية + دورها + إسهامها + الدرس الملهم\nالأسلوب: {p}',
        # 🛡️ الإسلام وحفظ الإنسان
        'islam_dignity':    f'👑 اكتب منشور عن كيف كرّم الإسلام الإنسان وصان كرامته\nآيات وأحاديث + مقارنة بالحضارات الأخرى + تطبيق عملي اليوم\nالأسلوب: {p}',
        'islam_family':     f'🏠 اكتب منشور عن كيف حفظ الإسلام الأسرة والنسل\nالزواج الشرعي + حقوق الأبناء + حماية الأسرة + نتائج الانحلال\nالأسلوب: {p}',
        'islam_mind':       f'🧠 اكتب منشور عن كيف حفظ الإسلام العقل\nتحريم الخمر والمخدرات + الأمر بالتفكر والتعلم + أثر ذلك على الحضارة\nالأسلوب: {p}',
        'islam_honor':      f'🌺 اكتب منشور عن الإسلام والعفاف وصون العرض\nالحجاب والعفة + حفظ الأعراض + جمال الطهارة + كيف يحمي المجتمع\nالأسلوب: {p}',
        'islam_wealth':     f'💰 اكتب منشور عن كيف حفظ الإسلام المال والاقتصاد\nتحريم الربا + الزكاة + التجارة الشريفة + عدالة التوزيع\nالأسلوب: {p}',
        'islam_rights':     f'⚖️ اكتب منشور عن حقوق الإنسان في الإسلام\nحقوق أقرها الإسلام قبل 14 قرناً + مقارنة بالمواثيق الحديثة\nالأسلوب: {p}',
        'islam_justice':    f'⚖️ اكتب منشور عن العدل في الإسلام\nآيات وأحاديث + قصة عدل من التاريخ الإسلامي + كيف نطبقه\nالأسلوب: {p}',
        'islam_mercy':      f'🤍 اكتب منشور عن الرحمة في الإسلام\nرحمة النبي + آيات الرحمة + مواقف مضيئة + كيف نكون رحماء\nالأسلوب: {p}',
        # 🧠 الحضارة الإسلامية
        'civilization_science': f'🔬 اكتب منشور عن عالم مسلم وإنجازاته الحضارية\nاختر عالماً كابن سينا أو الخوارزمي + اكتشافه + أثره على العالم\nالأسلوب: {p}',
        'civilization_golden':  f'🏛️ اكتب منشور عن الحضارة الإسلامية الذهبية\nعصر العلم والازدهار + ماذا أعطى الإسلام للعالم + درس للأجيال\nالأسلوب: {p}',
        'civilization_medicine':f'⚕️ اكتب منشور عن الطب الإسلامي عبر التاريخ\nعلماء الطب المسلمون + اكتشافاتهم + كيف أسسوا الطب الحديث\nالأسلوب: {p}',
        'civilization_andalus': f'🌹 اكتب منشور عن الأندلس ومجد الحضارة الإسلامية\nعصر الازدهار + ما أعطته الأندلس لأوروبا + الدرس من سقوطها\nالأسلوب: {p}',
        # 💎 الأخلاق
        'akhlaq_patience':  f'🌿 اكتب منشور عن الصبر في الإسلام\nآيات وأحاديث + قصة صبر مؤثرة + كيف نكتسب الصبر\nالأسلوب: {p}',
        'akhlaq_shukr':     f'☀️ اكتب منشور عن الشكر والقناعة في الإسلام\nآيات الشكر + فوائد القناعة + كيف نشكر الله في يومنا\nالأسلوب: {p}',
        'akhlaq_tawakkul':  f'🌟 اكتب منشور عن التوكل على الله\nمعنى التوكل الحقيقي + آيات وأحاديث + قصة توكل + كيف نطبقه\nالأسلوب: {p}',
        'akhlaq_ikhlas':    f'💎 اكتب منشور عن الإخلاص والصدق في الإسلام\nمعنى الإخلاص + أثره على قبول العمل + قصة مؤثرة + تطبيق عملي\nالأسلوب: {p}',
        'akhlaq_rehma':     f'🤍 اكتب منشور عن الرحمة والتراحم في الإسلام\nأحاديث الرحمة + مواقف النبي الرحيمة + كيف نكون رحماء في حياتنا\nالأسلوب: {p}',
        # 🤲 الأذكار والأدعية
        'adhkar_morning':   f'🌅 اكتب منشور أذكار الصباح المباركة\nالأذكار المأثورة + فضل المداومة + اختم بـ: اللهم بارك لنا في صباحنا ☀️\nالأسلوب: {p}',
        'adhkar_evening':   f'🌙 اكتب منشور أذكار المساء\nالأذكار المأثورة + فضلها + اختم بـ: اللهم بارك في مسائنا 🌙\nالأسلوب: {p}',
        'adhkar_sleep':     f'😴 اكتب منشور أذكار النوم\nالأذكار المأثورة + آية الكرسي + سنن النوم\nالأسلوب: {p}',
        'adhkar_home':      f'🏠 اكتب منشور دعاء دخول وخروج البيت\nالدعاء + الفضل + السنة النبوية\nالأسلوب: {p}',
        'duaa_hardship':    f'😢 اكتب منشور دعاء الكرب والضيقة\nالأدعية المأثورة + قصة فرج + وعد الله + اختم بـ: اللهم فرّج كربنا 🤲\nالأسلوب: {p}',
        'duaa_rizq':        f'💰 اكتب منشور دعاء الرزق والفرج\nالأدعية + آية أو حديث + أسباب جلب الرزق + اختم بـ: اللهم ارزقنا 🤍\nالأسلوب: {p}',
        'duaa_healing':     f'🌿 اكتب منشور دعاء الشفاء\nدعاء الشفاء المأثور + الله هو الشافي + اختم بـ: اللهم اشفِ مرضانا 🤲\nالأسلوب: {p}',
        'duaa_parents':     f'❤️ اكتب منشور دعاء للوالدين\nالدعاء المأثور + فضل الدعاء للوالدين + قصة + اختم بـ: اللهم اغفر لوالدينا 🤍\nالأسلوب: {p}',
        'duaa_short':       f'✨ اكتب منشور دعاء قصير مؤثر سهل الحفظ\nالدعاء بشكل بارز + معناه + متى يُقال + اختم بـ: رددوه معي 🤍\nالأسلوب: {p}',
        # 📚 الفقه والعلم
        'friday_khutba':    f'🕌 اكتب خطبة جمعة مؤثرة عن: {t}\nحمد + موضوع بأدلة قرآنية + توجيهات + دعاء\nالأسلوب: {p}',
        'fiqh_lesson':      f'📚 اكتب درس فقهي مبسط عن: {t}\nالمسألة + الحكم الشرعي + دليله + تطبيق عملي\nالأسلوب: {p}',
        'fatwa':            f'⚖️ اكتب إجابة على سؤال شرعي شائع عن: {t}\nالسؤال + الحكم + دليله + توضيح + هل لديك سؤال؟\nالأسلوب: {p}',
        'ibadah_ruling':    f'🕋 اكتب أحكام عبادة مبسطة عن: {t}\nشروط وأركان + الأخطاء الشائعة + فضل العبادة\nالأسلوب: {p}',
        'hadith_sahih':     f'🌹 اكتب منشور حول حديث نبوي صحيح عن موضوع: {t}\nالحديث كاملاً + راويه + شرحه + التطبيق اليومي\nالأسلوب: {p}',
        'islamic_fact':     f'🔍 اكتب منشور معلومة إسلامية مثيرة عن: {t}\nمعلومة غير متوقعة + دليلها + سؤال: هل كنت تعلم؟\nالأسلوب: {p}',
        # 😢 قصص مؤثرة
        'story_tawba':      f'😢 اكتب قصة توبة مؤثرة وعودة إلى الله\nشخص عاش بعيداً + اللحظة الفارقة + حياته بعد التوبة + اختم بـ: باب التوبة مفتوح 🤍\nالأسلوب: {p}',
        'story_good_end':   f'🌹 اكتب قصة مؤثرة عن حسن الخاتمة\nمواقف مؤثرة + علامات حسن الخاتمة + دعاء: اللهم توفنا وأنت راضٍ عنا 🤲\nالأسلوب: {p}',
        'story_karama':     f'✨ اكتب قصة كرامة من كرامات الصالحين\nقصة حقيقية + السياق + الدرس + اختم بـ: اللهم اجعلنا من الصالحين 🤍\nالأسلوب: {p}',
        'story_duaa_answered': f'🤲 اكتب قصة مؤثرة عن استجابة الدعاء\nضيقة شديدة + الدعاء + الاستجابة المذهلة + اختم بـ: لا تيأس من رحمة الله 🤍\nالأسلوب: {p}',
        'story_hidaya':     f'🌙 اكتب قصة هداية مؤثرة من الظلام إلى النور\nحياة قبل الهداية + لحظة الهداية + حياة بعدها + اختم بـ: الهداية نعمة 🤍\nالأسلوب: {p}',
        # المناسبات
        'ramadan':          f'🌙 اكتب منشور رمضاني مميز عن: {t}\nفضل رمضان + عمل مقترح + دعاء\nالأسلوب: {p}',
        'eid':              f'🎊 اكتب منشور عيد مبارك\nتهنئة جميلة + فضل العيد + دعاء\nالأسلوب: {p}',
        'hajj_umrah':       f'🕋 اكتب منشور عن الحج أو العمرة عن: {t}\nالفريضة + فضلها + أدعية + اختم بـ: اللهم ارزقنا زيارة بيتك 🤲\nالأسلوب: {p}',
        'islamic_wisdom':   f'💎 اكتب موعظة إسلامية مؤثرة عن: {t}\nموضوع وعظي + آية أو حديث + قصة معبرة + دعاء\nالأسلوب: {p}',
        # 🔢 سلاسل يومية
        'allah_name':       f'✨ اكتب منشور "اسم الله اليوم"\nاختر اسماً من أسماء الله الحسنى الـ99\nمعناه اللغوي + معناه العميق + كيف يؤثر في حياتنا + دعاء باسم الله هذا\nاختم بـ: رددوا معي يا [اسم الله] 🤍\nالأسلوب: {p}',
        'aya_taammul':      f'🌿 اكتب منشور "آية وتأمل"\nاختر آية قرآنية قصيرة مؤثرة\nاكتبها بشكل بارز ثم قدّم تأملاً شخصياً عميقاً فيها\nاختم بسؤال: ماذا تقول لك هذه الآية؟ 👇\nالأسلوب: {p}',
        'hadith_daily':     f'🌹 اكتب منشور "حديث اليوم"\nاختر حديثاً نبوياً صحيحاً قصيراً ومؤثراً\nاكتبه بشكل بارز + اسم الراوي + شرح بسيط + تطبيق عملي واحد في حياتنا اليوم\nاختم بـ: اللهم صلِّ على محمد 🌹\nالأسلوب: {p}',
        # 💬 تفاعلي
        'dini_question':    f'🤔 اكتب منشور "سؤال ديني تفاعلي"\nاطرح سؤالاً شرعياً أو دينياً بسيطاً يعرفه الناس لكنهم قد يختلفون فيه\nاكتب السؤال بشكل مثير للفضول\nاكتب: الجواب في التعليقات 👇 شاركنا ما تعرفه\nثم اكتب الجواب الصحيح كاملاً مع دليله\nالأسلوب: {p}',
        'complete_aya':     f'📖 اكتب منشور "أكمل الآية"\nاختر آية قرآنية مشهورة واكتب نصفها الأول فقط\nاكتب: أكمل الآية الكريمة 👇\nثم ضع الإجابة وكامل الآية + اسم السورة + معنى الآية\nاختم بـ: من حفظ؟ 🌟\nالأسلوب: {p}',
        'who_is_sahabi':    f'🌟 اكتب منشور "من هذا الصحابي؟"\nاختر صحابياً كريماً واكتب وصفه وبعض صفاته وأبرز مواقفه بدون ذكر اسمه\nاكتب: من هذا الصحابي الكريم؟ خمّن في التعليقات 👇\nثم اكشف اسمه مع قصة مؤثرة من حياته\nالأسلوب: {p}',
        'islamic_did_you_know': f'🔍 اكتب منشور "هل تعلم؟" إسلامي\nاختر معلومة إسلامية مثيرة غير معروفة لدى كثيرين\nابدأ بـ: هل تعلم أن...\nاشرح المعلومة بأسلوب مثير + دليلها + ما تستفيده\nاختم بـ: شاركها لتنشر العلم 🌿\nالأسلوب: {p}',
        # 🌙 وقت محدد
        'fajr_duaa':        f'🌅 اكتب منشور "دعاء الفجر"\nاكتب كأنك تناجي الله في وقت الفجر المبارك\nدعاء مأثور لوقت الفجر + فضل صلاة الفجر + تشجيع على الاستيقاظ\nاختم بـ: اللهم بارك لنا في فجرنا ☀️\nالأسلوب: {p}',
        'night_reminder':   f'🌙 اكتب منشور "نصيحة ما قبل النوم"\nاكتب بأسلوب هادئ وروحاني كأنك تودّع يومك\nنصيحة روحانية قصيرة + ذكر من أذكار النوم + تذكير بمحاسبة النفس\nاختم بـ: بارك الله في نومكم وأعاننا على طاعته 🌙\nالأسلوب: {p}',
        'salah_reminder':   f'🕌 اكتب منشور "تذكير بالصلاة"\nذكّر بفضل الصلاة وأهميتها في حياة المسلم\nحديث عن فضل الصلاة + ما تفعله الصلاة في القلب + تشجيع على المحافظة عليها\nاختم بـ: حافظ على صلاتك يحفظك الله 🤍\nالأسلوب: {p}',
        # 📚 تعليمي متسلسل
        'islam_pillars':    f'🕋 اكتب منشور تفصيلي عن ركن من أركان الإسلام\nاختر ركناً محدداً + اشرحه بعمق + فضله + كيف نؤديه على أكمل وجه\nاختم بسؤال تفاعلي\nالأسلوب: {p}',
        'jannah_description': f'🌺 اكتب منشور عن وصف من أوصاف الجنة\nاختر وصفاً قرآنياً أو حديثياً للجنة\nاشرحه بأسلوب شوّقي يجعل القلب يشتاق + الآيات والأحاديث\nاختم بـ: اللهم اجعلنا من أهل الجنة 🤍\nالأسلوب: {p}',
        'judgment_signs':   f'🔮 اكتب منشور عن علامة من علامات الساعة الصغرى\nاختر علامة محددة + اذكرها بأسلوب شيق + الدليل + هل نراها اليوم؟\nاختم بسؤال: هل تلاحظ هذه العلامة؟ 👇\nالأسلوب: {p}',
        # 🤲 روحاني عميق
        'creation_reflection': f'🌍 اكتب منشور "تأمل في خلق الله"\nاختر ظاهرة طبيعية أو مخلوقاً عجيباً\nتأمل فيه علمياً ثم روحانياً + الآية التي تتعلق به\nاختم بـ: سبحان الله ما أعظم خلقه 🌿\nالأسلوب: {p}',
        'islam_answers':    f'💡 اكتب منشور "الإسلام يجيب"\nاطرح سؤالاً وجودياً أو فلسفياً يؤرق الناس مثل: لماذا يبتلينا الله؟ أو ما الحكمة من الموت؟\nثم أجب عليه من منظور إسلامي عميق بآيات وأحاديث وحكمة\nالأسلوب: {p}',
        # 📿 سلاسل قرآنية
        'quran_numeric_ijaz': f'🔢 اكتب منشور "إعجاز رقمي في القرآن"\nاختر حقيقة رقمية مذهلة من القرآن مثل: عدد مرات ذكر كلمة معينة أو تناسق الأرقام\nاشرحها بأسلوب مثير + الآيات الدالة عليها\nاختم بـ: سبحان الله ما أعظم كتابه 🤍\nالأسلوب: {p}',
        'surah_story':        f'📖 اكتب منشور "قصة سورة"\nاختر سورة قرآنية واحكِ قصة نزولها وسبب تسميتها وأبرز موضوعاتها\nأسلوب شيق كأنك تحكي قصة + الفائدة من هذه السورة\nالأسلوب: {p}',
        'quran_word_deep':    f'💎 اكتب منشور "تعمق في كلمة قرآنية"\nاختر كلمة واحدة من القرآن الكريم وتعمق في معناها\nالمعنى اللغوي + السياق القرآني + الفوائد المستخرجة\nاختم بـ: ما أعمق كلام الله 🤍\nالأسلوب: {p}',
        # ⚡ محتوى صادم ومثير
        'islam_before_science': f'🔬 اكتب منشور "الإسلام سبق العلم"\nاختر حقيقة علمية اكتشفها العلم الحديث وكان القرآن أو الحديث قد أشار إليها قبل 1400 سنة\nالاكتشاف العلمي + النص الشرعي + التطابق المذهل\nاختم بـ: سبحان الله العليم 🌟\nالأسلوب: {p}',
        'non_muslims_about_islam': f'🌍 اكتب منشور "ماذا قال غير المسلمين عن الإسلام"\nاختر شهادة عالم أو مفكر أو شخصية غربية مشهورة أعجبت بالإسلام\nمن هو + ماذا قال + ما الذي أعجبه\nاختم بسؤال: هل تعلم من قال هذا؟ 👇\nالأسلوب: {p}',
        'shocking_islam_facts': f'🤯 اكتب منشور "حقائق صادمة عن الإسلام"\nاختر 3 حقائق مذهلة عن الإسلام لا يعرفها كثير من المسلمين أنفسهم\nكل حقيقة مع دليلها + لماذا هي مذهلة\nاختم بـ: فخور بديني 🤍\nالأسلوب: {p}',
        # 🌍 الإسلام في العالم
        'muslims_worldwide':  f'🌐 اكتب منشور "مسلمو العالم"\nاختر بلداً غير متوقع فيه مسلمون كثيرون أو مجتمعاً إسلامياً مثيراً\nكيف وصل الإسلام إليه + قصتهم المؤثرة + رسالة الإسلام العالمية\nالأسلوب: {p}',
        'revert_story':       f'🌙 اكتب منشور "أسلم لأن..."\nاكتب قصة إسلام شخص غير مسلم مؤثرة وحقيقية\nحياته قبل الإسلام + اللحظة التي هداه الله فيها + حياته بعد الإسلام\nاختم بـ: الهداية نعمة لا تُقدر 🤍\nالأسلوب: {p}',
        'islam_in_numbers':   f'📊 اكتب منشور "الإسلام في أرقام"\nاختر إحصاءات مذهلة عن انتشار الإسلام في العالم أو نمو عدد المسلمين\nالأرقام + ما تدل عليه + الفخر بالإسلام\nاختم بـ: الحمد لله على نعمة الإسلام 🤍\nالأسلوب: {p}',
        # 💪 الإسلام وتحديات الحياة
        'islam_depression':   f'💙 اكتب منشور "الإسلام والاكتئاب والقلق"\nكيف يعالج الإسلام القلق والحزن والاكتئاب؟\nآيات وأحاديث تشفي القلب + الأسباب الروحية للقلق + الحل الإسلامي العملي\nاختم بـ: الله معك 🤍\nالأسلوب: {p}',
        'islam_success':      f'🏆 اكتب منشور "الإسلام والنجاح"\nاكشف مبادئ إسلامية للنجاح في الحياة من القرآن والسنة\nمبدأ مع دليله + قصة نجاح إسلامية + تطبيق عملي اليوم\nالأسلوب: {p}',
        'islam_health':       f'⚕️ اكتب منشور "الإسلام والصحة"\nاختر سنة نبوية يثبتها الطب الحديث مثل الصيام أو السواك أو الختان\nالسنة النبوية + ما يقوله الطب الحديث + الفائدة\nاختم بـ: ما أحكم شريعة الإسلام 🌿\nالأسلوب: {p}',
        # 🌺 الأسرة والمجتمع
        'parents_rights':     f'❤️ اكتب منشور "حق الوالدين في الإسلام"\nآيات وأحاديث في بر الوالدين + قصة مؤثرة + كيف نبر والدينا اليوم\nاختم بـ: اللهم اغفر لوالدينا وارحمهم 🤲\nالأسلوب: {p}',
        'islamic_parenting':  f'👨‍👩‍👧 اكتب منشور "التربية الإسلامية"\nكيف ربّى النبي الأجيال؟ + مبدأ تربوي إسلامي مع مثال عملي\nكيف نطبقه مع أبنائنا اليوم + دعاء للأبناء\nالأسلوب: {p}',
        # ✈️ رحلات إسلامية
        'journey_mecca':      f'🕋 اكتب منشور "جولة في مكة المكرمة"\nاختر مكاناً محدداً في مكة مثل الكعبة أو زمزم أو الصفا والمروة أو جبل النور\nصِف المكان بأسلوب شوقي يجعل القارئ يشعر أنه هناك + التاريخ + الفضل\nاختم بـ: اللهم ارزقنا زيارة بيتك الحرام 🤍\nالأسلوب: {p}',
        'journey_madina':     f'🌹 اكتب منشور "جولة في المدينة المنورة"\nاختر مكاناً محدداً في المدينة مثل المسجد النبوي أو البقيع أو أحد أو قباء\nصِف المكان بأسلوب شوقي مؤثر + ذكريات النبي فيه + الفضل\nاختم بـ: اللهم ارزقنا زيارة نبيك 🌹\nالأسلوب: {p}',
        'journey_mosque':     f'🕌 اكتب منشور "مسجد تاريخي عظيم"\nاختر مسجداً تاريخياً مشهوراً في العالم الإسلامي مثل الأزهر أو قرطبة أو السلطان أحمد\nتاريخه + من بناه + ما الذي يميزه + الدرس\nاختم بـ: مجد الإسلام في كل مكان 🌟\nالأسلوب: {p}',
        # 💌 رسائل إيمانية
        'letter_hardship':    f'💙 اكتب رسالة إيمانية مؤثرة "لمن يمر بضيقة وألم"\nاكتب بضمير المخاطب كأنك تكلم شخصاً يعاني الآن\nكلمات تحمل + آية مواسية + حديث + وعد الله بالفرج\nاختم بدعاء: اللهم فرّج عن كل مضيَّق 🤍\nالأسلوب: {p}',
        'letter_away_from_allah': f'🌙 اكتب رسالة إيمانية مؤثرة "لمن ابتعد عن الله"\nاكتب بضمير المخاطب بأسلوب الحب والرحمة لا العتاب\nذكّره بفضل الله + باب التوبة المفتوح + قصة عودة مؤثرة\nاختم بـ: الله يحبك ويريدك أن تعود 🤍\nالأسلوب: {p}',
        'letter_youth':       f'💪 اكتب رسالة إيمانية ملهمة "للشباب المسلم"\nاكتب بضمير المخاطب موجهاً للشاب المسلم في زمن الفتن\nقدّر طاقتهم + ذكّرهم بدورهم + أمثلة من شباب الصحابة + تحدٍّ إيماني\nاختم بـ: أنت أمل هذه الأمة 💪\nالأسلوب: {p}',
        # 🔥 تحفيز وإلهام
        'muslim_success':     f'🏆 اكتب منشور "قصة نجاح مسلم"\nاختر شخصية مسلمة حققت إنجازاً عظيماً في العلم أو الفن أو الرياضة أو الأعمال\nقصتها بأسلوب ملهم + ما أعانها على النجاح من إيمانها + الدرس\nاختم بـ: المسلم قادر على التميز 💪\nالأسلوب: {p}',
        'daily_word':         f'✨ اكتب منشور "كلمة تغير يومك"\nاختر جملة قصيرة مؤثرة من القرآن أو السنة أو الحكماء تشعل الهمة\nاكتبها بشكل بارز + شرح عميق لها + كيف تطبقها اليوم\nاختم بـ: ابدأ يومك بهذه الكلمة 🌟\nالأسلوب: {p}',
        'daily_challenge':    f'💪 اكتب منشور "تحدي اليوم"\nاقترح تحدياً عملياً صغيراً ذا أثر إسلامي مثل: صلِّ الفجر في وقته أو أعطِ صدقة أو اقرأ صفحة قرآن\nاشرح فضل هذا العمل + كيف يغير حياتك\nاختم بـ: من معنا في تحدي اليوم؟ 👇\nالأسلوب: {p}',
        'dont_give_up':       f'🌅 اكتب منشور "لا تستسلم"\nاكتب قصة إصرار وصمود ملهمة من التاريخ الإسلامي أو الحياة\nالتحدي + الصمود + النتيجة المذهلة + الدرس الإيماني\nاختم بـ: بعد كل عسر يسر 🤍\nالأسلوب: {p}',
        # 📜 شعر وأدب إسلامي
        'islamic_poetry':     f'📜 اكتب منشور "بيت شعر إسلامي"\nاختر بيتاً أو أبياتاً من الشعر العربي الإسلامي لشاعر مشهور\nاكتبها بشكل بارز + اسم الشاعر + شرح جميل للمعنى\nاختم بسؤال: ما أجمل بيت شعر يعجبك؟ 👇\nالأسلوب: {p}',
        'shafii_poetry':      f'🌹 اكتب منشور "من شعر الإمام الشافعي"\nاختر أبياتاً مشهورة للإمام الشافعي رحمه الله\nاكتبها بشكل بارز + سياقها ومناسبتها + شرح عميق للمعنى + الدرس\nالأسلوب: {p}',
        'prophet_love_poetry':f'💖 اكتب منشور "شعر في حب النبي"\nاكتب أبياتاً شعرية مؤثرة تعبر عن الشوق والحب للنبي محمد صلى الله عليه وسلم\nأبيات جميلة + اسم قائلها + شرح المشاعر فيها\nاختم بالصلاة على النبي 🌹\nالأسلوب: {p}',
        'zuhd_poetry':        f'🌿 اكتب منشور "شعر الزهد والتقوى"\nاختر أبياتاً في الزهد والتأمل في الدنيا والآخرة\nاكتبها بشكل بارز + اسم الشاعر + شرح التأمل فيها\nاختم بـ: الدنيا لحظة والآخرة الباقية 🤍\nالأسلوب: {p}',
        # 💬 كلمات معبرة
        'heart_sentence':     f'💎 اكتب منشور "جملة تهز القلب"\nاختر جملة واحدة عميقة مؤثرة من القرآن أو السنة أو الحكماء\nاكتبها وحدها بشكل بارز + تأمل عميق فيها + كيف تلمس حياتنا\nاختم بسؤال: ماذا تقول لك هذه الجملة؟ 👇\nالأسلوب: {p}',
        'scholar_quote':      f'📚 اكتب منشور "اقتباس من عالم مسلم"\nاختر قولاً مأثوراً لعالم إسلامي كبير كابن تيمية أو الغزالي أو ابن القيم\nاكتبه بشكل بارز + اسم العالم + شرح عميق + كيف نطبقه\nالأسلوب: {p}',
        'wise_men_words':     f'✨ اكتب منشور "كلام العارفين"\nاختر قولاً حكيماً من أقوال الصالحين والأولياء والزاهدين\nاكتبه بشكل بارز + من قاله + شرح المعنى العميق + الأثر في القلب\nالأسلوب: {p}',
        # ⚖️ حكم وأمثال
        'arabic_proverb':     f'⚖️ اكتب منشور "حكمة عربية أصيلة"\nاختر مثلاً عربياً قديماً أصيلاً\nاكتبه بشكل بارز + أصله وقصته + شرحه + كيف نطبقه اليوم\nاختم بسؤال: هل سمعت هذا المثل من قبل؟ 👇\nالأسلوب: {p}',
        'ancestors_wisdom':   f'🏺 اكتب منشور "من حكم الأجداد"\nاختر حكمة تراثية عربية إسلامية عميقة من التراث\nاكتبها بشكل بارز + شرح معناها + كيف تنطبق على حياتنا اليوم\nالأسلوب: {p}',
        'daily_wisdom':       f'💡 اكتب منشور "حكمة اليوم"\nاختر حكمة قصيرة مؤثرة من مصدر إسلامي أو عربي\nاكتبها بشكل بارز + شرح بسيط + درس عملي واحد\nاختم بـ: احفظها واعمل بها اليوم 🌟\nالأسلوب: {p}',
        'marriage_islam':     f'💍 اكتب منشور "الزواج في الإسلام"\nاختر جانباً جميلاً من الزواج الإسلامي - حقوق أو آداب أو فضائل\nآيات وأحاديث + كيف يجعل الإسلام الزواج سكينة ومودة ورحمة\nالأسلوب: {p}',
        'if_prophet_era':   f'🌹 اكتب منشور "لو كنت في زمن النبي"\n "لو كنت في زمن النبي"\nاختر موقفاً من السيرة النبوية واكتبه بصيغة تفاعلية\nاكتب: تخيّل أنك كنت موجوداً حين... ماذا كنت ستفعل؟\nاسرد الموقف بأسلوب قصصي مؤثر + الدرس + سؤال: شاركنا ماذا كنت ستفعل؟ 👇\nالأسلوب: {p}',
    }
    return prompts.get(post_type, f'اكتب منشور إسلامي مميز عن: {t}\nالأسلوب: {p}\nاستند إلى القرآن والسنة في كتابتك')

def generate_content(topic, post_type, page_name, page_id='', personality='mixed'):
    settings = load_json(SETTINGS_FILE, {})
    api_key = settings.get('groq_api_key', '')
    if page_id: post_type = get_smart_post_type(page_id, post_type)
    seasonal_ctx = get_seasonal_context()
    now_tz = datetime.now(pytz.timezone('Asia/Riyadh'))
    # تحويل post_type تلقائي حسب المناسبة الحالية
    fixed_types = ['quran_tafseer','friday_khutba','adhkar_morning','adhkar_evening']
    if post_type not in fixed_types:
        # مناسبة دينية حالية؟ انشر عنها بنسبة 60%
        if seasonal_ctx and random.random() < 0.6:
            chosen = random.choice(seasonal_ctx)
            post_type = chosen["ptype"]
        # فجر - دعاء الفجر
        elif now_tz.hour in [4,5] and random.random() < 0.5:
            post_type = 'fajr_duaa'
        # صباح - اذكار او سلسلة يومية
        elif now_tz.hour in [6,7,8] and random.random() < 0.4:
            post_type = random.choice(['adhkar_morning','allah_name','hadith_daily'])
        # ظهر - محتوى تعليمي او تفاعلي
        elif now_tz.hour in [12,13] and random.random() < 0.3:
            post_type = random.choice(['dini_question','complete_aya','who_is_sahabi','islamic_did_you_know'])
        # عصر - قصص وسيرة
        elif now_tz.hour in [15,16] and random.random() < 0.3:
            post_type = random.choice(['seerah_manners','sahabi_heroism','battles_heroism'])
        # مغرب - ايات وتامل
        elif now_tz.hour in [18,19] and random.random() < 0.3:
            post_type = random.choice(['aya_taammul','creation_reflection','islam_answers'])
        # مساء - اذكار او نصيحة
        elif now_tz.hour in [20,21,22] and random.random() < 0.4:
            post_type = random.choice(['adhkar_evening','night_reminder'])
        # جمعة صباحا - خطبة
        elif now_tz.weekday() == 4 and now_tz.hour in [9,10,11] and random.random() < 0.5:
            post_type = 'friday_khutba'
    if not api_key:
        return generate_fallback_content(topic, post_type), post_type
    try:
        angles = [
            'بأسلوب قصصي شيق', 'بطريقة مباشرة وعملية',
            'بأسلوب يثير الفضول', 'بطريقة عاطفية ومؤثرة'
        ]
        angle = random.choice(angles)
        prompt_text = get_prompt_for_type(post_type, topic, personality, seasonal_ctx)
        hashtags = get_hashtags(post_type, topic)
        system_msg = 'أنت كاتب محتوى إسلامي متخصص. تكتب بأسلوب قرآني راقٍ يجمع بين العلم الشرعي والأسلوب المؤثر. اكتب باللغة العربية الفصحى فقط بدون أي حروف أجنبية. استند إلى القرآن الكريم والسنة النبوية. ابدأ مباشرة بالمحتوى. استخدم الإيموجي المناسبة.'
        user_msg = (
            'اكتب منشور فيسبوك عربي مميز.\n'
            + prompt_text
            + '\nالاسلوب: ' + angle
            + '\nالطول: 150 الى 250 كلمة'
            + '\nاضف في النهاية:\n' + hashtags
        )
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg}
            ],
            "max_tokens": 900,
            "temperature": 0.85
        }
        logger.info(f"Groq API call — type:{post_type} topic:{topic}")
        r = requests.post(url, headers=headers, json=payload, timeout=45)
        data = r.json()

        if 'error' in data:
            err = data['error'].get('message', 'Groq error')
            logger.error(f"Groq API error: {err}")
            return f"خطأ Groq: {err}", post_type

        if 'choices' in data and data['choices']:
            result = data['choices'][0]['message']['content'].strip()
            if has_foreign_words(result):
                result = clean_foreign_words(result)
            if page_id:
                record_post_type(page_id, post_type)
            logger.info(f"Content generated OK — {len(result)} chars")
            return result, post_type

        logger.error(f"Groq unexpected response: {data}")
        return generate_fallback_content(topic, post_type), post_type

    except requests.Timeout:
        logger.error("Groq API timeout")
        return "انتهت مهلة الاتصال بـ Groq. حاول مرة اخرى.", post_type
    except Exception as e:
        logger.error(f"Generate error: {e}")
        return generate_fallback_content(topic, post_type), post_type

def generate_fallback_content(topic, post_type):
    t = {
        'tips': '💡 نصيحة اليوم\n\nشاركنا رأيك! 👇\n#نصائح',
        'offer': '🛍️ عرض مميز\n\n#عروض',
        'question': '🤔 سؤال اليوم\n\nشاركنا! 💬',
        'fact': '📚 هل تعلم؟\n\n#معلومة',
        'motivation': '✨ لا تستسلم!\n\n#تحفيز',
        'quran': '🌟 آية كريمة\n\n#القرآن_الكريم',
        'quran_tafseer': '📖 تفسير من كتاب الله\n\n#تفسير_القرآن',
        'prophet_story': '🕌 من قصص الأنبياء\n\n#إسلاميات',
        'sahabi_story': '⭐ من قصص الصحابة\n\n#إسلاميات',
        'islamic_fact': '📖 معلومة إسلامية\n\n#إسلاميات',
        'hadith': '🌹 حديث شريف\n\n#حديث_نبوي',
        'duaa': '🤲 دعاء الصباح\n\nآمين\n#دعاء',
        'friday': '🕌 جمعة مباركة\n\n#الجمعة',
        'seasonal': '✨ مناسبة مباركة\n\n#إسلاميات',
        'wisdom': '💡 حكمة اليوم\n\n#حكمة',
        'poet_quote': '🎭 بيت شعر\n\n#أدب_عربي',
        'video_idea': '🎥 محتوى جديد\n\nشاركوا! 🔄',
    }
    return t.get(post_type, f'منشور عن {topic} ✨')

def should_post_today(schedule):
    days = schedule.get('days', ['mon','tue','wed','thu','fri','sat','sun'])
    if not days: return True
    day_map = {'mon':0,'tue':1,'wed':2,'thu':3,'fri':4,'sat':5,'sun':6}
    today = datetime.now(pytz.timezone('Asia/Riyadh')).weekday()
    return any(day_map.get(d) == today for d in days)

def publish_scheduled_post(page_id_str, schedule_id):
    pages = load_json(PAGES_FILE, [])
    page = next((p for p in pages if p['id'] == page_id_str), None)
    if not page or not page.get('active', True): return
    schedule = next((s for s in page.get('schedules',[]) if s['id'] == schedule_id), None)
    if not schedule or not should_post_today(schedule): return
    post_type = schedule.get('post_type', 'tips')
    personality = page.get('personality', 'mixed')
    use_image = page.get('use_image', True)
    content, actual_type = generate_content(page.get('topic','عام'), post_type, page['name'], page['id'], personality)
    if use_image:
        success, result = post_image_to_facebook(page['page_id'], page['access_token'], content, actual_type)
    else:
        success, result = post_to_facebook(page['page_id'], page['access_token'], content)
    type_name = POST_TYPES.get(actual_type, actual_type)
    mode = '🖼️' if use_image else '📝'
    message = f"✅ {mode} ({type_name}): {content[:60]}..." if success else f"❌ فشل: {result}"
    add_log(page['name'], 'success' if success else 'error', message)
    update_stats(success, actual_type)
    update_weekly_stats(page['name'], actual_type, success)

def setup_scheduler():
    scheduler.remove_all_jobs()
    pages = load_json(PAGES_FILE, [])
    tz = pytz.timezone('Asia/Riyadh')
    for page in pages:
        if not page.get('active', True): continue
        for schedule in page.get('schedules', []):
            try:
                h, m = map(int, schedule['time'].split(':'))
                days = schedule.get('days', [])
                dow = ','.join(days) if days else 'mon,tue,wed,thu,fri,sat,sun'
                scheduler.add_job(publish_scheduled_post, CronTrigger(hour=h,minute=m,day_of_week=dow,timezone=tz),
                    args=[page['id'],schedule['id']], id=f"{page['id']}_{schedule['id']}", replace_existing=True)
            except Exception as e:
                logger.error(f"Schedule error: {e}")

@app.route('/')
def index(): return render_template('index.html')

@app.route('/token-generator')
def token_generator(): return render_template('token-generator.html')

@app.route('/ping')
def ping(): return 'pong', 200

@app.route('/api/settings', methods=['GET'])
def get_settings():
    settings = load_json(SETTINGS_FILE, {})
    safe = {k:v for k,v in settings.items() if k != 'groq_api_key'}
    safe['has_api_key'] = bool(settings.get('groq_api_key'))
    return jsonify(safe)

@app.route('/api/settings', methods=['POST'])
def save_settings():
    settings = load_json(SETTINGS_FILE, {})
    settings.update(request.json)
    save_json(SETTINGS_FILE, settings)
    return jsonify({'success': True})

@app.route('/api/pages', methods=['GET'])
def get_pages(): return jsonify(load_json(PAGES_FILE, []))

@app.route('/api/pages', methods=['POST'])
def add_page():
    data = request.json
    pages = load_json(PAGES_FILE, [])
    if not data.get('schedules'):
        data['schedules'] = [{'id':f"s_{datetime.now().strftime('%f')}","time":"09:00","post_type":"tips","days":["mon","tue","wed","thu","fri","sat","sun"]}]
    data['id'] = f"page_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    data['active'] = True
    data.setdefault('personality','mixed')
    data.setdefault('use_image', True)
    data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pages.append(data)
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success':True,'id':data['id']})

@app.route('/api/pages/<page_id>', methods=['PUT'])
def update_page(page_id):
    pages = load_json(PAGES_FILE, [])
    for i,p in enumerate(pages):
        if p['id'] == page_id:
            pages[i].update(request.json)
            break
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True})

@app.route('/api/pages/<page_id>', methods=['DELETE'])
def delete_page(page_id):
    pages = [p for p in load_json(PAGES_FILE,[]) if p['id'] != page_id]
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True})

@app.route('/api/pages/<page_id>/schedules', methods=['POST'])
def add_schedule(page_id):
    data = request.json
    pages = load_json(PAGES_FILE, [])
    for page in pages:
        if page['id'] == page_id:
            if 'schedules' not in page: page['schedules'] = []
            data['id'] = f"s_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            if 'days' not in data: data['days'] = ['mon','tue','wed','thu','fri','sat','sun']
            page['schedules'].append(data)
            break
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True})

@app.route('/api/pages/<page_id>/schedules/<schedule_id>', methods=['DELETE'])
def delete_schedule(page_id, schedule_id):
    pages = load_json(PAGES_FILE, [])
    for page in pages:
        if page['id'] == page_id:
            page['schedules'] = [s for s in page.get('schedules',[]) if s['id'] != schedule_id]
            break
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True})

@app.route('/api/publish/page/<page_id>', methods=['POST'])
def publish_page(page_id):
    data = request.json or {}
    pages = load_json(PAGES_FILE, [])
    page = next((p for p in pages if p['id'] == page_id), None)
    if not page: return jsonify({'success':False,'error':'الصفحة غير موجودة'})
    post_type = data.get('post_type','tips')
    personality = page.get('personality','mixed')
    use_image = data.get('use_image', page.get('use_image', True))
    content, actual_type = generate_content(page.get('topic','عام'), post_type, page['name'], page_id, personality)
    if use_image:
        success, result = post_image_to_facebook(page['page_id'], page['access_token'], content, actual_type)
    else:
        success, result = post_to_facebook(page['page_id'], page['access_token'], content)
    type_name = POST_TYPES.get(actual_type, actual_type)
    mode = '🖼️' if use_image else '📝'
    add_log(page['name'],'success' if success else 'error',f"{'✅' if success else '❌'} {mode} ({type_name}): {content[:60]}...")
    update_stats(success, actual_type)
    update_weekly_stats(page['name'], actual_type, success)
    return jsonify({'success':success,'result':result,'content':content,'type':actual_type})

@app.route('/api/publish/all', methods=['POST'])
def publish_all():
    pages = load_json(PAGES_FILE, [])
    results = []
    for page in pages:
        if not page.get('active', True): continue
        post_type = page.get('schedules',[{'post_type':'tips'}])[0].get('post_type','tips')
        personality = page.get('personality','mixed')
        content, actual_type = generate_content(page.get('topic','عام'), post_type, page['name'], page['id'], personality)
        success, result = post_to_facebook(page['page_id'], page['access_token'], content)
        add_log(page['name'],'success' if success else 'error',f"{'✅' if success else '❌'} {content[:60]}...")
        update_stats(success, actual_type)
        results.append({'page':page['name'],'success':success})
    return jsonify({'success':True,'results':results})

@app.route('/api/logs', methods=['GET'])
def get_logs(): return jsonify(load_json(LOGS_FILE, []))

@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = load_json(STATS_FILE, {'total':0,'today':0,'errors':0})
    pages = load_json(PAGES_FILE, [])
    stats['pages'] = len(pages)
    stats['active_pages'] = sum(1 for p in pages if p.get('active',True))
    stats['total_schedules'] = sum(len(p.get('schedules',[])) for p in pages)
    return jsonify(stats)

@app.route('/api/weekly_report', methods=['GET'])
def weekly_report():
    week = datetime.now().strftime('%Y-W%W')
    prev = (datetime.now()-timedelta(weeks=1)).strftime('%Y-W%W')
    weekly = load_json(WEEKLY_FILE, {})
    current = weekly.get(week,{'total':0,'success':0,'by_page':{},'by_type':{}})
    previous = weekly.get(prev,{'total':0,'success':0,'by_page':{},'by_type':{}})
    by_type = current.get('by_type',{})
    best_type = max(by_type,key=by_type.get) if by_type else ''
    by_page = current.get('by_page',{})
    best_page = max(by_page,key=by_page.get) if by_page else ''
    return jsonify({'week':week,'current':current,'previous':previous,
        'best_type':POST_TYPES.get(best_type,best_type),'best_page':best_page,
        'seasonal_events':get_seasonal_context(),
        'total_types':{POST_TYPES.get(k,k):v for k,v in by_type.items()}})

@app.route('/api/post_types', methods=['GET'])
def get_post_types(): return jsonify(POST_TYPES)

@app.route('/api/schedule_templates', methods=['GET'])
def get_schedule_templates():
    return jsonify({k: {'desc': v['desc'], 'hours_count': len(v['hours'])} for k,v in SCHEDULE_TEMPLATES.items()})

@app.route('/api/pages/<page_id>/apply_template', methods=['POST'])
def apply_template(page_id):
    data = request.json or {}
    template_name = data.get('template')
    if template_name not in SCHEDULE_TEMPLATES:
        return jsonify({'success': False, 'error': 'القالب غير موجود'})
    pages = load_json(PAGES_FILE, [])
    page_idx = next((i for i,p in enumerate(pages) if p['id'] == page_id), None)
    if page_idx is None:
        return jsonify({'success': False, 'error': 'الصفحة غير موجودة'})
    template = SCHEDULE_TEMPLATES[template_name]
    # احسب offset التنويع بناءً على رقم الصفحة في القائمة
    offset = page_idx % 6  # تنويع تلقائي بين الصفحات
    hours = template['hours']
    # دوّر الساعات حسب offset الصفحة
    rotated = hours[offset:] + hours[:offset]
    all_days = ['mon','tue','wed','thu','fri','sat','sun']
    now = datetime.now().strftime('%Y%m%d%H%M%S%f')
    schedules = []
    for i, (hour, category) in enumerate(rotated):
        schedules.append({
            'id': f"s_{now}_{i}",
            'time': f"{hour:02d}:00",
            'post_type': category,
            'days': all_days
        })
    # احتفظ بالمواعيد القديمة أو استبدلها
    replace = data.get('replace', True)
    if replace:
        pages[page_idx]['schedules'] = schedules
    else:
        existing = pages[page_idx].get('schedules', [])
        pages[page_idx]['schedules'] = existing + schedules
    pages[page_idx]['template'] = template_name
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True, 'schedules_added': len(schedules), 'template': template_name})

@app.route('/api/post_categories', methods=['GET'])
def get_post_categories(): return jsonify(POST_CATEGORIES)

@app.route('/api/category_names', methods=['GET'])
def get_category_names():
    # يرجع الفئات الرئيسية فقط للواجهة
    return jsonify({k: k for k in POST_CATEGORIES.keys()})

@app.route('/api/personalities', methods=['GET'])
def get_personalities(): return jsonify(PAGE_PERSONALITIES)

@app.route('/api/seasonal', methods=['GET'])
def get_seasonal():
    current = get_seasonal_context()
    upcoming = get_upcoming_event()
    return jsonify({
        'events': [e['name'] for e in current],
        'current_detail': current,
        'upcoming': [{'name': e['name'], 'days_until': e['days_until'], 'date': str(e['start'])} for e in upcoming]
    })

@app.route('/api/get_page_tokens', methods=['POST'])
def get_page_tokens():
    data = request.json
    app_id = data.get('app_id','')
    app_secret = data.get('app_secret','')
    user_token = data.get('user_token','')
    if not app_id or not app_secret or not user_token:
        return jsonify({'success':False,'error':'أدخل جميع البيانات'})
    try:
        r1 = requests.get("https://graph.facebook.com/oauth/access_token",
            params={'grant_type':'fb_exchange_token','client_id':app_id,'client_secret':app_secret,'fb_exchange_token':user_token},timeout=15)
        d1 = r1.json()
        if 'error' in d1: return jsonify({'success':False,'error':d1['error'].get('message','خطأ')})
        r2 = requests.get("https://graph.facebook.com/v19.0/me/accounts",
            params={'access_token':d1['access_token']},timeout=15)
        d2 = r2.json()
        if 'error' in d2: return jsonify({'success':False,'error':d2['error'].get('message','خطأ')})
        pages = d2.get('data',[])
        if not pages: return jsonify({'success':False,'error':'لا توجد صفحات'})
        return jsonify({'success':True,'pages':[{'name':p['name'],'id':p['id'],'token':p['access_token']} for p in pages]})
    except Exception as e:
        return jsonify({'success':False,'error':str(e)})

@app.route('/api/test_token', methods=['POST'])
def test_token():
    data = request.json
    try:
        r = requests.get(f"https://graph.facebook.com/v19.0/me?access_token={data['access_token']}",timeout=10)
        result = r.json()
        if 'id' in result: return jsonify({'success':True,'name':result.get('name','الصفحة')})
        return jsonify({'success':False,'error':result.get('error',{}).get('message','خطأ')})
    except Exception as e:
        return jsonify({'success':False,'error':str(e)})

@app.route('/api/quran_progress', methods=['GET'])
def get_quran_progress_api():
    p = get_quran_progress()
    si = next((x for x in QURAN_SURAHS if x[0]==p['surah']), QURAN_SURAHS[0])
    total = sum(s[2] for s in QURAN_SURAHS)
    done = sum(s[2] for s in QURAN_SURAHS if s[0]<p['surah'])+p['ayah']
    return jsonify({'surah':p['surah'],'surah_name':si[1],'ayah':p['ayah'],
        'total_surah_ayahs':si[2],'progress_percent':round((done/total)*100,2),
        'done_ayahs':done,'total_ayahs':total})

if not scheduler.running:
    scheduler.start()
setup_scheduler()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
