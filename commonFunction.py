
import datetime
import re
import os
import webapp2
import logging


#---------------- Import from Google ------------------
from google.appengine.api import users, images, memcache
from google.appengine.ext import blobstore, db
from google.appengine.ext.webapp import template

#
#------------------------------------------------------

#----------------- Custom Classes & -------------------
#----------------- Datastore Schema -------------------
#
import schema

#
#------------------------------------------------------


def returnXmlResult(self, *args):
  path = os.path.join(os.path.dirname(__file__), "template/result.xml")
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


def returnJsonResult(self, *args):
  path = os.path.join(os.path.dirname(__file__), "template/statusResult.json")
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



def retrieveTargetApplicationInfo(token):

  tokenList = []
  tokenListQuery = schema.ApplicationApiSettings.all().filter('apiType = ', 'partner').filter('key = ', token)
  tokenListResult = tokenListQuery.fetch(1000)
  
  for api in tokenListResult:
    logging.debug("Retrieved from datastore: token = " + api.token)
    tokenList.append({
      'domain': api.domain,
      'auth_token': api.token
    })
  
  return tokenList


def retrieveTargetApplicationList():

  tokenList = []
  tokenListQuery = schema.ApplicationApiSettings.all().filter('apiType = ', 'partner')
  tokenListResult = tokenListQuery.fetch(1000)
  
  for api in tokenListResult:
    logging.debug("Retrieved from datastore: token = " + api.token)
    tokenList.append({
      'domain': api.domain,
      'auth_token': api.token
    })
  
  return tokenList


  
  


# get token list.
# Since it is frequently used one, we have to put it in memcache to improve performance.
def getTokenList():
  
  # prepare restricted nickname from cache then datastore
  tokenList = memcache.get('api-own-token-list')
  if tokenList is not None:
    logging.debug('cache hit: tokenList = ' + str(tokenList))
    
  else:
    tokenList = []
    tokenListQuery = schema.ApplicationApiSettings.all().filter('apiType = ', 'own')
    tokenListResult = tokenListQuery.fetch(1000)
    
    for api in tokenListResult:
      logging.debug("Retrieved from datastore: token = " + api.token)
      tokenList.append(api.token)
    
    memcache.set('api-own-token-list', value= tokenList, time=3600)
    logging.debug('Put into cache: tokenList = ' + str(tokenList))
  
  return tokenList

def invalidateTokenList():
  memcache.delete('api-own-token-list')
  return

def retrieveEventLogFullSet():
  list = ['',
    'CREATE_ITEM',
    'UPDATE_ITEM',
    'DELETE_ITEM',
    'PUBLISH_ITEM',
    
    'EXPIRE_ITEM_REMINDER',
    
    'ACCOUNT_ACCESS_DENIED',
    'SHOPITEM_ACCESS_DENIED',
    'MESSAGE_ACCESS_DENIED',
    'TRNASACTION_ACCESS_DENIED',
    
    'ACCOUNT_CREATE',
    'ACCOUNT_PROFILE_CHANGE',
    'ACCOUNT_ACTIVATE',
    'ACCOUNT_DEACTIVATE',
    'ACCOUNT_DELETE',
    'ACCOUNT_ITEM_CLEAR',
    
    'STUDENT_ACCOUNT_VERIFY',
    'STUDENT_ACCOUNT_EXPIRE',
    'STUDENT_ACC_VERIFY_FAILED',
    
    'ADMIN_CREATE',
    'ADMIN_DELETE',
    'ADMIN_DELETE_ITEM',
    'ADMIN_API_UPDATE',
    
    'APP_SETTINGS_UPDATE',
      
    'TRANSACTION_CREATE',
    'TRANSACTION_CANCEL',
    'TRANSACTION_APPROVED',
    'TRANSACTION_REJECTED',
    'TRANSACTION_RESOLVED',
  
    'MESSAGE_CREATE',
    'MESSAGE_REPLY'
  ]
  return sorted(list)
#

def createEventLog(nickname, type, target, content):
  log = schema.EventLog(
    actor = nickname,
    actionType = type,
    target = target,
    content = content
  )
  log.put()
#



def retrieveRestrictedNicknameList():
  list = ['robot', 'system', 'admin', 'master', 'visitor', 'noreply']
  return sorted(list)

