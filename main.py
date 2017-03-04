# -*- coding: utf-8 -*-

import json
import lxml.html as LH
import math
import random
import re
import urllib
import urllib2
import copy
import datetime
import time

import jinja2
import webapp2
from google.appengine.api import users
from google.appengine.ext import deferred
from google.appengine.ext import ndb
from twilio.rest import TwilioRestClient

from keys import *

POSTS_PER_PAGE = 6

class Lead(ndb.Model):
    ga = ndb.StringProperty()
    name = ndb.StringProperty()
    phone = ndb.StringProperty()
    email = ndb.StringProperty()
    contact = ndb.StringProperty()
    message = ndb.StringProperty()
    ip = ndb.StringProperty()
    product = ndb.StringProperty()
    leadId = ndb.IntegerProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)


class Insta(ndb.Model):
    src = ndb.StringProperty()
    link = ndb.StringProperty()
    type = ndb.IntegerProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)


class Post(ndb.Model):
    title = ndb.StringProperty()
    duration = ndb.StringProperty(default="PT00H00M00S")
    thumbnailUrl = ndb.StringProperty()
    uploadDate = ndb.StringProperty()
    authorName = ndb.StringProperty()
    ytCode = ndb.StringProperty()
    taskId = ndb.IntegerProperty()
    entryContent = ndb.StringProperty(repeated=True)
    tagList = ndb.StringProperty(repeated=True)
    sts = ndb.IntegerProperty(default=0)
    date = ndb.DateTimeProperty(auto_now_add=True)


class Product(ndb.Model):
    title = ndb.StringProperty()
    images = ndb.StringProperty(repeated=True)
    manufacturer = ndb.StringProperty()
    type = ndb.StringProperty()
    material = ndb.StringProperty()
    layers = ndb.IntegerProperty()
    crmId = ndb.IntegerProperty()
    length = ndb.FloatProperty()
    width = ndb.FloatProperty()
    diameter = ndb.FloatProperty()
    wheels_width = ndb.FloatProperty()
    bearing = ndb.StringProperty()
    hardness = ndb.StringProperty()
    suspension = ndb.FloatProperty()
    price = ndb.FloatProperty()


class Token(ndb.Model):
    title = ndb.StringProperty()
    prefix = ndb.StringProperty()
    token = ndb.StringProperty()
    refresh_token = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader('.'),
    extensions=['jinja2.ext.autoescape'],
    autoescape=False)


