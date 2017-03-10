# -*- coding: utf-8 -*-

import sys

reload(sys)
sys.setdefaultencoding('utf8')

import copy
import datetime
import json
import lxml.html as LH
import math
import random
import re
import time
import urllib
import urllib2
import logging

import jinja2
import webapp2
from google.appengine.api import users
from google.appengine.ext import deferred
from google.appengine.ext import ndb
from twilio.rest import TwilioRestClient

from google.appengine.api import urlfetch

urlfetch.set_default_fetch_deadline(45)

from keys import *
from messages import *

POSTS_PER_PAGE = 6


class Lead(ndb.Model):
    ga = ndb.StringProperty()
    name = ndb.StringProperty()
    phone = ndb.StringProperty()
    email = ndb.StringProperty()
    contact = ndb.StringProperty()
    message = ndb.StringProperty()
    ip = ndb.StringProperty()
    product = ndb.KeyProperty()
    promo = ndb.KeyProperty()
    crmId = ndb.IntegerProperty(default=0)
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
    crmId = ndb.IntegerProperty(default=0)
    length = ndb.FloatProperty()
    width = ndb.FloatProperty()
    diameter = ndb.FloatProperty()
    wheels_width = ndb.FloatProperty()
    bearing = ndb.StringProperty()
    hardness = ndb.StringProperty()
    suspension = ndb.FloatProperty()
    price = ndb.FloatProperty()


