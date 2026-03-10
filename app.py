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
    'quran_ayah': 'آية اليوم',
    'quran_tafseer': 'تفسير القرآن بالترتيب',
    'quran_recitation': 'تلاوة وتفسير آية',
    'quran_khatma': 'ختمة قرآنية',
    # 🕌 الدروس والمحاضرات
    'friday_khutba': 'خطبة الجمعة',
    'fiqh_lesson': 'درس فقهي',
    'scholar_lecture': 'محاضرة عالم دين',
    # 🤲 الأدعية والأذكار
    'morning_adhkar': 'أذكار الصباح',
    'evening_adhkar': 'أذكار المساء',
    'occasion_duaa': 'دعاء مناسبة',
    'tasbih': 'تسبيح وأوراد',
    # ✨ المحتوى التحفيزي الديني
    'prophet_story': 'قصة نبي',
    'sahabi_story': 'قصة صحابي',
    'islamic_wisdom': 'عبرة وموعظة دينية',
    # 📚 الفتاوى والأحكام
    'fatwa': 'فتوى وحكم شرعي',
    'ibadah_ruling': 'أحكام العبادات',
    'muamalat': 'فقه المعاملات',
    # 🌙 المناسبات الدينية
    'ramadan': 'محتوى رمضان',
    'eid': 'محتوى العيدين',
    'hajj_umrah': 'الحج والعمرة',
    # 📖 قصص وحكايات
    'story_suspense': 'قصة تشويقية',
    'story_romance': 'قصة رومانسية',
    'story_horror': 'قصة رعب',
    'story_personal': 'تجربة شخصية حقيقية',
    'story_today': 'اللي حصلي النهارده',
    'story_serial': 'قصة متسلسلة',
    # 😂 كوميدي
    'meme': 'ميم ونكتة',
    'comedy_sketch': 'موقف كوميدي',
    # 🎭 دراما وتشويق
    'drama_mystery': 'غرائب وعجائب',
    'truth_or_lie': 'صح ولا كذب؟',
    # 🌍 وثائقي
    'weird_facts': 'حقائق غريبة ومثيرة',
    'country_culture': 'ثقافات وبلدان',
    'history_simple': 'تاريخ بشكل مبسط',
    # 💡 تحفيزي
    'success_story': 'قصة نجاح',
    'life_change': 'قصة تغيير حياة',
    'inspiration_quote': 'اقتباس ملهم',
    # 👳 قصص الأنبياء
    'prophet_moses': 'قصة سيدنا موسى',
    'prophet_yusuf': 'قصة سيدنا يوسف',
    'prophet_ibrahim': 'قصة سيدنا إبراهيم',
    'prophet_miracles': 'المعجزات والأحداث العظيمة',
    'prophet_lessons': 'عبر ودروس من قصص الأنبياء',
    # ⚔️ قصص الصحابة
    'sahabi_heroism': 'بطولات وتضحيات الصحابة',
    'sahabi_islam': 'قصص إسلام الصحابة',
    'sahabi_moment': 'مواقف مؤثرة من حياة الصحابة',
    # 😢 قصص مؤثرة ومبكية
    'story_tawba': 'قصة توبة وعودة لله',
    'story_good_end': 'قصة حسن الخاتمة',
    'story_karama': 'قصة كرامات الصالحين',
    # 💫 قصص من الحياة اليومية
    'story_divine_gift': 'ربنا كرمني لما...',
    'story_duaa_answered': 'قصة استجابة الدعاء',
    'story_religious_exp': 'تجربة شخصية دينية',
    # 🌅 أذكار اليوم
    'adhkar_morning': 'أذكار الصباح',
    'adhkar_evening': 'أذكار المساء',
    'adhkar_home': 'دعاء دخول وخروج البيت',
    'adhkar_sleep': 'أذكار النوم',
    # 🤲 أدعية المناسبات
    'duaa_hardship': 'دعاء الكرب والضيقة',
    'duaa_rizq': 'دعاء الرزق والفرج',
    'duaa_ramadan_friday': 'أدعية رمضان والجمعة',
    # ✨ الأدعية القصيرة المؤثرة
    'duaa_short': 'دعاء قصير مؤثر سهل الحفظ',
    'duaa_healing': 'دعاء الشفاء والرحمة',
    'duaa_parents': 'دعاء للوالدين والمغفرة',
    'tips': 'نصيحة مفيدة',
    'offer': 'عرض ومنتج مميز',
    'question': 'سؤال تفاعلي',
    'fact': 'معلومة مثيرة',
    'motivation': 'كلمة تحفيزية',
    'wisdom': 'حكمة وقول مأثور',
    'poet_quote': 'بيت شعر وتأمل',
}

