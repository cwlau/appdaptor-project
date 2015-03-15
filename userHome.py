
# users need to be logged in (Google users) when arriving methods in this file

import datetime
import re
import os
import webapp2
import logging

#---------------- Import from Google ------------------
#
from google.appengine.api import urlfetch
from google.appengine.api import users, images, memcache
from google.appengine.ext import blobstore, db
from google.appengine.ext.webapp import blobstore_handlers, template
#
#------------------------------------------------------

#----------------- Custom Classes & -------------------
#----------------- Datastore Schema -------------------
#
from commonFunction import createEventLog
from commonFunction import findAccount
from commonFunction import findAccountByNickname
from commonFunction import findItemById
from commonFunction import getCommonUiParams
from commonFunction import getUserInfo
from commonFunction import dateFromNow
from commonFunction import oneDayOrDate
from commonFunction import prepareShopItemData
from commonFunction import returnJsonResult
from commonFunction import returnXmlResult
from commonFunction import retrieveTargetApplicationList
from commonFunction import retrieveApplicationSettings, retrieveRestrictedNicknameList
from decorator import AccessControlForMessage
from decorator import AccessControlForShopItem
from decorator import AccessControlForTransaction
from decorator import UserNicknameRequired
import schema

#
#------------------------------------------------------
_settings = {
  'NICKNAME_MIN_LENGTH': retrieveApplicationSettings('env', 'nickname_min_chars'),
  'NICKNAME_MAX_LENGTH': retrieveApplicationSettings('env', 'nickname_max_chars'),

  'ITEM_MIN_QUANTITY': retrieveApplicationSettings('env', 'item_min_quantity'),
  'ITEM_MAX_QUANTITY': retrieveApplicationSettings('env', 'item_max_quantity'),
  'ITEM_MIN_PRICE': retrieveApplicationSettings('env', 'item_min_price')*100,
  'ITEM_MAX_PRICE': retrieveApplicationSettings('env', 'item_max_price')*100,
  'ITEM_MIN_ACTIVEDAYS': retrieveApplicationSettings('env', 'item_min_activeDays'),
  'ITEM_MAX_ACTIVEDAYS': retrieveApplicationSettings('env', 'item_max_activeDays')
}


class AddItemHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/itemEdit.html")
    self.response.out.write(template.render(path, getCommonUiParams(self, _settings)))
  
  @UserNicknameRequired
  def post(self):
    self.response.headers['Content-Type'] = "text/xml"
    
    user = users.get_current_user()
    account = findAccount()
    
    #TODO run in transaction
    itemTitle = itemDescription = itemPrivacy = ''
    itemPrice = itemQuantity = itemExpireIn = 0
    
    if self.request.get('title', '') is not '':
      itemTitle = self.request.get('title')
    if self.request.get('description', '') is not '':
      itemDescription = self.request.get('description')
    if self.request.get('price', '') is not '':
      itemPrice = int(round(float(self.request.get('price'))))
      if not _settings['ITEM_MIN_PRICE'] <= itemPrice <= _settings['ITEM_MAX_PRICE']:
        returnXmlResult(self, 'false', 'Price out of range')
        return
    if self.request.get('quantity', '') is not '':
      itemQuantity = int(self.request.get('quantity'))
      if not _settings['ITEM_MIN_QUANTITY'] <= itemQuantity <= _settings['ITEM_MAX_QUANTITY']:
        returnXmlResult(self, 'false', 'Quantity out of range')
        return
    if self.request.get('privacy', '') is not '':
      itemPrivacy = self.request.get('privacy')
    if self.request.get('expireIn', '') is not '':
      itemExpireIn = int(self.request.get('expireIn'))
      if not _settings['ITEM_MIN_ACTIVEDAYS'] <= itemExpireIn <= _settings['ITEM_MAX_ACTIVEDAYS']:
        returnXmlResult(self, 'false', 'Number of active days out of range')
        return
    
    item = schema.ShopItem(
      title = itemTitle,
      description = itemDescription,
      profilePicBlobKey = '',
      picBlobKeys = [],
      videoBlobKeys = [],
      markedPrice = itemPrice,
      discountPrice = None,
      quantity = itemQuantity,
      status = 'Draft',
      privacy = itemPrivacy,
      creationDate = None,
      expiryDate = None,
      expireIn = itemExpireIn,
      owner = account.nickname,
      viewCount = 0
    )
    item.put()
    createEventLog(account.nickname, 'CREATE_ITEM', 'itemId = '+str(item.key().id()), '')
    
    
    
    
    # breakdown title to each individual KeywordRepo
    titleInputList = re.sub(r'[^ a-zA-Z0-9]', '', item.title.lower()).split()
    
    for i in titleInputList:
      input = schema.KeywordRepo(
        shopItemId = str(item.key().id()),
        keyword = i,
        weight = 3
      )
      input.put()
    
    # add description
    # breakdown description to each individual KeywordRepo
    
    parsedDescription = item.description.replace('&nbsp;',' ').lower()
    parsedDescription = re.sub('<[^<]+?>', '', parsedDescription)
    parsedDescription = re.sub(r'[^ a-zA-Z0-9]', '', parsedDescription )
    descriptionInputList = parsedDescription.split()
    
    for i in descriptionInputList:
      input = schema.KeywordRepo(
        shopItemId = str(item.key().id()),
        keyword = i,
        weight = 1
      )
      input.put()
    
    returnXmlResult(self, 'true', str(item.key().id())+','+blobstore.create_upload_url('/user/uploadItemPhoto') )
#