class Promo(ndb.Model):
    code = ndb.StringProperty()
    discount = ndb.IntegerProperty(default=0)
    crmId = ndb.IntegerProperty(default=0)


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
                ndb.delete_multi(Token.query().fetch(keys_only=True))  # TODO: переделать в бач
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

        overquotatmpl = JINJA_ENVIRONMENT.get_template('overquota.html')

        try:
            photo_stream = self.getPhotoStream(0, 16)
        except BaseException, message:
            logging.critical('Ошибка 139 строка - {}'.format(message))
            return self.respond_html(overquotatmpl.render({
                'title': SERVER_OVER_QUOTA,
                'scripts': scripts.render({
                    'uIP': self.request.remote_addr,
                    'host': self.request.host_url
                })
            }))

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
                        'mainpage': True,
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

        self.respond_html(template.render({
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
        agree = self.request.get('agree')
        responseData = {'status': "ok"}
        if label == self.request.cookies.get('_ga') and sl > 300 and agree:
            name = self.request.get('name')
            phone = self.request.get('phone')
            email = self.request.get('email')
            message = self.request.get('message')
            contact = self.request.get('discount')
            promo = self.request.get('promo')
            product = int(self.request.get('product')) if self.request.get('product') else 0

            if phone or email or contact:
                promoKey = Promo.query(Promo.code == promo).get() if promo else 0
                productKey = Product.get_by_id(product) if product else 0
                data = {
                    'label': label,
                    'sl': sl,
                    'name': name,
                    'phone': phone,
                    'email': email,
                    'message': message,
                    'contact': contact,
                    'product': productKey,
                    'ip': self.request.remote_addr,
                    'promo': promoKey
                }

                task = deferred.defer(addLead, data)

                responseData['deferred'] = task.name
            else:
                responseData['status'] = "nofields"
        elif not agree:
            responseData['status'] = "notagree"
        else:
            responseData['status'] = "no"

        self.respond_json(responseData)

    def respond_json(self, responseData=''):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(responseData))

    def respond_html(self, responseData=''):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(responseData)

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
        responseData = {
            'status': 'ok'
        }
        path = self.request.path
        currentImages = [img.link for img in Insta.query().fetch(None)]
        currentVideos = [post.ytCode for post in Post.query().fetch(None)]

        if path == '/cron_getstream':
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
                responseData['added_keys'] = [key.id() for key in keys]

        if path == '/cron_getmine':
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
            responseData['added_keys'] = [key.id() for key in keys]

        if path == '/cron_getvideos':
            q = {
                'part': 'snippet',
                'maxResults': '1',
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
            responseData['added_keys'] = [key.id() for key in keys]
            responseData['added_tasks'] = []

            for key in keys:
                post = Post.get_by_id(key.id())
                taskId = Tasker().add(
                    title="Подготовить описание для клипа - {}".format(key.id()),
                    descr="Адрес на сайте - http://longbrd.ru/blog.html#post-{}".format(key.id())
                )
                if taskId:
                    post.taskId = taskId
                    post.put()
                    responseData['added_tasks'].append(taskId)

        if path == '/cron_getnewtoken' and self.request.server_name != 'localhost':
            responseData['token_key'] = Tasker.refreshToken()

        if path == '/cron_testlead':
            _ga = "GA1.2.{}.{}".format(
                random.randrange(1000000, 9000000),
                random.randrange(1000000, 9000000)
            )
            name = "Тест {}".format(random.randrange(1000000, 9000000))
            q = {
                'name': name,
                'email': "{}@markschk.ru".format(random.randrange(1000000, 9000000)),
                'phone': "+7 ({}) {}-{}-{}".format(
                    random.randrange(800, 900),
                    random.randrange(100, 900),
                    random.randrange(10, 90),
                    random.randrange(10, 90),
                ),
                'message': "Сообщение {}".format(random.randrange(1000000, 9000000)),
                'label': _ga,
                'sl': random.randrange(1000, 3000)
            }
            q = urllib.urlencode(q)
            url = 'http://longbrd.ru/order'
            # url = 'http://localhost:8080/order'
            req = urllib2.Request(url=url, data=q)
            req.add_header('Cookie', '_ga={}'.format(_ga))
            try:
                fp = urllib2.urlopen(req)
                data = fp.read()
                responseData['test_create'] = data
                time.sleep(5)
                q = {
                    'filter[NAME]': name
                }
                q = urllib.urlencode(q)
                url = "https://longbord.bitrix24.ru/rest/crm.lead.list.json?auth={}".format(Tasker.getToken())
                req = urllib2.Request(url=url, data=q)
                try:
                    fp = urllib2.urlopen(req)
                    data = json.loads(fp.read())
                    if data['total']:
                        responseData['test_get'] = data
                        logging.info(LEAD_TEST_CREATED)
                    else:
                        responseData['test_get'] = 'FAIL'
                        logging.error(LEAD_TEST_CRM_NOT_FOUND)
                except BaseException as err:
                    if 'code' in err and err.code == 401:
                        responseData['test_get'] = '{}'.format()
                        logging.error(LEAD_TEST_AUTH_FAIL)
            except BaseException as err:
                responseData['status'] = 'no'
                responseData['error'] = err
                logging.error(LEAD_FAIL)

        return self.response_json(responseData)

    def response_json(self, str):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(str)


def addLead(data, lead=False):
    if not lead:
        lead = Lead(
            ga=data['label'],
            name=data['name'],
            phone=data['phone'],
            email=data['email'],
            message=data['message'],
            contact=data['contact'],
            promo=data['promo'].key if data['promo'] else None,
            product=data['product'].key if data['product'] else None,
            crmId=0,
            ip=data['ip']
        )

    leader = Leader()
    leaderData = leader.add(
        name=data['name'] if data['name'] else '',
        phone=data['phone'] if data['phone'] else '',
        email=data['email'],
        message=data['message'],
        contact=data['contact'],
        promo=data['promo'] if data['promo'] else 0,
        product=data['product'] if data['product'] else 0,
        ip=data['ip'],
        ga=data['label']
    )
    if not isinstance(leaderData, int):
        return addLead(data=data, lead=lead)
    lead.crmId = leaderData
    key = lead.put()

    return {
        'leadid': leaderData,
        'key': key.id()
    }


def sendSMS(key, leadId):
    MainPage.sendSMS(key, leadId)
    pass


class Blog(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('blog.html')
        masthead = JINJA_ENVIRONMENT.get_template('masthead.html')
        colophon = JINJA_ENVIRONMENT.get_template('colophon.html')
        posttmpl = JINJA_ENVIRONMENT.get_template('post.html')
        scripts = JINJA_ENVIRONMENT.get_template('scripts.html')
        producttmpl = JINJA_ENVIRONMENT.get_template('product.html')

        overquotatmpl = JINJA_ENVIRONMENT.get_template('overquota.html')

        try:
            photo_stream = MainPage.getPhotoStream(0, 16)
        except BaseException, message:
            logging.critical('Ошибка 506 строка - {}'.format(message))
            return self.respond_html(overquotatmpl.render({
                'title': SERVER_OVER_QUOTA,
                'scripts': scripts.render({
                    'uIP': self.request.remote_addr,
                    'host': self.request.host_url
                })
            }))
        recent = MainPage.getPhotoStream(1)

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
                     'ytCode': post.ytCode,
                     'currentPage': self.request.path_url
                 } for post in posts]

        products = Product.query().fetch(3)
        products = [{
                        'admin': admin,
                        'productId': product.key.id(),
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
        random.shuffle(products)

        productsoutput = ""
        for product in products:
            productsoutput += producttmpl.render(product)

        i = 0
        postsoutput = ""
        for post in posts:
            i += 1
            if i == 3:
                postsoutput += u'<div class="service-details"><div class="row text-center">{}</div></div>'.format(
                    productsoutput)
            postsoutput += posttmpl.render(post)

        request = urllib2.urlopen(
            'https://api.instagram.com/v1/users/4538785375/?access_token={}'.format(INSTAGRAM_ACCESS_TOKEN))
        jsonData = json.loads(request.read())
        request.close()

        next = next.urlsafe() if next != None else None

        self.respond_html(template.render({
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
            'products': productsoutput,
            'scripts': scripts.render({
                'uIP': self.request.remote_addr,
                'host': self.request.host_url,
                'admin': admin
            })
        }))

    def respond_html(self, responseData=''):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(responseData)


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
    tries = 0

    def add(self, title, descr):
        q = {
            'TASKDATA[TITLE]': title,
            'TASKDATA[DESCRIPTION]': descr,
            'TASKDATA[RESPONSIBLE_ID]': 1,
            'TASKDATA[GROUP_ID]': 10
        }
        q = urllib.urlencode(q)
        try:
            url = "https://longbord.bitrix24.ru/rest/task.item.add.json?auth={}".format(Tasker.getToken())
            req = urllib2.Request(url=url, data=q)
            fp = urllib2.urlopen(req)
            data = json.loads(fp.read())
            return data['result']
        except BaseException as err:
            if 'code' in err and err.code == 401:
                logging.error(TASK_AUTH_FAIL)
                Tasker.refreshToken()
                return self.add(title, descr)

    def renew(self, taskId):
        q = {
            'TASKID': taskId
        }
        q = urllib.urlencode(q)
        try:
            url = "https://longbord.bitrix24.ru/rest/task.item.renew.json?auth={}".format(Tasker.getToken())
            req = urllib2.Request(url=url, data=q)
            fp = urllib2.urlopen(req)
            data = json.loads(fp.read())
            return data['result']
        except BaseException as err:
            if 'code' in err and err.code == 401:
                logging.error(TASK_AUTH_FAIL)
                Tasker.refreshToken()
                return self.renew(taskId)

    def update(self, taskId):
        q = {
            'TASKID': taskId
        }
        q = urllib.urlencode(q)
        try:
            url = "https://longbord.bitrix24.ru/rest/task.item.complete.json?auth={}".format(Tasker.getToken())
            req = urllib2.Request(url=url, data=q)
            fp = urllib2.urlopen(req)
            data = json.loads(fp.read())
            return data['result']
        except BaseException as err:
            if 'code' in err and err.code == 401:
                logging.error(TASK_AUTH_FAIL)
                Tasker.refreshToken()
                return self.update(taskId)

    def delete(self, taskId):
        q = {
            'TASKID': taskId
        }
        q = urllib.urlencode(q)
        try:
            url = "https://longbord.bitrix24.ru/rest/task.item.delete.json?auth={}".format(Tasker.getToken())
            req = urllib2.Request(url=url, data=q)
            fp = urllib2.urlopen(req)
            data = json.loads(fp.read())
            return data['result']
        except BaseException as err:
            if 'code' in err and err.code == 401:
                logging.error(TASK_AUTH_FAIL)
                Tasker.refreshToken()
                return self.delete(taskId)

    @staticmethod
    def getToken():
        return Token.query().get().token

    @staticmethod
    def getRefreshToken():
        return Token.query().get().refresh_token

    @staticmethod
    def refreshToken():
        q = {
            'client_id': BTRX24_CODE,
            'grant_type': "refresh_token",
            'client_secret': BTRX24_KEY,
            'redirect_uri': "http://longbrd.ru",
            'refresh_token': Tasker.getRefreshToken()
        }
        q = urllib.urlencode(q)
        url = "https://longbord.bitrix24.ru/oauth/token/?{}".format(q)
        try:
            fp = urllib2.urlopen(url)
            data = json.loads(fp.read())
            ndb.delete_multi(Token.query().fetch(keys_only=True))  # TODO: переделать в бач
            token = Token(title="Bitrix24", prefix="btrx", token=data['access_token'],
                          refresh_token=data['refresh_token'])
            key = token.put()
            logging.info(TOKEN_UPDATED)
            return key
        except BaseException as err:
            if 'code' in err and err.code == 401:
                logging.error(TOKEN_UPDATE_FAIL)
                return Tasker.refreshToken()


class Leader():
    tries = 0

    def add(self,
            name='',
            phone='',
            email='',
            message='',
            contact='',
            promo=0,
            product=0,
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
            url = "https://longbord.bitrix24.ru/rest/crm.lead.add.json?auth={}".format(Tasker.getToken())
            req = urllib2.Request(url=url, data=q)
            fp = urllib2.urlopen(req)
            data = json.loads(fp.read())
            lead = data['result']
            if product:
                q = {
                    'id': lead,
                    'rows[0][PRODUCT_ID]': product.crmId,
                    'rows[0][PRICE]': product.price,
                    'rows[0][QUANTITY]': 1
                }
                if promo:
                    q['rows[1][PRODUCT_ID]'] = promo.crmId
                    q['rows[1][PRICE]'] = -promo.discount
                    q['rows[1][QUANTITY]'] = 1
                q = urllib.urlencode(q)
                url = "https://longbord.bitrix24.ru/rest/crm.lead.productrows.set.json?auth={}".format(
                    Tasker.getToken())
                req = urllib2.Request(url=url, data=q)
                fp = urllib2.urlopen(req)
                data = json.loads(fp.read())
            return lead
        except BaseException as err:
            if err.code == 401:
                logging.error(LEAD_AUTH_FAIL)
                Tasker.refreshToken()
                return self.add(
                    name=name,
                    phone=phone,
                    email=email,
                    message=message,
                    contact=contact,
                    promo=promo,
                    product=product,
                    ip=ip,
                    ga=ga)


class BTX24(webapp2.RequestHandler):
    responseData = {
        'status': 'ok',
        'synced': []
    }
    models = {
        'products': Product(),
        'promo': Promo(),
    }
    handling = {
        'products': {
            'add': 'crm.product.add',
            'list': 'crm.product.list',
            'fields': {
                'title': "NAME",
                'price': "PRICE"
            },
            'serviceFields': {
                'ACTIVE': "Y",
                'CURRENCY_ID': "RUB",
                'MEASURE': 9,
                'VAT_INCLUDED': "Y",
                'CATALOG_ID': 24,
                'SECTION_ID': 16
            }
        },
        'promo': {
            'add': 'crm.product.add',
            'list': 'crm.product.list',
            'fields': {
                'title': "NAME",
                'price': "PRICE"
            },
            'serviceFields': {
                'ACTIVE': "Y",
                'CURRENCY_ID': "RUB",
                'MEASURE': 9,
                'VAT_INCLUDED': "Y",
                'CATALOG_ID': 24,
                'SECTION_ID': 22
            }
        }
    }

    def get(self, func, params):
        admin = users.is_current_user_admin()
        if func == 'sync' and admin:
            addfunc = self.handling[params]['add']
            listfunc = self.handling[params]['list']

            fields = self.handling[params]['fields']
            serviceFields = self.handling[params]['serviceFields']

            listItems = self.models[params].query().fetch()
            self.responseData['funcs'] = {
                'add': addfunc,
                'list': listfunc
            }
            self.responseData['item'] = params
            self.responseData['size'] = len(listItems)
            for item in listItems:
                q = []
                for i in fields.keys():
                    value = getattr(item, i)
                    if isinstance(value, list):
                        value = value[0]
                    if i == 'images':
                        # url = 'http:{}'.format(value)
                        # fp = urllib2.urlopen(url)
                        # image = fp.read().encode('base64')

                        # q.append('fields[DETAIL_PICTURE][fileData][0]={}.png'.format(item.key.id()))
                        # q.append('fields[DETAIL_PICTURE][fileData][1]={}'.format(image))
                        # q.append('fields[PREVIEW_PICTURE][fileData][0]={}.png'.format(item.key.id()))
                        # q.append('fields[PREVIEW_PICTURE][fileData][1]={}'.format(image))
                        continue

                    q.append('fields[{}]={}'.format(fields[i], value))
                for i in serviceFields.keys():
                    q.append('fields[{}]={}'.format(i, serviceFields[i]))
                q = "&".join(q)
                url = "https://longbord.bitrix24.ru/rest/crm.product.add?auth={}".format(Tasker.getToken())
                req = urllib2.Request(url=url, data=q)
                fp = urllib2.urlopen(req)
                data = json.loads(fp.read())
                item.crmId = data['result']
                item.put()
                self.responseData['synced'].append({
                    'key': item.key.id(),
                    'crmId': data['result']
                })
            return self.respond_json(self.responseData)
        try:
            url = "https://longbord.bitrix24.ru/rest/{}?auth={}".format(func, Tasker.getToken())
            req = urllib2.Request(url=url, data=params)
            fp = urllib2.urlopen(req)
            data = json.loads(fp.read())
            return self.respond_json(data)
        except BaseException as err:
            data = json.loads(err.fp.read())
            return self.respond_json(data)

    def respond_json(self, responseData={'status': "ok"}):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(responseData))


class Exporter(webapp2.RequestHandler):
    def get(self, kind):
        admin = users.is_current_user_admin()
        models = {
            # 'leads': Lead(), # Лиды из-за кдючей невозможно экспортировать, а делать доп.привязку мне вломак
            'insta': Insta(),
            'posts': Post(),
            'products': Product(),
            'token': Token()
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
                # 'leads': Lead(),
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
                    for keys in self.batch(models[kind].query().fetch(keys_only=True), n=100):
                        ndb.delete_multi(keys)

                for keys in self.batch(iterable=objects, n=100):
                    ndb.put_multi(keys)

    def batch(self, iterable=[], n=1):
        l = len(iterable)
        for ndx in range(0, l, n):
            yield iterable[ndx:min(ndx + n, l)]


class InstaCheck(webapp2.RequestHandler):
    def get(self):
        if self.request.get('code'):
            code = self.request.get('code')
            q = {
                'client_id': INSTAGRAM_CLIENT_ID,
                'client_secret': INSTAGRAM_CLIENT_SECRET,
                'grant_type': 'authorization_code',
                'redirect_uri': INSTAGRAM_REDIRECT_URI,
                'code': code
            }
            q = urllib.urlencode(q)
            url = 'https://api.instagram.com/oauth/access_token'
            req = urllib2.Request(url=url, data=q)
            try:
                fp = urllib2.urlopen(req)
                data = fp.read()
                return self.response_json(data)
            except BaseException, msg:
                return self.response_json(msg)

        if self.request.get('authorize'):
            q = {
                'client_id': INSTAGRAM_CLIENT_ID,
                'redirect_uri': INSTAGRAM_REDIRECT_URI,
                'response_type': 'code',
                'scope': 'follower_list'
            }
            q = urllib.urlencode(q)
            url = 'https://api.instagram.com/oauth/authorize/?{}'.format(q)
            # req = urllib2.Request(url=url)
            # fp = urllib2.urlopen(req)
            # data = fp.read()
            return self.response_html('<script>window.open("{}", "_blank")</script>'.format(url))

        q = {
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        q = urllib.urlencode(q)
        url = "https://api.instagram.com/v1/users/{}/followed-by?{}".format(
            'self',
            # INSTAGRAM_USER_ID,
            q
        )
        req = urllib2.Request(url=url)
        fp = urllib2.urlopen(req)
        data = fp.read()
        return self.response_json(data)

    def response_json(self, str):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(str)

    def response_html(self, str):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(str)


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

    ('/cron_\w+', Cron),

    (r'/export.(.+)', Exporter),
    (r'/import.(.+)', Importer),

    (r'/btx24/(.+)/(.+|)', BTX24),

    ('/instacheck', InstaCheck)
], debug=True)
