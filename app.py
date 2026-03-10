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
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
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
UNSPLASH_KEY = 'gZrefpx0NIcCATHYfGXq873vRehUuDMWEdZw0JH-rOY'

# كلمات البحث - طبيعة فقط بدون أشخاص
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
    'default':      ['flowers nature beautiful','sky clouds peaceful','garden colorful bloom']
}

# كلمات محظورة لتجنب صور الأشخاص
UNSPLASH_EXCLUDE = 'people,person,man,woman,girl,boy,human,face,portrait,crowd'
CALENDAR_FILE = os.path.join(DATA_DIR, 'content_calendar.json')
WEEKLY_FILE = os.path.join(DATA_DIR, 'weekly_stats.json')

os.makedirs(DATA_DIR, exist_ok=True)
scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Riyadh'))

POST_TYPES = {
    'tips': 'نصيحة مفيدة',
    'offer': 'عرض ومنتج مميز',
    'question': 'سؤال تفاعلي',
    'fact': 'معلومة مثيرة',
    'motivation': 'كلمة تحفيزية',
    'quran': 'آية قرآنية وتفسير',
    'quran_tafseer': 'تفسير القرآن بالترتيب',
    'prophet_story': 'قصة نبي',
    'sahabi_story': 'قصة صحابي',
    'islamic_fact': 'معلومة إسلامية',
    'hadith': 'حديث نبوي شريف',
    'duaa': 'دعاء اليوم',
    'friday': 'بوست الجمعة',
    'seasonal': 'محتوى موسمي',
    'video_idea': 'محتوى فيديو',
    'wisdom': 'حكمة وقول مأثور',
    'poet_quote': 'بيت شعر وتأمل'
}

PAGE_PERSONALITIES = {
    'spiritual': 'روحاني هادئ - يركز على التأمل والقرآن والدعاء',
    'motivational': 'تحفيزي قوي - يشجع ويحفز ويبث الطاقة',
    'educational': 'علمي تعليمي - يقدم المعلومات بأسلوب منظم',
    'friendly': 'ودي مرح - أسلوب خفيف ومحبب',
    'commercial': 'تجاري احترافي - يسوق ويقنع بذكاء',
    'mixed': 'متنوع - يمزج بين كل الأساليب'
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
    'quran': ['#القرآن_الكريم','#تفسير_القرآن','#آيات_قرآنية','#نور_القرآن','#ختمة_قرآنية','#كلام_الله'],
    'hadith': ['#حديث_نبوي','#السنة_النبوية','#نبينا_محمد','#اللهم_صل_على_محمد','#الحديث_الشريف'],
    'motivation': ['#تحفيز','#تطوير_الذات','#نجاح','#إيجابية','#همة','#اقتبسات','#تحفيزية'],
    'tips': ['#نصائح','#فائدة_اليوم','#معلومة','#تعلم_كل_يوم','#نصيحة_اليوم'],
    'offer': ['#عروض','#تسوق','#خصومات','#منتجات_مميزة','#عروض_حصرية'],
    'general': ['#عربي','#محتوى_عربي','#يومياتي'],
    'wisdom': ['#حكمة','#اقتباسات','#توعية','#ثقافة','#أدب_عربي','#فلسفة','#تأمل','#نجيب_محفوظ']
}

DAYS_AR = {
    'mon': 'الإثنين','tue': 'الثلاثاء','wed': 'الأربعاء',
    'thu': 'الخميس','fri': 'الجمعة','sat': 'السبت','sun': 'الأحد'
}

def load_json(filepath, default):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
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
            stats.setdefault('by_type', {})[post_type] = stats.get('by_type', {}).get(post_type, 0) + 1
    else:
        stats['errors'] = stats.get('errors', 0) + 1
    save_json(STATS_FILE, stats)

def update_weekly_stats(page_name, post_type, success):
    week = datetime.now().strftime('%Y-W%W')
    stats = load_json(WEEKLY_FILE, {})
    if week not in stats:
        stats[week] = {'total':0,'success':0,'by_page':{},'by_type':{}}
    stats[week]['total'] += 1
    if success:
        stats[week]['success'] += 1
    stats[week]['by_page'][page_name] = stats[week]['by_page'].get(page_name, 0) + 1
    stats[week]['by_type'][post_type] = stats[week]['by_type'].get(post_type, 0) + 1
    save_json(WEEKLY_FILE, stats)

