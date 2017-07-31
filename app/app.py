import datetime
import functools
import json
import os
import random
import string

from flask import (
        Flask, flash, redirect, render_template, Response, request, session,
        url_for, send_file
)
from peewee import (
        CharField, DateTimeField, TextField, ForeignKeyField
)
from playhouse.flask_utils import FlaskDB, get_object_or_404, object_list


ADMIN_PASSWORD = 'Panasonic'
APP_DIR = os.path.dirname(os.path.realpath(__file__))
DATABASE = 'sqlite:///{}'.format(os.path.join(APP_DIR, 'logger.db'))
DEBUG = False
SECRET_KEY = 'Secret_Key_Logger'
UPLOAD_DIR = os.path.join(APP_DIR, 'uploads/')
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
SITE_NAME = 'Imges'

IMG_ID_LEN = 8
DELETE_ID_LEN = 12


app = Flask(__name__)
app.config.from_object(__name__)

flask_db = FlaskDB(app)
database = flask_db.database


''' Helper Functions '''


def rand_str(length):
    return ''.join([
        random.choice(string.ascii_letters + string.digits) for __ in range(length)
    ])


''' Database Models '''


class JSONField(TextField):
    """ Store JSON date in a TextField """
    def python_value(self, value):
        if value is not None:
            return json.loads(value)

    def db_value(self, value):
        if value is not None:
            return json.dumps(value)


class Image(flask_db.Model):
    img_id = CharField(unique=True)
    delete_id = CharField(unique=True)
    ext = CharField()
    keyword = CharField(default='', index=True)
    timestamp = DateTimeField(default=datetime.datetime.now, index=True)

    class Meta:
        database = database

    def raw(self):
        return send_file(
                os.path.join(app.config['UPLOAD_DIR'],
                             '{}.{}'.format(self.img_id, self.ext)))

    @classmethod
    def gen_id(cls, id_type, length=app.config['IMG_ID_LEN']):
        rand = rand_str(length)
        if id_type == 'img':
            q = Image.select().where(Image.img_id == rand)
        elif id_type == 'delete':
            q = Image.select().where(Image.delete_id == rand)
        if q.exists():
            rand = cls.gen_id()
        return rand

    @classmethod
    def upload(cls, file):
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in app.config['ALLOWED_EXTENSIONS']:
            return None
        image = Image.create(
                img_id=Image.gen_id('img'),
                delete_id=Image.gen_id('delete',
                                         length=app.config['DELETE_ID_LEN']),
                ext=ext)

        filename = '{}.{}'.format(image.img_id, image.ext)
        file.save(os.path.join(app.config['UPLOAD_DIR'], filename))

        return image

    @classmethod
    def delete_img(cls, delete_id):
        image = get_object_or_404(Image.select(), Image.delete_id == delete_id)

        filename = '{}.{}'.format(image.img_id, image.ext)
        os.remove(os.path.join(app.config['UPLOAD_DIR'], filename))

        image.delete_instance()



class Visitor(flask_db.Model):
    image = ForeignKeyField(Image, related_name='visitors')
    ip = CharField()
    headers = JSONField()
    timestamp = DateTimeField(default=datetime.datetime.now, index=True)

    class Meta:
        database = database


''' Views Helpers '''


@app.template_filter('unique')
def unique(inputlist):
    return list(set(inputlist))


@app.errorhandler(404)
def not_found(exc):
    return Response('<h3>Not found</h3>', 404)


def login_required(fn):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        if session.get('logged_in'):
            return fn(*args, **kwargs)
        return redirect(url_for('login', next=request.path))
    return inner


''' Views '''


@app.route('/login/', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next') or request.form.get('next') or \
                url_for('index')
    if request.method == 'POST' and request.form.get('password'):
        password = request.form.get('password')
        if password == app.config['ADMIN_PASSWORD']:
            session['logged_in'] = True
            session.permanent = True
            flash('You are now logged in.', 'success')
            print(type(next_url))
            return redirect(next_url)
        else:
            flash('Wrong password.', 'danger')
    return render_template('login.html', next_url=next_url)


@app.route('/logout/', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/upload/', methods=['GET', 'POST'])
@login_required
def upload():
    def fail():
        flash('Upload Failed', 'danger')
        return redirect(request.url)

    if request.method == 'POST':
        if 'file' not in request.files:
            fail()
        file = request.files['file']

        if file.filename == '':
            fail()
        if file:
            image = Image.upload(file)
            if not image:
                flash('Filetype not permitted.', 'danger')
                return redirect(request.url)

            if request.form['keyword']:
                image.keyword = request.form['keyword']
                image.save()
            flash('Image Uploaded: {}'.format(image.img_id), 'success')
            return redirect(url_for('data', img_id=image.img_id))
    return render_template('upload.html')


@app.route('/<img_id>/data')
@login_required
def data(img_id):
    entry = get_object_or_404(Image.select(), Image.img_id == img_id)
    return render_template('data.html', entry=entry)


@app.route('/<img_id>/')
def image_page(img_id):
    entry = get_object_or_404(Image.select(), Image.img_id == img_id)
    return render_template('image.html', entry=entry)


@app.route('/<img_id>/raw')
def image_raw(img_id):
    entry = get_object_or_404(Image.select(), Image.img_id == img_id)
    t = request.args.get('t')
    if t != 'No':
        print('Added visitor.')
        Visitor.create(image=entry, ip=request.remote_addr, headers=dict(request.headers))
    return entry.raw()


@app.route('/delete/<delete_id>')
def delete(delete_id):
    if request.args.get('s') == 'Yes':
        Image.delete_img(delete_id)
        return 'Ok.'
    return 'Are you sure? {}?s=Yes'.format(request.url)


@app.route('/')
@login_required
def index():
    q = Image.select().order_by(Image.timestamp.desc())
    # return object_list('index.html', query=q)
    return render_template('index.html', entries=q)


def main():
    database.create_tables([Image, Visitor], safe=True)
    app.run(debug=True)


if __name__ == '__main__':
    main()