class UploadItemPhotoHandler(blobstore_handlers.BlobstoreUploadHandler):
  @UserNicknameRequired
  @AccessControlForShopItem
  def post(self):
    
    itemId = self.request.get('itemId', '-1')
    account = findAccount()
    upload_files = self.get_uploads('file')  # 'file' is file upload field in the form

    item = schema.ShopItem.get_by_id(int(itemId))
    
    # item is not found
    if item is None:
      logging.info("item is not found")
      self.redirect( "/item/" + itemId )
      return
    
    actionType = self.request.get('actionType', '')
    
    if len(upload_files)<1:
      logging.info("No files selected")
      if actionType == 'addItem':
        url = "/user/previewItem?itemId=" + itemId + "&noImageSelected=true"
      else:
        url = "/item/" + itemId + "?itemUpdated=true&noImageSelected=true"
      
      self.redirect( url )
      return
    
    # security issue: only images allowed
    # we only allow certain mime types (mainly for .jpg, .png and .gif images) here
    
    for blob_info in upload_files:
      content_type = blob_info.content_type
      if content_type != 'image/jpeg' and content_type != 'image/png' and content_type != 'image/gif':
        logging.info("Incorrect file format")
        if actionType == 'addItem':
          url = "/user/previewItem?itemId=" + itemId + "&invalidImageFormat=true"
        else:
          url = "/item/" + itemId + "?itemUpdated=true&invalidImageFormat=true"
        
        self.redirect( url )
        return
    
    
    if item.profilePicBlobKey is not None and item.profilePicBlobKey != '':
      #remove the original file
      images.delete_serving_url(item.profilePicBlobKey)
      blobstore.delete(item.profilePicBlobKey)
      logging.info("User "+account.nickname+" deleted profile image for itemId = "+itemId+" KEY = "+item.profilePicBlobKey)
    
    for blob_info in upload_files:
      logging.info("***** User '"+ account.nickname +"' uploaded a file: '"+ blob_info.filename +"', type = '" +blob_info.content_type+ "' ")
      item.profilePicBlobKey = str(blob_info.key())
      logging.info("User "+account.nickname+" uploaded image for itemId = "+itemId+", KEY = "+item.profilePicBlobKey)

    item.put()
    
    if actionType == 'addItem':
      url = "/user/previewItem?itemId=" + itemId
    else:
      url = "/item/" + itemId + "?itemUpdated=true"
    
    self.redirect( url )
#

class PreviewItemHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  @AccessControlForShopItem
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    itemId = self.request.get('itemId', '-1')
    item = schema.ShopItem.get_by_id(int(itemId))
    if item.status == "Active":
      self.redirect("/item/"+itemId)
    path = os.path.join(os.path.dirname(__file__), "template/item.html")
    self.response.out.write(template.render(path, getCommonUiParams(self, prepareShopItemData(self, itemId, 'preview') )))
  
#

class EditItemHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  @AccessControlForShopItem
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    itemId = self.request.get('itemId', '-1')
    path = os.path.join(os.path.dirname(__file__), "template/itemEdit.html")
    self.response.out.write(template.render(path, getCommonUiParams(self, _settings, prepareShopItemData(self, itemId, 'edit') )))
  
  @UserNicknameRequired
  @AccessControlForShopItem
  def post(self):
    self.response.headers['Content-Type'] = "text/xml"
    if int(round(float(self.request.get('price', 0)))) <= 0 or int(round(float(self.request.get('quantity', 0)))) <= 0 \
        or ( self.request.get('expireIn') is not None and int(self.request.get('expireIn', 1)) <= 0):
      returnXmlResult(self, 'false', 'Input value cannot be null or negative')
      return
      
    account = findAccount()
    
    #TODO run in transaction
    itemId = self.request.get('itemId', '-1')
    item = schema.ShopItem.get_by_id(int(itemId))
    item.title =  self.request.get('title')
    item.description = self.request.get('description')
    
    itemPrice = int(round(float(self.request.get('price', 0))))
    if not _settings['ITEM_MIN_PRICE'] <= itemPrice <= _settings['ITEM_MAX_PRICE']:
      returnXmlResult(self, 'false', 'Price out of range')
      return
    item.markedPrice = itemPrice
    #if self.request.get('expiryDate', '') is not '':
    #  item.expiryDate = self.request.get('expiryDate', '')
    itemExpireIn = int(round(float(self.request.get('expireIn', -1))))
    if not itemExpireIn <= _settings['ITEM_MAX_ACTIVEDAYS']:
      returnXmlResult(self, 'false', 'Number of active days out of range')
      return
    item.expireIn = int(self.request.get('expireIn', -1))
    
    itemQuantity = int(round(float(self.request.get('quantity', 0))))
    if not _settings['ITEM_MIN_QUANTITY'] <= itemQuantity <= _settings['ITEM_MAX_QUANTITY']:
      returnXmlResult(self, 'false', 'Quantity out of range')
      return
    item.quantity = itemQuantity
    item.put()
    
    # KeywordRepo for title (weight = 3)
    # DELETE existing records
    
    keywordRepoQuery = schema.KeywordRepo.all().filter("shopItemId = ", itemId).filter("weight = ", 3)
    keywordRepoList = keywordRepoQuery.fetch(999999)
    
    for k in keywordRepoList:
      k.delete()
    
    # add title
    # breakdown title to each individual KeywordRepo
    
    # The str.split() method without an argument splits on whitespace
    # http://stackoverflow.com/questions/8113782/split-string-on-whitespace-in-python
    titleInputList = re.sub(r'[^ a-zA-Z0-9]', '', item.title.lower()).split()
    
    for i in titleInputList:
      input = schema.KeywordRepo(
        shopItemId = itemId,
        keyword = i,
        weight = 3
      )
      input.put()
    
    # DELETE existing records
    
    keywordRepoQuery = schema.KeywordRepo.all().filter("shopItemId = ", itemId).filter("weight = ", 1)
    keywordRepoList = keywordRepoQuery.fetch(999999)
    
    for k in keywordRepoList:
      k.delete()
    
    # add description
    # breakdown description to each individual KeywordRepo
    
    parsedDescription = item.description.replace('&nbsp;',' ').lower()
    parsedDescription = re.sub('<[^<]+?>', '', parsedDescription)
    parsedDescription = re.sub(r'[^ a-zA-Z0-9]', '', parsedDescription )
    descriptionInputList = parsedDescription.split()
    
    for i in descriptionInputList:
      input = schema.KeywordRepo(
        shopItemId = itemId,
        keyword = i,
        weight = 1
      )
      input.put()
    
    createEventLog(account.nickname, 'UPDATE_ITEM', 'itemId = '+itemId, '')
    
    returnXmlResult(self, 'true', itemId+','+blobstore.create_upload_url('/user/uploadItemPhoto'))
    return