class MainPage(webapp2.RequestHandler):
    def get(self):

        self.response.headers['Content-Type'] = 'text/html'

        if self.request.get('code'):
            code = self.request.get('code')
            q = {
                'client_id': BTRX24_CODE,
                'grant_type': "authorization_code",
                'client_secret': BTRX24_KEY,
                'redirect_uri': "http://longbrd.ru",
                'code': code,
                'scope': "crm,user,task,tasks_extended,sonet_group"
            }
            q = urllib.urlencode(q)
            url = "https://longbord.bitrix24.ru/oauth/token/?{}".format(q)
            try:
                fp = urllib2.urlopen(url)
                data = json.loads(fp.read())
                ndb.delete_multi(Token.query().fetch(keys_only=True))
                token = Token(title="Bitrix24", prefix="btrx", token=data['access_token'],
                              refresh_token=data['refresh_token'])
                token.put()
                self.redirect("/")
            except urllib2.HTTPError as err:
                self.redirect("/?error")

        template = JINJA_ENVIRONMENT.get_template('index.html')
        masthead = JINJA_ENVIRONMENT.get_template('masthead.html')
        colophon = JINJA_ENVIRONMENT.get_template('colophon.html')
        scripts = JINJA_ENVIRONMENT.get_template('scripts.html')
        producttmpl = JINJA_ENVIRONMENT.get_template('product.html')
        posttmpl = JINJA_ENVIRONMENT.get_template('post_short.html')

        photo_stream = self.getPhotoStream(0, 16)

        admin = users.is_current_user_admin()
        if admin:
            postscount = Post.query().count()
        else:
            postscount = Post.query(Post.sts == 1).count()

        request = urllib2.urlopen(
            'https://api.instagram.com/v1/users/4538785375/?access_token={}'.format(INSTAGRAM_ACCESS_TOKEN))
        jsonData = json.loads(request.read())
        request.close()

        products = Product.query().fetch()
        products = [{
                        'admin': admin,
                        'productId': product.key.id(),
                        'crmId': product.crmId,
                        'images': product.images,
                        'title': product.title,
                        'manufacturer': product.manufacturer,
                        'type': product.type,
                        'material': product.material,
                        'layers': product.layers,
                        'length': product.length,
                        'width': product.width,
                        'diameter': product.diameter,
                        'wheels_width': product.wheels_width,
                        'bearing': product.bearing,
                        'hardness': product.hardness,
                        'suspension': product.suspension,
                        'price': product.price
                    } for product in products]

        productsoutput = ""
        for product in products:
            productsoutput += producttmpl.render(product)

        posts = Post.query(Post.sts == 1).order(Post.sts, -Post.date).fetch(6)
        posts = [{
                     'postId': post.key.id(),
                     'title': post.title,
                     'thumbnailUrl': post.thumbnailUrl,
                     'entryContent': post.entryContent[0]
                 } for post in posts]

        postsoutput = ""
        for post in posts:
            postsoutput += posttmpl.render(post)

        self.response.write(template.render({
            'masthead': masthead.render(),
            'colophon': colophon.render({
                'postscount': postscount,
                'instaphotos': jsonData['data']['counts']['media'],
                'instafollowers': jsonData['data']['counts']['followed_by'],
                'photo_stream': photo_stream
            }),
            'products': productsoutput,
            'posts': postsoutput,
            'scripts': scripts.render({
                'uIP': self.request.remote_addr,
                'host': self.request.host_url
            })
        }))

    def post(self):
        label = self.request.get('label')
        sl = int(self.request.get('sl'))
        response = {'status': "ok"}
        if label == self.request.cookies.get('_ga') and sl > 300:
            name = self.request.get('name')
            phone = self.request.get('phone')
            email = self.request.get('email')
            message = self.request.get('message')
            contact = self.request.get('discount')

            if phone or email or contact:
                data = {
                    'label': label,
                    'sl': sl,
                    'name': name,
                    'phone': phone,
                    'email': email,
                    'message': message,
                    'contact': contact,
                    'ip': self.request.remote_addr
                }

                task = deferred.defer(addLead, data)

                response['deferred'] = task.name
                # response['lead'] = addLead(data)
            else:
                response['status'] = "nofields"
        else:
            response['status'] = "no"

        self.respond_json(response)

    def respond_json(self, response={'status': "ok"}):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))
        # self.response.write(response)

    @staticmethod
    def getPhotoStream(kind, num=18):
        images, next, more = Insta.query(Insta.type == kind).order(Insta.date).fetch_page(64)

        filtered = []
        for img in images:
            if img.link not in filtered:
                filtered.append(img.link)
            else:
                images.remove(img)

        random.shuffle(images)
        return [{
                    'src': photo.src,
                    'url': photo.link,
                } for photo in images[:num]]

    @staticmethod
    def sendSMS(key, leadId):
        client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)

        message = client.messages.create(
            to="+79217884124",
            from_="+79217884124",
            body="Создан заказ: {}, номер лида: {}".format(key.id(), leadId),
        )
        pass