def updateApplicationSettings(type, name, remarks, value):

  if type == 'delete-restricted':
    record = schema.ApplicationSettings.all().filter('type = ', 'nickname').filter('value = ', value).get()
    logging.debug(record)
    if record is not None:
      record.delete()
    return

  # save into datastore then memcache
  # check existence of record before creating one, update if exist
  
  record = schema.ApplicationSettings.all().filter('type = ', type).filter('name = ', name).get()
  if record is not None and type != 'nickname':
    record.value = value
    record.put()
    
  else:
    record = schema.ApplicationSettings(
      type = type,
      name = name,
      remarks = remarks,
      value = value
    )
    record.put()
  
  if type != 'nickname':
    memcache.set(generateMemcacheKey(type, name), value= value, time=3600)
  logging.debug("Updated application settings. " + name + " = " + str(value))
  
  return
  

def retrieveApplicationSettings(type, name):

  if name == 'item_max_activeDays':
    return retrieveApplicationSettingsWithDefault(type, name, 180)
  elif name == 'item_min_activeDays':
    return retrieveApplicationSettingsWithDefault(type, name, 1)
  elif name == 'item_max_price':
    return retrieveApplicationSettingsWithDefault(type, name, 5000)
  elif name == 'item_min_price':
    return retrieveApplicationSettingsWithDefault(type, name, 1)
  elif name == 'item_max_quantity':
    return retrieveApplicationSettingsWithDefault(type, name, 1000)
  elif name == 'item_min_quantity':
    return retrieveApplicationSettingsWithDefault(type, name, 1)
  elif name == 'nickname_max_chars':
    return retrieveApplicationSettingsWithDefault(type, name, 20)
  elif name == 'nickname_min_chars':
    return retrieveApplicationSettingsWithDefault(type, name, 5)
  elif name == 'item_expire_alert_daysBefore':
    return retrieveApplicationSettingsWithDefault(type, name, 3)
  elif name == 'search_result_length':
    return retrieveApplicationSettingsWithDefault(type, name, 10)
  elif name == 'conversation_group_size':
    return retrieveApplicationSettingsWithDefault(type, name, 5)
  elif name == 'cron_item_expiryDateChecker':
    return retrieveApplicationSettingsWithDefault(type, name, '1') #true
  elif name == 'cron_account_expiryDateChecker':
    return retrieveApplicationSettingsWithDefault(type, name, '1') #true
    
  else:
    logging.error("missing application settings: type = " +type+ ",name = "+ name)
    return 0


def retrieveApplicationSettingsWithDefault(type, name, default):
  # get from memcache then datastore
  value = memcache.get(generateMemcacheKey(type, name))
  
  # check memcache
  if value is not None:
    logging.debug("hit from memcache for name = " + name + ". value = " + str(value))
    return value
  
  # check datastore
  else:
    record = schema.ApplicationSettings.all().filter('type =', type).filter('name =', name).get()
    
    if record is not None:
      value = record.value
      logging.debug("record found from datastore for name = " + name + ". value = " + str(value))
      # update memcache
      memcache.set(generateMemcacheKey(type, name), value= value, time=3600)
      logging.debug("saved to memcache for name = " + name + ", type = "+ type +" with value = " + str(value))
    
    else:
      value = default
      logging.debug("record not found from datastore for name = " +name + ", type = "+ type )
      memcache.set(generateMemcacheKey(type, name), value= value, time=3600)
      logging.debug("saved to memcache for name = " + name + ", type = "+ type +" with default value = " + str(value))
  return value

#private
def generateMemcacheKey(type, name):
  return type + '_' + name



#private
class UtcTzinfo(datetime.tzinfo):
  def utcoffset(self, dt): return datetime.timedelta(0)
  def dst(self, dt): return datetime.timedelta(0)
  def tzname(self, dt): return 'UTC'
  def olsen_name(self): return 'UTC'

TZINFOS = {
  'utc': UtcTzinfo()
}

#private
def adds(num):
  try:
    float(num)
    if num >= 2 or num == 0:
      return "s "
    else:
      return " "
  except:
    return " "


def oneDayOrDate(the_date):

  if the_date is None:
    return ''

  if the_date == 0:
    return ''

  try:
    utc = TZINFOS['utc']
    fileDate = the_date.replace(tzinfo = utc)
    
    today = datetime.datetime.today().replace(tzinfo = utc)
    
    # see if 16 hours is a better way to display the list
    one_day = datetime.timedelta(hours=16)

    timezone = datetime.timedelta(0)
    
    # adjust timezone timedelta here
    #timezone = datetime.timedelta(hours=8)
    
    dayBorder = today - one_day + timezone
    today = today + timezone

    if fileDate > dayBorder:
      return the_date.strftime("%H:%M")
    elif fileDate.year < today.year:
      return the_date.strftime("%b %d, %Y")
    else:
      return the_date.strftime("%b %d")
    
  except:
    return the_date
    