def get_seasonal_context():
    now = datetime.now(pytz.timezone('Asia/Riyadh'))
    month, day, weekday = now.month, now.day, now.weekday()
    contexts = []
    if weekday == 4:
        contexts.append('يوم الجمعة المبارك')
    if month in [3, 4]:
        contexts.append('شهر رمضان المبارك')
    if month == 4 and day <= 10:
        contexts.append('عيد الفطر المبارك')
    if month in [6, 7] and day <= 15:
        contexts.append('موسم الحج وعيد الأضحى')
    if month == 3 and day >= 20:
        contexts.append('العشر الأواخر من رمضان')
    if month == 7:
        contexts.append('شهر محرم والسنة الهجرية الجديدة')
    if month == 9 and day <= 20:
        contexts.append('ذكرى المولد النبوي الشريف')
    return contexts

def get_smart_post_type(page_id, requested_type):
    if requested_type in ['quran_tafseer','duaa','friday','seasonal']:
        return requested_type
    calendar = load_json(CALENDAR_FILE, {})
    history = calendar.get(page_id, [])
    last_3 = history[-3:] if len(history) >= 3 else history
    if requested_type in last_3:
        all_types = [t for t in POST_TYPES.keys() if t not in ['quran_tafseer','duaa','friday','seasonal']]
        available = [t for t in all_types if t not in last_3]
        if available:
            return random.choice(available)
    return requested_type

def record_post_type(page_id, post_type):
    calendar = load_json(CALENDAR_FILE, {})
    if page_id not in calendar:
        calendar[page_id] = []
    calendar[page_id].append(post_type)
    calendar[page_id] = calendar[page_id][-20:]
    save_json(CALENDAR_FILE, calendar)

def get_quran_progress():
    return load_json(QURAN_FILE, {'surah':1,'ayah':1})

def save_quran_progress(surah, ayah):
    save_json(QURAN_FILE, {'surah':surah,'ayah':ayah})

def get_next_ayah():
    progress = get_quran_progress()
    s, a = progress['surah'], progress['ayah']
    surah_info = next((x for x in QURAN_SURAHS if x[0]==s), QURAN_SURAHS[0])
    max_ayah = surah_info[2]
    next_a = a + 1
    next_s = s
    if next_a > max_ayah:
        next_a = 1
        next_s = s + 1
        if next_s > 114:
            next_s = 1
    save_quran_progress(next_s, next_a)
    return s, a, surah_info[1]

def get_hashtags(post_type, topic=''):
    tags = []
    if post_type in ['quran','quran_tafseer']:
        tags = random.sample(HASHTAGS['quran'], 4) + random.sample(HASHTAGS['islamic'], 2)
    elif post_type == 'hadith':
        tags = HASHTAGS['hadith'][:3] + random.sample(HASHTAGS['islamic'], 2)
    elif post_type in ['prophet_story','sahabi_story','islamic_fact','duaa','friday','seasonal']:
        tags = random.sample(HASHTAGS['islamic'], 5)
    elif post_type in ['wisdom','poet_quote']:
        tags = random.sample(HASHTAGS['wisdom'], 5)
    elif post_type == 'motivation':
        tags = random.sample(HASHTAGS['motivation'], 4)
    elif post_type == 'offer':
        tags = random.sample(HASHTAGS['offer'], 3) + random.sample(HASHTAGS['general'], 1)
    else:
        tags = random.sample(HASHTAGS['tips'], 3) + random.sample(HASHTAGS['general'], 1)
    return ' '.join(tags)

