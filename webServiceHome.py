
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
import schema
from commonFunction import findAccountByNickname
from commonFunction import retrieveApplicationSettings
from decorator import AuthRequired
from searchHome import lookupRelevantShopItems
from searchHome import lookupRelevantShopItemsByTitle
#
#------------------------------------------------------







# only for use in this class
def returnApiJsonResult(self, *args):
  path = os.path.join(os.path.dirname(__file__), "template/api_statusResult.json")
  success='false'
  message='no parameter given'
  
  if len(args)>0:
    success = args[0]
    message=''
  if len(args)>1:
    message = args[1]
  
  self.response.out.write(template.render(path, {
    'success': success,
    'message': message,
  }))
#

def getSenderApplicationId(token):
  return ""

#








class WebServiceSearchHandler(webapp2.RequestHandler):
  @AuthRequired
  def get(self):
    self.post()
  
  @AuthRequired
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    
    # get input from request. We use lowercase for filtering
    query = self.request.get('query', '').lower()
    
    
    range = int(float(self.request.get('limit', retrieveApplicationSettings('env', 'search_result_length')) ) )
    offset = int(float(self.request.get('offset', 0)))
    
    
    items = []
    
    # sort by relevance when there is some input
    if query != '':
      itemsNoOffset = lookupRelevantShopItems(query)
      
    
    # sort by popularity when there is some input
    else:
      itemQuery = ShopItem.all()
      itemQuery.filter("status = ", 'Active')
      itemQuery.order("-viewCount")
      itemQuery.order("-markedPrice")
      itemsNoOffset = itemQuery.fetch(999999)
    
    index = 0
    availableRange = range
    restrictedOffset = offset
    
    for item in itemsNoOffset:
    
      
      item.markedPriceInFloat = discountPriceInFloat = 0.0
      item.description = re.sub('[<]', ' <', item.description) # add space before removing html tags
      item.description = re.sub(r'\\', r'\\\\', item.description) # prevent error caused by \&quot; in json string
      item.description = re.sub(' <b>',  '<b>', item.description) # whitelist for some html elements 
      item.description = re.sub(' </b>', '</b>', item.description) #
      item.description = re.sub(' <i>',  '<i>', item.description) #
      item.description = re.sub(' </i>', '</i>', item.description) #
      item.description = re.sub(' <font',  '<font', item.description) #
      item.description = re.sub(' </font>', '</font>', item.description) #
      item.description = re.sub(' <span',  '<span', item.description) #
      item.description = re.sub(' </span>', '</span>', item.description) #
      item.description = re.sub(' <sub',  '<sub', item.description) #
      item.description = re.sub(' </sub>', '</sub>', item.description) #
      item.description = re.sub(' <sup',  '<sup', item.description) #
      item.description = re.sub(' </sup>', '</sup>', item.description) #
      item.description = re.sub('&nbsp;', ' ', item.description) # remove unwanted strings
      
      if item.markedPrice is not None:
        item.markedPriceInFloat = item.markedPrice/100.0
      if item.discountPrice is not None:
        item.discountPriceInFloat = item.discountPrice/100.0
        
      
      item.id = item.key().id()
      if index == 0:
        item.noComma = 'true'
      else:
        item.noComma = 'false'
      
      index = index + 1
    
      if item.profilePicBlobKey is not None and item.profilePicBlobKey != '':
        item.imageUrl = images.get_serving_url(item.profilePicBlobKey, size=None, crop=False, secure_url=True)+'=s108-c'
      else:
        item.imageUrl = "https://" + re.sub('s~', '', os.environ.get('APPLICATION_ID', 'hardcode-appdaptor')) + ".appspot.com/image/noimage.png"

      item.localUrl = "https://" + re.sub('s~', '', os.environ.get('APPLICATION_ID', 'hardcode-appdaptor')) + ".appspot.com/item/" + str(item.id)

      # handle range and offset
      if restrictedOffset > 0:
        restrictedOffset -= 1
        continue
      elif availableRange > 0:
        availableRange -= 1
        
        if availableRange == 0:
          item.noComma = 'true'
        items.append(item)
      else:
        break
    
    
    
    searchResult = {
      'items': items,
      'total': str(len(items)),
    }
    
    path = os.path.join(os.path.dirname(__file__), "template/api_searchResult.json")
    self.response.out.write(template.render(path, searchResult))