# الفئات الرئيسية فقط للاختيار - الموقع يختار النوع تلقائياً
POST_CATEGORIES = {
    '📖 القرآن الكريم': [
        'quran_ayah','quran_tafseer','quran_recitation','quran_khatma'
    ],
    '🕌 الدروس والمحاضرات': [
        'friday_khutba','fiqh_lesson','scholar_lecture'
    ],
    '👳 قصص الأنبياء': [
        'prophet_story','prophet_moses','prophet_yusuf','prophet_ibrahim',
        'prophet_miracles','prophet_lessons'
    ],
    '⚔️ قصص الصحابة': [
        'sahabi_story','sahabi_heroism','sahabi_islam','sahabi_moment'
    ],
    '😢 قصص مؤثرة ومبكية': [
        'story_tawba','story_good_end','story_karama'
    ],
    '💫 قصص من الحياة اليومية': [
        'story_divine_gift','story_duaa_answered','story_religious_exp'
    ],
    '🌅 أذكار اليوم': [
        'adhkar_morning','adhkar_evening','adhkar_home','adhkar_sleep'
    ],
    '🤲 أدعية المناسبات': [
        'duaa_hardship','duaa_rizq','duaa_ramadan_friday','occasion_duaa','tasbih'
    ],
    '✨ أدعية قصيرة مؤثرة': [
        'duaa_short','duaa_healing','duaa_parents'
    ],
    '💡 المحتوى التحفيزي الديني': [
        'islamic_wisdom','motivation','inspiration_quote','success_story','life_change'
    ],
    '📚 الفتاوى والأحكام': [
        'fatwa','ibadah_ruling','muamalat'
    ],
    '🌙 المناسبات الدينية': [
        'ramadan','eid','hajj_umrah'
    ],
    '📖 قصص وحكايات': [
        'story_suspense','story_romance','story_horror',
        'story_personal','story_today','story_serial'
    ],
    '😂 محتوى كوميدي': [
        'meme','comedy_sketch'
    ],
    '🎭 دراما وتشويق': [
        'drama_mystery','truth_or_lie'
    ],
    '🌍 محتوى وثائقي': [
        'weird_facts','country_culture','history_simple'
    ],
    '💡 متنوع وعام': [
        'tips','offer','question','fact','wisdom','poet_quote'
    ],
}

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

