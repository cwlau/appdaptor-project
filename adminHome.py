
import os
import webapp2
import logging

#---------------- Import from Google ------------------
#
from google.appengine.api import users, images
from google.appengine.ext import db
from google.appengine.ext.webapp import template
#
#------------------------------------------------------

#----------------- Custom Classes & -------------------
#----------------- Datastore Schema -------------------
#
from commonFunction import createEventLog
from commonFunction import dateFromNow, oneDayOrDate
from commonFunction import getCommonUiParams
from commonFunction import invalidateTokenList
from commonFunction import findAccount, findAccountByNickname
from commonFunction import returnJsonResult
from commonFunction import retrieveEventLogFullSet, retrieveApplicationSettings
from commonFunction import retrieveRestrictedNicknameList
from commonFunction import updateApplicationSettings
from decorator import AdminOnly
from decorator import UserNicknameRequired
import schema
#
#------------------------------------------------------



class AdminManagementHandler(webapp2.RequestHandler):
  @AdminOnly
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/adminManagement.html")
    self.response.out.write(template.render(path, getCommonUiParams(self)))
#


class ListAdminHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
    
  @AdminOnly
  def post(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/adminAdminList.json")
    
    account = findAccount()
    adminAccountQuery = schema.Account.all().filter("level = ", 'admin')
    
    result_length = 1000
    admins = adminAccountQuery.fetch(result_length)
    result_length = min(result_length, len(admins))
    
    adminList = []
    index = 0
    
    for a in admins:
    
      if result_length-1 == index:
        noComma = 'True'
      else:
        index = index + 1
        noComma = 'False'
      
      adminInfo = {
        'nickname': a.nickname,
        'noComma': noComma
      }
      adminList.append(adminInfo)
    
    if result_length == 0:
      adminList.append({
        'endOfList': 'True',
        'noComma': 'True'
      })
    
    resultList = {
      'adminList': adminList,
    }
    self.response.out.write(template.render(path, resultList))
#



class AddAdminHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
    
  @AdminOnly
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    if self.request.get('admin', None) is not None:
    
      account = findAccount()
      admin = findAccountByNickname(self.request.get('admin'))
      if admin is None:
        returnJsonResult(self, 'false', 'no such account')
        return
      
      admin.level = 'admin'
      admin.put()
      
      createEventLog(account.nickname, 'ADMIN_CREATE', 'admin = ' + admin.nickname , '' )
      returnJsonResult(self, 'true')
    
    else:
      returnJsonResult(self, 'false', 'blank')
#
class RemoveAdminHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
    
  @AdminOnly
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    if self.request.get('admin', None) is not None:
      account = findAccount()
      admin = findAccountByNickname(self.request.get('admin'))
      if admin is None:
        returnJsonResult(self, 'false', 'no such account')
        return
      
      admin.level = 'user'
      admin.put()
      
      createEventLog(account.nickname, 'ADMIN_DELETE', 'admin = ' + admin.nickname , '' )
      returnJsonResult(self, 'true')
    
    else:
      returnJsonResult(self, 'false', 'blank')
#






class UserManagementHandler(webapp2.RequestHandler):
  @AdminOnly
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/adminUserManagement.html")
    self.response.out.write(template.render(path, getCommonUiParams(self)))
#

class ListUserHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
    
  @AdminOnly
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    type = self.request.get('type', '')
    value = self.request.get('value', '')
    
    accountList = []
    
    if type != '' and value != '':
      if type == 'nickname':
        userAccountQuery = schema.Account.all().filter("nickname = ", value)
        result_length = 1000
        accounts = userAccountQuery.fetch(result_length)
        result_length = min(result_length, len(accounts))
        
        index = 0
        
        for a in accounts:
        
          if result_length-1 == index:
            noComma = 'True'
          else:
            index = index + 1
            noComma = 'False'
          
          accountInfo = {
            'id': a.key().id(),
            'nickname': a.nickname,
            'itemCount': db.GqlQuery("SELECT __key__ FROM ShopItem WHERE owner = :1 ", a.nickname).count(),
            'status': a.status,
            'noComma': noComma
          }
          accountList.append(accountInfo)
        
        if result_length == 0:
          accountList.append({
            'endOfList': 'True',
            'noComma': 'True'
          })
      
      elif type == 'id':
        if not value.isdigit() or int(value) < 1:
          returnJsonResult(self, 'false', 'Bad request')
          return
          
        account = schema.Account.get_by_id(int(value))
        if account is None:
          returnJsonResult(self, 'false', 'Account not found')
          return
        else:
          accountList.append({
            'id': account.key().id(),
            'nickname': account.nickname,
            'itemCount': db.GqlQuery("SELECT __key__ FROM ShopItem WHERE owner = :1 ", account.nickname).count(),
            'status': account.status,
            'noComma': 'True'
          })
      else:
        accountList.append({
          'endOfList': 'True',
          'noComma': 'True'
        })
    else:
      userAccountQuery = schema.Account.all()
      result_length = 1000
      accounts = userAccountQuery.fetch(result_length)
      result_length = min(result_length, len(accounts))
      
      index = 0
      
      for a in accounts:
      
        if result_length-1 == index:
          noComma = 'True'
        else:
          index = index + 1
          noComma = 'False'
        
        accountInfo = {
          'id': a.key().id(),
          'nickname': a.nickname,
          'itemCount': db.GqlQuery("SELECT __key__ FROM ShopItem WHERE owner = :1 ", a.nickname).count(),
          'status': a.status,
          'noComma': noComma
        }
        accountList.append(accountInfo)
      
      if result_length == 0:
        accountList.append({
          'endOfList': 'True',
          'noComma': 'True'
        })
    
    resultList = {
      'accountList': accountList,
    }
    
    path = os.path.join(os.path.dirname(__file__), "template/adminUserList.json")
    self.response.out.write(template.render(path, resultList))
#


class UpdateUserStatusHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
    
  @AdminOnly
  def post(self):
  
    type = self.request.get('type', '')
    value = self.request.get('value', '')
    
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    account = findAccount()
    
    if type != '' and value != '':
      user = findAccountByNickname(value)
      if user is None:
        returnJsonResult(self, 'false', 'Account not exist')
        return
        
      if type == 'activate':
        user.status='Active'
        user.put()
        createEventLog(account.nickname, 'ACCOUNT_ACTIVATE', 'account = ' + user.nickname , '' )
        returnJsonResult(self, 'true')
        
        # update account item status to Suspend if status = Suspend
        
        shopItemQuery = schema.ShopItem.all().filter("owner = ", user.nickname).filter("status = ", 'Suspend')
        shopItems = shopItemQuery.fetch(999999)
        
        for item in shopItems:
          item.status = 'Active'
          item.put()
        
        return
      elif type == 'deactivate':
        user.status='Suspend'
        user.put()
        createEventLog(account.nickname, 'ACCOUNT_DEACTIVATE', 'account = ' + user.nickname , '' )
        logging.info("account " + user.nickname + " is suspended")
        # update account item status to Suspend if status = Active
        
        shopItemQuery = schema.ShopItem.all().filter("owner = ", user.nickname).filter("status = ", 'Active')
        shopItems = shopItemQuery.fetch(999999)
        
        for item in shopItems:
          item.status = 'Suspend'
          item.put()
        
        returnJsonResult(self, 'true')
        return
    
    returnJsonResult(self, 'false', 'Bad Request')


class ListItemHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
    
  @AdminOnly
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    type = self.request.get('type', '')
    value = self.request.get('value', '')
    
    itemList = []
    
    if type != '' and value != '':
      if type == 'nickname':
        logging.info("type = nickname")
        itemQuery = schema.ShopItem.all().filter("owner = ", value)
        result_length = 1000
        items = itemQuery.fetch(result_length)
        result_length = min(result_length, len(items))
        
        index = 0
        
        for a in items:
        
          if result_length-1 == index:
            noComma = 'True'
          else:
            index = index + 1
            noComma = 'False'
          
          itemInfo = {
            'id': a.key().id(),
            'title': a.title,
            'owner': a.owner,
            'viewCount': a.viewCount,
            'status': a.status,
            'noComma': noComma
          }
          itemList.append(itemInfo)
        
        if result_length == 0:
          itemList.append({
            'endOfList': 'True',
            'noComma': 'True'
          })
      
      elif type == 'id':
        logging.info("type = id")
        if not value.isdigit() or int(value) < 1:
          returnJsonResult(self, 'false', 'Bad request')
          return
          
        item = schema.ShopItem.get_by_id(int(value))
        if item is None:
          returnJsonResult(self, 'false', 'Item not found')
          return
        else:
          itemList.append({
            'id': item.key().id(),
            'title': item.title,
            'owner': item.owner,
            'viewCount': item.viewCount,
            'status': item.status,
            'noComma': 'True'
          })
      else:
        logging.info("else")
        itemList.append({
          'endOfList': 'True',
          'noComma': 'True'
        })
    else:
      itemList.append({
        'endOfList': 'True',
        'noComma': 'True'
      })
    
    resultList = {
      'itemList': itemList,
    }
    
    path = os.path.join(os.path.dirname(__file__), "template/adminItemList.json")
    self.response.out.write(template.render(path, resultList))
#

class DeleteItemHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
    
  @AdminOnly
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    account = findAccount()
    
    #TODO run in transaction
    itemId = self.request.get('value', '')
    
    if not itemId.isdigit() or int(itemId) < 1:
      returnJsonResult(self, 'false', 'Bad request')
      return
    
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
      createEventLog(account.nickname, 'ADMIN_DELETE_ITEM', 'itemId = '+ itemId , '')
      returnJsonResult(self, 'true')
    else:
      returnJsonResult(self, 'false', 'Item does not exist')











class ItemManagementHandler(webapp2.RequestHandler):
  @AdminOnly
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/adminItemManagement.html")
    self.response.out.write(template.render(path, getCommonUiParams(self)))
#





class EventManagementHandler(webapp2.RequestHandler):
  @AdminOnly
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    
    params = {
      'actor': self.request.get('actor', ''),
      'actionType': self.request.get('actionType', '')
    }
    
    path = os.path.join(os.path.dirname(__file__), "template/adminEventLog.html")
    self.response.out.write(template.render(path, getCommonUiParams(self, params, retrieveEventLogFullSet()) ))
#

class EventLogListHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
  
  @AdminOnly
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    path = os.path.join(os.path.dirname(__file__), "template/adminEventLogList.json")
    
    account = findAccount()
    eventLogQuery = schema.EventLog.all()
    
    actor = self.request.get('actor', '')
    actionType = self.request.get('actionType', '')
    
    if actor != '':
      eventLogQuery.filter('actor = ', actor)
    if actionType != '':
      eventLogQuery.filter('actionType = ', actionType)
    
    #
    eventLogQuery.order("-date")
    
    result_length = 1000
    eventLogs = eventLogQuery.fetch(result_length)
    result_length = min(result_length, len(eventLogs))
    
    eventLogList = []
    index = 0
    endOfList = ''
    
    for e in eventLogs:
    
      if result_length-1 == index:
        noComma = 'True'
      else:
        index = index + 1
        noComma = 'False'
      
      datetime = oneDayOrDate(e.date)
      date_fromnow = dateFromNow(e.date)
      exactDate = e.date
      
      eventLogInfo = {
        'eventType': e.actionType,
        'actorName': e.actor,
        'eventTarget': e.target,
        'eventDetails': e.content,
        'datetime': datetime,
        'exactDate': exactDate,
        'date_fromnow': date_fromnow,
        'endOfList': endOfList,
        'noComma': noComma
      }
      
      eventLogList.append(eventLogInfo)
    
    if len(eventLogList) == 0:
      eventLogList.append({
        'endOfList': 'True',
        'noComma': 'True'
      })
    
    resultList = {
      'eventLogList': eventLogList,
    }
    self.response.out.write(template.render(path, resultList))
    return
#


class ApplicationSettingsViewHandler(webapp2.RequestHandler):
  @AdminOnly
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    
    params = {
      'item_max_activeDays': retrieveApplicationSettings('env', 'item_max_activeDays'),
      'item_min_activeDays': retrieveApplicationSettings('env', 'item_min_activeDays'),
      'item_max_price': retrieveApplicationSettings('env', 'item_max_price'),
      'item_min_price': retrieveApplicationSettings('env', 'item_min_price'),
      'item_max_quantity': retrieveApplicationSettings('env', 'item_max_quantity'),
      'item_min_quantity': retrieveApplicationSettings('env', 'item_min_quantity'),
      'nickname_max_chars': retrieveApplicationSettings('env', 'nickname_max_chars'),
      'nickname_min_chars': retrieveApplicationSettings('env', 'nickname_min_chars'),
      'item_expire_alert_daysBefore': retrieveApplicationSettings('env', 'item_expire_alert_daysBefore'),
      'search_result_length': retrieveApplicationSettings('env', 'search_result_length'),
      'conversation_group_size': retrieveApplicationSettings('env', 'conversation_group_size'),
      'restrictedNicknameList': self.request.get('actor', ''),
      'cron_item_expiryDateChecker': retrieveApplicationSettings('cron', 'cron_item_expiryDateChecker'),
      'cron_account_expiryDateChecker': retrieveApplicationSettings('cron', 'cron_account_expiryDateChecker')
    }
    
    path = os.path.join(os.path.dirname(__file__), "template/adminApplicationSettings.html")
    self.response.out.write(template.render(path, getCommonUiParams(self, params, retrieveEventLogFullSet()) ))
#

class ApplicationSettingsUpdateHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/')
  
  @AdminOnly
  def post(self):
    account = findAccount()
    
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    type = self.request.get('type', '')
    name = self.request.get('name', '')
    value = self.request.get('value', 0)
    remarks = self.request.get('remarks', '')
    
    if type == '' or value == '':
      returnJsonResult(self, 'false', 'Required values cannot be blank')
      return
      
    if type != 'nickname' and type!='delete-restricted' and name == '': # only skip the case for restricted nicknames
      returnJsonResult(self, 'false', 'Required values cannot be blank')
      return
    
    updateApplicationSettings(type, name, remarks, value)
    
    createEventLog(account.nickname, 'APP_SETTINGS_UPDATE', name + ' = '+ str(value) , '')
    returnJsonResult(self, 'true', 'Changes saved')
#


class RestrictedNicknameListHandler(webapp2.RequestHandler):
  def get(self):
    self.post()
    #self.redirect('/')
  
  @AdminOnly
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    nicknameList = []
    
    for name in retrieveRestrictedNicknameList():
      nicknameList.append({
        'type': 'system_default',
        'value': name,
        'remarks': '',
        'endOfList': ''
      })
    
    nicknameQuery = schema.ApplicationSettings.all().filter('type = ', 'nickname')
    restrictedList = nicknameQuery.fetch(999999)
    
    for record in restrictedList:
      nicknameList.append({
        'type': 'restricted',
        'value': record.value,
        'remarks': record.remarks,
        'endOfList': ''
      })
    
    nicknameList.append({
      'endOfList': 'True',
      'noComma': 'True'
    })
    
    resultList = {
      'nicknameList': nicknameList,
    }
    
    path = os.path.join(os.path.dirname(__file__), "template/adminRestrictedNicknameList.json")
    self.response.out.write(template.render(path, resultList ))
#



class APISettingsListViewHandler(webapp2.RequestHandler):
  @AdminOnly
  def get(self):
    self.post()
  
  @AdminOnly
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    type = self.request.get('type', '')
    
    # retrieve a list of api (access token given by other applications)
    
    if type != "partner" and type != "own":
      returnJsonResult(self, 'false', 'API type is missing')
      return
    
    # TODO get from cache. If cache miss, get from datastore.
    
    
    
    # TODO cache miss
    apiQuery = schema.ApplicationApiSettings.all().filter("apiType = ", type)
    apiResult = apiQuery.fetch(999999)
    
    apiList = []
    for api in apiResult:
      apiList.append({
        'id': api.key().id(),
        'domain': api.domain,
        'key': api.token,
        'remarks': api.remarks
      })
    
    apiList.append({
      'endOfList': 'True',
      'noComma': 'True'
    })
     
    resultList = {
      'apiList': apiList
    }
    
    path = os.path.join(os.path.dirname(__file__), "template/adminApiList.json")
    self.response.out.write(template.render(path, resultList ))
    
    
    
#

class APISettingsUpdateHandler(webapp2.RequestHandler):
  def get(self):
    self.post()
    #self.redirect('/')
  
  @AdminOnly
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    account = findAccount()
    
    action = self.request.get('action', '')
    if action == 'add':
      
      type = self.request.get('type', '')
      if type is None:
        returnJsonResult(self, 'false', 'missing api type')
        return
      
      domain = self.request.get('domain', '')
      key = self.request.get('key', '')
      remarks = self.request.get('remarks', '')
      
      if domain == '' or key == '':
        returnJsonResult(self, 'false', 'missing domain or key')
        return
      
      apiRecord = schema.ApplicationApiSettings(
        domain = domain,
        token = key,
        apiType = type,
        remarks = remarks
      )
      apiRecord.put()
      
      invalidateTokenList()
      createEventLog(account.nickname, 'ADMIN_API_UPDATE', domain + ', token = '+ str(key) , 'api id = '+ str(apiRecord.key().id()))
      returnJsonResult(self, 'true', 'API added')
    
    elif action == 'delete':
    
      id = self.request.get('id', '')
      apiRecord = schema.ApplicationApiSettings.get_by_id(int( id ))
      if apiRecord is None:
        returnJsonResult(self, 'false', 'api record not found')
        return
      
      apiRecord.delete()
      createEventLog(account.nickname, 'ADMIN_API_DELETE', 'api id = '+ str(id) , '')
      
      invalidateTokenList()
      returnJsonResult(self, 'true', 'API deleted')
    
    else:
      returnJsonResult(self, 'false', 'missing action type')
      #pass
    
    # update other application's data. for API calls.
    # effective immediately. reload cache
    
    
#





class WishlistManagementHandler(webapp2.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    path = os.path.join(os.path.dirname(__file__), "template/adminWishlistManagement.html")
    self.response.out.write(template.render(path, getCommonUiParams(self)))
#


class WishlistSearchHandler(webapp2.RequestHandler):
  def get(self):
    self.post()
    #self.redirect('/')
  
  @AdminOnly
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    account = findAccount() # current logged in account
    
    # both can be blank. returning all result
    itemid = self.request.get('itemid', '')
    nickname = self.request.get('account', '')
    
    #if itemid == '' and nickname = '':
    #  returnJsonResult(self, 'false', 'Must give some information here')
    
    
    #TODO validate itemid and account
    # wrong itemid/ account will result in no returning result
    
    wishlistQuery = schema.WishList.all()
    if itemid != '':
      wishlistQuery = wishlistQuery.filter("shopItemId = ", itemid)
      logging.debug("shopItemId = " + str(itemid))
    if nickname != '':
      wishlistQuery = wishlistQuery.filter("nickname = ", nickname)
      logging.debug("nickname = " + nickname)
    
    wishlists = wishlistQuery.fetch(999999)
    
    wishlistItemList = []
    for wishlist in wishlists:
      item = schema.ShopItem.get_by_id(int(wishlist.shopItemId))
      
      # item should not be None here. All wishlist item should be able to map with one existing item.
      # report error, skip getting item information
      #TODO remove associated wishlist item when item owner attempts to remove one item
      if item is None:
        logging.error("Error while getting wishlist item information. Item (id = "+ str(wishlist.shopItemId) +") does not exist.")
        continue
      
      itemTitle = item.title

      wishlistItemList.append({
        'itemid': str(wishlist.shopItemId),
        'itemTitle': itemTitle,
        'wishlistOwnerAccount': wishlist.nickname
      })
    
    wishlistItemList.append({
      'endOfList': 'True',
      'noComma': 'True'
    })
    
    resultList = {
      'wishlistItemList': wishlistItemList,
    }
    
    path = os.path.join(os.path.dirname(__file__), "template/adminWishlistItemList.json")
    self.response.out.write(template.render(path, resultList ))


class WishlistDeleteHandler(webapp2.RequestHandler):
  def get(self):
    self.post()
    #self.redirect('/')
  
  @AdminOnly
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    account = findAccount() # current logged in account
    
    # all fields required
    itemid = self.request.get('itemid', '')
    nickname = self.request.get('account', '')
    
    if itemid == '' or nickname == '':
      returnJsonResult(self, 'false', 'Must give all information here')
    
    
    #TODO validate itemid and account
    # wrong itemid/ account will result in no returning result
    
    wishlistQuery = schema.WishList.all()
    if itemid != '':
      wishlistQuery = wishlistQuery.filter("shopItemId = ", itemid)
    if nickname != '':
      wishlistQuery = wishlistQuery.filter("nickname = ", nickname)
    
    # should return at most one record
    wishlist = wishlistQuery.get()
    
    if wishlist is not None:
      wishlist.delete()
      
      # Event Log
      createEventLog(account.nickname, 'WISHLIST_ADMIN_REMOVE', 'itemId = '+ itemid + ', account = ' + nickname , '')
      returnJsonResult(self, 'true', 'Wishlist item was removed')
    else:
      
      returnJsonResult(self, 'false', 'Wishlist item could not be found')
    #
#




app = webapp2.WSGIApplication([
  ('/admin/manage', AdminManagementHandler),
  ('/admin/listAdmin', ListAdminHandler),
  ('/admin/addAdmin', AddAdminHandler),
  ('/admin/removeAdmin', RemoveAdminHandler),
  
  ('/admin/user', UserManagementHandler),
  ('/admin/userList', ListUserHandler),
  ('/admin/updateStatus', UpdateUserStatusHandler),
  
  ('/admin/item', ItemManagementHandler),
  ('/admin/itemList', ListItemHandler),
  ('/admin/deleteItem', DeleteItemHandler),
  
  ('/admin/wishlist', WishlistManagementHandler),
  ('/admin/wishlist/find', WishlistSearchHandler),
  ('/admin/wishlist/delete', WishlistDeleteHandler),
  
  ('/admin/event', EventManagementHandler),
  ('/admin/eventLogList', EventLogListHandler),
  
  ('/admin/apiSettingsList', APISettingsListViewHandler),
  ('/admin/updateApiSettings', APISettingsUpdateHandler),
  
  ('/admin/appSettings', ApplicationSettingsViewHandler),
  ('/admin/restrictedNicknameList', RestrictedNicknameListHandler),
  ('/admin/updateAppSettings', ApplicationSettingsUpdateHandler),
  
  ('/admin/', AdminManagementHandler)
], debug=True)