#
class PublishItemHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  @AccessControlForShopItem
  def get(self):
    self.redirect('/')
  
  @UserNicknameRequired
  @AccessControlForShopItem
  def post(self):
    self.response.headers['Content-Type'] = "text/xml"
    account = findAccount()
    #TODO run in transaction
    itemId = self.request.get('itemId', '-1')
    item = schema.ShopItem.get_by_id(int(itemId))
    item.status = 'Active'
    item.creationDate = datetime.datetime.now()
    item.expiryDate = datetime.datetime.now()+datetime.timedelta(days=item.expireIn)
    item.expireIn = -1
    item.viewCount = 0
    item.put()
    createEventLog(account.nickname, 'PUBLISH_ITEM', 'itemId = '+str(item.key().id()), '')
    
    # HARDCODE FINAL
    # notify partner applications
    # Only applicable for production environment
    # skipped in localhost
    
    if "localhost" not in os.environ.get('HTTP_HOST'):
      
    
      itemTitle = re.sub('[\']', '\\\'', item.title)
      
      if item.profilePicBlobKey is not None and item.profilePicBlobKey != '':
        itemImageLinkUrl = images.get_serving_url(item.profilePicBlobKey, size=None, crop=False, secure_url=True)
        itemImageUrl = itemImageLinkUrl + '=s108-c'
      else:
        itemImageUrl = ""
      
      itemUrl = "https://" + re.sub('s~', '', os.environ.get('APPLICATION_ID', 'hardcode-appdaptor')) + ".appspot.com/item/" + str(item.key().id())
      
      itemMarkedPrice = "0"
      if item.markedPrice is not None:
        itemMarkedPrice = str(item.markedPrice/100.0)
      
      parsedDescription = item.description.replace('&nbsp;',' ').lower()
      parsedDescription = re.sub('<[^<]+?>', '', parsedDescription)
      parsedDescription = re.sub(r'[^ a-zA-Z0-9]', '', parsedDescription )
      
      applicationRecipientList = retrieveTargetApplicationList()
      
      
      for app in applicationRecipientList:
        dataToSend = """\"auth_token\": "%s",
"data": [{
"id": "%s",
"title": "%s",
"description": "%s",
"seller": {
  "id": "%s",
  "username": "%s"
},
"image": "%s",
"price": "%s",
"url": "%s"
}]""" % (app['auth_token'], str(item.key().id()), itemTitle, parsedDescription, item.owner, item.owner, itemImageUrl, "$ "+ itemMarkedPrice, itemUrl)
      
        logging.info(dataToSend)
        logging.info(app['domain'])
        logging.info(app['auth_token'])
        
        
        try:
          #form_fields = {
          #  "auth_token": app['auth_token'],
          #  "last_name": "Johnson",
          #  "email_address": "Albert.Johnson@example.com"
          #}
          #form_data = urllib.urlencode(form_fields)
          result = urlfetch.fetch(url=app['domain'] + "webservices/new_item",
                                  payload=dataToSend,
                                  method=urlfetch.POST,
                                  headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                  validate_certificate=False)
          logging.info(app['domain'] + "webservices/new_item")
        
        except:
          logging.error("Send item create notification error: " + app['domain'] + "webservices/new_item")
      #
    else:  
      logging.debug("urlfetch skipped for local environment")
      
    
    returnXmlResult(self, 'true')
    return

#

class UserSettingsHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/accountSettings.html")
    self.response.out.write(template.render(path, getCommonUiParams(self)))

#

class DeleteAllMyItemHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def post(self):
    account = findAccount()
    
    #TODO run in transaction
    itemQuery = schema.ShopItem.all().filter("owner = ", account.nickname)
    items = itemQuery.fetch(999999)
    
    for item in items:
      
      # Remove associated photos/ videos
      if item.profilePicBlobKey != '':
        images.delete_serving_url(item.profilePicBlobKey)
        blobstore.delete(item.profilePicBlobKey)
      
      # delete record in KeywordRepo
      keywordRepoQuery = schema.KeywordRepo.all().filter("shopItemId = ", str(item.key().id()))
      keywordRepoList = keywordRepoQuery.fetch(999999)
      
      for k in keywordRepoList:
        k.delete()
      
      item.delete()
    
  
    createEventLog(account.nickname, 'ACCOUNT_ITEM_CLEAR', 'accountId = '+str(account.key().id()), '')
  
    self.response.headers['Content-Type'] = "text/xml"
    returnXmlResult(self, 'true')