def get_seasonal_context():
    now = datetime.now(pytz.timezone('Asia/Riyadh'))
    month, day, weekday = now.month, now.day, now.weekday()
    contexts = []
    if weekday == 4: contexts.append('يوم الجمعة المبارك')
    if month in [3,4]: contexts.append('شهر رمضان المبارك')
    if month == 4 and day <= 10: contexts.append('عيد الفطر المبارك')
    if month in [6,7] and day <= 15: contexts.append('موسم الحج وعيد الأضحى')
    if month == 3 and day >= 20: contexts.append('العشر الأواخر من رمضان')
    if month == 7: contexts.append('شهر محرم والسنة الهجرية الجديدة')
    if month == 9 and day <= 20: contexts.append('ذكرى المولد النبوي الشريف')
    return contexts

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
    if post_type in ['quran','quran_tafseer']:
        return ' '.join(random.sample(HASHTAGS['quran'],4) + random.sample(HASHTAGS['islamic'],2))
    elif post_type == 'hadith':
        return ' '.join(HASHTAGS['hadith'][:3] + random.sample(HASHTAGS['islamic'],2))
    elif post_type in ['prophet_story','sahabi_story','islamic_fact','duaa','friday','seasonal']:
        return ' '.join(random.sample(HASHTAGS['islamic'],5))
    elif post_type == 'motivation':
        return ' '.join(random.sample(HASHTAGS['motivation'],4))
    elif post_type in ['quran_ayah','quran_tafseer','quran_recitation','quran_khatma']:
        return ' '.join(random.sample(HASHTAGS['quran'],4) + random.sample(HASHTAGS['islamic'],2))
    elif post_type in ['friday_khutba','fiqh_lesson','scholar_lecture','islamic_wisdom','fatwa','ibadah_ruling','muamalat']:
        return ' '.join(random.sample(HASHTAGS['islamic'],5) + ['#علم_نافع'])
    elif post_type in ['morning_adhkar','evening_adhkar','occasion_duaa','tasbih']:
        return ' '.join(['#أذكار','#ذكر_الله','#دعاء','#اللهم'] + random.sample(HASHTAGS['islamic'],2))
    elif post_type in ['ramadan','eid','hajj_umrah']:
        return ' '.join(random.sample(HASHTAGS['islamic'],4) + ['#مناسبات_إسلامية'])
    elif post_type in ['prophet_moses','prophet_yusuf','prophet_ibrahim','prophet_miracles','prophet_lessons','prophet_story']:
        return ' '.join(['#قصص_الأنبياء','#الأنبياء_والرسل'] + random.sample(HASHTAGS['islamic'],3))
    elif post_type in ['sahabi_heroism','sahabi_islam','sahabi_moment','sahabi_story']:
        return ' '.join(['#قصص_الصحابة','#الصحابة_الكرام'] + random.sample(HASHTAGS['islamic'],3))
    elif post_type in ['story_tawba','story_good_end','story_karama','story_divine_gift','story_duaa_answered','story_religious_exp']:
        return ' '.join(['#قصص_إسلامية','#قصص_مؤثرة','#رحمة_الله'] + random.sample(HASHTAGS['islamic'],2))
    elif post_type in ['adhkar_morning','adhkar_evening','adhkar_home','adhkar_sleep','morning_adhkar','evening_adhkar']:
        return ' '.join(['#أذكار','#أذكار_الصباح','#أذكار_المساء','#ذكر_الله','#حصن_المسلم'])
    elif post_type in ['duaa_hardship','duaa_rizq','duaa_ramadan_friday','duaa_short','duaa_healing','duaa_parents','occasion_duaa','tasbih']:
        return ' '.join(['#دعاء','#اللهم','#دعاء_مستجاب'] + random.sample(HASHTAGS['islamic'],2))
    elif post_type in ['prophet_story','sahabi_story']:
        return ' '.join(['#قصص_الأنبياء','#قصص_الصحابة'] + random.sample(HASHTAGS['islamic'],3))
    elif post_type in ['wisdom','poet_quote','inspiration_quote']:
        return ' '.join(random.sample(HASHTAGS['wisdom'],4))
    elif post_type in ['story_suspense','story_romance','story_horror','story_personal','story_today','story_serial']:
        return ' '.join(random.sample(HASHTAGS['story'],4) + random.sample(HASHTAGS['general'],1))
    elif post_type in ['meme','comedy_sketch']:
        return ' '.join(random.sample(HASHTAGS['comedy'],4) + random.sample(HASHTAGS['general'],1))
    elif post_type in ['drama_mystery','truth_or_lie']:
        return ' '.join(random.sample(HASHTAGS['drama'],4) + random.sample(HASHTAGS['general'],1))
    elif post_type in ['weird_facts','country_culture','history_simple']:
        return ' '.join(random.sample(HASHTAGS['documentary'],4) + random.sample(HASHTAGS['general'],1))
    elif post_type in ['success_story','life_change']:
        return ' '.join(random.sample(HASHTAGS['success'],4) + random.sample(HASHTAGS['motivation'],2))
    elif post_type == 'offer':
        return ' '.join(random.sample(HASHTAGS['offer'],3)+random.sample(HASHTAGS['general'],1))
    else:
        return ' '.join(random.sample(HASHTAGS['tips'],3)+random.sample(HASHTAGS['general'],1))

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
    try:
        img_data = create_post_image(content[:200], post_type)
        if img_data:
            url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
            r = requests.post(url, data={'caption': content, 'access_token': access_token},
                files={'source': ('image.jpg', img_data, 'image/jpeg')}, timeout=60)
            result = r.json()
            if 'id' in result or 'post_id' in result:
                return True, result.get('post_id', result.get('id',''))
        return post_to_facebook(page_id, access_token, content)
    except Exception as e:
        logger.error(f"Image post error: {e}")
        return post_to_facebook(page_id, access_token, content)