def get_prompt_for_type(post_type, topic, personality='mixed', seasonal_ctx=None):
    pname = PAGE_PERSONALITIES.get(personality, PAGE_PERSONALITIES['mixed'])
    if post_type == 'quran_tafseer':
        s, a, sname = get_next_ayah()
        return f'''اكتب منشور فيسبوك إسلامي متكامل عن الآية رقم {a} من سورة {sname} (السورة رقم {s}).
المنشور يحتوي على:
📖 عنوان: تفسير سورة {sname} - الآية {a}
- نص الآية الكريمة كاملاً بالرسم العثماني
- تفسير الآية بأسلوب واضح وبسيط ومؤثر
- الفوائد والدروس المستفادة
- دعاء مناسب في الختام
اكتب كل شيء باللغة العربية فقط.'''
    if post_type == 'duaa':
        return f'''اكتب منشور دعاء الصباح لصفحة فيسبوك إسلامية.
يحتوي على:
🤲 عنوان: دعاء الصباح
- دعاء مأثور من القرآن أو السنة النبوية
- شرح مختصر لمعنى الدعاء
- تشجيع المتابعين على قوله كل صباح
الأسلوب: {pname}'''
    if post_type == 'friday':
        return f'''اكتب منشور ليوم الجمعة المبارك.
يحتوي على:
🕌 تهنئة بيوم الجمعة
- آية أو حديث عن فضل يوم الجمعة
- تذكير بسنن الجمعة
- دعاء خاص بيوم الجمعة
الأسلوب: {pname}'''
    if post_type == 'seasonal' and seasonal_ctx:
        ctx = random.choice(seasonal_ctx)
        return f'''اكتب منشور فيسبوك خاص بـ: {ctx}
الموضوع: {topic}
الأسلوب: {pname}
اجعله مناسباً للمناسبة ومؤثراً وفيه فائدة دينية.'''
    prompts = {
        'tips': f'اكتب نصيحة مفيدة وعملية عن موضوع: {topic}\nالأسلوب: {pname}',
        'offer': f'اكتب بوست تسويقي جذاب لعرض أو منتج عن: {topic}\nالأسلوب: {pname}',
        'question': f'اكتب سؤالاً تفاعلياً ذكياً يشجع التعليق عن موضوع: {topic}\nالأسلوب: {pname}',
        'fact': f'اكتب معلومة مثيرة ومفاجئة عن موضوع: {topic}\nالأسلوب: {pname}',
        'motivation': f'اكتب منشوراً تحفيزياً قوياً عن: {topic}. استخدم آيات وأحاديث.\nالأسلوب: {pname}',
        'quran': f'''اختر آية قرآنية عشوائية مناسبة لموضوع: {topic}
اكتب: الآية كاملة مع رقمها والسورة، تفسيرها، الدروس المستفادة.
الأسلوب: {pname}''',
        'prophet_story': f'''اكتب قصة مؤثرة من قصص الأنبياء عليهم السلام مناسبة لـ: {topic}
اذكر: اسم النبي، الموقف، الدرس المستفاد، آية في الختام.
الأسلوب: {pname}''',
        'sahabi_story': f'''اكتب قصة مؤثرة من قصص الصحابة مناسبة لـ: {topic}
اذكر: اسم الصحابي، الموقف البطولي، الدرس المستفاد.
الأسلوب: {pname}''',
        'islamic_fact': f'''اكتب معلومة إسلامية مثيرة عن موضوع: {topic}
مثل: الإعجاز العلمي في القرآن، أسرار العبادات، أسماء الله الحسنى.
الأسلوب: {pname}''',
        'hadith': f'''اذكر حديثاً نبوياً صحيحاً مناسباً لـ: {topic}
اكتب: الحديث كاملاً مع راويه، شرحه، كيف نطبقه في حياتنا.
الأسلوب: {pname}''',
        'video_idea': f'اكتب نص بوست جذاب يقدم فيديو عن: {topic}.\nالأسلوب: {pname}',
        'wisdom': f'''اكتب منشور فيسبوك عن حكمة أو قول مأثور لأحد عظماء الأدب العربي.
اختر عشوائياً من: نجيب محفوظ، جبران خليل جبران، مصطفى صادق الرافعي، العقاد، طه حسين، المتنبي، أبو القاسم الشابي، إيليا أبو ماضي، ميخائيل نعيمة، أحمد شوقي.
اكتب:
💡 اقتبس الحكمة أو القول كاملاً مع اسم قائله
- شرح معنى الحكمة بأسلوب بسيط ومعاصر
- كيف نطبق هذه الحكمة في حياتنا اليوم
- سؤال تفاعلي في الختام يدعو للتأمل
الموضوع: {topic}، الأسلوب: {pname}''',
        'poet_quote': f'''اكتب منشور فيسبوك عن بيت شعر أو مقطع شعري من الأدب العربي.
اختر عشوائياً من: المتنبي، أبو تمام، أبو نواس، أحمد شوقي، نزار قباني، محمود درويش، أبو القاسم الشابي، إيليا أبو ماضي.
اكتب:
🎭 البيت أو المقطع الشعري كاملاً مع اسم الشاعر
- شرح معنى البيت بأسلوب بسيط وجميل
- الرسالة التي أراد الشاعر إيصالها
- كيف يرتبط بحياتنا اليومية
الموضوع: {topic}، الأسلوب: {pname}'''
    }
    return prompts.get(post_type, f'اكتب بوست مناسب عن: {topic}\nالأسلوب: {pname}')

