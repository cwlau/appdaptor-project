
import re
import os
import webapp2
import logging

#---------------- Import from Google ------------------
#
from google.appengine.api import users, files, images
from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import template
#
#------------------------------------------------------

#----------------- Custom Classes & -------------------
#----------------- Datastore Schema -------------------
#
from commonFunction import getCommonUiParams
from commonFunction import getUserInfo
from decorator import UserNicknameRequired
import schema

#
#------------------------------------------------------


class UserDescriptionViewHandler(webapp2.RequestHandler):
  def get(self, nickname):
    
    userInfo = getUserInfo(nickname)
    
    if userInfo is None:
      logging.info("User '" + nickname + "' does not exist, cannot find user profile.")
      self.redirect('/error/404?type=user')
      return
      
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/description.html")
    
    self.response.out.write( template.render(path, userInfo) )
#




class UserProfileViewHandler(webapp2.RequestHandler):
  def get(self, nickname):
    
    userInfo = getUserInfo(nickname)
    
    if userInfo is None:
      logging.info("User '" + nickname + "' does not exist, cannot find user profile.")
      self.redirect('/error/404?type=user')
      return
      
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/profile.html")
    self.response.out.write( template.render(path, getCommonUiParams(self, userInfo )) )
  
#

class MainHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
#






app = webapp2.WSGIApplication([
  ('/profile/description/([^/]+)', UserDescriptionViewHandler),
  ('/profile/([^/]+)', UserProfileViewHandler),
  ('/', MainHandler)
], debug=True)


