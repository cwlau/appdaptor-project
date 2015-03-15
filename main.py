
import re
import os
import webapp2
import logging

#---------------- Import from Google ------------------
#
from google.appengine.api import users, files, images
from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers, template
#
#------------------------------------------------------

#----------------- Custom Classes & -------------------
#----------------- Datastore Schema -------------------
#
from commonFunction import getCommonUiParams
import schema
#
#------------------------------------------------------


class NotFoundErrorHandler(webapp2.RequestHandler):
  
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/error404.html")
    errorType = self.request.get('type', '')
    self.response.out.write(template.render(path, getCommonUiParams(self, errorType)))

class AccountSuspensionErrorHandler(webapp2.RequestHandler):
  
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/errorAccountSuspended.html")
    errorType = self.request.get('type', '')
    self.response.out.write(template.render(path, getCommonUiParams(self, errorType)))
    
class AccountDeletedErrorHandler(webapp2.RequestHandler):
  
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/errorAccountDeleted.html")
    errorType = self.request.get('type', '')
    self.response.out.write(template.render(path, getCommonUiParams(self, errorType)))


class ApiErrorHandler(webapp2.RequestHandler):
  
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/errorApi.html")
    errorType = self.request.get('type', '')
    self.response.out.write(template.render(path, getCommonUiParams(self, errorType)))


class AccessErrorHandler(webapp2.RequestHandler):
  
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/errorAccess.html")
    errorType = self.request.get('type', '')
    self.response.out.write(template.render(path, getCommonUiParams(self, errorType)))
    
    







class TrendsHandler(webapp2.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/trends.html")
    self.response.out.write(template.render(path, getCommonUiParams(self)))
    
#


class NewItemsHandler(webapp2.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/itemsNew.html")
    self.response.out.write(template.render(path, getCommonUiParams(self)))
    
#



class MainHandler(webapp2.RequestHandler):
  def get(self):
    if self.request.get('login', '') is not '':
      self.redirect(users.create_login_url(self.request.uri.replace('?login', '')) )
      
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/index.html")
    self.response.out.write(template.render(path, getCommonUiParams(self)))
    






app = webapp2.WSGIApplication([
  ('/error/404', NotFoundErrorHandler),
  ('/error/suspend', AccountSuspensionErrorHandler),
  ('/error/deleted', AccountDeletedErrorHandler),
  ('/error/api', ApiErrorHandler),
  ('/error', AccessErrorHandler),
  ('/trends', TrendsHandler),
  ('/new', NewItemsHandler),
  ('/', MainHandler)
], debug=True)