class Cron(webapp2.RequestHandler):
    def get(self):
        path = self.request.path
        currentImages = [img.link for img in Insta.query().fetch(None)]
        currentVideos = [post.ytCode for post in Post.query().fetch(None)]

        if path == '/getstream':
            tags = [
                'longboard',
                'longboarding',
                'skateboard'
            ]
            for tag in tags:
                url = 'https://www.instagram.com/explore/tags/{}/'.format(tag)
                request = urllib2.urlopen(url)
                root = LH.fromstring(request.read())
                request.close()

                jsonData = json.loads(root.xpath('//script[contains(text(), "window._sharedData")]')[0].text.replace(
                    'window._sharedData = ', '').replace(';', ''))
                images = [
                    Insta(link='https://www.instagram.com/p/{}'.format(img['code']), src=img['thumbnail_src'], type=0)
                    for img in jsonData['entry_data']['TagPage'][0]['tag']['media']['nodes'] if
                    'https://www.instagram.com/p/{}'.format(img['code']) not in currentImages]
                keys = ndb.put_multi(images)

        if path == '/getmine':
            q = {
                'count': 12,
                'access_token': '{}'.format(INSTAGRAM_ACCESS_TOKEN)
            }
            q = urllib.urlencode(q)
            url = 'https://api.instagram.com/v1/users/4538785375/media/recent?{}'.format(q)

            fp = urllib2.urlopen(url)
            jsonData = json.loads(fp.read())

            images = [Insta(link=img['link'], src=img['images']['thumbnail']['url'], type=1) for img in jsonData['data']
                      if img['link'] not in currentImages]
            keys = ndb.put_multi(images)

        if path == '/getvideos':
            q = {
                'part': 'snippet',
                'maxResults': '15',
                'type': 'video',
                'q': 'Лонгбординг',
                'relevanceLanguage': 'ru',
                'regionCode': 'RU',
                'key': '{}'.format(YT_TOKEN)
            }
            q = urllib.urlencode(q)
            url = 'https://www.googleapis.com/youtube/v3/search?{}'.format(q)

            fp = urllib2.urlopen(url)
            jsonData = json.loads(fp.read())

            videos = []
            tagList = [
                'лонгборд',
                'скейтборд',
                'лонгбординг',
                'скейтбординг',
                'скорость',
                'даунхилл',
                'longboard',
                'skateboard',
                'longboarding',
                'skateboarding',
            ]
            random.shuffle(tagList)
            for item in jsonData['items']:
                if item['id']['videoId'] not in currentVideos:
                    videos.append(Post(
                        title=item['snippet']['title'],
                        thumbnailUrl=item['snippet']['thumbnails']['high']['url'],
                        uploadDate=item['snippet']['publishedAt'],
                        authorName=item['snippet']['channelTitle'],
                        ytCode=item['id']['videoId'],
                        entryContent=[''],
                        tagList=tagList[:5]
                    ))

            keys = ndb.put_multi(videos)

            for key in keys:
                post = Post.get_by_id(key.id())
                taskId = Tasker().add(
                    title="Подготовить описание для клипа - {}".format(key.id()),
                    descr="Адрес на сайте - http://longbrd.ru/blog.html#post-{}".format(key.id())
                )
                if taskId:
                    post.taskId = taskId
                    post.put()

        if path == '/getnewtoken':
            Tasker.refreshToken()
            pass


def addLead(data, tries = 0):
    Tasker.refreshToken()

    leader = Leader()
    leadId = leader.add(
        name=data['name'] if data['name'] else '',
        phone=data['phone'] if data['phone'] else '',
        email=data['email'],
        message=data['message'],
        contact=data['contact'],
        ip=data['ip'],
        ga=data['label']
    )

    if not leadId and tries < 10:
        tries += 1
        time.sleep(5)
        return addLead(data, tries)
    lead = Lead(
        ga=data['label'],
        name=data['name'],
        phone=data['phone'],
        email=data['email'],
        message=data['message'],
        contact=data['contact'],
        leadId=leadId,
        ip=data['ip']
    )
    key = lead.put()
    return {
        'leadid': leadId,
        'key': key.id()
    }


def sendSMS(key, leadId):
    MainPage.sendSMS(key, leadId)
    pass