def generate_content(topic, post_type, page_name, page_id='', personality='mixed'):
    settings = load_json(SETTINGS_FILE, {})
    api_key = settings.get('groq_api_key', '')

    if page_id:
        post_type = get_smart_post_type(page_id, post_type)

    seasonal_ctx = get_seasonal_context()
    now_tz = datetime.now(pytz.timezone('Asia/Riyadh'))

    if post_type not in ['quran_tafseer','duaa','friday','seasonal']:
        if seasonal_ctx and random.random() < 0.25:
            post_type = 'seasonal'
        elif now_tz.hour in [5,6,7,8] and random.random() < 0.35:
            post_type = 'duaa'
        elif now_tz.weekday() == 4 and random.random() < 0.4:
            post_type = 'friday'

    if not api_key:
        return generate_fallback_content(topic, post_type), post_type

    try:
        angles = [
            'بأسلوب قصصي شيق',
            'بطريقة مباشرة وعملية',
            'بأسلوب يثير الفضول',
            'بطريقة عاطفية ومؤثرة',
            'بأسلوب الخبير المتخصص',
            'بطريقة خفيفة وممتعة',
            'بأسلوب الحوار والتساؤلات',
            'بطريقة تربط الماضي بالحاضر'
        ]
        angle = random.choice(angles)
        seed = datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(1000,9999))
        prompt_text = get_prompt_for_type(post_type, topic, personality, seasonal_ctx)
        hashtags = get_hashtags(post_type, topic)

        system_prompt = """أنت كاتب محتوى عربي محترف متخصص في صفحات فيسبوك.
قواعد صارمة لا يمكن تجاهلها:
1. اكتب باللغة العربية فقط - ممنوع منعاً باتاً أي كلمة أجنبية
2. ممنوع كتابة أي حرف لاتيني في أي مكان في المنشور
3. حتى الأرقام اكتبها بالعربية مثل: ١، ٢، ٣ أو باللفظ
4. ابدأ مباشرة بالمحتوى بدون مقدمة
5. استخدم الإيموجي المناسبة بشكل طبيعي
6. اختم بدعوة للتفاعل"""

        full_prompt = f"""اكتب منشور فيسبوك عربي مميز ومتكامل.
{prompt_text}
الأسلوب: {angle}
رقم التنويع: {seed}
الطول: بين ١٥٠ و ٣٠٠ كلمة
أضف في نهاية المنشور هذه الهاشتاقات:
{hashtags}"""

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            "max_tokens": 800,
            "temperature": 0.85
        }
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        data = r.json()
        logger.info(f"Groq status: {r.status_code}")
        if 'choices' in data and data['choices']:
            content = data['choices'][0]['message']['content']
            if page_id:
                record_post_type(page_id, post_type)
            return content, post_type
        elif 'error' in data:
            logger.error(f"Groq error: {data['error'].get('message','unknown')}")
            return generate_fallback_content(topic, post_type), post_type
        else:
            return generate_fallback_content(topic, post_type), post_type
    except Exception as e:
        logger.error(f"Generate error: {e}")
        return generate_fallback_content(topic, post_type), post_type

