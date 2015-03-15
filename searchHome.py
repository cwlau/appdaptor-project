
import re
import os
import urllib
import webapp2
import logging
import json

#---------------- Import from Google ------------------
#
from google.appengine.api import users, images, urlfetch
from google.appengine.ext import db
from google.appengine.ext.webapp import template
#
#------------------------------------------------------

#----------------- Custom Classes & -------------------
#----------------- Datastore Schema -------------------
#
from commonFunction import findAccount
from commonFunction import findItemById
from commonFunction import getSearchQuery
from commonFunction import getCommonUiParams
from commonFunction import returnJsonResult
from commonFunction import returnXmlResult
from commonFunction import retrieveTargetApplicationList
from commonFunction import retrieveApplicationSettings


import schema
from schema import ShopItem
from schema import WishList

#
#------------------------------------------------------

def lookupRelevantShopItems(value):

  logging.info("lookupRelevantShopItems: searching items for \"" + value + "\" ")
  
  allItemIdList = []
  allItems = schema.ShopItem.all().filter("status = ", 'Active').fetch(999999)
  for item in allItems:
    allItemIdList.append(str(item.key().id()))
  
  rawResult = {}
  for key in value.split():
  
    keywordQuery = schema.KeywordRepo.all().filter("keyword = ", key)
    keywordList = keywordQuery.fetch(999999)
    
    for record in keywordList:
      item = findItemById(record.shopItemId)
      
      if rawResult.has_key(record.shopItemId):
        rawResult[record.shopItemId] += record.weight
      else:
        rawResult[record.shopItemId] = record.weight

  #
  # Sort by weight of item
  sortedItemIdList = sorted(rawResult, key=rawResult.__getitem__, reverse=True)
  
  
  # filter unwanted items
  items = []
  for id in sortedItemIdList:
    item = schema.ShopItem.get_by_id(int(id))
    if item.status == 'Active':
      items.append(item)

  return items




def lookupRelevantShopItemsByTitle(value):

  logging.debug("lookupRelevantShopItemsByTitle: searching items for \"" + value + "\" ")
  
  rawResult = {}
  # search for each keyword
  for key in value.split():
  
    keywordQuery = schema.KeywordRepo.all().filter("keyword = ", key).filter("weight = ", 3) # get title only
    keywordList = keywordQuery.fetch(999999)
    
    for record in keywordList:
      item = findItemById(record.shopItemId)
      
      if rawResult.has_key(record.shopItemId):
        rawResult[record.shopItemId] += record.weight
      else:
        rawResult[record.shopItemId] = record.weight
  
  #
  # Sort by weight of item
  sortedItemIdList = sorted(rawResult, key=rawResult.__getitem__, reverse=True)
  
  #filter unwanted items
  items = []
  _search_suggestion_limit = retrieveApplicationSettings('env', 'search_result_length')
  for id in sortedItemIdList:
    item = schema.ShopItem.get_by_id(int(id))
    if item.status!= 'Active':
      continue
    items.append(item)
    if len(items) >= int(_search_suggestion_limit):
      break
  
  return items