class Blog(webapp2.RequestHandler):
    def get(self):
        recent = MainPage.getPhotoStream(1)
        photo_stream = MainPage.getPhotoStream(0, 16)

        offset = 0

        path = self.request.path
        m = re.search(ur'/blog-(\d+)', path)
        currentPage = 0

        if m != None:
            offset = int(m.group(1)) * POSTS_PER_PAGE - POSTS_PER_PAGE
            currentPage = int(m.group(1))

        admin = users.is_current_user_admin()

        if admin:
            posts, next, more = Post.query(Post.sts < 2).order(Post.sts, -Post.date).fetch_page(POSTS_PER_PAGE,
                                                                                                offset=offset)
            pages = Post.query(Post.sts < 2).count()
            postscount = pages
        else:
            posts, next, more = Post.query(Post.sts == 1).order(Post.sts, -Post.date).fetch_page(POSTS_PER_PAGE,
                                                                                                 offset=offset)
            pages = Post.query(Post.sts == 1).count()
            postscount = pages

        pages = int(math.ceil(float(pages) / POSTS_PER_PAGE))
        posts = [{
                     'admin': admin,
                     'sts': post.sts,
                     'postId': post.key.id(),
                     'authorName': post.authorName,
                     'duration': post.duration,
                     'entryContent': post.entryContent,
                     'content': "\n".join(post.entryContent),
                     'tagList': post.tagList,
                     'tags': ",".join(post.tagList),
                     'thumbnailUrl': post.thumbnailUrl,
                     'title': post.title,
                     'uploadDate': post.uploadDate,
                     'ytCode': post.ytCode
                 } for post in posts]

        self.response.headers['Content-Type'] = 'text/html'

        template = JINJA_ENVIRONMENT.get_template('blog.html')
        masthead = JINJA_ENVIRONMENT.get_template('masthead.html')
        colophon = JINJA_ENVIRONMENT.get_template('colophon.html')
        posttmpl = JINJA_ENVIRONMENT.get_template('post.html')
        scripts = JINJA_ENVIRONMENT.get_template('scripts.html')

        postsoutput = ""
        for post in posts:
            postsoutput += posttmpl.render(post)

        request = urllib2.urlopen(
            'https://api.instagram.com/v1/users/4538785375/?access_token={}'.format(INSTAGRAM_ACCESS_TOKEN))
        jsonData = json.loads(request.read())
        request.close()

        next = next.urlsafe() if next != None else None

        self.response.write(template.render({
            'next': next,
            'admin': admin,
            'pages': pages,
            'currentPage': currentPage,
            'masthead': masthead.render(),
            'colophon': colophon.render({
                'postscount': postscount,
                'instaphotos': jsonData['data']['counts']['media'],
                'instafollowers': jsonData['data']['counts']['followed_by'],
                'photo_stream': photo_stream
            }),
            'posts': postsoutput,
            'recent': recent,
            'scripts': scripts.render({
                'uIP': self.request.remote_addr,
                'host': self.request.host_url,
                'admin': admin
            })
        }))


class EditPost(webapp2.RequestHandler):
    def post(self):
        admin = users.is_current_user_admin()
        if admin:
            postId = int(self.request.get('postId'))
            post = Post.get_by_id(id=postId)
            title = self.request.get('title')
            authorName = self.request.get('authorName')
            duration = self.request.get('duration')
            thumbnailUrl = self.request.get('thumbnailUrl')
            uploadDate = self.request.get('uploadDate')
            entryContent = self.request.get('entryContent')
            tagList = self.request.get('tagList')

            post.title = title
            post.authorName = authorName
            post.duration = duration
            post.thumbnailUrl = thumbnailUrl
            post.uploadDate = uploadDate
            post.entryContent = entryContent.split("\n")
            post.tagList = tagList.split(',')
            post.put()
            task = Tasker().update(post.taskId)

    def get(self):
        admin = users.is_current_user_admin()
        if admin:
            if self.request.path == '/removepost':
                postid = int(self.request.get('postid'))
                post = Post.get_by_id(id=postid)
                post.sts = 2
                post.put()
                task = Tasker().delete(post.taskId)
            if self.request.path == '/publishpost':
                postid = int(self.request.get('postid'))
                post = Post.get_by_id(id=postid)
                post.sts = not post.sts
                post.put()
                if post.sts:
                    Tasker().update(post.taskId)
                else:
                    Tasker().renew(post.taskId)
                self.response.headers['Content-Type'] = 'text/html'
                self.response.write(post.sts)