def generate_fallback_content(topic, post_type):
    t = {
        'tips': f'💡 نصيحة اليوم\n\nشاركنا رأيك! 👇\n#نصائح #فائدة_اليوم',
        'offer': f'🛍️ عرض مميز\n\n#عروض #تسوق',
        'question': f'🤔 سؤال اليوم\n\nشاركنا! 💬',
        'fact': f'📚 هل تعلم؟\n\n#معلومة',
        'motivation': f'✨ لا تستسلم!\n\n#تحفيز',
        'quran': f'🌟 آية كريمة\n\n#القرآن_الكريم',
        'quran_tafseer': f'📖 تفسير من كتاب الله\n\n#تفسير_القرآن',
        'prophet_story': f'🕌 من قصص الأنبياء\n\n#إسلاميات',
        'sahabi_story': f'⭐ من قصص الصحابة\n\n#إسلاميات',
        'islamic_fact': f'📖 معلومة إسلامية\n\n#إسلاميات',
        'hadith': f'🌹 حديث شريف\n\n#حديث_نبوي',
        'duaa': f'🤲 دعاء الصباح\n\nآمين يارب\n#دعاء',
        'friday': f'🕌 جمعة مباركة\n\n#الجمعة',
        'seasonal': f'✨ مناسبة مباركة\n\n#إسلاميات',
        'video_idea': f'🎥 محتوى جديد\n\nشاركوا! 🔄',
        'wisdom': f'💡 حكمة اليوم\n\nشاركها مع من تحب! ❤️\n#حكمة #اقتباسات',
        'poet_quote': f'🎭 بيت شعر\n\nشاركها! 🔄\n#أدب_عربي #شعر'
    }
    return t.get(post_type, f'منشور عن {topic} ✨')

def fetch_unsplash_image(post_type):
    """جلب صورة طبيعية من Unsplash بدون أشخاص"""
    try:
        queries = IMAGE_QUERIES.get(post_type, IMAGE_QUERIES['default'])
        # جرب أكثر من مرة للتأكد من عدم وجود أشخاص
        for attempt in range(3):
            query = random.choice(queries)
            r = requests.get(
                'https://api.unsplash.com/photos/random',
                params={
                    'query': query,
                    'orientation': 'squarish',
                    'content_filter': 'high',
                    'topics': 'nature,flowers,textures-patterns',
                },
                headers={'Authorization': f'Client-ID {UNSPLASH_KEY}'},
                timeout=15
            )
            if r.status_code == 200:
                data = r.json()
                # تحقق من وصف الصورة - تجنب الصور التي تحتوي على أشخاص
                desc = (data.get('description') or data.get('alt_description') or '').lower()
                tags = [t.get('title','').lower() for t in data.get('tags', [])]
                has_people = any(w in desc or any(w in t for t in tags)
                    for w in ['person','people','man','woman','girl','boy','human','face','portrait'])
                if has_people:
                    logger.info(f"Skipped image with people, retrying...")
                    continue
                img_url = data['urls']['regular']
                img_r = requests.get(img_url, timeout=20)
                if img_r.status_code == 200:
                    return Image.open(BytesIO(img_r.content)).convert('RGB')
    except Exception as e:
        logger.error(f"Unsplash error: {e}")
    return None

def create_post_image(text, post_type):
    """إنشاء صورة نظيفة بدون كتابة - الكتابة تكون في النص المرفق"""
    if not PIL_AVAILABLE:
        return None
    try:
        SIZE = (1080, 1080)
        img = fetch_unsplash_image(post_type)
        if img:
            # صورة طبيعية نظيفة بدون أي تعديل
            img = img.resize(SIZE, Image.LANCZOS)
        else:
            # خلفية طبيعية بتدرج لوني جميل كاحتياط
            img = Image.new('RGB', SIZE)
            nature_colors = [
                [(20,83,45),(5,150,105)],    # أخضر طبيعة
                [(12,74,110),(3,105,161)],   # أزرق سماء
                [(124,45,18),(180,83,9)],    # برتقالي غروب
                [(76,29,149),(107,33,168)],  # بنفسجي غسق
                [(6,78,59),(4,120,87)],      # أخضر غابة
            ]
            c = random.choice(nature_colors)
            draw_bg = ImageDraw.Draw(img)
            for y in range(SIZE[1]):
                t = y / SIZE[1]
                r2 = int(c[0][0]*(1-t) + c[1][0]*t)
                g2 = int(c[0][1]*(1-t) + c[1][1]*t)
                b2 = int(c[0][2]*(1-t) + c[1][2]*t)
                draw_bg.line([(0,y),(SIZE[0],y)], fill=(r2,g2,b2))

        # حفظ الصورة نظيفة بدون كتابة
        output = BytesIO()
        img.save(output, format='JPEG', quality=95)
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Image creation error: {e}")
        return None