#


class WebServiceSearchSuggestionHandler(webapp2.RequestHandler):
  @AuthRequired
  def get(self):
    self.post()
  
  @AuthRequired
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    items = []
    query = self.request.get('query', '').lower()
    suggestedItems = lookupRelevantShopItemsByTitle(query)
    
    for suggestedItem in suggestedItems:
      logging.debug( "allItem: "+ str(suggestedItem.key().id()))
      items.append(suggestedItem)
    
    index = 0
    resultList = []
    
    # size of items is already limited in lookupRelevantShopItemsByTitle.
    # Further list size checking is not required.
    for item in items:
      item.id = item.key().id()
      if index == 0:
        item.noComma = 'true'
      else:
        item.noComma = 'false'
      index = index + 1
      
      resultList.append(item)
    
    searchResult = {
      'items': resultList,
    }
    
    path = os.path.join(os.path.dirname(__file__), "template/api_searchSuggest.json")
    self.response.out.write(template.render(path, searchResult))
#



class WebServiceSendMessageHandler(webapp2.RequestHandler):
  #@AuthRequired
  #def get(self):
  #  self.post()
  
  @AuthRequired
  def post(self):
    
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    token = self.request.get("token")
    
    # define parameters to accept
    # createm conversation after receiving all required information
    item_id = self.request.get('item_id', '-1')
    
    # need to take care of  "app-id + item_id" as unique identifier
    app_id = re.sub('s~', '', os.environ.get('APPLICATION_ID', 'hardcode-appdaptor'))
    app_id = re.sub('dev~', '', app_id)
    
    item_id = re.sub('s~', '', item_id)
    item_id = re.sub('dev~', '', item_id)
    item_id = re.sub(app_id, '', item_id)
    
    # remove any extra characters??!
    
    
    # item_id should be int here
    if item_id == -1:
      # some conversation may not relate to an item
      item_id = ""
    else:
      item = schema.ShopItem.get_by_id(int(item_id))
      if item is None:
        item_id = ""
    
    
    conversationInfo = {
      'source_user_id': self.request.get('source_user_id', None),
      'source_user_name': self.request.get('source_user_name', None),
      'destination_user_id': self.request.get('destination_user_id', None),
      'subject': self.request.get('subject', None),
      'message': self.request.get('message', None),
      'source_conversation_id': self.request.get('source_conversation_id', None),
      'destination_conversation_id': self.request.get('destination_conversation_id', None)
    }
    
    for i in conversationInfo:
      if conversationInfo[i] is None:
        logging.error("IMPORTANT -- missing: conversationInfo[" + str(i) + "] ")
        returnApiJsonResult(self, 'false', "Missing required information: " + str(i))
        return
    
    # checking on information is done.
    # Now work on the parameters
    
    shopItemId = None
    shopItemPrice = None
    shopItemTitle = None
    
    if item is not None:
      shopItemId = item_id
      shopItemPrice = item.markedPrice
      shopItemTitle = item.title
    
    recipient = conversationInfo['destination_user_id']
    recipientAccount = findAccountByNickname(recipient)
    
    # if target account does not exist, return error
    if recipientAccount is None:
      returnApiJsonResult(self, 'false', "Account does not exist: " + str(recipient))
      return
    
    
    # Create New Conversation
    newConversation = schema.Conversation(
      title = conversationInfo['subject'],
      shopItemId = shopItemId,
      shopItemPrice = shopItemPrice,
      shopItemTitle = shopItemTitle,
      partnerConversationId = conversationInfo['destination_conversation_id']
    )
    newConversation.put()
    
    
    # Create Message in conversation
    newMessage = schema.Message(
      sender = conversationInfo['source_user_name'] + " (Partner Apps)",
      senderApplicationId = getSenderApplicationId(token), # for partner messages only
      senderId = conversationInfo['source_user_id'], # for partner messages only
      recipient = recipient,
      content = conversationInfo['message'],
      owner = recipient,
      isRead = False,
      parentConversation = newConversation
    )
    newMessage.put()
   
    
    # Create ConversationAssignment
    assignment = schema.ConversationAssignment(
      conversation = newConversation,
      ownerAccount = recipientAccount
    )
    assignment.put()
    
    result = {
      'id': str(newConversation.key().id())
    }
    
    # return conversation id after creating new conversation
    path = os.path.join(os.path.dirname(__file__), "template/api_sendMessage.json")
    self.response.out.write( template.render(path, result) )
  