class Ga(webapp2.RequestHandler):
    def get(self):
        urllib2.urlopen("http://www.google-analytics.com/r/collect?{}".format(self.request.query))


class Login(webapp2.RequestHandler):
    def get(self):
        if self.request.path == '/loginmepls':
            url = users.CreateLoginURL('/')
        else:
            url = users.CreateLogoutURL('/')
        self.redirect(url)


class Tasker():
    token = Token.query().get().token
    refresh_token = Token.query().get().refresh_token

    tries = 0

    def add(self, title, descr):
        q = {
            'TASKDATA[TITLE]': title,
            'TASKDATA[DESCRIPTION]': descr,
            'TASKDATA[RESPONSIBLE_ID]': 1,
            'TASKDATA[GROUP_ID]': 10,
            'auth': Tasker.token
        }
        q = urllib.urlencode(q)
        try:
            url = "https://longbord.bitrix24.ru/rest/task.item.add.json?{}".format(q)
            fp = urllib2.urlopen(url)
            data = json.loads(fp.read())
            return data['result']
        except BaseException as err:
            if self.tries < 10:
                self.tries += 1
                time.sleep(5)
                return self.add(title, descr)

    def renew(self, taskId):
        q = {
            'TASKID': taskId,
            'auth': Tasker.token
        }
        q = urllib.urlencode(q)
        try:
            url = "https://longbord.bitrix24.ru/rest/task.item.renew.json?{}".format(q)
            fp = urllib2.urlopen(url)
            data = json.loads(fp.read())
        except BaseException as err:
            if self.tries < 10:
                self.tries += 1
                time.sleep(5)
                return self.renew(taskId)

    def update(self, taskId):
        q = {
            'TASKID': taskId,
            'auth': Tasker.token
        }
        q = urllib.urlencode(q)
        try:
            url = "https://longbord.bitrix24.ru/rest/task.item.complete.json?{}".format(q)
            fp = urllib2.urlopen(url)
            data = json.loads(fp.read())
            return data['result']
        except BaseException as err:
            if self.tries < 10:
                self.tries += 1
                time.sleep(5)
                return self.update(taskId)

    def delete(self, taskId):
        q = {
            'TASKID': taskId,
            'auth': Tasker.token
        }
        q = urllib.urlencode(q)
        try:
            url = "https://longbord.bitrix24.ru/rest/task.item.delete.json?{}".format(q)
            fp = urllib2.urlopen(url)
            data = json.loads(fp.read())
            return data['result']
        except BaseException as err:
            if self.tries < 10:
                self.tries += 1
                time.sleep(5)
                return self.delete(taskId)

    @staticmethod
    def refreshToken():
        try:
            q = {
                'client_id': BTRX24_CODE,
                'grant_type': "refresh_token",
                'client_secret': BTRX24_KEY,
                'redirect_uri': "http://longbrd.ru",
                'refresh_token': Tasker.refresh_token
            }
            q = urllib.urlencode(q)
            url = "https://longbord.bitrix24.ru/oauth/token/?{}".format(q)
            fp = urllib2.urlopen(url)
            data = json.loads(fp.read())
            ndb.delete_multi(Token.query().fetch(keys_only=True))
            token = Token(title="Bitrix24", prefix="btrx", token=data['access_token'],
                          refresh_token=data['refresh_token'])
            token.put()
        except BaseException as err:
            if Tasker.tries < 10:
                Tasker.tries += 1
                time.sleep(5)
                return Tasker.refreshToken()


