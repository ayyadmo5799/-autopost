from flask import Flask, render_template, request, jsonify
import anthropic
import requests
import json
import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = '/data'
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
PAGES_FILE = os.path.join(DATA_DIR, 'pages.json')
LOGS_FILE = os.path.join(DATA_DIR, 'logs.json')
STATS_FILE = os.path.join(DATA_DIR, 'stats.json')

os.makedirs(DATA_DIR, exist_ok=True)

scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Riyadh'))

POST_TYPES = {
    'tips': 'نصيحة مفيدة',
    'offer': 'عرض ومنتج مميز',
    'question': 'سؤال تفاعلي',
    'fact': 'معلومة مثيرة',
    'motivation': 'كلمة تحفيزية',
    'religious': 'محتوى ديني إسلامي',
    'video_idea': 'فكرة فيديو ديني'
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
    logs.insert(0, {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'page': page_name,
        'status': status,
        'message': message
    })
    logs = logs[:200]
    save_json(LOGS_FILE, logs)

def update_stats(success=True):
    stats = load_json(STATS_FILE, {'total': 0, 'today': 0, 'errors': 0, 'last_reset': ''})
    today = datetime.now().strftime('%Y-%m-%d')
    if stats.get('last_reset') != today:
        stats['today'] = 0
        stats['last_reset'] = today
    stats['total'] += 1
    if success:
        stats['today'] += 1
    else:
        stats['errors'] += 1
    save_json(STATS_FILE, stats)

def generate_content_with_claude(topic, post_type, page_name):
    settings = load_json(SETTINGS_FILE, {})
    api_key = settings.get('claude_api_key', '')
    if not api_key:
        return generate_fallback_content(topic, post_type)
    try:
        client = anthropic.Anthropic(api_key=api_key)
        type_prompts = {
            'tips': f'اكتب نصيحة مفيدة وعملية عن موضوع: {topic}',
            'offer': f'اكتب بوست جذاب لعرض أو منتج متعلق بـ: {topic}',
            'question': f'اكتب سؤالاً تفاعلياً يشجع المتابعين على التعليق عن موضوع: {topic}',
            'fact': f'اكتب معلومة مثيرة ومفيدة عن موضوع: {topic}',
            'motivation': f'اكتب كلمة تحفيزية ومؤثرة عن موضوع: {topic}',
            'religious': f'اكتب محتوى إسلامي مفيد ومؤثر عن موضوع: {topic}. يمكن أن يكون آية قرآنية مع تفسير، حديث نبوي، أو فائدة دينية.',
            'video_idea': f'اكتب نص بوست يقدم فيديو ديني إسلامي عن موضوع: {topic}.'
        }
        prompt = type_prompts.get(post_type, f'اكتب بوست مناسب عن: {topic}')
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": f"""أنت مدير صفحة فيسبوك عربية محترف. 
{prompt}
متطلبات: باللغة العربية، جذاب، 100-300 كلمة، يحتوي إيموجي، ينتهي بدعوة للتفاعل.
اكتب المنشور مباشرة بدون مقدمة."""}]
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude error: {e}")
        return generate_fallback_content(topic, post_type)

def generate_fallback_content(topic, post_type):
    templates = {
        'tips': f'💡 نصيحة اليوم عن {topic}\n\nشاركنا رأيك في التعليقات! 👇',
        'offer': f'🛍️ عرض مميز في {topic}\n\nاضغط لايك إذا أعجبك! ❤️',
        'question': f'🤔 سؤال اليوم عن {topic}\n\nشاركنا إجابتك! 💬',
        'fact': f'📚 هل تعلم عن {topic}؟\n\nشاركها مع أصدقائك! 🔄',
        'motivation': f'✨ كلمة اليوم عن {topic}\n\nشاركها مع من تحب! ❤️',
        'religious': f'🌙 فائدة إسلامية عن {topic}\n\nاللهم علمنا ما ينفعنا 🤲',
        'video_idea': f'🎥 فيديو جديد عن {topic}\n\nشاركوا مع أحبابكم! 🔄'
    }
    return templates.get(post_type, f'منشور عن {topic} ✨')

def post_to_facebook(page_id, access_token, content):
    try:
        url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
        response = requests.post(url, data={
            'message': content,
            'access_token': access_token
        }, timeout=30)
        result = response.json()
        if 'id' in result:
            return True, result['id']
        else:
            error_msg = result.get('error', {}).get('message', 'خطأ غير معروف')
            return False, error_msg
    except Exception as e:
        return False, str(e)

def publish_scheduled_post(page_id_str, schedule_id):
    pages = load_json(PAGES_FILE, [])
    page = next((p for p in pages if p['id'] == page_id_str), None)
    if not page or not page.get('active', True):
        return
    schedule = next((s for s in page.get('schedules', []) if s['id'] == schedule_id), None)
    if not schedule:
        return
    post_type = schedule.get('post_type', 'tips')
    topic = page.get('topic', 'عام')
    content = generate_content_with_claude(topic, post_type, page['name'])
    success, result = post_to_facebook(page['page_id'], page['access_token'], content)
    type_name = POST_TYPES.get(post_type, post_type)
    message = f"✅ نُشر ({type_name}): {content[:50]}..." if success else f"❌ فشل: {result}"
    add_log(page['name'], 'success' if success else 'error', message)
    update_stats(success)

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
                scheduler.add_job(
                    publish_scheduled_post,
                    CronTrigger(hour=h, minute=m, timezone=tz),
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
    safe = {k: v for k, v in settings.items() if k != 'claude_api_key'}
    safe['has_api_key'] = bool(settings.get('claude_api_key'))
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
        data['schedules'] = [{'id': f"s_{datetime.now().strftime('%f')}", 'time': data.get('post_time', '09:00'), 'post_type': data.get('post_type', 'tips')}]
    data['id'] = f"page_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    data['active'] = True
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
    content = generate_content_with_claude(page.get('topic', 'عام'), post_type, page['name'])
    success, result = post_to_facebook(page['page_id'], page['access_token'], content)
    type_name = POST_TYPES.get(post_type, post_type)
    message = f"✅ نُشر يدوياً ({type_name}): {content[:50]}..." if success else f"❌ فشل: {result}"
    add_log(page['name'], 'success' if success else 'error', message)
    update_stats(success)
    return jsonify({'success': success, 'result': result, 'content': content})

@app.route('/api/publish/all', methods=['POST'])
def publish_all():
    pages = load_json(PAGES_FILE, [])
    results = []
    for page in pages:
        if not page.get('active', True):
            continue
        post_type = page.get('schedules', [{'post_type': 'tips'}])[0].get('post_type', 'tips')
        content = generate_content_with_claude(page.get('topic', 'عام'), post_type, page['name'])
        success, result = post_to_facebook(page['page_id'], page['access_token'], content)
        add_log(page['name'], 'success' if success else 'error', f"{'✅' if success else '❌'} {content[:50]}...")
        update_stats(success)
        results.append({'page': page['name'], 'success': success})
    return jsonify({'success': True, 'results': results})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify(load_json(LOGS_FILE, []))

@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = load_json(STATS_FILE, {'total': 0, 'today': 0, 'errors': 0})
    pages = load_json(PAGES_FILE, [])
    stats['pages'] = len(pages)
    stats['active_pages'] = sum(1 for p in pages if p.get('active', True))
    stats['total_schedules'] = sum(len(p.get('schedules', [])) for p in pages)
    return jsonify(stats)

@app.route('/api/post_types', methods=['GET'])
def get_post_types():
    return jsonify(POST_TYPES)

@app.route('/api/test_token', methods=['POST'])
def test_token():
    data = request.json
    try:
        url = f"https://graph.facebook.com/v19.0/{data['page_id']}?fields=name,id&access_token={data['access_token']}"
        r = requests.get(url, timeout=10)
        result = r.json()
        if 'name' in result:
            return jsonify({'success': True, 'name': result['name']})
        return jsonify({'success': False, 'error': result.get('error', {}).get('message', 'خطأ')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if not scheduler.running:
    scheduler.start()
setup_scheduler()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