def dateFromNow(the_date):

  if the_date is None:
    return ''

  try:
    if the_date == 0:
      return 'Unknown time '
    
    utc = TZINFOS['utc']
    
    loginTime = the_date.replace(tzinfo = utc)
    now = datetime.datetime.today().replace(tzinfo = utc)
    diff = now - loginTime
    
    # to compare:
    diff_sec = (diff.days)*86400 - diff.seconds - diff.microseconds/1000000
    diff_days = ((diff.days)*86400 - diff.seconds - diff.microseconds/1000000)/60
    
    if diff.days == 0:
      if 0 <= diff.seconds < 60:
        return str(diff.seconds) + " second" + adds(diff.seconds)
      elif 60 <= diff.seconds < 3600:
        if diff.seconds%60 == 0:
          return str(diff.seconds/60) + " minute" + adds(diff.seconds/60)
        return str(diff.seconds/60) + " minute" + adds(diff.seconds/60) + str(diff.seconds%60) + " sec" + adds(diff.seconds%60)
      elif 3600 <= diff.seconds < 86400:
        if diff.seconds/60%60 == 0:
          return str(diff.seconds/3600) + " hour" + adds(diff.seconds/3600)
        return str(diff.seconds/3600) + " hour" + adds(diff.seconds/3600) + str(diff.seconds/60%60) + " minute" + adds(diff.seconds/60%60)
      else:
        logging.error("Error: Unexpected time value --> "+str(diff))
        return the_date
        
    elif diff.days<366:
      if diff.seconds/3600 == 0:
        return str(abs(diff.days)) + " day" + adds(diff.days)
      return str(abs(diff.days)) + " day" + adds(diff.days) + str(diff.seconds/3600) + " hour" + adds(diff.seconds/3600)
    else:
      return str(diff.days/365) + " year" + adds(diff.days/365)

  except:
    return the_date
#