class Leader():
    tries = 0

    def add(self,
            name='',
            phone='',
            email='',
            message='',
            contact='',
            ip=None,
            ga=None
            ):
        name = name.encode('utf-8') if name else u"Заявка на скидку".encode('utf-8')
        contact = contact.encode('utf-8')
        phone = phone.encode('utf-8')
        email = email.encode('utf-8')
        message = message.encode('utf-8')
        q = {
            'fields[TITLE]': name,
            'fields[NAME]': contact if contact else name,
            'fields[PHONE][0][VALUE]': phone if phone else '',
            'fields[PHONE][0][VALUE_TYPE]': "OTHER",
            'fields[EMAIL][0][VALUE]': email if email else '',
            'fields[EMAIL][0][VALUE_TYPE]': "OTHER",
            'fields[COMMENTS]': message,
            'fields[UF_CRM_IP]': ip,
            'fields[UF_CRM_GA]': ga,
            'fields[UF_CRM_CONTACT]': contact,
            'params[REGISTER_SONET_EVENT]': "Y"
        }
        try:
            q = urllib.urlencode(q)
            url = "https://longbord.bitrix24.ru/rest/crm.lead.add.json?auth={}".format(Tasker.token)
            req = urllib2.Request(url=url, data=q)
            fp = urllib2.urlopen(req)
            data = json.loads(fp.read())
            return data['result']
        except urllib2.HTTPError as err:
            if self.tries < 1:
                self.tries += 1
                time.sleep(5)
                return self.add(name, phone, email, message, contact, ip, ga)
            return json.loads(err.read())


class BTX24(webapp2.RequestHandler):
    def get(self, func, params):
        Tasker.refreshToken()
        if func == 'sync':
            models = {
                'leads': Lead(),
                'products': Product()
            }
            list = models[params].query().fetch()


            return
        try:
            url = "https://longbord.bitrix24.ru/rest/{}?auth={}".format(func, Tasker.token)
            req = urllib2.Request(url=url, data=params)
            fp = urllib2.urlopen(req)
            data = json.loads(fp.read())
            return self.respond_json(data)
        except urllib2.HTTPError as err:
            data = json.loads(err.fp.read())
            return self.respond_json(data)

    def respond_json(self, response={'status': "ok"}):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))


class Exporter(webapp2.RequestHandler):
    def get(self, kind):
        admin = users.is_current_user_admin()
        models = {
            'leads': Lead(),
            'insta': Insta(),
            'posts': Post(),
            'products': Product(),
            # 'token': Token()
        }
        data = []
        if kind in models:
            data = [item.to_dict() for item in models[kind].query().fetch()]

        str = json.dumps(data, default=Exporter.datetime_parser)
        return self.response_json(str)

    @staticmethod
    def datetime_parser(dct):
        return dct.isoformat()

    def response_json(self, str):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(str)


class Importer(webapp2.RequestHandler):
    def get(self, params):
        if 'localhost' in self.request.host:
            pass
        params = params.split('.')
        kind = params[0]
        mode = 'sfi'
        if len(params) > 1:
            mode = params[1]
        admin = users.is_current_user_admin()
        if admin:
            models = {
                'leads': Lead(),
                'insta': Insta(),
                'posts': Post(),
                'products': Product(),
                'token': Token()
            }
            if kind in models:
                url = 'http://longbrd.ru/export.{}'.format(kind)

                fp = urllib2.urlopen(url)
                data = json.loads(fp.read())

                objects = []
                for line in data:
                    object = models[kind]
                    for i, val in line.items():
                        if i == 'date':
                            val = datetime.datetime.strptime(val, "%Y-%m-%dT%H:%M:%S.%f")
                        setattr(object, i, val)
                    objects.append(copy.deepcopy(object))
                if mode == 'nsfi':
                    ndb.delete_multi(models[kind].query().fetch(keys_only=True))
                ndb.put_multi(objects)


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/order', MainPage),

    ('/ga', Ga),

    ('/blog.html', Blog),
    ('/blog-\d+.html', Blog),

    ('/savepost', EditPost),
    ('/removepost', EditPost),
    ('/publishpost', EditPost),

    ('/loginmepls', Login),
    ('/logoutmepls', Login),

    ('/getstream', Cron),
    ('/getmine', Cron),
    ('/getvideos', Cron),
    ('/getnewtoken', Cron),

    (r'/export.(.+)', Exporter),
    (r'/import.(.+)', Importer),

    (r'/btx24/(.+)/(.+|)', BTX24)
], debug=True)
