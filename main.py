# -*- coding: utf-8 -*-

import urllib2
import json
import jinja2
import webapp2
import random
import re
import math
import lxml.html as LH

from twilio.rest import TwilioRestClient
from google.appengine.api import users
from google.appengine.ext import ndb, deferred

from keys import *

POSTS_PER_PAGE = 5

class Order(ndb.Model):
    ga = ndb.StringProperty()
    name = ndb.StringProperty()
    phone = ndb.StringProperty()
    email = ndb.StringProperty()
    contact = ndb.StringProperty()
    message = ndb.StringProperty()
    ip = ndb.StringProperty()
    product = ndb.StringProperty()
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
    length = ndb.FloatProperty()
    width = ndb.FloatProperty()
    diameter = ndb.FloatProperty()
    wheels_width = ndb.FloatProperty()
    bearing = ndb.StringProperty()
    hardness = ndb.StringProperty()
    suspension = ndb.FloatProperty()
    price = ndb.FloatProperty()

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader('.'),
    extensions=['jinja2.ext.autoescape'],
    autoescape=False)

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'

        template = JINJA_ENVIRONMENT.get_template('index.html')
        masthead = JINJA_ENVIRONMENT.get_template('masthead.html')
        colophon = JINJA_ENVIRONMENT.get_template('colophon.html')
        scripts = JINJA_ENVIRONMENT.get_template('scripts.html')
        producttmpl = JINJA_ENVIRONMENT.get_template('product.html')

        photo_stream = self.getPhotoStream(0)

        admin = users.is_current_user_admin()
        postscount = 0
        if admin:
            postscount = Post.query().count()
        else:
            postscount = Post.query(Post.sts == 0).count()

        request = urllib2.urlopen('https://api.instagram.com/v1/users/4538785375/?access_token={}'.format(INSTAGRAM_ACCESS_TOKEN))
        jsonData = json.loads(request.read())
        request.close()

        products = Product.query().fetch()
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

        productsoutput = ""
        for product in products:
            productsoutput += producttmpl.render(product)

        self.response.write(template.render({
            'masthead': masthead.render(),
            'colophon': colophon.render({
                'postscount': postscount,
                'instaphotos': jsonData['data']['counts']['media'],
                'instafollowers': jsonData['data']['counts']['followed_by'],
                'photo_stream': photo_stream
            }),
            'products': productsoutput,
            'scripts': scripts.render({
                'uIP': self.request.remote_addr,
                'host': self.request.host_url
            })
        }))

    def post(self):
        label = self.request.get('label')
        if label == self.request.cookies.get('_ga'):
            name = self.request.get('name')
            phone = self.request.get('phone')
            email = self.request.get('email')
            message = self.request.get('message')
            contact = self.request.get('discount')

            order = Order(
                ga=self.request.cookies.get('_ga'),
                name=name,
                phone=phone,
                email=email,
                message=message,
                contact=contact,
                ip=self.request.remote_addr
            )
            key = order.put()

            deferred.defer(sendSMS, key)

            self.respond_json("ok")
        else:
            self.respond_json("no")

    def respond_json(self, sts="ok"):
        self.response.headers['Content-Type'] = 'application/json'
        result = {'status': sts}
        self.response.write(json.dumps(result))

    @staticmethod
    def getPhotoStream(type):
        images, next, more = Insta.query(Insta.type == type).order(Insta.date).fetch_page(64)

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
         } for photo in images[:16]]

    @staticmethod
    def sendSMS(key):
        client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)

        message = client.messages.create(
            to="+79217884124",
            from_="+79217884124",
            body="Создан заказ: {}".format(key.id()),
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

                jsonData = json.loads(root.xpath('//script[contains(text(), "window._sharedData")]')[0].text.replace('window._sharedData = ', '').replace(';', ''))
                images = [Insta(link='https://www.instagram.com/p/{}'.format(img['code']), src=img['thumbnail_src'], type=0) for img in jsonData['entry_data']['TagPage'][0]['tag']['media']['nodes'] if 'https://www.instagram.com/p/{}'.format(img['code']) not in currentImages]
                keys = ndb.put_multi(images)

        if path == '/getmine':
            user = users.get_current_user()
            request = urllib2.urlopen('https://api.instagram.com/v1/users/4538785375/media/recent?count=12&access_token={}'.format(INSTAGRAM_ACCESS_TOKEN))
            jsonData = json.loads(request.read())
            request.close()

            images = [Insta(link=img['link'], src=img['images']['thumbnail']['url'], type=1) for img in jsonData['data'] if img['link'] not in currentImages]
            keys = ndb.put_multi(images)

        if path == '/getvideos':
            request = urllib2.urlopen('https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=50&type=video&q=longboard&key={}'.format(YT_TOKEN))
            jsonData = json.loads(request.read())
            request.close()

            videos = []

            for item in jsonData['items']:
                if item['id']['videoId'] not in currentVideos:
                    videos.append(Post(
                        title=item['snippet']['title'],
                        thumbnailUrl=item['snippet']['thumbnails']['high']['url'],
                        uploadDate=item['snippet']['publishedAt'],
                        authorName=item['snippet']['channelTitle'],
                        ytCode=item['id']['videoId'],
                        entryContent=[''],
                        tagList=['longboard']
                    ))
            keys = ndb.put_multi(videos)

def sendSMS(key):
    return MainPage.sendSMS(key)

class Blog(webapp2.RequestHandler):
    def get(self):
        recent = MainPage.getPhotoStream(1)
        photo_stream = MainPage.getPhotoStream(0)

        offset = 0

        path = self.request.path
        m = re.search(ur'/blog-(\d+)', path)
        currentPage = 0

        if m != None:
            offset = int(m.group(1)) * POSTS_PER_PAGE - POSTS_PER_PAGE
            currentPage = int(m.group(1))

        admin = users.is_current_user_admin()
        pages = 0
        postscount = 0

        if admin:
            posts, next, more = Post.query().filter(Post.sts < 2).order(Post.sts, -Post.date).fetch_page(POSTS_PER_PAGE, offset=offset)
            pages = Post.query().count()
            postscount = pages
        else:
            posts, next, more = Post.query().filter(Post.sts == 1).order(Post.sts, -Post.date).fetch_page(POSTS_PER_PAGE, offset=offset)
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

        request = urllib2.urlopen('https://api.instagram.com/v1/users/4538785375/?access_token={}'.format(INSTAGRAM_ACCESS_TOKEN))
        jsonData = json.loads(request.read())
        request.close()

        self.response.write(template.render({
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
    def get(self):
        admin = users.is_current_user_admin()
        if admin:
            if self.request.path == '/removepost':
                postid = int(self.request.get('postid'))
                post = Post.get_by_id(id=postid)
                post.sts = 2
                post.put()
            if self.request.path == '/publishpost':
                postid = int(self.request.get('postid'))
                post = Post.get_by_id(id=postid)
                post.sts = not post.sts
                post.put()
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
    ('/getvideos', Cron)
], debug=True)