def getCommonUiParams(self, *args):
  #
  user = users.get_current_user()
  
  # params to be returned
  username = ''
  loggedIn = ''
  message = ''
  userInfo = ''
  userType = ''
  
  if user is not None:
    account = findAccount()
    
    loggedIn = 'true'
    if account is not None:
      if account.name is not None:
        accountName = account.name
      else:
        accountName = ''
        
      if account.description is not None:
        accountDescription = account.description
      else:
        accountDescription = ''
      
      if len(args) > 0 and args[0] is 'edit':
        accountDescription = re.sub('[\']', '\\\'', accountDescription)
        accountDescription = re.sub('[\"]', '\\\"', accountDescription)
        accountDescription = re.sub('[\n\r]', '', accountDescription)
      
      if account.profilePicBlobKey is not None and account.profilePicBlobKey != '':
        accountImageLinkUrl = images.get_serving_url(account.profilePicBlobKey, size=None, crop=False, secure_url=True)
        accountImageUrl = accountImageLinkUrl + '=s108-c'
      else:
        accountImageLinkUrl = ''
        accountImageUrl = '/image/user.jpg'
      
      if account.isStudent == True:
        accountIsStudent = 'true'
      else:
        accountIsStudent = ''
      
      userInfo = {
        'nickname': account.nickname,
        'email':account.email,
        'id': account.id,
        'name': accountName,
        'description': accountDescription,
        'imageLinkUrl': accountImageLinkUrl,
        'imageUrl': accountImageUrl,
        'isStudent': accountIsStudent,
        'isStudentUntil': account.isStudentUntil,
        'itemCount': db.GqlQuery("SELECT __key__ FROM ShopItem WHERE owner = :1 ", account.nickname).count(),
        'wishCount': db.GqlQuery("SELECT __key__ FROM WishList WHERE nickname = :1 ", account.nickname).count(),
        'unreadCount': db.GqlQuery("SELECT __key__ FROM Message WHERE owner = :1 AND isRead = :2", account.nickname, False).count(),
        'requestCount': db.GqlQuery("SELECT __key__ FROM Transaction WHERE owner = :1 AND status = :2", account.nickname, 'Pending').count(),
      }
      userType = 'user'
    else:
      accountImageLinkUrl = ''
      accountImageUrl = '/image/user.jpg'
      userInfo = {
        'nickname': user.nickname(),
        'email':user.email(),
        'id': user.user_id(),
        'name': '',
        'description': '',
        'imageLinkUrl': accountImageLinkUrl,
        'imageUrl': accountImageUrl,
        'isStudent': '',
        'isStudentUntil': '',
        'itemCount': 0,
        'wishCount': 0,
        'unreadCount': 0,
        'requestCount': 0,
      }
      userType = 'visitor'
      
    if db.GqlQuery("SELECT nickname FROM Account WHERE level = 'admin' and id = :1", user.user_id()).count() == 1 or users.is_current_user_admin():
      userType = 'admin'
    
  param = {
    #
    'userType': userType,
    'loggedIn': loggedIn,
    'message': message,
    'osInfo': {
      'application_id': re.sub('s~', '', os.environ.get('APPLICATION_ID', 'hardcode-appdaptor')),
      'version': os.environ.get('CURRENT_VERSION_ID', 'unknown'),
      'user_agent': os.environ.get('HTTP_USER_AGENT', 'unknown'),
      'http_host': os.environ.get('HTTP_HOST', 'unknown'),
      'query_string': os.environ.get('QUERY_STRING', ''),
    },
    'userInfo': userInfo,
  }
  param['url'] = {
      'signin': users.create_login_url(self.request.uri.replace('?logout', '')),
      'signout': users.create_logout_url('http://'+ param['osInfo']['http_host'] +'/?logout'),
      'current': self.request.uri,
  }
  if len(args) > 0:
    param['optionalInfo'] = args[0]
    
  if len(args) > 1:
    param['optionalInfo2'] = args[1]
  
  
  
  if param['osInfo']['query_string'] == "logout" :
    message = "<div class='notice'><div>You have successfully signed out. <a href='" + \
          users.create_login_url(self.request.uri.replace('?logout', '')+'') + \
          "'>Sign in again</a> </div></div>\n\n"
    param['message'] = message
    
  elif param['osInfo']['query_string'] == "profileUpdated" :
    message = "<div class='notice'><div>Your profile is successfully updated.</div></div>\n\n"
    param['message'] = message
  elif param['osInfo']['query_string'] == "profileSetup" :
    message = "<div class='notice'><div>Welcome, "+ userInfo['nickname'] +"! Your account is created.</div></div>\n\n"
    param['message'] = message
    
  elif self.request.get('itemUpdated', '') == "true":
    message = "<div class='notice'><div>The item is successfully updated.</div></div>\n\n"
    param['message'] = message
  elif self.request.get('itemPublished', '') == "true" :
    message = "<div class='notice'><div>The item is published.  <span style='display:inline-block;margin-left:20px;'><a href='/user/addItem'>Add another item</a></span></div></div>\n\n"
    param['message'] = message
  elif self.request.get('itemDeleted', '') == "true" :
    message = "<div class='notice'><div>Item was deleted.</div></div>\n\n"
    param['message'] = message
  elif self.request.get('accountDeleted', '') == "true" :
    message = "<div class='notice'><div>We are sorry to see you going. Your account has been removed.</div></div>\n\n"
    param['message'] = message
  elif self.request.get('allItemsDeleted', '') == "true" :
    message = "<div class='notice'><div>All of your items have been removed successfully.</div></div>\n\n"
    param['message'] = message
  
  if self.request.get('invalidImageFormat', '') == "true" :
    message = "<div class='notice'><div>Error occur when saving image. Please select a valid image file to upload.</div></div><div class='notice'><div>Other changes have been saved successfully. </div></div>\n\n"
    param['message'] = message
  
  return param
#

def getSearchQuery(self):
  
  type = self.request.get("type", 'allItem')
  
  keyword = self.request.get("query", '')
  sortBy = self.request.get("sortBy", '')
  display = self.request.get("display", '')
  priceMin = self.request.get("priceMin", 0)
  priceMax = self.request.get("priceMax", 0)
  
  searchQuery  = {
    'type': type,
    'keyword': keyword,
    'sortBy': sortBy,
    'display': display,
    'priceMin': priceMin, #TODO
    'priceMax': priceMax, #TODO
  }
  return searchQuery
#