def post_to_facebook(page_id, access_token, content):
    try:
        url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
        r = requests.post(url, data={'message': content, 'access_token': access_token}, timeout=30)
        result = r.json()
        if 'id' in result: return True, result['id']
        return False, result.get('error',{}).get('message','خطأ غير معروف')
    except Exception as e:
        return False, str(e)

def get_prompt_for_type(post_type, topic, personality='mixed', seasonal_ctx=None):
    pname = PAGE_PERSONALITIES.get(personality, PAGE_PERSONALITIES['mixed'])
    t = topic
    p = pname
    # أنواع خاصة تحتاج معالجة مختلفة
    if post_type == 'quran_tafseer':
        s, a, sname = get_next_ayah()
        return f'اكتب منشور فيسبوك إسلامي عن الآية رقم {a} من سورة {sname} (السورة رقم {s}).\n📖 عنوان: تفسير سورة {sname} - الآية {a}\n- نص الآية كاملاً - تفسيرها بأسلوب بسيط - الفوائد - دعاء في الختام\nباللغة العربية فقط.'
    if post_type in ['seasonal','ramadan','eid','hajj_umrah'] and seasonal_ctx:
        ctx = random.choice(seasonal_ctx)
        return f'اكتب منشور خاص بـ: {ctx}\nالموضوع: {t}\nالأسلوب: {p}'
    prompts = {
        # القرآن الكريم
        'quran_ayah':       f'📖 اكتب منشور آية اليوم - اختر آية قرآنية جميلة مؤثرة\nنص الآية + اسم السورة + تفسير مبسط + فائدة + دعاء\nالأسلوب: {p}',
        'quran_recitation': f'🎙️ اكتب منشور تلاوة وتفسير آية عن: {t}\nالآية + معناها + كيف نطبقها + دعاء\nالأسلوب: {p}',
        'quran_khatma':     f'📿 اكتب منشور يشجع على ختم القرآن - فضل القراءة + خطة مقترحة + تحدٍّ للمتابعين\nاختم بـ: من معنا في الختمة؟ اكتب 📖 في التعليقات\nالأسلوب: {p}',
        # الدروس والمحاضرات
        'friday_khutba':    f'🕌 اكتب خطبة جمعة مؤثرة عن: {t}\nحمد + موضوع بأدلة قرآنية وحديثية + توجيهات عملية + دعاء\nالأسلوب: {p}',
        'fiqh_lesson':      f'📚 اكتب درس فقهي مبسط عن: {t}\nالمسألة + الحكم الشرعي + دليله + تطبيق عملي + سؤال للمتابعين\nالأسلوب: {p}',
        'scholar_lecture':  f'🎓 اكتب ملخص فائدة علمية من محاضرة عن: {t}\nالموضوع + أبرز النقاط + حكمة العالم + سؤال تفاعلي\nالأسلوب: {p}',
        # الأذكار
        'morning_adhkar':   f'🌅 اكتب منشور أذكار الصباح الكاملة\nالأذكار المأثورة + فضل كل ذكر + اختم بـ: ابدأ يومك بذكر الله ☀️\nالأسلوب: {p}',
        'evening_adhkar':   f'🌙 اكتب منشور أذكار المساء الكاملة\nالأذكار المأثورة + فضل كل ذكر + اختم بـ: أمسيت في حمى الله 🌙\nالأسلوب: {p}',
        'adhkar_morning':   f'🌅 اكتب منشور أذكار الصباح المباركة\nالأذكار المأثورة + فضل المداومة + اختم بـ: اللهم بارك لنا في صباحنا ☀️\nالأسلوب: {p}',
        'adhkar_evening':   f'🌙 اكتب منشور أذكار المساء\nالأذكار المأثورة + فضلها + اختم بـ: اللهم بارك لنا في مسائنا 🌙\nالأسلوب: {p}',
        'adhkar_home':      f'🏠 اكتب منشور دعاء دخول وخروج البيت\nالدعاء كاملاً + الفضل + السنة النبوية + تشجيع على التطبيق\nالأسلوب: {p}',
        'adhkar_sleep':     f'😴 اكتب منشور أذكار النوم\nالأذكار المأثورة + آية الكرسي + سنن النوم + اختم بدعاء\nالأسلوب: {p}',
        'occasion_duaa':    f'🤲 اكتب دعاء مناسبة مؤثر عن: {t}\nالدعاء المأثور + شرحه + متى يُقال + اختم بـ: آمين يارب 🤲\nالأسلوب: {p}',
        'tasbih':           f'📿 اكتب منشور تسبيح وأوراد يومية\nالتسبيح + عدده + فضله + قصة أو حديث + اختم بـ: سبحان الله وبحمده 🌿\nالأسلوب: {p}',
        # الأدعية
        'duaa_hardship':    f'😢 اكتب منشور دعاء الكرب والضيقة\nأدعية الكرب المأثورة + قصة فرج + وعد الله بالفرج + اختم بـ: اللهم فرّج كربنا 🤲\nالأسلوب: {p}',
        'duaa_rizq':        f'💰 اكتب منشور دعاء الرزق والفرج\nأدعية الرزق + آية أو حديث + أسباب جلب الرزق + اختم بـ: اللهم ارزقنا 🤍\nالأسلوب: {p}',
        'duaa_ramadan_friday': f'🌙 اكتب منشور أدعية رمضان والجمعة\nأدعية خاصة + ساعة الاستجابة + تشجيع على الدعاء + دعاء جماعي\nالأسلوب: {p}',
        'duaa_short':       f'✨ اكتب منشور دعاء قصير مؤثر سهل الحفظ\nالدعاء بشكل بارز + معناه العميق + متى يُقال + اختم بـ: رددوه معي 🤍\nالأسلوب: {p}',
        'duaa_healing':     f'🌿 اكتب منشور دعاء الشفاء والرحمة\nدعاء الشفاء المأثور + حديث النبي + الله هو الشافي + اختم بـ: اللهم اشفِ مرضانا 🤲\nالأسلوب: {p}',
        'duaa_parents':     f'❤️ اكتب منشور دعاء للوالدين\nالدعاء المأثور + فضل الدعاء للوالدين + قصة قصيرة + اختم بـ: اللهم اغفر لوالدينا 🤍\nالأسلوب: {p}',
        # قصص الأنبياء
        'prophet_story':    f'👳 اكتب قصة نبي مؤثرة - اختر نبياً وموقفاً محدداً\nالموقف + الآيات + الدرس + دعاء + سؤال تفاعلي\nالأسلوب: {p}',
        'prophet_moses':    f'👳 اكتب قصة مؤثرة من قصة سيدنا موسى عليه السلام\nاختر موقفاً محدداً + الآيات القرآنية + العبرة + دعاء\nالأسلوب: {p}',
        'prophet_yusuf':    f'👳 اكتب قصة مؤثرة من قصة سيدنا يوسف عليه السلام\nاختر موقفاً محدداً + الآيات القرآنية + العبرة + دعاء\nالأسلوب: {p}',
        'prophet_ibrahim':  f'👳 اكتب قصة مؤثرة من قصة سيدنا إبراهيم عليه السلام\nاختر موقفاً محدداً + الآيات القرآنية + العبرة + دعاء\nالأسلوب: {p}',
        'prophet_miracles': f'✨ اكتب منشور عن معجزة عظيمة لأحد الأنبياء\nاختر نبياً ومعجزة + اشرحها بأسلوب شيق + الحكمة + اختم بـ: سبحان الله 🤍\nالأسلوب: {p}',
        'prophet_lessons':  f'📖 اكتب درس وعبرة من قصص الأنبياء عن: {t}\nالقصة باختصار + العبرة الأساسية + كيف نطبقها اليوم + سؤال تفاعلي\nالأسلوب: {p}',
        # قصص الصحابة
        'sahabi_story':     f'⚔️ اكتب قصة صحابي مؤثرة - اختر صحابياً وموقفاً محدداً\nالموقف + الدرس + الصلاة على النبي + سؤال\nالأسلوب: {p}',
        'sahabi_heroism':   f'⚔️ اكتب قصة بطولة وتضحية لأحد الصحابة\nاختر صحابياً + موقف بطولي + أسلوب ملحمي + الدرس + سؤال\nالأسلوب: {p}',
        'sahabi_islam':     f'🌟 اكتب قصة إسلام أحد الصحابة الكرام\nاختر صحابياً مشهوراً + قصة إسلامه + التحول في حياته + اختم بدعاء\nالأسلوب: {p}',
        'sahabi_moment':    f'💫 اكتب موقفاً مؤثراً من حياة أحد الصحابة\nالصحابي + الموقف بأسلوب عاطفي + الدرس + سؤال تفاعلي\nالأسلوب: {p}',
        # قصص مؤثرة
        'islamic_wisdom':   f'✨ اكتب عبرة وموعظة دينية مؤثرة عن: {t}\nموضوع وعظي + آية أو حديث + قصة معبرة + دعاء + تذكير\nالأسلوب: {p}',
        'story_tawba':      f'😢 اكتب قصة توبة مؤثرة وعودة إلى الله\nشخص عاش بعيداً ثم تاب + اللحظة الفارقة + حياته بعد التوبة + اختم بـ: باب التوبة مفتوح 🤍\nالأسلوب: {p}',
        'story_good_end':   f'🌹 اكتب قصة مؤثرة عن حسن الخاتمة\nمواقف مؤثرة + علامات حسن الخاتمة + اختم بدعاء: اللهم توفنا وأنت راضٍ عنا 🤲\nالأسلوب: {p}',
        'story_karama':     f'✨ اكتب قصة كرامة من كرامات الصالحين\nقصة حقيقية + السياق + الدرس + اختم بـ: اللهم اجعلنا من عبادك الصالحين 🤍\nالأسلوب: {p}',
        'story_divine_gift': f'💫 اكتب قصة "ربنا كرمني لما..." مؤثرة\nاكتب بضمير المتكلم + لحظة كرم الله + الشعور والامتنان + اختم بـ: شاركنا كيف كرمك ربنا؟ 👇\nالأسلوب: {p}',
        'story_duaa_answered': f'🤲 اكتب قصة مؤثرة عن استجابة الدعاء\nضيقة شديدة + الدعاء + الاستجابة المذهلة + الدرس + اختم بـ: لا تيأس من رحمة الله 🤍\nالأسلوب: {p}',
        'story_religious_exp': f'💬 اكتب تجربة شخصية دينية مؤثرة\nاكتب بضمير المتكلم + موقف غير حياته روحياً + الأثر على إيمانه + سؤال: شاركنا تجربتك 👇\nالأسلوب: {p}',
        # الفتاوى
        'fatwa':            f'⚖️ اكتب إجابة على سؤال شرعي شائع عن: {t}\nالسؤال + الحكم مع دليله + توضيح عملي + اختم بـ: هل لديك سؤال شرعي؟ 👇\nالأسلوب: {p}',
        'ibadah_ruling':    f'🕋 اكتب أحكام عبادة مبسطة عن: {t}\nشروط وأركان + الأخطاء الشائعة + فضل العبادة + تشجيع على الالتزام\nالأسلوب: {p}',
        'muamalat':         f'💼 اكتب حكم فقهي في المعاملات عن: {t}\nالمسألة + الحكم بأدلته + التطبيق + تحذير من المحرمات\nالأسلوب: {p}',
        # المناسبات
        'ramadan':          f'🌙 اكتب منشور رمضاني مميز عن: {t}\nفضل رمضان + عمل مقترح + دعاء + اختم بـ: رمضان كريم 🌙\nالأسلوب: {p}',
        'eid':              f'🎊 اكتب منشور عيد مبارك مميز\nتهنئة جميلة + فضل العيد وسننه + دعاء العيد + تهنئة للمتابعين\nالأسلوب: {p}',
        'hajj_umrah':       f'🕋 اكتب منشور عن الحج أو العمرة عن: {t}\nالفريضة وفضلها + خطوات مبسطة + أدعية + اختم بـ: اللهم ارزقنا زيارة بيتك 🤲\nالأسلوب: {p}',
        # قصص وحكايات
        'story_suspense':   f'🔥 اكتب قصة تشويقية مثيرة عن: {t}\nمشهد جذاب + شخصيات حية + منعطف غير متوقع + نهاية مفاجئة + سؤال: ماذا تتوقع؟\nالأسلوب: {p}',
        'story_romance':    f'💕 اكتب قصة رومانسية مؤثرة عن: {t}\nلقاء أو موقف عاطفي + مشاعر صادقة + اختم بـ: هل مررت بموقف مشابه؟\nالأسلوب: {p}',
        'story_horror':     f'👻 اكتب قصة رعب قصيرة مثيرة عن: {t}\nجو غامض + تصعيد تدريجي + نهاية مفاجئة + سؤال: هل تصدق هذه القصة؟\nالأسلوب: {p}',
        'story_personal':   f'💬 اكتب تجربة شخصية حقيقية مؤثرة عن: {t}\nاكتب بضمير المتكلم + موقف تفصيلي + مشاعر صادقة + درس + سؤال للمتابعين\nالأسلوب: {p}',
        'story_today':      f'📱 اكتب بوست "اللي حصلي النهارده" عن: {t}\nأسلوب عفوي كأنك تحكي لأصدقائك + حدث طريف أو مفاجئ + سؤال: حصل معاكم؟\nالأسلوب: {p}',
        'story_serial':     f'📖 اكتب جزء من قصة متسلسلة عن: {t}\nابدأ بـ: الجزء الجديد 🔥 + تذكير سريع + أحداث جديدة + نهاية مفتوحة + الجزء القادم غداً\nالأسلوب: {p}',
        # كوميدي
        'meme':             f'😂 اكتب بوست كوميدي ظريف عن: {t}\nنكتة أو موقف مضحك من الحياة اليومية + خفيف وعفوي + اختم بـ: من يشاركني؟ 😂\nالأسلوب: {p}',
        'comedy_sketch':    f'🎭 اكتب موقف كوميدي قصير عن: {t}\nسكتش بأسلوب حوار أو سرد + شخصيات مضحكة + اختم بـ: من عنده موقف أضحك؟ 😂\nالأسلوب: {p}',
        # دراما وتشويق
        'drama_mystery':    f'🌀 اكتب بوست عن غريبة أو عجيبة حقيقية عن: {t}\nابدأ بسؤال مثير + اشرح الظاهرة بأسلوب شيق + اختم بـ: هل تصدق هذا؟ 🤯\nالأسلوب: {p}',
        'truth_or_lie':     f'🎯 اكتب بوست "صح ولا كذب؟" عن: {t}\n3 معلومات واحدة كذب + معلومتان غريبتان حقيقيتان + معلومة كاذبة مقنعة + الإجابة في التعليقات! 👇\nالأسلوب: {p}',
        # وثائقي
        'weird_facts':      f'🌍 اكتب بوست 5 حقائق غريبة ومثيرة عن: {t}\nكل حقيقة تبدأ بـ: هل تعلم أن... + موثوقة ومثيرة + اختم بـ: أيهم أدهشك أكثر؟ 👇\nالأسلوب: {p}',
        'country_culture':  f'🗺️ اكتب بوست عن ثقافة أو بلد مثير عن: {t}\nعادات وتقاليد غريبة + حقائق لا يعرفها الكثيرون + اختم بـ: هل زرت هذا البلد؟ 👇\nالأسلوب: {p}',
        'history_simple':   f'⏳ اكتب بوست تاريخي مبسط وشيق عن: {t}\nحدث تاريخي مثير + شخصيات وأحداث بأسلوب قصصي + اختم بـ: ماذا تعلمت؟ 👇\nالأسلوب: {p}',
        # تحفيزي
        'success_story':    f'🏆 اكتب قصة نجاح حقيقية وملهمة عن: {t}\nبداية صعبة + تحديات + نقطة التحول + النجاح + الدرس + اختم بـ: ما هو حلمك؟ 👇\nالأسلوب: {p}',
        'life_change':      f'✨ اكتب قصة تغيير حياة مؤثرة عن: {t}\nالحياة قبل + اللحظة الفارقة + الحياة بعد + اختم بـ: هل أنت مستعد للتغيير؟ 💪\nالأسلوب: {p}',
        'inspiration_quote': f'💫 اكتب منشور اقتباس ملهم عن: {t}\nاقتباس قوي بارز + شرح وتأمل + كيف نطبقه + سؤال تفاعلي\nالأسلوب: {p}',
        # عام
        'tips':             f'💡 اكتب نصيحة مفيدة عن: {t}\nالأسلوب: {p}',
        'offer':            f'🛍️ اكتب بوست تسويقي جذاب عن: {t}\nالأسلوب: {p}',
        'question':         f'🤔 اكتب سؤالاً تفاعلياً مثيراً عن: {t}\nالأسلوب: {p}',
        'fact':             f'📚 اكتب معلومة مثيرة ومفيدة عن: {t}\nالأسلوب: {p}',
        'motivation':       f'🔥 اكتب منشوراً تحفيزياً قوياً عن: {t}\nالأسلوب: {p}',
        'wisdom':           f'💡 اكتب حكمة لأحد عظماء الأدب العربي (نجيب محفوظ، جبران، المتنبي، الشابي، نزار قباني)\nالحكمة + قائلها + شرحها + تطبيقها + سؤال\nالموضوع: {t}، الأسلوب: {p}',
        'poet_quote':       f'🎭 اكتب بيت شعر من الأدب العربي (المتنبي، نزار، درويش، الشابي، شوقي)\nالبيت + الشاعر + شرحه + رسالته\nالموضوع: {t}، الأسلوب: {p}',
    }
    return prompts.get(post_type, f'اكتب بوست مناسب عن: {t}\nالأسلوب: {p}')