#
class DeleteMyAccountHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def post(self):
  
    account = findAccount()
    
    # delete all ShopItem.profileImg
    # delete all ShopItem
    
    itemQuery = schema.ShopItem.all().filter("owner = ", account.nickname)
    items = itemQuery.fetch(999999)
    
    for item in items:
      
      # Remove associated photos/ videos
      if item.profilePicBlobKey != '':
        images.delete_serving_url(item.profilePicBlobKey)
        blobstore.delete(item.profilePicBlobKey)
      
      # delete record in KeywordRepo
      keywordRepoQuery = schema.KeywordRepo.all().filter("shopItemId = ", str(item.key().id()))
      keywordRepoList = keywordRepoQuery.fetch(999999)
      
      for k in keywordRepoList:
        k.delete()
      
      item.delete()
    
    #TODO? delete conversationAssignment
    
    #TODO? delete messages
    
    #TODO? delete wishlist
    
    #TODO? delete request items
    
    #TODO? delete user profile image
    
    #TODO? clear user settings
    
    # Finally
    
    account.status = "Deleted"
    account.put()
    createEventLog(account.nickname, 'ACCOUNT_DELETE', 'accountId = '+str(account.key().id()), '')
  
    self.response.headers['Content-Type'] = "text/xml"
    returnXmlResult(self, 'true')

#


class UserNicknameSettingsHandler(webapp2.RequestHandler):
  def get(self):
    # if username has been set, redirect to user profile
    if db.GqlQuery("SELECT __key__ FROM Account WHERE id = :1", users.get_current_user().user_id()).count() == 1:
      self.redirect('/user/myProfile')
    
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/editNicknameFirstTime.html")
    self.response.out.write(template.render(path, getCommonUiParams(self)))
    #
  
  def post(self):
    
    self.response.headers['Content-Type'] = "text/xml"
    
    if len(self.request.get('nickname', '')) < _settings['NICKNAME_MIN_LENGTH']:
      returnXmlResult(self, 'false', 'This nickname is too short.')
      return
    
    if len(self.request.get('nickname')) > _settings['NICKNAME_MAX_LENGTH']:
      returnXmlResult(self, 'false', 'This nickname is too long.')
      return
    
    if db.GqlQuery("SELECT __key__ FROM Account WHERE id = :1", users.get_current_user().user_id()).count() == 1:
      returnXmlResult(self, 'false', 'Your account nickname has been set already.')
      return
    
    if db.GqlQuery("SELECT __key__ FROM Account WHERE nickname = :1", self.request.get('nickname')).count() == 1:
      returnXmlResult(self, 'false', '"'+self.request.get('nickname', '')+'" is not available.')
      return
    
    if bool(re.compile(r'[^a-zA-Z0-9]').search(self.request.get('nickname', ''))):
      returnXmlResult(self, 'false', 'Only letters and numbers are allowed.')
      return
      
    # check for restricted account nickname
    matched = 0
    
    
    # prepare restricted nickname from cache then datastore
    _RESTRICTED_ACCOUNT_NICKNAME = memcache.get('restricted-account-nickname-list')
    if _RESTRICTED_ACCOUNT_NICKNAME is not None:
      logging.debug('cache hit: _RESTRICTED_ACCOUNT_NICKNAME = ' + str(_RESTRICTED_ACCOUNT_NICKNAME))
      
    else:
      _RESTRICTED_ACCOUNT_NICKNAME = retrieveRestrictedNicknameList()
      
      nicknameQuery = schema.ApplicationSettings.all().filter('type = ', 'nickname')
      nicknameList = nicknameQuery.fetch(999999)
      
      for name in nicknameList:
        _RESTRICTED_ACCOUNT_NICKNAME.append(name.value)
      
      memcache.set('restricted-account-nickname-list', value= _RESTRICTED_ACCOUNT_NICKNAME, time=3600)
      logging.debug('Put into cache: _RESTRICTED_ACCOUNT_NICKNAME = ' + str(_RESTRICTED_ACCOUNT_NICKNAME))
    
    
    # compare user input nickname
    for name in _RESTRICTED_ACCOUNT_NICKNAME:
      if name == self.request.get('nickname').lower():
        matched += 1
        logging.info('name = '+ name + ' is restricted from registration')
    
    if matched != 0:
      returnXmlResult(self, 'false', 'You cannot use "'+self.request.get('nickname', '')+'" as nickname.')
      return
      
    # check for matched account names, for case-insensitive purpose
    accountQuery = schema.Account.all()
    matched = 0
    for account in accountQuery.fetch(999999):
      if account.nickname.lower() == self.request.get('nickname').lower():
        matched += 1
    
    if matched != 0:
      returnXmlResult(self, 'false', '"'+self.request.get('nickname', '')+'" is not available.')
      return
    
    # save to datastore
    user = users.get_current_user()
    if self.request.get('nickname', '') is not '' and user is not None:
    # TODO run in transaction for saving
      account = schema.Account(
        id = user.user_id(),
        googleNickname = user.nickname(),
        nickname = self.request.get('nickname'),
        name = '',
        description = '',
        email = user.email(),
        profilePicBlobKey = '',
        level = 'user',
        status = 'Active',
        accountSince = datetime.datetime.now(),
        authType = 'goog'
      )
      account.put()
      createEventLog(account.nickname, 'ACCOUNT_CREATE', 'accountId = '+str(account.key().id()), '')
      
      returnXmlResult(self, 'true', 'Account created')
      return
    returnXmlResult(self, 'false', 'You are not logged in')