def post_image_to_facebook(page_id, access_token, content, post_type):
    """نشر صورة مع نص على فيسبوك"""
    try:
        img_data = create_post_image(content[:200], post_type)
        if img_data:
            url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
            r = requests.post(url, data={
                'caption': content,
                'access_token': access_token
            }, files={'source': ('image.jpg', img_data, 'image/jpeg')}, timeout=60)
            result = r.json()
            if 'id' in result or 'post_id' in result:
                return True, result.get('post_id', result.get('id',''))
            logger.error(f"Photo post error: {result}")
        # fallback: نشر نص فقط
        return post_to_facebook(page_id, access_token, content)
    except Exception as e:
        logger.error(f"Image post error: {e}")
        return post_to_facebook(page_id, access_token, content)

def post_to_facebook(page_id, access_token, content):
    try:
        url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
        r = requests.post(url, data={'message': content, 'access_token': access_token}, timeout=30)
        result = r.json()
        if 'id' in result:
            return True, result['id']
        return False, result.get('error', {}).get('message', 'خطأ غير معروف')
    except Exception as e:
        return False, str(e)

def should_post_today(schedule):
    days = schedule.get('days', ['mon','tue','wed','thu','fri','sat','sun'])
    if not days:
        return True
    day_map = {'mon':0,'tue':1,'wed':2,'thu':3,'fri':4,'sat':5,'sun':6}
    today = datetime.now(pytz.timezone('Asia/Riyadh')).weekday()
    return any(day_map.get(d) == today for d in days)

def publish_scheduled_post(page_id_str, schedule_id):
    pages = load_json(PAGES_FILE, [])
    page = next((p for p in pages if p['id'] == page_id_str), None)
    if not page or not page.get('active', True):
        return
    schedule = next((s for s in page.get('schedules', []) if s['id'] == schedule_id), None)
    if not schedule:
        return
    if not should_post_today(schedule):
        return
    post_type = schedule.get('post_type', 'tips')
    personality = page.get('personality', 'mixed')
    content, actual_type = generate_content(page.get('topic','عام'), post_type, page['name'], page['id'], personality)
    use_image = page.get('use_image', True)
    if use_image:
        success, result = post_image_to_facebook(page['page_id'], page['access_token'], content, actual_type)
    else:
        success, result = post_to_facebook(page['page_id'], page['access_token'], content)
    type_name = POST_TYPES.get(actual_type, actual_type)
    mode = '🖼️' if use_image else '📝'
    message = f"✅ {mode} نُشر ({type_name}): {content[:60]}..." if success else f"❌ فشل: {result}"
    add_log(page['name'], 'success' if success else 'error', message)
    update_stats(success, actual_type)
    update_weekly_stats(page['name'], actual_type, success)

def setup_scheduler():
    scheduler.remove_all_jobs()
    pages = load_json(PAGES_FILE, [])
    tz = pytz.timezone('Asia/Riyadh')
    for page in pages:
        if not page.get('active', True):
            continue
        for schedule in page.get('schedules', []):
            try:
                h, m = map(int, schedule['time'].split(':'))
                days = schedule.get('days', [])
                dow = ','.join(days) if days else 'mon,tue,wed,thu,fri,sat,sun'
                scheduler.add_job(
                    publish_scheduled_post,
                    CronTrigger(hour=h, minute=m, day_of_week=dow, timezone=tz),
                    args=[page['id'], schedule['id']],
                    id=f"{page['id']}_{schedule['id']}",
                    replace_existing=True
                )
            except Exception as e:
                logger.error(f"Schedule error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    settings = load_json(SETTINGS_FILE, {})
    safe = {k: v for k, v in settings.items() if k != 'groq_api_key'}
    safe['has_api_key'] = bool(settings.get('groq_api_key'))
    return jsonify(safe)

@app.route('/api/settings', methods=['POST'])
def save_settings():
    settings = load_json(SETTINGS_FILE, {})
    settings.update(request.json)
    save_json(SETTINGS_FILE, settings)
    return jsonify({'success': True})

@app.route('/api/pages', methods=['GET'])
def get_pages():
    return jsonify(load_json(PAGES_FILE, []))

@app.route('/api/pages', methods=['POST'])
def add_page():
    data = request.json
    pages = load_json(PAGES_FILE, [])
    if not data.get('schedules'):
        data['schedules'] = [{'id': f"s_{datetime.now().strftime('%f')}", 'time':'09:00','post_type':'tips','days':['mon','tue','wed','thu','fri','sat','sun']}]
    data['id'] = f"page_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    data['active'] = True
    data.setdefault('personality', 'mixed')
    data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pages.append(data)
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True, 'id': data['id']})