class SearchHandler(webapp2.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = "text/html"
    account = findAccount()
    target = self.request.get('type')
    if account is None:
      if target=='myItem' or target == 'myWishlist': 
        self.redirect("/search/")
    
    path = os.path.join(os.path.dirname(__file__), "template/search.html")
    self.response.out.write(template.render(path, getCommonUiParams(self, getSearchQuery(self), retrieveApplicationSettings('env', 'search_result_length'))))

#

class SearchQueryHandler(webapp2.RequestHandler):
  def get(self):
    self.post()
    
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    # request parameters processing
    # target,value,price,sortOrder
    
    target = self.request.get('target')
    if target is None: 
      returnJsonResult(self, 'false')
      logging.info("target is None")
      return
    
    
    
    
    
    
    # get input from request. We use lowercase for filtering
    value = self.request.get('value', '').lower()
    
    
    range = int(float(self.request.get('range', retrieveApplicationSettings('env', 'search_result_length')) ) )
    offset = int(float(self.request.get('offset', 0)))
    
    
    items = []
    
    if target == 'partner':
    
      # get result from external site.
      # use urlfetch for production site. do nothing for localhost
      
      if "localhost" not in os.environ.get('HTTP_HOST'):
        
        applicationRecipientList = retrieveTargetApplicationList()
        temp_result = []
        for app in applicationRecipientList:
          logging.info(app['domain'])
          logging.info(app['auth_token'])
          
          #form_fields = {
          #  "auth_token": app['auth_token'],
          #  "query": value,
          #  "limit": int(float(self.request.get('range', retrieveApplicationSettings('env', 'search_result_length')) ) ),
          #  "offset": int(float(self.request.get('offset', 0)))
          #}
          #form_data = urllib.urlencode(form_fields)
          
          
          ## search
          
          try:
            queryString = "?auth_token=" + app['auth_token'] + "&query=" + value + "&limit=" + str(int(float(self.request.get('range', retrieveApplicationSettings('env', 'search_result_length')) ) )) + "&offset=" + str(int(float(self.request.get('offset', 0))))
            
            result = urlfetch.fetch(url=app['domain'] + "webservices/search" + queryString,
                                    #payload=form_data,
                                    method=urlfetch.GET,
                                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                    validate_certificate=False)
            logging.info(app['domain'] + "webservices/search" + queryString)
          except:
            continue
          
          if result.status_code != 200:
            logging.info("Error occurred when retrieving information from "
              + app['domain'] + ", with token = " + app['auth_token'])
          
          else:
            received_content = result.content
            json_decoder = json.decoder.JSONDecoder()
            try:
              decoded_json = json_decoder.decode(received_content)
            except:
              returnJsonResult(self, 'false', 'Error Occurred')
            
            else:
              temp_result.append(decoded_json)
              logging.info(decoded_json)
              
            
        #
        # get results back. parse them to the format we want
          
        # here is the result from all other applications
        temp_index = 0
        for tempItem in temp_result:
          logging.info(tempItem)
          if tempItem['items'] == []:
            continue
          
          # get its value, one by one. Should be capped at upper limit.
          items.append({
            'id': tempItem['items'][0]['id'],
            'title': tempItem['items'][0]['title'],
            'url': tempItem['items'][0]['url'],
            'description': tempItem['items'][0]['description'],
            'imageUrl': tempItem['items'][0]['image'],
            'price': tempItem['items'][0]['price'],
            'partnerSite': "Partner Site",
            'owner': tempItem['items'][0]['seller']['username']
          })
          temp_index += 1
        
        items.append({
          'endOfList': 'True',
          'noComma': 'true'
        })
        
        searchResult = {
          'items': items
        }
        
        path = os.path.join(os.path.dirname(__file__), "template/searchPartnerResult.json")
        self.response.out.write(template.render(path, searchResult))
        
      else:
        logging.debug("urlfetch skipped for local environment")
        
      
      
    
    
    else:
      # my items
      if target == 'myItem':
      
        account = findAccount()
        if account is None:
          returnJsonResult(self, 'false', 'Login Required')
          return
          
        # sort by relevance when there is some input
        if value != '':
          raw_items = lookupRelevantShopItems(value)
          itemsNoOffset = []
          for item in raw_items:
            if item.owner == account.nickname:
              logging.debug(str(item.key().id()) + " matched")
              itemsNoOffset.append(item)
          
        
        # sort by popularity when there is some input
        else:
        
          itemQuery = ShopItem.all()
          #itemQuery.filter("status = ", 'Active')
          itemQuery.filter("owner = ", account.nickname)
          itemQuery.order("-viewCount")
          itemQuery.order("-markedPrice")
          itemsNoOffset = itemQuery.fetch(999999)
        
      # all items
      elif target == 'allItem':
        
        # sort by relevance when there is some input
        if value != '':
          itemsNoOffset = lookupRelevantShopItems(value)
          
        
        # sort by popularity when there is some input
        else:
          itemQuery = ShopItem.all()
          itemQuery.filter("status = ", 'Active')
          itemQuery.order("-viewCount")
          itemQuery.order("-markedPrice")
          itemsNoOffset = itemQuery.fetch(999999)
        
      
      # my wishlist
      elif target == 'myWishlist':
        account = findAccount()
        if account is None:
          returnJsonResult(self, 'false', 'Login Required')
          return
        
        wishlistQuery = WishList.all()
        wishlistQuery.filter("nickname = ", account.nickname)
        wishlistItems = wishlistQuery.fetch(999999)
        
        itemsNoOffset = []
        for w in wishlistItems:
          item = schema.ShopItem.get_by_id(int(w.shopItemId))
          itemsNoOffset.append(item)
        
      else:
        returnJsonResult(self, 'false')
        logging.info("Target is unexpected value: "+ target)
        return
      
      
      
      
      
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
        if len(itemsNoOffset)-1 == index:
          item.noComma = 'true'
        else:
          index = index + 1
          item.noComma = 'false'
      
        if item.profilePicBlobKey is not None and item.profilePicBlobKey != '':
          item.imageUrl = images.get_serving_url(item.profilePicBlobKey, size=None, crop=False, secure_url=True)+'=s108-c'
        else:
          item.imageUrl = '/image/noimage.png'


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
          # reached the end
          break
      
      #
      
      
      
      
      if len(items) == 0:
        items.append({
          'endOfList': 'True',
          'noComma': 'true'
        })
      
      searchResult = {
        'items': items,
      }
      
      path = os.path.join(os.path.dirname(__file__), "template/searchResult.json")
      self.response.out.write(template.render(path, searchResult))
#













class SearchSuggestHandler(webapp2.RequestHandler):
  def get(self):
    self.post()
  
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    target = self.request.get('target')
    if target is None: 
      returnJsonResult(self, 'false')
      logging.info("target is None")
      return
      
    
    
    # get input from request. We use lowercase for filtering
    value = self.request.get('value', '').lower()
    items = []
    
    if target == 'myItem':
      account = findAccount()
      if account is None:
        returnJsonResult(self, 'false', 'Login Required')
        return
      
      suggestedItems = lookupRelevantShopItemsByTitle(value)
      
      for suggestedItem in suggestedItems:
        logging.debug(suggestedItem.key().id())
        if suggestedItem.owner == account.nickname:
          logging.debug(str(suggestedItem.key().id()) + " matched")
          items.append(suggestedItem)
        
      
    elif target == 'allItem':
      
      suggestedItems = lookupRelevantShopItemsByTitle(value)
      
      for suggestedItem in suggestedItems:
        logging.debug( "allItem: "+ str(suggestedItem.key().id()))
        items.append(suggestedItem)
      
    elif target == 'partner':
      pass
    
    else:
      returnJsonResult(self, 'false')
      return
    
    
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
    
    
    
    ## search suggestion
    
    # if display limit has not reached, we use external result for suggestion
    if "localhost" not in os.environ.get('HTTP_HOST') and target == 'partner':
      if len(resultList) < int(float(self.request.get('range', retrieveApplicationSettings('env', 'search_result_length')) ) ):
        applicationRecipientList = retrieveTargetApplicationList()
        temp_result = []
        for app in applicationRecipientList:
          logging.info(app['domain'])
          logging.info(app['auth_token'])
          
          #form_fields = {
          #  "auth_token": app['auth_token'],
          #  "query": value
          #}
          #form_data = urllib.urlencode(form_fields)
          
          queryString = "?auth_token=" + app['auth_token'] + "&query=" + value
          
          result = urlfetch.fetch(url=app['domain'] + "webservices/search_suggestions" + queryString,
                                  #payload=form_data,
                                  method=urlfetch.GET,
                                  headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                  validate_certificate=False)
          
          logging.info(app['domain'] + "webservices/search_suggestions" + queryString)
          
          if result.status_code != 200:
            logging.info("Error occurred when retrieving information from "
              + app['domain'] + ", with token = " + app['auth_token'])
          
          else:
            received_content = result.content
            json_decoder = json.decoder.JSONDecoder()
            try:
              decoded_json = json_decoder.decode(received_content)
            except:
              returnJsonResult(self, 'false', 'Error Occurred')
            
            else:
              temp_result.append(decoded_json)
              logging.info(decoded_json)
              
        
        logging.info("resultList = " + str(resultList))
        for tempItem in temp_result:
          if tempItem['items'] == []:
            continue
          
          logging.info(tempItem)
          resultList.append({
            'title': tempItem['items'][0]['fullString']
          })
          
          logging.info(tempItem)
          
          
          if len(resultList) > int(float(self.request.get('range', retrieveApplicationSettings('env', 'search_result_length')) ) ):
            break
            
          #
        #
    
    searchResult = {
      'items': resultList,
    }
    
    path = os.path.join(os.path.dirname(__file__), "template/searchSuggest.json")
    self.response.out.write(template.render(path, searchResult))
#










class SearchQuickListHandler(webapp2.RequestHandler):
  def get(self):
    self.post()
  
  def post(self):
    self.response.headers['Content-Type'] = "application/json;charset=UTF-8"
    
    type = self.request.get('type', '')
    range = int(float(self.request.get('range', retrieveApplicationSettings('env', 'search_result_length')) ) )
    offset = int(float(self.request.get('offset', 0)))
    
    rawResult = {}
    
    # What's New
    if type == 'new':
    
      itemQuery = ShopItem.all()
      itemQuery.filter("status = ", 'Active')
      itemQuery.order("-creationDate")
      items = itemQuery.fetch(range)
    
    # What's Hot
    elif type == 'hot':
    
      itemQuery = ShopItem.all()
      itemQuery.filter("status = ", 'Active')
      itemQuery.order("-viewCount")
      items = itemQuery.fetch(range)

    # Most wanted items
    elif type == 'wanted':
      wishlistQuery = schema.WishList.all()
      wishlistEntries = wishlistQuery.fetch(999999)
      
      for record in wishlistEntries:
        item = findItemById(record.shopItemId)
        
        if rawResult.has_key(record.shopItemId):
          rawResult[record.shopItemId] += 1
        else:
          rawResult[record.shopItemId] = 1
  
      # Sort by item wishlist count
      sortedItemIdList = sorted(rawResult, key=rawResult.__getitem__, reverse=True)
      
      items = []
      index = 0
      for id in sortedItemIdList:
        item = schema.ShopItem.get_by_id(int(id))
        item.wishListCount = rawResult[id]
        index += 1
        if index > range:
          break
        items.append(item)


    # Recent Deals
    elif type == 'deals':
      transactionQuery = schema.Transaction.all().filter('endDate != ', None).order('-endDate')
      transactionList = transactionQuery.fetch(range)
      
      items = []
      for t in transactionList:
        item = schema.ShopItem.get_by_id(int(t.itemId))
        items.append(item)

    else:
      items = []
      pass
    
    # End of general data collection, start data processing
    
    index = 0
    
    for item in items:
      item.id = item.key().id()
      #item.description = re.sub('[<]', ' <', item.description) # add space before removing html tags
      #item.description = re.sub('&nbsp;', ' ', item.description) # remove unwanted strings
      
      if item.markedPrice is not None:
        item.markedPriceInFloat = item.markedPrice/100.0
      if item.discountPrice is not None:
        item.discountPriceInFloat = item.discountPrice/100.0
      if item.profilePicBlobKey is not None and item.profilePicBlobKey != '':
        item.imageUrl = images.get_serving_url(item.profilePicBlobKey, size=None, crop=False, secure_url=True)+'=s108-c'
      else:
        item.imageUrl = '/image/noimage.png'
      
      if index == 0:
        item.noComma = 'true'
      else:
        item.noComma = 'false'
        
      index = index + 1
    
    if len(items) == 0:
      items.append({
        'endOfList': 'True',
        'noComma': 'true'
      })
    
    searchResult = {
      'items': items,
    }
    
    path = os.path.join(os.path.dirname(__file__), "template/quickSearchResult.json")
    self.response.out.write(template.render(path, searchResult))
#






app = webapp2.WSGIApplication([
  ('/search/', SearchHandler),
  ('/search/query', SearchQueryHandler),
  ('/search/suggest', SearchSuggestHandler),
  ('/search/quickList', SearchQuickListHandler)
], debug=True)