#


class UserNicknameAvailabilityChecker(webapp2.RequestHandler):
  def post(self):
    self.response.headers['Content-Type'] = "text/xml"
    if len(self.request.get('nickname', '')) < _settings['NICKNAME_MIN_LENGTH']:
      returnXmlResult(self, 'false', 'This nickname is too short.')
      return
      
    if len(self.request.get('nickname', '')) > _settings['NICKNAME_MAX_LENGTH']:
      returnXmlResult(self, 'false', 'This nickname is too long.')
      return
    
    if db.GqlQuery("SELECT __key__ FROM Account WHERE id = :1", users.get_current_user().user_id()).count() == 1:
      returnXmlResult(self, 'false', 'Your account nickname has been set already.')
      return
    
    logging.info("Checking availability of nickname '"+ self.request.get('nickname') +"'")
    
    if db.GqlQuery("SELECT __key__ FROM Account WHERE nickname = :1", self.request.get('nickname')).count() == 1:
      returnXmlResult(self, 'false', '"'+self.request.get('nickname')+'" is not available.')
      return
    
    if bool(re.compile(r'[^a-zA-Z0-9]').search(self.request.get('nickname'))):
      returnXmlResult(self, 'false', 'Only letters and numbers are allowed.')
      return
      
    # check for restricted account nickname
    matched = 0
    
    
    # prepare restricted nickname from cache then datastore
    _RESTRICTED_ACCOUNT_NICKNAME = memcache.get('restricted-account-nickname-list')
    if _RESTRICTED_ACCOUNT_NICKNAME is not None:
      logging.debug('cache hit: _RESTRICTED_ACCOUNT_NICKNAME = ' + str(_RESTRICTED_ACCOUNT_NICKNAME))
      
    else:
      _RESTRICTED_ACCOUNT_NICKNAME = retrieveRestrictedNicknameList()
      
      nicknameQuery = schema.ApplicationSettings.all().filter('type = ', 'nickname')
      nicknameList = nicknameQuery.fetch(999999)
      
      for name in nicknameList:
        _RESTRICTED_ACCOUNT_NICKNAME.append(name.value.encode('utf-8'))
      
      memcache.set('restricted-account-nickname-list', value= _RESTRICTED_ACCOUNT_NICKNAME, time=3600)
      logging.debug('Put into cache: _RESTRICTED_ACCOUNT_NICKNAME = ' + str(_RESTRICTED_ACCOUNT_NICKNAME))
    
    
    # compare user input nickname
    for name in _RESTRICTED_ACCOUNT_NICKNAME:
      if name == self.request.get('nickname').lower():
        matched += 1
        logging.info('name = '+ name + ' is restricted from registration')
    
    if matched != 0:
      returnXmlResult(self, 'false', 'You cannot use "'+self.request.get('nickname', '')+'" as nickname.')
      return
    
    # check for matched account names, for case-insensitive purpose
    accountQuery = schema.Account.all()
    matched = 0
    for account in accountQuery.fetch(999999):
      if account.nickname.lower() == self.request.get('nickname').lower():
        matched += 1
    
    if matched != 0:
      returnXmlResult(self, 'false', '"'+self.request.get('nickname', '')+'" is not available.')
      return
    
    returnXmlResult(self, 'true')
#





class MyProfileViewHandler(webapp2.RequestHandler):
  def get(self):
  
    user = users.get_current_user()
    if user is not None:
      self.response.headers['Content-Type'] = "text/html"
      path = os.path.join(os.path.dirname(__file__), "template/profile.html")
      self.response.out.write(template.render(path, getCommonUiParams(self)))
      
    else:
      self.redirect('/')
#



class UserProfileEditHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/profileEdit.html")
    self.response.out.write(template.render(path, getCommonUiParams(self, 'edit')))
  
  @UserNicknameRequired
  def post(self):
    self.response.headers['Content-Type'] = "text/xml"
    
    user = users.get_current_user()
    
    #TODO run in transaction
    account = findAccount()
    
    if self.request.get('name', '') is not '':
      account.name = self.request.get('name')
    if self.request.get('description', '') is not '':
      account.description = self.request.get('description')
    
    account.put()
    createEventLog(account.nickname, 'ACCOUNT_PROFILE_CHANGE', 'accountId = '+str(account.key().id()), '')
    
    returnXmlResult(self, 'true', blobstore.create_upload_url('/user/uploadUserProfilePhoto'))
#



class UploadUserProfilePhotoHandler(blobstore_handlers.BlobstoreUploadHandler):
  @UserNicknameRequired
  def post(self):
    
    account = findAccount()
    upload_files = self.get_uploads('file')  # 'file' is file upload field in the form

    if len(upload_files)<1:
      self.redirect( "/user/myProfile?noImageSelected=true" )
      return
    
    
    # security issue: only images allowed
    # we only allow certain mime types (mainly for .jpg, .png and .gif images) here
    
    for blob_info in upload_files:
      content_type = blob_info.content_type
      if content_type != 'image/jpeg' and content_type != 'image/png' and content_type != 'image/gif':
        self.redirect( "/user/myProfile?invalidImageFormat=true" )
        return
    
    if account.profilePicBlobKey is not None and account.profilePicBlobKey != '':
      #remove the original file
      images.delete_serving_url(account.profilePicBlobKey)
      blobstore.delete(account.profilePicBlobKey)
      logging.info("User "+account.nickname+" deleted his/her profile image, KEY = "+account.profilePicBlobKey)
    
    for blob_info in upload_files:
      logging.info("***** User '"+ account.nickname +"' uploaded a file: '"+ blob_info.filename +"', type = '" +blob_info.content_type+ "' ")
      account.profilePicBlobKey = str(blob_info.key())
      logging.info("User "+account.nickname+" uploaded his/her profile image, new KEY = "+account.profilePicBlobKey)

    account.put()
    url = "/user/myProfile?profileUpdated"
    
    self.redirect( url )