@app.route('/api/pages/<page_id>', methods=['PUT'])
def update_page(page_id):
    pages = load_json(PAGES_FILE, [])
    for i, p in enumerate(pages):
        if p['id'] == page_id:
            pages[i].update(request.json)
            break
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True})

@app.route('/api/pages/<page_id>', methods=['DELETE'])
def delete_page(page_id):
    pages = [p for p in load_json(PAGES_FILE, []) if p['id'] != page_id]
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True})

@app.route('/api/pages/<page_id>/schedules', methods=['POST'])
def add_schedule(page_id):
    data = request.json
    pages = load_json(PAGES_FILE, [])
    for page in pages:
        if page['id'] == page_id:
            if 'schedules' not in page:
                page['schedules'] = []
            data['id'] = f"s_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            if 'days' not in data:
                data['days'] = ['mon','tue','wed','thu','fri','sat','sun']
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
            page['schedules'] = [s for s in page.get('schedules', []) if s['id'] != schedule_id]
            break
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True})

@app.route('/api/publish/page/<page_id>', methods=['POST'])
def publish_page(page_id):
    data = request.json or {}
    pages = load_json(PAGES_FILE, [])
    page = next((p for p in pages if p['id'] == page_id), None)
    if not page:
        return jsonify({'success': False, 'error': 'الصفحة غير موجودة'})
    post_type = data.get('post_type', 'tips')
    personality = page.get('personality', 'mixed')
    content, actual_type = generate_content(page.get('topic','عام'), post_type, page['name'], page_id, personality)
    use_image = data.get('use_image', page.get('use_image', True))
    if use_image:
        success, result = post_image_to_facebook(page['page_id'], page['access_token'], content, actual_type)
    else:
        success, result = post_to_facebook(page['page_id'], page['access_token'], content)
    type_name = POST_TYPES.get(actual_type, actual_type)
    mode = '🖼️' if use_image else '📝'
    add_log(page['name'], 'success' if success else 'error', f"{'✅' if success else '❌'} {mode} ({type_name}): {content[:60]}...")
    update_stats(success, actual_type)
    update_weekly_stats(page['name'], actual_type, success)
    return jsonify({'success': success, 'result': result, 'content': content, 'type': actual_type})

@app.route('/api/publish/all', methods=['POST'])
def publish_all():
    pages = load_json(PAGES_FILE, [])
    results = []
    for page in pages:
        if not page.get('active', True):
            continue
        post_type = page.get('schedules', [{'post_type':'tips'}])[0].get('post_type','tips')
        personality = page.get('personality', 'mixed')
        content, actual_type = generate_content(page.get('topic','عام'), post_type, page['name'], page['id'], personality)
        success, result = post_to_facebook(page['page_id'], page['access_token'], content)
        add_log(page['name'], 'success' if success else 'error', f"{'✅' if success else '❌'} {content[:60]}...")
        update_stats(success, actual_type)
        results.append({'page': page['name'], 'success': success})
    return jsonify({'success': True, 'results': results})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify(load_json(LOGS_FILE, []))

@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = load_json(STATS_FILE, {'total':0,'today':0,'errors':0})
    pages = load_json(PAGES_FILE, [])
    stats['pages'] = len(pages)
    stats['active_pages'] = sum(1 for p in pages if p.get('active', True))
    stats['total_schedules'] = sum(len(p.get('schedules', [])) for p in pages)
    return jsonify(stats)