#


class WebServiceItemHandler(webapp2.RequestHandler):
  @AuthRequired
  def get(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    # define parameters to accept
    
    item_id = self.request.get('item_id', '-1')
    item = schema.ShopItem.get_by_id(int(item_id))
    if item is None:
      returnApiJsonResult(self, 'false', "invalid item_id")
      return
    
    # work on the parameters/ attributes
    
    itemTitle = item.title
    itemTitle = re.sub('[\n\r]', '', itemTitle)
    
    if item.profilePicBlobKey is not None and item.profilePicBlobKey != '':
      item.imageUrl = images.get_serving_url(item.profilePicBlobKey, size=None, crop=False, secure_url=True)+'=s108-c'
    else:
      item.imageUrl = ''
    
    item.markedPriceInFloat = item.markedPrice/100.0
    
    itemInfo = {
      "id": item_id,
      "title": itemTitle,
      "description": item.description,#TODO check for security issues
      "owner": item.owner,
      "image": item.imageUrl,
      "price": str(item.markedPriceInFloat),
      "url": "https://" + re.sub('s~', '', os.environ.get('APPLICATION_ID', 'hardcode-appdaptor')) + ".appspot.com/item/" + str(item_id)
    }
    
    returnResult = {
      'item': itemInfo,
    }
    
    path = os.path.join(os.path.dirname(__file__), "template/api_itemInfo.json")
    self.response.out.write(template.render(path, returnResult))
    return

  
  @AuthRequired
  def post(self):
    self.get()
#


class WebServiceNewItemAlertHandler(webapp2.RequestHandler):
  #@AuthRequired
  #def get(self):
  #  self.post()
  
  @AuthRequired
  def post(self):
    # receive item information.
    
    
    # generate alert to users. if applicable
    
    
    returnApiJsonResult(self, 'true', 'okay')
  
#

class WebServiceAddUserRatingHandler(webapp2.RequestHandler):
  @AuthRequired
  def get(self):
    self.post()
  
  @AuthRequired
  def post(self):
    
    returnApiJsonResult(self, 'false', "under construction")
  
#

class WebServiceAddItemRatingHandler(webapp2.RequestHandler):
  @AuthRequired
  def get(self):
    self.post()
  
  @AuthRequired
  def post(self):
    
    returnApiJsonResult(self, 'false', "under construction")
  
#

class WebServiceUserImportHandler(webapp2.RequestHandler):
  @AuthRequired
  def get(self):
    self.post()
  
  @AuthRequired
  def post(self):
    
    returnApiJsonResult(self, 'false', "under construction")
  
#


app = webapp2.WSGIApplication([
  ('/webservices/search', WebServiceSearchHandler),
  ('/webservices/search_suggestions', WebServiceSearchSuggestionHandler),
  ('/webservices/send_message', WebServiceSendMessageHandler),
  ('/webservices/item', WebServiceItemHandler),
  ('/webservices/new_item', WebServiceNewItemAlertHandler),
  ('/webservices/add_user_rating', WebServiceAddUserRatingHandler),
  ('/webservices/add_item_rating', WebServiceAddItemRatingHandler),
  ('/webservices/user_import', WebServiceUserImportHandler)
], debug=True)