#




class MyItemHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def get(self):
    self.redirect('/search/?type=myItem')
#

class DeleteItemHandler(webapp2.RequestHandler):
  
  @UserNicknameRequired
  @AccessControlForShopItem
  def post(self):
    self.response.headers['Content-Type'] = "text/xml"
    account = findAccount()
    
    #TODO run in transaction
    itemId = self.request.get('itemId', '-1')
    item = schema.ShopItem.get_by_id(int(itemId))
    
    if item is not None:
      
      # Remove associated photos/ videos
      
      if item.profilePicBlobKey != '':
        images.delete_serving_url(item.profilePicBlobKey)
        blobstore.delete(item.profilePicBlobKey)
      
      #TODO? update associated message conversations
      
      
      
      # delete record in KeywordRepo
      
      
      keywordRepoQuery = schema.KeywordRepo.all().filter("shopItemId = ", itemId)
      keywordRepoList = keywordRepoQuery.fetch(999999)
      
      for k in keywordRepoList:
        k.delete()
      
      item.delete()
      
      # Event Log
      createEventLog(account.nickname, 'DELETE_ITEM', 'itemId = '+str(item.key().id()), '')
    
    returnXmlResult(self, 'true')
    return
#



class ConfirmDeleteItemHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  @AccessControlForShopItem
  def get(self):
    itemId = self.request.get('itemId', '-1')
    item = schema.ShopItem.get_by_id(int(itemId))
    if item is None:
      self.response.out.write("invalid itemId")
      return
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/item.html")
    self.response.out.write(template.render(path, getCommonUiParams(self, prepareShopItemData(self, itemId, 'confirmDelete') )))
#



class MyWishlistHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def get(self):
    self.redirect('/search/?type=myWishlist')
#

class AddToWishlistHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def post(self):
    self.response.headers['Content-Type'] = "text/xml"
    itemId = self.request.get('itemId', '-1')
    item = schema.ShopItem.get_by_id(int(itemId))
    if item is None:
      returnXmlResult(self, 'false', "invalid itemId")
      return
    account = findAccount()
    
    # check for existence
    if db.GqlQuery("SELECT __key__ FROM WishList WHERE nickname = :1 AND shopItemId = :2", account.nickname, itemId).count() == 1:
      returnXmlResult(self, 'true', "Item already in wishlist")
      return
    
    wishlistItem = schema.WishList(
      nickname = account.nickname,
      shopItemId = itemId
    )
    wishlistItem.put()
    
    returnXmlResult(self, 'true')
    return
#


class RemoveFromWishlistHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def post(self):
    self.response.headers['Content-Type'] = "text/xml"
    itemId = self.request.get('itemId', '-1')
    item = schema.ShopItem.get_by_id(int(itemId))
    if item is None:
      returnXmlResult(self, 'false', "invalid itemId")
      return
    account = findAccount()
    
    wishlistItemQuery = schema.WishList.all().filter("nickname = ", account.nickname).filter("shopItemId = ", itemId)
    wishlistItem = wishlistItemQuery.fetch(1)
    
    for item in wishlistItem:
      item.delete()
    
    returnXmlResult(self, 'true')
    return
#




class RequestItemHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    itemId = self.request.get('itemId', '-1')
    item = schema.ShopItem.get_by_id(int(itemId))
    if item is None:
      returnJsonResult(self, 'false', "invalid itemId")
      return
    
    quantity = self.request.get('quantity', '0')
    totalPrice = self.request.get('totalPrice', '0')
    
    account = findAccount()
    ownerAccount = findAccountByNickname(item.owner)
    
    try:
      val = int(quantity)
    except ValueError:
      logging.info("quantity = " + str(quantity) + " is not an integer")
      returnJsonResult(self, 'false', "Invalid quantity value")
      return
    
    
    if item.quantity < int(round(float(quantity))):
      logging.info("Error occurred: available amount < requested amount")
      returnJsonResult(self, 'false', "There is not enough item available to fulfill your request.")
      return
    
    if int(float(totalPrice)*100) != int(quantity)* int(item.markedPrice):
      logging.info("Error occurred: total price != counted price")
      returnJsonResult(self, 'false', "Item price is updated, please refresh page and try again")
      return
      
    
    transaction = schema.Transaction(
      actor = account.nickname,
      owner = ownerAccount.nickname,
      status = 'Pending',
      itemId = itemId,
      quantity = int(quantity),
      itemTitle = item.title,
      itemPrice = item.markedPrice
    )
    transaction.put()
    
    createEventLog(account.nickname, 'TRANSACTION_CREATE', 'transactionId = '+str(transaction.key().id()), '')
    returnJsonResult(self, 'true')
    
#






class CancelRequestHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  @AccessControlForTransaction
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    transactionId = self.request.get('transactionId', '-1')
    transaction = schema.Transaction.get_by_id(int(transactionId))
    if transaction is None:
      returnJsonResult(self, 'false', "invalid transactionId")
      return
    
    account = findAccount()
    if transaction.actor != account.nickname:
      returnJsonResult(self, 'false', "This account cannot access this transaction")
      return
    
    transaction.status = "Cancelled"
    transaction.endDate = datetime.datetime.now()
    transaction.put()
    
    # update conversation as well
    # message to owner
    
    recipient = transaction.owner
    
    newConversation = schema.Conversation(
      title = 'Item request cancelled by '+transaction.actor,
      shopItemId = transaction.itemId,
      shopItemPrice = transaction.itemPrice,
      shopItemTitle = transaction.itemTitle
    )
    newConversation.put()
    newMessage = schema.Message(
      sender = 'System',
      recipient = recipient,
      content = 'Item request ('+ str(transaction.quantity) +' items) cancelled by '+account.nickname+'.\nClick on "Item Info" for more information.\n\nThis is a system generated message. Please do not reply.',
      owner = recipient,
      isRead = False,
      parentConversation = newConversation
    )
    newMessage.put()
    assignment = schema.ConversationAssignment(
      conversation = newConversation,
      ownerAccount = findAccountByNickname(recipient)
    )
    assignment.put()
    createEventLog(account.nickname, 'TRANSACTION_CANCEL', 'transactionId = '+str(transaction.key().id()), '')
    
    returnJsonResult(self, 'true')
    return
#
class ApproveRequestHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  @AccessControlForTransaction
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    transactionId = self.request.get('transactionId', '-1')
    transaction = schema.Transaction.get_by_id(int(transactionId))
    if transaction is None:
      returnJsonResult(self, 'false', "invalid transactionId")
      return
    
    account = findAccount()
    if transaction.owner != account.nickname:
      returnJsonResult(self, 'false', "Your account cannot access this transaction")
      return
    
    item = findItemById(transaction.itemId)
    if item.quantity > transaction.quantity:
      item.quantity = item.quantity - transaction.quantity
      item.put()
    else:
      returnJsonResult(self, 'false', "You do not have enough item to fulfill this request.")
      return
    
    transaction.status = "Approved"
    transaction.endDate = datetime.datetime.now()
    transaction.put()
    
    # update conversation as well
    # message to actor
    
    recipient = transaction.actor
    
    newConversation = schema.Conversation(
      title = 'Item request Approved by '+ account.nickname,
      shopItemId = transaction.itemId,
      shopItemPrice = transaction.itemPrice,
      shopItemTitle = transaction.itemTitle
    )
    newConversation.put()
    newMessage = schema.Message(
      sender = 'System',
      recipient = recipient,
      content = 'Item request ('+ str(transaction.quantity) +' items) was approved by '+account.nickname+'.\nClick on "Item Info" for more information.\n\nThis is a system generated message. Please do not reply.',
      owner = recipient,
      isRead = False,
      parentConversation = newConversation
    )
    newMessage.put()
    assignment = schema.ConversationAssignment(
      conversation = newConversation,
      ownerAccount = findAccountByNickname(recipient)
    )
    assignment.put()
    createEventLog(account.nickname, 'TRANSACTION_APPROVED', 'transactionId = '+str(transaction.key().id()), '')
    
    
    returnJsonResult(self, 'true')
    return
#
class RejectRequestHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  @AccessControlForTransaction
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    transactionId = self.request.get('transactionId', '-1')
    transaction = schema.Transaction.get_by_id(int(transactionId))
    if transaction is None:
      returnJsonResult(self, 'false', "invalid transactionId")
      return
    
    account = findAccount()
    if transaction.owner != account.nickname:
      returnJsonResult(self, 'false', "Your account cannot access this transaction")
      return
    
    transaction.status = "Rejected"
    transaction.endDate = datetime.datetime.now()
    transaction.put()
    
    # update conversation as well
    # message to actor
    recipient = transaction.actor
    
    newConversation = schema.Conversation(
      title = 'Item request Rejected by '+ account.nickname,
      shopItemId = transaction.itemId,
      shopItemPrice = transaction.itemPrice,
      shopItemTitle = transaction.itemTitle
    )
    newConversation.put()
    newMessage = schema.Message(
      sender = 'System',
      recipient = recipient,
      content = 'Item request ('+ str(transaction.quantity) +' items) was rejected by '+account.nickname+'.\nClick on "Item Info" for more information.\n\nThis is a system generated message. Please do not reply.',
      owner = recipient,
      isRead = False,
      parentConversation = newConversation
    )
    newMessage.put()
    assignment = schema.ConversationAssignment(
      conversation = newConversation,
      ownerAccount = findAccountByNickname(recipient)
    )
    assignment.put()
    createEventLog(account.nickname, 'TRANSACTION_REJECTED', 'transactionId = '+str(transaction.key().id()), '')
    
    returnJsonResult(self, 'true')
    return
#

class ResolveTransactionHandler(webapp2.RequestHandler):
  @UserNicknameRequired
  @AccessControlForTransaction
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    transactionId = self.request.get('transactionId', '-1')
    transaction = schema.Transaction.get_by_id(int(transactionId))
    if transaction is None:
      returnJsonResult(self, 'false', "invalid transactionId")
      return
    
    account = findAccount()
    if transaction.owner != account.nickname:
      returnJsonResult(self, 'false', "Your account cannot access this transaction")
      return
    
    transaction.status = "Resolved"
    transaction.endDate = datetime.datetime.now()
    transaction.put()
    
    createEventLog(account.nickname, 'TRANSACTION_RESOLVED', 'transactionId = '+str(transaction.key().id()), '')
    
    returnJsonResult(self, 'true')
    return
#







