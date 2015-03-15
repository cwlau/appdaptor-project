
import re
import os
import webapp2
import logging

#---------------- Import from Google ------------------
#
from google.appengine.api import users
from google.appengine.ext.webapp import template
#
#------------------------------------------------------

#----------------- Custom Classes & -------------------
#----------------- Datastore Schema -------------------
#
from commonFunction import getCommonUiParams
from commonFunction import findAccount
from commonFunction import prepareShopItemData
from commonFunction import returnJsonResult
from decorator import UserNicknameRequired
import schema

#
#------------------------------------------------------



class ItemTitleHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
  
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    itemId = self.request.get('itemId', '-1')
    if not itemId.isdigit() or int(itemId) <1:
      returnJsonResult(self, 'true', '')
      return
    
    item = schema.ShopItem.get_by_id(int(itemId))
    if item is None:
      returnJsonResult(self, 'false', "Item does not exist.")
      return
    
    itemTitle = item.title
    #itemTitle = re.sub('[\']', '\\\'', itemTitle)
    #itemTitle = re.sub('[\"]', '\\\"', itemTitle)
    itemTitle = re.sub('[\n\r]', '', itemTitle)
    
    returnJsonResult(self, 'true', itemTitle)
#


class ItemDescriptionHandler(webapp2.RequestHandler):
  def get(self, itemId):
    if not itemId.isdigit() or int(itemId) <1:
      self.response.out.write("bad request")
      return
    
    item = schema.ShopItem.get_by_id(int(itemId))
    if item is None:
      self.response.out.write("Item does not exist.")
      return
    
    itemInfo = {'description': item.description}
    
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/description.html")
    self.response.out.write(template.render(path, itemInfo))
#



class ItemViewHandler(webapp2.RequestHandler):
  def get(self, itemId):
    
    if not itemId.isdigit() or int(itemId) <1:
      self.response.out.write("bad request")
      return
    
    item = schema.ShopItem.get_by_id(int(itemId))
    if item is None:
      self.response.out.write("Item does not exist.")
      return
      
    # For Draft and Private / Expired items, only their owner/ admin can see details of them
    if item.status != 'Active' or item.privacy != 'Public':
      if users.get_current_user() is not None:
        account = findAccount()
        if account.nickname != item.owner and account.level != 'admin':
          if item.status == 'Expired':
            self.response.out.write("This item is expired")
          else:
            self.response.out.write("You are not permitted to view this item")
          return
        else:
          pass
          # Item owner and Admin are still allowed to view the item
      else:
        self.response.out.write("Login required to view this item")
        return
    
    if item.viewCount is None:
      item.viewCount = 1
      item.put()
    
    elif item.expireIn < 0:
      item.viewCount = item.viewCount + 1
      item.put()
    
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/item.html")
    self.response.out.write(template.render(path, getCommonUiParams(self, prepareShopItemData(self, itemId) )))
#



class MainHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
#



app = webapp2.WSGIApplication([
  ('/item/findTitle', ItemTitleHandler),
  ('/item/description/([^/]+)', ItemDescriptionHandler),
  ('/item/([^/]+)', ItemViewHandler),
  ('/', MainHandler)
], debug=True)