def generate_content(topic, post_type, page_name, page_id='', personality='mixed'):
    settings = load_json(SETTINGS_FILE, {})
    api_key = settings.get('groq_api_key', '')
    if page_id: post_type = get_smart_post_type(page_id, post_type)
    seasonal_ctx = get_seasonal_context()
    now_tz = datetime.now(pytz.timezone('Asia/Riyadh'))
    if post_type not in ['quran_tafseer','duaa','friday','seasonal']:
        if seasonal_ctx and random.random() < 0.25: post_type = 'seasonal'
        elif now_tz.hour in [5,6,7,8] and random.random() < 0.35: post_type = 'adhkar_morning'
        elif now_tz.weekday() == 4 and random.random() < 0.4: post_type = 'friday_khutba'
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
        system_msg = 'أنت كاتب محتوى عربي محترف. اكتب باللغة العربية فقط بدون أي حروف أجنبية. ابدأ مباشرة بالمحتوى. استخدم الإيموجي المناسبة.'
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

@app.route('/api/post_categories', methods=['GET'])
def get_post_categories(): return jsonify(POST_CATEGORIES)

@app.route('/api/category_names', methods=['GET'])
def get_category_names():
    # يرجع الفئات الرئيسية فقط للواجهة
    return jsonify({k: k for k in POST_CATEGORIES.keys()})

@app.route('/api/personalities', methods=['GET'])
def get_personalities(): return jsonify(PAGE_PERSONALITIES)

@app.route('/api/seasonal', methods=['GET'])
def get_seasonal(): return jsonify({'events': get_seasonal_context()})

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