class PendingTransactionListHandler(webapp2.RequestHandler):
  def get(self):
    self.post()
    
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    account = findAccount()
    if account is None:
      returnJsonResult(self, 'false', 'Login Required')
      return
    
    transactionQuery = schema.Transaction.all().filter("owner = ", account.nickname).filter("status = ", 'Pending')
    transactionList = transactionQuery.fetch(10000)
    
    index = 0
    result_length = len(transactionList)
    for transaction in transactionList:
      transaction.id = transaction.key().id()
      transaction.displayDate = oneDayOrDate(transaction.recordDate)
      transaction.date_fromnow = dateFromNow(transaction.recordDate)
      transaction.itemPriceInFloat = transaction.itemPrice/100.0
      if result_length-1 == index:
        transaction.noComma = 'True'
      else:
        index = index + 1
        transaction.noComma = 'False'
    
    if len(transactionList)==0:
      transactionList.append({
        'endOfList': 'True',
        'noComma': 'True'
      })
    
    searchResult = {
      'transactionList': transactionList,
    }
    path = os.path.join(os.path.dirname(__file__), "template/transactionList.json")
    self.response.out.write(template.render(path, searchResult))
#

class RequestTransactionListHandler(webapp2.RequestHandler):
  def get(self):
    self.post()
    
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    account = findAccount()
    if account is None:
      returnJsonResult(self, 'false', 'Login Required')
      return
    
    transactionQuery = schema.Transaction.all().filter("actor = ", account.nickname).filter("status = ", 'Pending')
    
    transactionList = transactionQuery.fetch(10000)
    
    index = 0
    result_length = len(transactionList)
    for transaction in transactionList:
      transaction.id = transaction.key().id()
      transaction.displayDate = oneDayOrDate(transaction.recordDate)
      transaction.date_fromnow = dateFromNow(transaction.recordDate)
      transaction.itemPriceInFloat = transaction.itemPrice/100.0
      if result_length-1 == index:
        transaction.noComma = 'True'
      else:
        index = index + 1
        transaction.noComma = 'False'
    
    if len(transactionList)==0:
      transactionList.append({
        'endOfList': 'True',
        'noComma': 'True'
      })
    
    searchResult = {
      'transactionList': transactionList,
    }
    path = os.path.join(os.path.dirname(__file__), "template/transactionList.json")
    self.response.out.write(template.render(path, searchResult))
#


class ApprovedTransactionListHandler(webapp2.RequestHandler):
  def get(self):
    self.post()
    
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    account = findAccount()
    if account is None:
      returnJsonResult(self, 'false', 'Login Required')
      return
    
    transactionQuery = schema.Transaction.all().filter("owner = ", account.nickname).filter("status = ", 'Approved')
    transactionList = transactionQuery.fetch(10000)
    
    index = 0
    result_length = len(transactionList)
    for transaction in transactionList:
      transaction.id = transaction.key().id()
      transaction.displayDate = oneDayOrDate(transaction.recordDate)
      transaction.date_fromnow = dateFromNow(transaction.recordDate)
      transaction.itemPriceInFloat = transaction.itemPrice/100.0
      if result_length-1 == index:
        transaction.noComma = 'True'
      else:
        index = index + 1
        transaction.noComma = 'False'
    
    if len(transactionList)==0:
      transactionList.append({
        'endOfList': 'True',
        'noComma': 'True'
      })
    
    searchResult = {
      'transactionList': transactionList,
    }
    path = os.path.join(os.path.dirname(__file__), "template/transactionList.json")
    self.response.out.write(template.render(path, searchResult))
#







app = webapp2.WSGIApplication([
  ('/user/addItem', AddItemHandler),
  ('/user/addItem/', AddItemHandler),#alias
  ('/user/additem', AddItemHandler),#alias
  ('/user/additem/', AddItemHandler),#alias
  ('/user/uploadItemPhoto', UploadItemPhotoHandler),
  ('/user/editItem', EditItemHandler),
  ('/user/previewItem', PreviewItemHandler),
  ('/user/publishItem', PublishItemHandler),
  ('/user/confirmDeleteItem', ConfirmDeleteItemHandler),
  ('/user/deleteItem', DeleteItemHandler),
  
  ('/user/settings', UserSettingsHandler),
  ('/user/settings/', UserSettingsHandler),
  ('/user/settings/deleteAllMyItems', DeleteAllMyItemHandler),
  ('/user/settings/deleteMyAccount', DeleteMyAccountHandler),
  ('/user/settings/nickname', UserNicknameSettingsHandler),
  ('/user/settings/checkNicknameAvailability', UserNicknameAvailabilityChecker),
  ('/user/editProfile', UserProfileEditHandler),
  
  ('/user/myProfile', MyProfileViewHandler),
  ('/user/myprofile', MyProfileViewHandler),#alias
  ('/user/uploadUserProfilePhoto', UploadUserProfilePhotoHandler),
  ('/user/myItem', MyItemHandler),
  ('/user/myWishlist', MyWishlistHandler),
  ('/user/addToWishlist', AddToWishlistHandler),
  ('/user/removeFromWishlist', RemoveFromWishlistHandler),
  
  ('/user/requestItem', RequestItemHandler),
  ('/user/confirmCancel', CancelRequestHandler),
  ('/user/confirmApprove', ApproveRequestHandler),
  ('/user/confirmReject', RejectRequestHandler),
  ('/user/resolveTransaction', ResolveTransactionHandler),
  ('/user/transaction/list', PendingTransactionListHandler),
  ('/user/transaction/request/list', RequestTransactionListHandler),
  ('/user/transaction/approved/list', ApprovedTransactionListHandler)
], debug=True)