def getUserInfo(nickname):
  account = findAccountByNickname(nickname)

  if account is None:
    return None
  
  if account.profilePicBlobKey is not None and account.profilePicBlobKey != '':
    accountImageLinkUrl = images.get_serving_url(account.profilePicBlobKey, size=None, crop=False, secure_url=True)
    accountImageUrl = accountImageLinkUrl + '=s108-c'
  else:
    accountImageLinkUrl = ''
    accountImageUrl = '/image/user.jpg'
  
  if account.isStudent == True:
    accountIsStudent = 'true'
  else:
    accountIsStudent = ''
  
  
  userInfo  = {
    'nickname': account.nickname,
    'description': account.description,
    #'name': account.name,
    #'email':account.email,
    'status': account.status,
    'imageLinkUrl': accountImageLinkUrl,
    'imageUrl': accountImageUrl,
    'isStudent': accountIsStudent,
    'isStudentUntil': account.isStudentUntil,
    'itemCount': db.GqlQuery("SELECT __key__ FROM ShopItem WHERE owner = :1", nickname).count(),
    'avgRating': 0,
    'totalRatingCount': 0,
    'action': 'view',
  }
  return userInfo
#

def findAccount():
  user = users.get_current_user()
  
  if user is None:
    return None
  
  accountQuery = schema.Account.all()
  accountQuery.filter("id = ", user.user_id()) # for google account login only
  account = accountQuery.get()
  
  return account
#
def findAccountByNickname(nickname):
  
  accountQuery = schema.Account.all()
  accountQuery.filter("nickname = ", nickname)
  account = accountQuery.get()
  
  return account
#


def prepareShopItemData(self, *args):
  
  itemId = ''
  action = ''
  
  if len(args) > 0:
    itemId = args[0]
    
  if len(args) > 1:
    action = args[1]
    
  item = schema.ShopItem.get_by_id(int(itemId))
  
  itemTitle = itemDescription = itemStatus = itemPrivacy = \
    itemCreationDate = itemExpiryDate = itemOwner = itemImageLinkUrl = ''
  itemImageUrl = '/image/noimage.png'
  itemPicBlobKeys = itemVideoBlobKeys = []
  itemMarkedPrice = itemDiscountPrice = itemQuantity = itemExpireIn = itemViewCount = 0
  
  if item.title is not None:
    itemTitleReadOnly = item.title
    itemTitle = re.sub('[\']', '\\\'', item.title)
  if item.description is not None:
    itemDescription = re.sub('[\n\r]', '', item.description)
  if item.profilePicBlobKey is not None and item.profilePicBlobKey != '':
    itemImageLinkUrl = images.get_serving_url(item.profilePicBlobKey, size=None, crop=False, secure_url=True)
    itemImageUrl = itemImageLinkUrl + '=s108-c'
    
  if item.picBlobKeys is not None:
    itemPicBlobKeys = item.picBlobKeys
  if item.videoBlobKeys is not None:
    itemVideoBlobKeys = item.videoBlobKeys
  if item.markedPrice is not None:
    itemMarkedPrice = item.markedPrice/100.0
  if item.discountPrice is not None:
    itemDiscountPrice = item.discountPrice/100.0
  if item.quantity is not None:
    itemQuantity = item.quantity
  if item.status is not None:
    itemStatus = item.status
  if item.privacy is not None:
    itemPrivacy = item.privacy
  if item.creationDate is not None:
    itemCreationDate = item.creationDate
  if item.expiryDate is not None:
    itemExpiryDate = item.expiryDate
  if item.expireIn is not None:
    itemExpireIn = item.expireIn
  if item.owner is not None:
    itemOwner = item.owner
  if item.viewCount is not None:
    itemViewCount = item.viewCount
  
  if action is 'edit':
    itemDescription = re.sub('[\']', '\\\'', itemDescription)
    itemDescription = re.sub('[\"]', '\\\"', itemDescription)
      
  itemInfo = {
    'id': itemId,
    'title': itemTitle,
    'titleReadOnly': itemTitleReadOnly,
    'description': itemDescription,
    'imageUrl': itemImageUrl,
    'imageLinkUrl': itemImageLinkUrl,
    'picBlobKeys': itemPicBlobKeys,
    'videoBlobKeys': itemVideoBlobKeys,
    'markedPrice': itemMarkedPrice,
    'discountPrice': itemDiscountPrice,
    'quantity': itemQuantity,
    'status': itemStatus,
    'privacy': itemPrivacy,
    'creationDate': itemCreationDate,
    'expiryDate': itemExpiryDate,
    'expireIn': itemExpireIn,
    'owner': itemOwner,
    'viewCount': itemViewCount,
    'action': action
  }
  
  return itemInfo
  
def findItemById(itemId):
  if not itemId.isdigit() or int(itemId) <1:
    return None
    
  return schema.ShopItem.get_by_id(int(itemId))