@app.route('/api/weekly_report', methods=['GET'])
def weekly_report():
    week = datetime.now().strftime('%Y-W%W')
    prev_week = (datetime.now() - timedelta(weeks=1)).strftime('%Y-W%W')
    weekly = load_json(WEEKLY_FILE, {})
    current = weekly.get(week, {'total':0,'success':0,'by_page':{},'by_type':{}})
    previous = weekly.get(prev_week, {'total':0,'success':0,'by_page':{},'by_type':{}})
    by_type = current.get('by_type', {})
    best_type = max(by_type, key=by_type.get) if by_type else ''
    by_page = current.get('by_page', {})
    best_page = max(by_page, key=by_page.get) if by_page else ''
    return jsonify({
        'week': week,
        'current': current,
        'previous': previous,
        'best_type': POST_TYPES.get(best_type, best_type),
        'best_page': best_page,
        'seasonal_events': get_seasonal_context(),
        'total_types': {POST_TYPES.get(k,k): v for k,v in by_type.items()}
    })

@app.route('/api/post_types', methods=['GET'])
def get_post_types():
    return jsonify(POST_TYPES)

@app.route('/api/personalities', methods=['GET'])
def get_personalities():
    return jsonify(PAGE_PERSONALITIES)

@app.route('/api/seasonal', methods=['GET'])
def get_seasonal():
    return jsonify({'events': get_seasonal_context()})

@app.route('/token-generator')
def token_generator():
    return render_template('token-generator.html')

@app.route('/api/get_page_tokens', methods=['POST'])
def get_page_tokens():
    data = request.json
    app_id = data.get('app_id','')
    app_secret = data.get('app_secret','')
    user_token = data.get('user_token','')
    if not app_id or not app_secret or not user_token:
        return jsonify({'success': False, 'error': 'أدخل جميع البيانات'})
    try:
        # Step 1: Get long-lived token
        r1 = requests.get(
            f"https://graph.facebook.com/oauth/access_token",
            params={'grant_type':'fb_exchange_token','client_id':app_id,'client_secret':app_secret,'fb_exchange_token':user_token},
            timeout=15
        )
        d1 = r1.json()
        if 'error' in d1:
            return jsonify({'success': False, 'error': d1['error'].get('message','خطأ في التوكن')})
        long_token = d1['access_token']
        # Step 2: Get page tokens
        r2 = requests.get(
            f"https://graph.facebook.com/v19.0/me/accounts",
            params={'access_token': long_token},
            timeout=15
        )
        d2 = r2.json()
        if 'error' in d2:
            return jsonify({'success': False, 'error': d2['error'].get('message','خطأ في جلب الصفحات')})
        pages = d2.get('data', [])
        if not pages:
            return jsonify({'success': False, 'error': 'لا توجد صفحات مرتبطة بهذا الحساب'})
        return jsonify({'success': True, 'pages': [{'name':p['name'],'id':p['id'],'token':p['access_token']} for p in pages]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test_token', methods=['POST'])
def test_token():
    data = request.json
    try:
        url = f"https://graph.facebook.com/v19.0/me?access_token={data['access_token']}"
        r = requests.get(url, timeout=10)
        result = r.json()
        if 'id' in result:
            return jsonify({'success': True, 'name': result.get('name','الصفحة')})
        return jsonify({'success': False, 'error': result.get('error',{}).get('message','خطأ')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/quran_progress', methods=['GET'])
def get_quran_progress_api():
    p = get_quran_progress()
    surah_info = next((x for x in QURAN_SURAHS if x[0]==p['surah']), QURAN_SURAHS[0])
    total_ayahs = sum(s[2] for s in QURAN_SURAHS)
    done_ayahs = sum(s[2] for s in QURAN_SURAHS if s[0] < p['surah']) + p['ayah']
    return jsonify({
        'surah': p['surah'],
        'surah_name': surah_info[1],
        'ayah': p['ayah'],
        'total_surah_ayahs': surah_info[2],
        'progress_percent': round((done_ayahs/total_ayahs)*100, 2),
        'done_ayahs': done_ayahs,
        'total_ayahs': total_ayahs
    })

if not scheduler.running:
    scheduler.start()
setup_scheduler()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
